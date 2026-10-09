"""
tests/test_campaign_frontend.py -- F6 Step 7 frontend integration tests.

3 backend API contract tests validating the shape of responses consumed
by CampaignIntelligencePanel.tsx. No browser / Playwright required.

Run from backend/:
    pytest tests/test_campaign_frontend.py -v
"""

import sys
import os
import asyncio
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.graph_client import graph_client

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def campaign_contract_fixture():
    """Provide one disposable campaign for the API shape tests."""
    fixture_campaign_id = f"TEST-SOC-CAMPAIGN-CONTRACT-{uuid.uuid4().hex}"
    now_ms = int(time.time() * 1000)

    async def seed() -> None:
        existing = await graph_client.run_query(
            "MATCH (c:Campaign {domain: 'soc', campaign_id: "
            f"'{fixture_campaign_id}'}}) RETURN c"
        )
        if existing:
            return
        await graph_client.run_query(
            "CREATE (c:Campaign {"
            f"domain: 'soc', campaign_id: '{fixture_campaign_id}', "
            f"first_seen: {now_ms}, last_seen: {now_ms}, alert_count: 0, "
            "category_sequence: ['phishing'], shared_entities: ['fixture-host'], "
            "technique_sequence: [], confidence: 0.8, "
            "trigger_rule: 'shared_entity', rule_type: 'shared_entity', "
            "derived_entity_key: 'fixture-host', category: 'phishing', "
            "time_bucket: 0, severity: 'MEDIUM', correlation_window_hours: 24, "
            "nl_summary: 'Disposable campaign contract fixture', "
            f"updated_at_epoch: {now_ms}}})"
        )

    async def cleanup() -> None:
        await graph_client.run_query(
            "MATCH (c:Campaign {domain: 'soc', campaign_id: "
            f"'{fixture_campaign_id}'}}) DETACH DELETE c"
        )

    asyncio.run(seed())
    yield fixture_campaign_id
    asyncio.run(cleanup())

REQUIRED_CAMPAIGN_FIELDS = {
    "campaign_id", "first_seen", "last_seen", "alert_count",
    "category_sequence", "shared_entities", "confidence",
    "trigger_rule", "severity", "nl_summary",
}


# ============================================================================
# Test 1 — GET /api/soc/campaigns returns required top-level keys
# ============================================================================

def test_campaigns_endpoint_returns_required_fields():
    """
    CampaignIntelligencePanel.tsx reads data.campaigns, data.active_campaigns.
    All three top-level keys must always be present even with empty graph.
    """
    response = client.get("/api/soc/campaigns")

    assert response.status_code == 200, (
        f"Expected 200. Got {response.status_code}: {response.text[:300]}"
    )
    data = response.json()

    assert "campaigns" in data, f"Missing 'campaigns': {list(data.keys())}"
    assert "total" in data, f"Missing 'total': {list(data.keys())}"
    assert "active_campaigns" in data, f"Missing 'active_campaigns': {list(data.keys())}"
    assert isinstance(data["campaigns"], list), (
        f"'campaigns' must be a list. Got: {type(data['campaigns'])}"
    )


# ============================================================================
# Test 2 — Campaign list items have all fields consumed by the frontend
# ============================================================================

def test_campaign_list_items_have_required_fields(campaign_contract_fixture: str):
    """
    CampaignIntelligencePanel renders campaign_id, alert_count, confidence,
    category_sequence, shared_entities, severity, nl_summary.
    If any campaigns exist, every item must have all these fields.
    """
    # Trigger recorrelation first to populate if possible
    client.post("/api/soc/campaigns/recorrelate")

    response = client.get("/api/soc/campaigns")
    assert response.status_code == 200
    data = response.json()

    c = next(
        (
            campaign
            for campaign in data["campaigns"]
            if campaign.get("campaign_id") == campaign_contract_fixture
        ),
        None,
    )
    assert c is not None, f"Fixture campaign {campaign_contract_fixture} missing from response"
    missing = REQUIRED_CAMPAIGN_FIELDS - set(c.keys())
    assert not missing, (
        f"Campaign item missing required fields: {missing}. "
        f"Got fields: {list(c.keys())}"
    )


# ============================================================================
# Test 3 — Campaign detail includes attack_progression with stages
# ============================================================================

def test_campaign_detail_returns_attack_progression(campaign_contract_fixture: str):
    """
    The campaign detail endpoint must include attack_progression.stages --
    consumed by the frontend campaign detail view (future tab).
    """
    # Recorrelate to populate
    client.post("/api/soc/campaigns/recorrelate")

    list_resp = client.get("/api/soc/campaigns")
    assert list_resp.status_code == 200
    campaigns = list_resp.json().get("campaigns", [])

    campaign = next(
        (
            item
            for item in campaigns
            if item.get("campaign_id") == campaign_contract_fixture
        ),
        None,
    )
    assert campaign is not None, f"Fixture campaign {campaign_contract_fixture} missing from response"
    campaign_id = campaign["campaign_id"]

    detail_resp = client.get(f"/api/soc/campaigns/{campaign_id}")
    assert detail_resp.status_code == 200, (
        f"Expected 200 for detail. Got {detail_resp.status_code}: {detail_resp.text[:200]}"
    )
    detail = detail_resp.json()

    assert "attack_progression" in detail, (
        f"Missing 'attack_progression' in campaign detail: {list(detail.keys())}"
    )
    assert "stages" in detail["attack_progression"], (
        f"Missing 'stages' in attack_progression: {detail['attack_progression']}"
    )


def test_campaign_list_ids_are_detail_readable():
    """
    Every non-empty campaign_id returned by the list endpoint must resolve
    through the detail endpoint with the same canonical campaign_id.
    """
    client.post("/api/soc/campaigns/recorrelate")

    list_resp = client.get("/api/soc/campaigns")
    assert list_resp.status_code == 200
    campaigns = list_resp.json().get("campaigns", [])

    if not campaigns:
        pytest.skip("no campaigns in test graph")

    for campaign in campaigns:
        campaign_id = campaign.get("campaign_id")
        if not campaign_id:
            continue
        detail_resp = client.get(f"/api/soc/campaigns/{campaign_id}")
        assert detail_resp.status_code == 200, (
            f"List returned campaign_id={campaign_id}, but detail returned "
            f"{detail_resp.status_code}: {detail_resp.text[:200]}"
        )
        detail = detail_resp.json()
        assert detail["campaign_id"] == campaign_id
        assert all(d.get("alert_id") for d in detail.get("decisions", []))
