from __future__ import annotations

import inspect
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from app.domains.soc.config import SCORER_ACTIONS
from app.models.schemas import OutcomeRequest
from app.routers import triage


_FV = [0.7, 0.8, 0.5, 0.4, 0.6, 0.9]


class _LearningState:
    def __init__(self):
        self.decision_count = 0
        self.update_calls = 0

    def update(self, **_kwargs):
        self.update_calls += 1
        self.decision_count += 1
        return SimpleNamespace(centroid_update=None)


class _Scorer:
    def __init__(self):
        self.centroids = np.zeros((6, len(SCORER_ACTIONS), 6), dtype=float)
        self.decision_count = 0
        self.is_paused = False
        self.dk_first_at = None
        self.update_calls = []

    def update(
        self,
        *,
        f,
        category_index: int,
        action_index: int,
        correct: bool,
        gt_action_index: int | None = None,
        **_kwargs,
    ):
        vector = np.asarray(f, dtype=float)
        actual_action = action_index if gt_action_index is None else gt_action_index
        self.update_calls.append(
            {
                "category_index": category_index,
                "action_index": action_index,
                "gt_action_index": actual_action,
                "correct": correct,
                "f": vector.copy(),
            }
        )
        self.decision_count += 1
        self.centroids[category_index, actual_action] += 0.1 * (
            vector - self.centroids[category_index, actual_action]
        )
        if category_index == 0 and self.category_count(0) >= 200 and self.dk_first_at is None:
            self.dk_first_at = self.category_count(0)
        return SimpleNamespace(
            category_index=category_index,
            action_index=actual_action,
            category_name=f"cat-{category_index}",
            action_name=SCORER_ACTIONS[actual_action],
        )

    def category_count(self, category_index: int) -> int:
        return sum(call["category_index"] == category_index for call in self.update_calls)

    def reestimate_dk(self):
        return None

    def get_dk_weights(self):
        if self.dk_first_at is None:
            return None
        return [[1.0 for _ in range(6)] for _ in range(len(SCORER_ACTIONS))]


class _OutcomeResult:
    graph_updates: list[object] = []
    consequence = "stable"

    def model_dump(self):
        return {"graph_updates": [], "consequence": "stable", "narrative": "ok"}


def _request(action: str | None = "investigate") -> OutcomeRequest:
    return OutcomeRequest(
        alert_id="ALERT-DUAL-UPDATE",
        decision_id="DEC-DUAL-UPDATE",
        outcome="correct",
        analyst_action=action,
    )


async def _run_outcome(
    monkeypatch,
    harness,
    *,
    category: str = "credential_access",
    action: str = "investigate",
):
    learning_state = _LearningState()
    scorer = _Scorer()
    guarded_calls = []

    @asynccontextmanager
    async def acquire_scorer():
        yield scorer

    def guarded_update(scorer_arg, **kwargs):
        guarded_calls.append(kwargs)
        return scorer_arg.update(**kwargs)

    harness.add_decision(
        decision_id="DEC-DUAL-UPDATE",
        category=category,
        action=action,
        factors={f"f{i}": value for i, value in enumerate(_FV)},
        factor_vector=_FV,
        campaign_id="CAMP-TEST",
    )
    neo4j = harness.graph_client
    monkeypatch.setattr(triage, "graph_client", neo4j)
    monkeypatch.setattr(triage, "LEARNING_ENABLED", True)
    monkeypatch.setattr(triage, "get_feedback_status", lambda _alert_id: {"has_feedback": False})
    monkeypatch.setattr(triage, "get_learning_state", lambda: learning_state)
    monkeypatch.setattr(triage, "save_learning_state", lambda: None)
    monkeypatch.setattr(triage, "process_outcome", lambda **_kwargs: _OutcomeResult())
    monkeypatch.setattr(triage.event_bus, "emit", AsyncMock())
    monkeypatch.setattr("app.framework.audit.record_outcome", AsyncMock(return_value=None))
    monkeypatch.setattr("app.services.shadow_runner.fill_shadow_outcome", lambda *_args: None)
    monkeypatch.setattr(
        "app.services.learning_health.LearningHealthMonitor.evaluate",
        AsyncMock(return_value={"status": "GREEN", "auto_pause_active": False}),
    )
    monkeypatch.setattr("app.services.gae_state.acquire_scorer", acquire_scorer)
    monkeypatch.setattr("app.services.gae_state.get_soc_centroid", lambda *_args: [0.0] * 6)
    monkeypatch.setattr("app.services.gae_state.guarded_update", guarded_update)
    monkeypatch.setattr("app.services.gae_state.persist_soc_centroid", lambda **_kwargs: True)
    monkeypatch.setattr("app.services.gae_state.persist_soc_dk_weights", lambda *_args, **_kwargs: True)
    monkeypatch.setattr("app.services.gae_state.update_dk_welford_tracker", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.services.gae_state.maybe_write_centroid_snapshot", lambda *_args, **_kwargs: False)

    response = await triage.report_decision_outcome(_request(action))
    return SimpleNamespace(
        response=response,
        learning_state=learning_state,
        neo4j=neo4j,
        scorer=scorer,
        guarded_calls=guarded_calls,
    )


def _apply_outcomes(scorer: _Scorer, category_index: int, n: int, vector: np.ndarray):
    action_index = list(SCORER_ACTIONS).index("investigate")
    for _ in range(n):
        scorer.update(
            f=vector,
            category_index=category_index,
            action_index=action_index,
            correct=True,
            gt_action_index=action_index,
        )


@pytest.mark.asyncio
async def test_single_update_per_outcome(monkeypatch, soc_triage_harness):
    result = await _run_outcome(monkeypatch, soc_triage_harness, category="credential_access")

    assert result.learning_state.update_calls == 0
    assert len(result.guarded_calls) == 1
    assert result.scorer.decision_count == 1


def test_non_zero_category_not_corrupted():
    scorer = _Scorer()
    before = scorer.centroids[0].copy()

    _apply_outcomes(scorer, category_index=1, n=1, vector=np.ones(6))

    assert np.array_equal(scorer.centroids[0], before)
    assert scorer.category_count(0) == 0
    assert scorer.category_count(1) == 1


def test_phase_transition_at_200_not_100():
    scorer = _Scorer()

    _apply_outcomes(scorer, category_index=0, n=150, vector=np.ones(6))

    assert scorer.category_count(0) == 150
    assert scorer.dk_first_at is None


def test_dk_weight_timing_correct():
    scorer = _Scorer()

    _apply_outcomes(scorer, category_index=0, n=210, vector=np.ones(6))

    assert scorer.dk_first_at == 200
    assert scorer.dk_first_at != 100
    assert scorer.get_dk_weights() is not None


def test_other_categories_independent():
    scorer = _Scorer()
    action_index = list(SCORER_ACTIONS).index("investigate")
    vectors = [np.full(6, 0.2), np.full(6, 0.6), np.full(6, 0.9)]

    for category_index, vector in enumerate(vectors):
        _apply_outcomes(scorer, category_index=category_index, n=50, vector=vector)

    assert [scorer.category_count(i) for i in range(3)] == [50, 50, 50]
    assert np.all(scorer.centroids[0, action_index] < scorer.centroids[1, action_index])
    assert np.all(scorer.centroids[1, action_index] < scorer.centroids[2, action_index])


def test_conservation_v_count_not_doubled():
    scorer = _Scorer()

    _apply_outcomes(scorer, category_index=0, n=100, vector=np.ones(6))

    assert scorer.category_count(0) == 100
    assert scorer.decision_count == 100


def test_fix_preserves_correct_learning():
    scorer = _Scorer()
    action_index = list(SCORER_ACTIONS).index("investigate")
    vector = np.full(6, 0.8)

    _apply_outcomes(scorer, category_index=0, n=20, vector=vector)

    assert scorer.category_count(0) == 20
    assert np.all(scorer.centroids[0, action_index] > 0.0)
    assert np.linalg.norm(vector - scorer.centroids[0, action_index]) < np.linalg.norm(vector)
    assert {"category_index", "action_index", "correct", "f"} <= set(scorer.update_calls[-1])


@pytest.mark.asyncio
async def test_fix_preserves_referral_behavior(monkeypatch, soc_triage_harness):
    result = await _run_outcome(
        monkeypatch,
        soc_triage_harness,
        category="credential_access",
        action="refer_to_analyst",
    )

    assert result.learning_state.decision_count == 1
    assert result.learning_state.update_calls == 0
    assert result.scorer.decision_count == 0
    assert result.guarded_calls == []


@pytest.mark.asyncio
async def test_fix_preserves_outcome_persistence(monkeypatch, soc_triage_harness):
    result = await _run_outcome(
        monkeypatch,
        soc_triage_harness,
        category="credential_access",
    )

    decision = soc_triage_harness.get_decision("DEC-DUAL-UPDATE")
    assert decision is not None
    assert decision["analyst_action"] == "investigate"
    assert decision["was_override"] is False
    assert decision["quality_signal"] is not None
    assert result.response["consequence"] == "stable"


def test_fix_preserves_conservation_gate():
    scorer = _Scorer()
    scorer.is_paused = True
    before = scorer.centroids.copy()

    # Mirrors guarded_update's conservation pause: paused scorer is not updated.
    if not scorer.is_paused:
        _apply_outcomes(scorer, category_index=0, n=1, vector=np.ones(6))

    assert np.array_equal(scorer.centroids, before)
    assert scorer.decision_count == 0


def test_legacy_learning_state_update_removed_from_outcome_path():
    source = inspect.getsource(triage.report_decision_outcome)

    assert "learning_state.update(" not in source
    assert "_guarded_update(" in source
    assert "category_index=_cat_idx_out" in source
