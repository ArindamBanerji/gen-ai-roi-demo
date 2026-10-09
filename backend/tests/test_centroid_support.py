"""
Tests for Block 3.6 -- Centroid Support Monitoring.

Covers the compute_centroid_support function and the
GET /api/soc/centroid-support endpoint.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.centroid_support import compute_centroid_support

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test 1 — endpoint returns 200
# ---------------------------------------------------------------------------

def test_centroid_support_returns_200():
    resp = client.get("/api/soc/centroid-support")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Test 2 — support_summary has exactly 6 categories (or 0 on cold start)
# ---------------------------------------------------------------------------

def test_centroid_support_has_six_categories(monkeypatch):
    import app.services.gae_state as gae_state
    shape = (6, 4, 6)
    monkeypatch.setattr(gae_state, "get_profile_scorer", lambda: SimpleNamespace(centroids=np.full(shape, 0.5)))
    monkeypatch.setattr(gae_state, "get_bootstrap_centroids", AsyncMock(return_value={"mu": np.full(shape, 0.5).tolist()}))
    data = client.get("/api/soc/centroid-support").json()
    assert data["support_available"] is True
    assert len(data["support_summary"]) == 6


# ---------------------------------------------------------------------------
# Test 3 — overall_health is one of the three allowed values
# ---------------------------------------------------------------------------

def test_centroid_support_overall_health_valid():
    data = client.get("/api/soc/centroid-support").json()
    if data["support_available"]:
        assert data["overall_health"] in ["GREEN", "AMBER", "RED"]
    else:
        assert data["overall_health"] == "UNAVAILABLE"
        assert data["reason"]


# ---------------------------------------------------------------------------
# Test 4 — unit test: 2 factors outside 2σ triggers warning
# ---------------------------------------------------------------------------

def test_centroid_support_compute_function_flags_outside():
    mu      = np.full((1, 1, 6), 0.5)
    mu_zero = np.full((1, 1, 6), 0.5)
    sigma   = [0.1] * 6
    # Push 2 factors outside 2σ boundary (threshold = 0.2)
    mu[0, 0, 0] = 0.9   # deviation 0.4 > 0.2 -> outside
    mu[0, 0, 1] = 0.1   # deviation 0.4 > 0.2 -> outside
    result = compute_centroid_support(mu, mu_zero, sigma)
    assert result[(0, 0)]["n_factors_outside"] == 2
    assert result[(0, 0)]["support_status"] == "warning"


# ---------------------------------------------------------------------------
# Test 5 — unit test: small deviation stays inside support
# ---------------------------------------------------------------------------

def test_centroid_support_compute_function_ok_when_inside():
    mu      = np.full((1, 1, 6), 0.5)
    mu_zero = np.full((1, 1, 6), 0.5)
    sigma   = [0.1] * 6
    # Deviation 0.05 < threshold 0.2 → inside
    mu[0, 0, 0] = 0.55
    result = compute_centroid_support(mu, mu_zero, sigma)
    assert result[(0, 0)]["n_factors_outside"] == 0
    assert result[(0, 0)]["support_status"] == "ok"


def _assert_no_none(value):
    if isinstance(value, dict):
        assert all(item is not None for item in value.values())
        for item in value.values():
            _assert_no_none(item)
    elif isinstance(value, list):
        for item in value:
            _assert_no_none(item)


def test_centroid_support_scorer_absent(monkeypatch):
    import app.services.gae_state as gae_state
    monkeypatch.setattr(gae_state, "get_profile_scorer", lambda: None)
    response = client.get("/api/soc/centroid-support")
    assert response.status_code == 200
    data = response.json()
    assert data["support_available"] is False
    assert data["status"] == "cold_start"
    assert data["reason"] == "scorer_uninitialized"
    assert data["overall_health"] == "UNAVAILABLE"
    _assert_no_none(data)


def test_centroid_support_bootstrap_absent(monkeypatch):
    import app.services.gae_state as gae_state
    monkeypatch.setattr(gae_state, "get_profile_scorer", lambda: SimpleNamespace(centroids=np.zeros((6, 4, 6))))
    bootstrap = AsyncMock(return_value=None)
    monkeypatch.setattr(gae_state, "get_bootstrap_centroids", bootstrap)
    data = client.get("/api/soc/centroid-support").json()
    assert data["support_available"] is False
    assert data["reason"] == "bootstrap_missing"
    assert data["overall_health"] == "UNAVAILABLE"
    bootstrap.assert_awaited_once()


def test_centroid_support_bootstrap_read_fails(monkeypatch, caplog):
    import app.services.gae_state as gae_state
    monkeypatch.setattr(gae_state, "get_profile_scorer", lambda: SimpleNamespace(centroids=np.zeros((6, 4, 6))))
    bootstrap = AsyncMock(side_effect=RuntimeError("graph unavailable"))
    monkeypatch.setattr(gae_state, "get_bootstrap_centroids", bootstrap)
    data = client.get("/api/soc/centroid-support").json()
    assert data["support_available"] is False
    assert data["reason"] == "bootstrap_read_failed"
    assert "Bootstrap read failed" in caplog.text
    bootstrap.assert_awaited_once()


def test_centroid_support_valid_no_drift(monkeypatch):
    import app.services.gae_state as gae_state
    shape = (6, 4, 6)
    monkeypatch.setattr(gae_state, "get_profile_scorer", lambda: SimpleNamespace(centroids=np.full(shape, 0.5)))
    bootstrap = AsyncMock(return_value={"mu": np.full(shape, 0.5).tolist()})
    monkeypatch.setattr(gae_state, "get_bootstrap_centroids", bootstrap)
    data = client.get("/api/soc/centroid-support").json()
    assert data["support_available"] is True
    assert data["status"] == "ok"
    assert data["overall_health"] == "GREEN"
    assert data["degraded"] is False


def test_centroid_support_no_null_in_http_response(monkeypatch):
    import app.services.gae_state as gae_state
    monkeypatch.setattr(gae_state, "get_profile_scorer", lambda: None)
    data = client.get("/api/soc/centroid-support").json()
    _assert_no_none(data)
