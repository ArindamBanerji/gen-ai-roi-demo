"""
Step 11.1 — Tab content export endpoint tests.
All tests mock neo4j_client and service functions — no live Neo4j required.
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _neo4j_tab1_mock():
    """Mock neo4j_client.run_query for Tab 1 queries (alert_count, pending, types)."""
    mock = AsyncMock()
    mock.run_query.side_effect = [
        [{"cnt": 120}],                                         # alert_count
        [{"cnt": 15}],                                          # pending_count
        [                                                       # top_alert_types
            {"type": "brute_force", "n": 42},
            {"type": "phishing",    "n": 35},
            {"type": "malware",     "n": 20},
        ],
    ]
    return mock


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Test 1 — Tab 1 returns required content fields
# ---------------------------------------------------------------------------

def test_tab1_returns_content():
    """GET /api/soc/tab/1/content returns alert_count, top_alert_types, pending_count."""
    from app.routers.soc import _tab1_content

    mock_client = _neo4j_tab1_mock()
    with patch("app.routers.soc.neo4j_client", mock_client):
        content = _run(_tab1_content())

    assert "alert_count" in content,     "Missing alert_count"
    assert "top_alert_types" in content, "Missing top_alert_types"
    assert "pending_count" in content,   "Missing pending_count"
    assert content["alert_count"]   == 120
    assert content["pending_count"] == 15
    assert len(content["top_alert_types"]) == 3
    assert content["top_alert_types"][0]["type"] == "brute_force"
    assert content["top_alert_types"][0]["count"] == 42


# ---------------------------------------------------------------------------
# Test 2 — Tab 5 returns required narrative fields
# ---------------------------------------------------------------------------

def test_tab5_returns_narrative_fields():
    """GET /api/soc/tab/5/content returns headline, what_changed, what_discovered,
    what_system_knows."""
    from app.routers.soc import _tab5_content

    mock_narrative = {
        "headline": "System processed 500 alerts, learned from 120 decisions.",
        "what_changed": {
            "total_verified": 120,
            "total_centroid_updates": 80,
            "top_shifts": [
                {"label": "lateral_movement/escalate", "magnitude": 0.35,
                 "description": "lateral_movement/escalate: 28 correct decisions."},
                {"label": "malware/isolate", "magnitude": 0.25,
                 "description": "malware/isolate: 20 correct decisions."},
            ],
            "iks_delta": 0.0,
        },
        "what_discovered": {
            "attack_chains_detected": 4,
            "chain_summaries": ["Campaign A", "Campaign B"],
            "new_entities": {"users": 0, "assets": 0, "threat_indicators": 0},
            "graph_growth": {"nodes_added": 0, "relationships_added": 0},
        },
        "what_knows": {
            "iks_current": 62.5,
            "categories_calibrated": 4,
            "categories_total": 6,
            "health_status": "GREEN",
        },
        "metrics": {
            "alerts_total": 500, "decisions_verified": 120,
            "campaigns_detected": 4, "iks_current": 62.5,
        },
        "generated_at": "2026-04-04T10:00:00Z",
        "pdf_available": True,
    }

    with patch(
        "app.services.executive_narrative.build_executive_narrative_async",
        new=AsyncMock(return_value=mock_narrative),
    ):
        with patch("app.routers.soc.neo4j_client", AsyncMock()):
            content = _run(_tab5_content())

    assert "headline" in content,          "Missing headline"
    assert "what_changed" in content,      "Missing what_changed"
    assert "what_discovered" in content,   "Missing what_discovered"
    assert "what_system_knows" in content, "Missing what_system_knows"

    assert content["headline"] == mock_narrative["headline"]
    assert len(content["what_changed"]) == 2       # top_shifts sliced to 3
    assert content["what_discovered"]["campaign_count"] == 4
    assert content["what_discovered"]["chain_count"]    == 2
    assert content["what_system_knows"]["iks"]                   == 62.5
    assert content["what_system_knows"]["categories_calibrated"] == 4
    assert content["what_system_knows"]["health_status"]         == "GREEN"


# ---------------------------------------------------------------------------
# Test 3 — Invalid tab n returns 404
# ---------------------------------------------------------------------------

def test_invalid_tab_returns_404():
    """GET /api/soc/tab/6/content returns 404."""
    for invalid_n in (0, 6, 99):
        resp = client.get(f"/api/soc/tab/{invalid_n}/content")
        assert resp.status_code == 404, (
            f"Expected 404 for tab {invalid_n}, got {resp.status_code}"
        )
        detail = resp.json().get("detail", "")
        assert "1-5" in detail or str(invalid_n) in detail, (
            f"404 detail should reference valid range, got: {detail!r}"
        )
