"""
tests/test_ols_status.py -- OLS Dashboard (L-09) test suite.

5 tests validating OLSMonitor integration, warm-start guard,
ACM qualification, delta_pct arithmetic, and endpoint contract.

Run from backend/:
    pytest tests/test_ols_status.py -v
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient

from app.services.ols_status import get_ols_status
from app.main import app

client = TestClient(app)


# ============================================================================
# Test 1 — warm_start_active=True returns warming_up immediately
# ============================================================================

def test_warm_start_blocks_monitoring():
    """
    When warm_start_active=True, get_ols_status must return status="warming_up"
    regardless of ols_history length.  OLSMonitor must NOT run.
    """
    # Feed a full plateau's worth of history — still blocked by warm_start
    ols_history = [1.2] * 30
    result = get_ols_status(
        ols_history=ols_history,
        warm_start_active=True,
        analyst_overrides={"analyst_A": 50},
    )

    assert result["status"] == "warming_up", (
        f"warm_start_active=True must yield status='warming_up'. Got: {result['status']}"
    )
    assert result["baseline_ols"] is None, (
        "baseline_ols must be None during warm-start (no baseline computed)."
    )
    assert result["alarm"] is False, (
        "alarm must be False during warm-start."
    )


# ============================================================================
# Test 2 — fewer than 2 observations returns warming_up
# ============================================================================

def test_insufficient_history_returns_warming_up():
    """
    With len(ols_history) < 2, monitoring cannot proceed.
    Status must be 'warming_up' and delta_pct must be None.
    """
    result = get_ols_status(
        ols_history=[1.3],
        warm_start_active=False,
        analyst_overrides={},
    )

    assert result["status"] == "warming_up", (
        f"Single OLS value must yield status='warming_up'. Got: {result['status']}"
    )
    assert result["delta_pct"] is None, (
        "delta_pct must be None when baseline not yet frozen."
    )
    assert result["current_ols"] == pytest.approx(1.3, abs=0.001), (
        f"current_ols must reflect the only history value. Got: {result['current_ols']}"
    )


# ============================================================================
# Test 3 — plateau reached → status=monitoring, baseline_frozen=True
# ============================================================================

def test_plateau_reached_monitoring_status():
    """
    After feeding 25 identical OLS values (variance=0 < plateau_threshold=0.02),
    OLSMonitor freezes the baseline.  Status must be 'monitoring' and
    baseline_frozen must be True.
    """
    ols_history = [1.25] * 25

    result = get_ols_status(
        ols_history=ols_history,
        warm_start_active=False,
        analyst_overrides={},
    )

    assert result["baseline_frozen"] is True, (
        "25 identical OLS values must trigger plateau detection. "
        f"baseline_frozen={result['baseline_frozen']}, baseline_ols={result['baseline_ols']}"
    )
    assert result["status"] == "monitoring", (
        f"Expected 'monitoring' after plateau. Got: {result['status']}"
    )
    assert result["baseline_ols"] == pytest.approx(1.25, abs=0.01), (
        f"baseline_ols should ~= 1.25 (mean of flat history). Got: {result['baseline_ols']}"
    )


# ============================================================================
# Test 4 — ACM activates only above qualification_threshold
# ============================================================================

def test_acm_qualification_threshold():
    """
    ACM (Analyst Competency Metric) must be inactive when no analyst has
    reached qualification_threshold overrides, and active when at least one has.
    """
    ols_history = [1.2] * 5  # short -- status=warming_up, but ACM still computed

    # Below threshold: analyst A has 19 overrides, threshold=20
    result_below = get_ols_status(
        ols_history=ols_history,
        warm_start_active=False,
        analyst_overrides={"analyst_A": 19, "analyst_B": 10},
        qualification_threshold=20,
    )
    assert result_below["acm_active"] is False, (
        f"ACM must be inactive when no analyst reaches threshold. "
        f"qualified={result_below['qualified_analysts']}"
    )
    assert result_below["qualified_analysts"] == 0, (
        f"Expected 0 qualified analysts. Got: {result_below['qualified_analysts']}"
    )

    # At threshold: analyst A now has exactly 20 overrides
    result_at = get_ols_status(
        ols_history=ols_history,
        warm_start_active=False,
        analyst_overrides={"analyst_A": 20, "analyst_B": 10},
        qualification_threshold=20,
    )
    assert result_at["acm_active"] is True, (
        f"ACM must activate when analyst reaches threshold (20 >= 20). "
        f"qualified={result_at['qualified_analysts']}"
    )
    assert result_at["qualified_analysts"] == 1, (
        f"Expected 1 qualified analyst. Got: {result_at['qualified_analysts']}"
    )


# ============================================================================
# Test 5 — GET /api/soc/ols-status returns required keys
# ============================================================================

def test_api_ols_status_returns_required_keys():
    """
    The endpoint must return HTTP 200 with all required keys.
    With an empty Neo4j (no decisions), it should return warming_up status.
    """
    response = client.get("/api/soc/ols-status")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:300]}"
    )
    body = response.json()

    required_keys = {
        "status", "baseline_ols", "current_ols", "delta_pct",
        "cusum", "alarm", "baseline_frozen", "qualified_analysts",
        "acm_active", "message",
    }
    missing = required_keys - set(body.keys())
    assert not missing, f"Response missing keys: {missing}. Got: {list(body.keys())}"

    # Status must be one of the three valid values
    assert body["status"] in ("warming_up", "monitoring", "alarm"), (
        f"Invalid status value: {body['status']!r}"
    )
    # alarm must be bool
    assert isinstance(body["alarm"], bool), (
        f"alarm must be bool. Got: {type(body['alarm'])}"
    )
