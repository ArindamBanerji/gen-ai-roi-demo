"""Score-keyed SOC investigation routing for VLD Phase 1a."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES
from app.services.investigation_patterns import InvestigationPattern

POLICY_VERSION = "soc_vld_investigation_router.v2"


@dataclass(frozen=True)
class RouteDecision:
    pattern: InvestigationPattern | None
    cat_distances: dict[str, float]
    candidate_reads: list[str]
    selected_category: str | None
    propensity: float
    policy_version: str = POLICY_VERSION


@dataclass(frozen=True)
class BestCentroidScore:
    category: str
    action: str
    category_index: int
    action_index: int
    distance: float
    confidence: float


class InvestigationRouter:
    def __init__(self, patterns: dict[str, InvestigationPattern], *, L_max: int = 3) -> None:
        self.patterns = dict(patterns)
        self.L_max = int(L_max)

    def category_distances(self, v_t: np.ndarray, scorer: Any) -> dict[str, float]:
        centroids = getattr(scorer, "centroids", None)
        if centroids is None:
            centroids = getattr(scorer, "mu", None)
        if centroids is None:
            raise ValueError("scorer does not expose centroids/mu for VLD routing")
        mu = np.asarray(centroids, dtype=np.float64)
        v = np.asarray(v_t, dtype=np.float64).reshape(-1)
        if mu.ndim != 3:
            raise ValueError(f"centroid tensor must be 3-D, got shape {mu.shape}")
        if mu.shape[2] != v.shape[0]:
            raise ValueError(f"factor vector length {v.shape[0]} does not match centroids {mu.shape}")
        categories = list(getattr(scorer, "categories", None) or SOC_CATEGORIES)
        distances: dict[str, float] = {}
        for cat_index, category in enumerate(categories[: mu.shape[0]]):
            distances[str(category)] = float(np.min(np.linalg.norm(mu[cat_index] - v, axis=1)))
        return distances

    def score_best_from_centroids(self, v_t: np.ndarray, scorer: Any) -> BestCentroidScore:
        centroids = getattr(scorer, "centroids", None)
        if centroids is None:
            centroids = getattr(scorer, "mu", None)
        if centroids is None:
            raise ValueError("scorer does not expose centroids/mu for VLD scoring")
        mu = np.asarray(centroids, dtype=np.float64)
        v = np.asarray(v_t, dtype=np.float64).reshape(-1)
        if mu.ndim != 3:
            raise ValueError(f"centroid tensor must be 3-D, got shape {mu.shape}")
        if mu.shape[2] != v.shape[0]:
            raise ValueError(f"factor vector length {v.shape[0]} does not match centroids {mu.shape}")
        categories = list(getattr(scorer, "categories", None) or SOC_CATEGORIES)
        actions = list(getattr(scorer, "actions", None) or SCORER_ACTIONS)
        distances = np.linalg.norm(mu - v.reshape(1, 1, -1), axis=2)
        flat_index = int(np.argmin(distances))
        category_index, action_index = np.unravel_index(flat_index, distances.shape)
        logits = -distances.reshape(-1) / max(float(getattr(scorer, "tau", 0.1)), 1.0e-8)
        logits = logits - float(np.max(logits))
        exp = np.exp(logits)
        probabilities = exp / float(np.sum(exp))
        return BestCentroidScore(
            category=str(categories[category_index]),
            action=str(actions[action_index]),
            category_index=int(category_index),
            action_index=int(action_index),
            distance=float(distances[category_index, action_index]),
            confidence=float(probabilities[flat_index]),
        )

    def route_decision(
        self,
        v_t: np.ndarray,
        scorer: Any,
        investigated: set[str],
        *,
        alert_context: dict[str, Any] | None = None,
    ) -> RouteDecision:
        distances = self.category_distances(v_t, scorer)
        if len(investigated) >= self.L_max:
            return RouteDecision(None, distances, [], None, 0.0)

        sorted_categories = sorted(distances, key=lambda category: distances[category])
        eligible: list[tuple[str, InvestigationPattern]] = []
        for category in sorted_categories:
            pattern = self.patterns.get(category)
            if pattern is None or category in investigated:
                continue
            if alert_context is not None and not pattern.supports(alert_context):
                continue
            eligible.append((category, pattern))

        if not eligible:
            return RouteDecision(None, distances, [], None, 0.0)

        selected_category, selected_pattern = eligible[0]
        candidate_reads = [pattern.candidate_read for _category, pattern in eligible]
        return RouteDecision(
            selected_pattern,
            distances,
            candidate_reads,
            selected_category,
            1.0,
        )

    def route(self, v_t: np.ndarray, scorer: Any, investigated: set[str]) -> InvestigationPattern | None:
        return self.route_decision(v_t, scorer, investigated).pattern
