"""SOC adapter coverage for SDK-backed prompt evolution."""
from pathlib import Path

from copilot_sdk.evolution.prompt_evolver import PromptVariantEvolver

from app.services import evolver


def setup_function():
    evolver.reset_evolver_state()


def test_get_prompt_variant_no_args():
    assert evolver.get_prompt_variant() == "DEFAULT_v1"


def test_get_prompt_variant_with_category():
    evolver.CATEGORY_PROMPT_STATS["credential_access"] = {
        "CATEGORY_A_v1": {"success": 9, "total": 10, "success_rate": 0.9},
        "CATEGORY_B_v1": {"success": 1, "total": 10, "success_rate": 0.1},
    }

    assert evolver.get_prompt_variant(category="credential_access") == "CATEGORY_A_v1"


def test_get_prompt_variant_with_alert_type_positional():
    assert evolver.get_prompt_variant("anomalous_login") == "TRAVEL_CONTEXT_v2"


def test_record_decision_outcome_updates_stats():
    evolver.record_decision_outcome(
        "decision-1",
        "TRAVEL_CONTEXT_v2",
        True,
        alert_type="anomalous_login",
    )

    assert evolver.PROMPT_STATS["TRAVEL_CONTEXT_v2"]["success"] == 43
    assert evolver.PROMPT_STATS["TRAVEL_CONTEXT_v2"]["total"] == 48
    assert (
        evolver.CATEGORY_PROMPT_STATS["credential_access"]["TRAVEL_CONTEXT_v2"]["success"]
        == 1
    )


def test_check_for_promotion_returns_dict_or_none():
    result = evolver.check_for_promotion("anomalous_login")
    assert result is None or {"promoted", "old_variant", "new_variant"} <= set(result)


def test_get_evolution_summary_returns_soc_shape():
    summary = evolver.get_evolution_summary("anomalous_login")

    assert summary.alert_type == "anomalous_login"
    assert summary.current_prompt == "TRAVEL_CONTEXT_v2"
    assert summary.operational_impact is not None


def test_reset_evolver_state_clears_everything():
    evolver.record_decision_outcome(
        "decision-2",
        "TRAVEL_CONTEXT_v2",
        True,
        alert_type="anomalous_login",
    )
    assert "credential_access" in evolver.CATEGORY_PROMPT_STATS

    evolver.reset_evolver_state()

    assert evolver.CATEGORY_PROMPT_STATS == {}
    assert evolver.RECENT_PROMOTIONS == {}


def test_reset_re_registers_initial_variants():
    evolver.reset_evolver_state()

    assert evolver.get_prompt_variant("anomalous_login") == "TRAVEL_CONTEXT_v2"
    assert evolver.get_prompt_variant("phishing") == "PHISHING_RESPONSE_v1"
    assert isinstance(evolver._evolver, PromptVariantEvolver)


def test_category_ucb_selection_preserved():
    evolver.CATEGORY_PROMPT_STATS["schema_change"] = {
        "SCHEMA_A_v1": {"success": 50, "total": 100, "success_rate": 0.5},
        "SCHEMA_B_v1": {"success": 9, "total": 10, "success_rate": 0.9},
    }

    assert evolver.get_prompt_variant(category="schema_change") == "SCHEMA_B_v1"


def test_category_ucb_differs_from_global():
    evolver.PROMPT_STATS["GLOBAL_A_v1"] = {
        "success": 99,
        "total": 100,
        "success_rate": 0.99,
    }
    evolver.PROMPT_STATS["GLOBAL_B_v1"] = {
        "success": 1,
        "total": 100,
        "success_rate": 0.01,
    }
    evolver.CATEGORY_PROMPT_STATS["schema_change"] = {
        "GLOBAL_A_v1": {"success": 1, "total": 20, "success_rate": 0.05},
        "GLOBAL_B_v1": {"success": 18, "total": 20, "success_rate": 0.9},
    }

    assert evolver.get_prompt_variant(category="schema_change") == "GLOBAL_B_v1"


def test_reset_clears_category_stats():
    evolver.CATEGORY_PROMPT_STATS["x"] = {
        "X_v1": {"success": 1, "total": 1, "success_rate": 1.0}
    }

    evolver.reset_evolver_state()

    assert evolver.CATEGORY_PROMPT_STATS == {}


def test_alert_type_maps_to_context_key_not_category():
    evolver.CATEGORY_PROMPT_STATS["credential_access"] = {
        "CRED_A_v1": {"success": 1, "total": 10, "success_rate": 0.1},
        "CRED_B_v1": {"success": 9, "total": 10, "success_rate": 0.9},
    }

    assert evolver.get_prompt_variant("anomalous_login") == "CRED_B_v1"


def test_evolution_router_imports_still_work():
    from app.services.evolver import (
        check_for_promotion,
        get_evolution_summary,
        get_prompt_variant,
        get_variant_comparison,
        get_weight_history,
        record_decision_outcome,
        reset_evolver_state,
    )

    assert callable(get_prompt_variant)
    assert callable(record_decision_outcome)
    assert callable(check_for_promotion)
    assert callable(get_evolution_summary)
    assert callable(get_variant_comparison)
    assert callable(get_weight_history)
    assert callable(reset_evolver_state)


def test_triage_fire_and_forget_preserved():
    triage_source = Path("app/routers/triage.py").read_text()

    assert "create_task" in triage_source
    assert "maybe_shadow_compare" in triage_source


def test_no_level1_imports_in_evolver():
    source = Path("app/services/evolver.py").read_text()

    assert "ProfileScorer" not in source
    assert "CompoundingScorer" not in source
    assert ".centroids" not in source
