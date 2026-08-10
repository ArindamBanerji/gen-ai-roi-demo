"""
ServiceNow mock integration tests for the triage outcome path.

These tests call report_decision_outcome() directly using the existing
patched-graph pattern from the triage outcome tests. The goal is to prove the
ServiceNow auto-create hook is wired to confirmed escalation outcomes.
"""
import asyncio
import contextlib
import json
import os
import sys
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models.schemas import OutcomeRequest
from app.routers.triage import report_decision_outcome
from app.services.servicenow_mock import get_servicenow_mock


_DECISION_ID = "DEC-SN-TRIAGE-001"
_ALERT_ID = "ALERT-SN-TRIAGE-001"
_CATEGORY = "credential_access"
_FV_JSON = json.dumps([0.7, 0.8, 0.5, 0.4, 0.6, 0.9])


@pytest.fixture(autouse=True)
def reset_servicenow_mock():
    get_servicenow_mock().reset()
    yield
    get_servicenow_mock().reset()


def _make_learning_state():
    ls = MagicMock()
    ls.decision_count = 100
    ls.W = np.ones((4, 6))
    ls.update.return_value = None
    return ls


def _make_outcome_result():
    result = MagicMock()
    result.graph_updates = []
    result.consequence = "stable"
    result.model_dump.return_value = {
        "graph_updates": [],
        "consequence": "stable",
        "narrative": "Escalation confirmed by analyst.",
    }
    return result


def _make_request(
    decision_id: str = _DECISION_ID,
    alert_id: str = _ALERT_ID,
    outcome: str = "correct",
) -> OutcomeRequest:
    return OutcomeRequest(
        alert_id=alert_id,
        decision_id=decision_id,
        outcome=cast(Any, outcome),
    )


def _patches(ls):
    return [
        patch("app.routers.triage.get_feedback_status", return_value={"has_feedback": False}),
        patch("app.routers.triage.process_outcome", return_value=_make_outcome_result()),
        patch("app.routers.triage.event_bus.emit", new_callable=AsyncMock),
        patch("app.routers.triage.get_learning_state", return_value=ls),
        patch("app.routers.triage.save_learning_state"),
        patch("app.framework.audit.record_outcome", new_callable=AsyncMock,
              return_value={"hash": "fakehash", "chain_index": 0}),
        patch("app.state.graph_snapshot.get_snapshot", return_value=MagicMock()),
        patch("app.services.gae_state.get_mu_zero", return_value=None),
        patch("app.services.gae_state.maybe_write_centroid_snapshot", return_value=False),
    ]


async def _call(harness, action: str = "escalate", outcome: str = "correct", decision_id: str = _DECISION_ID):
    harness.add_decision(
        decision_id=decision_id,
        category=_CATEGORY,
        action=action,
        confidence=0.91,
        factors={f"f{i}": value for i, value in enumerate([0.7, 0.8, 0.5, 0.4, 0.6, 0.9])},
        factor_vector=_FV_JSON,
        alert_type="impossible_travel",
    )
    ls = _make_learning_state()
    with contextlib.ExitStack() as stack:
        for patcher in _patches(ls):
            stack.enter_context(patcher)
        return await report_decision_outcome(
            _make_request(decision_id=decision_id, outcome=outcome)
        )


def _run(coro):
    return asyncio.run(coro)


def test_confirmed_escalation_creates_servicenow_incident(soc_triage_harness):
    _run(_call(soc_triage_harness, action="escalate", outcome="correct"))

    incident = get_servicenow_mock().get_incident(_DECISION_ID)

    assert incident is not None
    assert incident.decision_id == _DECISION_ID
    assert incident.alert_id == _ALERT_ID
    assert incident.incident_number.startswith("INC")
    assert len(get_servicenow_mock().get_all_incidents()) == 1


def test_confirmed_escalation_is_idempotent(soc_triage_harness):
    _run(_call(soc_triage_harness, action="escalate", outcome="correct"))
    first = get_servicenow_mock().get_incident(_DECISION_ID)

    second = get_servicenow_mock().create_incident(
        decision_id=_DECISION_ID,
        alert_id=_ALERT_ID,
        alert_type="impossible_travel",
        category=_CATEGORY,
        confidence=0.91,
    )

    assert first is not None
    assert second is not None
    assert second.incident_number == first.incident_number
    assert len(get_servicenow_mock().get_all_incidents()) == 1


def test_non_escalate_does_not_create_servicenow_incident(soc_triage_harness):
    _run(_call(soc_triage_harness, action="investigate", outcome="correct"))

    assert get_servicenow_mock().get_incident(_DECISION_ID) is None
    assert get_servicenow_mock().get_all_incidents() == []


def test_incorrect_escalation_does_not_create_incident(soc_triage_harness):
    _run(_call(soc_triage_harness, action="escalate", outcome="incorrect"))

    assert get_servicenow_mock().get_incident(_DECISION_ID) is None
    assert get_servicenow_mock().get_all_incidents() == []
