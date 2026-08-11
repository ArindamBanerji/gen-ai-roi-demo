from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from unittest.mock import AsyncMock

from app.domains.soc import config as soc_config
from app.models.schemas import ProcessAlertRequest
from app.routers import triage
from app.services import rl_engine
from test_rl_triage_integration import (
    _call_outcome,
    _decision_record,
    _patch_common_analyze,
    _patch_common_outcome,
)


@pytest.mark.asyncio
async def test_all_flags_true_pipeline_exercises_rl_paths(monkeypatch, soc_triage_harness):
    rl_engine.reset_rl_state()
    monkeypatch.setattr(soc_config, "RL_REWARD_LEDGER_ENABLED", True)
    monkeypatch.setattr(soc_config, "RL_EXPLORATION_ENABLED", True)
    monkeypatch.setattr(soc_config, "RL_ETA_MODULATION_ENABLED", True)
    monkeypatch.setattr(soc_config, "RL_CHAIN_CREDIT_ENABLED", True)
    monkeypatch.setattr(triage, "LEARNING_ENABLED", True)

    policy = rl_engine.ExplorationPolicy(6, 4, epsilon_base=1.0, target_headroom=2.0)
    policy.alphas[0] = [1.0, 5.0, 1.0, 1.0]
    monkeypatch.setattr(rl_engine, "get_exploration_policy", lambda: policy)
    monkeypatch.setattr(rl_engine.random, "betavariate", lambda alpha, beta: alpha)

    analyze_graph = _patch_common_analyze(monkeypatch)
    analyze_response = await triage.analyze_alert(ProcessAlertRequest(alert_id="ALERT-RL"))

    assert analyze_response["recommendation"]["action"] == "escalate"
    assert any("d.explored                = true" in query for query in analyze_graph.queries)
    before_posterior_alpha = policy.alphas[0][1]

    outcome_graph, _learning_state = _patch_common_outcome(
        monkeypatch,
        soc_triage_harness,
        _decision_record(
            action="investigate",
            explored=True,
            explored_but_referred=False,
            exploration_executed=True,
            explored_action="investigate",
        ),
    )
    monkeypatch.setattr(
        "app.services.learning_health.LearningHealthMonitor.evaluate",
        AsyncMock(return_value={"status": "GREEN", "conservation": {"headroom": 10.0}}),
    )
    monkeypatch.setattr("app.services.gae_state.get_mu_zero", lambda: None)

    scorer = SimpleNamespace(
        eta=0.05,
        eta_neg=0.05,
        eta_override=0.01,
        set_conservation_status=lambda _status: None,
    )
    eta_seen = []

    @asynccontextmanager
    async def fake_acquire():
        yield scorer

    def guarded_update_spy(scorer_arg, **_kwargs):
        eta_seen.append((scorer_arg.eta, scorer_arg.eta_neg, scorer_arg.eta_override))
        return SimpleNamespace(centroid_update=None)

    chain_calls = []

    class Assigner:
        async def assign_chain_credit(self, **kwargs):
            chain_calls.append(kwargs)
            return []

    monkeypatch.setattr("app.services.gae_state.acquire_scorer", fake_acquire)
    monkeypatch.setattr("app.services.gae_state.guarded_update", guarded_update_spy)
    monkeypatch.setattr(rl_engine, "get_credit_assigner", lambda: Assigner())

    result = await _call_outcome()

    entries = rl_engine.get_reward_ledger().get_entries()
    assert result["consequence"] == "ok"
    assert len(entries) == 1
    assert entries[0]["binary_outcome"] is True
    assert entries[0]["graded_reward"] > 0
    assert policy.alphas[0][1] == before_posterior_alpha + 1.0
    assert chain_calls and chain_calls[0]["source_decision_id"] == "D-RL"
    assert eta_seen and eta_seen[0][0] > 0.05 and eta_seen[0][1] > 0.05 and eta_seen[0][2] > 0.01
    assert scorer.eta == 0.05
    assert scorer.eta_neg == 0.05
    assert scorer.eta_override == 0.01
    assert any("TRIGGERED_EVOLUTION" in query for query, _ in outcome_graph._queries)
