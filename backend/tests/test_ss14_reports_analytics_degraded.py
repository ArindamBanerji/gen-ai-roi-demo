import pytest


class BrokenGraph:
    async def run_query(self, *args, **kwargs):
        raise RuntimeError("graph unavailable")


@pytest.mark.asyncio
async def test_attack_chain_fetch_failure():
    from app.services.attack_chain import AttackChainService
    service = AttackChainService(BrokenGraph())
    assert await service._fetch_recent_alerts(72) is None


@pytest.mark.asyncio
async def test_balance_sheet_centroid_drift_failure():
    from app.services.balance_sheet import _safe_centroid_drift
    assert await _safe_centroid_drift(BrokenGraph()) is None


@pytest.mark.asyncio
async def test_balance_sheet_auto_approve_failure(monkeypatch):
    from app.services.balance_sheet import _safe_auto_approve_stats
    import app.routers.framework_router as framework_router

    async def fail(*args, **kwargs):
        raise RuntimeError("graph unavailable")

    monkeypatch.setattr(framework_router, "auto_approve_stats", fail)
    assert await _safe_auto_approve_stats() is None


@pytest.mark.asyncio
async def test_balance_sheet_timeline_failure(monkeypatch):
    from app.services import balance_sheet

    async def fail_checkpoint_store(_graph):
        raise RuntimeError("checkpoint store unavailable")

    monkeypatch.setattr(balance_sheet, "get_evolution_timeline", fail_checkpoint_store)
    assert await balance_sheet._safe_timeline(BrokenGraph()) is None


@pytest.mark.asyncio
async def test_balance_sheet_partial_timeline_survives_iks_failure(monkeypatch):
    from app.services import time_machine
    from unittest.mock import AsyncMock

    monkeypatch.setattr(time_machine, "_age_payloads", lambda: [{
        "backup_id": "one",
        "mu": [[[[0.0]]]],
        "shape": [1, 1, 1, 1],
        "timestamp_epoch": 1,
        "step": 1,
        "sha256": "hash",
        "version": "test",
        "metadata": {"decision_count": 1},
    }])
    monkeypatch.setattr(time_machine, "get_mu_zero", lambda: None)
    monkeypatch.setattr(time_machine, "_compute_current_ceiling_estimate", lambda: None)
    monkeypatch.setattr(time_machine, "compute_iks_v2", AsyncMock(side_effect=RuntimeError("iks down")))
    result = await time_machine.get_evolution_timeline(object())
    assert result is not None
    assert result["timeline_available"] is True
    assert result["iks_available"] is False


def test_benchmarking_decisions_failure():
    from app.services.benchmarking_report import BenchmarkingEngine
    engine = BenchmarkingEngine(BrokenGraph())
    engine._fetch_verified_decisions = lambda *args: None
    report = engine.generate_report("2026-01-01", "2026-01-02")
    assert report.decisions_available is False
    assert report.total_decisions == 0


@pytest.mark.asyncio
async def test_cluster_history_failure():
    from app.services.cluster_history import get_cluster_history
    assert await get_cluster_history("user-1", "decision-1", BrokenGraph()) is None


@pytest.mark.asyncio
async def test_discovery_watermark_failure():
    from app.services.cross_graph_discovery import DiscoveryService
    discovery = DiscoveryService()
    result = await discovery.refresh("soc", BrokenGraph())
    assert result.get("watermark_available") is False


@pytest.mark.asyncio
async def test_executive_narrative_partial_failure(monkeypatch):
    from app.services.executive_narrative import build_executive_narrative_async
    from unittest.mock import AsyncMock
    import app.services.gae_state as gae_state
    import app.services.iks as iks

    monkeypatch.setattr(gae_state, "get_profile_scorer", lambda: None)
    monkeypatch.setattr(iks, "compute_iks_v2", AsyncMock(side_effect=RuntimeError("iks unavailable")))
    result = await build_executive_narrative_async(BrokenGraph())
    assert isinstance(result["sections_degraded"], list)
    assert "verified_decisions" in result["sections_degraded"]
    assert "what_system_knows" in result["sections_degraded"]
    assert result["degraded"] is True
    assert result["data_available"] is False


@pytest.mark.asyncio
async def test_graph_explorer_top_nodes_failure():
    from app.services.graph_explorer import GraphExplorerService
    assert await GraphExplorerService.get_top_nodes(BrokenGraph()) is None


@pytest.mark.asyncio
async def test_graph_explorer_neighbors_failure():
    from app.services.graph_explorer import GraphExplorerService
    assert await GraphExplorerService.get_node_neighbors("n1", BrokenGraph()) is None


@pytest.mark.asyncio
async def test_graph_explorer_summary_failure():
    from app.services.graph_explorer import GraphExplorerService
    assert await GraphExplorerService.get_graph_summary(BrokenGraph()) is None


@pytest.mark.asyncio
async def test_visible_iks_failure():
    from app.services.iks import compute_visible_iks
    assert await compute_visible_iks(BrokenGraph(), scorer=None) is None


@pytest.mark.asyncio
async def test_investigation_bounded_read_failure():
    from app.services.investigation_patterns import CredentialInvestigationPattern
    result = await CredentialInvestigationPattern().execute({"alert_id": "a1"}, BrokenGraph())
    assert result["evidence_available"] is False
    assert result["vld_factor_vector"] == []
    assert result["evidence_keys"] == []
    assert result["evidence_admitted"] is False


@pytest.mark.asyncio
async def test_volume_baseline_failure():
    from app.services.learning_health import compute_volume_baseline
    assert await compute_volume_baseline(BrokenGraph()) is None


@pytest.mark.asyncio
async def test_override_detector_load_failure():
    from app.services.override_detector import load_from_graph, override_detector
    before = override_detector.example_count
    result = await load_from_graph(BrokenGraph())
    assert result.example_count == before
    assert result.graph_loaded is False


@pytest.mark.asyncio
async def test_promotion_shadow_stats_failure(monkeypatch):
    from app.services import promotion_gate
    monkeypatch.setattr(promotion_gate, "get_variant", lambda _: None)
    assert await promotion_gate._get_shadow_batch_stats("v1", BrokenGraph()) is None
