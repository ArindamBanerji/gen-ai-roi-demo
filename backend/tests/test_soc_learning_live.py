import asyncio
import json
from uuid import uuid4
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import numpy as np
import pytest

from app.main import app
from app.domains.soc import config as soc_config
from app.domains.soc.config import SCORER_ACTIONS
from app.domains.soc.scorer_adapter import SOCCompoundingScorerAdapter
from copilot_sdk.graph.memory_store import InMemoryGraphStore
from copilot_sdk.scoring.scorer import CompoundingScorer
from app.services.triage_providers import get_learning_policy
from app.models.schemas import OutcomeRequest
from app.routers import triage
from test_rl_triage_integration import _patch_common_outcome, _decision_record


@pytest.fixture(autouse=True)
def _test_profile_for_in_memory_scorers(monkeypatch):
    original = CompoundingScorer.from_preset

    def from_preset(*args, **kwargs):
        kwargs.setdefault("profile", "test")
        return original(*args, **kwargs)

    monkeypatch.setattr(CompoundingScorer, "from_preset", from_preset)


FACTOR_VECTOR = np.array([0.9, 0.9, 0.9, 0.9, 0.9, 0.1], dtype=float)
CATEGORY_INDEX = 0
GROUND_TRUTH_ACTION = "investigate"


class _LearningPolicy:
    def __init__(self, enabled: bool):
        self._enabled = enabled

    def enabled(self) -> bool:
        return self._enabled


def _set_soc_learning(monkeypatch, enabled: bool) -> None:
    monkeypatch.setattr(soc_config, "LEARNING_ENABLED", False)
    monkeypatch.setitem(
        app.dependency_overrides,
        get_learning_policy,
        lambda: _LearningPolicy(enabled),
    )
    if enabled:
        monkeypatch.setenv("SOC_LEARNING_ENABLED", "true")
    else:
        monkeypatch.delenv("SOC_LEARNING_ENABLED", raising=False)


def _score_probabilities(scorer: SOCCompoundingScorerAdapter) -> np.ndarray:
    result = scorer.score(FACTOR_VECTOR, category_index=CATEGORY_INDEX)
    return np.asarray(result.probabilities, dtype=float)


def _apply_verified_outcome(monkeypatch, harness) -> float:
    scorer = harness.scorer
    decision_id = "LEARN-" + uuid4().hex
    policy = app.dependency_overrides[get_learning_policy]
    result = scorer.score(FACTOR_VECTOR, category_index=CATEGORY_INDEX)
    _patch_common_outcome(monkeypatch, harness, _decision_record(
        factor_vector=json.dumps(FACTOR_VECTOR.tolist()),
        action=result.action_name, alert_type="anomalous_login"), decision_id=decision_id)
    monkeypatch.setitem(app.dependency_overrides, get_learning_policy, policy)
    monkeypatch.setattr("app.services.learning_health.LearningHealthMonitor.evaluate",
                        AsyncMock(return_value={"status": "GREEN", "auto_pause_active": False}))
    @asynccontextmanager
    async def acquire():
        yield scorer
    monkeypatch.setattr("app.services.gae_state.acquire_scorer", acquire)
    monkeypatch.setattr("app.services.gae_state.get_profile_scorer", lambda: scorer)
    monkeypatch.setattr("app.services.gae_state.get_learning_store", lambda: harness.store)
    before = np.asarray(scorer.mu, dtype=float).copy()
    asyncio.run(triage.report_decision_outcome(OutcomeRequest(
        alert_id="ALERT-RL", decision_id=decision_id,
        outcome="correct" if result.action_name == GROUND_TRUTH_ACTION else "incorrect",
        analyst_action=GROUND_TRUTH_ACTION)))
    assert harness.get_decision(decision_id)["status"] in {"confirmed", "overridden"}
    return float(np.linalg.norm(np.asarray(scorer.mu, dtype=float) - before))


def test_soc_learning_changes_score(monkeypatch, soc_triage_harness):
    _set_soc_learning(monkeypatch, True)
    scorer = soc_triage_harness.scorer

    score_1 = _score_probabilities(scorer)
    centroid_delta = _apply_verified_outcome(monkeypatch, soc_triage_harness)
    score_2 = _score_probabilities(scorer)

    assert app.dependency_overrides[get_learning_policy]().enabled() is True
    assert centroid_delta > 0.0
    assert not np.allclose(score_2, score_1)


def test_soc_learning_disabled_no_change(monkeypatch, soc_triage_harness):
    _set_soc_learning(monkeypatch, False)
    scorer = soc_triage_harness.scorer

    score_1 = _score_probabilities(scorer)
    centroid_delta = _apply_verified_outcome(monkeypatch, soc_triage_harness)
    score_2 = _score_probabilities(scorer)

    assert app.dependency_overrides[get_learning_policy]().enabled() is False
    assert centroid_delta == 0.0
    np.testing.assert_allclose(score_2, score_1)


def test_soc_learning_toggle(monkeypatch, soc_triage_harness):
    scorer = soc_triage_harness.scorer

    _set_soc_learning(monkeypatch, False)
    score_1 = _score_probabilities(scorer)
    disabled_delta = _apply_verified_outcome(monkeypatch, soc_triage_harness)
    score_2 = _score_probabilities(scorer)

    _set_soc_learning(monkeypatch, True)
    enabled_delta = _apply_verified_outcome(monkeypatch, soc_triage_harness)
    score_3 = _score_probabilities(scorer)

    assert disabled_delta == 0.0
    np.testing.assert_allclose(score_2, score_1)
    assert enabled_delta > 0.0
    assert not np.allclose(score_3, score_2)
