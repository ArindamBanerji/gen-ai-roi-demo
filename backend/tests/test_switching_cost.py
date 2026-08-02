from dataclasses import asdict
import asyncio
from unittest.mock import AsyncMock, patch

from app.services.switching_cost import (
    DEFAULT_COST_PER_DAY,
    DEFAULT_REBUILD_RATE,
    build_switching_cost_trajectory_payload,
    compute_switching_cost_trajectory,
)


MILESTONES = [
    {"month": 1, "decisions": 540, "iks": 12, "label": "Calibrating"},
    {"month": 3, "decisions": 1620, "iks": 45, "label": "Learning"},
    {"month": 6, "decisions": 3240, "iks": 67, "label": "Switching cost plateau"},
    {"month": 9, "decisions": 4860, "iks": 89, "label": "Expert"},
]


def test_trajectory_has_actual_and_projected_points():
    trajectory = compute_switching_cost_trajectory(MILESTONES)

    assert len(trajectory.points) == 7
    assert [point.month for point in trajectory.points] == [1, 3, 6, 9, 12, 18, 24]
    assert [point.point_type for point in trajectory.points[:4]] == ["actual"] * 4
    assert [point.point_type for point in trajectory.points[4:]] == ["projected"] * 3


def test_cost_formula_is_decisions_over_rebuild_rate_times_cost_per_day():
    trajectory = compute_switching_cost_trajectory(
        [{"month": 3, "decisions": 1620, "iks": 45, "label": "Learning"}],
        cost_per_day=800,
        rebuild_rate=10,
    )

    point = trajectory.current
    assert point is not None
    assert point.analyst_days == 162
    assert point.cost_usd == 129600


def test_projection_extrapolates_beyond_current_month():
    trajectory = compute_switching_cost_trajectory(MILESTONES, decisions_per_month=540)
    projected = [point for point in trajectory.points if point.point_type == "projected"]

    assert [point.month for point in projected] == [12, 18, 24]
    assert all(point.cost_usd > trajectory.current.cost_usd for point in projected)
    assert projected[0].cost_usd < projected[1].cost_usd < projected[2].cost_usd


def test_custom_cost_per_day_scales_exactly():
    base = compute_switching_cost_trajectory(MILESTONES, cost_per_day=800)
    higher = compute_switching_cost_trajectory(MILESTONES, cost_per_day=1200)

    assert higher.current.cost_usd / base.current.cost_usd == 1.5


def test_current_point_is_latest_actual_milestone():
    trajectory = compute_switching_cost_trajectory(MILESTONES)

    assert trajectory.current is not None
    assert trajectory.current.month == 9
    assert trajectory.current.point_type == "actual"
    assert trajectory.current.label == "Expert"


def test_empty_milestones_return_empty_trajectory():
    trajectory = compute_switching_cost_trajectory([])

    assert trajectory.points == []
    assert trajectory.current is None
    assert trajectory.projection_12m == 0.0
    assert trajectory.projection_24m == 0.0
    assert trajectory.rebuild_rate == DEFAULT_REBUILD_RATE
    assert trajectory.cost_per_day == DEFAULT_COST_PER_DAY


def test_unsorted_milestones_use_latest_month_as_current():
    trajectory = compute_switching_cost_trajectory([MILESTONES[2], MILESTONES[0], MILESTONES[3], MILESTONES[1]])

    assert [point.month for point in trajectory.points[:4]] == [1, 3, 6, 9]
    assert trajectory.current is not None
    assert trajectory.current.month == 9


def test_duplicate_month_prefers_last_milestone():
    trajectory = compute_switching_cost_trajectory([
        {"month": 3, "decisions": 100, "iks": 10, "label": "Old"},
        {"month": 3, "decisions": 200, "iks": 20, "label": "New"},
    ])

    assert trajectory.current is not None
    assert trajectory.current.decisions == 200
    assert trajectory.current.label == "New"


def test_rebuild_rate_zero_or_negative_falls_back():
    zero = compute_switching_cost_trajectory(MILESTONES, rebuild_rate=0)
    negative = compute_switching_cost_trajectory(MILESTONES, rebuild_rate=-5)

    assert zero.rebuild_rate == DEFAULT_REBUILD_RATE
    assert negative.rebuild_rate == DEFAULT_REBUILD_RATE


def test_negative_decisions_are_clamped_to_zero():
    trajectory = compute_switching_cost_trajectory([
        {"month": 1, "decisions": -100, "iks": 10, "label": "Bad input"}
    ])

    assert trajectory.current is not None
    assert trajectory.current.decisions == 0
    assert trajectory.current.analyst_days == 0
    assert trajectory.current.cost_usd == 0


def test_to_dict_uses_dict_and_list_primitives():
    payload = compute_switching_cost_trajectory(MILESTONES).to_dict()

    assert isinstance(payload, dict)
    assert isinstance(payload["points"], list)
    assert isinstance(payload["points"][0], dict)
    assert payload["current"] == asdict(compute_switching_cost_trajectory(MILESTONES).current)


def test_payload_helper_aligns_per_day_and_per_month_inputs():
    payload_from_day = build_switching_cost_trajectory_payload(
        iks_milestones=MILESTONES,
        decisions_per_day=18,
    )
    direct = compute_switching_cost_trajectory(
        MILESTONES,
        decisions_per_month=540,
    ).to_dict()

    assert payload_from_day["projection_12m"] == direct["projection_12m"]
    assert payload_from_day["projection_24m"] == direct["projection_24m"]
    assert payload_from_day["points"] == direct["points"]


def test_payload_helper_prefers_explicit_decisions_per_month():
    payload = build_switching_cost_trajectory_payload(
        iks_milestones=MILESTONES,
        decisions_per_day=999,
        decisions_per_month=540,
    )
    direct = compute_switching_cost_trajectory(MILESTONES, decisions_per_month=540).to_dict()

    assert payload["projection_12m"] == direct["projection_12m"]
    assert payload["projection_24m"] == direct["projection_24m"]


def test_soc_and_metrics_paths_use_same_trajectory_assumptions():
    timestamp_rows = [{"t_min": 1_700_000_000_000, "t_max": 1_700_086_400_000, "n": 18}]

    async def _run():
        from app.routers.metrics import get_decision_economics
        from app.routers.soc import _tab4_content

        with patch("app.routers.soc.graph_client") as soc_client:
            soc_client.run_query = AsyncMock(side_effect=[
                [{"cnt": 18}],
                timestamp_rows,
                [{"cnt": 14}],
            ])
            soc_payload = await _tab4_content()

        with patch("app.routers.metrics.graph_client") as metrics_client:
            metrics_client.run_query = AsyncMock(side_effect=[
                [{"total_decisions": 18}],
                [{"correct_decisions": 14}],
                timestamp_rows,
            ])
            metrics_payload = await get_decision_economics()

        return soc_payload["switching_cost_trajectory"], metrics_payload["switching_cost_trajectory"]

    soc_trajectory, metrics_trajectory = asyncio.run(_run())

    assert soc_trajectory["projection_12m"] == metrics_trajectory["projection_12m"]
    assert soc_trajectory["projection_24m"] == metrics_trajectory["projection_24m"]
    assert soc_trajectory["points"] == metrics_trajectory["points"]
