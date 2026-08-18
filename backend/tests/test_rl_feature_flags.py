from types import SimpleNamespace

import pytest

from app.domains.soc import config as soc_config
from app.models.schemas import ProcessAlertRequest
from app.routers import metrics
from app.routers import triage
from app.services import rl_engine


def test_all_rl_flags_default_false():
    assert soc_config.RL_REWARD_LEDGER_ENABLED is False
    assert soc_config.RL_EXPLORATION_ENABLED is False
    assert soc_config.RL_ETA_MODULATION_ENABLED is False
    assert soc_config.RL_CHAIN_CREDIT_ENABLED is False


def test_exploration_action_space_excludes_refer_to_analyst():
    assert "refer_to_analyst" not in soc_config.SCORER_ACTIONS
    assert "refer_to_analyst" in soc_config.SOC_ROUTING_ACTIONS
    policy = rl_engine.ExplorationPolicy(
        n_categories=1,
        n_actions=len(soc_config.SCORER_ACTIONS),
        epsilon_base=1.0,
        target_headroom=2.0,
    )
    decision = policy.propose([0.1, 0.2, 0.3, 0.4], 0, 2.0)
    assert decision.explored_action in range(len(soc_config.SCORER_ACTIONS))


def test_learning_enabled_is_still_centroid_gate():
    source = open(triage.__file__, encoding="utf-8").read()
    assert "_soc_learning_active = _soc_learning_enabled()" in source
    assert "if _soc_learning_active and action_name in SCORER_ACTIONS:" in source
    assert "_guarded_update(" in source
    assert triage.LEARNING_ENABLED is True


def test_binary_outcome_not_derived_from_graded_reward():
    result = rl_engine.RewardComputer(
        "soc",
        {"credential_access": {"base": 0.70}},
        reference_reward=0.01,
    ).compute("escalate", "incorrect", "credential_access", {})
    assert result.graded_reward < -1.0
    assert result.binary_outcome is False


@pytest.mark.asyncio
async def test_no_exploration_metadata_when_flag_false(monkeypatch):
    from test_rl_triage_integration import _patch_common_analyze

    fake_graph = _patch_common_analyze(monkeypatch)
    monkeypatch.setattr(soc_config, "RL_EXPLORATION_ENABLED", False)

    response = await triage.analyze_alert(ProcessAlertRequest(alert_id="ALERT-RL"))

    assert response["recommendation"]["action"] == "refer_to_analyst"
    assert not any("d.explored                = true" in query for query in fake_graph.queries)


@pytest.mark.asyncio
async def test_reset_demo_alerts_clears_rl_state(monkeypatch):
    rl_engine.reset_rl_state()
    rl_engine.get_reward_ledger().append(
        "D-1",
        rl_engine.RewardComputer("soc", {"credential_access": {"base": 0.70}}).compute(
            "escalate",
            "correct",
            "credential_access",
            {},
        ),
        "credential_access",
        "escalate",
    )

    class FakeAGE:
        async def run_query(self, query):
            return [{"reset_count": 1}]

    monkeypatch.setattr(triage, "graph_client", FakeAGE())
    monkeypatch.setattr(
        triage.state_manager,
        "reset_except",
        lambda _preserved: SimpleNamespace(__await__=lambda self: iter([None])),
    )

    async def fake_reset_except(_preserved):
        return None

    monkeypatch.setattr(triage.state_manager, "reset_except", fake_reset_except)
    monkeypatch.setattr(
        "app.services.servicenow_mock.get_servicenow_mock",
        lambda: SimpleNamespace(reset=lambda: None),
    )

    await triage.reset_demo_alerts()
    assert rl_engine.get_reward_ledger().get_entries() == []


@pytest.mark.asyncio
async def test_reset_all_demo_data_clears_rl_state(monkeypatch):
    rl_engine.reset_rl_state()
    rl_engine.get_reward_ledger().append(
        "D-1",
        rl_engine.RewardComputer("soc", {"credential_access": {"base": 0.70}}).compute(
            "escalate",
            "correct",
            "credential_access",
            {},
        ),
        "credential_access",
        "escalate",
    )

    hard_reset_calls = []

    class FakeStateManager:
        def __init__(self, **_kwargs):
            pass

        async def hard_reset(self, preserve_learning):
            hard_reset_calls.append(preserve_learning)

    async def fake_reset_except(_preserved):
        return None

    monkeypatch.setattr("app.services.state_manager.StateManager", FakeStateManager)
    monkeypatch.setattr("app.core.domain_registry.get_domain_config", lambda: SimpleNamespace())
    monkeypatch.setattr("app.core.state_manager.state_manager.reset_except", fake_reset_except)

    response = await metrics.reset_all_demo_data()

    assert response["status"] == "success"
    assert hard_reset_calls == [True]
    assert rl_engine.get_reward_ledger().get_entries() == []


def test_phase4_flags_are_runtime_patchable(monkeypatch):
    monkeypatch.setattr(soc_config, "RL_REWARD_LEDGER_ENABLED", True)
    monkeypatch.setattr(soc_config, "RL_EXPLORATION_ENABLED", True)
    monkeypatch.setattr(soc_config, "RL_ETA_MODULATION_ENABLED", True)
    monkeypatch.setattr(soc_config, "RL_CHAIN_CREDIT_ENABLED", True)
    assert triage._rl_soc_config().RL_REWARD_LEDGER_ENABLED is True
    assert triage._rl_soc_config().RL_EXPLORATION_ENABLED is True
    assert triage._rl_soc_config().RL_ETA_MODULATION_ENABLED is True
    assert triage._rl_soc_config().RL_CHAIN_CREDIT_ENABLED is True
