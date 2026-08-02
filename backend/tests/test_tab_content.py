"""
Step 11.1 -- Tab content export endpoint tests.
All tests mock graph_client and service functions -- no live Neo4j required.
"""
import asyncio
import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from copilot_sdk.graph.memory_store import InMemoryGraphStore
from copilot_sdk.scoring.scorer import CompoundingScorer

client = TestClient(app)


@pytest.fixture(autouse=True)
def _test_profile_for_in_memory_scorers(monkeypatch):
    original = CompoundingScorer.from_preset

    def from_preset(*args, **kwargs):
        kwargs.setdefault("profile", "test")
        return original(*args, **kwargs)

    monkeypatch.setattr(CompoundingScorer, "from_preset", from_preset)


@pytest.fixture(autouse=True)
def _isolated_scorer_graph(monkeypatch):
    """Keep tab-content unit tests independent of live AGE configuration.

    B1 correctly makes the production scorer AGE-backed and fail-closed. These
    endpoint contract tests exercise response shaping, so their scorer must be
    an explicitly injected in-memory store rather than whichever DSN the full
    suite or host environment happens to expose.
    """
    from copilot_sdk.config import GraphConfig
    from copilot_sdk.graph import factory as graph_factory

    monkeypatch.setattr(
        GraphConfig,
        "load",
        lambda _domain: SimpleNamespace(
            backend="sqlite",
            dsn=None,
            graph="test_graph",
            authorized="soc:test_graph",
        ),
    )
    monkeypatch.setattr(
        graph_factory,
        "create_graph_store",
        lambda **_kwargs: InMemoryGraphStore(domain="soc"),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _neo4j_tab1_mock():
    """Mock graph_client.run_query for Tab 1 queries."""
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
    with patch("app.routers.soc.graph_client", mock_client):
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
        "sections": [
            {"title": "System Health", "content": "System is healthy."},
            {"title": "What the System Has Learned", "content": "Learning summary."},
            {"title": "Recommendations", "content": "Recommendation summary.", "items": []},
        ],
    }

    mock_client_t2 = AsyncMock()
    mock_client_t2.run_query.return_value = [{"cnt": 0}]

    with patch(
        "app.services.executive_narrative.build_executive_narrative_async",
        new=AsyncMock(return_value=mock_narrative),
    ):
        with patch("app.routers.soc.graph_client", mock_client_t2):
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


def test_tab5_content_includes_sections():
    """Tab 5 content passes through executive narrative sections."""
    from app.routers.soc import _tab5_content

    mock_sections = [
        {"title": "System Health", "content": "System is healthy."},
        {"title": "What the System Has Learned", "content": "Learning summary."},
        {"title": "Recommendations", "content": "Recommendation summary.", "items": []},
    ]
    mock_narrative = {
        "headline": "System processed 500 alerts, learned from 120 decisions.",
        "what_changed": {"total_verified": 120, "top_shifts": []},
        "what_discovered": {"attack_chains_detected": 0, "chain_summaries": []},
        "what_knows": {"iks_current": 62.5, "health_status": "GREEN"},
        "metrics": {
            "alerts_total": 500,
            "decisions_verified": 120,
            "campaigns_detected": 4,
            "iks_current": 62.5,
        },
        "generated_at": "2026-04-04T10:00:00Z",
        "pdf_available": True,
        "sections": mock_sections,
    }

    mock_client_t2 = AsyncMock()
    mock_client_t2.run_query.return_value = [{"cnt": 0}]

    with patch(
        "app.services.executive_narrative.build_executive_narrative_async",
        new=AsyncMock(return_value=mock_narrative),
    ):
        with patch("app.routers.soc.graph_client", mock_client_t2):
            content = _run(_tab5_content())

    assert "sections" in content
    assert content["sections"] == mock_sections
    assert [section["title"] for section in content["sections"]] == [
        "System Health",
        "What the System Has Learned",
        "Recommendations",
    ]


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
        "interpretation": "Calibrated -- model has sufficient training signal",
        "components": {"trust_coverage": 50.0},
        "total_decisions": 537,
    }

    mock_client = AsyncMock()
    mock_client.run_query.return_value = [{"cnt": 12}]

    with patch("app.services.iks.compute_iks_v2", new=AsyncMock(return_value=mock_iks)):
        with patch("app.routers.soc.graph_client", mock_client):
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
        [],                # no pending alert -> centroid fallback
    ]

    with patch("app.routers.soc.graph_client", mock_client):
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
            "threat_intel_enrichment (sigma=0.07) must have the highest kernel weight"
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

    with patch("app.routers.soc.graph_client", mock_client):
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
        with patch("app.routers.soc.graph_client", mock_client):
            content = _run(_tab5_content())

    wsk = content["what_system_knows"]
    assert "flywheel_claim"      in wsk, "Missing flywheel_claim (FIX 2.8)"
    assert "flywheel_message"    in wsk, "Missing flywheel_message (FIX 2.8)"
    assert "flywheel_status"     in wsk, "Missing flywheel_status (FIX 2.8)"
    assert "flywheel_edge_count" in wsk, "Missing flywheel_edge_count (FIX 2.8)"

    assert "+10.13pp" in wsk["flywheel_claim"], "flywheel_claim must contain validated stat"
    assert wsk["flywheel_status"]     == "active", "50 edges -> status must be 'active'"
    assert wsk["flywheel_edge_count"] == 50,        "edge count must match mock"
    assert "50" in wsk["flywheel_message"],          "flywheel_message must reference edge count"

    # Case B: 0 edges → pre_activation
    mock_client_cold = AsyncMock()
    mock_client_cold.run_query.return_value = [{"cnt": 0}]

    with patch(
        "app.services.executive_narrative.build_executive_narrative_async",
        new=AsyncMock(return_value=mock_narrative),
    ):
        with patch("app.routers.soc.graph_client", mock_client_cold):
            content_cold = _run(_tab5_content())

    wsk_cold = content_cold["what_system_knows"]
    assert wsk_cold["flywheel_status"]     == "pre_activation", "0 edges -> pre_activation"
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
            with patch("app.routers.soc.graph_client", mock_client):
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


def test_tab5_pre_activation_conservation_narrative():
    from app.routers.soc import _tab5_content

    mock_narrative = {
        "headline": "Test.",
        "what_changed": {"top_shifts": [], "total_verified": 100},
        "what_discovered": {"attack_chains_detected": 0, "chain_summaries": []},
        "what_knows": {
            "iks_current": 75.0,
            "categories_calibrated": 6,
            "health_status": "CALIBRATING",
            "operational_knowledge_status": "GREEN",
            "pre_activation": True,
            "learning_enabled": False,
            "health_source": "learning_health_pre_activation",
            "status_reason": "learning_disabled_no_live_history",
        },
    }

    mock_client = AsyncMock()
    mock_client.run_query.return_value = [{"cnt": 0}]

    with patch(
        "app.services.executive_narrative.build_executive_narrative_async",
        new=AsyncMock(return_value=mock_narrative),
    ):
        with patch("app.routers.soc.graph_client", mock_client):
            content = _run(_tab5_content())

    wsk = content["what_system_knows"]
    narrative = wsk["conservation_narrative"]
    assert wsk["health_status"] == "CALIBRATING"
    assert wsk["pre_activation"] is True
    assert "Pre-activation" in narrative
    assert "Evidence Ledger" in narrative
    assert "EU AI Act Art. 13" in narrative or "Art. 13" in narrative
    assert "Conservation" in narrative
    assert "degraded" not in narrative.lower()
    assert "breached" not in narrative.lower()


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
        [                                                        # top alert types -- raw values
            {"category": "anomalous_login",  "alert_type": None, "n": 80},
            {"category": "malware_execution", "alert_type": None, "n": 60},
            {"category": "data_exfil",       "alert_type": "data_exfiltration", "n": 40},
        ],
        [],                                                      # per-category verified (empty ok)
    ]

    with patch("app.routers.soc.graph_client", mock_client):
        content = _run(_tab1_content())

    types = [t["type"] for t in content["top_alert_types"]]
    assert len(types) > 0, "top_alert_types must not be empty"
    for t in types:
        assert t in VALID_CATEGORIES, (
            f"alert type {t!r} is not in VALID_CATEGORIES -- normalization failed"
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
        with patch("app.routers.soc.graph_client", mock_client):
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
    with patch("app.routers.soc.graph_client", mock_with_decisions):
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
    with patch("app.routers.soc.graph_client", mock_no_decisions):
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

    with patch("app.routers.soc.graph_client", mock_client):
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
        with patch("app.routers.soc.graph_client", mock_client):
            content = _run(_tab5_content())

    wsk = content["what_system_knows"]

    assert wsk["flywheel_status"] == "pre_activation", (
        "0 edges -> flywheel_status must be 'pre_activation'"
    )
    assert "pre-activation" in wsk["flywheel_message"], (
        f"flywheel_message must mention 'pre-activation', got: {wsk['flywheel_message']!r}"
    )
    assert "p=0.0002" not in wsk["flywheel_message"], (
        f"flywheel_message must not contain technical stats, got: {wsk['flywheel_message']!r}"
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
    """Microsoft Copilot comparison appears only for categories with >=100 verified decisions."""
    from app.routers.soc import _tab1_content

    # malware_execution with 12 decisions — must NOT mention Microsoft Copilot
    mock_low = AsyncMock()
    mock_low.run_query.side_effect = [
        [{"cnt": 500}],
        [{"cnt": 20}],
        [{"category": "malware_execution", "alert_type": None, "n": 30}],
        [{"category": "malware_execution", "verified": 12, "overrides": 1}],
    ]
    with patch("app.routers.soc.graph_client", mock_low):
        content_low = _run(_tab1_content())

    insight_low = content_low["top_alert_types"][0]["analyst_insight"]
    assert "Microsoft Copilot" not in insight_low, (
        f"malware_execution (12 decisions) must NOT mention Microsoft Copilot, got: {insight_low!r}"
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
    with patch("app.routers.soc.graph_client", mock_high):
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
    """centroid_summary must not contain 'centered near prior' -- business translation required."""
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
        with patch("app.routers.soc.graph_client", mock_client):
            content = _run(_tab5_content())

    summary = content["what_system_knows"]["centroid_summary"]
    assert "centered near prior" not in summary, (
        f"centroid_summary must not contain 'centered near prior', got: {summary!r}"
    )
    assert "institutional" in summary or "calibrated" in summary, (
        f"centroid_summary must use business language, got: {summary!r}"
    )


# ---------------------------------------------------------------------------
# Test 16 — FIX 3A: Tab 3 recommendation has rationale field
# ---------------------------------------------------------------------------

def test_tab3_recommendation_has_rationale():
    """recommendation must include 'rationale' with override_rate and action."""
    from app.routers.soc import _tab3_content
    from app.services.gae_state import init_learning_state

    init_learning_state()

    mock_client = AsyncMock()
    mock_client.run_query.side_effect = [
        [{"cnt": 5000}],   # graph node count
        [],                # no pending alert -> centroid fallback
        [],                # override rate query -> falls back to 15.0
    ]

    with patch("app.routers.soc.graph_client", mock_client):
        content = _run(_tab3_content())

    rec = content["recommendation"]
    assert "rationale" in rec, "recommendation must include 'rationale' field (FIX 3A)"
    rationale = rec["rationale"]
    assert isinstance(rationale, str) and rationale, "rationale must be a non-empty string"
    assert "threat intel enrichment" in rationale.lower(), (
        f"rationale must mention threat intel enrichment, got: {rationale!r}"
    )
    assert "%" in rationale, (
        f"rationale must include override_rate percentage, got: {rationale!r}"
    )


# ---------------------------------------------------------------------------
# Test 17 — FIX 3B: Tab 5 flywheel_message is plain English (no stats)
# ---------------------------------------------------------------------------

def test_tab5_flywheel_message_plain_english():
    """flywheel_message must not contain 'p=0.0002' or 'CLAIM-W2' (moved to flywheel_detail)."""
    from app.routers.soc import _tab5_content

    mock_narrative = {
        "headline": "Test.",
        "what_changed": {"top_shifts": []},
        "what_discovered": {"attack_chains_detected": 0, "chain_summaries": []},
        "what_knows": {"iks_current": 65.0, "categories_calibrated": 4, "health_status": "GREEN"},
    }

    mock_client = AsyncMock()
    mock_client.run_query.return_value = [{"cnt": 0}]

    with patch(
        "app.services.executive_narrative.build_executive_narrative_async",
        new=AsyncMock(return_value=mock_narrative),
    ):
        with patch("app.routers.soc.graph_client", mock_client):
            content = _run(_tab5_content())

    wsk = content["what_system_knows"]
    msg = wsk["flywheel_message"]
    assert "p=0.0002" not in msg, (
        f"flywheel_message must not contain 'p=0.0002' (belongs in flywheel_detail), got: {msg!r}"
    )
    assert "CLAIM-W2" not in msg, (
        f"flywheel_message must not contain 'CLAIM-W2', got: {msg!r}"
    )


# ---------------------------------------------------------------------------
# Test 18 — FIX 3B: Tab 5 flywheel_detail has technical detail
# ---------------------------------------------------------------------------

def test_tab5_flywheel_detail_has_technical():
    """flywheel_detail must contain 'p=0.0002' and 'CLAIM-W2'."""
    from app.routers.soc import _tab5_content

    mock_narrative = {
        "headline": "Test.",
        "what_changed": {"top_shifts": []},
        "what_discovered": {"attack_chains_detected": 0, "chain_summaries": []},
        "what_knows": {"iks_current": 65.0, "categories_calibrated": 4, "health_status": "GREEN"},
    }

    mock_client = AsyncMock()
    mock_client.run_query.return_value = [{"cnt": 0}]

    with patch(
        "app.services.executive_narrative.build_executive_narrative_async",
        new=AsyncMock(return_value=mock_narrative),
    ):
        with patch("app.routers.soc.graph_client", mock_client):
            content = _run(_tab5_content())

    wsk = content["what_system_knows"]
    assert "flywheel_detail" in wsk, "flywheel_detail must be present in what_system_knows"
    detail = wsk["flywheel_detail"]
    assert "p=0.0002" in detail, (
        f"flywheel_detail must contain 'p=0.0002', got: {detail!r}"
    )
    assert "CLAIM-W2" in detail, (
        f"flywheel_detail must contain 'CLAIM-W2', got: {detail!r}"
    )


# ---------------------------------------------------------------------------
# Test 19 — FIX 3B addition: Tab 5 what_discovered has mechanism field
# ---------------------------------------------------------------------------

def test_tab5_what_discovered_has_mechanism():
    """what_discovered must include 'mechanism' with plain-English explanation."""
    from app.routers.soc import _tab5_content

    mock_narrative = {
        "headline": "Test.",
        "what_changed": {"top_shifts": []},
        "what_discovered": {"attack_chains_detected": 3, "chain_summaries": ["A", "B"]},
        "what_knows": {"iks_current": 65.0, "categories_calibrated": 4, "health_status": "GREEN"},
    }

    mock_client = AsyncMock()
    mock_client.run_query.return_value = [{"cnt": 0}]

    with patch(
        "app.services.executive_narrative.build_executive_narrative_async",
        new=AsyncMock(return_value=mock_narrative),
    ):
        with patch("app.routers.soc.graph_client", mock_client):
            content = _run(_tab5_content())

    wd = content["what_discovered"]
    assert "mechanism" in wd, "what_discovered must include 'mechanism' field (FIX 3B addition)"
    mech = wd["mechanism"]
    assert isinstance(mech, str) and mech, "mechanism must be a non-empty string"
    assert "graph" in mech.lower() or "campaign" in mech.lower(), (
        f"mechanism must mention graph/campaign context, got: {mech!r}"
    )
    assert "3" in mech, (
        f"mechanism must include campaign_count=3, got: {mech!r}"
    )


# ---------------------------------------------------------------------------
# Test 20 — FIX 3C: Tab 2 has calibration_note
# ---------------------------------------------------------------------------

def test_tab2_has_calibration_note():
    """Tab 2 content must include calibration_note (FIX 3C)."""
    from app.routers.soc import _tab2_content

    mock_iks = {
        "iks_v2": 71.0,
        "interpretation": "Calibrated",
        "components": {"trust_coverage": 50.0},
        "total_decisions": 537,
    }

    mock_client = AsyncMock()
    mock_client.run_query.return_value = [{"cnt": 12}]

    with patch("app.services.iks.compute_iks_v2", new=AsyncMock(return_value=mock_iks)):
        with patch("app.routers.soc.graph_client", mock_client):
            content = _run(_tab2_content())

    assert "calibration_note" in content, "Missing calibration_note (FIX 3C)"
    note = content["calibration_note"]
    assert isinstance(note, str) and note, "calibration_note must be a non-empty string"
    assert "Innovation #9" in note, (
        f"calibration_note must cite Innovation #9, got: {note!r}"
    )
    assert "manual configuration" in note, (
        f"calibration_note must mention no manual configuration, got: {note!r}"
    )


# ===========================================================================
# Phase A Tier 1 — permanent contract gate for all 15 Tier 1 commercial claims
# Uses live TestClient (no mocks) — validates actual endpoint responses.
# ===========================================================================

VALID_CATEGORIES = {
    "credential_access", "malware_execution", "lateral_movement",
    "data_exfiltration", "insider_threat", "cloud_infrastructure",
}

# ---------------------------------------------------------------------------
# TAB 1 TIER 1 TESTS
# ---------------------------------------------------------------------------

def test_tab1_alert_types_are_valid_categories_live():
    """No raw Sentinel strings or 'unknown' in top_alert_types."""
    resp = client.get("/api/soc/tab/1/content")
    assert resp.status_code == 200
    for alert in resp.json()["content"]["top_alert_types"]:
        assert alert["type"] in VALID_CATEGORIES, \
            f"Invalid category found: {alert['type']}"


def test_tab1_microsoft_comparison_only_above_threshold_live():
    """If Microsoft comparison appears, 'YOUR environment' must also appear (same branch)."""
    resp = client.get("/api/soc/tab/1/content")
    for alert in resp.json()["content"]["top_alert_types"]:
        insight = alert.get("analyst_insight", "")
        if "Microsoft" in insight:
            assert "YOUR environment" in insight, (
                f"Microsoft comparison present but 'YOUR environment' missing "
                f"for {alert['type']}: {insight!r}"
            )


def test_tab1_learning_signal_present_per_category_live():
    """Every alert type has a non-empty learning_signal."""
    resp = client.get("/api/soc/tab/1/content")
    for alert in resp.json()["content"]["top_alert_types"]:
        assert "learning_signal" in alert
        assert len(alert["learning_signal"]) > 10


def test_tab1_analyst_insight_present_live():
    """Every alert type has an analyst_insight field."""
    resp = client.get("/api/soc/tab/1/content")
    for alert in resp.json()["content"]["top_alert_types"]:
        assert "analyst_insight" in alert
        assert len(alert["analyst_insight"]) > 10


# ---------------------------------------------------------------------------
# TAB 2 TIER 1 TESTS
# ---------------------------------------------------------------------------

def test_tab2_trust_coverage_has_trajectory_live():
    """trust_coverage_summary contains 80%+ and day 270."""
    content = client.get("/api/soc/tab/2/content").json()["content"]
    assert "80%+" in content["trust_coverage_summary"]
    assert "day 270" in content["trust_coverage_summary"]


def test_tab2_calibration_note_present_live():
    """calibration_note present and references self-calibrate."""
    content = client.get("/api/soc/tab/2/content").json()["content"]
    assert "calibration_note" in content
    assert "self-calibrate" in content["calibration_note"].lower() \
        or "self-calibrating" in content["calibration_note"].lower()


def test_tab2_decision_glossary_has_three_keys_live():
    """decision_count_glossary has all 3 required keys."""
    content = client.get("/api/soc/tab/2/content").json()["content"]
    glossary = content["decision_count_glossary"]
    assert "verified_decisions" in glossary
    assert "switching_cost_threshold" in glossary
    assert "override_examples" in glossary


def test_tab2_drift_summary_has_percentage_live():
    """drift_alert_summary includes a percentage."""
    content = client.get("/api/soc/tab/2/content").json()["content"]
    assert "%" in content["drift_alert_summary"]


def test_tab2_iks_score_present_and_positive_live():
    """IKS score is present and > 0."""
    content = client.get("/api/soc/tab/2/content").json()["content"]
    assert content["iks_score"] > 0


# ---------------------------------------------------------------------------
# TAB 3 TIER 1 TESTS
# ---------------------------------------------------------------------------

def test_tab3_kernel_note_names_diagonalkernel_live():
    """kernel_note explicitly names DiagonalKernel."""
    content = client.get("/api/soc/tab/3/content").json()["content"]
    assert "DiagonalKernel" in content["kernel_note"]


def test_tab3_recommendation_has_rationale_live():
    """recommendation block has a rationale field."""
    content = client.get("/api/soc/tab/3/content").json()["content"]
    rec = content["recommendation"]
    assert "rationale" in rec
    assert len(rec["rationale"]) > 20


def test_tab3_recommendation_action_is_valid_live():
    """recommendation action is a valid SOC action."""
    content = client.get("/api/soc/tab/3/content").json()["content"]
    valid_actions = {"escalate", "investigate", "suppress", "monitor"}
    assert content["recommendation"]["action"] in valid_actions


def test_tab3_factor_breakdown_has_six_factors_live():
    """factor_breakdown has exactly 6 factors."""
    content = client.get("/api/soc/tab/3/content").json()["content"]
    assert len(content["factor_breakdown"]) == 6


def test_tab3_each_factor_has_sigma_and_weight_live():
    """Each factor has sigma, kernel_weight, and interpretation."""
    content = client.get("/api/soc/tab/3/content").json()["content"]
    for factor in content["factor_breakdown"]:
        assert "sigma" in factor, f"Missing sigma for {factor['name']}"
        assert "kernel_weight" in factor
        assert "interpretation" in factor


def test_tab3_graph_context_present_live():
    """graph_context field is present and non-empty."""
    content = client.get("/api/soc/tab/3/content").json()["content"]
    assert "graph_context" in content
    assert len(content["graph_context"]) > 20


# ---------------------------------------------------------------------------
# TAB 4 TIER 1 TESTS
# ---------------------------------------------------------------------------

def test_tab4_roi_methodology_has_calculation_live():
    """roi_methodology has a calculation string."""
    content = client.get("/api/soc/tab/4/content").json()["content"]
    assert "calculation" in content["roi_methodology"]
    calc = content["roi_methodology"]["calculation"]
    assert "annually" in calc.lower()


def test_tab4_roi_methodology_has_source_live():
    """roi_methodology cites SANS or Hackett."""
    content = client.get("/api/soc/tab/4/content").json()["content"]
    source = content["roi_methodology"].get("source", "")
    assert "SANS" in source or "Hackett" in source


def test_tab4_switching_cost_has_iks_reset_live():
    """switching_cost_dollars narrative mentions IKS resets."""
    content = client.get("/api/soc/tab/4/content").json()["content"]
    narrative = content["switching_cost_dollars"]["narrative"]
    assert "IKS resets" in narrative or "resets to zero" in narrative


def test_tab4_switching_cost_has_dollar_amount_live():
    """switching_cost_dollars has a cost_usd > 0."""
    content = client.get("/api/soc/tab/4/content").json()["content"]
    assert content["switching_cost_dollars"]["cost_usd"] > 0


def test_tab4_decisions_per_day_positive_live():
    """decisions_per_day is positive."""
    content = client.get("/api/soc/tab/4/content").json()["content"]
    assert content["decisions_per_day"] > 0


# ---------------------------------------------------------------------------
# TAB 5 TIER 1 TESTS
# ---------------------------------------------------------------------------

def test_tab5_flywheel_message_jargon_free_live():
    """flywheel_message has no p-values, CLAIM codes, or tensor notation."""
    content = client.get("/api/soc/tab/5/content").json()["content"]
    msg = content["what_system_knows"]["flywheel_message"]
    assert "p=0.000" not in msg, "p-value in flywheel_message"
    assert "CLAIM-" not in msg, "CLAIM code in flywheel_message"
    assert "tensor" not in msg.lower(), "tensor in flywheel_message"


def test_tab5_flywheel_detail_has_technical_live():
    """flywheel_detail (separate field) has the technical content."""
    content = client.get("/api/soc/tab/5/content").json()["content"]
    knows = content["what_system_knows"]
    assert "flywheel_detail" in knows or "flywheel_claim" in knows


def test_tab5_conservation_has_claim_ols01_live():
    """conservation_narrative cites CLAIM-OLS-01."""
    content = client.get("/api/soc/tab/5/content").json()["content"]
    narrative = content["what_system_knows"]["conservation_narrative"]
    assert "CLAIM-OLS-01" in narrative


def test_tab5_conservation_has_zero_percent_live():
    """conservation_narrative cites 0% miss rate."""
    content = client.get("/api/soc/tab/5/content").json()["content"]
    narrative = content["what_system_knows"]["conservation_narrative"]
    assert "0%" in narrative


def test_tab5_what_discovered_has_mechanism_live():
    """what_discovered has a mechanism field."""
    content = client.get("/api/soc/tab/5/content").json()["content"]
    assert "mechanism" in content["what_discovered"]
    assert len(content["what_discovered"]["mechanism"]) > 20


def test_tab5_headline_has_verified_decisions_live():
    """Tab 5 headline mentions verified decisions."""
    content = client.get("/api/soc/tab/5/content").json()["content"]
    assert "verified decisions" in content["headline"].lower()


def test_tab5_iks_positive_live():
    """IKS in Tab 5 what_system_knows is positive."""
    content = client.get("/api/soc/tab/5/content").json()["content"]
    assert content["what_system_knows"]["iks"] > 0


# ===========================================================================
# Phase A Tier 2 — GraphSnapshot structural consistency tests
# BACKLOG-020 Phase 7: cross-tab divergence is now structurally impossible
# (both tabs read from the same GraphSnapshot). Tests replaced with:
#   1. Snapshot populated on startup (non-negative verified count).
#   2. Snapshot survives restart (idempotent from_graph() call).
# ===========================================================================

def test_snapshot_initialized_on_startup():
    """
    GraphSnapshot is populated at startup -- verified_decisions is non-negative.
    Checks that the learning-state endpoint exposes verified_decisions from snapshot.
    """
    resp = client.get("/api/soc/learning-state")
    assert resp.status_code == 200
    data = resp.json()
    assert "verified_decisions" in data
    assert data["verified_decisions"] >= 0


@pytest.mark.asyncio
async def test_restart_does_not_lose_decision_count():
    """
    Simulates restart: two sequential GraphSnapshot.from_graph() calls
    return identical verified_decisions -- restart is idempotent.
    """
    from app.state.graph_snapshot import GraphSnapshot
    from unittest.mock import AsyncMock
    mock_client = AsyncMock()
    mock_client.count_verified_decisions = AsyncMock(return_value=42)
    mock_client.count_decisions_by_category = AsyncMock(return_value={"credential_access": 42})
    mock_client.compute_outcome_stats = AsyncMock(return_value={"override_rate": 0.1, "override_quality": 0.8})
    mock_client.compute_iks = AsyncMock(return_value=76.0)

    snap1 = await GraphSnapshot.from_graph(mock_client)
    snap2 = await GraphSnapshot.from_graph(mock_client)
    assert snap1.verified_decisions == snap2.verified_decisions == 42


def test_iks_consistent_tab2_tab5():
    """IKS score matches between Tab 2 and Tab 5 what_system_knows."""
    t2 = client.get("/api/soc/tab/2/content").json()["content"]
    t5 = client.get("/api/soc/tab/5/content").json()["content"]

    iks_t2 = t2["iks_score"]
    iks_t5 = t5["what_system_knows"]["iks"]

    # Tolerance of 35: catches gross divergence (0 vs 76, or filtered vs unfiltered
    # count bugs) while allowing for minor variation between two independent
    # async compute_iks_v2 calls to the same Neo4j client.
    assert abs(iks_t2 - iks_t5) < 35.0, \
        f"Tab 2 IKS ({iks_t2}) differs from Tab 5 ({iks_t5}) by > 35 -- inconsistent data source"


def test_roi_arithmetic_consistent():
    """roi_annual_usd field matches the calculation string within 5%."""
    import re
    content = client.get("/api/soc/tab/4/content").json()["content"]
    roi_field = content["roi_annual_usd"]
    calc = content["roi_methodology"]["calculation"]

    match = re.search(r'\$([\d,]+)\s+annually', calc)
    if match:
        roi_calc = int(match.group(1).replace(",", ""))
        pct_diff = abs(roi_field - roi_calc) / roi_field
        assert pct_diff < 0.05, \
            f"ROI field ({roi_field:,.0f}) differs >5% from " \
            f"calculation string ({roi_calc:,.0f})"


def test_tab4_roi_annual_positive():
    """roi_annual_usd is positive."""
    content = client.get("/api/soc/tab/4/content").json()["content"]
    assert content["roi_annual_usd"] > 0


def test_tab3_recommendation_confidence_range():
    """recommendation confidence is between 0 and 1."""
    content = client.get("/api/soc/tab/3/content").json()["content"]
    conf = content["recommendation"]["confidence"]
    assert 0.0 < conf <= 1.0, f"Confidence {conf} out of range"


def test_tab2_iks_matches_interpretation():
    """IKS interpretation string is non-empty."""
    content = client.get("/api/soc/tab/2/content").json()["content"]
    assert "iks_interpretation" in content
    assert len(content["iks_interpretation"]) > 5


def test_tab5_categories_calibrated_max_six():
    """categories_calibrated must be <= 6 (BACKLOG-007: 'unknown' exclusion)."""
    content = client.get("/api/soc/tab/5/content").json()["content"]
    knows = content["what_system_knows"]
    assert knows["categories_calibrated"] <= 6, \
        f"categories_calibrated={knows['categories_calibrated']} > 6"


def test_tab2_noise_map_not_cold_start_at_high_decisions():
    """Noise map should not show cold-start message at 8k+ decisions (BACKLOG-003)."""
    content = client.get("/api/soc/tab/2/content").json()["content"]
    glossary = content["decision_count_glossary"]
    raw = glossary["verified_decisions"]
    count = int(raw.split()[0].replace(",", ""))
    if count >= 100:
        # If noise_map field exists, it should not show cold-start message
        noise = content.get("noise_map", {})
        for category, data in noise.items():
            assert "needs 10+" not in str(data), \
                f"Noise map cold-start message despite {count} decisions"


# ---------------------------------------------------------------------------
# Test 57 — BACKLOG-004: Tab 2 IKS reflects drift-based formula (≥ 67 at phase 3)
# ---------------------------------------------------------------------------

def test_tab2_iks_reflects_decision_volume():
    """
    BACKLOG-004: Tab 2 iks_score must use the centroid-drift IKS formula.
    At phase 3 calibration (>=537 decisions, formal switching cost plateau),
    IKS must be >= 67 -- the threshold where switching cost justifies lock-in.

    If iks_score < 67 despite high decision volume, the composite v2 formula
    is underweighting calibrated centroids due to trust_coverage drag.
    """
    t2 = client.get("/api/soc/tab/2/content").json()["content"]
    iks = t2["iks_score"]
    raw = t2["decision_count_glossary"]["verified_decisions"]
    decisions = int(raw.split()[0].replace(",", ""))

    if decisions >= 537:
        assert iks >= 67.0, (
            f"At {decisions:,} decisions (phase 3+), IKS must be >= 67 "
            f"(switching cost plateau). Got {iks:.1f} -- likely using composite v2 "
            "instead of drift-based formula (BACKLOG-004)."
        )


# ---------------------------------------------------------------------------
# Test 58 — BACKLOG-014: Evidence Ledger in Tab 5 conservation_narrative
# ---------------------------------------------------------------------------

def test_tab5_conservation_has_evidence_ledger():
    content = client.get("/api/soc/tab/5/content").json()["content"]
    narrative = content["what_system_knows"]["conservation_narrative"]
    assert "Evidence Ledger" in narrative
    assert "EU AI Act Art. 13" in narrative


# ---------------------------------------------------------------------------
# Tests 59-60 — Block 3.5: centroid-evolution drift from bootstrap baseline
# ---------------------------------------------------------------------------

def test_centroid_evolution_returns_data():
    """centroid-evolution fails closed when AGE is unavailable."""
    resp = client.get("/api/soc/centroid-evolution")
    assert resp.status_code == 503


def test_centroid_drift_nonzero_at_high_decisions():
    """AGE failures are surfaced as HTTP 503 instead of in-memory fallback data.

    The old test exercised a removed fallback that synthesized drift from the
    in-memory scorer.  The endpoint now fails closed when AGE is unavailable.
    """
    import numpy as np

    # Build a mock scorer whose centroids differ from mu_zero by a known drift.
    n_categories, n_actions, n_factors = 6, 4, 6
    mu_zero_val = np.zeros((n_categories, n_actions, n_factors), dtype=np.float64)
    # Shift category 0 action 0 by 0.10 in factor 0 — drift per category 0 ≈ 0.025
    mu_t_val = mu_zero_val.copy()
    mu_t_val[0, 0, 0] = 0.10

    mock_scorer = MagicMock()
    mock_scorer.centroids = mu_t_val
    mock_scorer.categories = [
        "credential_access", "lateral_movement", "malware_execution",
        "data_exfiltration", "privilege_escalation", "reconnaissance",
    ]
    mock_scorer.actions = ["escalate", "investigate", "suppress", "monitor"]

    mock_learning_state = MagicMock()
    mock_learning_state.decision_count = 8000

    async def _raise(*args, **kwargs):
        raise RuntimeError("forced-fail for fallback test")

    mock_neo4j = AsyncMock()
    mock_neo4j.run_query.side_effect = _raise

    # Imports inside get_centroid_evolution happen at call time, so patch source modules.
    with patch("app.routers.framework_router.graph_client", mock_neo4j), \
         patch("app.services.gae_state.get_profile_scorer", return_value=mock_scorer), \
         patch("app.services.gae_state.get_learning_state", return_value=mock_learning_state), \
         patch("app.services.iks._load_mu_zero", return_value=mu_zero_val):
        local_client = TestClient(app)
        resp = local_client.get("/api/soc/centroid-evolution")

    assert resp.status_code == 503
    assert resp.json()["detail"] == "AGE query failed for centroid evolution"
