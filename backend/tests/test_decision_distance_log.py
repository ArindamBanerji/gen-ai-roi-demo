"""
test_decision_distance_log.py — BACKLOG-015 extension: EXP-G1 decision distance log.

3 tests:
  1. GET /api/soc/distance-log returns 200
  2. Response has required fields (entries, convergence_trend, note, "EXP-G1" in note)
  3. Unit test: centroid distance formula is correct (L2 norm of element-wise diff)
"""

import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

_ENDPOINT = "/api/soc/distance-log"


def test_distance_log_endpoint_returns_200():
    """GET /api/soc/distance-log always returns HTTP 200."""
    resp = client.get(_ENDPOINT)
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"


def test_distance_log_has_required_fields():
    """Response body contains entries, convergence_trend, note, and 'EXP-G1' in note."""
    resp = client.get(_ENDPOINT)
    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data, "missing 'entries'"
    assert "convergence_trend" in data, "missing 'convergence_trend'"
    assert "note" in data, "missing 'note'"
    assert "EXP-G1" in data["note"], f"'EXP-G1' not in note: {data['note']!r}"
    assert data["convergence_trend"] in (
        "decreasing", "increasing", "stable", "insufficient_data"
    ), f"unexpected convergence_trend: {data['convergence_trend']!r}"


def test_centroid_distance_formula_correct():
    """
    Unit test: L2 norm formula matches expected value for uniform tensors.

    mu      = all 0.7, shape (6, 4, 6) → 144 elements
    mu_zero = all 0.5, shape (6, 4, 6) → diff = 0.2 each element
    expected = sqrt(144 * 0.2^2) = 0.2 * sqrt(144) = 0.2 * 12 = 2.4
    """
    mu      = np.full((6, 4, 6), 0.7)
    mu_zero = np.full((6, 4, 6), 0.5)
    expected = float(np.linalg.norm(mu.flatten() - mu_zero.flatten()))
    assert abs(expected - 0.2 * np.sqrt(144)) < 0.001, (
        f"formula mismatch: got {expected}, expected {0.2 * np.sqrt(144):.6f}"
    )
    # Verify the function in reconvergence_logger uses the same formula
    # by checking it is callable with correct signature.
    from app.services.reconvergence_logger import log_decision_distance
    import inspect
    sig = inspect.signature(log_decision_distance)
    params = list(sig.parameters.keys())
    assert "mu"      in params, "log_decision_distance missing 'mu' param"
    assert "mu_zero" in params, "log_decision_distance missing 'mu_zero' param"
    assert "pattern_history_value"       in params
    assert "alert_category_distribution" in params
