"""
backend/app/state/graph_snapshot.py -- Block 8.5 Phase 7

GraphSnapshot: single source of truth for all display-layer statistics
that have a graph equivalent. Eliminates the LearningState split-read
pattern that caused verified_decisions to reset on restart.

Design contract:
    1. On startup: initialize from graph (GraphSnapshot.from_graph())
    2. On verified decision: write graph FIRST, update snapshot AFTER
    3. All tab reads use snapshot (O(1), never a graph query per render)
    4. If graph write fails -> exception -> snapshot unchanged -> consistent
    5. Silent divergence is structurally impossible

Fields that move FROM LearningState TO here (Phase 7 full wiring):
    decision_count      -> verified_decisions
    override_rate       -> override_rate
    override_quality    -> override_quality
    category_counts     -> category_counts
    iks_score           -> iks_score

Fields that STAY in LearningState (no graph equivalent):
    centroid_tensor     -- centroid sync already explicit
    frozen_accuracy     -- no graph equivalent
    learning_enabled    -- control flag, not a stat
    conservation_state  -- computed from snapshot fields

Pattern rule (carry forward to every future feature):
    Any statistic that:
        (a) appears in multiple tabs AND
        (b) has a graph equivalent
    goes in GraphSnapshot. Never in LearningState first.
    That is how this bug was created.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from ci_platform.graph.age_client import AGEClient

logger = logging.getLogger(__name__)


@dataclass
class GraphSnapshot:
    """
    Derived statistics initialized from graph on startup,
    updated in sync with every graph write.
    """
    verified_decisions: int = 0
    correct_decisions: int = 0
    override_rate: float = 0.0
    override_quality: float = 0.0
    category_counts: Dict[str, int] = field(default_factory=dict)
    iks_score: float = 0.0

    @classmethod
    async def from_graph(cls, graph_client: "AGEClient") -> "GraphSnapshot":
        """
        Build snapshot from graph. Called on startup.
        Closes the restart gap -- all stats read from graph, not memory.
        """
        snap = cls()

        # verified_decisions
        snap.verified_decisions = await graph_client.count_verified_decisions()

        # correct_decisions — Decision nodes with outcome='correct' OR correct=true.
        # Bootstrap source: these fields are set by triage outcome writes and by
        # support/setup/bootstrap_learning_loop.py for historical migrations.
        snap.correct_decisions = await graph_client.count_correct_decisions()

        # category_counts
        snap.category_counts = await graph_client.count_decisions_by_category()

        # override_rate and override_quality
        outcome_stats = await graph_client.compute_outcome_stats()
        snap.override_rate = outcome_stats.get("override_rate", 0.0)
        snap.override_quality = outcome_stats.get("override_quality", 0.0)

        # IKS — prefer the graph client's own value when it is non-zero, but
        # fall back to the visible scorer-driven path when the backend returns
        # a sentinel placeholder (AGE currently returns 0.0).
        from app.services.iks import compute_visible_iks

        snap.iks_score = await graph_client.compute_iks()
        if snap.iks_score == 0.0:
            snap.iks_score = await compute_visible_iks(graph_client)

        logger.info(
            f"GraphSnapshot initialized: "
            f"{snap.verified_decisions} decisions, "
            f"correct={snap.correct_decisions}, "
            f"override_rate={snap.override_rate:.3f}, "
            f"IKS={snap.iks_score:.1f}"
        )
        return snap

    def on_verified_decision(
        self,
        category: str,
        was_override: bool,
        quality_signal: float,
        is_correct: bool,
    ) -> None:
        """
        Called AFTER successful graph write. Never called if write fails.
        Updates all derived statistics atomically.
        """
        self.verified_decisions += 1
        if is_correct:
            self.correct_decisions += 1

        self.category_counts[category] = (
            self.category_counts.get(category, 0) + 1
        )

        n = self.verified_decisions
        self.override_rate = self._rolling_update(
            self.override_rate,
            1.0 if was_override else 0.0,
            n,
        )
        if was_override and self.override_rate > 0:
            n_overrides = max(1, int(self.override_rate * n))
            self.override_quality = self._rolling_update(
                self.override_quality, quality_signal, n_overrides
            )

    def on_iks_recalculated(self, new_iks: float) -> None:
        """Called after centroid update + IKS recalculation."""
        self.iks_score = new_iks

    # Band thresholds: (min_count_inclusive, label) ordered high → low
    _BAND_THRESHOLDS = [(500, "expert"), (200, "calibrating"), (50, "learning")]

    def _band(self, count: int) -> str:
        for threshold, label in self._BAND_THRESHOLDS:
            if count >= threshold:
                return label
        return "novice"

    def get_epistemic_state(self) -> Dict[str, Dict]:
        """Per-category epistemic state: count + knowledge band."""
        return {
            cat: {"count": cnt, "band": self._band(cnt)}
            for cat, cnt in (self.category_counts or {}).items()
        }

    @staticmethod
    def _rolling_update(current: float, new_val: float, n: int) -> float:
        """Incremental mean. Numerically stable for large n."""
        if n <= 0:
            return new_val
        return current + (new_val - current) / n


# =============================================================================
# Module-level singleton — set once at startup, read everywhere.
# Pattern mirrors gae_state._learning_state for test patchability.
# =============================================================================

_snapshot: Optional["GraphSnapshot"] = None


def set_snapshot(snap: "GraphSnapshot") -> None:
    """Called once in startup_event() after from_graph() completes."""
    global _snapshot
    _snapshot = snap


def get_snapshot() -> "GraphSnapshot":
    """
    Return the live GraphSnapshot.

    Raises RuntimeError if called before startup_event() completes.
    All endpoint callers should guard with try/except RuntimeError.
    """
    if _snapshot is None:
        raise RuntimeError(
            "GraphSnapshot not initialized -- startup_event() has not run yet."
        )
    return _snapshot
