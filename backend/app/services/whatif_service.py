"""
FEATURE-03 What-If Simulator -- pure-math conservation projection.

v1 intentionally does not touch any live scorer or learning state. It projects
daily q(t), computes signal alpha*q*V, and evaluates status via the GAE
conservation-law primitives.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

import numpy as np

from gae.calibration import check_conservation
from gae.snr import compute_snr_report

from app.domains.soc.config import (
    SCORER_ACTIONS,
    SOC_CATEGORIES,
    SOC_FACTORS,
    SOC_FACTOR_SIGMA,
    compute_theta_min,
)
from app.services.gae_state import get_profile_scorer
from app.services.learning_health import AUTO_PAUSE_RED_DAYS

_CEILING_NOTE = (
    "Ceiling values are an approximate structural estimate for relative comparison only; "
    "they are not predicted accuracy."
)


@dataclass
class WhatIfScenario:
    name: str = "custom"
    description: str = ""
    alpha: float = 0.25
    V: float = 200.0
    q_initial: float = 0.80
    q_target: float = 0.80
    q_ramp_days: int = 0           # 0 = instant; >0 = linear ramp over N days
    horizon_days: int = 30
    disruption_day: Optional[int] = None
    disruption_delta: float = 0.0
    eta: float = 0.05
    n_half: float = 14.0
    t_max_days: float = 21.0
    iks_initial: float = 50.0
    iks_gain_green: float = 0.8
    iks_gain_amber: float = 0.3
    iks_gain_red: float = -0.2


@dataclass
class DailyProjection:
    day: int
    q: float
    signal: float
    status: str
    passed: bool
    headroom: float
    iks_estimate: float


@dataclass
class WhatIfResult:
    scenario: dict[str, Any]
    daily_trajectory: list[dict[str, Any]]
    summary: dict[str, Any]
    conservation_law: dict[str, Any]
    iks_estimate: float
    ceiling_estimate: float | None = None
    ceiling_note: str = _CEILING_NOTE
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _interpolate_q(day_index: int, scenario: WhatIfScenario) -> float:
    # FIX-13: ramp computed entirely in the backend using q_ramp_days.
    if scenario.q_ramp_days > 0 and scenario.q_initial != scenario.q_target:
        progress = min(day_index / scenario.q_ramp_days, 1.0)
        q_value = scenario.q_initial + (scenario.q_target - scenario.q_initial) * progress
    else:
        q_value = scenario.q_target  # instant transition (q_ramp_days=0)

    if scenario.disruption_day is not None and day_index >= scenario.disruption_day:
        q_value += scenario.disruption_delta

    return _clamp(q_value, 0.0, 1.0)


def _iks_delta(status: str, scenario: WhatIfScenario) -> float:
    if status == "GREEN":
        return scenario.iks_gain_green
    if status == "AMBER":
        return scenario.iks_gain_amber
    return scenario.iks_gain_red


def _build_warnings(scenario: WhatIfScenario, q_threshold: float) -> list[str]:
    warnings: list[str] = []
    if scenario.horizon_days <= 0:
        warnings.append("horizon_days <= 0: no trajectory will be produced")
    if scenario.alpha == 0:
        warnings.append("alpha == 0: signal is zero for every day")
    if scenario.V == 0:
        warnings.append("V == 0: signal is zero for every day")
    if scenario.q_initial == 0 and scenario.q_target == 0:
        warnings.append("q is pinned at zero: every projected day will breach conservation")
    if scenario.disruption_day is not None and scenario.disruption_day < 0:
        warnings.append("disruption_day < 0: disruption applies from day 0")
    if scenario.disruption_delta < 0:
        warnings.append("negative disruption_delta reduces q from disruption_day onward")
    if q_threshold == float("inf"):
        warnings.append("q threshold is infinite because alpha * V <= 0")
    elif q_threshold > 1.0:
        warnings.append("required q threshold exceeds 1.0: deployment is mathematically infeasible")
    return warnings


def _compute_current_ceiling_estimate() -> float | None:
    scorer = get_profile_scorer()
    if scorer is None:
        return None
    try:
        sigma = np.array([SOC_FACTOR_SIGMA[f] for f in SOC_FACTORS], dtype=np.float64)
        report = compute_snr_report(
            centroids=np.asarray(scorer.centroids, dtype=np.float64),
            sigma=sigma,
            categories=list(SOC_CATEGORIES),
            actions=list(SCORER_ACTIONS),
            factor_names=list(SOC_FACTORS),
        )
        return float(report.mean_ceiling_estimate * 100.0)
    except Exception:
        return None


def run_whatif(scenario: WhatIfScenario) -> WhatIfResult:
    override_rate = float(scenario.alpha)
    verified_volume = float(scenario.V)
    theta_min = float(compute_theta_min(override_rate, verified_volume))

    alpha_v = float(override_rate * verified_volume)
    q_threshold = float("inf") if alpha_v <= 0 else theta_min / alpha_v
    horizon_days = max(0, int(scenario.horizon_days))
    warnings = _build_warnings(scenario, q_threshold)
    ceiling_estimate = _compute_current_ceiling_estimate()

    daily_entries: list[DailyProjection] = []
    iks_current = _clamp(scenario.iks_initial, 0.0, 100.0)
    days_green = 0
    days_amber = 0
    days_red = 0
    first_amber_day: Optional[int] = None
    first_red_day: Optional[int] = None

    for day_index in range(horizon_days):
        q_value = _interpolate_q(day_index, scenario)
        cc = check_conservation(
            alpha=float(scenario.alpha),
            q=float(q_value),
            V=float(scenario.V),
            theta_min=float(theta_min),
        )

        if cc.status == "GREEN":
            days_green += 1
        elif cc.status == "AMBER":
            days_amber += 1
            if first_amber_day is None:
                first_amber_day = day_index
        else:
            days_red += 1
            if first_red_day is None:
                first_red_day = day_index

        iks_current = _clamp(iks_current + _iks_delta(cc.status, scenario), 0.0, 100.0)
        daily_entries.append(
            DailyProjection(
                day=day_index,
                q=round(q_value, 6),
                signal=float(round(cc.signal, 6)),
                status=cc.status,
                passed=bool(cc.passed),
                headroom=float(round(cc.headroom, 6)),
                iks_estimate=round(iks_current, 4),
            )
        )

    final_status = daily_entries[-1].status if daily_entries else "RED"
    auto_pause_triggered = days_red >= AUTO_PAUSE_RED_DAYS

    return WhatIfResult(
        scenario=asdict(scenario),
        daily_trajectory=[asdict(entry) for entry in daily_entries],
        summary={
            "days_green": days_green,
            "days_amber": days_amber,
            "days_red": days_red,
            "first_amber_day": first_amber_day,
            "first_red_day": first_red_day,
            "auto_pause_triggered": auto_pause_triggered,
            "final_status": final_status,
            "final_iks": round(iks_current, 4),
        },
        conservation_law={
            "theta_min": round(theta_min, 6),
            "formula": "signal = alpha * q * V; theta_min = 23.53 / (alpha * V)",
            "explanation": (
                "The minimum required override quality is q >= theta_min / (alpha * V). "
                "Statuses come directly from check_conservation(): GREEN >= 2*theta_min, "
                "AMBER >= theta_min, RED < theta_min."
            ),
            "q_threshold": None if q_threshold == float("inf") else round(q_threshold, 6),
        },
        iks_estimate=round(iks_current, 4),
        ceiling_estimate=ceiling_estimate,
        warnings=warnings,
    )


PRESETS: dict[str, WhatIfScenario] = {
    "healthy_deployment": WhatIfScenario(
        name="healthy_deployment",
        description="Stable high-quality verified feedback at standard SOC throughput.",
        alpha=0.25,
        V=200.0,
        q_initial=0.82,
        q_target=0.82,
        horizon_days=30,
    ),
    "gradual_degradation": WhatIfScenario(
        name="gradual_degradation",
        description="Quality slowly degrades toward the conservation floor over one month.",
        alpha=0.25,
        V=30.0,
        q_initial=0.90,
        q_target=0.10,
        q_ramp_days=30,
        horizon_days=30,
    ),
    "sudden_disruption": WhatIfScenario(
        name="sudden_disruption",
        description="Healthy system hit by a sudden process disruption mid-horizon.",
        alpha=0.25,
        V=30.0,
        q_initial=0.90,
        q_target=0.90,
        horizon_days=30,
        disruption_day=10,
        disruption_delta=-0.70,
    ),
    "low_volume_stress": WhatIfScenario(
        name="low_volume_stress",
        description="Low-volume deployment hovering just above the absolute floor (AMBER).",
        alpha=0.25,
        V=50.0,
        q_initial=0.19,
        q_target=0.19,
        horizon_days=21,
    ),
    "high_automation_good_quality": WhatIfScenario(
        name="high_automation_good_quality",
        description="Lower override rate but strong quality and sufficient volume remain healthy.",
        alpha=0.05,
        V=200.0,
        q_initial=0.50,
        q_target=0.50,
        horizon_days=21,
    ),
}


def get_presets() -> dict[str, dict[str, Any]]:
    return {name: asdict(scenario) for name, scenario in PRESETS.items()}


def run_preset(preset_name: str) -> WhatIfResult:
    scenario = PRESETS[preset_name]
    return run_whatif(scenario)
