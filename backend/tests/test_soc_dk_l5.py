import math
import inspect
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from app.domains.soc import config as soc_config
from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES, SOCDomainConfig
from app.models.schemas import OutcomeRequest
from app.routers import triage
from app.services import gae_state
from gae.dk_estimator import CoordinateDescentEstimator
from gae.shrinkage import FixedAlpha
from gae.two_phase import DecisionCountPolicy


def test_soc_profile_scorer_uses_full_learning_strategy():
    scorer = SOCDomainConfig().build_profile_scorer()

    strategy = getattr(scorer, "_learning_strategy", None)
    assert strategy is not None
    assert isinstance(strategy.phase_policy, DecisionCountPolicy)
    assert strategy.phase_policy.n == 200
    assert isinstance(strategy.dk_estimator, CoordinateDescentEstimator)
    assert isinstance(strategy.shrinkage_schedule, FixedAlpha)
    assert math.isclose(strategy.shrinkage_schedule.alpha, 0.5)
    assert scorer.eta_override == 0.01
    assert scorer.auto_pause_on_amber is True
    assert list(scorer.categories) == list(SOC_CATEGORIES)
    assert list(scorer.actions) == list(SCORER_ACTIONS)


def test_soc_learning_enabled_gate_is_controlled(monkeypatch):
    monkeypatch.delenv("SOC_LEARNING_ENABLED", raising=False)
    monkeypatch.setattr(soc_config, "LEARNING_ENABLED", False)
    assert soc_config.is_learning_enabled() is False

    monkeypatch.setenv("SOC_LEARNING_ENABLED", "true")
    assert soc_config.is_learning_enabled() is True

    monkeypatch.setenv("SOC_LEARNING_ENABLED", "0")
    assert soc_config.is_learning_enabled() is False


def test_soc_under_calibrated_red_remains_red_for_l5_profile_path():
    status, reason = triage._soc_effective_conservation_status(
        {
            "status": "RED",
            "auto_pause_active": False,
            "components": {"verified_decisions": 5},
        }
    )

    assert status == "RED"
    assert reason is None


def test_soc_missing_status_is_unknown():
    status, reason = triage._soc_effective_conservation_status({})

    assert status == "UNKNOWN"
    assert reason is None


def test_soc_calibrating_status_is_not_green():
    status, reason = triage._soc_effective_conservation_status(
        {"status": "CALIBRATING", "auto_pause_active": False}
    )

    assert status == "CALIBRATING"
    assert reason is None


def test_soc_unrecognized_status_is_unknown():
    status, reason = triage._soc_effective_conservation_status({"status": "BROKEN"})

    assert status == "UNKNOWN"
    assert reason == "unrecognized_learning_health_status"


def test_soc_calibrated_red_still_pauses_l5_profile_path():
    status, reason = triage._soc_effective_conservation_status(
        {
            "status": "RED",
            "auto_pause_active": False,
            "components": {"verified_decisions": 300},
        }
    )

    assert status == "RED"
    assert reason is None


def test_soc_auto_pause_still_forces_red_l5_profile_path():
    status, reason = triage._soc_effective_conservation_status(
        {
            "status": "GREEN",
            "auto_pause_active": True,
            "components": {"verified_decisions": 5},
        }
    )

    assert status == "RED"
    assert reason == "auto_pause_active"


def test_soc_dk_phase_transition_and_reestimate():
    scorer = SOCDomainConfig().build_profile_scorer()
    category_index = 0
    action_index = 0
    f = np.array([0.9, 0.5, 0.5, 0.5, 0.5, 0.5], dtype=np.float64)

    for _ in range(200):
        scorer.update(
            f=f,
            category_index=category_index,
            action_index=action_index,
            correct=True,
            gt_action_index=action_index,
        )

    assert scorer.get_phase(category_index) == "VARIANCE_LEARNING"

    for _ in range(10):
        scorer.update(
            f=f,
            category_index=category_index,
            action_index=action_index,
            correct=True,
            gt_action_index=action_index,
        )

    scorer.reestimate_dk()
    assert scorer.get_dk_weights(category_index) is not None


def test_soc_dk_behavioral_gate_signal_vs_noise():
    scorer = SOCDomainConfig().build_profile_scorer()
    category_index = 0
    escalate_index = 0
    suppress_index = 2
    probe = np.array([0.95, 0.5, 0.5, 0.5, 0.5, 0.5], dtype=np.float64)
    before = scorer.score(probe, category_index)

    for _ in range(200):
        scorer.update(
            f=np.array([0.9, 0.5, 0.5, 0.5, 0.5, 0.5], dtype=np.float64),
            category_index=category_index,
            action_index=escalate_index,
            correct=True,
            gt_action_index=escalate_index,
        )

    rng = np.random.default_rng(7)
    for i in range(60):
        signal = 0.95 if i % 2 == 0 else 0.05
        gt = escalate_index if i % 2 == 0 else suppress_index
        f = np.array([signal, 0.5, 0.5, 0.5, 0.5, rng.random()], dtype=np.float64)
        scorer.update(
            f=f,
            category_index=category_index,
            action_index=gt,
            correct=True,
            gt_action_index=gt,
        )

    scorer.reestimate_dk()
    after = scorer.score(probe, category_index)

    assert scorer.get_dk_weights(category_index) is not None
    assert before.action_index != after.action_index
    assert after.action_index == escalate_index


def test_soc_outcome_persists_centroid_l5_in_mean_convergence(monkeypatch):
    store = MagicMock()
    monkeypatch.setattr(gae_state, "_learning_store", store)
    scorer = SimpleNamespace(
        get_phase=MagicMock(return_value="MEAN_CONVERGENCE"),
        centroids=np.zeros((len(SOC_CATEGORIES), len(SCORER_ACTIONS), 6), dtype=np.float64),
    )
    scorer.centroids[0, 1] = np.array([0.2, 0.3, 0.4, 0.5, 0.6, 0.7])

    assert gae_state.persist_soc_centroid(
        scorer=scorer,
        category="credential_access",
        category_index=0,
        action="investigate",
        action_index=1,
        caused_by_decision_id="DEC-SOC-1",
        pre_centroid=[0.0] * 6,
    )

    store.update_centroid.assert_called_once()
    assert store.update_centroid.call_args.kwargs["domain"] == "soc"
    assert store.update_centroid.call_args.kwargs["category"] == "credential_access"
    assert store.update_centroid.call_args.kwargs["action"] == "investigate"
    assert store.update_centroid.call_args.kwargs["caused_by_decision_id"] == "DEC-SOC-1"


def test_soc_outcome_skips_centroid_l5_in_variance_learning(monkeypatch):
    store = MagicMock()
    monkeypatch.setattr(gae_state, "_learning_store", store)
    scorer = SimpleNamespace(
        get_phase=MagicMock(return_value="VARIANCE_LEARNING"),
        centroids=np.zeros((len(SOC_CATEGORIES), len(SCORER_ACTIONS), 6), dtype=np.float64),
    )

    assert not gae_state.persist_soc_centroid(
        scorer=scorer,
        category="credential_access",
        category_index=0,
        action="investigate",
        action_index=1,
        caused_by_decision_id="DEC-SOC-2",
        pre_centroid=[0.0] * 6,
    )
    store.update_centroid.assert_not_called()


def test_soc_outcome_persists_dk_weight_welford_after_reestimate(monkeypatch):
    store = MagicMock()
    monkeypatch.setattr(gae_state, "_learning_store", store)
    gae_state.reset_dk_welford_tracker()
    gae_state.update_dk_welford_tracker(np.ones(6, dtype=np.float64), is_correct=True)
    scorer = SimpleNamespace(
        n_categories=len(SOC_CATEGORIES),
        get_dk_weights=MagicMock(return_value=np.ones(6, dtype=np.float64)),
    )

    assert gae_state.persist_soc_dk_weights(scorer)

    store.update_dk_weights.assert_called_once()
    kwargs = store.update_dk_weights.call_args.kwargs
    assert kwargs["domain"] == "soc"
    assert len(kwargs["weight_tensor"]) == len(SOC_CATEGORIES)
    assert kwargs["welford_state"] is not None


def test_soc_l5_failures_nonfatal(monkeypatch, caplog):
    store = MagicMock()
    store.update_centroid.side_effect = RuntimeError("store down")
    monkeypatch.setattr(gae_state, "_learning_store", store)
    scorer = SimpleNamespace(
        get_phase=MagicMock(return_value="MEAN_CONVERGENCE"),
        centroids=np.zeros((len(SOC_CATEGORIES), len(SCORER_ACTIONS), 6), dtype=np.float64),
    )

    with pytest.raises(RuntimeError, match="SOC L5 centroid persistence failed"):
        gae_state.persist_soc_centroid(
            scorer=scorer,
            category="credential_access",
            category_index=0,
            action="investigate",
            action_index=1,
            caused_by_decision_id="DEC-SOC-3",
            pre_centroid=[0.0] * 6,
        )
    assert "SOC L5 centroid persistence failed" in caplog.text


def test_soc_no_store_runtime_dk_still_runs(monkeypatch):
    monkeypatch.setattr(gae_state, "_learning_store", None)
    gae_state.reset_dk_welford_tracker()
    gae_state.update_dk_welford_tracker(np.ones(6, dtype=np.float64), is_correct=True)
    scorer = SimpleNamespace(
        n_categories=len(SOC_CATEGORIES),
        get_dk_weights=MagicMock(return_value=np.ones(6, dtype=np.float64)),
    )

    assert not gae_state.persist_soc_dk_weights(scorer)
    scorer.get_dk_weights.assert_not_called()


def test_soc_outcome_response_surfaces_l5_persistence_status():
    source = inspect.getsource(triage.report_decision_outcome)

    assert 'response_body["l5_centroid_persisted"]' in source
    assert 'response_body["l5_shaped_by_attempted"]' in source
    assert 'response_body["l5_persistence_skipped_reason"]' in source
    assert 'response_body["l5_persistence"]' in source
    assert "welford_state" not in source
    assert 'response_body["dk_weights"]' not in source


def test_soc_outcome_route_uses_l5_helpers_not_direct_age_writes():
    source = inspect.getsource(triage.report_decision_outcome)

    assert "_persist_soc_outcome_and_centroid(" in source
    assert "_persist_soc_dk_weights(" in source
    assert "_update_dk_welford_tracker(" in source
    assert "reestimate_dk" in source
    assert "update_centroid(" not in source
    assert "update_dk_weights(" not in source
    assert "_l5_upsert_current" not in source


class _RouteScorer:
    n_categories = len(SOC_CATEGORIES)

    def __init__(self, *, reestimate_error: Exception | None = None):
        self.reestimate_error = reestimate_error
        self.reestimate_calls = 0
        self.centroids = np.zeros((len(SOC_CATEGORIES), len(SCORER_ACTIONS), 6), dtype=np.float64)

    def reestimate_dk(self):
        self.reestimate_calls += 1
        if self.reestimate_error is not None:
            raise self.reestimate_error

    def get_dk_weights(self, _category_index):
        return np.ones(6, dtype=np.float64)


class _RouteLearningState:
    def __init__(self):
        self.decision_count = 42

    def update(self, **_kwargs):
        self.decision_count += 1
        return SimpleNamespace(centroid_update=None)


def _centroid_update(action_index: int):
    return SimpleNamespace(
        category_name="credential_access",
        category_index=0,
        action_name=SCORER_ACTIONS[action_index],
        action_index=action_index,
    )


async def _run_soc_outcome_with_route_patches(
    monkeypatch,
    harness,
    *,
    predicted_action: str = "escalate",
    analyst_action: str | None = None,
    outcome: str = "correct",
    reestimate_error: Exception | None = None,
):
    scorer = _RouteScorer(reestimate_error=reestimate_error)
    centroid_calls = []
    dk_calls = []

    harness.add_decision(
        decision_id="DEC-SOC-L5",
        category="credential_access",
        action=predicted_action,
        confidence=0.8,
        factors={f"f{i}": value for i, value in enumerate([0.2, 0.3, 0.4, 0.1, 0.5, 0.6])},
        factor_vector="[0.2, 0.3, 0.4, 0.1, 0.5, 0.6]",
        campaign_id="C-1",
        alert_type="anomalous_login",
    )

    @asynccontextmanager
    async def fake_acquire_scorer():
        yield scorer

    monkeypatch.setattr(triage, "LEARNING_ENABLED", True)
    monkeypatch.setattr(triage, "get_feedback_status", lambda _alert_id: {"has_feedback": False})
    monkeypatch.setattr(triage, "get_learning_state", lambda: _RouteLearningState())
    monkeypatch.setattr(triage, "save_learning_state", lambda: None)
    monkeypatch.setattr(triage.event_bus, "emit", AsyncMock())
    monkeypatch.setattr(
        triage,
        "process_outcome",
        lambda **_kwargs: SimpleNamespace(
            model_dump=lambda: {"graph_updates": [], "consequence": "ok"},
            graph_updates=[],
            consequence="ok",
        ),
    )
    monkeypatch.setattr("app.framework.audit.record_outcome", AsyncMock(return_value=None))
    monkeypatch.setattr("app.services.shadow_runner.fill_shadow_outcome", lambda *_args: None)
    monkeypatch.setattr(
        "app.services.learning_health.LearningHealthMonitor.evaluate",
        AsyncMock(return_value={"status": "GREEN", "auto_pause_active": False}),
    )
    monkeypatch.setattr("app.services.gae_state.acquire_scorer", fake_acquire_scorer)
    monkeypatch.setattr("app.services.gae_state.get_profile_scorer", lambda: scorer)
    monkeypatch.setattr("app.services.gae_state.get_soc_centroid", lambda *_args: [0.0] * 6)
    monkeypatch.setattr("app.services.gae_state.update_dk_welford_tracker", lambda *_args, **_kwargs: None)

    def fake_guarded_update(_scorer, **kwargs):
        return _centroid_update(kwargs["action_index"])

    def fake_persist_centroid(**kwargs):
        centroid_calls.append(kwargs)
        return True

    def fake_persist_dk_weights(*args, **kwargs):
        dk_calls.append((args, kwargs))
        return True

    monkeypatch.setattr("app.services.gae_state.guarded_update", fake_guarded_update)
    monkeypatch.setattr("app.services.gae_state.persist_soc_centroid", fake_persist_centroid)
    monkeypatch.setattr("app.services.gae_state.persist_soc_dk_weights", fake_persist_dk_weights)

    response = await triage.report_decision_outcome(
        OutcomeRequest(
            alert_id="ALERT-SOC-L5",
            decision_id="DEC-SOC-L5",
            outcome=outcome,
            analyst_action=analyst_action,
        )
    )
    return SimpleNamespace(
        response=response,
        scorer=scorer,
        centroid_calls=centroid_calls,
        dk_calls=dk_calls,
    )


@pytest.mark.asyncio
async def test_soc_outcome_l5_centroid_uses_actual_action_on_override(monkeypatch, soc_triage_harness):
    result = await _run_soc_outcome_with_route_patches(
        monkeypatch,
        soc_triage_harness,
        predicted_action="escalate",
        analyst_action="suppress",
        outcome="incorrect",
    )

    assert result.centroid_calls
    assert result.centroid_calls[0]["action"] == "suppress"
    assert result.centroid_calls[0]["action_index"] == SCORER_ACTIONS.index("suppress")
    assert result.centroid_calls[0]["caused_by_decision_id"] == "DEC-SOC-L5"
    assert result.response["l5_centroid_persisted"] is True
    assert result.response["l5_shaped_by_attempted"] is True
    assert result.response["l5_persistence_skipped_reason"] is None
    assert result.response["l5_persistence"]["l5_persistence_source"] == "profile_scorer"
    assert "dk_weights" not in result.response
    assert "welford_state" not in result.response


@pytest.mark.asyncio
async def test_soc_outcome_l5_centroid_uses_predicted_when_actual_equals_predicted(monkeypatch, soc_triage_harness):
    result = await _run_soc_outcome_with_route_patches(
        monkeypatch,
        soc_triage_harness,
        predicted_action="escalate",
        analyst_action="escalate",
        outcome="correct",
    )

    assert result.centroid_calls
    assert result.centroid_calls[0]["action"] == "escalate"
    assert result.centroid_calls[0]["action_index"] == SCORER_ACTIONS.index("escalate")


@pytest.mark.asyncio
async def test_soc_dk_persistence_skipped_when_reestimate_fails(monkeypatch, soc_triage_harness):
    result = await _run_soc_outcome_with_route_patches(
        monkeypatch,
        soc_triage_harness,
        predicted_action="escalate",
        analyst_action="escalate",
        outcome="correct",
        reestimate_error=RuntimeError("dk failed"),
    )

    assert result.scorer.reestimate_calls == 1
    assert result.dk_calls == []
    assert result.response["graph_updates"] == []


@pytest.mark.asyncio
async def test_soc_dk_persistence_runs_when_reestimate_succeeds(monkeypatch, soc_triage_harness):
    result = await _run_soc_outcome_with_route_patches(
        monkeypatch,
        soc_triage_harness,
        predicted_action="escalate",
        analyst_action="escalate",
        outcome="correct",
    )

    assert result.scorer.reestimate_calls == 1
    assert len(result.dk_calls) == 1
