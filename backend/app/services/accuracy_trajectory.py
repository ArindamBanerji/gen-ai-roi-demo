"""
app/services/accuracy_trajectory.py — Accuracy trajectory builder.

Produces the GET /api/soc/accuracy-trajectory response from:
  - app.domains.soc.constants  (published reference curves)
  - live decision counts per category from Neo4j (injected by endpoint)
  - sigma per category (injected by endpoint, defaults to 0.18)

No GAE math here — pure interpolation against reference constants.
"""
from __future__ import annotations

from app.domains.soc.constants import (
    ENRICHED_PLATEAU,
    COLD_START_REFERENCE_TRAJECTORY,
    get_sigma_band,
    get_permanent_gap_pp,
    COLD_START_PLATEAU_BY_SIGMA,
    n_half_applicable,
)

# Reference trajectory decision checkpoints (sorted)
_CHECKPOINTS = sorted(COLD_START_REFERENCE_TRAJECTORY.keys())


def _interpolate_accuracy(decision_count: int, sigma: float = 0.18) -> float:
    """
    Interpolate current accuracy from the cold-start reference trajectory.

    Uses linear interpolation between the two nearest checkpoints.
    At or beyond the last checkpoint, returns the cold-start plateau for sigma.
    """
    band = get_sigma_band(sigma)
    plateau = COLD_START_PLATEAU_BY_SIGMA[band]

    if decision_count <= 0:
        return 0.0

    # Below first checkpoint — linear from 0 to first value
    first_cp = _CHECKPOINTS[0]
    if decision_count <= first_cp:
        frac = decision_count / first_cp
        return round(frac * COLD_START_REFERENCE_TRAJECTORY[first_cp], 4)

    # Beyond last checkpoint — cap at cold-start plateau
    last_cp = _CHECKPOINTS[-1]
    if decision_count >= last_cp:
        return round(plateau, 4)

    # Linear interpolation between bracketing checkpoints
    for i in range(len(_CHECKPOINTS) - 1):
        lo, hi = _CHECKPOINTS[i], _CHECKPOINTS[i + 1]
        if lo <= decision_count <= hi:
            t = (decision_count - lo) / (hi - lo)
            acc_lo = COLD_START_REFERENCE_TRAJECTORY[lo]
            acc_hi = COLD_START_REFERENCE_TRAJECTORY[hi]
            return round(acc_lo + t * (acc_hi - acc_lo), 4)

    return round(plateau, 4)


def build_trajectory_for_category(
    category: str,
    decision_count: int,
    sigma: float = 0.18,
) -> dict:
    """
    Build the accuracy-trajectory dict for a single category.

    Returns:
        category           str   — category name
        decision_count     int   — verified analyst decisions
        sigma              float — volatility used
        sigma_band         str   — low / medium / high
        current_accuracy   float — interpolated cold-start accuracy (fraction)
        enriched_plateau   float — target accuracy with enrichment
        permanent_gap_pp   float — expected permanent gap in pp
        trajectory_points  list  — [{decisions, accuracy}] reference curve points
        pct_to_enriched    float — progress toward enriched plateau (0–100)
    """
    band = get_sigma_band(sigma)
    current_acc = _interpolate_accuracy(decision_count, sigma)
    cold_plateau = COLD_START_PLATEAU_BY_SIGMA[band]

    # Progress toward the cold-start plateau (0–100%)
    if cold_plateau > 0:
        pct = round(min(current_acc / cold_plateau, 1.0) * 100, 1)
    else:
        pct = 0.0

    trajectory_points = [
        {"decisions": k, "accuracy": v}
        for k, v in COLD_START_REFERENCE_TRAJECTORY.items()
    ]

    gap_pp = get_permanent_gap_pp(sigma)
    return {
        "category":           category,
        "decision_count":     decision_count,
        "sigma":              sigma,
        "sigma_band":         band,
        "current_accuracy":   current_acc,
        "enriched_plateau":   ENRICHED_PLATEAU,
        "cold_start_plateau": cold_plateau,
        "permanent_gap_pp":   gap_pp,
        "n_half_applicable":  n_half_applicable(sigma),
        "trajectory_points":  trajectory_points,
        "pct_to_enriched":    pct,
    }


def build_accuracy_trajectory(
    live_data: dict[str, int],
    decisions_per_day: float = 50.0,
    sigma_per_category: dict[str, float] | None = None,
) -> dict:
    """
    Build the full accuracy-trajectory response.

    Args:
        live_data:             {category: decision_count} from Neo4j
        decisions_per_day:     deployment rate (used for ETA)
        sigma_per_category:    {category: sigma} overrides; defaults to 0.18

    Returns:
        {
          "categories":        [build_trajectory_for_category(...)],
          "enriched_plateau":  float,
          "decisions_per_day": float,
          "days_to_plateau":   float | None,
          "source":            "live" | "cold_start",
        }
    """
    sigma_map = sigma_per_category or {}

    categories_out = []
    total_decisions = 0
    for cat, count in live_data.items():
        sigma = sigma_map.get(cat, 0.18)
        categories_out.append(build_trajectory_for_category(cat, count, sigma))
        total_decisions += count

    # If no live data, emit a single "overall" cold-start entry
    if not categories_out:
        categories_out.append(build_trajectory_for_category("overall", 0))

    # Days to cold-start plateau: remaining decisions / rate
    # Use the aggregate cold-start plateau for σ=0.18 (medium band default)
    cold_plateau = COLD_START_PLATEAU_BY_SIGMA[get_sigma_band(0.18)]
    remaining = max(0, _CHECKPOINTS[-1] - total_decisions)
    if decisions_per_day > 0 and remaining > 0:
        days_to_plateau: float | None = round(remaining / decisions_per_day, 1)
    elif remaining == 0:
        days_to_plateau = 0.0
    else:
        days_to_plateau = None

    return {
        "categories":        categories_out,
        "enriched_plateau":  ENRICHED_PLATEAU,
        "decisions_per_day": decisions_per_day,
        "days_to_plateau":   days_to_plateau,
        "source":            "live" if live_data else "cold_start",
    }
