"""Contract tests for the SOC Learning Control Room aggregation surface."""

from __future__ import annotations

import numpy as np

from app.models.responses import LearningControlRoomResponse
from app.services.soc_learning_control import _DayZeroScorerView, _finite_float


class _Scorer:
    actions = ["allow"]
    categories = ["identity"]
    kernel = "l2"
    decision_count = 8

    def get_checkpoint_state(self):
        return {"centroids": np.ones((1, 1, 2)), "decision_counts": [8]}


def test_control_room_response_contract_has_all_required_sections() -> None:
    response = LearningControlRoomResponse()
    assert {
        "centroid_history", "centroid_state", "dk_weights", "conservation",
        "iks", "verified_count", "evolution_summary", "convergence", "evidence",
    } <= set(LearningControlRoomResponse.model_fields)


def test_day_zero_view_is_read_only_and_zeroes_decision_counts() -> None:
    view = _DayZeroScorerView(_Scorer(), np.zeros((1, 1, 2)))
    checkpoint = view.get_checkpoint_state()
    assert checkpoint["decision_counts"] == [0]
    assert np.array_equal(view.centroids, np.zeros((1, 1, 2)))
    assert _Scorer().decision_count == 8


def test_finite_float_rejects_non_finite_values() -> None:
    assert _finite_float(float("nan"), 7.0) == 7.0
    assert _finite_float(float("inf"), 7.0) == 7.0
    assert _finite_float("0.25") == 0.25


def test_control_room_response_accepts_frozen_comparison_labels() -> None:
    response = LearningControlRoomResponse(
        frozen_comparison={"evidence_tier": "T_O", "measured": True, "iks_delta": 0.1}
    )
    assert response.frozen_comparison["evidence_tier"] == "T_O"
