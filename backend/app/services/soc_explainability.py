"""Read-only SOC novelty and per-factor counterfactual explanations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence, cast

import numpy as np

from app.domains.soc.config import (
    SCORER_ACTIONS,
    SOC_CATEGORIES,
    SOC_FACTORS,
    SOC_FACTOR_SIGMA,
)


@dataclass(frozen=True)
class NoPrecedentResult:
    category: str
    min_distance: float
    threshold: float
    is_novel: bool
    known_evidence: list[str]
    missing_evidence: list[str]
    confidence_in_action: float
    similar_count: int
    nearest_action: str
    factor_distances: list[float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FactorBoundary:
    factor_name: str
    current_value: float
    boundary_value: float
    direction: str
    magnitude: float
    target_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WhatIfResult:
    category: str
    current_action: str
    nearest_alternative: dict[str, Any]
    per_factor: list[FactorBoundary]
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "current_action": self.current_action,
            "nearest_alternative": dict(self.nearest_alternative),
            "per_factor": [item.to_dict() for item in self.per_factor],
            "explanation": self.explanation,
        }


class NoPrecedentDetector:
    """Detect factor vectors outside the category's known centroid envelope."""

    def __init__(
        self,
        centroids: np.ndarray,
        *,
        categories: Sequence[str] = SOC_CATEGORIES,
        actions: Sequence[str] = SCORER_ACTIONS,
        factor_names: Sequence[str] = SOC_FACTORS,
        thresholds: Mapping[str, float] | None = None,
    ) -> None:
        array = np.asarray(centroids, dtype=np.float64)
        if array.ndim != 3:
            raise ValueError("centroids must have shape (categories, actions, factors)")
        if array.shape != (len(categories), len(actions), len(factor_names)):
            raise ValueError("centroid shape does not match category/action/factor metadata")
        if not np.all(np.isfinite(array)):
            raise ValueError("centroids must be finite")
        self.centroids = array.copy()
        self.categories = tuple(categories)
        self.actions = tuple(actions)
        self.factor_names = tuple(factor_names)
        self.thresholds = {str(key): float(value) for key, value in (thresholds or {}).items()}

    def threshold_for(self, category: str) -> float:
        category_index = self._category_index(category)
        if category in self.thresholds:
            return self.thresholds[category]
        category_centroids = self.centroids[category_index]
        center = category_centroids.mean(axis=0)
        spread = float(np.mean(np.linalg.norm(category_centroids - center, axis=1)))
        # A category-specific boundary derived from its centroid geometry. The
        # floor avoids calling a small, tightly clustered category novel for
        # harmless factor noise.
        return max(0.20, 1.5 * spread)

    def detect(
        self,
        factor_vector: Sequence[float],
        category: str,
        *,
        confidence: float | None = None,
    ) -> NoPrecedentResult:
        vector = self._vector(factor_vector)
        category_index = self._category_index(category)
        category_centroids = self.centroids[category_index]
        distances = np.linalg.norm(category_centroids - vector, axis=1)
        nearest_index = int(np.argmin(distances))
        nearest = category_centroids[nearest_index]
        factor_distances = np.abs(nearest - vector)
        threshold = self.threshold_for(category)
        is_novel = bool(float(distances[nearest_index]) > threshold)
        sigma = np.asarray([SOC_FACTOR_SIGMA[name] for name in self.factor_names])
        known = [
            name for name, delta, limit in zip(self.factor_names, factor_distances, 2.0 * sigma)
            if float(delta) <= float(limit)
        ]
        missing = [
            name for name, delta, limit in zip(self.factor_names, factor_distances, 2.0 * sigma)
            if float(delta) > float(limit)
        ]
        return NoPrecedentResult(
            category=category,
            min_distance=round(float(distances[nearest_index]), 6),
            threshold=round(float(threshold), 6),
            is_novel=is_novel,
            known_evidence=known,
            missing_evidence=missing,
            confidence_in_action=round(
                float(np.clip(confidence if confidence is not None else 1.0 / (1.0 + distances[nearest_index]), 0.0, 1.0)),
                6,
            ),
            similar_count=int(np.count_nonzero(distances <= threshold)),
            nearest_action=self.actions[nearest_index],
            factor_distances=[round(float(value), 6) for value in factor_distances],
        )

    def _category_index(self, category: str) -> int:
        try:
            return self.categories.index(category)
        except ValueError as exc:
            raise ValueError(f"Unknown SOC category: {category}") from exc

    def _vector(self, values: Sequence[float]) -> np.ndarray:
        vector = np.asarray(values, dtype=np.float64)
        if vector.shape != (len(self.factor_names),) or not np.all(np.isfinite(vector)):
            raise ValueError(f"factor_vector must contain {len(self.factor_names)} finite values")
        return cast(np.ndarray[Any, Any], vector)


class WhatIfInspector:
    """Explain the independent factor movement toward the nearest alternative."""

    def __init__(
        self,
        centroids: np.ndarray,
        *,
        categories: Sequence[str] = SOC_CATEGORIES,
        actions: Sequence[str] = SCORER_ACTIONS,
        factor_names: Sequence[str] = SOC_FACTORS,
    ) -> None:
        self.detector = NoPrecedentDetector(
            centroids,
            categories=categories,
            actions=actions,
            factor_names=factor_names,
        )

    def inspect(
        self,
        factor_vector: Sequence[float],
        category: str,
        current_action: str,
    ) -> WhatIfResult:
        vector = self.detector._vector(factor_vector)
        category_index = self.detector._category_index(category)
        centroids = self.detector.centroids[category_index]
        # Routing actions such as ``auto_remediate`` and ``refer_to_analyst``
        # are valid triage outcomes but are not centroid actions.  They still
        # need a read-only what-if explanation, so treat every scorer action
        # as an alternative when the current outcome has no centroid row.
        current_index = self.detector.actions.index(current_action) if current_action in self.detector.actions else None
        distances = np.linalg.norm(centroids - vector, axis=1)
        alternatives = [index for index in range(len(self.detector.actions)) if index != current_index]
        alternative_index = min(alternatives, key=lambda index: float(distances[index]))
        alternative_action = self.detector.actions[alternative_index]
        current_centroid = vector if current_index is None else centroids[current_index]
        alternative_centroid = centroids[alternative_index]
        boundaries: list[FactorBoundary] = []
        for name, value, left, right in zip(
            self.detector.factor_names, vector, current_centroid, alternative_centroid
        ):
            boundary = float((left + right) / 2.0)
            delta = boundary - float(value)
            if abs(delta) < 1e-9:
                direction = "none"
            else:
                direction = "increase" if delta > 0 else "decrease"
            boundaries.append(
                FactorBoundary(
                    factor_name=name,
                    current_value=round(float(value), 6),
                    boundary_value=round(boundary, 6),
                    direction=direction,
                    magnitude=round(abs(delta), 6),
                    target_action=alternative_action,
                )
            )
        meaningful = [item for item in boundaries if item.direction != "none"]
        explanation = (
            f"The current {current_action} profile is closest to {alternative_action} "
            f"as the nearest alternative. "
            f"{len(meaningful)} of {len(boundaries)} factor boundaries differ from the current vector; "
            "the listed midpoint deltas show the measured distance to that alternative."
        )
        return WhatIfResult(
            category=category,
            current_action=current_action,
            nearest_alternative={
                "action": alternative_action,
                "distance": round(float(distances[alternative_index]), 6),
                "factors_to_change": [item.to_dict() for item in meaningful],
            },
            per_factor=boundaries,
            explanation=explanation,
        )


def build_detector(scorer: Any | None = None) -> NoPrecedentDetector:
    if scorer is None:
        from app.services.gae_state import get_profile_scorer

        scorer = get_profile_scorer()
    if scorer is None:
        raise RuntimeError("SOC ProfileScorer is not initialized")
    return NoPrecedentDetector(
        np.asarray(scorer.centroids, dtype=np.float64),
        categories=SOC_CATEGORIES,
        actions=SCORER_ACTIONS,
        factor_names=SOC_FACTORS,
    )


def build_inspector(scorer: Any | None = None) -> WhatIfInspector:
    detector = build_detector(scorer)
    return WhatIfInspector(
        detector.centroids,
        categories=detector.categories,
        actions=detector.actions,
        factor_names=detector.factor_names,
    )
