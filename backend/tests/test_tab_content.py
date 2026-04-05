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
            {"category": "credential_access", "alert_type": None, "n": 42},
            {"category": "lateral_movement",  "alert_type": None, "n": 35},
            {"category": "malware_execution", "alert_type": None, "n": 20},
        ],
        [                                                        # per-category verified (Fix 1.2)
            {"category": "credential_access", "verified": 50,  "overrides": 5},
            {"category": "lateral_movement",  "verified": 30,  "overrides": 3},
            {"category": "malware_execution", "verified": 120, "overrides": 10},
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
    assert first["type"]  == "credential_access"
    assert first["count"] == 42
    # Fix 1.2 fields
    assert "learning_signal"  in first, "Missing learning_signal"
    assert "analyst_insight"  in first, "Missing analyst_insight"
    assert "credential access" in first["learning_signal"]
    assert "credential access" in first["analyst_insight"]


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

    mock_client_t2 = AsyncMock()
    mock_client_t2.run_query.return_value = [{"cnt": 0}]

    with patch(
        "app.services.executive_narrative.build_executive_narrative_async",
        new=AsyncMock(return_value=mock_narrative),
    ):
        with patch("app.routers.soc.neo4j_client", mock_client_t2):
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
    trust_summary = content["trust_coverage_summary"]
    assert "80%+" in trust_summary,   f"trust_coverage_summary must contain '80%+': {trust_summary!r}"
    assert "day 270" in trust_summary, f"trust_coverage_summary must contain 'day 270': {trust_summary!r}"


# ---------------------------------------------------------------------------
# Block 11.2 — Test 5: Tab 3 has recommendation and kernel weights (FIX 2.4)
# ---------------------------------------------------------------------------

def test_tab3_has_recommendation_and_kernel_weights():
    """Tab 3 content includes recommendation, kernel_note, and factor_breakdown with weights."""
    from app.routers.soc import _tab3_content
    from app.services.gae_state import init_learning_state

    init_learning_state()  # scorer must be ready for centroid fallback scoring

    _VALID_ACTIONS = {"escalate", "investigate", "suppress", "monitor"}

    mock_client = AsyncMock()
    mock_client.run_query.side_effect = [
        [{"cnt": 5000}],   # graph node count query
        [],                # no pending alert → centroid fallback
    ]

    with patch("app.routers.soc.neo4j_client", mock_client):
        content = _run(_tab3_content())

    assert "recommendation" in content, "Missing recommendation (FIX 2.4)"
    assert "kernel_note"    in content, "Missing kernel_note (FIX 2.4)"
    assert "graph_context"  in content, "Missing graph_context (FIX 2.5)"

    rec = content["recommendation"]
    assert "action"     in rec, "recommendation missing 'action'"
    assert "confidence" in rec, "recommendation missing 'confidence'"
    assert "basis"      in rec, "recommendation missing 'basis'"
    assert isinstance(rec["confidence"], float)
    assert rec["action"] in _VALID_ACTIONS, (
        f"action must be one of {_VALID_ACTIONS}, got: {rec['action']!r}"
    )
    assert rec["basis"] in ("live_scoring", "centroid_fallback"), (
        f"basis must be live_scoring or centroid_fallback, got: {rec['basis']!r}"
    )

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
    assert "calculation" in meth, "roi_methodology must include 'calculation' field (FIX 3)"
    calc = meth["calculation"]
    assert "15 min saved" in calc,        f"calculation must mention '15 min saved': {calc!r}"
    assert "40% auto-approve rate" in calc, f"calculation must mention '40% auto-approve rate': {calc!r}"
    assert "31 min gap" in calc,          f"calculation must mention '31 min gap': {calc!r}"
    assert "$75"         in calc,         f"calculation must mention '$75' hourly rate: {calc!r}"
    assert "365 days"    in calc,         f"calculation must mention '365 days': {calc!r}"
    assert "/day"        in calc,         f"calculation must include daily figure: {calc!r}"
    assert "annually"    in calc,         f"calculation must include annual figure: {calc!r}"

    sw = content["switching_cost_dollars"]
    assert "cost_usd"               in sw, "Missing cost_usd"
    assert "analyst_days_to_rebuild" in sw, "Missing analyst_days_to_rebuild"
    assert "narrative"              in sw and sw["narrative"], "Missing switching cost narrative"
    assert sw["cost_usd"] > 0, "Switching cost must be positive"


# ---------------------------------------------------------------------------
# Block 11.2 — Test 7: Tab 5 has w2_flywheel claim (FIX 2.8)
# ---------------------------------------------------------------------------

def test_tab5_has_w2_flywheel_claim():
    """Tab 5 what_system_knows includes structured flywheel fields (FIX 2.8)."""
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

    # Case A: 50 edges → flywheel active
    mock_client = AsyncMock()
    mock_client.run_query.return_value = [{"cnt": 50}]

    with patch(
        "app.services.executive_narrative.build_executive_narrative_async",
        new=AsyncMock(return_value=mock_narrative),
    ):
        with patch("app.routers.soc.neo4j_client", mock_client):
            content = _run(_tab5_content())

    wsk = content["what_system_knows"]
    assert "flywheel_claim"      in wsk, "Missing flywheel_claim (FIX 2.8)"
    assert "flywheel_message"    in wsk, "Missing flywheel_message (FIX 2.8)"
    assert "flywheel_status"     in wsk, "Missing flywheel_status (FIX 2.8)"
    assert "flywheel_edge_count" in wsk, "Missing flywheel_edge_count (FIX 2.8)"

    assert "+10.13pp" in wsk["flywheel_claim"], "flywheel_claim must contain validated stat"
    assert wsk["flywheel_status"]     == "active", "50 edges → status must be 'active'"
    assert wsk["flywheel_edge_count"] == 50,        "edge count must match mock"
    assert "50" in wsk["flywheel_message"],          "flywheel_message must reference edge count"

    # Case B: 0 edges → pre_activation
    mock_client_cold = AsyncMock()
    mock_client_cold.run_query.return_value = [{"cnt": 0}]

    with patch(
        "app.services.executive_narrative.build_executive_narrative_async",
        new=AsyncMock(return_value=mock_narrative),
    ):
        with patch("app.routers.soc.neo4j_client", mock_client_cold):
            content_cold = _run(_tab5_content())

    wsk_cold = content_cold["what_system_knows"]
    assert wsk_cold["flywheel_status"]     == "pre_activation", "0 edges → pre_activation"
    assert wsk_cold["flywheel_edge_count"] == 0
    assert "+10.13pp" in wsk_cold["flywheel_claim"]

    assert "centroid_summary" in wsk, "Missing centroid_summary (FIX 2.9)"
    assert isinstance(wsk["centroid_summary"], str) and wsk["centroid_summary"]


# ---------------------------------------------------------------------------
# Block 11.2 — Test 8: Tab 5 has conservation_narrative (FIX 2.10)
# ---------------------------------------------------------------------------

def test_tab5_has_conservation_narrative():
    """Tab 5 what_system_knows includes conservation_narrative with CLAIM-OLS-01."""
    from app.routers.soc import _tab5_content

    for status in ("GREEN", "AMBER", "RED"):
        mock_narrative = {
            "headline": "Test.",
            "what_changed": {"top_shifts": [], "total_verified": 100},
            "what_discovered": {"attack_chains_detected": 0, "chain_summaries": []},
            "what_knows": {
                "iks_current": 50.0,
                "categories_calibrated": 3,
                "health_status": status,
            },
        }

        mock_client = AsyncMock()
        mock_client.run_query.return_value = [{"cnt": 0}]

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
        assert "CLAIM-OLS-01" in narrative, (
            f"conservation_narrative must cite CLAIM-OLS-01, got: {narrative!r}"
        )
        assert "0%" in narrative, (
            f"conservation_narrative must contain '0%', got: {narrative!r}"
        )


# ---------------------------------------------------------------------------
# Test 9 — Tab 1 alert types are all valid SOC categories
# ---------------------------------------------------------------------------

def test_tab1_alert_types_are_valid_categories():
    """All top_alert_types[*].type values must be members of VALID_CATEGORIES."""
    from app.routers.soc import _tab1_content, VALID_CATEGORIES

    mock_client = AsyncMock()
    mock_client.run_query.side_effect = [
        [{"cnt": 200}],                                          # alert_count
        [{"cnt": 18}],                                           # pending_count
        [                                                        # top alert types — raw values
            {"category": "anomalous_login",  "alert_type": None, "n": 80},
            {"category": "threat_intel_match", "alert_type": None, "n": 60},
            {"category": "data_exfil",       "alert_type": "data_exfiltration", "n": 40},
        ],
        [],                                                      # per-category verified (empty ok)
    ]

    with patch("app.routers.soc.neo4j_client", mock_client):
        content = _run(_tab1_content())

    types = [t["type"] for t in content["top_alert_types"]]
    assert len(types) > 0, "top_alert_types must not be empty"
    for t in types:
        assert t in VALID_CATEGORIES, (
            f"alert type {t!r} is not in VALID_CATEGORIES — normalization failed"
        )


# ---------------------------------------------------------------------------
# Test 10 — Tab 5 conservation_narrative cites CLAIM-OLS-01
# ---------------------------------------------------------------------------

def test_tab5_conservation_has_claim():
    """Tab 5 conservation_narrative must contain '0%' and 'CLAIM-OLS-01'."""
    from app.routers.soc import _tab5_content

    mock_narrative = {
        "headline": "Test.",
        "what_changed": {"top_shifts": [], "total_verified": 500},
        "what_discovered": {"attack_chains_detected": 0, "chain_summaries": []},
        "what_knows": {
            "iks_current": 72.0,
            "categories_calibrated": 5,
            "health_status": "GREEN",
        },
    }

    mock_client = AsyncMock()
    mock_client.run_query.return_value = [{"cnt": 0}]

    with patch(
        "app.services.executive_narrative.build_executive_narrative_async",
        new=AsyncMock(return_value=mock_narrative),
    ):
        with patch("app.routers.soc.neo4j_client", mock_client):
            content = _run(_tab5_content())

    narrative = content["what_system_knows"]["conservation_narrative"]
    assert "CLAIM-OLS-01" in narrative, (
        f"conservation_narrative must cite CLAIM-OLS-01, got: {narrative!r}"
    )
    assert "0%" in narrative, (
        f"conservation_narrative must contain '0%', got: {narrative!r}"
    )
    # GREEN status → healthy signal
    assert "healthy" in narrative, (
        f"GREEN status must produce 'healthy' signal, got: {narrative!r}"
    )


# ---------------------------------------------------------------------------
# Test 11 — FIX 1: Tab 1 analyst_insight gates "YOUR environment" on verified_count
# ---------------------------------------------------------------------------

def test_tab1_analyst_insight_gates_on_verified_count():
    """analyst_insight contains 'YOUR environment' only when verified_count > 0."""
    from app.routers.soc import _tab1_content

    # Case A: verified_count = 150 (≥100) → "YOUR environment" must appear
    mock_with_decisions = AsyncMock()
    mock_with_decisions.run_query.side_effect = [
        [{"cnt": 120}],
        [{"cnt": 15}],
        [{"category": "credential_access", "alert_type": None, "n": 42}],
        [{"category": "credential_access", "verified": 150, "overrides": 5}],
    ]
    with patch("app.routers.soc.neo4j_client", mock_with_decisions):
        content_a = _run(_tab1_content())

    insight_a = content_a["top_alert_types"][0]["analyst_insight"]
    assert "YOUR environment" in insight_a, (
        f"verified_count=150 must produce 'YOUR environment' in analyst_insight, got: {insight_a!r}"
    )

    # Case B: verified_count = 0 → "YOUR environment" must NOT appear
    mock_no_decisions = AsyncMock()
    mock_no_decisions.run_query.side_effect = [
        [{"cnt": 120}],
        [{"cnt": 15}],
        [{"category": "credential_access", "alert_type": None, "n": 42}],
        [{"category": "credential_access", "verified": 0, "overrides": 0}],
    ]
    with patch("app.routers.soc.neo4j_client", mock_no_decisions):
        content_b = _run(_tab1_content())

    insight_b = content_b["top_alert_types"][0]["analyst_insight"]
    assert "YOUR environment" not in insight_b, (
        f"verified_count=0 must NOT produce 'YOUR environment', got: {insight_b!r}"
    )


# ---------------------------------------------------------------------------
# Test 12 — FIX 2: Tab 3 kernel_note names DiagonalKernel
# ---------------------------------------------------------------------------

def test_tab3_kernel_note_names_diagonal_kernel():
    """kernel_note must contain 'DiagonalKernel' (Innovation #4)."""
    from app.routers.soc import _tab3_content
    from app.services.gae_state import init_learning_state

    init_learning_state()

    mock_client = AsyncMock()
    mock_client.run_query.side_effect = [
        [{"cnt": 5000}],
        [],
    ]

    with patch("app.routers.soc.neo4j_client", mock_client):
        content = _run(_tab3_content())

    kernel_note = content.get("kernel_note", "")
    assert "DiagonalKernel" in kernel_note, (
        f"kernel_note must contain 'DiagonalKernel', got: {kernel_note!r}"
    )
    assert "Innovation #4" in kernel_note, (
        f"kernel_note must reference 'Innovation #4', got: {kernel_note!r}"
    )


# ---------------------------------------------------------------------------
# Test 13 — FIX 3: Tab 5 flywheel reframe for pre-activation state
# ---------------------------------------------------------------------------

def test_tab5_flywheel_preactivation_reframe():
    """With 0 TRIGGERED_EVOLUTION edges, flywheel_message explains pre-activation
    and flywheel_activation_note is present."""
    from app.routers.soc import _tab5_content

    mock_narrative = {
        "headline": "Test.",
        "what_changed": {"top_shifts": []},
        "what_discovered": {"attack_chains_detected": 0, "chain_summaries": []},
        "what_knows": {
            "iks_current": 65.0,
            "categories_calibrated": 4,
            "health_status": "GREEN",
        },
    }

    mock_client = AsyncMock()
    mock_client.run_query.return_value = [{"cnt": 0}]

    with patch(
        "app.services.executive_narrative.build_executive_narrative_async",
        new=AsyncMock(return_value=mock_narrative),
    ):
        with patch("app.routers.soc.neo4j_client", mock_client):
            content = _run(_tab5_content())

    wsk = content["what_system_knows"]

    assert wsk["flywheel_status"] == "pre_activation", (
        "0 edges → flywheel_status must be 'pre_activation'"
    )
    assert "first real alert" in wsk["flywheel_message"], (
        f"flywheel_message must mention 'first real alert', got: {wsk['flywheel_message']!r}"
    )
    assert "flywheel_activation_note" in wsk, (
        "flywheel_activation_note must be present in what_system_knows"
    )
    note = wsk["flywheel_activation_note"]
    assert note is not None, "flywheel_activation_note must not be None"
    assert "CLAIM-W2" in note, (
        f"flywheel_activation_note must cite CLAIM-W2, got: {note!r}"
    )
    assert "+10.13pp" in note, (
        f"flywheel_activation_note must state +10.13pp, got: {note!r}"
    )


# ---------------------------------------------------------------------------
# Test 14 — FIX 1 v2: Tab 1 Microsoft comparison requires ≥100 verified
# ---------------------------------------------------------------------------

def test_tab1_microsoft_only_above_threshold():
    """Microsoft Copilot comparison appears only for categories with ≥100 verified decisions."""
    from app.routers.soc import _tab1_content

    # threat_intel_match with 12 decisions — must NOT mention Microsoft Copilot
    mock_low = AsyncMock()
    mock_low.run_query.side_effect = [
        [{"cnt": 500}],
        [{"cnt": 20}],
        [{"category": "threat_intel_match", "alert_type": None, "n": 30}],
        [{"category": "threat_intel_match", "verified": 12, "overrides": 1}],
    ]
    with patch("app.routers.soc.neo4j_client", mock_low):
        content_low = _run(_tab1_content())

    insight_low = content_low["top_alert_types"][0]["analyst_insight"]
    assert "Microsoft Copilot" not in insight_low, (
        f"threat_intel_match (12 decisions) must NOT mention Microsoft Copilot, got: {insight_low!r}"
    )
    assert "learning" in insight_low, (
        f"Low-count insight must mention 'learning', got: {insight_low!r}"
    )

    # credential_access with 1723 decisions — must contain "YOUR environment"
    mock_high = AsyncMock()
    mock_high.run_query.side_effect = [
        [{"cnt": 500}],
        [{"cnt": 20}],
        [{"category": "credential_access", "alert_type": None, "n": 200}],
        [{"category": "credential_access", "verified": 1723, "overrides": 50}],
    ]
    with patch("app.routers.soc.neo4j_client", mock_high):
        content_high = _run(_tab1_content())

    insight_high = content_high["top_alert_types"][0]["analyst_insight"]
    assert "YOUR environment" in insight_high, (
        f"credential_access (1723 decisions) must contain 'YOUR environment', got: {insight_high!r}"
    )
    assert "Microsoft Copilot" in insight_high, (
        f"credential_access (1723 decisions) must mention Microsoft Copilot, got: {insight_high!r}"
    )


# ---------------------------------------------------------------------------
# Test 15 — FIX 2 v2: Tab 5 centroid_summary uses business language
# ---------------------------------------------------------------------------

def test_tab5_centroid_summary_business_language():
    """centroid_summary must not contain 'centered near prior' — business translation required."""
    from app.routers.soc import _tab5_content
    from app.services.gae_state import init_learning_state

    init_learning_state()

    mock_narrative = {
        "headline": "Test.",
        "what_changed": {"top_shifts": []},
        "what_discovered": {"attack_chains_detected": 0, "chain_summaries": []},
        "what_knows": {
            "iks_current": 65.0,
            "categories_calibrated": 4,
            "health_status": "GREEN",
        },
    }

    mock_client = AsyncMock()
    mock_client.run_query.return_value = [{"cnt": 0}]

    with patch(
        "app.services.executive_narrative.build_executive_narrative_async",
        new=AsyncMock(return_value=mock_narrative),
    ):
        with patch("app.routers.soc.neo4j_client", mock_client):
            content = _run(_tab5_content())

    summary = content["what_system_knows"]["centroid_summary"]
    assert "centered near prior" not in summary, (
        f"centroid_summary must not contain 'centered near prior', got: {summary!r}"
    )
    assert "institutional" in summary or "calibrated" in summary, (
        f"centroid_summary must use business language, got: {summary!r}"
    )
