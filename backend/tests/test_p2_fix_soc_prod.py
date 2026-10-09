from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domains.soc import orchestrator
from app.framework.composite_gate import CompositeDiscriminant
from app.routers import metrics, soc
from app.services import evidence_room, iks, override_detector, shadow_runner, time_machine
from app.services.variant_generator import CoverageGapRule, GraphSignal, VariantGenerator


@pytest.mark.asyncio
async def test_iks_delta_query_exception_is_unavailable(monkeypatch):
    graph = MagicMock()
    graph.run_query = AsyncMock(side_effect=RuntimeError("graph down"))
    monkeypatch.setattr("app.db.graph_client.graph_client", graph)

    assert await iks._compute_delta_7d(42.0) == (0.0, False)


@pytest.mark.asyncio
async def test_iks_delta_malformed_history_is_unavailable(monkeypatch):
    graph = MagicMock()
    graph.run_query = AsyncMock(return_value=[{"mu": "not-json"}])
    monkeypatch.setattr("app.db.graph_client.graph_client", graph)

    assert await iks._compute_delta_7d(42.0) == (0.0, False)


def test_time_machine_malformed_metadata_is_unavailable():
    assert time_machine._decision_count({"metadata": "bad", "step": 9}) == (0, False)


def test_time_machine_malformed_count_is_unavailable():
    assert time_machine._decision_count({"metadata": {"decision_count": None}}) == (0, False)


@pytest.mark.asyncio
async def test_evidence_room_iks_exception_is_unavailable(monkeypatch):
    health = {"status": "RED", "signal": 0.0, "theta_min": 0.5, "pre_activation": False}
    monkeypatch.setattr("app.services.learning_health.LearningHealthMonitor.evaluate", AsyncMock(return_value=health))
    snapshot = MagicMock(verified_decisions=3)
    monkeypatch.setattr("app.state.graph_snapshot.get_snapshot", MagicMock(return_value=snapshot))
    monkeypatch.setattr("app.services.iks.compute_visible_iks", AsyncMock(side_effect=RuntimeError("down")))

    result = await evidence_room.EvidenceRoomService()._collect_conservation()

    assert result["iks_available"] is False


@pytest.mark.asyncio
async def test_evidence_room_iks_none_is_unavailable(monkeypatch):
    health = {"status": "RED", "signal": 0.0, "theta_min": 0.5, "pre_activation": False}
    monkeypatch.setattr("app.services.learning_health.LearningHealthMonitor.evaluate", AsyncMock(return_value=health))
    snapshot = MagicMock(verified_decisions=3)
    monkeypatch.setattr("app.state.graph_snapshot.get_snapshot", MagicMock(return_value=snapshot))
    monkeypatch.setattr("app.services.iks.compute_visible_iks", AsyncMock(return_value=None))

    result = await evidence_room.EvidenceRoomService()._collect_conservation()

    assert result["iks_available"] is False


@pytest.mark.asyncio
async def test_composite_gate_history_exception_reports_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.framework.composite_gate.DecisionHistoryService.get_category_stats",
        AsyncMock(side_effect=RuntimeError("down")),
    )
    score = MagicMock(
        probabilities=[0.9, 0.05, 0.03, 0.02],
        distances=[0.1, 0.5, 0.6, 0.7],
        action_index=0,
        action_name="escalate",
    )

    result = await CompositeDiscriminant.evaluate(score, "credential_access", [0.5] * 6, 0.0, MagicMock())

    assert result["category_history_available"] is False
    assert "category_history_unavailable" in result["reason_codes"]
    assert not any("maturity gate" in reason for reason in result["reason_codes"])


@pytest.mark.asyncio
async def test_composite_gate_history_none_reports_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.framework.composite_gate.DecisionHistoryService.get_category_stats",
        AsyncMock(return_value=None),
    )
    score = MagicMock(
        probabilities=[0.9, 0.05, 0.03, 0.02],
        distances=[0.1, 0.5, 0.6, 0.7],
        action_index=0,
        action_name="escalate",
    )

    result = await CompositeDiscriminant.evaluate(score, "credential_access", [0.5] * 6, 0.0, MagicMock())

    assert result["category_history_available"] is False
    assert result["auto_approve"] is False


@pytest.mark.asyncio
async def test_variant_coverage_exception_marks_scan_incomplete():
    graph = MagicMock()
    graph.run_query = AsyncMock(side_effect=RuntimeError("down"))

    result = await VariantGenerator(rules=[CoverageGapRule()], registry=MagicMock()).scan_for_opportunities(graph)

    assert result.scan_complete is False
    assert result.rules_failed == [CoverageGapRule.rule_id]


@pytest.mark.asyncio
async def test_variant_none_history_does_not_proceed(monkeypatch):
    rule = MagicMock(rule_id="RULE-HISTORY", last_data_available=True)
    rule.detect = AsyncMock(return_value=GraphSignal("RULE-HISTORY", "trigger", "routing_rule", {}, None, "test"))
    registry = MagicMock()
    registry.has_active_or_shadow.return_value = False
    monkeypatch.setattr("app.services.variant_generator._consult_history", AsyncMock(return_value=None))

    result = await VariantGenerator(rules=[rule], registry=registry).scan_for_opportunities(MagicMock())

    assert result.history_available is False
    assert result.scan_complete is False
    assert list(result) == []


@pytest.mark.asyncio
async def test_orchestrator_query_exception_preserves_unavailable():
    graph = MagicMock()
    graph.run_query = AsyncMock(side_effect=RuntimeError("down"))

    assert await orchestrator._query_has_rows(graph, "RETURN 1") == (False, False)


@pytest.mark.asyncio
async def test_orchestrator_query_none_preserves_unavailable():
    graph = MagicMock()
    graph.run_query = AsyncMock(return_value=None)

    assert await orchestrator._query_has_rows(graph, "RETURN 1") == (False, False)


@pytest.mark.asyncio
async def test_shadow_flush_failure_then_success_stays_failed(monkeypatch):
    monkeypatch.setattr(shadow_runner, "SHADOW_BATCH_SIZE", 1)
    monkeypatch.setattr(shadow_runner, "_shadow_buffer", [
        shadow_runner.ShadowComparison("a", "a1", "cat", "monitor", "escalate", 0.5, "escalate", 1.0),
        shadow_runner.ShadowComparison("b", "b1", "cat", "monitor", "escalate", 0.5, "escalate", 1.0),
    ])
    monkeypatch.setattr(shadow_runner, "flush_failed", False)
    monkeypatch.setattr("app.services.variant_registry.get_variant", MagicMock(return_value=MagicMock(status="shadow", artifact_type="routing_rule")))
    monkeypatch.setattr("gae.evolution.record_evolution_event", AsyncMock(side_effect=[RuntimeError("down"), None]))

    await shadow_runner._flush_shadow_batch(MagicMock())

    assert shadow_runner.flush_failed is True


@pytest.mark.asyncio
async def test_shadow_flush_success_then_failure_stays_failed(monkeypatch):
    monkeypatch.setattr(shadow_runner, "SHADOW_BATCH_SIZE", 1)
    monkeypatch.setattr(shadow_runner, "_shadow_buffer", [
        shadow_runner.ShadowComparison("a", "a1", "cat", "monitor", "escalate", 0.5, "escalate", 1.0),
        shadow_runner.ShadowComparison("b", "b1", "cat", "monitor", "escalate", 0.5, "escalate", 1.0),
    ])
    monkeypatch.setattr(shadow_runner, "flush_failed", False)
    monkeypatch.setattr("app.services.variant_registry.get_variant", MagicMock(return_value=MagicMock(status="shadow", artifact_type="routing_rule")))
    monkeypatch.setattr("gae.evolution.record_evolution_event", AsyncMock(side_effect=[None, RuntimeError("down")]))

    await shadow_runner._flush_shadow_batch(MagicMock())

    assert shadow_runner.flush_failed is True


@pytest.mark.asyncio
async def test_override_detector_exception_marks_graph_unavailable(monkeypatch):
    graph = MagicMock()
    graph.run_query = AsyncMock(side_effect=RuntimeError("down"))
    monkeypatch.setattr(override_detector.override_detector, "graph_loaded", True)

    result = await override_detector.load_from_graph(graph)

    assert result.graph_loaded is False


@pytest.mark.asyncio
async def test_override_detector_none_marks_graph_unavailable(monkeypatch):
    graph = MagicMock()
    graph.run_query = AsyncMock(return_value=None)
    monkeypatch.setattr(override_detector.override_detector, "graph_loaded", True)

    result = await override_detector.load_from_graph(graph)

    assert result.graph_loaded is False


@pytest.mark.asyncio
async def test_compounding_historical_exception_degrades_response(monkeypatch):
    graph = MagicMock()
    graph.run_query = AsyncMock(side_effect=[[{"n": 0}], [{"n": 0}], RuntimeError("down"), []])
    monkeypatch.setattr(metrics, "graph_client", graph)

    result = await metrics.get_compounding_metrics(weeks=1)

    assert result["historical_context_available"] is False
    assert result["data_available"] is False
    assert "historical_context" in result["degraded_fields"]


@pytest.mark.asyncio
async def test_compounding_historical_none_degrades_response(monkeypatch):
    graph = MagicMock()
    graph.run_query = AsyncMock(side_effect=[[{"n": 0}], [{"n": 0}], None, []])
    monkeypatch.setattr(metrics, "graph_client", graph)

    result = await metrics.get_compounding_metrics(weeks=1)

    assert result["historical_context_available"] is False
    assert result["data_available"] is False


@pytest.mark.asyncio
async def test_override_detector_unavailable_reaches_tab_response(monkeypatch):
    monkeypatch.setattr(override_detector.override_detector, "graph_loaded", False)
    monkeypatch.setattr("app.services.iks.compute_visible_iks", AsyncMock(return_value=50.0))
    monkeypatch.setattr("app.services.iks.compute_iks_v2", AsyncMock(return_value={
        "components": {}, "total_decisions": 0, "iks_v2": 50.0, "interpretation": "Developing"
    }))
    monkeypatch.setattr(soc.graph_client, "run_query", AsyncMock(return_value=[{"cnt": 0}]))

    result = await soc._tab2_content()

    assert result["data_available"] is False
    assert "override_learning_status" in result["degraded_fields"]
