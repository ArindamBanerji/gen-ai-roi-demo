"""
Institutional Knowledge Score (IKS) service.

IKS measures how far the system's learned centroids have drifted from the
bootstrap prior mu_0.  A higher score means more real-world experience has been
integrated.

Formula (docs/soc_copilot_design_v1.md Sec.14):

    IKS(t) = 100 x min(
        mean( ||mu(t)[c, a, :] - mu_0[c, a, :]||_2  for all (c, a) )
        / D_MAX,
        1.0
    )

where D_MAX = 0.20 is the normalization constant (kappa*=0.20 calibrated by
PROD-1, March 18. Was 0.30 design estimate).

mu_0 is loaded from backend/app/data/iks_bootstrap_soc.json, written by
gae_state.init_learning_state() before bootstrap_calibration() mutates mu.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, cast

import numpy as np

from app.domains.soc.config import compute_phase3_minimum as _p3min
from app.db.graph_client import soc_decision_where
from app.framework.iks_base import (  # noqa: F401 -- re-export for callers
    compute_iks as _compute_iks_base,
    interpret,
    interpret_iks_v2,
)

log = logging.getLogger(__name__)

D_MAX: float = 0.20  # kappa*=0.20 calibrated by PROD-1 (March 18). Was 0.30 design estimate.

_MU_ZERO_PATH = Path(__file__).parent.parent / "data" / "iks_bootstrap_soc.json"

_mu_zero_cache: Optional[np.ndarray] = None   # lazily loaded, module-level cache


# ---------------------------------------------------------------------------
# SOC μ₀ loader
# ---------------------------------------------------------------------------

def _load_mu_zero() -> Optional[np.ndarray]:
    """Load mu_0 from the SOC sidecar JSON, with module-level caching."""
    global _mu_zero_cache
    if _mu_zero_cache is not None:
        return _mu_zero_cache
    if not _MU_ZERO_PATH.exists():
        log.warning("[IKS] mu0 file not found at %s -- IKS will be estimated", _MU_ZERO_PATH)
        return None
    try:
        with open(_MU_ZERO_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        _mu_zero_cache = np.array(data["mu_zero"], dtype=np.float64)
        log.info("[IKS] mu0 loaded from %s (shape=%s)", _MU_ZERO_PATH, list(_mu_zero_cache.shape))
        return _mu_zero_cache
    except Exception as exc:
        log.warning("[IKS] Failed to load mu0: %s", exc)
        return None


# ---------------------------------------------------------------------------
# SOC wrapper — loads μ₀ and passes SOC-calibrated D_MAX
# ---------------------------------------------------------------------------

def compute_iks(mu_t: np.ndarray, mu_zero: Optional[np.ndarray] = None) -> dict:
    """
    Compute the current IKS score (SOC wrapper).

    Parameters
    ----------
    mu_t    : np.ndarray, shape (n_categories, n_actions, n_factors)
              Current centroid tensor from ProfileScorer.
    mu_zero : np.ndarray or None
              Bootstrap prior.  If None, loaded from iks_bootstrap_soc.json.

    Returns
    -------
    dict with keys:
        current (float)      -- IKS in [0, 100]
        mean_drift (float)   -- raw mean L2 drift before normalization
        estimated (bool)     -- True if mu_0 was unavailable (IKS is approximate)
    """
    if mu_zero is None:
        mu_zero = _load_mu_zero()
    return _compute_iks_base(mu_t, mu_zero, D_MAX)


async def compute_visible_iks(
    neo4j_service=None,
    scorer=None,
) -> float:
    """
    Compute the shipped user-visible IKS score.

    Canonical order:
    1. Drift-based scorer IKS from current centroids, using mu_0 from gae_state.get_mu_zero().
       Only returned when score > 50.0 -- below that, centroids have not diverged enough
       from mu_0 for drift to be informative. Threshold at 50 (half of 0-100 range) means
       centroids must have moved significantly across all categories before drift-IKS
       is trusted. Small post-decision shifts (~5-10) correctly fall back to v2.
    2. Graph-composite IKS v2 as fallback when drift <= 50.0 or scorer unavailable.
    """
    if scorer is None:
        try:
            from app.services.gae_state import get_profile_scorer

            scorer = get_profile_scorer()
        except Exception:
            scorer = None

    if scorer is not None:
        try:
            from app.services.gae_state import get_mu_zero
            mu_zero = get_mu_zero()
            result = compute_iks(scorer.centroids, mu_zero=mu_zero)
            score = float(result.get("current", 0.0))
            if score > 50.0:
                return score
        except Exception:
            pass

    if neo4j_service is not None:
        try:
            iks_data = await compute_iks_v2(neo4j_service)
            return float(iks_data.get("iks_v2", 0.0))
        except Exception:
            pass

    return 0.0


async def get_iks_trend() -> list[dict]:
    """
    Return IKS values at each ProfileSnapshot node (ordered by decision_count).

    Each entry: {"decision_count": int, "iks": float, "timestamp": str}

    Returns [] if no snapshots exist or Neo4j is unavailable.
    """
    try:
        from app.db.graph_client import graph_client

        rows = await graph_client.run_query(
            """
            MATCH (ps:ProfileSnapshot)
            RETURN ps.decision_count AS decision_count,
                   ps.mu             AS mu,
                   ps.timestamp      AS timestamp
            ORDER BY ps.decision_count ASC
            """,
            {},
        )
    except Exception as exc:
        log.warning("[IKS] get_iks_trend query failed: %s", exc)
        return []

    if not rows:
        return []

    mu_zero = _load_mu_zero()
    trend = []
    for row in rows:
        try:
            mu_str = row.get("mu", "[]")
            mu_t = np.array(json.loads(mu_str), dtype=np.float64)
            result = compute_iks(mu_t, mu_zero)
            trend.append({
                "decision_count": int(row["decision_count"]),
                "iks": result["current"],
                "timestamp": row.get("timestamp", ""),
            })
        except Exception as exc:
            log.debug("[IKS] Skipping malformed snapshot row: %s", exc)

    return trend


# ---------------------------------------------------------------------------
# IKS v2 — composite metric (replaces centroid-drift IKS for Chart A)
# ---------------------------------------------------------------------------

async def compute_iks_v2(neo4j_service) -> dict:
    """
    Compute IKS v2 from Neo4j graph state.

    IKS v2 = equal-weight composite of 4 components, each scaled 0-100:
      - Graph Richness:    min(total_decisions / 1000, 1.0) * 100
      - Decision Maturity: min(mean_category_count / 100, 1.0) * 100
      - Trust Coverage:    fraction of decisions with confidence >= 0.70 * 100
      - Factor Quality:    mean verified accuracy per category * 100
                           (defaults to 50 if no verified outcomes yet)

    Parameters
    ----------
    neo4j_service : object with async run_query(query, params=None) method
    """
    # ── Component 1: Graph Richness ─────────────────────────────────────────
    _neo4j_query_ok = True
    try:
        rows = await neo4j_service.run_query(
            f"MATCH (d:Decision) WHERE {soc_decision_where()} "
            "RETURN count(d) AS total", {}
        )
        total_decisions = int((rows[0].get("total") or 0) if rows else 0)
    except Exception as exc:
        log.warning("[IKS-v2] graph_richness query failed: %s", exc)
        raise RuntimeError("AGE query failed for IKS graph richness") from exc

    graph_richness = min(total_decisions / float(_p3min(200.0, 0.25)), 1.0) * 100.0

    # ── Component 2: Decision Maturity ──────────────────────────────────────
    _dm_query_ok = True
    try:
        rows = await neo4j_service.run_query(
            f"MATCH (d:Decision) WHERE {soc_decision_where()} "
            "RETURN d.category AS category, count(d) AS n", {}
        )
        cat_counts = {
            r["category"]: int(r.get("n") or 0)
            for r in rows
            if r.get("category") is not None
        }
    except Exception as exc:
        log.warning("[IKS-v2] decision_maturity query failed: %s", exc)
        raise RuntimeError("AGE query failed for IKS decision maturity") from exc

    mean_cat_count = (sum(cat_counts.values()) / len(cat_counts)) if cat_counts else 0.0
    # Threshold: reaches 1.0 at mean_cat_count = 1 (6 total for 6 cats);
    # reaches 100.0 at mean_cat_count >= 100 (~600 total for 6 categories).
    decision_maturity = min(mean_cat_count / 100.0, 1.0) * 100.0

    # ── Component 3: Trust Coverage ──────────────────────────────────────────
    try:
        rows = await neo4j_service.run_query(
            f"MATCH (d:Decision) WHERE {soc_decision_where()} "
            "AND d.confidence >= 0.70 RETURN count(d) AS high_conf", {}
        )
        high_conf = int((rows[0].get("high_conf") or 0) if rows else 0)
    except Exception as exc:
        log.warning("[IKS-v2] trust_coverage query failed: %s", exc)
        raise RuntimeError("AGE query failed for trust coverage") from exc

    trust_coverage = min((high_conf / max(total_decisions, 1)) * 100.0, 100.0)

    # ── Component 4: Factor Quality ──────────────────────────────────────────
    try:
        rows = await neo4j_service.run_query(
            """
            MATCH (d:Decision)
            WHERE """ + soc_decision_where() + """
              AND d.outcome IS NOT NULL
            RETURN d.category AS category,
                   avg(CASE WHEN d.outcome = 'correct' THEN 1.0 ELSE 0.0 END) AS accuracy
            """,
            {},
        )
        verified_accuracies = [
            float(r.get("accuracy") or 0.0)
            for r in rows
            if r.get("accuracy") is not None
        ]
    except Exception as exc:
        log.warning("[IKS-v2] factor_quality query failed: %s", exc)
        raise RuntimeError("AGE query failed for factor quality") from exc

    factor_quality = (
        (sum(verified_accuracies) / len(verified_accuracies)) * 100.0
        if verified_accuracies
        else (
            # Mature systems (≥phase3 minimum decisions) earn a 75% confidence prior:
            # calibration volume + GAE convergence justify a higher baseline
            # than the uninformative 50% used at early stage.
            75.0 if total_decisions >= _p3min(200.0, 0.25)
            else 50.0 if total_decisions > 0
            else 0.0   # true cold start -- no decisions at all
        )
    )

    iks_total = (graph_richness + decision_maturity + trust_coverage + factor_quality) / 4.0

    return {
        "iks_v2": round(iks_total, 1),
        "components": {
            "graph_richness":    round(graph_richness, 1),
            "decision_maturity": round(decision_maturity, 1),
            "trust_coverage":    round(trust_coverage, 1),
            "factor_quality":    round(factor_quality, 1),
        },
        "total_decisions":    total_decisions,
        "categories_active":  len(cat_counts),
        "interpretation":     interpret_iks_v2(iks_total),
    }


async def _compute_delta_7d(current_iks: float) -> float:
    """
    Compute IKS change over the last 7 days using ProfileSnapshot nodes.

    Returns current_iks - oldest_iks_within_7d_window, or 0.0 if insufficient data.
    """
    try:
        from app.db.graph_client import graph_client

        rows = await graph_client.run_query(
            """
            MATCH (ps:ProfileSnapshot)
            WHERE ps.timestamp_epoch >= $cutoff_epoch
            RETURN ps.mu AS mu
            ORDER BY ps.decision_count ASC
            LIMIT 1
            """,
            {"cutoff_epoch": int((datetime.utcnow().timestamp() - 7 * 86400) * 1000)},
        )
    except Exception as exc:
        log.debug("[IKS] delta_7d query failed: %s", exc)
        raise RuntimeError("AGE query failed for IKS delta") from exc

    if not rows:
        return 0.0

    try:
        mu_zero = _load_mu_zero()
        mu_str = rows[0].get("mu", "[]")
        mu_oldest = np.array(json.loads(mu_str), dtype=np.float64)
        oldest_result = compute_iks(mu_oldest, mu_zero)
        return cast(float, round(current_iks - cast(Any, oldest_result["current"]), 1))
    except Exception as exc:
        log.debug("[IKS] delta_7d computation failed: %s", exc)
        return 0.0
