"""
test_triage_routing_actions.py -- routing-action outcome handling tests.

Validates that report_decision_outcome() counts verified routing decisions,
does not mutate centroids for refer_to_analyst, and still counts outcomes
when the Decision.factor_vector is NULL.
"""
import asyncio
import contextlib
import json
import os
import sys
from typing import Any, cast
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from gae.calibration import CalibrationProfile
from app.framework.learning_state import make_state
from app.models.schemas import OutcomeRequest
from app.routers.triage import report_decision_outcome

_ROUTING_ACTION = "refer_to_analyst"
_DECISION_ID = "DEC-TRIAGE-ROUTING-001"
_ALERT_ID = "ALERT-TRIAGE-ROUTING-001"
_CATEGORY = "credential_access"
_FV_JSON = json.dumps([0.7, 0.8, 0.5, 0.4, 0.6, 0.9])


def _make_learning_state(decision_count: int = 100):
    return make_state(
        W=np.zeros((4, 6), dtype=np.float64),
        factor_names=[f"f{i}" for i in range(6)],
        profile=CalibrationProfile(
            learning_rate=0.02,
            penalty_ratio=20.0,
            temperature=0.1,
        ),
        decision_count=decision_count,
    )


def _make_outcome_result():
    result = MagicMock()
    result.model_dump.return_value = {
        "graph_updates": [],
        "consequence": "stable",
        "narrative": "ok",
    }
    return result


def _make_request(outcome: str = "correct") -> OutcomeRequest:
    return OutcomeRequest(
        alert_id=_ALERT_ID,
        decision_id=_DECISION_ID,
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


async def _call(harness, ls, outcome: str = "correct") -> dict[str, Any]:
    harness.add_decision(
        decision_id=_DECISION_ID,
        category=_CATEGORY,
        action=_ROUTING_ACTION,
        factors={f"f{i}": value for i, value in enumerate([0.7, 0.8, 0.5, 0.4, 0.6, 0.9])},
        factor_vector=None if outcome == "null-factor-vector" else _FV_JSON,
    )
    with contextlib.ExitStack() as stack:
        for p in _patches(ls):
            stack.enter_context(p)
        request_outcome = "correct" if outcome == "null-factor-vector" else outcome
        return cast(dict[str, Any], await report_decision_outcome(_make_request(request_outcome)))
    raise AssertionError("unreachable")


def _run(coro):
    return asyncio.run(coro)


def test_refer_to_analyst_increments_decision_count(soc_triage_harness):
    ls = _make_learning_state(decision_count=100)
    before = ls.decision_count

    _run(_call(soc_triage_harness, ls, outcome="correct"))

    after = ls.decision_count
    assert after == before + 1


def test_refer_to_analyst_does_not_update_centroids(soc_triage_harness):
    ls = _make_learning_state(decision_count=100)
    before = np.array(soc_triage_harness.scorer._scorer.mu, copy=True)

    _run(_call(soc_triage_harness, ls, outcome="correct"))

    after = np.array(soc_triage_harness.scorer._scorer.mu, copy=True)
    assert np.array_equal(after, before)


def test_fv_none_still_increments_decision_count(soc_triage_harness):
    ls = _make_learning_state(decision_count=100)
    before = ls.decision_count

    _run(_call(soc_triage_harness, ls, outcome="null-factor-vector"))

    after = ls.decision_count
    assert after == before + 1


def test_outcome_for_nonexistent_decision_returns_404(soc_triage_harness):
    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch("app.routers.triage.get_feedback_status", return_value={"has_feedback": False})
        )
        process_mock = stack.enter_context(
            patch("app.routers.triage.process_outcome", return_value=_make_outcome_result())
        )
        emit_mock = stack.enter_context(
            patch("app.routers.triage.event_bus.emit", new_callable=AsyncMock)
        )
        audit_mock = stack.enter_context(
            patch("app.framework.audit.record_outcome", new_callable=AsyncMock)
        )

        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/alert/outcome",
            json={
                "alert_id": _ALERT_ID,
                "decision_id": "DEC-DOES-NOT-EXIST",
                "outcome": "correct",
            },
        )

    assert response.status_code == 404
    assert "Decision DEC-DOES-NOT-EXIST not found" in response.json()["detail"]
    process_mock.assert_not_called()
    emit_mock.assert_not_called()
    audit_mock.assert_not_called()
