"""Comparator policies for SOC VLD rho measurement."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

import numpy as np

from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES
from app.models.investigation import InvestigationResult, InvestigationStep
from app.services.investigation_patterns import InvestigationPattern
from app.services.investigation_router import InvestigationRouter
from app.services.triage_providers import build_evidence_scoped_graph


class SinglePassPolicy:
    policy = "single_pass"

    async def investigate(self, alert_context: dict[str, Any], scorer: Any, factor_provider: Any, graph_store: Any) -> InvestigationResult:
        v_raw, _ = await factor_provider.compute(alert_context, graph_store)
        v = np.asarray(v_raw, dtype=np.float64).reshape(-1)
        router = InvestigationRouter({})
        score = router.score_best_from_centroids(v, scorer)
        return _result(
            policy=self.policy,
            action=score.action,
            confidence=float(score.confidence),
            category=score.category,
            investigated_category=None,
            v=v,
            single_pass_action=score.action,
            single_pass_confidence=float(score.confidence),
            trace=[],
            halt_reason="single_pass",
        )


class ContentRulePolicy:
    policy = "content_rule"

    def __init__(self, patterns: dict[str, InvestigationPattern] | None = None) -> None:
        self.patterns = dict(patterns or {})

    async def investigate(self, alert_context: dict[str, Any], scorer: Any, factor_provider: Any, graph_store: Any) -> InvestigationResult:
        category = str(alert_context.get("category") or alert_context.get("alert_type") or "")
        if category not in self.patterns:
            return await SinglePassPolicy().investigate(alert_context, scorer, factor_provider, graph_store)
        return await _one_or_many_pattern_result(
            policy=self.policy,
            alert_context=alert_context,
            scorer=scorer,
            factor_provider=factor_provider,
            graph_store=graph_store,
            patterns=[self.patterns[category]],
        )


class MajorityBranchPolicy:
    policy = "majority_branch"

    def __init__(self, majority_category: str, patterns: dict[str, InvestigationPattern] | None = None) -> None:
        self.majority_category = majority_category
        self.patterns = dict(patterns or {})

    async def investigate(self, alert_context: dict[str, Any], scorer: Any, factor_provider: Any, graph_store: Any) -> InvestigationResult:
        pattern = self.patterns.get(self.majority_category)
        if pattern is None:
            return await SinglePassPolicy().investigate(alert_context, scorer, factor_provider, graph_store)
        return await _one_or_many_pattern_result(
            policy=self.policy,
            alert_context=alert_context,
            scorer=scorer,
            factor_provider=factor_provider,
            graph_store=graph_store,
            patterns=[pattern],
        )


class RandomBranchPolicy:
    policy = "random_branch"

    def __init__(self, patterns: dict[str, InvestigationPattern] | None = None, *, seed: int = 0) -> None:
        self.patterns = dict(patterns or {})
        self.seed = int(seed)

    async def investigate(self, alert_context: dict[str, Any], scorer: Any, factor_provider: Any, graph_store: Any) -> InvestigationResult:
        if not self.patterns:
            return await SinglePassPolicy().investigate(alert_context, scorer, factor_provider, graph_store)
        alert_id = str(alert_context.get("alert_id") or alert_context.get("id") or "")
        rng = random.Random(f"{self.seed}:{alert_id}")
        pattern = self.patterns[rng.choice(sorted(self.patterns))]
        return await _one_or_many_pattern_result(
            policy=self.policy,
            alert_context=alert_context,
            scorer=scorer,
            factor_provider=factor_provider,
            graph_store=graph_store,
            patterns=[pattern],
        )


class BreadthPolicy:
    policy = "breadth_all"

    def __init__(self, patterns: dict[str, InvestigationPattern] | None = None) -> None:
        self.patterns = dict(patterns or {})

    async def investigate(self, alert_context: dict[str, Any], scorer: Any, factor_provider: Any, graph_store: Any) -> InvestigationResult:
        ordered = [self.patterns[name] for name in SOC_CATEGORIES if name in self.patterns]
        if not ordered:
            return await SinglePassPolicy().investigate(alert_context, scorer, factor_provider, graph_store)
        return await _one_or_many_pattern_result(
            policy=self.policy,
            alert_context=alert_context,
            scorer=scorer,
            factor_provider=factor_provider,
            graph_store=graph_store,
            patterns=ordered,
        )


async def _one_or_many_pattern_result(
    *,
    policy: str,
    alert_context: dict[str, Any],
    scorer: Any,
    factor_provider: Any,
    graph_store: Any,
    patterns: list[InvestigationPattern],
) -> InvestigationResult:
    surface_raw, _ = await factor_provider.compute(alert_context, graph_store)
    surface = np.asarray(surface_raw, dtype=np.float64).reshape(-1)
    router = InvestigationRouter({})
    before_distances = router.category_distances(surface, scorer)
    single_category = _closest_category(before_distances)
    single_action, single_confidence = _nearest_action(surface, single_category, scorer)
    admitted: list[dict[str, Any]] = []
    trace: list[InvestigationStep] = []
    v = surface.copy()
    candidate_reads = [pattern.candidate_read for pattern in patterns]
    for idx, pattern in enumerate(patterns):
        before = v.copy()
        distances_before = router.category_distances(before, scorer)
        evidence = await pattern.execute(alert_context, graph_store)
        admitted.append(evidence)
        evidence_graph = build_evidence_scoped_graph(graph_store, admitted, surface)
        v_raw, _ = await factor_provider.compute(alert_context, evidence_graph)
        v = np.asarray(v_raw, dtype=np.float64).reshape(-1)
        distances_after = router.category_distances(v, scorer)
        trace.append(
            InvestigationStep(
                step=idx,
                pattern=pattern.category_name,
                alert_category=_alert_category(alert_context),
                v_before=[float(x) for x in before.tolist()],
                v_after=[float(x) for x in v.tolist()],
                cat_distances_before=distances_before,
                cat_distances_after=distances_after,
                evidence_keys=[str(key) for key in evidence.get("evidence_keys", sorted(evidence.keys()))],
                candidate_reads=candidate_reads,
                selected_edge=pattern.selected_edge,
                propensity=1.0 / float(len(patterns)),
                cost=float(evidence.get("read_cost", 1.0) or 1.0),
                timestamp=datetime.now(timezone.utc).isoformat(),
                policy_version=policy,
                residual=float(np.linalg.norm(v - before) / max(float(np.linalg.norm(before)), 1.0e-8)),
                halt_reason="budget_exhausted" if idx == len(patterns) - 1 else None,
            )
        )
    score = router.score_best_from_centroids(v, scorer)
    investigated_category = trace[-1].pattern if trace else None
    return _result(
        policy=policy,
        action=score.action,
        confidence=float(score.confidence),
        category=score.category,
        investigated_category=investigated_category,
        v=v,
        single_pass_action=single_action,
        single_pass_confidence=single_confidence,
        trace=trace,
        halt_reason="budget_exhausted",
    )


def _result(
    *,
    policy: str,
    action: str,
    confidence: float,
    category: str,
    investigated_category: str | None,
    v: np.ndarray,
    single_pass_action: str,
    single_pass_confidence: float,
    trace: list[InvestigationStep],
    halt_reason: str,
) -> InvestigationResult:
    return InvestigationResult(
        action=action,
        confidence=confidence,
        category=category,
        investigated_category=investigated_category,
        routing_agreed=investigated_category == category if investigated_category is not None else True,
        trace=trace,
        v_final=[float(x) for x in v.tolist()],
        steps=len(trace),
        single_pass_action=single_pass_action,
        single_pass_confidence=single_pass_confidence,
        agreement=action == single_pass_action,
        halt_reason=halt_reason,
        policy=policy,
    )


def _closest_category(distances: dict[str, float]) -> str:
    return str(min(distances, key=lambda category: distances[category])) if distances else str(SOC_CATEGORIES[0])


def _nearest_action(v: np.ndarray, category: str, scorer: Any) -> tuple[str, float]:
    raw_centroids = getattr(scorer, "centroids", None)
    if raw_centroids is None:
        raw_centroids = getattr(scorer, "mu")
    centroids = np.asarray(raw_centroids, dtype=np.float64)
    distances = np.linalg.norm(centroids[SOC_CATEGORIES.index(category)] - np.asarray(v, dtype=np.float64), axis=1)
    action_index = int(np.argmin(distances))
    actions = list(getattr(scorer, "actions", SCORER_ACTIONS))
    logits = -distances / max(float(getattr(scorer, "tau", 0.1)), 1.0e-8)
    logits = logits - float(np.max(logits))
    probs = np.exp(logits) / float(np.sum(np.exp(logits)))
    return str(actions[action_index]), float(probs[action_index])


def _alert_category(alert_context: dict[str, Any]) -> str | None:
    value = alert_context.get("category") or alert_context.get("alert_type")
    return str(value) if value is not None else None
