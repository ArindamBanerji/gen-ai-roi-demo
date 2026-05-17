import asyncio
import contextlib
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.models.schemas import OutcomeRequest
from app.routers.triage import report_decision_outcome


_ALERT_ID = "ALERT-FACTOR-VALIDATION-001"
_DECISION_ID = "DEC-FACTOR-VALIDATION-001"
_CATEGORY = "credential_access"
_VALID_VECTOR = [0.7, 0.8, 0.5, 0.4, 0.6, 0.9]


class _OutcomeResult:
    graph_updates = []
    consequence = "stable"

    def model_dump(self):
        return {
            "graph_updates": [],
            "consequence": "stable",
            "narrative": "ok",
        }


def _make_request() -> OutcomeRequest:
    return OutcomeRequest(
        alert_id=_ALERT_ID,
        decision_id=_DECISION_ID,
        outcome="correct",
    )


def _make_neo4j(factor_vector, action: str = "investigate"):
    async def _run(query, params=None):
        if "RETURN d.factor_vector AS factor_vector" in query:
            return [{
                "factor_vector": factor_vector,
                "action": action,
                "confidence": 0.85,
                "category": _CATEGORY,
                "alert_type": _CATEGORY,
            }]
        return []

    client = AsyncMock()
    client.run_query.side_effect = _run
    return client


def _make_learning_state():
    state = SimpleNamespace(decision_count=100)
    state.update = MagicMock(return_value=SimpleNamespace(centroid_update=None))
    return state


async def _call_with_factor_vector(factor_vector, action: str = "investigate"):
    neo4j = _make_neo4j(factor_vector=factor_vector, action=action)
    learning_state = _make_learning_state()

    with contextlib.ExitStack() as stack:
        stack.enter_context(patch("app.routers.triage.neo4j_client", neo4j))
        stack.enter_context(patch("app.routers.triage.get_feedback_status", return_value={"has_feedback": False}))
        stack.enter_context(patch("app.routers.triage.process_outcome", return_value=_OutcomeResult()))
        stack.enter_context(patch("app.routers.triage.event_bus.emit", new_callable=AsyncMock))
        stack.enter_context(patch("app.routers.triage.get_learning_state", return_value=learning_state))
        stack.enter_context(patch("app.routers.triage.save_learning_state"))
        stack.enter_context(patch("app.framework.audit.record_outcome", new_callable=AsyncMock, return_value={"hash": "hash", "chain_index": 1}))
        stack.enter_context(patch("app.state.graph_snapshot.get_snapshot", return_value=MagicMock()))
        stack.enter_context(patch("app.services.gae_state.get_mu_zero", return_value=None))
        stack.enter_context(patch("app.services.gae_state.get_profile_scorer", return_value=None))
        stack.enter_context(patch("app.services.gae_state.maybe_write_centroid_snapshot", return_value=False))
        stack.enter_context(patch("app.services.snapshots.maybe_write_profile_snapshot", new_callable=AsyncMock))
        stack.enter_context(patch("app.services.learning_health.LearningHealthMonitor.evaluate", new_callable=AsyncMock, return_value={"status": "GREEN"}))

        result = await report_decision_outcome(_make_request())

    return result, learning_state


def _run(coro):
    return asyncio.run(coro)


def test_empty_factor_vector_raises():
    with pytest.raises(ValueError, match="factor_vector must have 6 elements, got 0"):
        _run(_call_with_factor_vector([]))


def test_none_factor_vector_raises():
    with pytest.raises(ValueError, match="factor_vector must have 6 elements, got None"):
        _run(_call_with_factor_vector(None))


def test_wrong_length_factor_vector_raises():
    with pytest.raises(ValueError, match="factor_vector must have 6 elements, got 3"):
        _run(_call_with_factor_vector([0.1, 0.2, 0.3]))


def test_valid_factor_vector_scores_correctly():
    result, learning_state = _run(_call_with_factor_vector(json.dumps(_VALID_VECTOR)))

    learning_state.update.assert_called_once()
    update_call = learning_state.update.call_args.kwargs
    assert update_call["action_name"] == "investigate"
    assert update_call["f"].shape == (1, 6)
    assert np.allclose(update_call["f"].flatten(), np.asarray(_VALID_VECTOR))
    assert result["consequence"] == "stable"


def test_factor_validation_message_includes_expected_length():
    with pytest.raises(ValueError) as exc:
        _run(_call_with_factor_vector([0.1, 0.2, 0.3]))

    message = str(exc.value)
    assert "factor_vector must have 6 elements" in message
    assert "got 3" in message
