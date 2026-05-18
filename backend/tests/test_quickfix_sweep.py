import inspect
from pathlib import Path

import numpy as np
import pytest

from app.core.state_manager import DemoStateManager
from app.routers import platform, soc
from app.services import rl_engine
import app.main as main


def test_reset_handlers_are_registered_in_startup_order():
    source = Path(main.__file__).read_text(encoding="utf-8")

    expected = [
        'state_manager.register("learning_state"',
        'state_manager.register("rl_engine"',
        'state_manager.register("platform_caches"',
        'state_manager.register("baseline_caches"',
        'state_manager.register("servicenow_mock"',
    ]
    for snippet in expected:
        assert snippet in source

    positions = [source.index(snippet) for snippet in expected]
    assert positions == sorted(positions)


@pytest.mark.asyncio
async def test_state_manager_registration_resets_rl_singletons():
    rl_engine.reset_rl_state()
    old_ledger = rl_engine.get_reward_ledger()
    reward = rl_engine.RewardComputer(
        "soc",
        {"credential_access": {"base": 0.70}},
    ).compute("escalate", "correct", "credential_access", {})
    old_ledger.append("D-quickfix", reward, "credential_access", "escalate")
    assert old_ledger.get_entries()

    manager = DemoStateManager()
    manager.register("rl_engine", rl_engine.reset_rl_state)

    await manager.reset_except([])

    assert rl_engine._reward_ledger is None
    assert rl_engine.get_reward_ledger().get_entries() == []
    assert old_ledger.get_entries()


def test_platform_reset_reassigns_all_cache_globals(monkeypatch):
    signal_cache = [{"signal": "kept"}]
    domain_cache = {"domains": [{"id": "soc"}]}
    warm_cache = {"warm_start_evidence": [{"id": "warm"}]}
    chain_cache = {"chain_credits": [{"id": "chain"}]}
    reward_cache = {"reward_breakdown": [{"id": "reward"}]}
    exploration_cache = {"exploration_log": [{"id": "explore"}]}

    monkeypatch.setattr(platform, "_SIGNAL_CACHE", signal_cache)
    monkeypatch.setattr(platform, "_DOMAIN_TABLE_CACHE", domain_cache)
    monkeypatch.setattr(platform, "_WARM_START_CACHE", warm_cache)
    monkeypatch.setattr(platform, "_CHAIN_CREDIT_CACHE", chain_cache)
    monkeypatch.setattr(platform, "_RL_REWARD_CACHE", reward_cache)
    monkeypatch.setattr(platform, "_RL_EXPLORATION_CACHE", exploration_cache)

    platform.reset_platform_caches()

    assert platform._SIGNAL_CACHE is None
    assert platform._DOMAIN_TABLE_CACHE is None
    assert platform._WARM_START_CACHE is None
    assert platform._CHAIN_CREDIT_CACHE is None
    assert platform._RL_REWARD_CACHE is None
    assert platform._RL_EXPLORATION_CACHE is None
    assert signal_cache == [{"signal": "kept"}]
    assert domain_cache == {"domains": [{"id": "soc"}]}
    assert warm_cache == {"warm_start_evidence": [{"id": "warm"}]}
    assert chain_cache == {"chain_credits": [{"id": "chain"}]}
    assert reward_cache == {"reward_breakdown": [{"id": "reward"}]}
    assert exploration_cache == {"exploration_log": [{"id": "explore"}]}
    assert ".clear(" not in inspect.getsource(platform.reset_platform_caches)


@pytest.mark.asyncio
async def test_state_manager_registration_resets_platform_caches(monkeypatch):
    monkeypatch.setattr(platform, "_SIGNAL_CACHE", [{"signal": "stale"}])
    monkeypatch.setattr(platform, "_DOMAIN_TABLE_CACHE", {"domains": []})
    monkeypatch.setattr(platform, "_WARM_START_CACHE", {"warm_start_evidence": []})
    monkeypatch.setattr(platform, "_CHAIN_CREDIT_CACHE", {"chain_credits": []})
    monkeypatch.setattr(platform, "_RL_REWARD_CACHE", {"reward_breakdown": []})
    monkeypatch.setattr(platform, "_RL_EXPLORATION_CACHE", {"exploration_log": []})

    manager = DemoStateManager()
    manager.register("platform_caches", platform.reset_platform_caches)

    await manager.reset_all()

    assert platform._SIGNAL_CACHE is None
    assert platform._DOMAIN_TABLE_CACHE is None
    assert platform._WARM_START_CACHE is None
    assert platform._CHAIN_CREDIT_CACHE is None
    assert platform._RL_REWARD_CACHE is None
    assert platform._RL_EXPLORATION_CACHE is None


def test_baseline_reset_reassigns_initial_values(monkeypatch):
    scorer = object()
    bootstrap = np.ones((1, 1, 1), dtype=np.float64)

    monkeypatch.setattr(soc, "_BASELINE_SCORER", scorer)
    monkeypatch.setattr(soc, "_BASELINE_SCORER_SOURCE", "bootstrap_centroids")
    monkeypatch.setattr(soc, "_BOOTSTRAP_CENTROIDS_CACHE", bootstrap)

    soc.reset_baseline_caches()

    assert soc._BASELINE_SCORER is None
    assert soc._BASELINE_SCORER_SOURCE == "uninitialized"
    assert soc._BOOTSTRAP_CENTROIDS_CACHE is None
    np.testing.assert_allclose(bootstrap, np.ones((1, 1, 1), dtype=np.float64))


@pytest.mark.asyncio
async def test_state_manager_registration_resets_baseline_caches(monkeypatch):
    monkeypatch.setattr(soc, "_BASELINE_SCORER", object())
    monkeypatch.setattr(soc, "_BASELINE_SCORER_SOURCE", "bootstrap_centroids")
    monkeypatch.setattr(soc, "_BOOTSTRAP_CENTROIDS_CACHE", np.ones((1, 1, 1)))

    manager = DemoStateManager()
    manager.register("baseline_caches", soc.reset_baseline_caches)

    await manager.reset_except([])

    assert soc._BASELINE_SCORER is None
    assert soc._BASELINE_SCORER_SOURCE == "uninitialized"
    assert soc._BOOTSTRAP_CENTROIDS_CACHE is None
