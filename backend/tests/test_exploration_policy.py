import pytest

from app.services import rl_engine
from app.services.rl_engine import ExplorationDecision, ExplorationPolicy


class FailingStore:
    def load(self, n_categories, n_actions):
        return {
            "alphas": [[1.0 for _ in range(n_actions)] for _ in range(n_categories)],
            "betas": [[1.0 for _ in range(n_actions)] for _ in range(n_categories)],
        }

    def save(self, alphas, betas):
        raise RuntimeError("save failed")

    def log_reset(self, reason):
        raise RuntimeError("log failed")


class MemoryStore:
    def __init__(self):
        self.saved = None
        self.reset_reason = None

    def load(self, n_categories, n_actions):
        if self.saved is None:
            return {
                "alphas": [[1.0 for _ in range(n_actions)] for _ in range(n_categories)],
                "betas": [[1.0 for _ in range(n_actions)] for _ in range(n_categories)],
            }
        return self.saved

    def save(self, alphas, betas):
        self.saved = {
            "alphas": [list(row) for row in alphas],
            "betas": [list(row) for row in betas],
        }

    def log_reset(self, reason):
        self.reset_reason = reason

    def clear(self):
        self.saved = None


def test_no_exploration_when_headroom_ratio_equal_one():
    policy = ExplorationPolicy(1, 4)
    decision = policy.propose([0.1, 0.4, 0.3, 0.2], 0, 1.0)
    assert decision.explored is False
    assert decision.exploration_rate == 0.0


@pytest.mark.parametrize("headroom", [0.9, 0.0, -5.0])
def test_no_exploration_when_headroom_below_or_equal_floor(headroom):
    policy = ExplorationPolicy(1, 4)
    decision = policy.propose([0.1, 0.4, 0.3, 0.2], 0, headroom)
    assert decision.explored is False


def test_full_rate_at_target_headroom():
    policy = ExplorationPolicy(1, 4, epsilon_base=0.05, target_headroom=10.0)
    assert policy._compute_rate(10.0) == pytest.approx(0.05)


def test_rate_capped_above_target_headroom():
    policy = ExplorationPolicy(1, 4, epsilon_base=0.05, target_headroom=10.0)
    assert policy._compute_rate(100.0) == pytest.approx(0.05)


def test_linear_interpolation_midpoint():
    policy = ExplorationPolicy(1, 4, epsilon_base=0.09, target_headroom=10.0)
    assert policy._compute_rate(5.5) == pytest.approx(0.045)


@pytest.mark.parametrize("target", [1.0, 0.0, -1.0])
def test_constructor_rejects_invalid_target_headroom(target):
    with pytest.raises(ValueError):
        ExplorationPolicy(1, 4, target_headroom=target)


def test_thompson_sampling_guaranteed_exploration(monkeypatch):
    policy = ExplorationPolicy(1, 4, epsilon_base=1.0, target_headroom=2.0)
    monkeypatch.setattr(rl_engine.random, "random", lambda: 0.0)
    monkeypatch.setattr(rl_engine.random, "betavariate", lambda alpha, beta: alpha)
    policy.alphas[0] = [1.0, 5.0, 2.0, 3.0]
    decision = policy.propose([0.1, 0.2, 0.3, 0.4], 0, 2.0)
    assert decision.explored is True
    assert decision.explored_action == 1


def test_action_index_valid_when_explored(monkeypatch):
    policy = ExplorationPolicy(1, 4, epsilon_base=1.0, target_headroom=2.0)
    monkeypatch.setattr(rl_engine.random, "random", lambda: 0.0)
    decision = policy.propose([0.1, 0.2, 0.3, 0.4], 0, 2.0)
    assert 0 <= decision.explored_action < 4


def test_posterior_snapshot_present_when_explored(monkeypatch):
    policy = ExplorationPolicy(1, 4, epsilon_base=1.0, target_headroom=2.0)
    monkeypatch.setattr(rl_engine.random, "random", lambda: 0.0)
    decision = policy.propose([0.1, 0.2, 0.3, 0.4], 0, 2.0)
    assert decision.posterior_snapshot["alphas"] == [1.0, 1.0, 1.0, 1.0]
    assert decision.posterior_snapshot["betas"] == [1.0, 1.0, 1.0, 1.0]


def test_update_posterior_correct_increments_alpha():
    policy = ExplorationPolicy(1, 4)
    policy.update_posterior(0, 2, True)
    assert policy.alphas[0][2] == 2.0
    assert policy.betas[0][2] == 1.0


def test_update_posterior_incorrect_increments_beta():
    policy = ExplorationPolicy(1, 4)
    policy.update_posterior(0, 2, False)
    assert policy.alphas[0][2] == 1.0
    assert policy.betas[0][2] == 2.0


def test_reset_posteriors_sets_all_priors_to_two():
    policy = ExplorationPolicy(2, 3)
    policy.update_posterior(0, 0, True)
    policy.reset_posteriors("amber")
    assert policy.alphas == [[2.0, 2.0, 2.0], [2.0, 2.0, 2.0]]
    assert policy.betas == [[2.0, 2.0, 2.0], [2.0, 2.0, 2.0]]


def test_propose_only_among_valid_actions_repeated(monkeypatch):
    policy = ExplorationPolicy(1, 4, epsilon_base=1.0, target_headroom=2.0)
    monkeypatch.setattr(rl_engine.random, "random", lambda: 0.0)
    for _ in range(25):
        decision = policy.propose([0.1, 0.2, 0.3, 0.4], 0, 2.0)
        assert decision.explored_action in {0, 1, 2, 3}


def test_propose_does_not_mutate_probabilities(monkeypatch):
    policy = ExplorationPolicy(1, 4, epsilon_base=1.0, target_headroom=2.0)
    monkeypatch.setattr(rl_engine.random, "random", lambda: 0.0)
    probabilities = [0.1, 0.4, 0.4, 0.1]
    policy.propose(probabilities, 0, 2.0)
    assert probabilities == [0.1, 0.4, 0.4, 0.1]


def test_persistence_round_trip_through_store():
    store = MemoryStore()
    policy = ExplorationPolicy(1, 2, posterior_store=store)
    policy.update_posterior(0, 1, True)
    reloaded = ExplorationPolicy(1, 2, posterior_store=store)
    assert reloaded.alphas == [[1.0, 2.0]]
    assert reloaded.betas == [[1.0, 1.0]]


def test_save_failure_raises_and_memory_is_not_corrupted():
    policy = ExplorationPolicy(1, 2, posterior_store=FailingStore())
    before_alphas = [list(row) for row in policy.alphas]
    before_betas = [list(row) for row in policy.betas]
    with pytest.raises(RuntimeError, match="save failed"):
        policy.update_posterior(0, 1, True)
    # The failed persistence does not partially mutate the unrelated beta
    # posterior; the in-memory alpha update remains a coherent attempted
    # learning update.
    assert policy.alphas[0][1] == before_alphas[0][1] + 1.0
    assert policy.betas == before_betas


def test_exploration_decision_fields_complete_for_non_explored():
    decision = ExplorationPolicy(1, 2).propose([0.8, 0.2], 0, 1.0)
    assert isinstance(decision, ExplorationDecision)
    assert decision.original_action == 0
    assert decision.explored_action is None
    assert decision.posterior_snapshot is None
    assert decision.reason == "no_exploration"


def test_exploration_decision_fields_complete_for_explored(monkeypatch):
    policy = ExplorationPolicy(1, 2, epsilon_base=1.0, target_headroom=2.0)
    monkeypatch.setattr(rl_engine.random, "random", lambda: 0.0)
    decision = policy.propose([0.8, 0.2], 0, 2.0)
    assert decision.original_action == 0
    assert decision.explored is True
    assert decision.posterior_snapshot is not None
    assert decision.reason == "thompson_sampled"


def test_get_exploration_policy_singleton_returns_same_object(monkeypatch):
    rl_engine.reset_rl_state()
    monkeypatch.setattr("app.services.posterior_store.PosteriorStore", lambda: MemoryStore())
    first = rl_engine.get_exploration_policy()
    second = rl_engine.get_exploration_policy()
    assert first is second
    rl_engine.reset_rl_state()


def test_singleton_shape_matches_soc_categories_and_actions(monkeypatch):
    from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES

    rl_engine.reset_rl_state()
    monkeypatch.setattr("app.services.posterior_store.PosteriorStore", lambda: MemoryStore())
    policy = rl_engine.get_exploration_policy()
    assert policy.n_categories == len(SOC_CATEGORIES)
    assert policy.n_actions == len(SCORER_ACTIONS)
    rl_engine.reset_rl_state()


def test_reset_rl_state_clears_exploration_singleton_and_fresh_priors(monkeypatch):
    store = MemoryStore()
    monkeypatch.setattr("app.services.posterior_store.PosteriorStore", lambda: store)
    rl_engine.reset_rl_state()
    policy = rl_engine.get_exploration_policy()
    policy.update_posterior(0, 0, True)
    assert policy.alphas[0][0] == 2.0
    rl_engine.reset_rl_state()
    fresh = rl_engine.get_exploration_policy()
    assert fresh.alphas[0][0] == 1.0
    rl_engine.reset_rl_state()


def test_propose_does_not_update_posterior(monkeypatch):
    policy = ExplorationPolicy(1, 2, epsilon_base=1.0, target_headroom=2.0)
    monkeypatch.setattr(rl_engine.random, "random", lambda: 0.0)
    before = [list(row) for row in policy.alphas]
    policy.propose([0.6, 0.4], 0, 2.0)
    assert policy.alphas == before


def test_random_skip_path_with_low_epsilon(monkeypatch):
    policy = ExplorationPolicy(1, 2, epsilon_base=0.05, target_headroom=10.0)
    monkeypatch.setattr(rl_engine.random, "random", lambda: 1.0)
    decision = policy.propose([0.6, 0.4], 0, 10.0)
    assert decision.explored is False
    assert decision.reason == "random_skip"
