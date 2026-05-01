"""
Tests for FEATURE-04 Centroid Time Machine backend.
"""

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.time_machine_router import router as time_machine_router
import app.services.time_machine as time_machine
from app.services.time_machine import compare_to_bootstrap


class DummyScorer:
    def __init__(self, centroids):
        self.centroids = np.array(centroids, dtype=np.float64)


class DummyNeo4j:
    async def run_query(self, query, params=None):
        return []


def _run(coro):
    return asyncio.run(coro)


def _snapshot_payload(mu, timestamp_epoch, decision_count, backup_id, version="1.0"):
    payload = {
        "mu": np.array(mu, dtype=np.float64).tolist(),
        "shape": list(np.array(mu, dtype=np.float64).shape),
        "step": int(decision_count),
        "timestamp_epoch": int(timestamp_epoch),
        "version": version,
    }
    canonical = json.dumps(payload, sort_keys=True)
    payload["sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    payload["backup_id"] = backup_id
    payload["metadata"] = {
        "trigger": "test",
        "decision_count": int(decision_count),
        "decision_id": f"decision-{decision_count}",
        "category": "credential_access",
    }
    return payload


def _write_snapshot(base_dir: Path, mu, timestamp_epoch, decision_count, suffix):
    backup_id = f"centroid_backup_{timestamp_epoch}_{suffix}"
    payload = _snapshot_payload(mu, timestamp_epoch, decision_count, backup_id)
    path = base_dir / f"{backup_id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload, path


@pytest.fixture
def snapshot_env(tmp_path):
    backup_dir = tmp_path / "centroid_backups"
    backup_dir.mkdir()

    mu_zero = np.zeros((6, 4, 6), dtype=np.float64)
    mu_a = mu_zero.copy()
    mu_b = mu_zero.copy()
    mu_c = mu_zero.copy()

    mu_b[0, 0, :] = 1.0
    mu_b[2, 1, :] = 2.0
    mu_c[0, 0, :] = 2.0
    mu_c[2, 1, :] = 4.0

    payload_a, _ = _write_snapshot(backup_dir, mu_a, 1000, 10, "aaaa1111")
    payload_b, _ = _write_snapshot(backup_dir, mu_b, 2000, 20, "bbbb2222")
    payload_c, _ = _write_snapshot(backup_dir, mu_c, 3000, 30, "cccc3333")

    current = DummyScorer(mu_c)
    monkeypatches = [
        patch.object(time_machine, "_BACKUP_DIR", backup_dir),
        patch.object(time_machine, "get_mu_zero", return_value=mu_zero),
        patch.object(time_machine, "get_profile_scorer", return_value=current),
    ]
    for item in monkeypatches:
        item.start()

    yield {
        "backup_dir": backup_dir,
        "mu_zero": mu_zero,
        "mu_a": mu_a,
        "mu_b": mu_b,
        "mu_c": mu_c,
        "payload_a": payload_a,
        "payload_b": payload_b,
        "payload_c": payload_c,
        "current": current,
    }

    for item in reversed(monkeypatches):
        item.stop()


def _build_test_client():
    app = FastAPI()
    app.include_router(time_machine_router, prefix="/api")
    return TestClient(app)


def test_list_snapshots_sorted(snapshot_env):
    snapshots = time_machine.list_snapshots()
    assert [item["snapshot_id"] for item in snapshots] == [
        snapshot_env["payload_a"]["backup_id"],
        snapshot_env["payload_b"]["backup_id"],
        snapshot_env["payload_c"]["backup_id"],
    ]
    assert [item["decision_count"] for item in snapshots] == [10, 20, 30]


def test_list_snapshots_empty_dir(tmp_path):
    backup_dir = tmp_path / "empty"
    with patch.object(time_machine, "_BACKUP_DIR", backup_dir):
        assert time_machine.list_snapshots() == []


def test_get_snapshot_returns_tensor_and_frobenius_drifts(snapshot_env):
    detail = time_machine.get_snapshot(snapshot_env["payload_b"]["backup_id"])
    expected_bootstrap = float(np.linalg.norm(snapshot_env["mu_b"] - snapshot_env["mu_zero"]))
    expected_current = float(np.linalg.norm(snapshot_env["mu_b"] - snapshot_env["mu_c"]))

    assert detail["shape"] == [6, 4, 6]
    assert detail["decision_count"] == 20
    assert detail["centroids"] == snapshot_env["mu_b"].tolist()
    assert detail["drift_from_bootstrap"] == pytest.approx(expected_bootstrap)
    assert detail["drift_from_current"] == pytest.approx(expected_current)


def test_get_snapshot_invalid_id_raises():
    with pytest.raises(time_machine.SnapshotNotFoundError):
        time_machine.get_snapshot("missing_snapshot")


def test_compare_snapshots_returns_distances(snapshot_env):
    result = time_machine.compare_snapshots(
        snapshot_env["payload_a"]["backup_id"],
        snapshot_env["payload_b"]["backup_id"],
    )
    expected_total = float(np.linalg.norm(snapshot_env["mu_b"] - snapshot_env["mu_a"]))

    assert result["overall_frobenius_distance"] == pytest.approx(expected_total)
    assert result["movement_direction"] == "away_from_bootstrap"
    assert result["timeline"]["decision_counts"] == [10, 20]


def test_compare_identical_snapshots_zero_distance(snapshot_env):
    result = time_machine.compare_snapshots(
        snapshot_env["payload_b"]["backup_id"],
        snapshot_env["payload_b"]["backup_id"],
    )
    assert result["overall_frobenius_distance"] == pytest.approx(0.0)
    assert all(value == pytest.approx(0.0) for value in result["per_category_distances"].values())
    assert all(item["distance"] == pytest.approx(0.0) for item in result["top_movers"])


def test_evolution_timeline_drift_increases(snapshot_env):
    with patch.object(
        time_machine,
        "compute_iks_v2",
        new=AsyncMock(return_value={
            "iks_v2": 42.0,
            "components": {"signal": 42.0},
            "interpretation": "stable",
        }),
    ):
        timeline = _run(time_machine.get_evolution_timeline(DummyNeo4j()))

    drifts = [item["drift_from_bootstrap"] for item in timeline["timeline"]]
    assert drifts == sorted(drifts)
    assert timeline["current"]["iks_v2"] == 42.0


def test_timeline_ceiling_estimate_populated(snapshot_env):
    with patch.object(
        time_machine,
        "compute_iks_v2",
        new=AsyncMock(return_value={
            "iks_v2": 42.0,
            "components": {"signal": 42.0},
            "interpretation": "stable",
        }),
    ):
        timeline = _run(time_machine.get_evolution_timeline(DummyNeo4j()))

    assert isinstance(timeline["ceiling_estimate"], float)
    assert timeline["ceiling_estimate"] > 0.0


def test_corrupted_snapshot_skipped(snapshot_env, caplog):
    bad_path = snapshot_env["backup_dir"] / "centroid_backup_2500_badbad00.json"
    bad_path.write_text("{not-json", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        snapshots = time_machine.list_snapshots()
    assert len(snapshots) == 3
    assert any("Skipping corrupted snapshot" in record.message for record in caplog.records)


def test_per_category_sums_and_top_movers_ordering(snapshot_env):
    result = time_machine.compare_snapshots(
        snapshot_env["payload_a"]["backup_id"],
        snapshot_env["payload_b"]["backup_id"],
    )
    expected_cat0 = float(np.linalg.norm(snapshot_env["mu_b"][0] - snapshot_env["mu_a"][0]))
    expected_cat2 = float(np.linalg.norm(snapshot_env["mu_b"][2] - snapshot_env["mu_a"][2]))

    assert result["per_category_distances"]["credential_access"] == pytest.approx(expected_cat0)
    assert result["per_category_distances"]["data_exfiltration"] == pytest.approx(expected_cat2)
    assert result["top_movers"][0]["category"] == "data_exfiltration"
    assert result["top_movers"][0]["action"] == "investigate"
    assert result["top_movers"][0]["distance"] >= result["top_movers"][1]["distance"]


def test_drift_from_bootstrap_matches_manual_frobenius(snapshot_env):
    detail = time_machine.get_snapshot(snapshot_env["payload_c"]["backup_id"])
    expected = float(np.linalg.norm(snapshot_env["mu_c"] - snapshot_env["mu_zero"]))
    assert detail["drift_from_bootstrap"] == pytest.approx(expected)


def test_timeline_skips_corrupted_and_returns_monotonic_decision_counts(snapshot_env):
    bad_payload, bad_path = _write_snapshot(
        snapshot_env["backup_dir"],
        snapshot_env["mu_b"],
        1500,
        15,
        "dddd4444",
    )
    raw = json.loads(bad_path.read_text(encoding="utf-8"))
    raw["sha256"] = "0" * 64
    bad_path.write_text(json.dumps(raw), encoding="utf-8")

    timeline = _run(time_machine.get_evolution_timeline(DummyNeo4j()))
    counts = [item["decision_count"] for item in timeline["timeline"]]
    assert counts == [10, 20, 30]
    assert all(earlier < later for earlier, later in zip(counts, counts[1:]))
    assert bad_payload["backup_id"] not in {item["snapshot_id"] for item in timeline["timeline"]}


def test_sha256_matches_file_content(snapshot_env):
    path = snapshot_env["backup_dir"] / f"{snapshot_env['payload_b']['backup_id']}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    canonical = json.dumps(
        {
            key: value
            for key, value in payload.items()
            if key not in {"sha256", "backup_id", "metadata"}
        },
        sort_keys=True,
    )
    expected = hashlib.sha256(canonical.encode()).hexdigest()
    assert payload["sha256"] == expected


def test_router_snapshots_list(snapshot_env):
    client = _build_test_client()
    response = client.get("/api/time-machine/snapshots")
    assert response.status_code == 200
    body = response.json()
    assert len(body["snapshots"]) == 3


def test_router_snapshot_detail(snapshot_env):
    client = _build_test_client()
    response = client.get(f"/api/time-machine/snapshots/{snapshot_env['payload_b']['backup_id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["shape"] == [6, 4, 6]
    assert body["decision_count"] == 20


def test_router_compare(snapshot_env):
    client = _build_test_client()
    response = client.get(
        f"/api/time-machine/compare?a={snapshot_env['payload_a']['backup_id']}"
        f"&b={snapshot_env['payload_b']['backup_id']}"
    )
    assert response.status_code == 200
    body = response.json()
    assert "per_category_distances" in body
    assert "top_movers" in body


def test_compare_to_bootstrap_overall_distance_matches_manual(snapshot_env):
    result = compare_to_bootstrap(snapshot_env["payload_b"]["backup_id"])
    expected = float(np.linalg.norm(snapshot_env["mu_b"] - snapshot_env["mu_zero"]))
    assert result["overall_frobenius_distance"] == pytest.approx(expected)
    assert result["snapshot_b"]["snapshot_id"] == "bootstrap"
    assert result["drift_from_bootstrap"]["snapshot_b"] == pytest.approx(0.0)
    assert result["drift_from_bootstrap"]["snapshot_a"] == pytest.approx(expected)


def test_compare_to_bootstrap_returns_per_category_distances(snapshot_env):
    result = compare_to_bootstrap(snapshot_env["payload_b"]["backup_id"])
    assert "per_category_distances" in result
    assert "top_movers" in result
    assert "movement_direction" in result
    from app.services.time_machine import _EXPORT_CATEGORIES
    for category in _EXPORT_CATEGORIES:
        assert category in result["per_category_distances"]
    assert result["movement_direction"] == "away_from_bootstrap"
    assert len(result["top_movers"]) <= 5


def test_router_compare_bootstrap_endpoint(snapshot_env):
    client = _build_test_client()
    response = client.get(
        f"/api/time-machine/compare-bootstrap?snapshot_id={snapshot_env['payload_b']['backup_id']}"
    )
    assert response.status_code == 200
    body = response.json()
    assert "per_category_distances" in body
    assert "overall_frobenius_distance" in body
    assert body["snapshot_b"]["snapshot_id"] == "bootstrap"


def test_router_timeline(snapshot_env):
    client = _build_test_client()
    with patch.object(
        time_machine,
        "compute_iks_v2",
        new=AsyncMock(return_value={
            "iks_v2": 7.5,
            "components": {"signal": 7.5},
            "interpretation": "cold",
        }),
    ), patch("app.routers.time_machine_router.neo4j_client", DummyNeo4j()):
        response = client.get("/api/time-machine/timeline")

    assert response.status_code == 200
    body = response.json()
    assert len(body["timeline"]) == 3
    assert "ceiling_estimate" in body
    assert "ceiling_estimate" in body["timeline"][0]
