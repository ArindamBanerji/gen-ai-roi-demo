"""
SimilarCasesService — retrieve k nearest-neighbour past decisions (§23.4).

Uses cosine similarity for retrieval (directional factor-profile matching).
L2 distance is the *scoring* metric (ProfileScorer); cosine is the *retrieval*
metric. They serve different purposes and must not be conflated.

Per-category θ thresholds from PROD-3 (March 14, 2026):
  lateral_movement    0.809   cloud_infrastructure 0.744
  insider_threat      0.792   threat_intel_match   0.745
  credential_access   0.787   data_exfiltration    0.772

Category filter is non-negotiable — cross-category retrieval produces
misleading agreement percentages (§23.4: "non-negotiable").

Reference: docs/soc_copilot_design_v5_6_part1.md §23.4
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (§23.4)
# ---------------------------------------------------------------------------

SIMILAR_CASES_K          = 3      # top-k results in sidebar
SIMILAR_CASES_MIN_PRIOR  = 5      # suppress sidebar if fewer decisions in category
SIMILAR_CASES_MAX_SCAN   = 500    # max verified decisions fetched per query (perf SLA)

# Per-category θ from PROD-3 (centroidal synthetic, 50 seeds, noise_rate=0.10)
SIMILAR_CASES_THETA: Dict[str, float] = {
    "credential_access":    0.787,
    "threat_intel_match":   0.745,
    "lateral_movement":     0.809,
    "data_exfiltration":    0.772,
    "insider_threat":       0.792,
    "cloud_infrastructure": 0.744,
    "_default":             0.787,  # credential_access as fallback
}


# ---------------------------------------------------------------------------
# SimilarCasesService
# ---------------------------------------------------------------------------

class SimilarCasesService:
    """Retrieve top-k similar past Decision nodes for a given alert.

    All computation is done in Python (not Cypher) for environments without
    the Neo4j Graph Data Science plugin.

    Usage
    -----
    svc = SimilarCasesService()
    cases = await svc.get_similar_cases(factor_vector, category, neo4j_client)
    pct   = svc.get_agreement_pct(cases, current_action)
    """

    # ── Cosine similarity ────────────────────────────────────────────────────

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Return cosine similarity in [0, 1].  Returns 0.0 for zero vectors."""
        a = np.asarray(v1, dtype=np.float64)
        b = np.asarray(v2, dtype=np.float64)
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        return float(np.dot(a, b) / denom) if denom > 0.0 else 0.0

    # ── θ lookup ─────────────────────────────────────────────────────────────

    @staticmethod
    def get_theta(category: str) -> float:
        """Return per-category θ (PROD-3).  Falls back to _default if unknown."""
        return SIMILAR_CASES_THETA.get(category, SIMILAR_CASES_THETA["_default"])

    # ── Neo4j query ──────────────────────────────────────────────────────────

    async def _fetch_verified_decisions(
        self,
        category: str,
        neo4j_client: Any,
        limit: int = SIMILAR_CASES_MAX_SCAN,
    ) -> List[Dict[str, Any]]:
        """
        Fetch up to *limit* verified Decision nodes for *category* from Neo4j,
        most-recent first.

        Returns a list of dicts with keys:
          decision_id, action, confidence, outcome, factor_vector, timestamp
        """
        try:
            rows = await neo4j_client.run_query(
                """
                MATCH (d:Decision)
                WHERE d.category = $category
                  AND d.factor_vector IS NOT NULL
                  AND d.outcome IS NOT NULL
                RETURN d.id            AS decision_id,
                       d.action        AS action,
                       d.confidence    AS confidence,
                       d.outcome       AS outcome,
                       d.factor_vector AS factor_vector,
                       d.timestamp     AS timestamp
                ORDER BY d.timestamp DESC
                LIMIT $limit
                """,
                {"category": category, "limit": limit},
            )
        except Exception as exc:
            log.warning("[SIMILAR-CASES] Neo4j query failed for category=%r: %s", category, exc)
            return []

        results = []
        for row in rows:
            fv = row.get("factor_vector")
            if isinstance(fv, str):
                try:
                    import json
                    fv = json.loads(fv)
                except Exception:
                    continue
            if not isinstance(fv, (list, tuple)) or len(fv) == 0:
                continue
            results.append({
                "decision_id": row.get("decision_id"),
                "action":      row.get("action"),
                "confidence":  float(row.get("confidence") or 0.0),
                "outcome":     row.get("outcome"),
                "factor_vector": [float(x) for x in fv],
                "timestamp":   row.get("timestamp"),
            })
        return results

    # ── Public API ────────────────────────────────────────────────────────────

    async def get_similar_cases(
        self,
        factor_vector: List[float],
        category: str,
        neo4j_client: Any,
        k: int = SIMILAR_CASES_K,
    ) -> List[Dict[str, Any]]:
        """
        Return up to k similar past Decision nodes for *category*.

        Category filter is non-negotiable — never returns cross-category results.
        Returns [] if fewer than SIMILAR_CASES_MIN_PRIOR verified decisions exist.

        Each returned dict adds a 'similarity' key (float in [0,1]).
        """
        decisions = await self._fetch_verified_decisions(category, neo4j_client)

        if len(decisions) < SIMILAR_CASES_MIN_PRIOR:
            log.debug(
                "[SIMILAR-CASES] Suppressing sidebar: only %d verified decisions "
                "in category=%r (min=%d)",
                len(decisions), category, SIMILAR_CASES_MIN_PRIOR,
            )
            return []

        theta = self.get_theta(category)
        scored: List[tuple[float, Dict[str, Any]]] = []

        for d in decisions:
            sim = self.cosine_similarity(factor_vector, d["factor_vector"])
            if sim >= theta:
                scored.append((sim, d))

        # Sort: similarity DESC, then timestamp DESC (recency as tie-breaker).
        # timestamp may be a neo4j DateTime or string; treat None as epoch.
        def _sort_key(item: tuple) -> tuple:
            sim, d = item
            ts = d.get("timestamp")
            ts_str = str(ts) if ts is not None else ""
            return (-sim, "" if ts is None else (-len(ts_str), ts_str))

        scored.sort(key=lambda x: (-x[0], str(x[1].get("timestamp") or "")))

        results = []
        for sim, d in scored[:k]:
            entry = dict(d)
            entry["similarity"] = round(sim, 4)
            results.append(entry)

        return results

    def get_agreement_pct(
        self,
        similar_cases: List[Dict[str, Any]],
        current_action: str,
    ) -> Optional[float]:
        """
        Return fraction of *similar_cases* whose action matches *current_action*.

        Returns None when similar_cases is empty (suppressed sidebar — cold start).
        Caller should then use the fallback template wording:
          "Calibrated from {calibration_count} verified outcomes." (no pct cited).
        """
        if not similar_cases:
            return None
        matching = sum(1 for c in similar_cases if c.get("action") == current_action)
        return matching / len(similar_cases)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

similar_cases_svc = SimilarCasesService()
