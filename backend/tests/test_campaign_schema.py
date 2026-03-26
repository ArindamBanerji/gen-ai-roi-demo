"""
tests/test_campaign_schema.py — F6 Campaign schema test suite.

7 tests covering pure-Python helpers: make_campaign_id, is_subsequence,
derive_severity, sliding_window_cluster, compute_confidence.

Run from backend/:
    pytest tests/test_campaign_schema.py -v
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timedelta

from app.domains.soc.campaigns import (
    make_campaign_id,
    is_subsequence,
    derive_severity,
    sliding_window_cluster,
    compute_confidence,
    CONFIDENCE_SHARED_ENTITY,
    CONFIDENCE_MULTI_RULE_BOOST,
    CONFIDENCE_MAX,
)


# ============================================================================
# Test 1 — make_campaign_id is order-independent
# ============================================================================

def test_make_campaign_id_deterministic():
    """
    UUID5 is derived from sorted alert IDs, so input order must not matter.
    Two calls with the same IDs in different order must produce the same ID.
    """
    id1 = make_campaign_id(["a", "b", "c"])
    id2 = make_campaign_id(["c", "a", "b"])

    assert id1 == id2, (
        f"make_campaign_id must be order-independent (sorts before uuid5). "
        f"Got id1={id1!r}, id2={id2!r}"
    )


# ============================================================================
# Test 2 — is_subsequence returns True when order is correct
# ============================================================================

def test_is_subsequence_true():
    """
    needle appears in order within haystack (interleaved with other items).
    """
    result = is_subsequence(
        ("credential_access", "lateral_movement"),
        ["credential_access", "cloud_infrastructure", "lateral_movement"],
    )
    assert result is True, (
        "credential_access → lateral_movement is a valid subsequence of "
        "['credential_access', 'cloud_infrastructure', 'lateral_movement']. "
        f"Got: {result}"
    )


# ============================================================================
# Test 3 — is_subsequence returns False when order is wrong
# ============================================================================

def test_is_subsequence_false():
    """
    needle in wrong order must return False even if both elements are present.
    """
    result = is_subsequence(
        ("lateral_movement", "credential_access"),   # reversed
        ["credential_access", "lateral_movement"],
    )
    assert result is False, (
        "lateral_movement → credential_access is NOT a valid subsequence of "
        "['credential_access', 'lateral_movement'] (wrong order). "
        f"Got: {result}"
    )


# ============================================================================
# Test 4 — derive_severity: HIGH dominates
# ============================================================================

def test_derive_severity_high():
    """Any HIGH or CRITICAL in the list must yield 'HIGH'."""
    result = derive_severity(["LOW", "HIGH", "MEDIUM"])
    assert result == "HIGH", (
        f"derive_severity(['LOW', 'HIGH', 'MEDIUM']) must be 'HIGH'. Got: {result!r}"
    )


# ============================================================================
# Test 5 — derive_severity: MEDIUM when no HIGH/CRITICAL
# ============================================================================

def test_derive_severity_medium():
    """MEDIUM wins when no HIGH/CRITICAL present."""
    result = derive_severity(["LOW", "MEDIUM"])
    assert result == "MEDIUM", (
        f"derive_severity(['LOW', 'MEDIUM']) must be 'MEDIUM'. Got: {result!r}"
    )


# ============================================================================
# Test 6 — sliding_window_cluster groups by time proximity
# ============================================================================

def test_sliding_window_cluster_splits_correctly():
    """
    window_seconds=3600 (1 hour).
    Gaps: a1→a2 = 30min, a2→a3 = 60min, a3→a4 = 10min.
    All gaps <= 3600s → all alerts in one cluster.
    """
    now = datetime(2026, 3, 25, 10, 0, 0)
    alerts = [
        {"ts": now,                           "alert_id": "a1"},
        {"ts": now + timedelta(minutes=30),   "alert_id": "a2"},
        {"ts": now + timedelta(minutes=90),   "alert_id": "a3"},  # 60min from a2 = 3600s
        {"ts": now + timedelta(minutes=100),  "alert_id": "a4"},
    ]
    clusters = sliding_window_cluster(alerts, window_seconds=3600)

    assert len(clusters) == 1, (
        f"All gaps <= 3600s — expected 1 cluster, got {len(clusters)}. "
        f"Cluster sizes: {[len(c) for c in clusters]}"
    )


# ============================================================================
# Test 7 — compute_confidence multi-rule boost and cap
# ============================================================================

def test_compute_confidence_multi_rule_boost():
    """
    Multi-rule boost adds CONFIDENCE_MULTI_RULE_BOOST (0.10) to the base.
    Must be capped at CONFIDENCE_MAX (0.95) — technique_sequence with
    additional rules must not exceed 0.95.
    """
    base = compute_confidence("shared_entity")
    boosted = compute_confidence("shared_entity", additional_rules=["temporal"])

    assert boosted == base + CONFIDENCE_MULTI_RULE_BOOST, (
        f"Expected boosted = {base} + {CONFIDENCE_MULTI_RULE_BOOST} = "
        f"{base + CONFIDENCE_MULTI_RULE_BOOST}. Got: {boosted}"
    )

    capped = compute_confidence("technique_sequence", ["shared_entity", "temporal"])
    assert capped <= CONFIDENCE_MAX, (
        f"compute_confidence must cap at {CONFIDENCE_MAX}. Got: {capped}"
    )
