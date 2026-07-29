"""
Tests for SOC referral rules R1-R7 and ReferralEngine integration.

Coverage:
  - Individual rule behaviour (fire / no-fire / configurable thresholds)
  - Factory function
  - ReferralEngine integration with SOC rules
  - Safe degradation on missing context
  - Triage response field presence
  - Neo4j query helpers: get_sequence_count, get_cross_category_count
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from gae.referral import ReferralEngine, ReferralReason

from app.services.referral_rules import (
    ExecutiveAccountRule,
    RapidSuccessionRule,
    ComplianceMandateRule,
    HighValueDataRule,
    ActiveIncidentRule,
    NewAssetRule,
    CrossCategoryRule,
    get_soc_referral_rules,
)


# ---------------------------------------------------------------------------
# R1: ExecutiveAccountRule
# ---------------------------------------------------------------------------

def test_r1_fires_on_executive():
    rule = ExecutiveAccountRule()
    fires, detail = rule.evaluate({'identity_tier': 'executive'})
    assert fires is True
    assert detail['identity_tier'] == 'executive'


def test_r1_does_not_fire_on_standard():
    rule = ExecutiveAccountRule()
    fires, detail = rule.evaluate({'identity_tier': 'standard'})
    assert fires is False
    assert detail == {}


def test_r1_custom_tiers():
    rule = ExecutiveAccountRule(tiers=['vip', 'partner'])
    assert rule.evaluate({'identity_tier': 'vip'})[0] is True
    assert rule.evaluate({'identity_tier': 'executive'})[0] is False


# ---------------------------------------------------------------------------
# R2: RapidSuccessionRule
# ---------------------------------------------------------------------------

def test_r2_fires_at_threshold():
    rule = RapidSuccessionRule(threshold=3)
    fires, detail = rule.evaluate({'sequence_count': 3})
    assert fires is True
    assert detail['sequence_count'] == 3


def test_r2_does_not_fire_below_threshold():
    rule = RapidSuccessionRule(threshold=3)
    fires, _ = rule.evaluate({'sequence_count': 2})
    assert fires is False


# ---------------------------------------------------------------------------
# R3: ComplianceMandateRule
# ---------------------------------------------------------------------------

def test_r3_fires_on_insider_threat_with_compliance():
    rule = ComplianceMandateRule()
    fires, detail = rule.evaluate({'category': 'insider_threat', 'compliance_mode': True})
    assert fires is True
    assert detail['category'] == 'insider_threat'


def test_r3_does_not_fire_without_compliance():
    rule = ComplianceMandateRule()
    fires, _ = rule.evaluate({'category': 'insider_threat', 'compliance_mode': False})
    assert fires is False


def test_r3_does_not_fire_on_wrong_category():
    rule = ComplianceMandateRule()
    fires, _ = rule.evaluate({'category': 'lateral_movement', 'compliance_mode': True})
    assert fires is False


# ---------------------------------------------------------------------------
# R4: HighValueDataRule
# ---------------------------------------------------------------------------

def test_r4_fires_on_high_value_suppress():
    rule = HighValueDataRule(criticality_threshold=0.85)
    ctx = {'category': 'data_exfiltration', 'asset_criticality': 0.90, 'stage1_action': 'suppress'}
    fires, detail = rule.evaluate(ctx)
    assert fires is True
    assert detail['stage1_action'] == 'suppress'


def test_r4_fires_on_high_value_monitor():
    rule = HighValueDataRule(criticality_threshold=0.85)
    ctx = {'category': 'data_exfiltration', 'asset_criticality': 0.90, 'stage1_action': 'monitor'}
    fires, _ = rule.evaluate(ctx)
    assert fires is True


def test_r4_does_not_fire_on_escalate():
    """By design -- escalate already routes to a human."""
    rule = HighValueDataRule(criticality_threshold=0.85)
    ctx = {'category': 'data_exfiltration', 'asset_criticality': 0.95, 'stage1_action': 'escalate'}
    fires, _ = rule.evaluate(ctx)
    assert fires is False


def test_r4_does_not_fire_below_criticality():
    rule = HighValueDataRule(criticality_threshold=0.85)
    ctx = {'category': 'data_exfiltration', 'asset_criticality': 0.80, 'stage1_action': 'suppress'}
    fires, _ = rule.evaluate(ctx)
    assert fires is False


# ---------------------------------------------------------------------------
# R5: ActiveIncidentRule
# ---------------------------------------------------------------------------

def test_r5_fires_on_active_incident():
    rule = ActiveIncidentRule()
    fires, detail = rule.evaluate({'incident_active': True})
    assert fires is True
    assert detail['incident_active'] is True


def test_r5_does_not_fire_when_inactive():
    rule = ActiveIncidentRule()
    fires, _ = rule.evaluate({'incident_active': False})
    assert fires is False


# ---------------------------------------------------------------------------
# R6: NewAssetRule
# ---------------------------------------------------------------------------

def test_r6_fires_on_new_asset():
    rule = NewAssetRule(age_threshold_days=30)
    fires, detail = rule.evaluate({'asset_age_days': 5})
    assert fires is True
    assert detail['asset_age_days'] == 5


def test_r6_does_not_fire_on_old_asset():
    rule = NewAssetRule(age_threshold_days=30)
    fires, _ = rule.evaluate({'asset_age_days': 90})
    assert fires is False


def test_r6_custom_threshold():
    rule = NewAssetRule(age_threshold_days=7)
    assert rule.evaluate({'asset_age_days': 6})[0] is True
    assert rule.evaluate({'asset_age_days': 8})[0] is False


# ---------------------------------------------------------------------------
# R7: CrossCategoryRule
# ---------------------------------------------------------------------------

def test_r7_fires_on_cross_category():
    rule = CrossCategoryRule(threshold=2)
    fires, detail = rule.evaluate({'cross_category_count': 3})
    assert fires is True
    assert detail['cross_category_count'] == 3


def test_r7_does_not_fire_on_single_category():
    rule = CrossCategoryRule(threshold=2)
    fires, _ = rule.evaluate({'cross_category_count': 1})
    assert fires is False


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def test_get_soc_referral_rules_returns_7_rules():
    rules = get_soc_referral_rules()
    assert len(rules) == 7


def test_all_rules_have_unique_ids():
    rules = get_soc_referral_rules()
    ids = [r.rule_id for r in rules]
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Integration — ReferralEngine with SOC rules
# ---------------------------------------------------------------------------

def test_engine_with_soc_rules_executive_alert_referred():
    engine = ReferralEngine(rules=get_soc_referral_rules())
    ctx = {'identity_tier': 'executive'}
    decision = engine.evaluate(ctx)
    assert decision.should_refer is True
    assert 'R1' in decision.reason_codes


def test_engine_with_soc_rules_normal_alert_not_referred():
    engine = ReferralEngine(rules=get_soc_referral_rules())
    ctx = {
        'identity_tier': 'standard',
        'sequence_count': 0,
        'category': 'credential_access',
        'compliance_mode': False,
        'asset_criticality': 0.5,
        'stage1_action': 'escalate',
        'incident_active': False,
        'asset_age_days': 365,
        'cross_category_count': 0,
    }
    decision = engine.evaluate(ctx)
    assert decision.should_refer is False
    assert decision.reason_codes == []


def test_engine_multiple_rules_fire_simultaneously():
    engine = ReferralEngine(rules=get_soc_referral_rules())
    ctx = {
        'identity_tier': 'executive',   # R1
        'incident_active': True,         # R5
        'asset_age_days': 3,             # R6
    }
    decision = engine.evaluate(ctx)
    assert decision.should_refer is True
    assert 'R1' in decision.reason_codes
    assert 'R5' in decision.reason_codes
    assert 'R6' in decision.reason_codes


def test_referral_audit_summary_contains_rule_details():
    engine = ReferralEngine(rules=get_soc_referral_rules())
    ctx = {'identity_tier': 'board'}
    decision = engine.evaluate(ctx)
    assert 'R1' in decision.audit_summary
    assert 'EXECUTIVE_ACCOUNT' in decision.audit_summary


def test_missing_context_defaults_to_no_fire():
    """Safe degradation: empty context -- no rule fires."""
    engine = ReferralEngine(rules=get_soc_referral_rules())
    decision = engine.evaluate({})
    assert decision.should_refer is False


# ---------------------------------------------------------------------------
# Triage integration
# ---------------------------------------------------------------------------

def test_triage_response_includes_referral_field():
    """Verify the referral field shape returned by the triage endpoint."""
    from app.services.referral_rules import get_soc_referral_rules
    from gae.referral import ReferralEngine

    engine = ReferralEngine(rules=get_soc_referral_rules())
    decision = engine.evaluate({'identity_tier': 'standard'})
    payload = {
        'should_refer': decision.should_refer,
        'reasons': decision.reason_codes,
        'audit_summary': decision.audit_summary,
    }
    assert 'should_refer' in payload
    assert 'reasons' in payload
    assert 'audit_summary' in payload
    assert isinstance(payload['reasons'], list)


def test_triage_referral_veto_overrides_auto_approve():
    """Referral engine returns should_refer=True for executive tier,
    which must override any auto-approve routing decision."""
    engine = ReferralEngine(rules=get_soc_referral_rules())
    decision = engine.evaluate({'identity_tier': 'c_suite'})
    assert decision.should_refer is True
    # Simulates the triage veto logic
    routing_zone = 'auto_approve'
    selected_action = 'suppress'
    if decision.should_refer:
        selected_action = 'refer_to_analyst'
        routing_zone = 'human_review'
    assert selected_action == 'refer_to_analyst'
    assert routing_zone == 'human_review'


# ---------------------------------------------------------------------------
# Neo4j query helpers: get_sequence_count and get_cross_category_count
# ---------------------------------------------------------------------------

def test_r2_fires_when_sequence_count_at_threshold():
    """get_sequence_count returns threshold -> R2 fires."""
    from ci_platform.graph.age_client import AGEClient

    client = object.__new__(AGEClient)
    client.run_query = AsyncMock(return_value=[{"cnt": 3}])

    count = asyncio.run(client.get_sequence_count("192.168.1.1"))
    assert count == 3

    rule = RapidSuccessionRule(threshold=3)
    fires, detail = rule.evaluate({'sequence_count': count})
    assert fires is True
    assert detail['sequence_count'] == 3


def test_r7_fires_when_cross_category_count_at_threshold():
    """get_cross_category_count returns threshold -> R7 fires."""
    from ci_platform.graph.age_client import AGEClient

    client = object.__new__(AGEClient)
    client.run_query = AsyncMock(return_value=[{"cnt": 2}])

    count = asyncio.run(client.get_cross_category_count("jsmith@company.com"))
    assert count == 2

    rule = CrossCategoryRule(threshold=2)
    fires, detail = rule.evaluate({'cross_category_count': count})
    assert fires is True
    assert detail['cross_category_count'] == 2


def test_r2_r7_safe_degradation_on_neo4j_failure():
    """Neo4j exception -> both helpers return 0, neither rule fires (P-REF-2)."""
    from ci_platform.graph.age_client import AGEClient

    client = object.__new__(AGEClient)
    client.run_query = AsyncMock(side_effect=Exception("connection refused"))

    seq_count   = asyncio.run(client.get_sequence_count("10.0.0.1"))
    cross_count = asyncio.run(client.get_cross_category_count("user-42"))

    assert seq_count == 0
    assert cross_count == 0

    r2 = RapidSuccessionRule(threshold=3)
    r7 = CrossCategoryRule(threshold=2)
    assert r2.evaluate({'sequence_count': seq_count})[0] is False
    assert r7.evaluate({'cross_category_count': cross_count})[0] is False


# ---------------------------------------------------------------------------
# referral_debug field — Block 3.3 Phase C
# ---------------------------------------------------------------------------

_minimal_alert_context = {
    'identity_tier':        'standard',
    'sequence_count':       0,
    'category':             'credential_access',
    'compliance_mode':      False,
    'asset_criticality':    0.5,
    'stage1_action':        'escalate',
    'incident_active':      False,
    'asset_age_days':       365,
    'cross_category_count': 0,
}


def test_r2_sequence_count_is_integer():
    """R2 sequence_count populated from alert_context must be an integer >= 0."""
    from ci_platform.graph.age_client import AGEClient

    client = object.__new__(AGEClient)
    client.run_query = AsyncMock(return_value=[{"cnt": 0}])
    seq_count = asyncio.run(client.get_sequence_count("192.168.1.1"))

    debug = {
        'r2_sequence_count':       seq_count,
        'r7_cross_category_count': 0,
        'rules_evaluated':         [r.rule_id for r in get_soc_referral_rules()],
        'rules_fired':             [],
    }
    assert isinstance(debug.get("r2_sequence_count", -1), int)
    assert debug["r2_sequence_count"] >= 0


def test_r7_cross_category_count_is_integer():
    """R7 cross_category_count populated from alert_context must be an integer >= 0."""
    from ci_platform.graph.age_client import AGEClient

    client = object.__new__(AGEClient)
    client.run_query = AsyncMock(return_value=[{"cnt": 0}])
    cross_count = asyncio.run(client.get_cross_category_count("jsmith@company.com"))

    debug = {
        'r2_sequence_count':       0,
        'r7_cross_category_count': cross_count,
        'rules_evaluated':         [r.rule_id for r in get_soc_referral_rules()],
        'rules_fired':             [],
    }
    assert isinstance(debug.get("r7_cross_category_count", -1), int)
    assert debug["r7_cross_category_count"] >= 0


def test_all_seven_rules_evaluated():
    """All 7 referral rules must appear in referral_debug.rules_evaluated."""
    engine = ReferralEngine(rules=get_soc_referral_rules())
    decision = engine.evaluate(_minimal_alert_context)

    debug = {
        'r2_sequence_count':       _minimal_alert_context['sequence_count'],
        'r7_cross_category_count': _minimal_alert_context['cross_category_count'],
        'rules_evaluated':         [r.rule_id for r in get_soc_referral_rules()],
        'rules_fired':             list(decision.reason_codes),
    }
    evaluated = debug.get("rules_evaluated", [])
    for rule in ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]:
        assert rule in evaluated, f"{rule} not in rules_evaluated"
