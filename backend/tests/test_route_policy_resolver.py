import logging

from app.services.route_policy import (
    CANONICAL_COPILOTS,
    RouteExecutionMode,
    RoutePolicyResolver,
    parse_copilot_route_policy,
    resolve_route_policy,
)


def test_route_execution_mode_contains_planned_values():
    assert {mode.value for mode in RouteExecutionMode} == {
        "canonical_only",
        "shadow",
        "pipeline_served",
        "disabled",
    }


def test_all_valid_route_execution_modes_parse():
    for mode in RouteExecutionMode:
        decision = resolve_route_policy(
            copilot="soc",
            route_name="analyze",
            env={"SOC_ROUTE_MODE": mode.value},
        )

        assert decision.selected_mode is mode
        assert decision.requested_mode is mode


def test_absent_soc_route_mode_defaults_to_canonical_only():
    decision = resolve_route_policy(copilot="soc", route_name="analyze", env={})

    assert decision.selected_mode is RouteExecutionMode.CANONICAL_ONLY
    assert decision.config_source == "default"
    assert decision.served_output_source == "canonical_route"
    assert decision.side_effect_policy == "canonical_current_semantics"
    assert decision.diagnostics_enabled is False
    assert decision.is_blocked is False


def test_explicit_soc_canonical_only_resolves_canonical_only():
    decision = resolve_route_policy(
        copilot="soc",
        route_name="analyze",
        env={"SOC_ROUTE_MODE": "canonical_only"},
    )

    assert decision.selected_mode is RouteExecutionMode.CANONICAL_ONLY
    assert decision.requested_mode is RouteExecutionMode.CANONICAL_ONLY
    assert decision.config_source == "SOC_ROUTE_MODE"
    assert decision.served_output_source == "canonical_route"


def test_invalid_soc_route_mode_fails_closed_with_diagnostics():
    decision = resolve_route_policy(
        copilot="soc",
        route_name="analyze",
        env={"SOC_ROUTE_MODE": "pipeline_served_typo"},
    )

    assert decision.selected_mode is RouteExecutionMode.DISABLED
    assert decision.served_output_source == "none"
    assert decision.fallback_state == "fail_closed"
    assert decision.diagnostics_enabled is True
    assert decision.is_blocked is True
    assert decision.errors == ("invalid route mode: pipeline_served_typo",)


def test_shadow_flag_alone_does_not_change_selected_served_mode():
    decision = resolve_route_policy(
        copilot="soc",
        route_name="analyze",
        env={"USE_SOC_DECISION_PIPELINE_SHADOW": "true"},
    )

    assert decision.selected_mode is RouteExecutionMode.CANONICAL_ONLY
    assert decision.served_output_source == "canonical_route"
    assert decision.diagnostic_evaluation_source == "none"


def test_entity_cache_flag_does_not_change_route_mode():
    decision = resolve_route_policy(
        copilot="soc",
        route_name="analyze",
        env={"USE_ENTITY_CACHE": "true"},
    )

    assert decision.selected_mode is RouteExecutionMode.CANONICAL_ONLY
    assert decision.served_output_source == "canonical_route"


def test_materialized_counter_flags_do_not_change_route_mode():
    decision = resolve_route_policy(
        copilot="soc",
        route_name="analyze",
        env={
            "USE_MATERIALIZED_COUNTERS": "true",
            "MATERIALIZED_COUNTER_ROUTE_ADOPTION": "true",
        },
    )

    assert decision.selected_mode is RouteExecutionMode.CANONICAL_ONLY
    assert decision.served_output_source == "canonical_route"


def test_per_copilot_default_policy_is_canonical_only():
    for copilot in CANONICAL_COPILOTS:
        decision = resolve_route_policy(copilot=copilot, route_name="analyze", env={})

        assert decision.copilot == copilot
        assert decision.selected_mode is RouteExecutionMode.CANONICAL_ONLY
        assert decision.served_output_source == "canonical_route"


def test_soc_mode_is_not_inherited_by_other_copilots():
    env = {"SOC_ROUTE_MODE": "shadow"}

    soc_decision = resolve_route_policy(copilot="soc", route_name="analyze", env=env)
    trading_decision = resolve_route_policy(copilot="trading", route_name="analyze", env=env)

    assert soc_decision.selected_mode is RouteExecutionMode.SHADOW
    assert trading_decision.selected_mode is RouteExecutionMode.CANONICAL_ONLY


def test_route_decision_has_required_diagnostic_metadata():
    decision = resolve_route_policy(copilot="soc", route_name="analyze", env={})
    diagnostics = decision.to_diagnostics()

    assert diagnostics["copilot"] == "soc"
    assert diagnostics["route_name"] == "analyze"
    assert diagnostics["selected_mode"] == "canonical_only"
    assert diagnostics["reason"]
    assert diagnostics["config_source"] == "default"
    assert diagnostics["served_output_source"] == "canonical_route"
    assert diagnostics["side_effect_policy"] == "canonical_current_semantics"
    assert diagnostics["benchmark_gate_status"] == {"default_canonical": True}
    assert diagnostics["fallback_state"] == "none"


def test_pipeline_served_is_explicit_but_blocked_without_approval():
    decision = resolve_route_policy(
        copilot="soc",
        route_name="analyze",
        env={"SOC_ROUTE_MODE": "pipeline_served"},
    )

    assert decision.requested_mode is RouteExecutionMode.PIPELINE_SERVED
    assert decision.selected_mode is RouteExecutionMode.PIPELINE_SERVED
    assert decision.approved_for_serving is False
    assert decision.is_blocked is True
    assert decision.served_output_source == "none"
    assert decision.benchmark_gate_status["passed"] is False


def test_old_state_names_map_to_current_modes_with_warnings(caplog):
    caplog.set_level(logging.WARNING)

    expected = {
        "shadow_only": RouteExecutionMode.SHADOW,
        "pipeline_read_only": RouteExecutionMode.SHADOW,
    }
    for old_name, expected_mode in expected.items():
        decision = resolve_route_policy(
            copilot="soc",
            route_name="analyze",
            env={"SOC_ROUTE_MODE": old_name},
        )

        assert decision.selected_mode is expected_mode
        assert decision.requested_mode is expected_mode
        assert decision.served_output_source == "canonical_route"
        assert any(old_name in warning for warning in decision.warnings)

    assert "deprecated route mode alias used: shadow_only" in caplog.text
    assert "deprecated route mode alias used: pipeline_read_only" in caplog.text


def test_removed_future_state_names_fail_closed_with_warnings(caplog):
    caplog.set_level(logging.WARNING)

    for old_name in ("hybrid_fast_path", "fallback_to_canonical"):
        decision = resolve_route_policy(
            copilot="soc",
            route_name="analyze",
            env={"SOC_ROUTE_MODE": old_name},
        )

        assert decision.selected_mode is RouteExecutionMode.DISABLED
        assert decision.requested_mode is RouteExecutionMode.DISABLED
        assert decision.is_blocked is True
        assert decision.served_output_source == "none"
        assert decision.fallback_state == "fail_closed"
        assert decision.errors == (f"deprecated route mode disabled: {old_name}",)
        assert any(old_name in warning for warning in decision.warnings)

    assert "deprecated route mode alias used: hybrid_fast_path" in caplog.text
    assert "deprecated route mode alias used: fallback_to_canonical" in caplog.text


def test_shadow_mode_is_represented_but_not_active_by_default():
    resolver = RoutePolicyResolver(env={})

    default_decision = resolver.resolve(copilot="soc", route_name="analyze")
    assert default_decision.selected_mode is RouteExecutionMode.CANONICAL_ONLY

    shadow_decision = RoutePolicyResolver(env={"SOC_ROUTE_MODE": "shadow"}).resolve(
        copilot="soc",
        route_name="analyze",
    )
    assert shadow_decision.selected_mode is RouteExecutionMode.SHADOW
    assert shadow_decision.served_output_source == "canonical_route"
    assert shadow_decision.approved_for_serving is False


def test_disabled_mode_is_explicit_fail_closed():
    decision = resolve_route_policy(
        copilot="soc",
        route_name="analyze",
        env={"SOC_ROUTE_MODE": "disabled"},
    )

    assert decision.requested_mode is RouteExecutionMode.DISABLED
    assert decision.selected_mode is RouteExecutionMode.DISABLED
    assert decision.fallback_state == "fail_closed"
    assert decision.side_effect_policy == "no_route_execution"
    assert decision.errors == ("route explicitly disabled",)


def test_future_multi_copilot_policy_can_select_copilot_without_soc_inheritance():
    env = {
        "SOC_ROUTE_MODE": "shadow",
        "COPILOT_ROUTE_POLICY": "trading:canonical_only,purchasing:pipeline_read_only",
    }

    trading = resolve_route_policy(copilot="trading", route_name="analyze", env=env)
    purchasing = resolve_route_policy(copilot="purchasing", route_name="analyze", env=env)
    dataops = resolve_route_policy(copilot="dataops", route_name="analyze", env=env)

    assert trading.selected_mode is RouteExecutionMode.CANONICAL_ONLY
    assert purchasing.selected_mode is RouteExecutionMode.SHADOW
    assert purchasing.served_output_source == "canonical_route"
    assert dataops.selected_mode is RouteExecutionMode.CANONICAL_ONLY


def test_parse_copilot_route_policy():
    assert parse_copilot_route_policy("soc:shadow, trading:canonical_only") == {
        "soc": "shadow",
        "trading": "canonical_only",
    }
