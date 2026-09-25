import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timedelta
import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app
from app.domains.soc import campaigns as campaigns_module


client = TestClient(app)


def _iso(days_ago: int = 0) -> str:
    return (datetime.utcnow() - timedelta(days=days_ago)).isoformat()


def _rows():
    return [
        {
            "c": {
                "campaign_id": "CAMP-ACTIVE",
                "first_seen": _iso(0),
                "last_seen": _iso(0),
                "alert_count": 1,
                "category_sequence": ["phishing"],
                "shared_entities": ["user:U1"],
                "confidence": 0.91,
                "trigger_rule": "shared_entity",
                "severity": "HIGH",
                "nl_summary": "Active campaign.",
            }
        },
        {
            "c": {
                "campaign_id": "CAMP-CONTINUES",
                "first_seen": _iso(4),
                "last_seen": _iso(2),
                "alert_count": 3,
                "category_sequence": ["credential_access", "lateral_movement"],
                "shared_entities": ["asset:A1"],
                "confidence": 0.87,
                "trigger_rule": "technique_sequence",
                "severity": "MEDIUM",
                "nl_summary": "Continuing campaign.",
            }
        },
        {
            "c": {
                "campaign_id": "CAMP-RESOLVED",
                "first_seen": _iso(14),
                "last_seen": _iso(10),
                "alert_count": 4,
                "category_sequence": ["data_exfiltration"],
                "shared_entities": ["user:U2"],
                "confidence": 0.78,
                "trigger_rule": "temporal",
                "severity": "LOW",
                "nl_summary": "Resolved campaign.",
            }
        },
    ]


class FakeCampaignRepository:
    calls = {"get_campaigns": 0, "get_campaign_detail": 0, "write_campaign": 0}
    rows = _rows()

    def __init__(self, _graph):
        self.graph = _graph

    async def get_campaigns(self, limit=50, min_confidence=0.0, trigger_rule=None):
        FakeCampaignRepository.calls["get_campaigns"] += 1
        return FakeCampaignRepository.rows[:limit]

    async def get_campaign_detail(self, campaign_id):
        FakeCampaignRepository.calls["get_campaign_detail"] += 1
        row = next((item for item in FakeCampaignRepository.rows if item["c"]["campaign_id"] == campaign_id), None)
        if not row:
            return None
        campaign = row["c"]
        return {
            "c": campaign,
            "decisions": [
                {
                    "alert_id": f"{campaign_id}-A1",
                    "category": "phishing",
                    "timestamp": campaign["first_seen"],
                },
                {
                    "alert_id": f"{campaign_id}-A2",
                    "category": "phishing",
                    "timestamp": campaign["last_seen"],
                },
            ],
        }

    async def write_campaign(self, _campaign):
        FakeCampaignRepository.calls["write_campaign"] += 1
        return True


def _patch_repo(monkeypatch, rows=None):
    FakeCampaignRepository.calls = {"get_campaigns": 0, "get_campaign_detail": 0, "write_campaign": 0}
    FakeCampaignRepository.rows = _rows() if rows is None else rows
    monkeypatch.setattr(campaigns_module, "CampaignRepository", FakeCampaignRepository)


def _patch_live_repo(monkeypatch, age_graph):
    repo = campaigns_module.CampaignRepository(age_graph.client)
    repo.write_campaign = AsyncMock(wraps=repo.write_campaign)
    for row in _rows():
        props = row["c"]
        cid = props["campaign_id"]
        age_graph.node("Campaign", domain="soc", **props)
        for index in range(2):
            aid = f"{cid}-A{index}"
            age_graph.alert(alert_id=aid)
            age_graph.decision(decision_id=aid, category="credential_access")
            age_graph.query(f"MATCH (d:Decision {{decision_id: '{aid}'}}), (a:Alert {{alert_id: '{aid}'}}), (c:Campaign {{campaign_id: '{cid}'}}) CREATE (d)-[:DECIDED_ON]->(a), (a)-[:MEMBER_OF]->(c) RETURN d")
    monkeypatch.setattr(campaigns_module, "CampaignRepository", lambda graph: repo)
    return repo


def test_campaign_timeline_returns_200_with_list(monkeypatch):
    _patch_repo(monkeypatch)
    response = client.get("/api/soc/campaign-timeline")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_campaign_timeline_has_required_fields(monkeypatch):
    _patch_repo(monkeypatch)
    data = client.get("/api/soc/campaign-timeline").json()
    first = data[0]
    for key in ("campaign_id", "state", "alert_count", "events"):
        assert key in first


def test_campaign_timeline_events_are_chronological(monkeypatch):
    _patch_repo(monkeypatch)
    data = client.get("/api/soc/campaign-timeline").json()
    for campaign in data:
        times = [event["at"] for event in campaign["events"]]
        assert times == sorted(times)


def test_campaign_timeline_states_are_valid(monkeypatch):
    _patch_repo(monkeypatch)
    states = {campaign["state"] for campaign in client.get("/api/soc/campaign-timeline").json()}
    assert states <= {"ACTIVE", "CONTINUES", "RESOLVED"}
    assert {"ACTIVE", "CONTINUES", "RESOLVED"} <= states


def test_campaign_timeline_empty_list(monkeypatch):
    _patch_repo(monkeypatch, rows=[])
    response = client.get("/api/soc/campaign-timeline")
    assert response.status_code == 200
    assert response.json() == []


def test_campaign_timeline_includes_provenance(monkeypatch):
    _patch_repo(monkeypatch)
    data = client.get("/api/soc/campaign-timeline").json()
    assert all(campaign["provenance"] in ("learned", "context") for campaign in data)


@pytest.mark.age
def test_campaign_timeline_is_read_only(monkeypatch, age_graph):
    repo = _patch_live_repo(monkeypatch, age_graph)
    before = age_graph.query("MATCH (n) RETURN count(n) AS n")
    response = client.get("/api/soc/campaign-timeline")
    after = age_graph.query("MATCH (n) RETURN count(n) AS n")
    assert response.status_code == 200
    assert before == after
    repo.write_campaign.assert_not_called()


def test_campaign_timeline_state_boundaries(monkeypatch):
    now = datetime.utcnow()
    rows = [
        {
            "c": {
                "campaign_id": "CAMP-BOUND-ACTIVE",
                "first_seen": (now - timedelta(hours=2)).isoformat(),
                "last_seen": (now - timedelta(hours=23, minutes=59)).isoformat(),
                "alert_count": 2,
                "category_sequence": ["phishing"],
                "shared_entities": ["user:U1"],
                "confidence": 0.91,
                "trigger_rule": "shared_entity",
                "severity": "HIGH",
                "nl_summary": "Still active.",
            }
        },
        {
            "c": {
                "campaign_id": "CAMP-BOUND-CONTINUES",
                "first_seen": (now - timedelta(days=2)).isoformat(),
                "last_seen": (now - timedelta(hours=24, minutes=1)).isoformat(),
                "alert_count": 2,
                "category_sequence": ["lateral_movement"],
                "shared_entities": ["user:U2"],
                "confidence": 0.88,
                "trigger_rule": "shared_entity",
                "severity": "MEDIUM",
                "nl_summary": "Continuing.",
            }
        },
    ]
    _patch_repo(monkeypatch, rows=rows)
    states = {campaign["campaign_id"]: campaign["state"] for campaign in client.get("/api/soc/campaign-timeline").json()}
    assert states["CAMP-BOUND-ACTIVE"] == "ACTIVE"
    assert states["CAMP-BOUND-CONTINUES"] == "CONTINUES"


def test_campaign_timeline_zero_alert_campaign_is_active(monkeypatch):
    rows = [
        {
            "c": {
                "campaign_id": "CAMP-ZERO",
                "first_seen": _iso(2),
                "last_seen": _iso(2),
                "alert_count": 0,
                "category_sequence": [],
                "shared_entities": [],
                "confidence": 0.5,
                "trigger_rule": "none",
                "severity": "LOW",
                "nl_summary": "Zero-alert placeholder.",
            }
        }
    ]
    _patch_repo(monkeypatch, rows=rows)
    data = client.get("/api/soc/campaign-timeline").json()
    assert data[0]["state"] == "ACTIVE"
    assert data[0]["alert_count"] == 0


def test_campaign_timeline_bounds_large_campaign_sets(monkeypatch):
    rows = []
    for idx in range(75):
        rows.append({
            "c": {
                "campaign_id": f"CAMP-LARGE-{idx:03d}",
                "first_seen": _iso(5),
                "last_seen": _iso(idx % 3),
                "alert_count": 120 if idx == 0 else 2,
                "category_sequence": ["phishing"],
                "shared_entities": [f"user:U{idx}"],
                "confidence": 0.9,
                "trigger_rule": "shared_entity",
                "severity": "MEDIUM",
                "nl_summary": "Large set.",
            }
        })
    _patch_repo(monkeypatch, rows=rows)
    data = client.get("/api/soc/campaign-timeline?limit=100").json()
    assert len(data) == 50
    assert max(campaign["alert_count"] for campaign in data) == 120


def test_campaign_timeline_keeps_concurrent_campaigns_for_same_entity(monkeypatch):
    rows = [
        {
            "c": {
                "campaign_id": "CAMP-ENTITY-1",
                "first_seen": _iso(2),
                "last_seen": _iso(1),
                "alert_count": 2,
                "category_sequence": ["phishing"],
                "shared_entities": ["user:shared"],
                "confidence": 0.8,
                "trigger_rule": "shared_entity",
                "severity": "MEDIUM",
                "nl_summary": "First.",
            }
        },
        {
            "c": {
                "campaign_id": "CAMP-ENTITY-2",
                "first_seen": _iso(3),
                "last_seen": _iso(1),
                "alert_count": 3,
                "category_sequence": ["credential_access"],
                "shared_entities": ["user:shared"],
                "confidence": 0.82,
                "trigger_rule": "shared_entity",
                "severity": "HIGH",
                "nl_summary": "Second.",
            }
        },
    ]
    _patch_repo(monkeypatch, rows=rows)
    data = client.get("/api/soc/campaign-timeline").json()
    assert {campaign["campaign_id"] for campaign in data} == {"CAMP-ENTITY-1", "CAMP-ENTITY-2"}
    assert {campaign["entity_key"] for campaign in data} == {"user:shared"}


@pytest.mark.age
def test_campaign_timeline_links_each_alert_to_its_campaign(monkeypatch, age_graph):
    _patch_live_repo(monkeypatch, age_graph)
    data = client.get("/api/soc/campaign-timeline").json()
    assert len(data) == 3
    for campaign in data:
        assert len(campaign["alert_links"]) == 2
        for link in campaign["alert_links"]:
            assert link["alert_id"]
            assert link["campaign_id"] == campaign["campaign_id"]
        for event in campaign["events"]:
            if event["type"] == "ALERT_ADDED":
                assert event["campaign_id"] == campaign["campaign_id"]


def test_campaign_timeline_exposes_stable_identity_key(monkeypatch):
    _patch_repo(monkeypatch)
    data = client.get("/api/soc/campaign-timeline").json()
    assert all(item["identity_key"] == item["campaign_id"] for item in data)
