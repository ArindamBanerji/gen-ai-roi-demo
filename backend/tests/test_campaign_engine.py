"""
tests/test_campaign_engine.py — F6 CampaignCorrelationEngine test suite.

8 tests covering rule priority, kill-chain detection, shared-entity grouping,
temporal clustering, no-false-positive guard, de-duplication, and determinism.

Run from backend/:
    pytest tests/test_campaign_engine.py -v
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timedelta

from app.domains.soc.campaigns import CampaignCorrelationEngine


# ── helpers ──────────────────────────────────────────────────────────────────

def make_event(alert_id, category, ts_offset_min=0,
               source_entity_id=None, technique_id=None, severity="MEDIUM"):
    return {
        "alert_id": alert_id,
        "category": category,
        "ts": datetime(2026, 3, 25, 10, 0) + timedelta(minutes=ts_offset_min),
        "source_entity_id": source_entity_id,
        "technique_id": technique_id,
        "severity": severity,
    }


DEFAULT_CONFIG = {
    "correlation_window_hours": 24,
    "temporal_window_minutes": 60,
    "min_alerts_for_campaign": 2,
    "max_campaign_age_days": 30,
}


# ============================================================================
# Test 1 — Rule 2: technique_sequence detects 2-stage kill chain
# ============================================================================

def test_rule2_technique_sequence_detects_kill_chain():
    """
    credential_access → lateral_movement on the same entity matches
    'credential_then_lateral'. trigger_rule must be 'technique_sequence'
    and confidence must be 0.85.
    """
    events = [
        make_event("a1", "credential_access", 0,   source_entity_id="ip-1"),
        make_event("a2", "lateral_movement",  120, source_entity_id="ip-1"),
    ]
    engine = CampaignCorrelationEngine(DEFAULT_CONFIG)
    campaigns = engine.correlate(events)

    assert len(campaigns) == 1, (
        f"Expected 1 campaign for 2-stage kill chain. Got {len(campaigns)}"
    )
    assert campaigns[0].trigger_rule == "technique_sequence", (
        f"Expected trigger_rule='technique_sequence'. Got: {campaigns[0].trigger_rule!r}"
    )
    assert campaigns[0].confidence == 0.85, (
        f"Expected confidence=0.85. Got: {campaigns[0].confidence}"
    )


# ============================================================================
# Test 2 — Rule 2: three-stage kill chain (credential → lateral → exfil)
# ============================================================================

def test_rule2_three_stage_kill_chain():
    """
    credential_access → lateral_movement → data_exfiltration matches
    'credential_then_lateral_then_exfil'. Both endpoints must appear in
    category_sequence.
    """
    events = [
        make_event("a1", "credential_access", 0,   source_entity_id="ip-1"),
        make_event("a2", "lateral_movement",  60,  source_entity_id="ip-1"),
        make_event("a3", "data_exfiltration", 240, source_entity_id="ip-1"),
    ]
    engine = CampaignCorrelationEngine(DEFAULT_CONFIG)
    campaigns = engine.correlate(events)

    assert len(campaigns) == 1, (
        f"Expected 1 campaign for 3-stage kill chain. Got {len(campaigns)}"
    )
    assert "credential_access" in campaigns[0].category_sequence, (
        f"category_sequence must include 'credential_access'. "
        f"Got: {campaigns[0].category_sequence}"
    )
    assert "data_exfiltration" in campaigns[0].category_sequence, (
        f"category_sequence must include 'data_exfiltration'. "
        f"Got: {campaigns[0].category_sequence}"
    )


# ============================================================================
# Test 3 — Rule 1: shared_entity groups two alerts on same entity
# ============================================================================

def test_rule1_shared_entity_groups_alerts():
    """
    Two alerts on the same entity (user-x) with no kill-chain match.
    Must produce 1 campaign with user-x in shared_entities.
    trigger_rule may be technique_sequence (if chain matched) or shared_entity.
    """
    events = [
        make_event("a1", "credential_access",    0,  source_entity_id="user-x"),
        make_event("a2", "cloud_infrastructure", 30, source_entity_id="user-x"),
    ]
    engine = CampaignCorrelationEngine(DEFAULT_CONFIG)
    campaigns = engine.correlate(events)

    assert len(campaigns) == 1, (
        f"Expected 1 campaign for 2 alerts on same entity. Got {len(campaigns)}"
    )
    assert campaigns[0].trigger_rule in ("technique_sequence", "shared_entity"), (
        f"Unexpected trigger_rule: {campaigns[0].trigger_rule!r}"
    )
    assert "user-x" in campaigns[0].shared_entities, (
        f"shared_entities must contain 'user-x'. Got: {campaigns[0].shared_entities}"
    )


# ============================================================================
# Test 4 — Rule 3: temporal clusters same-category alerts
# ============================================================================

def test_rule3_temporal_clusters_same_category():
    """
    3 credential_access alerts with no entity — falls through to temporal rule.
    All within 60-minute window → 1 cluster → 1 campaign.
    trigger_rule must be 'temporal', confidence must be 0.45.
    """
    events = [
        make_event("a1", "credential_access", 0,  source_entity_id=None),
        make_event("a2", "credential_access", 20, source_entity_id=None),
        make_event("a3", "credential_access", 40, source_entity_id=None),
    ]
    engine = CampaignCorrelationEngine(DEFAULT_CONFIG)
    campaigns = engine.correlate(events)

    assert len(campaigns) == 1, (
        f"Expected 1 temporal campaign. Got {len(campaigns)}"
    )
    assert campaigns[0].trigger_rule == "temporal", (
        f"Expected trigger_rule='temporal'. Got: {campaigns[0].trigger_rule!r}"
    )
    assert campaigns[0].confidence == 0.45, (
        f"Expected confidence=0.45 for temporal rule. Got: {campaigns[0].confidence}"
    )


# ============================================================================
# Test 5 — No false campaign for unrelated alerts
# ============================================================================

def test_no_false_campaign_for_unrelated_alerts():
    """
    3 alerts on 3 different entities, no sequence, no temporal proximity
    (different categories) → no campaign should be produced.
    """
    events = [
        make_event("a1", "credential_access", 0, source_entity_id="ip-1"),
        make_event("a2", "data_exfiltration", 0, source_entity_id="ip-2"),
        make_event("a3", "malware_execution",  0, source_entity_id="ip-3"),
    ]
    engine = CampaignCorrelationEngine(DEFAULT_CONFIG)
    campaigns = engine.correlate(events)

    assert len(campaigns) == 0, (
        f"Expected 0 campaigns for unrelated alerts across different entities. "
        f"Got {len(campaigns)}: {[(c.trigger_rule, c.member_alert_ids) for c in campaigns]}"
    )


# ============================================================================
# Test 6 — Each alert in at most one campaign (no duplicates)
# ============================================================================

def test_each_alert_in_at_most_one_campaign():
    """
    A 3-stage kill chain on one entity could match multiple overlapping rules.
    The claimed-set must ensure each alert_id appears in exactly one campaign.
    """
    events = [
        make_event("a1", "credential_access", 0,   source_entity_id="ip-1"),
        make_event("a2", "lateral_movement",  60,  source_entity_id="ip-1"),
        make_event("a3", "data_exfiltration", 120, source_entity_id="ip-1"),
    ]
    engine = CampaignCorrelationEngine(DEFAULT_CONFIG)
    campaigns = engine.correlate(events)

    all_member_ids = [aid for c in campaigns for aid in c.member_alert_ids]
    assert len(all_member_ids) == len(set(all_member_ids)), (
        f"Duplicate alert_ids across campaigns — each alert must belong to at most one. "
        f"All IDs: {all_member_ids}"
    )


# ============================================================================
# Test 7 — Campaign ID is deterministic across runs
# ============================================================================

def test_campaign_id_deterministic():
    """
    Running correlate() twice on the same events must produce campaigns with
    identical campaign_ids — UUID5 from sorted alert_ids is deterministic.
    """
    events = [
        make_event("a1", "credential_access", 0,  source_entity_id="ip-1"),
        make_event("a2", "lateral_movement",  60, source_entity_id="ip-1"),
    ]
    engine = CampaignCorrelationEngine(DEFAULT_CONFIG)
    campaigns1 = engine.correlate(events)
    campaigns2 = engine.correlate(events)

    assert len(campaigns1) == 1 and len(campaigns2) == 1, (
        "Expected 1 campaign per run for determinism check."
    )
    assert campaigns1[0].campaign_id == campaigns2[0].campaign_id, (
        f"Campaign ID must be deterministic. "
        f"Run 1: {campaigns1[0].campaign_id}, Run 2: {campaigns2[0].campaign_id}"
    )


# ============================================================================
# Test 8 — Temporal window respects config (split into 2 clusters)
# ============================================================================

def test_temporal_window_respects_config():
    """
    With temporal_window_minutes=10, a 20-minute gap between pairs must
    produce 2 separate campaigns (two clusters of 2).
    """
    config = {**DEFAULT_CONFIG, "temporal_window_minutes": 10}
    events = [
        make_event("a1", "credential_access", 0,  source_entity_id=None),
        make_event("a2", "credential_access", 5,  source_entity_id=None),
        make_event("a3", "credential_access", 25, source_entity_id=None),
        make_event("a4", "credential_access", 30, source_entity_id=None),
    ]
    engine = CampaignCorrelationEngine(config)
    campaigns = engine.correlate(events)

    assert len(campaigns) == 2, (
        f"Expected 2 temporal clusters (gap=20min > window=10min). "
        f"Got {len(campaigns)}: "
        f"{[(c.member_alert_ids, c.trigger_rule) for c in campaigns]}"
    )
