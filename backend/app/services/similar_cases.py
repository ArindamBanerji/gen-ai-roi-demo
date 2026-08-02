"""
SimilarCasesService -- retrieve k nearest-neighbour past decisions (Sec.23.4).

Uses cosine similarity for retrieval (directional factor-profile matching).
L2 distance is the *scoring* metric (ProfileScorer); cosine is the *retrieval*
metric. They serve different purposes and must not be conflated.

Per-category theta thresholds from PROD-3 (March 14, 2026):
  lateral_movement    0.809   cloud_infrastructure 0.744
  insider_threat      0.792   malware_execution    0.745
  credential_access   0.787   data_exfiltration    0.772

Category filter is non-negotiable -- cross-category retrieval produces
misleading agreement percentages (Sec.23.4: "non-negotiable").

Reference: docs/soc_copilot_design_v5_6_part1.md Sec.23.4
"""

from __future__ import annotations

import logging
from typing import Dict

from app.framework.similar_cases_base import (  # noqa: F401 -- re-export constants for callers
    SimilarCasesBase,
    SIMILAR_CASES_K,
    SIMILAR_CASES_MIN_PRIOR,
    SIMILAR_CASES_MAX_SCAN,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SOC per-category θ thresholds (PROD-3, March 14, 2026)
# ---------------------------------------------------------------------------

SIMILAR_CASES_THETA: Dict[str, float] = {
    "credential_access":    0.787,
    "malware_execution":    0.745,
    "lateral_movement":     0.809,
    "data_exfiltration":    0.772,
    "insider_threat":       0.792,
    "cloud_infrastructure": 0.744,
    "_default":             0.787,  # credential_access as fallback
}


# ---------------------------------------------------------------------------
# SimilarCasesService — SOC implementation
# ---------------------------------------------------------------------------

class SimilarCasesService(SimilarCasesBase):
    """Retrieve top-k similar past Decision nodes for a given alert.

    Inherits all retrieval/scoring logic from SimilarCasesBase.
    Supplies SOC-specific per-category theta thresholds (PROD-3).

    Usage
    -----
    svc = SimilarCasesService()
    cases = await svc.get_similar_cases(factor_vector, category, graph_client)
    pct   = svc.get_agreement_pct(cases, current_action)
    """

    def get_theta(self, category: str) -> float:
        """Return per-category theta (PROD-3).  Falls back to _default if unknown."""
        return SIMILAR_CASES_THETA.get(category, SIMILAR_CASES_THETA["_default"])


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

similar_cases_svc = SimilarCasesService()
