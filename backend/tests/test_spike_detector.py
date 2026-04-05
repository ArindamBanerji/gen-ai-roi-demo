"""
Block 9.2 — D3 Spike detector tests.
All Neo4j calls use AsyncMock — no live Neo4j required.
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.learning_health import compute_volume_baseline, detect_volume_spike
from app.services.gae_state import (
    set_volume_spike,
    is_volume_spike_active,
    guarded_update,
    init_learning_state,
    get_profile_scorer,
)


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _day_rows(*counts):
    """Build run_query rows for daily alert counts."""
    return [{"day_bucket": i, "daily_count": c} for i, c in enumerate(counts)]


def _mock_neo4j(rows):
    mock = AsyncMock()
    mock.run_query.return_value = rows
    return mock


# ---------------------------------------------------------------------------
# Test 1 — baseline computed correctly from history
# ---------------------------------------------------------------------------

def test_baseline_computed_from_history():
    """
    10 days of data: counts = [10, 20, 30, 10, 20, 30, 10, 20, 30, 10]
    mean = 19.0, std = 7.746...  (np.std)
    spike_sigma = 5.0 (conservative, n_decisions < 1000)
    threshold = 19.0 + 5.0 * max(7.746, 1.0) ≈ 57.73
    """
    counts = [10, 20, 30, 10, 20, 30, 10, 20, 30, 10]
    mock = _mock_neo4j(_day_rows(*counts))

    # Force conservative spike_sigma via low n_decisions
    with patch("app.domains.soc.config.GateConfig") as MockGC:
        instance = MockGC.return_value
        instance.spike_sigma = 5.0
        result = _run(compute_volume_baseline(mock))

    expected_mean = float(np.mean(counts))
    expected_std  = float(np.std(counts))

    assert result["data_points"]  == len(counts)
    assert result["window_days"]  == 30
    assert result["spike_sigma"]  == 5.0
    assert result["daily_mean"]   == pytest.approx(expected_mean, abs=0.01)
    assert result["daily_std"]    == pytest.approx(expected_std,  abs=0.01)
    assert "spike_threshold" in result
    assert result["spike_threshold"] > result["daily_mean"]


# ---------------------------------------------------------------------------
# Test 2 — spike detected when today_count exceeds threshold
# ---------------------------------------------------------------------------

def test_spike_detected_when_above_threshold():
    """
    Baseline: mean=20, std=2, spike_sigma=5 → threshold = 20 + 5*max(2,1) = 30.
    today_count=100 > 30 → spike_detected=True.
    """
    mock = _mock_neo4j(_day_rows(*([20] * 10)))   # flat baseline mean=20, std=0

    with patch("app.domains.soc.config.GateConfig") as MockGC:
        instance = MockGC.return_value
        instance.spike_sigma = 5.0
        result = _run(detect_volume_spike(mock, today_count=100))

    # threshold = 20 + 5 * max(0, 1.0) = 25   (std floored at 1.0)
    assert result["spike_detected"] is True,   f"Expected spike, got {result}"
    assert result["today_count"]    == 100
    assert result["spike_threshold"] > 0


# ---------------------------------------------------------------------------
# Test 3 — no spike when volume is normal
# ---------------------------------------------------------------------------

def test_no_spike_when_normal_volume():
    """
    Baseline: mean=20, std=0 (floored to 1), sigma=5 → threshold=25.
    today_count=22 < 25 → spike_detected=False.
    """
    mock = _mock_neo4j(_day_rows(*([20] * 10)))

    with patch("app.domains.soc.config.GateConfig") as MockGC:
        instance = MockGC.return_value
        instance.spike_sigma = 5.0
        result = _run(detect_volume_spike(mock, today_count=22))

    assert result["spike_detected"] is False, f"Expected no spike, got {result}"
    assert result["today_count"] == 22


# ---------------------------------------------------------------------------
# Test 4 — spike flag freezes centroid updates via guarded_update
# ---------------------------------------------------------------------------

def test_spike_flag_freezes_updates():
    """
    When _volume_spike_active=True, guarded_update() returns None
    and does NOT call scorer.update().
    """
    from unittest.mock import MagicMock
    scorer = MagicMock()

    try:
        set_volume_spike(True)
        assert is_volume_spike_active() is True

        f = np.zeros(6)
        result = guarded_update(scorer, f=f, category_index=0,
                                action_index=0, correct=True)

        assert result is None,             "Should return None when spike active"
        scorer.update.assert_not_called()  # update must NOT have been called
    finally:
        set_volume_spike(False)            # always restore flag


# ---------------------------------------------------------------------------
# Test 5 — endpoint returns baseline fields and spike_active flag
# ---------------------------------------------------------------------------

def test_endpoint_returns_baseline():
    """GET /api/soc/volume-baseline returns required fields."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    baseline_data = {
        "daily_mean":      25.0,
        "daily_std":       4.5,
        "spike_threshold": 47.5,
        "spike_sigma":     5.0,
        "window_days":     30,
        "data_points":     28,
    }

    with patch(
        "app.services.learning_health.compute_volume_baseline",
        new=AsyncMock(return_value=baseline_data),
    ):
        resp = client.get("/api/soc/volume-baseline")

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()

    for field in ("daily_mean", "daily_std", "spike_threshold",
                  "spike_sigma", "window_days", "data_points", "spike_active"):
        assert field in body, f"Missing field '{field}' in response"

    assert isinstance(body["spike_active"], bool)
    assert body["daily_mean"]      == pytest.approx(25.0,  abs=0.01)
    assert body["spike_threshold"] == pytest.approx(47.5,  abs=0.01)
    assert body["window_days"]     == 30
