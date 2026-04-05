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
    """Mock neo4j_client.run_query for Tab 1 queries."""
    mock = AsyncMock()
    mock.run_query.side_effect = [
        [{"cnt": 120}],                                          # alert_count
        [{"cnt": 15}],                                           # pending_count
        [                                                        # top_alert_types (Fix 1.1)
            {"category": "brute_force", "alert_type": None, "n": 42},
            {"category": "phishing",    "alert_type": None, "n": 35},
            {"category": "malware",     "alert_type": None, "n": 20},
        ],
        [                                                        # per-category verified (Fix 1.2)
            {"category": "brute_force", "verified": 50,  "overrides": 5},
            {"category": "phishing",    "verified": 30,  "overrides": 3},
            {"category": "malware",     "verified": 120, "overrides": 10},
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
    first = content["top_alert_types"][0]
    assert first["type"]  == "brute_force"
    assert first["count"] == 42
    # Fix 1.2 fields
    assert "learning_signal"  in first, "Missing learning_signal"
    assert "analyst_insight"  in first, "Missing analyst_insight"
    assert "brute force" in first["learning_signal"]
    assert "brute force" in first["analyst_insight"]


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


# ---------------------------------------------------------------------------
# Block 11.2 — Test 4: Tab 2 has decision_count_glossary (FIX 2.1)
# ---------------------------------------------------------------------------

def test_tab2_has_decision_glossary():
    """Tab 2 content includes decision_count_glossary with three keys."""
    from app.routers.soc import _tab2_content

    mock_iks = {
        "iks_v2": 71.0,
        "interpretation": "Calibrated — model has sufficient training signal",
        "components": {"trust_coverage": 50.0},
        "total_decisions": 537,
    }

    mock_client = AsyncMock()
    mock_client.run_query.return_value = [{"cnt": 12}]

    with patch("app.services.iks.compute_iks_v2", new=AsyncMock(return_value=mock_iks)):
        with patch("app.routers.soc.neo4j_client", mock_client):
            content = _run(_tab2_content())

    assert "decision_count_glossary" in content, "Missing decision_count_glossary"
    glossary = content["decision_count_glossary"]
    assert "verified_decisions"       in glossary, "Missing verified_decisions key"
    assert "switching_cost_threshold" in glossary, "Missing switching_cost_threshold key"
    assert "override_examples"        in glossary, "Missing override_examples key"
    # All three values must be non-empty strings
    for key, val in glossary.items():
        assert isinstance(val, str) and val, f"Glossary[{key!r}] must be a non-empty string"

    assert "drift_alert_summary"    in content, "Missing drift_alert_summary (FIX 2.2)"
    assert "trust_coverage_summary" in content, "Missing trust_coverage_summary (FIX 2.3)"


# ---------------------------------------------------------------------------
# Block 11.2 — Test 5: Tab 3 has recommendation and kernel weights (FIX 2.4)
# ---------------------------------------------------------------------------

def test_tab3_has_recommendation_and_kernel_weights():
    """Tab 3 content includes recommendation, kernel_note, and factor_breakdown with weights."""
    from app.routers.soc import _tab3_content

    mock_client = AsyncMock()
    mock_client.run_query.return_value = [{"cnt": 5000}]

    with patch("app.routers.soc.neo4j_client", mock_client):
        content = _run(_tab3_content())

    assert "recommendation" in content, "Missing recommendation (FIX 2.4)"
    assert "kernel_note"    in content, "Missing kernel_note (FIX 2.4)"
    assert "graph_context"  in content, "Missing graph_context (FIX 2.5)"

    rec = content["recommendation"]
    assert "action"     in rec, "recommendation missing 'action'"
    assert "confidence" in rec, "recommendation missing 'confidence'"
    assert isinstance(rec["confidence"], float)

    breakdown = content.get("factor_breakdown", [])
    assert len(breakdown) > 0, "factor_breakdown must not be empty"
    for item in breakdown:
        assert "sigma"          in item, f"factor_breakdown item missing 'sigma': {item}"
        assert "kernel_weight"  in item, f"factor_breakdown item missing 'kernel_weight': {item}"
        assert "interpretation" in item, f"factor_breakdown item missing 'interpretation': {item}"
        assert 0.0 <= item["kernel_weight"] <= 1.0, (
            f"kernel_weight out of [0,1]: {item['kernel_weight']}"
        )

    # threat_intel_enrichment must have the highest kernel weight (σ=0.07)
    weights = {item["name"]: item["kernel_weight"] for item in breakdown}
    if "threat_intel_enrichment" in weights:
        assert weights["threat_intel_enrichment"] == max(weights.values()), (
            "threat_intel_enrichment (σ=0.07) must have the highest kernel weight"
        )


# ---------------------------------------------------------------------------
# Block 11.2 — Test 6: Tab 4 has ROI methodology note (FIX 2.6) and switching cost (FIX 2.7)
# ---------------------------------------------------------------------------

def test_tab4_has_roi_methodology():
    """Tab 4 content includes roi_methodology and switching_cost_dollars."""
    from app.routers.soc import _tab4_content

    mock_client = AsyncMock()
    mock_client.run_query.side_effect = [
        [{"t_min": 1_700_000_000_000, "t_max": 1_700_086_400_000, "n": 200}],  # decisions
        [{"cnt": 180}],  # evolution events (correct decisions)
    ]

    with patch("app.routers.soc.neo4j_client", mock_client):
        content = _run(_tab4_content())

    assert "roi_methodology"        in content, "Missing roi_methodology (FIX 2.6)"
    assert "switching_cost_dollars" in content, "Missing switching_cost_dollars (FIX 2.7)"

    meth = content["roi_methodology"]
    assert meth["baseline_min_per_alert"] == 44, "Baseline must be 44 min/alert"
    assert meth["system_min_per_alert"]   == 13, "System must be 13 min/alert"
    assert "source" in meth and meth["source"], "Missing source attribution"

    sw = content["switching_cost_dollars"]
    assert "cost_usd"               in sw, "Missing cost_usd"
    assert "analyst_days_to_rebuild" in sw, "Missing analyst_days_to_rebuild"
    assert "narrative"              in sw and sw["narrative"], "Missing switching cost narrative"
    assert sw["cost_usd"] > 0, "Switching cost must be positive"


# ---------------------------------------------------------------------------
# Block 11.2 — Test 7: Tab 5 has w2_flywheel claim (FIX 2.8)
# ---------------------------------------------------------------------------

def test_tab5_has_w2_flywheel_claim():
    """Tab 5 what_system_knows includes w2_flywheel string."""
    from app.routers.soc import _tab5_content

    mock_narrative = {
        "headline": "System processed 500 alerts.",
        "what_changed": {
            "top_shifts": [
                {"label": "lateral_movement/escalate", "magnitude": 0.35,
                 "description": "lateral_movement/escalate: 28 decisions."},
            ],
        },
        "what_discovered": {
            "attack_chains_detected": 2,
            "chain_summaries": ["Campaign A"],
        },
        "what_knows": {
            "iks_current": 71.0,
            "categories_calibrated": 5,
            "health_status": "GREEN",
        },
    }

    # Mock: 50 evolution edges → flywheel active
    mock_client = AsyncMock()
    mock_client.run_query.return_value = [{"n": 50}]

    with patch(
        "app.services.executive_narrative.build_executive_narrative_async",
        new=AsyncMock(return_value=mock_narrative),
    ):
        with patch("app.routers.soc.neo4j_client", mock_client):
            content = _run(_tab5_content())

    wsk = content["what_system_knows"]
    assert "w2_flywheel" in wsk, "Missing w2_flywheel in what_system_knows (FIX 2.8)"
    assert isinstance(wsk["w2_flywheel"], str) and wsk["w2_flywheel"], (
        "w2_flywheel must be a non-empty string"
    )
    # With 50 edges, flywheel should be active
    assert "50" in wsk["w2_flywheel"] or "flywheel" in wsk["w2_flywheel"].lower(), (
        "w2_flywheel string should reference edge count or flywheel"
    )

    assert "centroid_summary" in wsk, "Missing centroid_summary (FIX 2.9)"
    assert isinstance(wsk["centroid_summary"], str) and wsk["centroid_summary"]


# ---------------------------------------------------------------------------
# Block 11.2 — Test 8: Tab 5 has conservation_narrative (FIX 2.10)
# ---------------------------------------------------------------------------

def test_tab5_has_conservation_narrative():
    """Tab 5 what_system_knows includes conservation_narrative for each health_status."""
    from app.routers.soc import _tab5_content

    for status, expected_keyword in [
        ("GREEN",   "satisfied"),
        ("AMBER",   "baseline"),
        ("RED",     "violated"),
        ("UNKNOWN", "not yet computed"),
    ]:
        mock_narrative = {
            "headline": "Test.",
            "what_changed": {"top_shifts": []},
            "what_discovered": {"attack_chains_detected": 0, "chain_summaries": []},
            "what_knows": {
                "iks_current": 50.0,
                "categories_calibrated": 3,
                "health_status": status,
            },
        }

        mock_client = AsyncMock()
        mock_client.run_query.return_value = [{"n": 0}]

        with patch(
            "app.services.executive_narrative.build_executive_narrative_async",
            new=AsyncMock(return_value=mock_narrative),
        ):
            with patch("app.routers.soc.neo4j_client", mock_client):
                content = _run(_tab5_content())

        wsk = content["what_system_knows"]
        assert "conservation_narrative" in wsk, (
            f"Missing conservation_narrative for health_status={status!r}"
        )
        narrative = wsk["conservation_narrative"]
        assert isinstance(narrative, str) and narrative, (
            f"conservation_narrative must be non-empty string for status={status!r}"
        )
        assert expected_keyword.lower() in narrative.lower(), (
            f"For status={status!r}, expected {expected_keyword!r} in narrative: {narrative!r}"
        )
