import asyncio
import contextlib
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.schemas import OutcomeRequest
from app.routers.triage import report_decision_outcome
from app.main import app
from app.domains.soc.config import SOCDomainConfig
from app.services.triage_providers import get_learning_policy


_ALERT_ID = "ALERT-FACTOR-VALIDATION-001"
_DECISION_ID = "DEC-FACTOR-VALIDATION-001"
_CATEGORY = "credential_access"
_VALID_VECTOR = [0.7, 0.8, 0.5, 0.4, 0.6, 0.9]


class _OutcomeResult:
    graph_updates: list[object] = []
    consequence = "stable"

    def model_dump(self):
        return {
            "graph_updates": [],
            "consequence": "stable",
            "narrative": "ok",
        }


class _LearningPolicy:
    def __init__(self, enabled: bool):
        self._enabled = enabled

    def enabled(self) -> bool:
        return self._enabled


def _make_request() -> OutcomeRequest:
    return OutcomeRequest(
        alert_id=_ALERT_ID,
        decision_id=_DECISION_ID,
        outcome="correct",
    )


def _make_learning_state():
    state = SimpleNamespace(decision_count=100)
    state.update = MagicMock(return_value=SimpleNamespace(centroid_update=None))
    return state


async def _call_with_factor_vector(
    factor_vector,
    harness,
    action: str = "investigate",
    learning_enabled: bool = False,
):
    harness.add_decision(
        decision_id=_DECISION_ID,
        category=_CATEGORY,
        action=action,
        factors={f"f{i}": value for i, value in enumerate(_VALID_VECTOR)},
        factor_vector=factor_vector,
    )
    learning_state = _make_learning_state()

    @contextlib.asynccontextmanager
    async def acquire_harness_scorer():
        yield harness.get_scorer()

    with contextlib.ExitStack() as stack:
        stack.enter_context(patch("app.routers.triage.get_feedback_status", return_value={"has_feedback": False}))
        stack.enter_context(patch("app.routers.triage.process_outcome", return_value=_OutcomeResult()))
        stack.enter_context(patch("app.routers.triage.event_bus.emit", new_callable=AsyncMock))
        stack.enter_context(patch("app.routers.triage.get_learning_state", return_value=learning_state))
        stack.enter_context(patch("app.routers.triage.save_learning_state"))
        stack.enter_context(patch("app.framework.audit.record_outcome", new_callable=AsyncMock, return_value={"hash": "hash", "chain_index": 1}))
        stack.enter_context(patch("app.state.graph_snapshot.get_snapshot", return_value=MagicMock()))
        stack.enter_context(patch("app.services.gae_state.get_mu_zero", return_value=None))
        stack.enter_context(patch("app.services.gae_state.get_profile_scorer", harness.get_scorer))
        stack.enter_context(patch("app.services.gae_state.acquire_scorer", acquire_harness_scorer))
        stack.enter_context(patch("app.services.gae_state.maybe_write_centroid_snapshot", return_value=False))
        stack.enter_context(patch("app.services.snapshots.maybe_write_profile_snapshot", new_callable=AsyncMock))
        stack.enter_context(patch("app.services.learning_health.LearningHealthMonitor.evaluate", new_callable=AsyncMock, return_value={"status": "GREEN"}))
        app.dependency_overrides[get_learning_policy] = lambda: _LearningPolicy(learning_enabled)
        stack.callback(app.dependency_overrides.pop, get_learning_policy, None)

        result = await report_decision_outcome(_make_request())

    return result, learning_state


def _run(coro):
    return asyncio.run(coro)


def test_empty_factor_vector_raises(soc_triage_harness):
    with pytest.raises(ValueError, match="factor_vector must have 6 elements, got 0"):
        _run(_call_with_factor_vector([], soc_triage_harness))


def test_none_factor_vector_raises(soc_triage_harness):
    with pytest.raises(ValueError, match="factor_vector must have 6 elements, got None"):
        _run(_call_with_factor_vector(None, soc_triage_harness))


def test_wrong_length_factor_vector_raises(soc_triage_harness):
    with pytest.raises(ValueError, match="factor_vector must have 6 elements, got 3"):
        _run(_call_with_factor_vector([0.1, 0.2, 0.3], soc_triage_harness))


def test_valid_factor_vector_uses_real_scorer_and_outcome_path(soc_triage_harness):
    cfg = SOCDomainConfig()
    scorer = cfg.build_profile_scorer()
    scoring = scorer.score(_VALID_VECTOR, cfg.get_category_index(_CATEGORY))

    assert scoring.action_name == "investigate"
    assert scoring.confidence == pytest.approx(0.8737039501931604)

    result, learning_state = _run(
        _call_with_factor_vector(json.dumps(_VALID_VECTOR), soc_triage_harness)
    )

    learning_state.update.assert_not_called()
    assert result["consequence"] == "stable"


def test_factor_validation_message_includes_expected_length(soc_triage_harness):
    with pytest.raises(ValueError) as exc:
        _run(_call_with_factor_vector([0.1, 0.2, 0.3], soc_triage_harness))

    message = str(exc.value)
    assert "factor_vector must have 6 elements" in message
    assert "got 3" in message
