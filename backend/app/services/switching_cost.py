"""Switching cost trajectory helpers for Tab 4 Decision Economics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import logging
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_REBUILD_RATE = 10
DEFAULT_COST_PER_DAY = 800.0
DEFAULT_DECISIONS_PER_MONTH = 540.0
PROJECTED_MONTHS = (12, 18, 24)


@dataclass
class SwitchingCostPoint:
    month: int
    decisions: float
    iks: float
    analyst_days: float
    cost_usd: float
    label: str
    point_type: str


@dataclass
class SwitchingCostTrajectory:
    points: list[SwitchingCostPoint]
    current: SwitchingCostPoint | None
    projection_12m: float
    projection_24m: float
    rebuild_rate: int
    cost_per_day: float
    note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "points": [asdict(point) for point in self.points],
            "current": asdict(self.current) if self.current else None,
            "projection_12m": self.projection_12m,
            "projection_24m": self.projection_24m,
            "rebuild_rate": self.rebuild_rate,
            "cost_per_day": self.cost_per_day,
            "note": self.note,
        }


def default_iks_milestones() -> list[dict[str, Any]]:
    """Return the same display milestones used by Tab 2 IKS-over-time copy."""
    return [
        {"month": 1, "decisions": 540, "iks": 12, "label": "Calibrating"},
        {"month": 3, "decisions": 1620, "iks": 45, "label": "Learning"},
        {"month": 6, "decisions": 3240, "iks": 67, "label": "Switching cost plateau"},
        {"month": 9, "decisions": 4860, "iks": 89, "label": "Expert"},
    ]


def _safe_rebuild_rate(rebuild_rate: int) -> int:
    if rebuild_rate <= 0:
        log.warning(
            "Invalid rebuild_rate=%s for switching cost; falling back to %s",
            rebuild_rate,
            DEFAULT_REBUILD_RATE,
        )
        return DEFAULT_REBUILD_RATE
    return int(rebuild_rate)


def _point(
    month: int,
    decisions: float,
    iks: float,
    label: str,
    point_type: str,
    rebuild_rate: int,
    cost_per_day: float,
) -> SwitchingCostPoint:
    safe_decisions = max(float(decisions), 0.0)
    analyst_days = safe_decisions / rebuild_rate
    return SwitchingCostPoint(
        month=int(month),
        decisions=round(safe_decisions, 2),
        iks=round(max(float(iks), 0.0), 2),
        analyst_days=round(analyst_days, 2),
        cost_usd=round(analyst_days * float(cost_per_day), 2),
        label=label,
        point_type=point_type,
    )


def _normalise_milestones(milestones: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_month: dict[int, dict[str, Any]] = {}
    for raw in milestones:
        try:
            month = int(raw.get("month", 0))
        except Exception:
            continue
        if month <= 0:
            continue
        by_month[month] = raw
    return [by_month[month] for month in sorted(by_month)]


def compute_switching_cost_trajectory(
    iks_milestones: list[dict[str, Any]],
    decisions_per_month: float = DEFAULT_DECISIONS_PER_MONTH,
    rebuild_rate: int = DEFAULT_REBUILD_RATE,
    cost_per_day: float = DEFAULT_COST_PER_DAY,
) -> SwitchingCostTrajectory:
    """Compute switching cost as decisions / rebuild_rate * cost_per_day."""
    safe_rate = _safe_rebuild_rate(rebuild_rate)
    safe_cost = max(float(cost_per_day), 0.0)
    milestones = _normalise_milestones(iks_milestones)
    if not milestones:
        return SwitchingCostTrajectory(
            points=[],
            current=None,
            projection_12m=0.0,
            projection_24m=0.0,
            rebuild_rate=safe_rate,
            cost_per_day=safe_cost,
            note="No IKS milestones available; switching cost trajectory unavailable.",
        )

    points: list[SwitchingCostPoint] = []
    for milestone in milestones:
        points.append(
            _point(
                month=int(milestone.get("month", 0)),
                decisions=float(milestone.get("decisions", 0) or 0),
                iks=float(milestone.get("iks", 0) or 0),
                label=str(milestone.get("label", "Actual")),
                point_type="actual",
                rebuild_rate=safe_rate,
                cost_per_day=safe_cost,
            )
        )

    current = points[-1]
    safe_decisions_per_month = max(float(decisions_per_month), 0.0)
    for month in PROJECTED_MONTHS:
        if month <= current.month:
            continue
        projected_decisions = safe_decisions_per_month * month
        # Cost comes from decisions only; IKS is display metadata.
        projected_iks = min(100.0, current.iks + (100.0 - current.iks) * 0.35)
        points.append(
            _point(
                month=month,
                decisions=projected_decisions,
                iks=projected_iks,
                label=f"Projected month {month}",
                point_type="projected",
                rebuild_rate=safe_rate,
                cost_per_day=safe_cost,
            )
        )

    projection_by_month = {point.month: point.cost_usd for point in points}
    return SwitchingCostTrajectory(
        points=points,
        current=current,
        projection_12m=float(projection_by_month.get(12, 0.0)),
        projection_24m=float(projection_by_month.get(24, 0.0)),
        rebuild_rate=safe_rate,
        cost_per_day=safe_cost,
        note=(
            "Switching cost is computed as analyst-days to rebuild institutional "
            "judgment: decisions / rebuild_rate * cost_per_day. Projected points "
            "use deployment throughput; ROI savings are not included."
        ),
    )


def build_switching_cost_trajectory_payload(
    *,
    iks_milestones: list[dict[str, Any]] | None = None,
    decisions_per_day: float | None = None,
    decisions_per_month: float | None = None,
    rebuild_rate: int = DEFAULT_REBUILD_RATE,
    cost_per_day: float = DEFAULT_COST_PER_DAY,
) -> dict[str, Any]:
    """Return the JSON-safe trajectory payload shared by Tab 4 API paths."""
    if decisions_per_month is not None:
        effective_decisions_per_month = decisions_per_month
    elif decisions_per_day is not None:
        effective_decisions_per_month = decisions_per_day * 30.0
    else:
        effective_decisions_per_month = DEFAULT_DECISIONS_PER_MONTH

    return compute_switching_cost_trajectory(
        iks_milestones or default_iks_milestones(),
        decisions_per_month=effective_decisions_per_month,
        rebuild_rate=rebuild_rate,
        cost_per_day=cost_per_day,
    ).to_dict()
