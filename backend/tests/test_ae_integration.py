from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
import numpy as np
import pytest

from app.framework.evolution_ledger import (
    ARTIFACT_ROUTING_RULE,
    ARTIFACT_SCORING_THRESHOLD,
)
from app.main import app
from app.services import promotion_gate as gate
from app.services import shadow_runner
from app.services import variant_generator as generator
from app.services import variant_registry as registry


def setup_function():
    registry.reset_variant_registry()
    shadow_runner.reset_shadow_runner()
    gate.reset_promotion_gate()


def _record(variant_id="variant_scan", artifact_type=ARTIFACT_ROUTING_RULE):
    return registry.VariantRecord(
        variant_id=variant_id,
        artifact_type=artifact_type,
        category="credential_access",
        config={"action": "escalate"},
        status=registry.CANDIDATE,
        trigger_key=f"trigger:{variant_id}",
        graph_trigger={"campaign_id": "C-007"},
        created_at=1000.0,
    )


def _patch_module(monkeypatch, module_name, module):
    real_import = generator.importlib.import_module

    def fake_import(name):
        if name == module_name:
            return module
        return real_import(name)

    monkeypatch.setattr(generator.importlib, "import_module", fake_import)


def _install_analyze_shadow_patches(monkeypatch, action="monitor", confidence=0.8):
    import app.routers.triage as triage_router

    alert = {
        "alert_id": "ALERT-SHADOW-ROUTE",
        "id": "ALERT-SHADOW-ROUTE",
        "alert_type": "anomalous_login",
        "severity": "medium",
        "source_location": "10.0.1.54",
        "user_id": "user-1",
        "asset_id": "asset-1",
        "status": "pending",
    }
    context = {
        "alert_type": "anomalous_login",
        "user_id": "user-1",
        "nodes_consulted": 4,
        "mfa_completed": True,
    }
    neo4j = MagicMock()
    neo4j.get_alert = AsyncMock(return_value=alert)
    neo4j.get_security_context = AsyncMock(return_value=context)
    neo4j.run_query = AsyncMock(return_value=[])
    neo4j.get_sequence_count = AsyncMock(return_value=0)
    neo4j.get_cross_category_count = AsyncMock(return_value=0)
    monkeypatch.setattr(triage_router, "neo4j_client", neo4j)
    monkeypatch.setattr(
        triage_router,
        "compute_factor_vector",
        AsyncMock(return_value=np.array([0.2, 0.3, 0.4, 0.1, 0.5, 0.6])),
    )
    monkeypatch.setattr(
        triage_router.narrator,
        "generate_reasoning",
        AsyncMock(return_value="mock shadow reasoning"),
    )
    monkeypatch.setattr(
        triage_router,
        "record_decision",
        AsyncMock(return_value={"hash": "hash-1", "chain_index": 1}),
    )
    monkeypatch.setattr(triage_router.event_bus, "emit", AsyncMock())
    monkeypatch.setattr(
        triage_router,
        "get_graph_data",
        AsyncMock(return_value={"nodes": [], "edges": []}),
    )

    scoring = SimpleNamespace(
        action_name=action,
        confidence=confidence,
        entropy=0.1,
        confidence_gap=0.7,
        probabilities=np.array([0.05, 0.05, 0.05, 0.85]),
    )
    scorer = MagicMock()
    scorer.score.return_value = scoring
    scorer.tau = 0.1

    learning_state = SimpleNamespace(decision_count=1)
    monkeypatch.setattr("app.services.gae_state.get_profile_scorer", lambda: scorer)
    monkeypatch.setattr("app.services.gae_state.init_learning_state", lambda: None)
    monkeypatch.setattr("app.services.gae_state.get_learning_state", lambda: learning_state)
    monkeypatch.setattr(triage_router, "get_learning_state", lambda: learning_state)

    class _NarrativeProvider:
        def generate(self, *_args, **_kwargs):
            return {"summary": "mock narrative"}

    monkeypatch.setattr(triage_router, "get_narrative_provider", lambda: _NarrativeProvider())
    return neo4j


def test_admin_evolution_scan_returns_generated_variants(monkeypatch):
    scanner = SimpleNamespace(
        scan_for_opportunities=AsyncMock(return_value=[_record()])
    )
    monkeypatch.setattr(
        "app.services.variant_generator.VariantGenerator",
        lambda: scanner,
    )

    response = TestClient(app).post("/api/admin/evolution-scan")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["count"] == 1
    assert body["variants"][0]["variant_id"] == "variant_scan"


def test_admin_evolution_scan_returns_zero_when_none_generated(monkeypatch):
    scanner = SimpleNamespace(scan_for_opportunities=AsyncMock(return_value=[]))
    monkeypatch.setattr(
        "app.services.variant_generator.VariantGenerator",
        lambda: scanner,
    )

    response = TestClient(app).post("/api/admin/evolution-scan")

    assert response.status_code == 200
    assert response.json() == {"success": True, "count": 0, "variants": []}


@pytest.mark.asyncio
async def test_full_campaign_evolution_chain_dedups(monkeypatch):
    service = SimpleNamespace(
        refresh=AsyncMock(return_value={
            "discoveries": [
                {
                    "type": "campaign",
                    "campaign_id": "C-007",
                    "category": "credential_access",
                }
            ]
        })
    )
    _patch_module(
        monkeypatch,
        "app.services.cross_graph_discovery",
        SimpleNamespace(discovery_service=service),
    )
    monkeypatch.setattr(
        generator,
        "record_evolution_event",
        AsyncMock(return_value={"id": "evo_1"}),
    )
    gen = generator.VariantGenerator(rules=[generator.CampaignEscalateRule()])

    first = await gen.scan_for_opportunities(object())
    second = await gen.scan_for_opportunities(object())

    assert len(first) == 1
    assert first[0].artifact_type == ARTIFACT_ROUTING_RULE
    assert first[0].config["campaign_pattern"] == "C-007"
    assert registry.has_active_or_shadow("RULE-CAMPAIGN-ESCALATE_C-007") is True
    assert second == []


@pytest.mark.asyncio
async def test_multiple_rules_fire_campaign_and_drift(monkeypatch):
    campaign_service = SimpleNamespace(
        refresh=AsyncMock(return_value={
            "discoveries": [{"type": "campaign", "campaign_id": "C-007"}]
        })
    )
    real_import = generator.importlib.import_module

    def fake_import(name):
        if name == "app.services.cross_graph_discovery":
            return SimpleNamespace(discovery_service=campaign_service)
        return real_import(name)

    monkeypatch.setattr(generator.importlib, "import_module", fake_import)
    monkeypatch.setattr(
        generator,
        "_get_per_category_accuracy_trends",
        AsyncMock(return_value={
            "insider_threat": {
                "recent_accuracy": 0.82,
                "prior_accuracy": 0.88,
                "recent_total": 50,
                "prior_total": 50,
                "decline_pp": 6.0,
            }
        }),
    )
    monkeypatch.setattr(
        generator,
        "record_evolution_event",
        AsyncMock(return_value={"id": "evo_1"}),
    )
    gen = generator.VariantGenerator(rules=[
        generator.CampaignEscalateRule(),
        generator.DriftThresholdRule(),
    ])

    created = await gen.scan_for_opportunities(object())

    assert len(created) == 2
    assert {record.artifact_type for record in created} == {
        ARTIFACT_ROUTING_RULE,
        ARTIFACT_SCORING_THRESHOLD,
    }
    drift = next(record for record in created if record.artifact_type == ARTIFACT_SCORING_THRESHOLD)
    assert drift.graph_trigger["detection_method"] == "per_category_accuracy_trend"


def test_reset_clears_memory_but_does_not_delete_graph_events():
    registry.register_variant(_record())
    graph = AsyncMock()
    graph.run_query = AsyncMock()

    registry.reset_variant_registry()

    assert registry.get_all_variants() == []
    graph.run_query.assert_not_called()


def test_recent_events_endpoint_still_works_with_mocked_ledger():
    with patch(
        "app.routers.evolution.get_ledger_recent_events",
        new=AsyncMock(return_value=[{
            "id": "e1",
            "event_type": "variant_created",
            "variant_id": "variant_scan",
        }]),
    ):
        response = TestClient(app).get("/api/evolution/recent-events?limit=5")

    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_variant_history_endpoint_still_works_with_mocked_ledger():
    with patch(
        "app.routers.evolution.get_ledger_variant_history",
        new=AsyncMock(return_value=[{
            "id": "e1",
            "event_type": "variant_created",
            "variant_id": "variant_scan",
        }]),
    ):
        response = TestClient(app).get(
            "/api/evolution/variant-history?variant_id=variant_scan"
        )

    assert response.status_code == 200
    assert response.json()["variant_id"] == "variant_scan"


def test_analyze_schedules_shadow_compare_without_changing_response(monkeypatch):
    _install_analyze_shadow_patches(monkeypatch, action="monitor", confidence=0.8)
    created = []

    def fake_create_task(coro):
        created.append(coro)
        coro.close()
        return SimpleNamespace(done=lambda: True)

    monkeypatch.setattr(shadow_runner.asyncio, "create_task", fake_create_task)
    shadow_record = _record(variant_id="variant_shadow_route")
    shadow_record.config = {
        "action": "escalate",
        "trigger_categories": ["credential_access"],
        "min_confidence": 0.7,
    }
    registry.register_variant(shadow_record)
    registry.transition_status("variant_shadow_route", registry.SHADOW)

    response = TestClient(app).post("/api/alert/analyze", json={"alert_id": "ALERT-SHADOW-ROUTE"})

    assert response.status_code == 200, response.text
    assert response.json()["recommendation"]["action"] == "monitor"
    assert len(created) == 1


@pytest.mark.asyncio
async def test_full_shadow_chain_writes_shadow_result(monkeypatch):
    ledger = AsyncMock(return_value={"id": "evo_shadow"})
    monkeypatch.setattr("gae.evolution.record_evolution_event", ledger)
    monkeypatch.setattr(shadow_runner, "SHADOW_BATCH_SIZE", 3)
    scheduled = []

    def fake_create_task(coro):
        scheduled.append(coro)
        return SimpleNamespace(done=lambda: False)

    monkeypatch.setattr(shadow_runner.asyncio, "create_task", fake_create_task)
    shadow_record = _record(variant_id="variant_shadow_chain")
    shadow_record.config = {
        "action": "escalate",
        "trigger_categories": ["credential_access"],
        "min_confidence": 0.7,
    }
    registry.register_variant(shadow_record)

    response = TestClient(app).post("/api/admin/shadow-start?variant_id=variant_shadow_chain")

    assert response.status_code == 200
    assert registry.get_variant("variant_shadow_chain").status == registry.SHADOW
    assert ledger.await_args.kwargs["event_type"] == "shadow_started"
    ledger.reset_mock()

    await shadow_runner.maybe_shadow_compare(
        "ALERT-SH-1", "credential_access", "monitor", 0.8, {}
    )
    await shadow_runner.maybe_shadow_compare(
        "ALERT-SH-2", "credential_access", "monitor", 0.8, {}
    )
    await shadow_runner.maybe_shadow_compare(
        "ALERT-SH-3", "credential_access", "investigate", 0.8, {}
    )

    assert len(shadow_runner._shadow_buffer) == 3
    assert all(entry.correct_action is None for entry in shadow_runner._shadow_buffer)

    shadow_runner.fill_shadow_outcome("ALERT-SH-1", "escalate")
    shadow_runner.fill_shadow_outcome("ALERT-SH-2", "suppress")
    shadow_runner.fill_shadow_outcome("ALERT-SH-3", "investigate")

    assert scheduled
    await scheduled[0]

    kwargs = ledger.await_args.kwargs
    assert kwargs["event_type"] == "shadow_result"
    assert kwargs["variant_id"] == "variant_shadow_chain"
    assert kwargs["metadata"]["wins"] == 1
    assert kwargs["metadata"]["total"] == 3
    assert kwargs["graph_context"]["win_rate"] == pytest.approx(0.3333)
    assert shadow_runner._shadow_buffer == []


@pytest.mark.asyncio
async def test_full_promotion_lifecycle_promotes_and_rolls_back(monkeypatch):
    ledger = AsyncMock(return_value={"id": "evo_promotion"})
    monkeypatch.setattr(gate, "record_evolution_event", ledger)
    monkeypatch.setattr(
        gate,
        "get_shadow_summary",
        lambda variant_id: {
            "shadow_active": False,
            "shadow_tested": True,
            "wins": 35,
            "total": 50,
            "win_rate": 0.70,
        },
    )
    monkeypatch.setattr(gate, "_production_q", lambda: 0.82)
    monkeypatch.setattr(
        gate,
        "_check_conservation_for_variant",
        AsyncMock(return_value={"passed": True, "status": "GREEN"}),
    )
    monkeypatch.setattr(
        gate,
        "_get_shadow_batch_stats",
        AsyncMock(return_value={
            "batch_count": gate.MIN_SHADOW_BATCHES,
            "batch_std": 0.01,
            "win_rates": [0.68, 0.70, 0.69],
        }),
    )
    monkeypatch.setattr(gate, "_get_daily_volume", lambda: 200.0)
    record = _record(variant_id="variant_promotion_chain")
    registry.register_variant(record)
    registry.transition_status("variant_promotion_chain", registry.SHADOW)

    response = TestClient(app).post(
        "/api/admin/promote-evaluate?variant_id=variant_promotion_chain"
    )

    assert response.status_code == 200, response.text
    assert response.json()["verdict"] == "promote"
    assert registry.get_variant("variant_promotion_chain").status == registry.ACTIVE
    assert ledger.await_args_list[0].kwargs["event_type"] == "promotion_approved"

    rolled_back = await gate.check_rollback(object())

    assert rolled_back.status == registry.ROLLED_BACK
    assert registry.get_variant("variant_promotion_chain").status == registry.ROLLED_BACK
    assert ledger.await_args_list[-1].kwargs["event_type"] == "rollback"
