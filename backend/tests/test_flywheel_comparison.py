"""
tests/test_flywheel_comparison.py -- W2 Flywheel Demo Moment (Feature 3) test suite.

4 tests validating cold-start suppression, Day-1 snapshot invariants,
delta computation, and edge-threshold guard.

Run from backend/:
    pytest tests/test_flywheel_comparison.py -v
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.flywheel_comparison import build_flywheel_comparison, FALLBACK_FACTOR_4, MIN_EDGES_TO_SHOW


# ============================================================================
# Test 1 — suppressed when edge count is zero (cold-start)
# ============================================================================

def test_fallback_factor_4_when_no_edges():
    """
    With current_edges=0 (below MIN_EDGES_TO_SHOW=10), the panel must be
    suppressed. cold-start guard prevents misleading Day-1 comparisons.
    """
    result = build_flywheel_comparison(
        current_edges=0, current_factor_4=0.40,
        current_confidence=0.71, current_action="investigate",
        current_provenance="...", category="credential_access"
    )

    assert result["flywheel_active"] == False, (
        f"Expected flywheel_active=False with 0 edges. Got: {result}"
    )
    assert result["reason"] == "cold_start", (
        f"Expected reason='cold_start'. Got: {result.get('reason')!r}"
    )


# ============================================================================
# Test 2 — Day-1 snapshot always shows FALLBACK_FACTOR_4 = 0.40
# ============================================================================

def test_day1_snapshot_shows_fallback():
    """
    When edges are present (847 >> threshold), day_1_snapshot must always
    reflect the fallback state: factor_4_value=0.40, triggered_evolution_edges=0.
    These values are invariant -- they represent the pre-W2 baseline.
    """
    result = build_flywheel_comparison(
        current_edges=847, current_factor_4=0.82,
        current_confidence=0.89, current_action="suppress",
        current_provenance="847 verified decisions.", category="credential_access"
    )

    assert result["flywheel_active"] == True, (
        f"847 edges >> MIN_EDGES_TO_SHOW ({MIN_EDGES_TO_SHOW}). flywheel_active must be True."
    )
    assert result["day_1_snapshot"]["factor_4_value"] == FALLBACK_FACTOR_4, (
        f"day_1_snapshot factor_4_value must always be {FALLBACK_FACTOR_4}. "
        f"Got: {result['day_1_snapshot']['factor_4_value']}"
    )
    assert result["day_1_snapshot"]["triggered_evolution_edges"] == 0, (
        f"day_1_snapshot must show 0 edges (pre-W2 baseline). "
        f"Got: {result['day_1_snapshot']['triggered_evolution_edges']}"
    )


# ============================================================================
# Test 3 — action_changed=True and edge_count_gain correct
# ============================================================================

def test_action_changed_true_when_edges_exist():
    """
    When current_action is set (i.e., edges exist and W2 path ran),
    action_changed must be True and edge_count_gain must equal current_edges.
    """
    result = build_flywheel_comparison(
        current_edges=50, current_factor_4=0.75,
        current_confidence=0.85, current_action="suppress",
        current_provenance="50 verified decisions.", category="lateral_movement"
    )

    assert result["delta"]["action_changed"] is True, (
        f"action_changed must be True when current_action is set. "
        f"Got: {result['delta']['action_changed']}"
    )
    assert result["delta"]["edge_count_gain"] == 50, (
        f"edge_count_gain must equal current_edges=50. "
        f"Got: {result['delta']['edge_count_gain']}"
    )


# ============================================================================
# Test 4 — suppressed when edges below MIN_EDGES_TO_SHOW (9 < 10)
# ============================================================================

def test_panel_suppressed_when_edges_below_threshold():
    """
    With current_edges=9 (below MIN_EDGES_TO_SHOW=10), the panel must be
    suppressed. This boundary test confirms the guard fires at exactly
    the threshold (9 < 10 -> suppressed; 10 >= 10 -> not suppressed).
    """
    result = build_flywheel_comparison(
        current_edges=9, current_factor_4=0.55,
        current_confidence=0.72, current_action="investigate",
        current_provenance="...", category="credential_access"
    )

    assert result["flywheel_active"] == False, (
        f"9 < MIN_EDGES_TO_SHOW ({MIN_EDGES_TO_SHOW}) -- flywheel_active must be False. "
        f"Got: {result}"
    )


# ============================================================================
# Test 5 — field name contract (frontend depends on this exact key)
# ============================================================================

def test_flywheel_active_field_name_contract():
    """Field name contract -- frontend depends on this exact key."""
    result_suppressed = build_flywheel_comparison(
        current_edges=5, current_factor_4=0.40,
        current_confidence=0.71, current_action="investigate",
        current_provenance="...", category="credential_access"
    )
    result_active = build_flywheel_comparison(
        current_edges=50, current_factor_4=0.75,
        current_confidence=0.85, current_action="suppress",
        current_provenance="50 verified decisions.", category="lateral_movement"
    )

    assert "flywheel_active" in result_suppressed
    assert result_suppressed["flywheel_active"] == False
    assert "flywheel_active" in result_active
    assert result_active["flywheel_active"] == True
    assert "suppressed" not in result_suppressed, "old 'suppressed' key must be gone"
