"""Regression tests for the SOC outcome duplicate contract."""

import asyncio
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.models.schemas import OutcomeRequest
from app.routers import triage


def _invoke(request: OutcomeRequest):
    return asyncio.run(triage.report_decision_outcome(request))


def test_identical_outcome_is_idempotent_at_route_level() -> None:
    request = OutcomeRequest(
        alert_id="ALERT-IDEMPOTENT",
        decision_id="DEC-IDEMPOTENT",
        outcome="correct",
    )
    previous = {
        "decision_id": request.decision_id,
        "outcome": request.outcome,
        "graph_updates": [],
    }

    with patch.object(triage, "get_feedback_record", return_value=previous):
        response = _invoke(request)

    assert response["alert_id"] == request.alert_id
    assert response["outcome"] == "correct"
    assert response["consequence"].startswith("Outcome already recorded")
    assert response["graph_updates"] == []


def test_conflicting_outcome_returns_409_at_route_level() -> None:
    request = OutcomeRequest(
        alert_id="ALERT-CONFLICT",
        decision_id="DEC-CONFLICT",
        outcome="incorrect",
    )
    previous = {
        "decision_id": request.decision_id,
        "outcome": "correct",
        "graph_updates": [],
    }

    with patch.object(triage, "get_feedback_record", return_value=previous):
        with pytest.raises(HTTPException) as exc_info:
            _invoke(request)

    assert exc_info.value.status_code == 409
    assert "Conflicting feedback" in str(exc_info.value.detail)
