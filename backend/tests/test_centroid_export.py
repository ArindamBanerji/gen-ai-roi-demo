"""
Block 2.3 -- Centroid export tests.
Requires Block 2.2 (bootstrap_centroids). No live Neo4j required.
"""
import asyncio
import hashlib
import json
import os
import sys
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.gae_state import (
    init_learning_state,
    get_profile_scorer,
    build_centroid_export,
)


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Shared scorer fixture
# ---------------------------------------------------------------------------

init_learning_state()
_SCORER = get_profile_scorer()

_BOOTSTRAP_MU = _SCORER.centroids.tolist()   # use current mu as fake bootstrap


def _neo4j_with_bootstrap(mu=None):
    """AsyncMock client that returns bootstrap data (or empty rows)."""
    mock = AsyncMock()
    if mu is not None:
        mock.run_query.return_value = [{
            "bootstrap_mu":    mu,
            "bootstrap_shape": list(np.array(mu).shape),
            "stored_at":       1700000000000,
            "gae_version":     "0.7.20",
        }]
    else:
        mock.run_query.return_value = []
    return mock


# ---------------------------------------------------------------------------
# Test 1 — export has exactly 10 fields (11 with sha256 always present)
# ---------------------------------------------------------------------------

def test_export_has_10_fields():
    """build_centroid_export returns a dict with the required 10 fields."""
    expected_fields = {
        "export_version", "generated_at_epoch", "gae_version",
        "tensor_shape", "current_mu", "bootstrap_mu",
        "drift_from_bootstrap", "decision_count",
        "categories", "actions", "sha256",
    }
    mock = _neo4j_with_bootstrap(_BOOTSTRAP_MU)
    export = _run(build_centroid_export(get_profile_scorer(), mock))

    missing = expected_fields - set(export.keys())
    assert not missing, f"Missing fields: {missing}"
    assert len(export) == len(expected_fields), (
        f"Expected {len(expected_fields)} fields, got {len(export)}: {list(export)}"
    )


# ---------------------------------------------------------------------------
# Test 2 — sha256 computed correctly over canonical current_mu JSON
# ---------------------------------------------------------------------------

def test_sha256_computed_correctly():
    """sha256 must equal SHA-256 of canonical JSON of current_mu."""
    mock = _neo4j_with_bootstrap(None)   # no bootstrap -- irrelevant for sha256
    export = _run(build_centroid_export(get_profile_scorer(), mock))

    canonical = json.dumps({"mu": export["current_mu"]}, sort_keys=True)
    expected  = hashlib.sha256(canonical.encode()).hexdigest()

    assert export["sha256"] == expected, (
        f"sha256 mismatch: stored={export['sha256']!r}, computed={expected!r}"
    )
    assert len(export["sha256"]) == 64


# ---------------------------------------------------------------------------
# Test 3 — drift computed correctly when bootstrap is present
# ---------------------------------------------------------------------------

def test_drift_computed_when_bootstrap_present():
    """
    drift_from_bootstrap = mean(|current_mu - bootstrap_mu|).
    When bootstrap == current, drift = 0.0.
    When bootstrap is perturbed by +0.1, drift ~= 0.1.
    """
    scorer = get_profile_scorer()

    # Case A: bootstrap == current → drift should be 0.0
    mock_same = _neo4j_with_bootstrap(scorer.centroids.tolist())
    export_same = _run(build_centroid_export(scorer, mock_same))
    assert export_same["drift_from_bootstrap"] == pytest.approx(0.0, abs=1e-9)

    # Case B: bootstrap perturbed by +0.1 → drift ≈ 0.1
    perturbed = (scorer.centroids + 0.1).tolist()
    mock_perturbed = _neo4j_with_bootstrap(perturbed)
    export_perturbed = _run(build_centroid_export(scorer, mock_perturbed))
    assert export_perturbed["drift_from_bootstrap"] == pytest.approx(0.1, abs=1e-6)


# ---------------------------------------------------------------------------
# Test 4 — drift is None when no bootstrap data available
# ---------------------------------------------------------------------------

def test_drift_none_when_no_bootstrap():
    """drift_from_bootstrap must be None when DeploymentState has no bootstrap."""
    mock = _neo4j_with_bootstrap(None)   # no rows -> get_bootstrap_centroids returns None
    export = _run(build_centroid_export(get_profile_scorer(), mock))

    assert export["drift_from_bootstrap"] is None,  "Expected None drift without bootstrap"
    assert export["bootstrap_mu"]         is None,  "Expected None bootstrap_mu"


# ---------------------------------------------------------------------------
# Test 5 — summary format excludes tensor fields
# ---------------------------------------------------------------------------

def test_summary_format_excludes_tensors():
    """?format=summary returns all fields EXCEPT current_mu and bootstrap_mu."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    mock_export = {
        "export_version":       "1.0",
        "generated_at_epoch":   1700000000000,
        "gae_version":          "0.7.21",
        "tensor_shape":         [6, 4, 6],
        "current_mu":           [[[0.5] * 6] * 4] * 6,
        "bootstrap_mu":         [[[0.5] * 6] * 4] * 6,
        "drift_from_bootstrap": 0.0,
        "decision_count":       500,
        "categories":           ["credential_access", "lateral_movement",
                                 "data_exfiltration", "malware_execution",
                                 "insider_threat", "cloud_infrastructure"],
        "actions":              ["escalate", "investigate", "suppress", "monitor"],
        "sha256":               "a" * 64,
    }

    with patch(
        "app.services.gae_state.build_centroid_export",
        new=AsyncMock(return_value=mock_export),
    ):
        resp = client.get("/api/soc/centroid-export?format=summary")

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()

    assert "current_mu"   not in body, "summary must exclude current_mu"
    assert "bootstrap_mu" not in body, "summary must exclude bootstrap_mu"

    # All other fields must be present
    for field in ("export_version", "generated_at_epoch", "gae_version",
                  "tensor_shape", "drift_from_bootstrap", "decision_count",
                  "categories", "actions", "sha256"):
        assert field in body, f"summary missing field '{field}'"


# =============================================================================
# Block 2.3 — Endpoint contract tests (10-field public schema)
# =============================================================================

from fastapi.testclient import TestClient as _TestClient  # noqa: E402
from app.main import app as _app  # noqa: E402

_client = _TestClient(_app)


def _endpoint_data():
    resp = _client.get("/api/soc/centroid-export")
    assert resp.status_code == 200
    return resp.json()


def _scorer_ready(data: dict) -> bool:
    return data.get("status") != "cold_start"


# ---------------------------------------------------------------------------
# Test 6 — endpoint returns 200 (including cold_start)
# ---------------------------------------------------------------------------

def test_centroid_export_returns_200():
    resp = _client.get("/api/soc/centroid-export")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Test 7 — all ten required fields present
# ---------------------------------------------------------------------------

def test_centroid_export_has_ten_fields():
    data = _endpoint_data()
    if not _scorer_ready(data):
        pytest.skip("ProfileScorer not initialized -- skipping field check")

    required = [
        "exported_at", "export_version", "tensor_shape",
        "categories", "actions", "factors", "centroids",
        "drift_from_bootstrap", "checksum", "decision_count",
    ]
    for field in required:
        assert field in data, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Test 8 — tensor shape [6, 4, 6] and list lengths
# ---------------------------------------------------------------------------

def test_centroid_export_tensor_shape_correct():
    data = _endpoint_data()
    if not _scorer_ready(data):
        pytest.skip("ProfileScorer not initialized -- skipping shape check")

    assert data["tensor_shape"] == [6, 4, 6]
    assert len(data["categories"]) == 6
    assert len(data["actions"]) == 4
    assert len(data["factors"]) == 6


# ---------------------------------------------------------------------------
# Test 9 — centroids dict has all categories/actions with 6 factor values
# ---------------------------------------------------------------------------

def test_centroid_export_centroids_have_six_factors():
    data = _endpoint_data()
    if not _scorer_ready(data):
        pytest.skip("ProfileScorer not initialized -- skipping centroids check")

    for cat in data["categories"]:
        assert cat in data["centroids"], f"Category missing from centroids: {cat}"
        for action in data["actions"]:
            assert action in data["centroids"][cat], \
                f"Action missing from centroids[{cat}]: {action}"
            assert len(data["centroids"][cat][action]) == 6, \
                f"Expected 6 factor values for {cat}/{action}"


# ---------------------------------------------------------------------------
# Test 10 — checksum is 64-char SHA-256 hex string
# ---------------------------------------------------------------------------

def test_centroid_export_checksum_is_string():
    data = _endpoint_data()
    if not _scorer_ready(data):
        pytest.skip("ProfileScorer not initialized -- skipping checksum check")

    assert isinstance(data["checksum"], str)
    assert len(data["checksum"]) == 64  # SHA-256 hex
