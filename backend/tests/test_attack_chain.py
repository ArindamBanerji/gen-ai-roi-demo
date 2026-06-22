"""Tests for AttackChainService (P16 -- L-06)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.attack_chain import AttackChainService, Campaign

# Minimal mock DB — unit tests don't touch Neo4j
mock_db = MagicMock()


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Test 1 — entity correlation: alerts sharing a user form a group
# ---------------------------------------------------------------------------

def test_entity_correlation_groups():
    """Alerts sharing a user form a group."""
    alerts = [
        {"alert_id": "A1", "users": ["john"], "assets": [], "iocs": []},
        {"alert_id": "A2", "users": ["john"], "assets": [], "iocs": []},
        {"alert_id": "A3", "users": ["john"], "assets": [], "iocs": []},
    ]
    service = AttackChainService(mock_db)
    groups = service._correlate_by_entity(alerts)
    assert len(groups) == 1
    assert len(groups[0]) == 3


# ---------------------------------------------------------------------------
# Test 2 — below minimum: <3 alerts must not form a campaign
# ---------------------------------------------------------------------------

def test_no_campaign_below_minimum():
    """<3 alerts don't form a campaign."""
    alerts = [
        {"alert_id": "A1", "users": ["john"], "assets": [], "iocs": []},
        {"alert_id": "A2", "users": ["john"], "assets": [], "iocs": []},
    ]
    service = AttackChainService(mock_db)
    groups = service._correlate_by_entity(alerts)
    assert len(groups) == 0


# ---------------------------------------------------------------------------
# Test 3 — IOC correlation: alerts sharing IOC form a group
# ---------------------------------------------------------------------------

def test_ioc_correlation():
    """Alerts sharing IOCs form a group."""
    alerts = [
        {"alert_id": "A1", "users": [], "assets": [], "iocs": ["evil.com"]},
        {"alert_id": "A2", "users": [], "assets": [], "iocs": ["evil.com"]},
        {"alert_id": "A3", "users": [], "assets": [], "iocs": ["evil.com"]},
    ]
    service = AttackChainService(mock_db)
    groups = service._correlate_by_ioc(alerts)
    assert len(groups) == 1


# ---------------------------------------------------------------------------
# Test 4 — NL summary is readable
# ---------------------------------------------------------------------------

def test_campaign_summary_readable():
    """Campaign summary is plain English."""
    campaign = Campaign(
        campaign_id="C-2026-0001",
        alerts=["A1", "A2", "A3"],
        shared_entities=[{"type": "user", "value": "john"}],
        correlation_type="entity",
        confidence=0.80,
        first_seen="2026-03-19T10:00:00",
        last_seen="2026-03-19T14:00:00",
        mitre_tactics=[],
        summary="Campaign of 3 alerts involving 1 user(s) and 0 asset(s).",
    )
    assert "Campaign" in campaign.summary
    assert "3 alerts" in campaign.summary


# ---------------------------------------------------------------------------
# Test 5 — merge overlapping groups
# ---------------------------------------------------------------------------

def test_merge_overlapping_groups():
    """Two groups sharing 2+ alerts merge into one."""
    service = AttackChainService(mock_db)
    g1 = [{"alert_id": "A1"}, {"alert_id": "A2"}, {"alert_id": "A3"}]
    g2 = [{"alert_id": "A2"}, {"alert_id": "A3"}, {"alert_id": "A4"}]
    merged = service._merge_groups([g1], [g2])
    assert len(merged) == 1
    assert len(merged[0]) == 4


# ---------------------------------------------------------------------------
# Test 6 — endpoint returns valid structure
# ---------------------------------------------------------------------------

def test_endpoint_returns_campaigns(client):
    """GET /api/soc/attack-chains returns valid structure."""
    response = client.get("/api/soc/attack-chains")
    assert response.status_code == 200
    data = response.json()
    assert "campaigns" in data
    assert "total_campaigns" in data
    assert isinstance(data["campaigns"], list)
    assert isinstance(data["total_campaigns"], int)
