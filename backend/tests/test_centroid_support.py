"""
Tests for Block 3.6 — Centroid Support Monitoring.

Covers the compute_centroid_support function and the
GET /api/soc/centroid-support endpoint.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pytest
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

def test_centroid_support_has_six_categories():
    data = client.get("/api/soc/centroid-support").json()
    assert "support_summary" in data
    # Cold start returns {} (no bootstrap yet); live system returns 6
    assert len(data["support_summary"]) in (0, 6)


# ---------------------------------------------------------------------------
# Test 3 — overall_health is one of the three allowed values
# ---------------------------------------------------------------------------

def test_centroid_support_overall_health_valid():
    data = client.get("/api/soc/centroid-support").json()
    assert data["overall_health"] in ["GREEN", "AMBER", "RED"]


# ---------------------------------------------------------------------------
# Test 4 — unit test: 2 factors outside 2σ triggers warning
# ---------------------------------------------------------------------------

def test_centroid_support_compute_function_flags_outside():
    mu      = np.full((1, 1, 6), 0.5)
    mu_zero = np.full((1, 1, 6), 0.5)
    sigma   = [0.1] * 6
    # Push 2 factors outside 2σ boundary (threshold = 0.2)
    mu[0, 0, 0] = 0.9   # deviation 0.4 > 0.2 → outside
    mu[0, 0, 1] = 0.1   # deviation 0.4 > 0.2 → outside
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
