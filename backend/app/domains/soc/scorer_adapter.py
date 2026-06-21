"""SOC scorer migration adapter.

Wraps ``CompoundingScorer.from_preset("soc")`` while preserving the raw
``ProfileScorer`` surface that SOC routers and tests still use.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from copilot_sdk.graph import InMemoryGraphStore
from copilot_sdk.scoring.scorer import CompoundingScorer


class SOCCompoundingScorerAdapter:
    """Drop-in replacement for SOC's legacy ``ProfileScorer`` instance."""

    def __init__(self, graph_store: Any | None = None) -> None:
        if graph_store is None:
            graph_store = InMemoryGraphStore(domain="soc")
        compound = CompoundingScorer.from_preset(
            "soc",
            graph_store=graph_store,
            enable_rl=False,
        )
        object.__setattr__(self, "_compound", compound)
        object.__setattr__(self, "_scorer", compound._scorer)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._scorer, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in {"_compound", "_scorer"}:
            object.__setattr__(self, name, value)
            return
        scorer = self.__dict__.get("_scorer")
        if scorer is not None and hasattr(scorer, name):
            setattr(scorer, name, value)
            return
        object.__setattr__(self, name, value)

    def score(
        self,
        factor_vector: Any = None,
        category_index: int | None = None,
        **kwargs: Any,
    ) -> Any:
        """Legacy ``ProfileScorer.score(f, category_index=...)`` API."""
        if factor_vector is None and "f" in kwargs:
            factor_vector = kwargs.pop("f")
        if category_index is None and "category_index" in kwargs:
            category_index = kwargs.pop("category_index")
        if kwargs:
            unexpected = ", ".join(sorted(kwargs))
            raise TypeError(f"unexpected score() keyword argument(s): {unexpected}")
        if category_index is None:
            raise TypeError("category_index is required")
        return self._scorer.score(factor_vector, category_index=category_index)

    def update(
        self,
        factor_vector: Any = None,
        category_index: int | None = None,
        action_index: int | None = None,
        correct: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Legacy ``ProfileScorer.update(...)`` API."""
        if factor_vector is None and "f" in kwargs:
            factor_vector = kwargs.pop("f")
        if category_index is None and "category_index" in kwargs:
            category_index = kwargs.pop("category_index")
        if action_index is None and "action_index" in kwargs:
            action_index = kwargs.pop("action_index")
        if category_index is None:
            raise TypeError("category_index is required")
        if action_index is None:
            raise TypeError("action_index is required")
        return self._scorer.update(
            f=factor_vector,
            category_index=category_index,
            action_index=action_index,
            correct=correct,
            **kwargs,
        )

    def reestimate_dk(self) -> None:
        """Legacy DK re-estimation API."""
        return self._scorer.reestimate_dk()

    def get_phase(self, category_index: int) -> str:
        """Legacy per-category phase API."""
        return self._scorer.get_phase(category_index)

    def get_dk_weights(self, category_index: int | None = None) -> Any:
        """Return raw ProfileScorer DK weights."""
        if category_index is not None:
            return self._scorer.get_dk_weights(category_index)
        return self._scorer._dk_weights

    def category_count(self, category_index: int) -> int:
        """Return observed update count for one category."""
        return int(np.asarray(self._scorer.counts[category_index]).sum())

    def get_centroid(self, category: str, action: str) -> list[float] | None:
        category_index = self._scorer.categories.index(category)
        action_index = self._scorer.actions.index(action)
        return self._scorer.mu[category_index][action_index].tolist()

    def get_category_phase(self, category: str) -> str:
        category_index = self._scorer.categories.index(category)
        return self._scorer.get_phase(category_index)
