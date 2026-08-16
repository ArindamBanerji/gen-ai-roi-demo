"""
EVAL-1-SOC: Ground-truth evaluation scenario validation tests.

Verifies that app/data/soc_eval_scenarios.json is well-formed, internally
consistent, and aligned with the SOC domain config.

Run from backend/:
    pytest tests/test_eval1_soc.py -v
"""

import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_SCENARIOS_PATH = Path("app/data/soc_eval_scenarios.json")


def _load():
    return json.loads(_SCENARIOS_PATH.read_text())


# ============================================================================
# TEST 1 — Scenarios file exists
# ============================================================================

def test_scenarios_file_exists():
    """app/data/soc_eval_scenarios.json must exist."""
    assert _SCENARIOS_PATH.exists(), (
        f"Scenarios file not found at {_SCENARIOS_PATH}"
    )


# ============================================================================
# TEST 2 — Correct scenario count
# ============================================================================

def test_scenarios_count():
    """JSON must contain exactly 36 scenarios (6 per category x 6 categories)."""
    scenarios = _load()
    assert len(scenarios) == 36, (
        f"Expected 36 scenarios, got {len(scenarios)}"
    )


# ============================================================================
# TEST 3 — All categories represented
# ============================================================================

def test_all_categories_represented():
    """Every SOC_CATEGORIES entry must appear at least once."""
    from app.domains.soc.config import SOC_CATEGORIES
    scenarios = _load()
    categories = {s["category"] for s in scenarios}
    for cat in SOC_CATEGORIES:
        assert cat in categories, (
            f"Category {cat!r} not found in scenarios. "
            f"Present categories: {sorted(categories)}"
        )


# ============================================================================
# TEST 4 — All 6 factors present and in [0.0, 1.0]
# ============================================================================

def test_all_factors_present():
    """Every scenario must have all 6 factors with values in [0.0, 1.0]."""
    FACTOR_NAMES = [
        # quarantined: travel_match_v1 — changes with scenario migration.
        "travel_match", "asset_criticality", "threat_intel_enrichment",
        "pattern_history", "time_anomaly", "device_trust",
    ]
    scenarios = _load()
    for s in scenarios:
        for f in FACTOR_NAMES:
            assert f in s["factors"], (
                f"Missing factor {f!r} in {s['scenario_id']}"
            )
            v = s["factors"][f]
            assert 0.0 <= v <= 1.0, (
                f"{s['scenario_id']}: factor {f!r} value {v} not in [0.0, 1.0]"
            )


# ============================================================================
# TEST 5 — All expected_action values are valid SOC actions
# ============================================================================

def test_valid_actions():
    """expected_action must be one of SOC_ACTIONS."""
    from app.domains.soc.config import SOC_ACTIONS
    scenarios = _load()
    for s in scenarios:
        assert s["expected_action"] in SOC_ACTIONS, (
            f"{s['scenario_id']}: expected_action {s['expected_action']!r} "
            f"not in SOC_ACTIONS {SOC_ACTIONS}"
        )


# ============================================================================
# TEST 6 — expected_action_index matches expected_action
# ============================================================================

def test_action_indices_match_actions():
    """expected_action_index must equal SOC_ACTIONS.index(expected_action)."""
    from app.domains.soc.config import SOC_ACTIONS
    scenarios = _load()
    for s in scenarios:
        expected_idx = SOC_ACTIONS.index(s["expected_action"])
        assert s["expected_action_index"] == expected_idx, (
            f"{s['scenario_id']}: expected_action_index {s['expected_action_index']} "
            f"does not match SOC_ACTIONS.index({s['expected_action']!r}) = {expected_idx}"
        )


# ============================================================================
# TEST 7 — category_index matches category
# ============================================================================

def test_category_indices_match_categories():
    """category_index must equal SOC_CATEGORIES.index(category)."""
    from app.domains.soc.config import SOC_CATEGORIES
    scenarios = _load()
    for s in scenarios:
        expected_idx = SOC_CATEGORIES.index(s["category"])
        assert s["category_index"] == expected_idx, (
            f"{s['scenario_id']}: category_index {s['category_index']} "
            f"does not match SOC_CATEGORIES.index({s['category']!r}) = {expected_idx}"
        )


# ============================================================================
# TEST 8 — credential_access suppress never high confidence
# ============================================================================

def test_credential_access_no_high_suppress():
    """credential_access suppress scenarios must not have confidence_tier='high'."""
    scenarios = _load()
    ca_suppress = [
        s for s in scenarios
        if s["category"] == "credential_access" and s["expected_action"] == "suppress"
    ]
    assert len(ca_suppress) > 0, (
        "No credential_access suppress scenarios found -- check scenario design"
    )
    for s in ca_suppress:
        assert s["confidence_tier"] != "high", (
            f"{s['scenario_id']}: credential_access suppress must not be "
            f"high confidence (Finding II)"
        )
