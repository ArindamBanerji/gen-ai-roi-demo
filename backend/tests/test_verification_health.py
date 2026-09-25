"""
Block 7.6 -- tests for compute_verification_health().
Verification coverage and windows are read from a disposable AGE graph.
"""
import asyncio
import math
import time
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.learning_health import compute_verification_health


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _verification_graph(age_graph, total=1000, verified=300,
                        last_total=100, last_verified=30,
                        prior_total=100, prior_verified=30,
                        conservation_status="GREEN"):
    scale = math.gcd(total, verified, last_total, last_verified, prior_total, prior_verified)
    now = time.time()
    for count, verified_count, age_days in [
        (last_total, last_verified, 3),
        (prior_total, prior_verified, 10),
        (total-last_total-prior_total, verified-last_verified-prior_verified, 20),
    ]:
        for index in range(count // scale):
            age_graph.decision(correct=True if index < verified_count // scale else None,
                               created_at=now-age_days*86400)
    return age_graph.client, conservation_status


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

@pytest.mark.age
def test_green_when_all_conditions_met(age_graph):
    mock, _ = _verification_graph(age_graph, 
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

@pytest.mark.age
def test_amber_when_coverage_low(age_graph):
    mock, _ = _verification_graph(age_graph, 
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

@pytest.mark.age
def test_amber_when_drift_detected(age_graph):
    mock, _ = _verification_graph(age_graph, 
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

@pytest.mark.age
def test_red_when_no_verifications(age_graph):
    mock, _ = _verification_graph(age_graph, 
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

@pytest.mark.age
def test_status_logic_all_unhealthy_is_red(age_graph):
    mock, _ = _verification_graph(age_graph, 
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


@pytest.mark.age
def test_calibrating_conservation_is_healthy(age_graph):
    mock, _ = _verification_graph(age_graph, 
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
