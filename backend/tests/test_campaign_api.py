"""
tests/test_campaign_api.py — F6 Campaign API endpoint tests.

4 tests validating GET /api/soc/campaigns, GET /api/soc/campaigns/{id},
POST /api/soc/campaigns/recorrelate, and query-param filtering.

Run from backend/:
    pytest tests/test_campaign_api.py -v
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ============================================================================
# Test 1 — GET /api/soc/campaigns returns required keys
# ============================================================================

def test_get_campaigns_returns_list():
    """
    GET /api/soc/campaigns must return 200 with 'campaigns', 'total',
    and 'active_campaigns' keys. Empty Neo4j → empty list, not 500.
    """
    response = client.get("/api/soc/campaigns")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:300]}"
    )
    body = response.json()
    assert "campaigns" in body, f"Missing 'campaigns' key: {list(body.keys())}"
    assert "total" in body, f"Missing 'total' key: {list(body.keys())}"
    assert "active_campaigns" in body, f"Missing 'active_campaigns' key: {list(body.keys())}"
    assert isinstance(body["campaigns"], list), (
        f"'campaigns' must be a list. Got: {type(body['campaigns'])}"
    )


# ============================================================================
# Test 2 — GET /api/soc/campaigns/{id} returns 404 for unknown campaign
# ============================================================================

def test_get_campaign_detail_404_on_missing():
    """
    GET /api/soc/campaigns/nonexistent-id must return 404.
    When CampaignRepository.get_campaign_detail returns None,
    the endpoint raises HTTPException(404).
    """
    response = client.get("/api/soc/campaigns/nonexistent-id-xyz-000")

    assert response.status_code == 404, (
        f"Expected 404 for unknown campaign. Got {response.status_code}: {response.text[:200]}"
    )


# ============================================================================
# Test 3 — POST /api/soc/campaigns/recorrelate returns count keys
# ============================================================================

def test_recorrelate_returns_counts():
    """
    POST /api/soc/campaigns/recorrelate must return 200 with
    'campaigns_found', 'campaigns_written', 'events_processed'.
    Empty graph → all zeros, not 500.
    """
    response = client.post("/api/soc/campaigns/recorrelate")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:300]}"
    )
    data = response.json()
    assert "campaigns_found" in data, f"Missing 'campaigns_found': {list(data.keys())}"
    assert "campaigns_written" in data, f"Missing 'campaigns_written': {list(data.keys())}"
    assert "events_processed" in data, f"Missing 'events_processed': {list(data.keys())}"
    assert isinstance(data["campaigns_found"], int), (
        f"campaigns_found must be int. Got: {type(data['campaigns_found'])}"
    )


# ============================================================================
# Test 4 — GET /api/soc/campaigns accepts filter query params
# ============================================================================

# ============================================================================
# Test 5 — POST /api/soc/campaigns/recorrelate is idempotent
# ============================================================================

def test_recorrelate_is_idempotent():
    """
    Calling recorrelate twice must not crash or produce negative counts.
    The second call is safe because write_campaign is idempotent under the
    Phase 1 AGE-safe MATCH-then-CREATE path.
    """
    r1 = client.post("/api/soc/campaigns/recorrelate")
    r2 = client.post("/api/soc/campaigns/recorrelate")

    assert r1.status_code == 200, (
        f"First recorrelate call failed: {r1.status_code}: {r1.text[:200]}"
    )
    assert r2.status_code == 200, (
        f"Second recorrelate call failed: {r2.status_code}: {r2.text[:200]}"
    )

    d1 = r1.json()
    d2 = r2.json()

    assert d2["campaigns_found"] >= 0, (
        f"Second recorrelate campaigns_found must be >= 0. Got: {d2['campaigns_found']}"
    )
    assert d2["events_processed"] >= 0, (
        f"Second recorrelate events_processed must be >= 0. Got: {d2['events_processed']}"
    )

def test_get_campaigns_accepts_filter_params():
    """
    GET /api/soc/campaigns?min_confidence=0.7&trigger_rule=technique_sequence
    must return 200 and include 'campaigns' key (even if empty).
    Query params are accepted without 422 validation error.
    """
    response = client.get(
        "/api/soc/campaigns?min_confidence=0.7&trigger_rule=technique_sequence"
    )

    assert response.status_code == 200, (
        f"Expected 200 with filter params. Got {response.status_code}: {response.text[:300]}"
    )
    body = response.json()
    assert "campaigns" in body, (
        f"'campaigns' key missing in filtered response: {list(body.keys())}"
    )
