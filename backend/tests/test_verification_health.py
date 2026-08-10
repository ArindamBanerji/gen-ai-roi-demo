"""
Block 7.6 -- tests for compute_verification_health().
All tests use AsyncMock for graph_client -- no live AGE required.
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.learning_health import compute_verification_health


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _graph_mock(total=1000, verified=300,
                last_total=100, last_verified=30,
                prior_total=100, prior_verified=30,
                conservation_status="GREEN"):
    """
    Build an AsyncMock graph_client whose run_query returns realistic data.

    Query dispatch is positional -- the order in compute_verification_health:
      call 0 : total decisions
      call 1 : verified decisions
      call 2 : last-7d window
      call 3 : prior-7d window
      call 4+ : LearningHealthMonitor.evaluate() queries (patched separately)
    """
    mock = AsyncMock()
    mock.run_query.side_effect = [
        [{"total": total}],                                          # call 0
        [{"verified": verified}],                                    # call 1
        [{"total": last_total,  "verified": last_verified}],        # call 2
        [{"total": prior_total, "verified": prior_verified}],       # call 3
    ]
    return mock, conservation_status


def _run(coro):
    return asyncio.run(coro)


def _patch_conservation(status: str):
    """Patch LearningHealthMonitor.evaluate to return a fixed status."""
    return patch(
        "app.services.learning_health.LearningHealthMonitor.evaluate",
        new=AsyncMock(return_value={"status": status}),
    )


# ---------------------------------------------------------------------------
# Test 1 — GREEN when all conditions met
# ---------------------------------------------------------------------------

def test_green_when_all_conditions_met():
    mock, _ = _graph_mock(
        total=1000, verified=300,       # coverage = 0.30 >= 0.20 [OK]
        last_total=100, last_verified=30,   # last rate = 0.30
        prior_total=100, prior_verified=30, # prior rate = 0.30 -> no drift [OK]
    )
    with _patch_conservation("GREEN"):
        result = _run(compute_verification_health(mock))

    assert result["status"] == "GREEN", f"Expected GREEN, got {result['status']}"
    assert result["coverage_healthy"] is True
    assert result["drift_healthy"] is True
    assert result["conservation_healthy"] is True
    assert result["coverage_rate"] == pytest.approx(0.30, abs=0.001)


# ---------------------------------------------------------------------------
# Test 2 — AMBER when coverage is low (< 20%)
# ---------------------------------------------------------------------------

def test_amber_when_coverage_low():
    mock, _ = _graph_mock(
        total=1000, verified=100,       # coverage = 0.10 < 0.20 [FAIL]
        last_total=100, last_verified=10,
        prior_total=100, prior_verified=10,
    )
    with _patch_conservation("GREEN"):
        result = _run(compute_verification_health(mock))

    assert result["status"] == "AMBER", f"Expected AMBER, got {result['status']}"
    assert result["coverage_healthy"] is False
    assert result["coverage_rate"] == pytest.approx(0.10, abs=0.001)


# ---------------------------------------------------------------------------
# Test 3 — AMBER when drift detected (last_7d rate drops > 20%)
# ---------------------------------------------------------------------------

def test_amber_when_drift_detected():
    mock, _ = _graph_mock(
        total=1000, verified=250,       # coverage 25% [OK]
        last_total=100, last_verified=10,   # last rate = 0.10
        prior_total=100, prior_verified=30, # prior rate = 0.30 -> drop = 67% [FAIL]
    )
    with _patch_conservation("GREEN"):
        result = _run(compute_verification_health(mock))

    assert result["status"] == "AMBER", f"Expected AMBER, got {result['status']}"
    assert result["drift_healthy"] is False
    assert result["drift_rate_last_7d"] == pytest.approx(0.10, abs=0.001)
    assert result["drift_rate_prior_7d"] == pytest.approx(0.30, abs=0.001)


# ---------------------------------------------------------------------------
# Test 4 — RED when no verifications at all (coverage_rate == 0)
# ---------------------------------------------------------------------------

def test_red_when_no_verifications():
    mock, _ = _graph_mock(
        total=500, verified=0,          # coverage = 0.0
        last_total=50, last_verified=0,
        prior_total=50, prior_verified=0,
    )
    with _patch_conservation("GREEN"):
        result = _run(compute_verification_health(mock))

    assert result["status"] == "RED", f"Expected RED, got {result['status']}"
    assert result["coverage_rate"] == 0.0
    assert result["verified_decisions"] == 0


# ---------------------------------------------------------------------------
# Test 5 — RED when all 3 conditions unhealthy simultaneously
# ---------------------------------------------------------------------------

def test_status_logic_all_unhealthy_is_red():
    mock, _ = _graph_mock(
        total=1000, verified=50,        # coverage = 0.05 < 0.20 [FAIL]
        last_total=100, last_verified=2,    # last rate = 0.02
        prior_total=100, prior_verified=20, # prior rate = 0.20 -> drop = 90% [FAIL]
    )
    with _patch_conservation("RED"):    # conservation AMBER/RED [FAIL]
        result = _run(compute_verification_health(mock))

    assert result["status"] == "RED", f"Expected RED, got {result['status']}"
    assert result["coverage_healthy"] is False
    assert result["drift_healthy"] is False
    assert result["conservation_healthy"] is False


def test_calibrating_conservation_is_healthy():
    mock, _ = _graph_mock(
        total=1000, verified=300,
        last_total=100, last_verified=30,
        prior_total=100, prior_verified=30,
    )
    with _patch_conservation("CALIBRATING"):
        result = _run(compute_verification_health(mock))

    assert result["status"] == "GREEN"
    assert result["coverage_healthy"] is True
    assert result["drift_healthy"] is True
    assert result["conservation_healthy"] is True
