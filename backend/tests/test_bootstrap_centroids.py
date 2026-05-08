"""P-01 expert bootstrap centroid artifact and Tab 3 baseline tests."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

from app.domains.soc.config import SCORER_ACTIONS, SOC_PROFILE_CENTROIDS
from app.main import app
from app.routers import soc


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_PATH = REPO_ROOT / "support" / "setup" / "bootstrap_centroids.json"
SCRIPT_PATH = REPO_ROOT / "support" / "scripts" / "calibrate_bootstrap.py"


def _load_calibration_script():
    spec = importlib.util.spec_from_file_location("calibrate_bootstrap", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _artifact_payload() -> dict:
    return json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))


def test_bootstrap_centroids_file_exists():
    assert ARTIFACT_PATH.exists()
    payload = _artifact_payload()
    assert set(payload) == {"shape", "values", "calibration"}
    assert payload["shape"] == [6, 4, 6]
    assert np.asarray(payload["values"], dtype=np.float64).shape == (6, 4, 6)
    assert payload["calibration"]["seed"] == 42


def test_bootstrap_produces_target_confidence():
    script = _load_calibration_script()
    payload = _artifact_payload()
    mean_confidence = script.score_pool(
        np.asarray(payload["values"], dtype=np.float64),
        script.load_seed_alerts(),
    )
    assert 0.48 <= mean_confidence <= 0.58
    assert 0.50 <= payload["calibration"]["mean_confidence"] <= 0.55


def test_bootstrap_below_converged():
    script = _load_calibration_script()
    seed_alerts = script.load_seed_alerts()
    bootstrap_mean = script.score_pool(
        np.asarray(_artifact_payload()["values"], dtype=np.float64),
        seed_alerts,
    )
    converged_mean = script.score_pool(np.asarray(SOC_PROFILE_CENTROIDS), seed_alerts)
    assert bootstrap_mean < converged_mean
    assert converged_mean - bootstrap_mean >= 0.15


def test_baseline_confidence_matches_bootstrap_scorer(monkeypatch):
    class FakeNeo4jClient:
        async def run_query(self, query, params=None):
            if "MATCH (a:Alert {status: 'pending'})" in query:
                return []
            if "RETURN count(n) AS cnt" in query:
                return [{"cnt": 0}]
            if "sum(CASE WHEN d.correct = false THEN 1 ELSE 0 END) AS overrides" in query:
                return [{"verified": 0, "overrides": 0}]
            if "RETURN count(d) AS cnt" in query:
                return [{"cnt": 0}]
            return []

    import app.services.gae_state as gae_state

    def no_live_scorer():
        raise RuntimeError("force centroid fallback category for baseline test")

    monkeypatch.setattr(soc, "neo4j_client", FakeNeo4jClient())
    monkeypatch.setattr(gae_state, "get_profile_scorer", no_live_scorer)
    soc._reset_baseline_scorer_cache()

    expected = round(float(soc._get_baseline_scorer().score(np.full(6, 0.5), 0).confidence), 4)
    calibration_mean = float(_artifact_payload()["calibration"]["mean_confidence"])
    assert not np.isclose(expected, calibration_mean, atol=1e-4)

    response = TestClient(app).get("/api/soc/tab/3/content")
    assert response.status_code == 200
    baseline = response.json()["content"]["recommendation"]["baseline_confidence"]
    assert np.isclose(baseline, expected)
    assert not np.isclose(baseline, calibration_mean, atol=1e-4)
    assert not np.isclose(baseline, 1 / len(SCORER_ACTIONS))


def test_baseline_confidence_falls_back_to_uniform_when_bootstrap_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(soc, "_BOOTSTRAP_CENTROIDS_PATH", tmp_path / "missing.json")
    soc._reset_baseline_scorer_cache()
    scorer = soc._get_baseline_scorer()
    result = scorer.score(np.full(6, 0.5), 0)
    assert soc._BASELINE_SCORER_SOURCE == "uniform_fallback"
    assert np.isclose(result.confidence, 1 / len(SCORER_ACTIONS))


def test_bootstrap_loader_caches(monkeypatch, tmp_path):
    payload_path = tmp_path / "bootstrap_centroids.json"
    payload_path.write_text(ARTIFACT_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(soc, "_BOOTSTRAP_CENTROIDS_PATH", payload_path)
    soc._reset_baseline_scorer_cache()

    first = soc._load_bootstrap_centroids()
    payload_path.unlink()
    second = soc._load_bootstrap_centroids()

    np.testing.assert_allclose(first, second)
