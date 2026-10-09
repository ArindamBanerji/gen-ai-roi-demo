"""SS-09 regression tests for SOC router outage metadata."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import numpy as np
import pytest

from app.domains.soc import config as soc_config
from app.routers import soc


def run(awaitable):
    return asyncio.run(awaitable)


def failing_graph(monkeypatch):
    graph = AsyncMock()
    graph.run_query.side_effect = RuntimeError("graph unavailable")
    monkeypatch.setattr(soc, "graph_client", graph)
    return graph


def test_tab1_marks_failed_reads(monkeypatch):
    failing_graph(monkeypatch)
    result = run(soc._tab1_content())
    assert {"alert_count", "pending_count", "top_alert_types"} <= set(result["degraded_fields"])
    assert result["data_available"] is False
    assert isinstance(result["top_alert_types"], list)


def test_tab2_marks_iks_and_counts_unavailable(monkeypatch):
    failing_graph(monkeypatch)
    import app.services.iks as iks
    monkeypatch.setattr(iks, "compute_visible_iks", AsyncMock(side_effect=RuntimeError("iks down")))
    monkeypatch.setattr(iks, "compute_iks_v2", AsyncMock(side_effect=RuntimeError("iks down")))
    result = run(soc._tab2_content())
    assert result["data_available"] is False
    assert "iks_score" in result["degraded_fields"]


def test_tab3_marks_graph_reads_unavailable(monkeypatch):
    failing_graph(monkeypatch)
    monkeypatch.setattr(soc, "_get_baseline_scorer", lambda: (_ for _ in ()).throw(RuntimeError("baseline down")))
    result = run(soc._tab3_content())
    assert result["data_available"] is False
    assert "graph_node_count" in result["degraded_fields"]
    assert isinstance(result["factor_names"], list)


def test_tab4_marks_failed_counts_and_preserves_types(monkeypatch):
    failing_graph(monkeypatch)
    result = run(soc._tab4_content())
    assert result["data_available"] is False
    assert "decisions_per_day" in result["degraded_fields"]
    assert isinstance(result["learning_events_count"], int)


def test_tab5_marks_iks_and_flywheel_unavailable(monkeypatch):
    failing_graph(monkeypatch)
    import app.services.executive_narrative as narrative
    import app.services.iks as iks
    monkeypatch.setattr(narrative, "build_executive_narrative_async", AsyncMock(return_value={
        "sections_degraded": ["campaigns_detected"],
        "what_changed": {},
        "what_discovered": {},
        "what_knows": {},
    }))
    monkeypatch.setattr(iks, "compute_visible_iks", AsyncMock(side_effect=RuntimeError("iks down")))
    result = run(soc._tab5_content())
    assert result["data_available"] is False
    assert "flywheel_edge_count" in result["degraded_fields"]
    assert "narrative.campaigns_detected" in result["degraded_fields"]
    assert result["degraded_fields"].count("narrative.campaigns_detected") == 1
    assert result["degraded"] is True


def test_tab5_successful_local_does_not_erase_narrative_failure(monkeypatch):
    import app.services.executive_narrative as narrative
    import app.services.iks as iks
    import app.services.gae_state as gae_state

    monkeypatch.setattr(narrative, "build_executive_narrative_async", AsyncMock(return_value={
        "headline": "Partial narrative",
        "sections": [],
        "sections_degraded": ["what_discovered"],
        "what_changed": {"total_verified": 1, "top_shifts": []},
        "what_discovered": {"attack_chains_detected": 0, "chain_summaries": []},
        "what_knows": {"iks_current": 1.0, "health_status": "GREEN", "learning_enabled": True},
    }))
    monkeypatch.setattr(iks, "compute_visible_iks", AsyncMock(return_value=1.0))
    monkeypatch.setattr(gae_state, "get_profile_scorer", lambda: None)
    monkeypatch.setattr(
        soc,
        "graph_client",
        SimpleNamespace(run_query=AsyncMock(return_value=[{"cnt": 1}])),
    )
    result = run(soc._tab5_content())
    assert result["sections_degraded"] == ["what_discovered"]
    assert result["degraded_fields"] == ["narrative.what_discovered"]
    assert result["data_available"] is False
    assert result["degraded"] is True


def test_query_soc_metrics_identifies_fallback(monkeypatch):
    failing_graph(monkeypatch)
    result = run(soc.query_soc_metrics(soc.SOCQueryRequest(question="threat intel coverage")))
    assert result["source"] == "fallback"
    assert result["degraded"] is True


def test_detection_engineering_and_tactic_breakdown_degraded(monkeypatch):
    failing_graph(monkeypatch)
    detection = run(soc.get_detection_engineering())
    tactics = run(soc.get_attack_tactic_breakdown())
    assert detection["degraded"] is True
    assert detection["data_available"] is False
    assert tactics["degraded"] is True
    assert tactics["breakdown"] == []


def test_learning_state_degraded(monkeypatch):
    failing_graph(monkeypatch)
    import app.services.iks as iks
    monkeypatch.setattr(iks, "compute_iks_v2", AsyncMock(side_effect=RuntimeError("iks down")))
    result = run(soc.get_learning_state_endpoint())
    assert result["degraded"] is True
    assert result["data_available"] is False


def test_explain_does_not_use_default_threat_source(monkeypatch):
    graph = AsyncMock()
    graph.run_query.side_effect = [
        [{"factor_vector": [0.5] * 6, "category": "malware_execution", "action": "investigate", "confidence": 0.8}],
        [{"cnt": 1}],
        RuntimeError("threat intel unavailable"),
    ]
    monkeypatch.setattr(soc, "graph_client", graph)
    result = run(soc.explain_decision("d-1"))
    assert result["source"] == "unavailable"
    assert result["degraded"] is True


def test_benchmarking_reports_unavailable_on_overall_failure(monkeypatch):
    failing_graph(monkeypatch)
    result = run(soc.get_analyst_benchmarking())
    assert result["status"] == "unavailable"
    assert result["data_available"] is False
    assert result["degraded"] is True


def test_enrichment_advisor_reports_unavailable_coverage(monkeypatch):
    failing_graph(monkeypatch)
    result = run(soc.get_enrichment_advisor())
    assert result["data_source"] == "unavailable"
    assert result["degraded"] is True


def test_analyst_weights_reports_missing_decision_counts(monkeypatch):
    failing_graph(monkeypatch)
    import app.services.learning_health as health
    import app.services.gae_state as gae_state
    monkeypatch.setattr(health, "compute_analyst_precision", AsyncMock(return_value={}))
    monkeypatch.setattr(gae_state, "get_learning_state", lambda: SimpleNamespace(decision_count=0))
    result = run(soc.get_analyst_weights())
    assert result["degraded"] is True
    assert result["data_source"] == "unavailable"


def test_centroid_export_unavailable_returns_zero_iks(monkeypatch):
    import app.services.gae_state as gae_state
    import app.services.iks as iks
    scorer = SimpleNamespace(centroids=np.zeros((soc_config.N_CATEGORIES, soc_config.N_ACTIONS, soc_config.N_FACTORS)))
    monkeypatch.setattr(gae_state, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(gae_state, "build_centroid_export", AsyncMock(return_value={
        "categories": list(soc_config.SOC_CATEGORIES),
        "actions": list(soc_config.SCORER_ACTIONS),
        "current_mu": np.zeros((soc_config.N_CATEGORIES, soc_config.N_ACTIONS, soc_config.N_FACTORS)),
        "bootstrap_mu": None,
        "generated_at_epoch": 1,
    }))
    monkeypatch.setattr(iks, "compute_iks_v2", AsyncMock(side_effect=RuntimeError("iks unavailable")))
    result = run(soc.get_centroid_export())
    assert result["iks_score"] == 0.0
    assert result["iks_available"] is False
    assert result["degraded"] is True
    assert result["centroids"][soc_config.SOC_CATEGORIES[0]][soc_config.SCORER_ACTIONS[0]] == [0.0] * soc_config.N_FACTORS
