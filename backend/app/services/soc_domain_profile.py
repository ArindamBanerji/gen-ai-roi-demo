"""SOC DomainProfile side-by-side harness for DecisionPipeline readiness.

This module maps SOC-shaped analyze data into the shared DecisionPipeline
without wiring the production triage route. It is intentionally fixture-driven
for Package 5B parity tests; live route adoption belongs in a later package.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Mapping

from ci_platform.copilot_core import (
    BackgroundTaskManager,
    DecisionDraft,
    DecisionOutcome,
    DecisionPipeline,
    PersistedDecision,
    Phase4TaskSpec,
    PipelineInput,
    PipelineResult,
)


DYNAMIC_FIELDS_EXCLUDED_FROM_PARITY = frozenset(
    {
        "decision_id",
        "timestamp",
        "timestamp_epoch",
        "elapsed_seconds",
        "narrative",
        "rationale",
    }
)

SOC_SHADOW_COMPARISON_FIELDS = (
    ("recommendation", "action"),
    ("recommendation", "confidence"),
    ("recommendation", "routing_zone"),
    ("gae_scoring", "factor_vector"),
    ("gae_scoring", "factor_names"),
    ("gae_scoring", "action_probabilities"),
    ("gae_scoring", "routing_zone"),
    ("gae_scoring", "softmax_sum"),
    ("gae_scoring", "temperature"),
    ("gae_scoring", "low_confidence"),
    ("gae_scoring", "ambiguous"),
    ("referral",),
    ("referral_debug",),
    ("composite_gate",),
    ("decision_metadata",),
)


@dataclass(frozen=True)
class SOCRouteShapedInput:
    alert: Mapping[str, Any]
    context: Mapping[str, Any]
    scoring: Mapping[str, Any]
    referral: Mapping[str, Any] = field(default_factory=dict)
    referral_debug: Mapping[str, Any] = field(default_factory=dict)
    composite_gate: Mapping[str, Any] = field(default_factory=dict)
    decision_metadata: Mapping[str, Any] = field(default_factory=dict)
    decision_id: str = "side-by-side-decision"
    phase4_fail: bool = False
    phase4_mutation_payload: Mapping[str, Any] = field(default_factory=dict)


def build_soc_route_shaped_reference(route_input: SOCRouteShapedInput) -> dict[str, Any]:
    """Build current-route-shaped decision-critical output independently.

    This mirrors the final analyze response assembly in triage.py for fields
    used by side-by-side parity tests. It intentionally does not call the
    profile decision helper, so profile/reference drift is visible in tests.
    """

    scoring = dict(route_input.scoring)
    referral = dict(route_input.referral)
    selected_action = str(scoring.get("action") or "investigate")
    if referral.get("should_refer"):
        selected_action = "refer_to_analyst"
    confidence = float(scoring.get("confidence") or 0.0)
    routing_zone = route_input.decision_metadata.get("routing_zone") or scoring.get("routing_zone")
    return {
        "recommendation": {
            "action": selected_action,
            "confidence": confidence,
            **({"routing_zone": routing_zone} if routing_zone is not None else {}),
        },
        "gae_scoring": {
            "factor_vector": list(scoring.get("factor_vector") or []),
            "factor_names": list(scoring.get("factor_names") or []),
            "action_probabilities": dict(scoring.get("action_probabilities") or {}),
            **_optional_fields(
                scoring,
                (
                    "routing_zone",
                    "softmax_sum",
                    "temperature",
                    "low_confidence",
                    "ambiguous",
                ),
            ),
        },
        "referral": referral,
        "referral_debug": dict(route_input.referral_debug),
        "composite_gate": dict(route_input.composite_gate),
        "decision_metadata": dict(route_input.decision_metadata),
    }


def soc_pipeline_result_to_route_shape(result: PipelineResult) -> dict[str, Any]:
    """Project frozen PipelineResult fields into a plain route-shaped dict."""

    return {
        "recommendation": {
            "action": result.action,
            "confidence": result.confidence,
            **_optional_fields(result.metadata["decision_metadata"], ("routing_zone",)),
        },
        "gae_scoring": {
            "factor_vector": list(result.factors["factor_vector"]),
            "factor_names": list(result.factors["factor_names"]),
            "action_probabilities": dict(result.factors["action_probabilities"]),
            **_optional_fields(
                result.factors,
                (
                    "routing_zone",
                    "softmax_sum",
                    "temperature",
                    "low_confidence",
                    "ambiguous",
                ),
            ),
        },
        "referral": _plain(result.metadata["referral"]),
        "referral_debug": _plain(result.metadata["referral_debug"]),
        "composite_gate": _plain(result.metadata["composite_gate"]),
        "decision_metadata": _plain(result.metadata["decision_metadata"]),
    }


class SOCDomainProfile:
    """SOC side-by-side profile for the shared DecisionPipeline skeleton."""

    def __init__(self) -> None:
        self.events: list[str] = []
        self.phase3_completed = False
        self.phase4_started = asyncio.Event()

    async def load_subject(self, pipeline_input: PipelineInput) -> dict[str, Any]:
        self.events.append("phase1:subject")
        route_input = _route_input(pipeline_input)
        return dict(route_input.alert)

    async def load_context(
        self,
        pipeline_input: PipelineInput,
        subject: Mapping[str, Any],
    ) -> dict[str, Any]:
        self.events.append("phase1:context")
        return dict(_route_input(pipeline_input).context)

    def compute_decision(
        self,
        pipeline_input: PipelineInput,
        subject: Mapping[str, Any],
        context: Mapping[str, Any],
    ) -> DecisionDraft:
        self.events.append("phase2:compute")
        route_input = _route_input(pipeline_input)
        decision = _compute_soc_profile_decision(route_input)
        return DecisionDraft(
            action=str(route_input.scoring.get("action") or "investigate"),
            confidence=float(route_input.scoring.get("confidence") or 0.0),
            factors={
                "factor_vector": list(decision["factor_vector"]),
                "factor_names": list(decision["factor_names"]),
                "action_probabilities": dict(decision["action_probabilities"]),
                **_optional_fields(
                    decision,
                    (
                        "routing_zone",
                        "softmax_sum",
                        "temperature",
                        "low_confidence",
                        "ambiguous",
                    ),
                ),
            },
            metadata={
                "candidate_action": route_input.scoring.get("action"),
                "category": subject.get("category") or context.get("category"),
            },
        )

    def apply_gates(
        self,
        pipeline_input: PipelineInput,
        subject: Mapping[str, Any],
        context: Mapping[str, Any],
        decision: DecisionDraft,
    ) -> DecisionOutcome:
        self.events.append("phase2:gates")
        route_input = _route_input(pipeline_input)
        routed = _compute_soc_profile_decision(route_input)
        return DecisionOutcome(
            action=str(routed["action"]),
            confidence=float(routed["confidence"]),
            factors={
                "factor_vector": list(routed["factor_vector"]),
                "factor_names": list(routed["factor_names"]),
                "action_probabilities": dict(routed["action_probabilities"]),
                **_optional_fields(
                    routed,
                    (
                        "routing_zone",
                        "softmax_sum",
                        "temperature",
                        "low_confidence",
                        "ambiguous",
                    ),
                ),
            },
            metadata={
                "referral": dict(routed["referral"]),
                "referral_debug": dict(routed["referral_debug"]),
                "composite_gate": dict(routed["composite_gate"]),
                "decision_metadata": dict(routed["decision_metadata"]),
            },
        )

    async def persist_decision(
        self,
        pipeline_input: PipelineInput,
        subject: Mapping[str, Any],
        context: Mapping[str, Any],
        decision: DecisionOutcome,
    ) -> PersistedDecision:
        self.events.append("phase3:persist")
        route_input = _route_input(pipeline_input)
        self.phase3_completed = True
        return PersistedDecision(
            decision_id=route_input.decision_id,
            metadata={"proof_persisted": True, "source": "soc-side-by-side"},
        )

    def phase4_tasks(
        self,
        pipeline_input: PipelineInput,
        subject: Mapping[str, Any],
        context: Mapping[str, Any],
        decision: DecisionOutcome,
        persisted: PersistedDecision,
    ) -> list[Phase4TaskSpec]:
        self.events.append("phase4:enumerate")
        route_input = _route_input(pipeline_input)
        if not route_input.phase4_mutation_payload and not route_input.phase4_fail:
            return []

        payload = dict(route_input.phase4_mutation_payload)

        async def _non_critical_telemetry() -> None:
            self.events.append("phase4:start")
            self.phase4_started.set()
            payload["mutated"] = True
            if route_input.phase4_fail:
                raise RuntimeError("soc phase4 telemetry failed")

        return [Phase4TaskSpec(_non_critical_telemetry(), name="soc-phase4-telemetry")]


def _compute_soc_profile_decision(route_input: SOCRouteShapedInput) -> dict[str, Any]:
    scoring = dict(route_input.scoring)
    referral = dict(route_input.referral)
    action = str(scoring.get("action") or "investigate")
    if referral.get("should_refer"):
        action = "refer_to_analyst"

    return {
        "action": action,
        "confidence": float(scoring.get("confidence") or 0.0),
        "factor_vector": list(scoring.get("factor_vector") or []),
        "factor_names": list(scoring.get("factor_names") or []),
        "action_probabilities": dict(scoring.get("action_probabilities") or {}),
        **_optional_fields(
            scoring,
            (
                "routing_zone",
                "softmax_sum",
                "temperature",
                "low_confidence",
                "ambiguous",
            ),
        ),
        "referral": referral,
        "referral_debug": dict(route_input.referral_debug),
        "composite_gate": dict(route_input.composite_gate),
        "decision_metadata": dict(route_input.decision_metadata),
    }


def build_soc_route_input_from_response(
    response: Mapping[str, Any],
    *,
    alert: Mapping[str, Any] | None = None,
    context: Mapping[str, Any] | None = None,
) -> SOCRouteShapedInput:
    """Build shadow input from the canonical route response."""

    recommendation = dict(response.get("recommendation") or {})
    gae_scoring = dict(response.get("gae_scoring") or {})
    decision_metadata = {
        "decision_method": response.get("decision_method"),
        **_optional_fields(recommendation, ("routing_zone",)),
    }
    return SOCRouteShapedInput(
        alert=dict(alert or response.get("alert") or {}),
        context=dict(context or response.get("context") or {}),
        scoring={
            "action": recommendation.get("action"),
            "confidence": recommendation.get("confidence"),
            "factor_vector": list(gae_scoring.get("factor_vector") or []),
            "factor_names": list(gae_scoring.get("factor_names") or []),
            "action_probabilities": dict(gae_scoring.get("action_probabilities") or {}),
            **_optional_fields(
                gae_scoring,
                (
                    "routing_zone",
                    "softmax_sum",
                    "temperature",
                    "low_confidence",
                    "ambiguous",
                ),
            ),
        },
        referral=dict(response.get("referral") or {}),
        referral_debug=dict(response.get("referral_debug") or {}),
        composite_gate=dict(response.get("composite_gate") or {}),
        decision_metadata=decision_metadata,
        decision_id=str(recommendation.get("decision_id") or "shadow-decision"),
    )


def extract_soc_route_comparable_output(response: Mapping[str, Any]) -> dict[str, Any]:
    """Extract decision-critical comparable fields from canonical route output."""

    recommendation = dict(response.get("recommendation") or {})
    gae_scoring = dict(response.get("gae_scoring") or {})
    return {
        "recommendation": {
            **_optional_fields(recommendation, ("action", "confidence", "routing_zone")),
        },
        "gae_scoring": {
            **_optional_fields(
                gae_scoring,
                (
                    "factor_vector",
                    "factor_names",
                    "action_probabilities",
                    "routing_zone",
                    "softmax_sum",
                    "temperature",
                    "low_confidence",
                    "ambiguous",
                ),
            ),
        },
        "referral": _plain(response.get("referral") or {}),
        "referral_debug": _plain(response.get("referral_debug") or {}),
        "composite_gate": _plain(response.get("composite_gate") or {}),
        "decision_metadata": {
            "decision_method": response.get("decision_method"),
            **_optional_fields(recommendation, ("routing_zone",)),
        },
    }


def compare_soc_route_and_pipeline_outputs(
    canonical_output: Mapping[str, Any],
    pipeline_output: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare route and pipeline outputs using explicit field coverage."""

    differences: list[dict[str, Any]] = []
    covered: list[str] = []
    for path in SOC_SHADOW_COMPARISON_FIELDS:
        expected_present, expected = _get_path(canonical_output, path)
        actual_present, actual = _get_path(pipeline_output, path)
        if not expected_present and not actual_present:
            continue
        path_text = ".".join(path)
        covered.append(path_text)
        if expected_present != actual_present or expected != actual:
            differences.append(
                {
                    "path": path_text,
                    "canonical_present": expected_present,
                    "pipeline_present": actual_present,
                    "canonical": expected if expected_present else None,
                    "pipeline": actual if actual_present else None,
                }
            )

    return {
        "matched": not differences,
        "differences": differences,
        "excluded_fields": sorted(DYNAMIC_FIELDS_EXCLUDED_FROM_PARITY),
        "field_coverage": covered,
    }


async def run_soc_decision_pipeline_shadow(
    response: Mapping[str, Any],
    *,
    alert: Mapping[str, Any] | None = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a no-write DecisionPipeline shadow comparison for route diagnostics."""

    route_input = build_soc_route_input_from_response(
        response,
        alert=alert,
        context=context,
    )
    profile = SOCDomainProfile()
    tasks = BackgroundTaskManager()
    pipeline = DecisionPipeline(profile, tasks=tasks)
    result = await pipeline.run(
        PipelineInput(
            subject_id=str(route_input.alert.get("alert_id") or route_input.decision_id),
            metadata={"soc_route_input": route_input},
        )
    )
    pipeline_output = soc_pipeline_result_to_route_shape(result)
    canonical_output = extract_soc_route_comparable_output(response)
    comparison = compare_soc_route_and_pipeline_outputs(canonical_output, pipeline_output)
    return {
        "enabled": True,
        **comparison,
        "phase_order": list(result.diagnostics.phase_order),
        "background_status": dict(tasks.get_status()),
        "persistence_strategy": "shadow_noop",
        "side_effects": {
            "decision_writes": 0,
            "outcome_writes": 0,
            "proof_writes": 0,
            "counter_updates": 0,
            "graph_mutations": 0,
        },
    }


def _route_input(pipeline_input: PipelineInput) -> SOCRouteShapedInput:
    route_input = pipeline_input.metadata.get("soc_route_input")
    if not isinstance(route_input, SOCRouteShapedInput):
        raise TypeError("PipelineInput.metadata['soc_route_input'] must be SOCRouteShapedInput")
    return route_input


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_plain(item) for item in value)
    return value


def _optional_fields(source: Mapping[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: _plain(source[key]) for key in keys if key in source}


def _get_path(source: Mapping[str, Any], path: tuple[str, ...]) -> tuple[bool, Any]:
    current: Any = source
    for part in path:
        if not isinstance(current, Mapping) or part not in current:
            return False, None
        current = current[part]
    return True, _plain(current)
