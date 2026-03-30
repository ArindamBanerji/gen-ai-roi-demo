"""
tests/test_campaign_matcher.py — F6 CampaignRepository + CampaignMatcher tests.

4 tests using AsyncMock Neo4j — no live database required.

Run from backend/:
    pytest tests/test_campaign_matcher.py -v
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock

from app.domains.soc.campaigns import (
    Campaign,
    CampaignCorrelationEngine,
    CampaignMatcher,
    CampaignRepository,
)

DEFAULT_CONFIG = {
    "correlation_window_hours": 24,
    "temporal_window_minutes": 60,
    "min_alerts_for_campaign": 2,
    "max_campaign_age_days": 30,
}


def run(coro):
    return asyncio.run(coro)


# ============================================================================
# Test 1 — check_alert returns None on exception (never raises)
# ============================================================================

def test_check_alert_returns_none_on_exception():
    """
    CampaignMatcher.check_alert must never raise.
    Neo4j failure → log warning → return None.
    """
    mock_neo4j = AsyncMock()
    mock_neo4j.run_query.side_effect = Exception("Neo4j down")

    engine = CampaignCorrelationEngine(DEFAULT_CONFIG)
    repo = CampaignRepository(mock_neo4j)
    matcher = CampaignMatcher(mock_neo4j, DEFAULT_CONFIG, engine, repo)

    result = run(matcher.check_alert("alert-123"))

    assert result is None, (
        f"check_alert must return None on Neo4j failure, not raise. Got: {result!r}"
    )


# ============================================================================
# Test 2 — check_alert joins existing campaign when found
# ============================================================================

def test_check_alert_joins_existing_campaign():
    """
    When _find_matching_campaign returns a campaign_id, check_alert must
    add the alert to that campaign and return its ID.
    """
    mock_neo4j = AsyncMock()
    # First run_query call (_find_matching_campaign) returns existing campaign
    mock_neo4j.run_query.return_value = [{"campaign_id": "camp-abc"}]

    engine = CampaignCorrelationEngine(DEFAULT_CONFIG)
    repo = CampaignRepository(mock_neo4j)
    matcher = CampaignMatcher(mock_neo4j, DEFAULT_CONFIG, engine, repo)

    result = run(matcher.check_alert("alert-new"))

    assert result == "camp-abc", (
        f"Expected campaign_id='camp-abc' when existing campaign found. Got: {result!r}"
    )


# ============================================================================
# Test 3 — check_alert returns None when no campaign and insufficient events
# ============================================================================

def test_check_alert_returns_none_when_no_campaign():
    """
    When no existing campaign and Neo4j returns no recent events,
    check_alert must return None (not create a spurious campaign).
    """
    mock_neo4j = AsyncMock()
    # All reads return empty — no existing campaign, no recent events
    mock_neo4j.run_query.return_value = []

    engine = CampaignCorrelationEngine(DEFAULT_CONFIG)
    repo = CampaignRepository(mock_neo4j)
    matcher = CampaignMatcher(mock_neo4j, DEFAULT_CONFIG, engine, repo)

    result = run(matcher.check_alert("alert-xyz"))

    assert result is None, (
        f"Expected None when no campaign and no events. Got: {result!r}"
    )


# ============================================================================
# Test 4 — write_campaign is idempotent (MERGE safe to call twice)
# ============================================================================

def test_repository_write_campaign_is_idempotent():
    """
    write_campaign uses MERGE — calling it twice with the same campaign_id
    must succeed both times (return True). No unique-constraint violation.
    """
    mock_neo4j = AsyncMock()
    mock_neo4j.run_query.return_value = None

    repo = CampaignRepository(mock_neo4j)

    campaign = Campaign(
        campaign_id="c-001",
        first_seen=datetime(2026, 3, 25, 10, 0),
        last_seen=datetime(2026, 3, 25, 16, 0),
        alert_count=2,
        category_sequence=["credential_access", "lateral_movement"],
        shared_entities=["ip-1"],
        technique_sequence=[],
        confidence=0.85,
        trigger_rule="technique_sequence",
        severity="HIGH",
        member_decision_ids=[],
        member_alert_ids=["a1", "a2"],
        correlation_window_hours=24,
        nl_summary="2 alerts: credential_access → lateral_movement over 6h.",
    )

    result1 = run(repo.write_campaign(campaign))
    result2 = run(repo.write_campaign(campaign))  # second write — MERGE is safe

    assert result1 is True, f"First write_campaign must return True. Got: {result1!r}"
    assert result2 is True, f"Second write_campaign must return True. Got: {result2!r}"
