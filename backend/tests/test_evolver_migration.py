import inspect
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.framework.evolution_ledger import ARTIFACT_PROMPT_MODULE
from app.main import app
from app.services import evolver
from app.services import variant_registry as registry


def setup_function():
    evolver.reset_evolver_state()
    registry.reset_variant_registry()


def _active_prompt_variant(category="anomalous_login"):
    return registry.VariantRecord(
        variant_id="ae_prompt_active",
        artifact_type=ARTIFACT_PROMPT_MODULE,
        category=category,
        config={
            "prompt_id_current": "TRAVEL_CONTEXT_v2",
            "prompt_id_variant": "TRAVEL_CONTEXT_v3",
        },
        status=registry.ACTIVE,
        trigger_key="RULE-OVERRIDE-PROMPT_travel_context",
        graph_trigger={"override_pattern": "travel_context"},
        created_at=1000.0,
        promoted_at=1100.0,
    )


def test_get_prompt_variant_falls_through_to_legacy_when_registry_empty():
    assert evolver.get_prompt_variant("anomalous_login") == "TRAVEL_CONTEXT_v2"
    assert evolver.get_prompt_variant("unknown_type") == "DEFAULT_v1"


def test_get_prompt_variant_returns_active_registry_variant_for_category():
    registry.register_variant(_active_prompt_variant())

    assert evolver.get_prompt_variant("anomalous_login") == "TRAVEL_CONTEXT_v3"


def test_get_prompt_variant_resolves_raw_alert_type_to_soc_category():
    registry.register_variant(_active_prompt_variant(category="credential_access"))

    assert evolver.get_prompt_variant("anomalous_login") == "TRAVEL_CONTEXT_v3"


def test_get_prompt_variant_unknown_alert_type_falls_through_safely():
    assert evolver.get_prompt_variant("unknown_type") == "DEFAULT_v1"


def test_unknown_alert_type_ignores_active_default_category_registry_variant():
    registry.register_variant(_active_prompt_variant(category="credential_access"))

    assert evolver.get_prompt_variant("unknown_type") == "DEFAULT_v1"
    assert evolver.get_prompt_variant("unknown_type") != "TRAVEL_CONTEXT_v3"


def test_known_alert_type_can_use_default_category_registry_variant():
    registry.register_variant(_active_prompt_variant(category="credential_access"))

    assert evolver.get_prompt_variant("anomalous_login") == "TRAVEL_CONTEXT_v3"


def test_get_prompt_variant_accepts_category():
    evolver.CATEGORY_PROMPT_STATS["credential_access"] = {
        "CATEGORY_PROMPT_v1": {"success": 3, "total": 3, "success_rate": 1.0}
    }

    assert evolver.get_prompt_variant() == "DEFAULT_v1"
    assert evolver.get_prompt_variant("anomalous_login") == "CATEGORY_PROMPT_v1"
    assert evolver.get_prompt_variant(category="credential_access") == "CATEGORY_PROMPT_v1"


def test_category_specific_selection_can_differ_from_global():
    evolver.ACTIVE_PROMPTS["anomalous_login"] = "GLOBAL_PROMPT_v1"
    evolver.PROMPT_STATS["GLOBAL_PROMPT_v1"] = {
        "success": 95,
        "total": 100,
        "success_rate": 0.95,
    }
    evolver.CATEGORY_PROMPT_STATS["credential_access"] = {
        "CATEGORY_PROMPT_v1": {"success": 5, "total": 5, "success_rate": 1.0}
    }

    assert evolver.get_prompt_variant("anomalous_login") == "CATEGORY_PROMPT_v1"
    assert evolver.get_prompt_variant("anomalous_login") != evolver.ACTIVE_PROMPTS["anomalous_login"]


def test_category_selection_uses_ucb_not_raw_success_rate_only():
    evolver.CATEGORY_PROMPT_STATS["credential_access"] = {
        "HIGHER_RAW_RATE_v1": {"success": 80, "total": 100, "success_rate": 0.80},
        "LOWER_RAW_RATE_FEWER_TRIALS_v1": {
            "success": 3,
            "total": 4,
            "success_rate": 0.75,
        },
    }

    assert (
        evolver.get_prompt_variant(category="credential_access")
        == "LOWER_RAW_RATE_FEWER_TRIALS_v1"
    )


def test_no_category_falls_back_to_global():
    assert evolver.get_prompt_variant() == "DEFAULT_v1"


def test_cold_start_category_falls_back_to_global():
    assert evolver.get_prompt_variant("anomalous_login", category="credential_access") == "TRAVEL_CONTEXT_v2"


def test_get_prompt_stats_merges_registry_and_legacy_stats():
    registry.register_variant(_active_prompt_variant())

    stats = evolver.get_prompt_stats()

    assert "TRAVEL_CONTEXT_v2" in stats
    assert stats["TRAVEL_CONTEXT_v2"]["success"] == 42
    assert stats["TRAVEL_CONTEXT_v3"]["source"] == "variant_registry"
    assert stats["TRAVEL_CONTEXT_v3"]["variant_id"] == "ae_prompt_active"


def test_record_decision_outcome_still_updates_legacy_stats():
    evolver.record_decision_outcome(
        "DEC-MIGRATION",
        "MIGRATION_PROMPT_v1",
        True,
        alert_type="migration",
    )

    stats = evolver.PROMPT_STATS["MIGRATION_PROMPT_v1"]
    assert stats == {"success": 1, "total": 1, "success_rate": 1.0}
    assert evolver.WEIGHT_HISTORY[-1]["trigger"] == "MIGRATION_PROMPT_v1"


def test_record_decision_outcome_tracks_category_stats():
    evolver.record_decision_outcome(
        "DEC-CATEGORY",
        "CATEGORY_PROMPT_v1",
        True,
        alert_type="anomalous_login",
        category="credential_access",
    )

    global_stats = evolver.PROMPT_STATS["CATEGORY_PROMPT_v1"]
    category_stats = evolver.CATEGORY_PROMPT_STATS["credential_access"]["CATEGORY_PROMPT_v1"]
    assert global_stats == {"success": 1, "total": 1, "success_rate": 1.0}
    assert category_stats == {"success": 1, "total": 1, "success_rate": 1.0}


def test_promotion_gate_unchanged_global():
    evolver.ACTIVE_PROMPTS["migration"] = "MIGRATION_v1"
    evolver.PROMPT_STATS["MIGRATION_v1"] = {
        "success": 5,
        "total": 10,
        "success_rate": 0.5,
    }
    evolver.PROMPT_STATS["MIGRATION_v2"] = {
        "success": 9,
        "total": 10,
        "success_rate": 0.9,
    }

    result = evolver.check_for_promotion("migration")

    assert result["promoted"] is True
    assert result["old_variant"] == "MIGRATION_v1"
    assert result["new_variant"] == "MIGRATION_v2"
    assert evolver.ACTIVE_PROMPTS["migration"] == "MIGRATION_v2"


def test_evolver_reset_clears_category_stats():
    registry.register_variant(_active_prompt_variant())
    evolver.CATEGORY_PROMPT_STATS["credential_access"] = {
        "CATEGORY_PROMPT_v1": {"success": 1, "total": 1, "success_rate": 1.0}
    }

    with patch("gae.evolution.reset_evolution_ledger") as reset_ledger:
        evolver.reset_evolver_state()

    reset_ledger.assert_called_once()
    assert registry.get_all_variants() == []
    assert evolver.CATEGORY_PROMPT_STATS == {}
    assert evolver.get_prompt_variant("anomalous_login") == "TRAVEL_CONTEXT_v2"


def test_triage_passes_correct_category_field_non_blocking():
    from app.routers import triage

    source = inspect.getsource(triage)
    assert "alert_category = resolve_alert_category(alert_type)" in source
    assert "category=alert_category" in source
    assert "_shadow_asyncio.create_task" in source
    assert "await maybe_shadow_compare" not in source


def test_evolution_router_get_deployments_still_works(monkeypatch):
    from app.routers import evolution

    neo4j = AsyncMock()
    neo4j.run_query = AsyncMock(return_value=[{"n": 10}])
    monkeypatch.setattr(evolution, "neo4j_client", neo4j)

    response = TestClient(app).get("/api/deployments")

    assert response.status_code == 200
    body = response.json()
    assert len(body["deployments"]) == 2
    assert body["deployments"][0]["pattern_count"] == 10


def test_evolution_router_alert_process_route_still_registered():
    paths = {
        route.path
        for route in app.routes
        if "POST" in getattr(route, "methods", set())
    }

    assert "/api/alert/process" in paths
