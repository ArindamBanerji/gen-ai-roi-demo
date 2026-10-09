from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest


class BrokenGraph:
    async def run_query(self, *args, **kwargs):
        raise RuntimeError("graph unavailable")

    async def get_alert(self, *args, **kwargs):
        raise RuntimeError("alert unavailable")

    async def get_security_context(self, *args, **kwargs):
        raise RuntimeError("context unavailable")


@pytest.mark.asyncio
async def test_consult_history_graph_failure():
    from app.services.variant_generator import _consult_history
    assert await _consult_history(BrokenGraph(), "v1") is None


@pytest.mark.asyncio
async def test_load_accuracy_trajectory_failure():
    from app.services.variant_generator import _load_accuracy_trajectory
    assert await _load_accuracy_trajectory(BrokenGraph()) is None


@pytest.mark.asyncio
async def test_category_accuracy_trends_failure():
    from app.services.variant_generator import _get_per_category_accuracy_trends
    assert await _get_per_category_accuracy_trends(BrokenGraph()) is None


@pytest.mark.asyncio
async def test_coverage_gap_detect_failure():
    from app.services.variant_generator import CoverageGapRule
    rule = CoverageGapRule()
    assert await rule.detect(BrokenGraph()) is None
    assert rule.last_data_available is False


@pytest.mark.asyncio
async def test_scan_opportunities_partial_failure():
    from app.services.variant_generator import VariantGenerator

    class FailingRule:
        rule_id = "RULE-FAIL"
        artifact_type = "test"
        description = "test"

        async def detect(self, graph_client):
            raise RuntimeError("rule unavailable")

    result = await VariantGenerator(rules=[FailingRule()]).scan_for_opportunities(BrokenGraph())
    assert list(result) == []
    assert result.scan_complete is False
    assert result.rules_failed == ["RULE-FAIL"]


@pytest.mark.asyncio
async def test_chain_credit_assign_failure():
    from app.services.rl_engine import CreditAssigner
    result = await CreditAssigner(BrokenGraph()).assign_chain_credit("d1", "cat", 0, 10, 1.0)
    assert result is None


@pytest.mark.asyncio
async def test_simulation_context_failure():
    from app.services.simulation import SimulationOrchestrator
    import app.db.graph_client as graph_module

    orchestrator = SimulationOrchestrator(None, None, None)
    with patch("app.services.gae_state.get_profile_scorer", return_value=None):
        result = await orchestrator.run(1, [{"alert_id": "a1", "category": "credential_access"}], speed_ms=0)
    assert result.context_degraded == ["graph_store"]


@pytest.mark.asyncio
async def test_shadow_batch_flush_failure(monkeypatch, caplog):
    import app.services.shadow_runner as runner
    import app.services.variant_registry as variant_registry
    runner.reset_shadow_runner()
    comparisons = [
        runner.ShadowComparison(
            variant_id="variant-failing-write",
            alert_id=f"alert-{index}",
            category="credential_access",
            production_action="monitor",
            variant_action="escalate",
            production_confidence=0.6,
            correct_action="escalate",
            timestamp=float(index),
        )
        for index in range(runner.SHADOW_BATCH_SIZE)
    ]
    monkeypatch.setattr(runner, "_shadow_buffer", comparisons)
    monkeypatch.setattr(runner, "flush_failed", False)
    monkeypatch.setattr(
        variant_registry,
        "get_variant",
        lambda _variant_id: SimpleNamespace(status="shadow", artifact_type="routing_rule"),
    )

    with caplog.at_level("WARNING"):
        await runner._flush_shadow_batch(BrokenGraph())

    assert runner.flush_failed is True
    assert runner._shadow_buffer == comparisons
    assert "Shadow batch write failed for variant_id=variant-failing-write" in caplog.text


@pytest.mark.asyncio
async def test_profile_snapshot_write_failure(monkeypatch):
    import app.services.snapshots as snapshots
    monkeypatch.setattr(snapshots, "log", SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None))
    monkeypatch.setattr(
        "app.db.graph_client.graph_client.run_query",
        AsyncMock(side_effect=RuntimeError("graph unavailable")),
    )
    monkeypatch.setattr(
        "app.services.gae_state.get_profile_scorer",
        lambda: SimpleNamespace(centroids=SimpleNamespace(tolist=lambda: [], shape=(0,)), counts=SimpleNamespace(tolist=lambda: [])),
    )
    assert await snapshots._write_profile_snapshot(50) is False
