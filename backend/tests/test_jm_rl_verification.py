"""Bespoke SOC verification for the shared JM and SDK RL contracts."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from app.services import rl_engine
from app.services.graph_store_adapter import GraphStoreAdapter
from app.services.learning import compute_soc_binary_reward
from copilot_sdk.config import GraphConfig
from copilot_sdk.graph.memory_store import InMemoryGraphStore
from copilot_sdk.graph.protocol import GraphStore
from copilot_sdk.rl import (
    CreditAssigner,
    DomainRewardFunction,
    ExplorationPolicy,
    RewardComputer,
)


ROOT = Path(__file__).parents[1]


class RecordingStore:
    """Complete stateful store used to verify adapter forwarding."""

    def __init__(self) -> None:
        self.values: dict[tuple[str, str, str], dict[str, Any]] = {}

    def save_evolution(self, domain: str, key: str, state: dict[str, Any]) -> None:
        self.values[("evolution", domain, key)] = dict(state)

    def get_evolution(self, domain: str, key: str) -> dict[str, Any] | None:
        return self.values.get(("evolution", domain, key))

    def save_posterior(self, domain: str, key: str, state: dict[str, Any]) -> None:
        self.values[("posterior", domain, key)] = dict(state)

    def get_posterior(self, domain: str, key: str) -> dict[str, Any] | None:
        return self.values.get(("posterior", domain, key))

    def save_promotion(self, domain: str, key: str, state: dict[str, Any]) -> None:
        self.values[("promotion", domain, key)] = dict(state)

    def get_promotion(self, domain: str, key: str) -> dict[str, Any] | None:
        return self.values.get(("promotion", domain, key))


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _store() -> InMemoryGraphStore:
    return InMemoryGraphStore(domain="soc", decision_id_prefix="SOC-")


def test_graphstore_protocol_is_runtime_available() -> None:
    assert isinstance(_store(), GraphStore)


def test_decision_round_trip_is_domain_scoped() -> None:
    store = _store()
    decision_id = store.write_decision("soc", "malware", "quarantine", 0.9, {"severity": 1.0})
    assert store.get_decision(decision_id, "soc")["domain"] == "soc"


def test_other_domain_decisions_are_not_returned() -> None:
    store = _store()
    store.write_decision("soc", "malware", "quarantine", 0.9, {"severity": 1.0})
    store.write_decision("trading", "malware", "quarantine", 0.9, {"severity": 1.0})
    assert all(row["domain"] == "soc" for row in store.get_decisions("soc"))


def test_evolution_state_round_trip_uses_age_contract() -> None:
    store = _store()
    state = {"generation": 3, "fitness": 0.82}
    store.save_evolution_state("soc", "variant-1", state)
    assert store.get_evolution_state("soc", "variant-1") == state


def test_posterior_state_round_trip_preserves_w_history() -> None:
    store = _store()
    state = {"W": [[1.0]], "history": [{"step": 1}]}
    store.save_posterior("soc", "posterior-1", state)
    assert store.get_posterior("soc", "posterior-1") == state


def test_promotion_state_round_trip_is_domain_scoped() -> None:
    store = _store()
    state = {"status": "promoted", "authority": "L3"}
    store.save_promotion("soc", "rule-1", state)
    assert store.get_promotion("soc", "rule-1") == state


def test_graphstore_adapter_forwards_evolution() -> None:
    backing = RecordingStore()
    adapter = GraphStoreAdapter(object(), backing)
    adapter.save_evolution("soc", "v1", {"generation": 2})
    assert adapter.get_evolution("soc", "v1") == {"generation": 2}


def test_graphstore_adapter_forwards_posterior_and_promotion() -> None:
    backing = RecordingStore()
    adapter = GraphStoreAdapter(object(), backing)
    adapter.save_posterior("soc", "p1", {"W": []})
    adapter.save_promotion("soc", "r1", {"status": "held"})
    assert adapter.get_posterior("soc", "p1") == {"W": []}
    assert adapter.get_promotion("soc", "r1") == {"status": "held"}


def test_graphstore_adapter_requires_real_dependencies() -> None:
    with pytest.raises(ValueError):
        GraphStoreAdapter(None, RecordingStore())
    with pytest.raises(ValueError):
        GraphStoreAdapter(object(), None)


def test_graph_failure_is_not_silently_substituted() -> None:
    source = _source("app/services/graph_store_adapter.py")
    assert "raise ValueError" in source
    assert "Using mock" not in source


def test_graph_config_is_the_soc_resolution_source() -> None:
    source = _source("app/main.py")
    assert "GraphConfig.load" in source
    assert "GraphConfig" in source


def test_graph_config_can_load_soc_test_profile() -> None:
    config = GraphConfig.load("soc", profile="test")
    assert config.domain == "soc"
    assert config.dsn


def test_conservation_reads_graph_store_state() -> None:
    source = _source("app/routers/triage.py")
    assert "conservation_status" in source
    assert "GraphStore" in source


def test_centroid_persistence_is_graph_backed() -> None:
    source = _source("app/services/gae_state.py")
    assert "write_centroid_checkpoint" in source
    assert "get_centroid_checkpoints" in source


def test_posterior_service_writes_graph_state() -> None:
    source = _source("app/services/posterior_store.py")
    assert "save_posterior" in source
    assert "create_graph_store" in source or "_graph_store" in source


def test_authority_ladder_writes_promotion_state() -> None:
    source = _source("app/services/authority_ladder.py")
    assert "save_promotion" in source
    assert "GraphStoreAdapter" in source


def test_no_runtime_json_checkpoint_writer() -> None:
    source = _source("app/services/gae_state.py")
    assert "json.dump(" not in source


def test_no_soc_sqlite_wal_checkpoint_path() -> None:
    source = _source("app/services/gae_state.py")
    assert "sqlite3.connect" not in source.lower()


def test_iks_path_uses_verified_decisions() -> None:
    source = _source("app/routers/soc.py")
    assert "verified" in source.lower()
    assert "iks" in source.lower()


def test_health_endpoint_reports_graph_component() -> None:
    source = _source("app/main.py")
    assert '"graph"' in source
    assert "posterior_store" in source


def test_soc_binary_reward_satisfies_sdk_protocol() -> None:
    reward = rl_engine.SOCBinaryReward()
    assert isinstance(reward, DomainRewardFunction)


def test_soc_binary_reward_range_is_canonical() -> None:
    assert rl_engine.SOCBinaryReward().reward_range() == (0.0, 1.0)


def test_soc_binary_reward_correct_triage_is_one() -> None:
    assert rl_engine.SOCBinaryReward().compute("suppress", "suppress", {}) == 1.0


def test_soc_binary_reward_incorrect_triage_is_zero() -> None:
    assert rl_engine.SOCBinaryReward().compute("suppress", "refer", {}) == 0.0


def test_sdk_reward_computer_returns_binary_result() -> None:
    result = rl_engine.get_sdk_reward_computer().compute("suppress", "suppress", {})
    assert result.reward == 1.0
    assert result.binary_reward == 1.0


def test_binary_reward_trajectory_is_deterministic() -> None:
    reward = rl_engine.SOCBinaryReward()
    trajectory = [reward.compute("suppress", action, {}) for action in ("suppress", "refer", "suppress")]
    assert trajectory == [1.0, 0.0, 1.0]


def test_reward_persists_through_sdk_graph_ledger() -> None:
    class LedgerStore:
        def __init__(self) -> None:
            self.saved: dict[str, Any] | None = None

        def save_ledger(self, domain: str, entry_id: str, state: dict[str, Any]) -> None:
            self.saved = {"domain": domain, "entry_id": entry_id, **state}

    store = LedgerStore()
    computer = RewardComputer(rl_engine.SOCBinaryReward(), domain="soc")
    result = computer.compute("suppress", "suppress", {}, decision_id="D-1")
    entry_id = computer.persist(store, result)
    assert store.saved is not None
    assert store.saved["entry_id"] == entry_id
    assert store.saved["binary_reward"] == 1.0


def test_sdk_credit_assigner_handles_immediate_outcome() -> None:
    credits = CreditAssigner(temporal_discount=1.0).assign_temporal(1.0, [("D-1", 0)])
    assert len(credits) == 1
    assert credits[0].credit == 1.0


def test_sdk_exploration_policy_is_bounded_by_conservation() -> None:
    policy = ExplorationPolicy(n_actions=4, epsilon=0.125)
    policy.set_conservation_status("RED")
    decision = policy.select_action([0.1, 0.2, 0.3, 0.4])
    assert decision.epsilon == 0.0
    assert decision.conservation_status == "RED"


def test_fifty_binary_cycles_preserve_reward_invariant() -> None:
    computer = rl_engine.get_sdk_reward_computer()
    rewards = [computer.compute("suppress", "suppress", {}).reward for _ in range(50)]
    assert len(rewards) == 50
    assert all(reward == 1.0 for reward in rewards)


def test_rl_components_are_imported_from_sdk() -> None:
    source = _source("app/services/rl_engine.py")
    assert "from copilot_sdk.rl import" in source
    assert "SDKRewardComputer" in source
    assert "SDKCreditAssigner" in source
    assert "SDKExplorationPolicy" in source


def test_learning_service_uses_sdk_reward_computer() -> None:
    result = compute_soc_binary_reward(
        {"decision_id": "D-1", "recommended_action": "suppress"},
        {"actual_action": "suppress"},
    )
    assert result.domain == "soc"
    assert result.reward == 1.0


def test_triage_flow_contains_score_and_learning_boundaries() -> None:
    source = _source("app/routers/triage.py")
    assert "get_reward_computer" in source
    assert "update_posterior" in source
    assert "write_outcome" in source


def test_soc_tensor_shape_matches_frozen_contract() -> None:
    from app.domains.soc.config import SOCDomainConfig

    # SOC's frozen contract is six categories, four actions, six factors.
    assert SOCDomainConfig().get_initial_centroids().shape == (6, 4, 6)


def test_async_runtime_remains_available_for_live_health_checks() -> None:
    assert asyncio.iscoroutinefunction(__import__("app.main", fromlist=["health"]).health)
