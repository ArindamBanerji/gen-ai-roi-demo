"""
OverrideDetector — analyst correct-override pattern detector.

Domain-agnostic. Safe to copy to copilot-sdk.

Tracks analyst overrides where the analyst was correct (agreed=False,
analyst_correct=True). Activates when a sufficient evidence base has been
accumulated (default threshold: 50 examples), at which point the system
can begin weighting analyst override patterns into its scoring logic.

Usage
-----
    detector = OverrideDetector()
    detector.load(examples)          # list of dicts from Neo4j
    if detector.activated:
        ...                          # use override patterns

Design notes
------------
- Threshold 50 is the minimum population required for override frequency
  estimates to be stable (±10 pp at 95% CI for a 50/50 base rate).
- `load()` is idempotent — re-calling with a fresh query result is safe.
- No external dependencies: pure Python, no Neo4j or domain imports here.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

log = logging.getLogger(__name__)

ACTIVATION_THRESHOLD: int = 50


class OverrideDetector:
    """
    Detects when enough analyst correct-override examples exist to activate
    override-aware scoring.

    Attributes
    ----------
    activated : bool
        True when example_count >= ACTIVATION_THRESHOLD.
    example_count : int
        Number of correct-override examples currently loaded.
    """

    def __init__(self, threshold: int = ACTIVATION_THRESHOLD) -> None:
        self._threshold: int = threshold
        self._examples: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def load(self, examples: List[Dict[str, Any]]) -> None:
        """
        Replace the current example set with *examples*.

        Typically called once at startup after querying Neo4j, and again
        after any batch of new ShadowDecision nodes are ingested.

        Parameters
        ----------
        examples:
            List of dicts representing ShadowDecision records where
            agreed=False and analyst_correct=True.
        """
        self._examples = list(examples)
        status = "ACTIVATED" if self.activated else "inactive"
        log.info(
            "[OverrideDetector] Loaded %d examples — %s (threshold=%d)",
            len(self._examples), status, self._threshold,
        )

    @property
    def activated(self) -> bool:
        """True when example_count >= threshold."""
        return len(self._examples) >= self._threshold

    @property
    def example_count(self) -> int:
        """Number of correct-override examples currently loaded."""
        return len(self._examples)

    @property
    def examples(self) -> List[Dict[str, Any]]:
        """Read-only snapshot of loaded examples."""
        return list(self._examples)

    def status(self) -> Dict[str, Any]:
        """Return a serialisable status dict for health/debug endpoints."""
        return {
            "activated":     self.activated,
            "example_count": self.example_count,
            "threshold":     self._threshold,
        }
