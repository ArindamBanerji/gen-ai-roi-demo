"""
tests/test_campaign_engine.py -- F6 CampaignCorrelationEngine test suite.

8 tests covering Phase 1 campaign identity authority: category/entity/bucket
separation, no no-entity campaigns, no-false-positive guard, de-duplication,
and stable deterministic identity.

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
# Test 1 — Phase 1 defers cross-category kill-chain campaigns
# ============================================================================

def test_phase1_defers_two_stage_cross_category_kill_chain():
    """
    Phase 1 L1 campaigns are bounded by category as part of stable identity.
    Cross-category attack-chain semantics are deferred to Level 2 / Phase 4.
    """
    events = [
        make_event("a1", "credential_access", 0,   source_entity_id="ip-1"),
        make_event("a2", "lateral_movement",  120, source_entity_id="ip-1"),
    ]
    engine = CampaignCorrelationEngine(DEFAULT_CONFIG)
    campaigns = engine.correlate(events)

    assert campaigns == []


# ============================================================================
# Test 2 — Phase 1 does not create L1 multi-category attack chains
# ============================================================================

def test_phase1_defers_three_stage_cross_category_kill_chain():
    """
    Same-entity, multi-category chains must not be merged into one L1 Campaign.
    CONTINUES/AttackChain-style continuity is later-phase work.
    """
    events = [
        make_event("a1", "credential_access", 0,   source_entity_id="ip-1"),
        make_event("a2", "lateral_movement",  60,  source_entity_id="ip-1"),
        make_event("a3", "data_exfiltration", 240, source_entity_id="ip-1"),
    ]
    engine = CampaignCorrelationEngine(DEFAULT_CONFIG)
    campaigns = engine.correlate(events)

    assert campaigns == []


# ============================================================================
# Test 3 — Rule 1: shared_entity groups two alerts on same entity
# ============================================================================

def test_rule1_shared_entity_groups_alerts():
    """
    Two same-category alerts on the same entity produce one Phase 1 L1 campaign.
    MEMBER_OF is the canonical live edge for this materialized campaign.
    """
    events = [
        make_event("a1", "credential_access", 0,  source_entity_id="user-x"),
        make_event("a2", "credential_access", 30, source_entity_id="user-x"),
    ]
    engine = CampaignCorrelationEngine(DEFAULT_CONFIG)
    campaigns = engine.correlate(events)

    assert len(campaigns) == 1, (
        f"Expected 1 campaign for 2 alerts on same entity. Got {len(campaigns)}"
    )
    assert campaigns[0].trigger_rule in ("technique_sequence", "shared_entity", "temporal"), (
        f"Unexpected trigger_rule: {campaigns[0].trigger_rule!r}"
    )
    assert campaigns[0].derived_entity_key == "entity:user-x", (
        f"Expected type-prefixed derived entity. Got: {campaigns[0].derived_entity_key}"
    )
    assert campaigns[0].category == "credential_access"


# ============================================================================
# Test 4 — Phase 1 skips no-entity temporal clusters
# ============================================================================

def test_rule3_temporal_clusters_same_category():
    """
    Phase 1 requires a derived entity key. No-entity temporal clusters are not
    materialized as Campaign nodes.
    """
    events = [
        make_event("a1", "credential_access", 0,  source_entity_id=None),
        make_event("a2", "credential_access", 20, source_entity_id=None),
        make_event("a3", "credential_access", 40, source_entity_id=None),
    ]
    engine = CampaignCorrelationEngine(DEFAULT_CONFIG)
    campaigns = engine.correlate(events)

    assert campaigns == []


# ============================================================================
# Test 5 — No false campaign for unrelated alerts
# ============================================================================

def test_no_false_campaign_for_unrelated_alerts():
    """
    3 alerts on 3 different entities, no sequence, no temporal proximity
    (different categories) -> no campaign should be produced.
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
        f"Duplicate alert_ids across campaigns -- each alert must belong to at most one. "
        f"All IDs: {all_member_ids}"
    )


# ============================================================================
# Test 7 — Campaign ID is deterministic across runs
# ============================================================================

def test_campaign_id_deterministic():
    """
    Running correlate() twice on the same Phase 1 identity tuple must produce
    identical campaign_ids. Identity is stable tuple-derived, not member-set
    derived, so the ID remains stable as members grow.
    """
    events = [
        make_event("a1", "credential_access", 0,  source_entity_id="ip-1"),
        make_event("a2", "credential_access", 60, source_entity_id="ip-1"),
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
    grown_campaign = engine.correlate(events + [
        make_event("a3", "credential_access", 90, source_entity_id="ip-1"),
    ])[0]
    assert grown_campaign.campaign_id == campaigns1[0].campaign_id


# ============================================================================
# Test 8 — No-entity temporal windows do not create Phase 1 campaigns
# ============================================================================

def test_temporal_window_respects_config():
    """
    Temporal clustering alone is not enough in Phase 1. Without a derived
    entity key, even close same-category alerts are left unmaterialized.
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

    assert campaigns == []
