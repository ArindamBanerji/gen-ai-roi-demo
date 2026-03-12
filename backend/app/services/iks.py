"""
Institutional Knowledge Score (IKS) service.

IKS measures how far the system's learned centroids have drifted from the
bootstrap prior μ₀.  A higher score means more real-world experience has been
integrated.

Formula (docs/soc_copilot_design_v1.md §14):

    IKS(t) = 100 × min(
        mean( ‖μ(t)[c, a, :] − μ₀[c, a, :]‖₂  for all (c, a) )
        / D_MAX,
        1.0
    )

where D_MAX = 0.30 is the normalization constant (empirically calibrated to
yield IKS ≈ 100 after ~500 real decisions).

μ₀ is loaded from backend/app/data/iks_bootstrap_soc.json, written by
gae_state.init_learning_state() before bootstrap_calibration() mutates μ.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)

D_MAX: float = 0.30  # normalization constant — empirically calibrated

_MU_ZERO_PATH = Path(__file__).parent.parent / "data" / "iks_bootstrap_soc.json"

_mu_zero_cache: Optional[np.ndarray] = None   # lazily loaded, module-level cache


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_mu_zero() -> Optional[np.ndarray]:
    """Load μ₀ from the sidecar JSON, with module-level caching."""
    global _mu_zero_cache
    if _mu_zero_cache is not None:
        return _mu_zero_cache
    if not _MU_ZERO_PATH.exists():
        log.warning("[IKS] μ₀ file not found at %s — IKS will be estimated", _MU_ZERO_PATH)
        return None
    try:
        with open(_MU_ZERO_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        _mu_zero_cache = np.array(data["mu_zero"], dtype=np.float64)
        log.info("[IKS] μ₀ loaded from %s (shape=%s)", _MU_ZERO_PATH, list(_mu_zero_cache.shape))
        return _mu_zero_cache
    except Exception as exc:
        log.warning("[IKS] Failed to load μ₀: %s", exc)
        return None


def _mean_centroid_drift(mu_t: np.ndarray, mu_zero: np.ndarray) -> float:
    """
    Compute mean ‖μ(t)[c,a,:] − μ₀[c,a,:]‖₂ over all (c, a) pairs.

    Parameters
    ----------
    mu_t : np.ndarray, shape (n_categories, n_actions, n_factors)
    mu_zero : np.ndarray, same shape

    Returns
    -------
    float
        Mean L2 drift across all centroid slots.
    """
    diff = mu_t - mu_zero                   # shape (C, A, F)
    per_slot = np.linalg.norm(diff, axis=2)  # shape (C, A)
    return float(np.mean(per_slot))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_iks(mu_t: np.ndarray, mu_zero: Optional[np.ndarray] = None) -> dict:
    """
    Compute the current IKS score.

    Parameters
    ----------
    mu_t : np.ndarray, shape (n_categories, n_actions, n_factors)
        Current centroid tensor from ProfileScorer.
    mu_zero : np.ndarray or None
        Bootstrap prior.  If None, loaded from the sidecar JSON.

    Returns
    -------
    dict with keys:
        current (float)      — IKS in [0, 100]
        mean_drift (float)   — raw mean L2 drift before normalization
        estimated (bool)     — True if μ₀ was unavailable (IKS is approximate)
    """
    if mu_zero is None:
        mu_zero = _load_mu_zero()

    if mu_zero is None:
        # μ₀ unavailable — approximate by treating current μ as fully learned
        # (returns a neutral 50 to avoid misleading zeros)
        log.debug("[IKS] μ₀ unavailable — returning estimated IKS=50")
        return {"current": 50.0, "mean_drift": 0.0, "estimated": True}

    mean_drift = _mean_centroid_drift(mu_t, mu_zero)
    iks = 100.0 * min(mean_drift / D_MAX, 1.0)
    return {"current": round(iks, 1), "mean_drift": round(mean_drift, 4), "estimated": False}


def interpret(iks_score: float) -> str:
    """Return a human-readable interpretation of the IKS score."""
    if iks_score < 20:
        return "Early learning \u2014 system is still close to priors"
    if iks_score < 50:
        return "Developing \u2014 meaningful drift from bootstrap detected"
    if iks_score < 80:
        return "Experienced \u2014 significant real-world adaptation"
    return "Mature \u2014 centroids substantially evolved from bootstrap"


async def get_iks_trend() -> list[dict]:
    """
    Return IKS values at each ProfileSnapshot node (ordered by decision_count).

    Each entry: {"decision_count": int, "iks": float, "timestamp": str}

    Returns [] if no snapshots exist or Neo4j is unavailable.
    """
    try:
        from app.db.neo4j import neo4j_client

        rows = await neo4j_client.run_query(
            """
            MATCH (ps:ProfileSnapshot)
            RETURN ps.decision_count AS decision_count,
                   ps.mu             AS mu,
                   toString(ps.timestamp) AS timestamp
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


async def _compute_delta_7d(current_iks: float) -> float:
    """
    Compute IKS change over the last 7 days using ProfileSnapshot nodes.

    Returns current_iks - oldest_iks_within_7d_window, or 0.0 if insufficient data.
    """
    try:
        from app.db.neo4j import neo4j_client

        rows = await neo4j_client.run_query(
            """
            MATCH (ps:ProfileSnapshot)
            WHERE ps.timestamp >= datetime() - duration({days: 7})
            RETURN ps.mu AS mu
            ORDER BY ps.decision_count ASC
            LIMIT 1
            """,
            {},
        )
    except Exception as exc:
        log.debug("[IKS] delta_7d query failed: %s", exc)
        return 0.0

    if not rows:
        return 0.0

    try:
        mu_zero = _load_mu_zero()
        mu_str = rows[0].get("mu", "[]")
        mu_oldest = np.array(json.loads(mu_str), dtype=np.float64)
        oldest_result = compute_iks(mu_oldest, mu_zero)
        return round(current_iks - oldest_result["current"], 1)
    except Exception as exc:
        log.debug("[IKS] delta_7d computation failed: %s", exc)
        return 0.0
