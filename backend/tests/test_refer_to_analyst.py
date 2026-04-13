"""
Tests for refer_to_analyst activation policy (v5.5).

Coverage:
  - should_refer_to_analyst: 9 tests (conditions 1-4, combinations)
  - get_fallback_action: 2 tests
  - Config integration: 1 test (SOC_ACTIONS shape, refer index)
"""

import numpy as np
import pytest

from app.services.referral_policy import (
    CONFIDENCE_BAND_HIGH,
    CONFIDENCE_BAND_LOW,
    MARGIN_THRESHOLD,
    REFER_ACTION_INDEX,
    get_fallback_action,
    should_refer_to_analyst,
)
from app.domains.soc.config import SOC_ACTIONS, SOC_PROFILE_CENTROIDS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _probs(refer=0.30, escalate=0.25, investigate=0.20, suppress=0.15, monitor=0.10):
    """Build a 5-element probability array in SOC_ACTIONS order."""
    arr = np.array([escalate, investigate, suppress, monitor, refer], dtype=np.float64)
    return arr / arr.sum()  # renormalize so sum = 1.0


def _factors(**kwargs):
    """Build a 6-element factor vector with all zeros unless overridden.
    Order: travel_match, asset_criticality, threat_intel_enrichment,
           pattern_history, time_anomaly, device_trust
    """
    defaults = dict(
        travel_match=0.0,
        asset_criticality=0.0,
        threat_intel_enrichment=0.0,
        pattern_history=0.0,
        time_anomaly=0.0,
        device_trust=0.5,
    )
    defaults.update(kwargs)
    return np.array(list(defaults.values()), dtype=np.float64)


# ---------------------------------------------------------------------------
# Test 1: should_refer — baseline "all gates pass" → True
# ---------------------------------------------------------------------------

def test_refer_all_conditions_pass():
    """Baseline: refer wins, confidence in band, narrow margin, no override → True."""
    probs = _probs(refer=0.32, escalate=0.25, investigate=0.20, suppress=0.13, monitor=0.10)
    conf = 0.50
    factors = _factors()
    assert should_refer_to_analyst(probs, conf, REFER_ACTION_INDEX, "credential_access", factors) is True


# ---------------------------------------------------------------------------
# Test 2: Condition 1 — refer is not top-1 and prob < 0.15 → False
# ---------------------------------------------------------------------------

def test_refer_blocked_condition1_low_prob():
    """refer_to_analyst is not winning and its probability is < 0.15 → False."""
    probs = np.array([0.55, 0.25, 0.10, 0.06, 0.04], dtype=np.float64)
    conf = 0.50
    factors = _factors()
    result = should_refer_to_analyst(probs, conf, 0, "credential_access", factors)
    assert result is False


# ---------------------------------------------------------------------------
# Test 3: Condition 2 — confidence too high (≥ 0.70) → False
# ---------------------------------------------------------------------------

def test_refer_blocked_confidence_too_high():
    probs = _probs(refer=0.40, escalate=0.30, investigate=0.15, suppress=0.10, monitor=0.05)
    conf = 0.75  # above CONFIDENCE_BAND_HIGH
    factors = _factors()
    assert should_refer_to_analyst(probs, conf, REFER_ACTION_INDEX, "lateral_movement", factors) is False


# ---------------------------------------------------------------------------
# Test 4: Condition 2 — confidence too low (< 0.30) → False
# ---------------------------------------------------------------------------

def test_refer_blocked_confidence_too_low():
    probs = _probs(refer=0.35, escalate=0.25, investigate=0.20, suppress=0.12, monitor=0.08)
    conf = 0.20  # below CONFIDENCE_BAND_LOW
    factors = _factors()
    assert should_refer_to_analyst(probs, conf, REFER_ACTION_INDEX, "data_exfiltration", factors) is False


# ---------------------------------------------------------------------------
# Test 5: Condition 3 — top-2 margin too large → False
# ---------------------------------------------------------------------------

def test_refer_blocked_large_margin():
    """refer wins but a wide gap exists between top-2 → False."""
    probs = np.array([0.05, 0.05, 0.05, 0.05, 0.80], dtype=np.float64)
    conf = 0.50
    factors = _factors()
    assert should_refer_to_analyst(probs, conf, REFER_ACTION_INDEX, "credential_access", factors) is False


# ---------------------------------------------------------------------------
# Test 6: Condition 4 — malware_execution single-factor override → False
# ---------------------------------------------------------------------------

def test_refer_blocked_threat_intel_override():
    """threat_intel_enrichment > 0.50 → override fires → False."""
    probs = _probs(refer=0.32, escalate=0.25, investigate=0.20, suppress=0.13, monitor=0.10)
    conf = 0.50
    factors = _factors(threat_intel_enrichment=0.60)  # above threshold 0.50
    assert should_refer_to_analyst(probs, conf, REFER_ACTION_INDEX, "malware_execution", factors) is False


# ---------------------------------------------------------------------------
# Test 7: Condition 4 — malware_execution, enrichment BELOW threshold → not blocked
# ---------------------------------------------------------------------------

def test_refer_allowed_threat_intel_below_threshold():
    """threat_intel_enrichment < 0.50 → override does NOT fire → True."""
    probs = _probs(refer=0.32, escalate=0.25, investigate=0.20, suppress=0.13, monitor=0.10)
    conf = 0.50
    factors = _factors(threat_intel_enrichment=0.40)  # below threshold 0.50
    assert should_refer_to_analyst(probs, conf, REFER_ACTION_INDEX, "malware_execution", factors) is True


# ---------------------------------------------------------------------------
# Test 8: Condition 4 — data_exfiltration AND override, both conditions met → False
# ---------------------------------------------------------------------------

def test_refer_blocked_data_exfil_and_override():
    """asset_criticality > 0.70 AND time_anomaly > 0.60 → AND override fires → False."""
    probs = _probs(refer=0.32, escalate=0.25, investigate=0.20, suppress=0.13, monitor=0.10)
    conf = 0.50
    factors = _factors(asset_criticality=0.80, time_anomaly=0.65)
    assert should_refer_to_analyst(probs, conf, REFER_ACTION_INDEX, "data_exfiltration", factors) is False


# ---------------------------------------------------------------------------
# Test 9: Condition 4 — data_exfiltration AND override, only ONE condition met → allowed
# ---------------------------------------------------------------------------

def test_refer_allowed_data_exfil_partial_override():
    """asset_criticality > 0.70 but time_anomaly < 0.60 → AND not fully satisfied → True."""
    probs = _probs(refer=0.32, escalate=0.25, investigate=0.20, suppress=0.13, monitor=0.10)
    conf = 0.50
    factors = _factors(asset_criticality=0.80, time_anomaly=0.40)  # time_anomaly below threshold
    assert should_refer_to_analyst(probs, conf, REFER_ACTION_INDEX, "data_exfiltration", factors) is True


# ---------------------------------------------------------------------------
# Test 10: get_fallback_action — returns highest non-refer index
# ---------------------------------------------------------------------------

def test_get_fallback_returns_best_non_refer():
    """escalate (index 0) has highest probability → fallback = 0."""
    probs = np.array([0.40, 0.25, 0.15, 0.10, 0.10], dtype=np.float64)
    assert get_fallback_action(probs) == 0


# ---------------------------------------------------------------------------
# Test 11: get_fallback_action — refer index excluded even if prob was highest
# ---------------------------------------------------------------------------

def test_get_fallback_excludes_refer_index():
    """refer (index 4) has highest probability; fallback should skip it → investigate (1)."""
    probs = np.array([0.15, 0.30, 0.20, 0.10, 0.25], dtype=np.float64)
    fb = get_fallback_action(probs)
    assert fb != REFER_ACTION_INDEX
    assert fb == 1  # investigate has next highest at 0.30


# ---------------------------------------------------------------------------
# Test 12: Config — SOC_ACTIONS has 5 elements and refer is at index 4
# ---------------------------------------------------------------------------

def test_config_soc_actions_shape():
    """SOC_ACTIONS must be length 5 with refer_to_analyst at index 4."""
    assert len(SOC_ACTIONS) == 5, f"Expected 5 actions, got {len(SOC_ACTIONS)}"
    assert SOC_ACTIONS[4] == "refer_to_analyst"
    # Tensor must be (6, 4, 6) — SCORER_ACTIONS only, refer_to_analyst excluded
    tensor = np.array(SOC_PROFILE_CENTROIDS)
    assert tensor.shape == (6, 4, 6), f"Expected (6,4,6), got {tensor.shape}"
