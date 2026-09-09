"""Read-only SOC VLD investigation loop."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

import numpy as np

from app.domains.soc.config import SOC_CATEGORIES
from app.models.investigation import InvestigationResult, InvestigationStep
from app.services.investigation_router import InvestigationRouter
from app.services.triage_providers import build_evidence_scoped_graph

RESIDUAL_THRESHOLD = 0.05
AggregationMethod = Literal["reextract", "damped"]


class InvestigationLoop:
    def __init__(
        self,
        scorer: Any,
        router: InvestigationRouter,
        factor_provider: Any,
        *,
        L_max: int = 3,
        eps: float = 0.3,
        residual_threshold: float = RESIDUAL_THRESHOLD,
        max_flips: int = 2,
        aggregation_method: AggregationMethod = "reextract",
    ) -> None:
        if L_max < 1:
            raise ValueError("L_max must be >= 1")
        if not 0.0 < eps <= 1.0:
            raise ValueError("eps must be in (0, 1]")
        if aggregation_method not in {"reextract", "damped"}:
            raise ValueError("aggregation_method must be 'reextract' or 'damped'")
        self.scorer = scorer
        self.router = router
        self.factor_provider = factor_provider
        self.L_max = int(L_max)
        self.eps = float(eps)
        self.residual_threshold = float(residual_threshold)
        self.max_flips = int(max_flips)
        self.aggregation_method = aggregation_method

    async def investigate(self, alert_context: dict[str, Any], graph_store: Any) -> InvestigationResult:
        supplied_category = _alert_category_for_trace(alert_context)
        v_raw, _provenance = await self.factor_provider.compute(alert_context, graph_store)
        surface_features = np.asarray(v_raw, dtype=np.float64).reshape(-1)
        v = surface_features.copy()
        single_pass_distances = self.router.category_distances(v, self.scorer)
        single_pass_category = _closest_category(single_pass_distances)
        single_pass_action, single_pass_confidence = _nearest_action(v, single_pass_category, self.scorer)
        previous_action = single_pass_action
        flip_count = 0
        trace: list[InvestigationStep] = []
        investigated: set[str] = set()
        investigated_category: str | None = None
        admitted_evidence: list[dict[str, Any]] = []
        halt_reason = "budget_exhausted"

        for step_index in range(self.L_max):
            route = self.router.route_decision(
                v,
                self.scorer,
                investigated,
                alert_context=alert_context,
            )
            if route.pattern is None:
                halt_reason = "no_pattern_available"
                break

            evidence = await route.pattern.execute(alert_context, graph_store)
            investigated.add(route.pattern.category_name)
            investigated_category = route.pattern.category_name
            admitted_evidence.append(evidence)
            evidence_graph = build_evidence_scoped_graph(graph_store, admitted_evidence, surface_features)
            v_candidate_raw, _candidate_provenance = await self.factor_provider.compute(alert_context, evidence_graph)
            v_candidate = np.asarray(v_candidate_raw, dtype=np.float64).reshape(-1)

            v_before = v.copy()
            target_residual = float(
                np.linalg.norm(v_candidate - v_before) / max(float(np.linalg.norm(v_before)), 1.0e-8)
            )
            if self.aggregation_method == "reextract":
                v = np.clip(v_candidate, 0.0, 1.0)
            else:
                v = np.clip((1.0 - self.eps) * v + self.eps * v_candidate, 0.0, 1.0)
            distances_after = self.router.category_distances(v, self.scorer)
            selected_category = _closest_category(distances_after)
            action_after, _confidence_after = _nearest_action(v, selected_category, self.scorer)
            if action_after != previous_action:
                flip_count += 1
                previous_action = action_after

            halt_for_step: str | None = None
            if target_residual < self.residual_threshold:
                halt_reason = "residual_below_threshold"
                halt_for_step = halt_reason
            elif flip_count >= self.max_flips:
                halt_reason = "oscillation"
                halt_for_step = halt_reason
            elif step_index == self.L_max - 1:
                halt_reason = "budget_exhausted"
                halt_for_step = halt_reason

            trace.append(
                InvestigationStep(
                    step=step_index,
                    pattern=route.pattern.category_name,
                    alert_category=supplied_category,
                    v_before=[float(x) for x in v_before.tolist()],
                    v_after=[float(x) for x in v.tolist()],
                    cat_distances_before=route.cat_distances,
                    cat_distances_after=distances_after,
                    evidence_keys=[str(key) for key in evidence.get("evidence_keys", sorted(evidence.keys()))],
                    candidate_reads=route.candidate_reads,
                    selected_edge=route.pattern.selected_edge,
                    propensity=float(route.propensity),
                    cost=float(evidence.get("read_cost", 1.0) or 1.0),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    policy_version=route.policy_version,
                    residual=target_residual,
                    halt_reason=halt_for_step,
                )
            )
            if halt_for_step is not None:
                break

        final_score = self.router.score_best_from_centroids(v, self.scorer)
        if trace and trace[-1].halt_reason is None:
            trace[-1].halt_reason = halt_reason
        return InvestigationResult(
            action=final_score.action,
            confidence=float(final_score.confidence),
            category=final_score.category,
            investigated_category=investigated_category,
            routing_agreed=investigated_category == final_score.category if investigated_category is not None else True,
            trace=trace,
            v_final=[float(x) for x in v.tolist()],
            steps=len(trace),
            single_pass_action=single_pass_action,
            single_pass_confidence=single_pass_confidence,
            agreement=final_score.action == single_pass_action,
            fixture_source=_fixture_source(alert_context),
            halt_reason=halt_reason,
        )


def _closest_category(distances: dict[str, float]) -> str:
    if not distances:
        return str(SOC_CATEGORIES[0])
    return str(min(distances, key=lambda category: distances[category]))


def _nearest_action(v: np.ndarray, category: str, scorer: Any) -> tuple[str, float]:
    raw_centroids = getattr(scorer, "centroids", None)
    if raw_centroids is None:
        raw_centroids = getattr(scorer, "mu")
    centroids = np.asarray(raw_centroids, dtype=np.float64)
    category_index = SOC_CATEGORIES.index(category)
    distances = np.linalg.norm(centroids[category_index] - np.asarray(v, dtype=np.float64).reshape(-1), axis=1)
    action_index = int(np.argmin(distances))
    actions = list(getattr(scorer, "actions", ["escalate", "investigate", "suppress", "monitor"]))
    logits = -distances / max(float(getattr(scorer, "tau", 0.1)), 1.0e-8)
    logits = logits - float(np.max(logits))
    exp = np.exp(logits)
    probs = exp / float(np.sum(exp))
    return str(actions[action_index]), float(probs[action_index])


def _alert_category_for_trace(alert_context: dict[str, Any]) -> str | None:
    value = alert_context.get("category") or alert_context.get("alert_type")
    if value is None:
        return None
    return str(value)


def _fixture_source(alert_context: dict[str, Any]) -> str | None:
    origin = str(alert_context.get("origin") or alert_context.get("fixture_source") or "")
    if origin in {"zero_day_synthetic", "zero_day_demo", "planted"}:
        return "planted"
    return None
