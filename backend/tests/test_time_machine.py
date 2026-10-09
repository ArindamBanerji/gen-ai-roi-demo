"""AGE checkpoint lineage tests for the centroid time machine."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import numpy as np
from fastapi.testclient import TestClient

from app.services import time_machine


def _payloads():
    return [
        {
            "backup_id": "soc:checkpoint:one",
            "mu": np.zeros((6, 4, 6)).tolist(),
            "shape": [6, 4, 6],
            "timestamp_epoch": 1000,
            "step": 10,
            "sha256": "one",
            "version": "age-checkpoint",
            "metadata": {"decision_count": 10},
        },
        {
            "backup_id": "soc:checkpoint:two",
            "mu": (np.ones((6, 4, 6)) * 2).tolist(),
            "shape": [6, 4, 6],
            "timestamp_epoch": 2000,
            "step": 20,
            "sha256": "two",
            "version": "age-checkpoint",
            "metadata": {"decision_count": 20},
        },
    ]


def _environment():
    scorer = SimpleNamespace(centroids=np.ones((6, 4, 6)) * 2)
    return scorer


def test_list_snapshots_reads_age_lineage():
    with patch.object(time_machine, "_age_payloads", return_value=_payloads()):
        rows = time_machine.list_snapshots()
    assert [row["snapshot_id"] for row in rows] == [
        "soc:checkpoint:one",
        "soc:checkpoint:two",
    ]
    assert all(row["file_path"] == "" for row in rows)


def test_get_snapshot_uses_current_scorer_and_bootstrap():
    scorer = _environment()
    with patch.object(time_machine, "_age_payloads", return_value=_payloads()), \
         patch.object(time_machine, "get_profile_scorer", return_value=scorer), \
         patch.object(time_machine, "get_mu_zero", return_value=np.zeros((6, 4, 6))):
        result = time_machine.get_snapshot("soc:checkpoint:two")
    assert result["snapshot_id"] == "soc:checkpoint:two"
    assert result["drift_from_bootstrap"] == np.sqrt(6 * 4 * 6 * 4)
    assert result["drift_from_current"] == 0.0


def test_compare_snapshots_returns_provenance_and_distances():
    with patch.object(time_machine, "_age_payloads", return_value=_payloads()), \
         patch.object(time_machine, "get_mu_zero", return_value=np.zeros((6, 4, 6))):
        result = time_machine.compare_snapshots(
            "soc:checkpoint:one", "soc:checkpoint:two"
        )
    assert result["snapshot_a"]["file_path"] == ""
    assert result["overall_frobenius_distance"] > 0
    assert result["timeline"]["decision_counts"] == [10, 20]
    assert result["top_movers"]


def test_missing_age_checkpoint_is_not_silent():
    with patch.object(time_machine, "_age_payloads", return_value=[]):
        try:
            time_machine.get_snapshot("missing")
        except time_machine.SnapshotNotFoundError:
            pass
        else:
            raise AssertionError("missing AGE checkpoint did not fail loudly")


def _run(awaitable):
    return asyncio.run(awaitable)


def _no_none(value):
    if isinstance(value, dict):
        return all(item is not None and _no_none(item) for item in value.values())
    if isinstance(value, list):
        return all(item is not None and _no_none(item) for item in value)
    return value is not None


def test_timeline_partial_iks_failure():
    with patch.object(time_machine, "_age_payloads", return_value=_payloads()), \
         patch.object(time_machine, "get_mu_zero", return_value=np.zeros((6, 4, 6))), \
         patch.object(time_machine, "_compute_current_ceiling_estimate", return_value=80.0), \
         patch.object(time_machine, "compute_iks_v2", new=AsyncMock(side_effect=RuntimeError("iks down"))):
        result = _run(time_machine.get_evolution_timeline(object()))

    assert result is not None
    assert len(result["timeline"]) == 2
    assert result["timeline_available"] is True
    assert result["iks_available"] is False
    assert result["current"]["iks_v2"] == 0.0
    assert result["degraded"] is True


def test_timeline_complete_route_json_types():
    from app.main import app

    with patch.object(time_machine, "_age_payloads", return_value=_payloads()), \
         patch.object(time_machine, "get_mu_zero", return_value=np.zeros((6, 4, 6))), \
         patch.object(time_machine, "_compute_current_ceiling_estimate", return_value=80.0), \
         patch.object(time_machine, "compute_iks_v2", new=AsyncMock(return_value={
             "iks_v2": 0.0, "components": {}, "interpretation": "healthy",
         })):
        response = TestClient(app).get("/api/time-machine/timeline")

    assert response.status_code == 200
    assert _no_none(response.json())


def test_timeline_construction_error_returns_typed_unavailable():
    from app.main import app
    from app.routers import time_machine_router

    with patch.object(
        time_machine_router,
        "get_evolution_timeline",
        new=AsyncMock(side_effect=RuntimeError("checkpoint store down")),
    ):
        response = TestClient(app).get("/api/time-machine/timeline")

    assert response.status_code == 200
    payload = response.json()
    assert payload["timeline"] == []
    assert payload["timeline_available"] is False
    assert payload["iks_available"] is False
    assert payload["ceiling_available"] is False
    assert payload["degraded"] is True
    assert payload["reason"]
    assert _no_none(payload)


def test_timeline_none_returns_typed_unavailable():
    from app.main import app
    from app.routers import time_machine_router

    with patch.object(
        time_machine_router,
        "get_evolution_timeline",
        new=AsyncMock(return_value=None),
    ):
        response = TestClient(app).get("/api/time-machine/timeline")

    assert response.status_code == 200
    payload = response.json()
    assert payload["timeline"] == []
    assert payload["timeline_available"] is False
    assert payload["iks_available"] is False
    assert payload["ceiling_available"] is False
    assert payload["degraded"] is True
    assert payload["reason"]
    assert _no_none(payload)


def test_timeline_healthy_zero_iks():
    with patch.object(time_machine, "_age_payloads", return_value=_payloads()), \
         patch.object(time_machine, "get_mu_zero", return_value=np.zeros((6, 4, 6))), \
         patch.object(time_machine, "_compute_current_ceiling_estimate", return_value=80.0), \
         patch.object(time_machine, "compute_iks_v2", new=AsyncMock(return_value={
             "iks_v2": 0.0, "components": {}, "interpretation": "healthy",
         })):
        result = _run(time_machine.get_evolution_timeline(object()))

    assert result is not None
    assert result["iks_available"] is True
    assert result["current"]["iks_v2"] == 0.0
