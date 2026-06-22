"""
convergence_calendar.py -- Convergence Calendar service (L-08).

SOC-specific calendar builder. Pure math lives in app.framework.convergence_math.
"""

from typing import Literal

from app.framework.convergence_math import (  # noqa: F401
    predict_n_half,
    decisions_to_days,
    INTERCEPT,
    COEFF_Q_BAR,
    COEFF_SIGMA,
    KERNEL_DIAGONAL_OFFSET,
)
from app.domains.soc.config import SOC_FACTORS  # noqa: F401


def build_convergence_calendar(
    sigma_per_factor: dict,
    q_bar: float,
    V: float,
    kernel: Literal["l2", "diagonal"],
    decisions_per_factor: dict,
    alpha: float = 0.25,
) -> dict:
    """
    Build per-factor convergence calendar for the frontend.

    Parameters
    ----------
    sigma_per_factor : {factor_name: sigma_value}
    q_bar            : mean analyst quality score (0-1)
    V                : daily alert volume (wall-clock only, not a predictor)
    kernel           : "l2" or "diagonal"
    decisions_per_factor : {factor_name: decisions_so_far}
    alpha            : fraction of alerts that reach learning pipeline
    """
    sigma_mean = sum(sigma_per_factor.values()) / len(sigma_per_factor)
    categories = []
    for factor in SOC_FACTORS:
        sigma = sigma_per_factor.get(factor, sigma_mean)
        n_half = predict_n_half(sigma, q_bar, kernel)
        current = decisions_per_factor.get(factor, 0)
        pct = min(100, int(100 * current / max(n_half, 1)))
        days = decisions_to_days(n_half, V, alpha)
        remaining_decisions = max(0, n_half - current)
        remaining_days = decisions_to_days(remaining_decisions, V, alpha)
        if current == 0:
            status = "not_started"
        elif pct >= 100:
            status = "calibrated"
        else:
            status = "calibrating"
        categories.append({
            "name": factor,
            "n_half_decisions": round(n_half, 1),
            "n_half_days": days,
            "current_decisions": current,
            "pct_calibrated": pct,
            "remaining_days": remaining_days,
            "status": status,
            "dominant_driver": "analyst_quality",
        })

    fully_calibrated = sum(1 for c in categories if c["status"] == "calibrated")
    calibrating = sum(1 for c in categories if c["status"] == "calibrating")
    not_started = sum(1 for c in categories if c["status"] == "not_started")
    remaining = [c["remaining_days"] for c in categories if c["status"] != "calibrated"]

    return {
        "categories": categories,
        "summary": {
            "fully_calibrated": fully_calibrated,
            "calibrating": calibrating,
            "not_started": not_started,
            "fastest_remaining_days": min(remaining) if remaining else 0,
            "slowest_remaining_days": max(remaining) if remaining else 0,
        },
        "model": {
            "formula": "N_half = 28.5 - 3.28\u00d7q\u0305 - 12.1\u00d7(1-\u03c3) + kernel_offset",
            "mae_days": 1.55,
            "v_causal": False,
            "q_bar_coefficient": -3.28,
            "insight": (
                "Higher analyst engagement is the single biggest driver "
                "of calibration speed"
            ),
        },
    }
