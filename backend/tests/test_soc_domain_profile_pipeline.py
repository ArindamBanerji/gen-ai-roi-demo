import json
import inspect

import pytest

from ci_platform.copilot_core import BackgroundTaskManager, DecisionPipeline, PipelineInput
import app.services.soc_domain_profile as soc_domain_profile
from app.services.soc_domain_profile import (
    DYNAMIC_FIELDS_EXCLUDED_FROM_PARITY,
    SOCDomainProfile,
    SOCRouteShapedInput,
    build_soc_route_shaped_reference,
    compare_soc_route_and_pipeline_outputs,
    run_soc_decision_pipeline_shadow,
    soc_pipeline_result_to_route_shape,
)


def _route_input(*, should_refer=False, phase4_fail=False, phase4_payload=None):
    return SOCRouteShapedInput(
        alert={
            "alert_id": "SOC-P5B-1",
            "alert_type": "impossible_travel",
            "category": "identity",
            "severity": "high",
            "source_location": "Berlin",
            "user_id": "user-1",
            "asset_id": "asset-1",
        },
        context={
            "user_id": "user-1",
            "asset_id": "asset-1",
            "category": "identity",
            "mfa_completed": False,
        },
        scoring={
            "action": "investigate",
            "confidence": 0.82,
            "factor_vector": [0.91, 0.42, 0.18],
            "factor_names": ["identity_risk", "asset_criticality", "mfa_gap"],
            "action_probabilities": {
                "investigate": 0.82,
                "monitor": 0.11,
                "escalate": 0.07,
            },
            "routing_zone": "human_review" if should_refer else "agent_zone",
            "softmax_sum": 1.0,
            "temperature": 0.1,
            "low_confidence": False,
            "ambiguous": False,
        },
        referral={
            "should_refer": should_refer,
            "reasons": ["rapid_succession"] if should_refer else [],
            "audit_summary": "route-shaped referral",
        },
        referral_debug={
            "sequence_count": 3 if should_refer else 1,
            "cross_category_count": 1,
            "graph_source": "fresh",
        },
        composite_gate={
            "auto_approve": False,
            "reason_codes": ["human_review"] if should_refer else ["agent_zone"],
        },
        decision_metadata={
            "category": "identity",
            "routing_zone": "human_review" if should_refer else "agent_zone",
            "decision_method": "gae_scoring",
        },
        decision_id="DYNAMIC-DECISION-ID",
        phase4_fail=phase4_fail,
        phase4_mutation_payload=phase4_payload or {},
    )


async def _run_pipeline(route_input):
    profile = SOCDomainProfile()
    tasks = BackgroundTaskManager()
    pipeline = DecisionPipeline(profile, tasks=tasks)
    result = await pipeline.run(
        PipelineInput(
            subject_id=str(route_input.alert["alert_id"]),
            metadata={"soc_route_input": route_input},
        )
    )
    return profile, tasks, result, soc_pipeline_result_to_route_shape(result)


@pytest.mark.asyncio
async def test_soc_domain_profile_matches_route_shaped_reference_for_agent_zone():
    route_input = _route_input()
    reference = build_soc_route_shaped_reference(route_input)

    profile, tasks, result, projected = await _run_pipeline(route_input)

    assert projected == reference
    assert result.diagnostics.phase_order == ("phase1", "phase2", "phase3", "phase4")
    assert profile.events == [
        "phase1:subject",
        "phase1:context",
        "phase2:compute",
        "phase2:gates",
        "phase3:persist",
        "phase4:enumerate",
    ]
    assert profile.phase3_completed
    assert tasks.get_status()["submitted"] == 0


@pytest.mark.asyncio
async def test_soc_domain_profile_matches_route_shaped_reference_for_referral_veto():
    route_input = _route_input(should_refer=True)
    reference = build_soc_route_shaped_reference(route_input)

    _, _, _, projected = await _run_pipeline(route_input)

    assert projected["recommendation"]["action"] == "refer_to_analyst"
    assert projected == reference
    assert projected["referral"]["should_refer"] is True
    assert projected["referral_debug"]["graph_source"] == "fresh"


@pytest.mark.asyncio
async def test_soc_domain_profile_excludes_dynamic_fields_from_parity():
    route_input = _route_input()

    _, _, result, projected = await _run_pipeline(route_input)

    assert result.decision_id == "DYNAMIC-DECISION-ID"
    assert "decision_id" not in projected["decision_metadata"]
    assert "timestamp" not in projected["decision_metadata"]
    assert "decision_id" in DYNAMIC_FIELDS_EXCLUDED_FROM_PARITY
    assert "timestamp" in DYNAMIC_FIELDS_EXCLUDED_FROM_PARITY


@pytest.mark.asyncio
async def test_soc_domain_profile_phase4_failure_is_captured_not_response_critical():
    route_input = _route_input(phase4_fail=True, phase4_payload={"note": ["before"]})

    profile, tasks, result, projected = await _run_pipeline(route_input)
    await tasks.drain()

    assert projected == build_soc_route_shaped_reference(route_input)
    assert result.action == "investigate"
    assert profile.events[-1] == "phase4:start"
    status = tasks.get_status()
    assert status["failed"] == 1
    assert status["last_errors"][0]["exception_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_soc_domain_profile_phase4_payload_mutation_cannot_change_result():
    payload = {"nested": ["before"]}
    route_input = _route_input(phase4_payload=payload)

    _, tasks, result, projected = await _run_pipeline(route_input)
    await tasks.drain()
    payload["nested"].append("after")

    assert projected == build_soc_route_shaped_reference(route_input)
    assert result.factors["factor_vector"] == (0.91, 0.42, 0.18)
    with pytest.raises(AttributeError):
        result.factors["factor_vector"].append(1.0)


@pytest.mark.asyncio
async def test_soc_domain_profile_output_is_json_like_after_projection():
    route_input = _route_input(should_refer=True)

    _, _, _, projected = await _run_pipeline(route_input)

    json.dumps(projected, sort_keys=True)
    assert isinstance(projected["gae_scoring"]["factor_vector"], list)
    assert isinstance(projected["gae_scoring"]["action_probabilities"], dict)


def test_soc_profile_is_side_by_side_only_no_triage_route_adoption():
    import app.routers.triage as triage

    source = inspect.getsource(triage.analyze_alert)

    assert "DecisionPipeline" not in source
    assert "SOCDomainProfile" not in source
    assert "soc_domain_profile" not in source


def test_route_shaped_reference_is_independent_from_profile_helper(monkeypatch):
    def fail_if_called(_route_input):
        raise AssertionError("reference must not call profile decision helper")

    monkeypatch.setattr(
        soc_domain_profile,
        "_compute_soc_profile_decision",
        fail_if_called,
    )

    reference = build_soc_route_shaped_reference(_route_input(should_refer=True))

    assert reference["recommendation"]["action"] == "refer_to_analyst"
    assert reference["gae_scoring"]["factor_vector"] == [0.91, 0.42, 0.18]


def _canonical_route_response(route_input):
    reference = build_soc_route_shaped_reference(route_input)
    return {
        "alert": dict(route_input.alert),
        **reference,
        "recommendation": {
            **reference["recommendation"],
            "reasoning": "dynamic narrative excluded from parity",
            "decision_id": "generated-decision-id",
        },
        "gae_scoring": {
            **reference["gae_scoring"],
            "decision_id": "generated-decision-id",
        },
        "decision_method": route_input.decision_metadata["decision_method"],
        "narrative": {"summary": "dynamic"},
    }


@pytest.mark.asyncio
async def test_route_shadow_flag_false_preserves_output_and_does_not_run_pipeline(monkeypatch):
    import app.routers.triage as triage

    route_input = _route_input()
    response = _canonical_route_response(route_input)
    monkeypatch.setenv("USE_SOC_DECISION_PIPELINE_SHADOW", "false")

    async def fail_if_called(*_args, **_kwargs):
        raise AssertionError("shadow pipeline should not run when flag is false")

    monkeypatch.setattr(
        soc_domain_profile,
        "run_soc_decision_pipeline_shadow",
        fail_if_called,
    )

    returned = await triage._soc_maybe_attach_decision_pipeline_shadow(
        response,
        alert_data=dict(route_input.alert),
        context=dict(route_input.context),
    )

    assert returned is response
    assert "_diagnostics" not in returned


@pytest.mark.asyncio
async def test_route_shadow_flag_true_attaches_diagnostics_and_preserves_canonical(monkeypatch):
    import app.routers.triage as triage

    route_input = _route_input(should_refer=True)
    response = _canonical_route_response(route_input)
    original = json.loads(json.dumps(response, sort_keys=True))
    monkeypatch.setenv("USE_SOC_DECISION_PIPELINE_SHADOW", "true")

    returned = await triage._soc_maybe_attach_decision_pipeline_shadow(
        response,
        alert_data=dict(route_input.alert),
        context=dict(route_input.context),
    )

    diagnostic = returned["_diagnostics"]["soc_decision_pipeline_shadow"]
    assert diagnostic["enabled"] is True
    assert diagnostic["matched"] is True
    assert diagnostic["differences"] == []
    assert diagnostic["side_effects"] == {
        "decision_writes": 0,
        "outcome_writes": 0,
        "proof_writes": 0,
        "counter_updates": 0,
        "graph_mutations": 0,
    }
    without_diagnostics = dict(returned)
    without_diagnostics.pop("_diagnostics")
    assert without_diagnostics == original


@pytest.mark.asyncio
async def test_route_shadow_runner_failure_is_sanitized_and_preserves_canonical(monkeypatch):
    import app.routers.triage as triage

    route_input = _route_input()
    response = _canonical_route_response(route_input)
    original = json.loads(json.dumps(response, sort_keys=True))
    monkeypatch.setenv("USE_SOC_DECISION_PIPELINE_SHADOW", "true")

    async def fail_shadow(*_args, **_kwargs):
        raise RuntimeError("sensitive user-1 asset-1 source payload")

    monkeypatch.setattr(
        soc_domain_profile,
        "run_soc_decision_pipeline_shadow",
        fail_shadow,
    )

    returned = await triage._soc_maybe_attach_decision_pipeline_shadow(
        response,
        alert_data=dict(route_input.alert),
        context=dict(route_input.context),
    )

    diagnostic = returned["_diagnostics"]["soc_decision_pipeline_shadow"]
    assert diagnostic["status"] == "shadow_failed"
    assert diagnostic["matched"] is False
    assert diagnostic["error_type"] == "RuntimeError"
    assert diagnostic["error"] == "shadow pipeline unavailable"
    assert diagnostic["differences"] == []
    assert diagnostic["side_effects"] == {
        "decision_writes": 0,
        "outcome_writes": 0,
        "proof_writes": 0,
        "counter_updates": 0,
        "graph_mutations": 0,
    }
    diagnostic_json = json.dumps(diagnostic, sort_keys=True)
    assert "sensitive" not in diagnostic_json
    assert "user-1" not in diagnostic_json
    assert "asset-1" not in diagnostic_json
    assert "Traceback" not in diagnostic_json
    without_diagnostics = dict(returned)
    without_diagnostics.pop("_diagnostics")
    assert without_diagnostics == original


@pytest.mark.asyncio
async def test_route_shadow_comparison_failure_is_sanitized_and_preserves_canonical(monkeypatch):
    import app.routers.triage as triage

    route_input = _route_input()
    response = _canonical_route_response(route_input)
    original = json.loads(json.dumps(response, sort_keys=True))
    monkeypatch.setenv("USE_SOC_DECISION_PIPELINE_SHADOW", "true")

    def fail_compare(*_args, **_kwargs):
        raise ValueError("secret alert context should not leak")

    monkeypatch.setattr(
        soc_domain_profile,
        "compare_soc_route_and_pipeline_outputs",
        fail_compare,
    )

    returned = await triage._soc_maybe_attach_decision_pipeline_shadow(
        response,
        alert_data=dict(route_input.alert),
        context=dict(route_input.context),
    )

    diagnostic = returned["_diagnostics"]["soc_decision_pipeline_shadow"]
    assert diagnostic["status"] == "shadow_failed"
    assert diagnostic["error_type"] == "ValueError"
    assert diagnostic["error"] == "shadow pipeline unavailable"
    diagnostic_json = json.dumps(diagnostic, sort_keys=True)
    assert "secret" not in diagnostic_json
    assert "context" not in diagnostic_json
    assert "Traceback" not in diagnostic_json
    without_diagnostics = dict(returned)
    without_diagnostics.pop("_diagnostics")
    assert without_diagnostics == original


@pytest.mark.asyncio
async def test_shadow_comparison_covers_route_metadata_fields():
    route_input = _route_input()
    response = _canonical_route_response(route_input)

    diagnostic = await run_soc_decision_pipeline_shadow(
        response,
        alert=dict(route_input.alert),
        context=dict(route_input.context),
    )

    coverage = set(diagnostic["field_coverage"])
    assert "recommendation.routing_zone" in coverage
    assert "gae_scoring.routing_zone" in coverage
    assert "gae_scoring.softmax_sum" in coverage
    assert "gae_scoring.temperature" in coverage
    assert "gae_scoring.low_confidence" in coverage
    assert "gae_scoring.ambiguous" in coverage
    assert diagnostic["matched"] is True


def test_shadow_comparison_reports_mismatch_without_replacing_canonical_output():
    route_input = _route_input()
    canonical = build_soc_route_shaped_reference(route_input)
    pipeline = json.loads(json.dumps(canonical))
    pipeline["recommendation"]["action"] = "monitor"

    comparison = compare_soc_route_and_pipeline_outputs(canonical, pipeline)

    assert comparison["matched"] is False
    assert comparison["differences"] == [
        {
            "path": "recommendation.action",
            "canonical_present": True,
            "pipeline_present": True,
            "canonical": "investigate",
            "pipeline": "monitor",
        }
    ]
    assert "decision_id" in comparison["excluded_fields"]
