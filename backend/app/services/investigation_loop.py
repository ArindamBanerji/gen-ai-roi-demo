"""Read-only SOC VLD investigation loop."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np

from app.domains.soc.config import SOC_CATEGORIES, resolve_alert_category
from app.models.investigation import InvestigationResult, InvestigationStep
from app.services.investigation_router import InvestigationRouter

RESIDUAL_THRESHOLD = 1.0e-3


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
    ) -> None:
        if L_max < 1:
            raise ValueError("L_max must be >= 1")
        if not 0.0 < eps <= 1.0:
            raise ValueError("eps must be in (0, 1]")
        self.scorer = scorer
        self.router = router
        self.factor_provider = factor_provider
        self.L_max = int(L_max)
        self.eps = float(eps)
        self.residual_threshold = float(residual_threshold)
        self.max_flips = int(max_flips)

    async def investigate(self, alert_context: dict[str, Any], graph_store: Any) -> InvestigationResult:
        initial_category = _resolve_category(alert_context)
        v_raw, _provenance = await self.factor_provider.compute(alert_context, graph_store)
        v = np.asarray(v_raw, dtype=np.float64).reshape(-1)
        initial_category_for_score = _score_category(initial_category, v, self.router, self.scorer)
        single_pass_score = self.scorer.score(v.copy(), category_index=SOC_CATEGORIES.index(initial_category_for_score))
        previous_action = str(single_pass_score.action_name)
        flip_count = 0
        trace: list[InvestigationStep] = []
        investigated: set[str] = set()
        context_for_factors = dict(alert_context)
        halt_reason = "budget_exhausted"

        for step_index in range(self.L_max):
            preferred = initial_category if step_index == 0 else None
            route = self.router.route_decision(
                v,
                self.scorer,
                investigated,
                alert_context=context_for_factors,
                preferred_category=preferred,
            )
            if route.pattern is None:
                halt_reason = "no_pattern_available"
                break

            category_before = _closest_category(route.cat_distances) or initial_category_for_score
            score_before = self.scorer.score(v.copy(), category_index=SOC_CATEGORIES.index(category_before))
            evidence = await route.pattern.execute(context_for_factors, graph_store)
            investigated.add(route.pattern.category_name)
            enriched_context = {**context_for_factors, **evidence}
            v_candidate, _candidate_provenance = await self.factor_provider.compute(alert_context, enriched_context)
            v_candidate = np.asarray(v_candidate, dtype=np.float64).reshape(-1)

            v_before = v.copy()
            v = np.clip((1.0 - self.eps) * v + self.eps * v_candidate, 0.0, 1.0)
            residual = float(np.linalg.norm(v - v_before) / max(float(np.linalg.norm(v_before)), 1.0e-8))
            distances_after = self.router.category_distances(v, self.scorer)
            category_after = _closest_category(distances_after) or category_before
            score_after = self.scorer.score(v.copy(), category_index=SOC_CATEGORIES.index(category_after))
            if str(score_after.action_name) != previous_action:
                flip_count += 1
                previous_action = str(score_after.action_name)

            halt_for_step: str | None = None
            if residual < self.residual_threshold:
                halt_reason = "residual_below_threshold"
                halt_for_step = halt_reason
            elif flip_count > self.max_flips:
                halt_reason = "oscillation"
                halt_for_step = halt_reason
            elif step_index == self.L_max - 1:
                halt_reason = "budget_exhausted"
                halt_for_step = halt_reason

            trace.append(
                InvestigationStep(
                    step=step_index,
                    pattern=route.pattern.category_name,
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
                    residual=residual,
                    halt_reason=halt_for_step,
                )
            )
            context_for_factors = enriched_context
            if halt_for_step is not None:
                break

        final_distances = self.router.category_distances(v, self.scorer)
        final_category = _closest_category(final_distances) or initial_category_for_score
        final_score = self.scorer.score(v.copy(), category_index=SOC_CATEGORIES.index(final_category))
        if trace and trace[-1].halt_reason is None:
            trace[-1].halt_reason = halt_reason
        return InvestigationResult(
            action=str(final_score.action_name),
            confidence=float(final_score.confidence),
            category=final_category,
            trace=trace,
            v_final=[float(x) for x in v.tolist()],
            steps=len(trace),
            single_pass_action=str(single_pass_score.action_name),
            single_pass_confidence=float(single_pass_score.confidence),
            agreement=str(final_score.action_name) == str(single_pass_score.action_name),
            fixture_source=_fixture_source(alert_context),
        )


def _resolve_category(alert_context: dict[str, Any]) -> str:
    raw = str(alert_context.get("category") or "").strip()
    if raw in SOC_CATEGORIES:
        return raw
    resolved = resolve_alert_category(str(alert_context.get("alert_type") or ""))
    return str(resolved) if resolved in SOC_CATEGORIES else str(SOC_CATEGORIES[0])


def _closest_category(distances: dict[str, float]) -> str | None:
    if not distances:
        return None
    return str(min(distances, key=lambda category: distances[category]))


def _score_category(category: str, v: np.ndarray, router: InvestigationRouter, scorer: Any) -> str:
    if category in SOC_CATEGORIES:
        return category
    return _closest_category(router.category_distances(v, scorer)) or SOC_CATEGORIES[0]


def _fixture_source(alert_context: dict[str, Any]) -> str | None:
    origin = str(alert_context.get("origin") or alert_context.get("fixture_source") or "")
    if origin in {"zero_day_synthetic", "zero_day_demo", "planted"}:
        return "planted"
    return None
