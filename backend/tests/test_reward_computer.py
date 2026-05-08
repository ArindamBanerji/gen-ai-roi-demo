import json
from pathlib import Path

import pytest

from app.domains.soc.config import SOC_CATEGORIES
from app.services.rl_engine import RewardComputer, RewardResult


SOC_WEIGHTS = {
    "credential_access": {"base": 0.70},
    "lateral_movement": {"base": 0.80},
    "data_exfiltration": {"base": 0.90},
}

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_soc_correct_basic_reward():
    computer = RewardComputer("soc", SOC_WEIGHTS, penalty_ratio=20.0, reference_reward=0.5)
    result = computer.compute("escalate", "correct", "credential_access", {})
    assert result.graded_reward == 0.7
    assert result.binary_outcome is True


def test_soc_incorrect_basic_reward():
    computer = RewardComputer("soc", SOC_WEIGHTS, penalty_ratio=20.0, reference_reward=0.5)
    result = computer.compute("escalate", "incorrect", "credential_access", {})
    assert result.graded_reward == -14.0
    assert result.binary_outcome is False


def test_soc_campaign_correct_multiplier():
    computer = RewardComputer("soc", SOC_WEIGHTS, penalty_ratio=20.0, reference_reward=0.5)
    result = computer.compute("investigate", "correct", "lateral_movement", {"campaign_id": "CAMP-1"})
    assert result.graded_reward == 1.2
    assert result.breakdown["campaign_multiplier"] == 1.5


def test_soc_campaign_incorrect_amplified():
    computer = RewardComputer("soc", SOC_WEIGHTS, penalty_ratio=20.0, reference_reward=0.5)
    result = computer.compute("investigate", "incorrect", "lateral_movement", {"campaign_id": "CAMP-1"})
    assert result.graded_reward == -24.0


def test_unknown_category_default_severity():
    computer = RewardComputer("soc", SOC_WEIGHTS, penalty_ratio=20.0, reference_reward=0.5)
    result = computer.compute("monitor", "correct", "unknown_category", {})
    assert result.graded_reward == 0.5
    assert result.breakdown["severity"] == 0.5


def test_all_soc_categories_use_configured_severity_weights():
    weights_path = REPO_ROOT / "support" / "setup" / "soc_severity_weights.json"
    weights = json.loads(weights_path.read_text(encoding="utf-8"))
    assert set(weights) == set(SOC_CATEGORIES)

    computer = RewardComputer("soc", weights, penalty_ratio=20.0, reference_reward=0.5)
    for category in SOC_CATEGORIES:
        result = computer.compute("monitor", "correct", category, {})
        assert result.graded_reward == pytest.approx(weights[category]["base"])
        assert result.breakdown["severity"] == pytest.approx(weights[category]["base"])


def test_s2p_financial_impact_correct():
    weights = {"price_variance": {"reference": 45}}
    computer = RewardComputer("supply_chain", weights, penalty_ratio=20.0, reference_reward=0.3)
    result = computer.compute("approve", "correct", "price_variance", {"financial_impact": 22.5})
    assert result.graded_reward == 0.5
    assert result.breakdown["impact_weight"] == 0.5


def test_s2p_zero_impact():
    weights = {"price_variance": {"reference": 45}}
    computer = RewardComputer("s2p", weights, penalty_ratio=20.0, reference_reward=0.3)
    result = computer.compute("approve", "correct", "price_variance", {"financial_impact": 0})
    assert result.graded_reward == 0.0
    assert result.reward_weight == 0.1


def test_s2p_exception_cluster_multiplier():
    weights = {"price_variance": {"reference": 45}}
    computer = RewardComputer("s2p", weights, penalty_ratio=20.0, reference_reward=0.3)
    result = computer.compute(
        "reject",
        "incorrect",
        "price_variance",
        {"financial_impact": 45, "exception_cluster": True},
    )
    assert result.graded_reward == -26.0
    assert result.breakdown["cluster_multiplier"] == 1.3


def test_reward_weight_clip_boundaries():
    computer = RewardComputer("soc", {"low": {"base": 0.01}, "high": {"base": 10.0}}, reference_reward=0.5)
    low = computer.compute("monitor", "correct", "low", {})
    high = computer.compute("escalate", "correct", "high", {})
    assert low.reward_weight == 0.1
    assert high.reward_weight == 3.0


def test_binary_outcome_independent_of_severity():
    computer = RewardComputer("soc", {"high": {"base": 0.99}}, reference_reward=0.5)
    correct = computer.compute("escalate", "correct", "high", {})
    incorrect = computer.compute("escalate", "incorrect", "high", {})
    assert correct.binary_outcome is True
    assert incorrect.binary_outcome is False


def test_reference_reward_bootstrap_before_400():
    computer = RewardComputer("soc", {"x": {"base": 0.25}}, reference_reward=0.5)
    result = computer.compute("monitor", "correct", "x", {})
    assert result.reward_weight == 0.5


def test_reference_reward_rolling_median_after_400():
    computer = RewardComputer("soc", {"x": {"base": 1.0}}, reference_reward=0.5)
    computer._reward_history = [1.0] * 399 + [2.0]
    result = computer.compute("monitor", "correct", "x", {})
    assert result.reward_weight == 1.0


def test_breakdown_contains_expected_keys():
    computer = RewardComputer("soc", SOC_WEIGHTS, penalty_ratio=20.0, reference_reward=0.5)
    result = computer.compute("escalate", "correct", "credential_access", {"campaign_id": "CAMP-1"})
    assert {
        "category",
        "severity",
        "campaign_multiplier",
        "penalty_ratio",
        "formula",
        "action",
        "outcome",
    }.issubset(result.breakdown)


def test_unknown_domain_fallback():
    computer = RewardComputer("mystery", {}, penalty_ratio=20.0, reference_reward=1.0)
    result = computer.compute("act", "incorrect", "cat", {})
    assert result.graded_reward == -20.0
    assert result.breakdown["fallback"] is True


def test_reward_result_has_no_conservation_or_scorer_fields():
    result = RewardComputer("soc", SOC_WEIGHTS).compute("monitor", "correct", "credential_access", {})
    assert isinstance(result, RewardResult)
    assert not hasattr(result, "q")
    assert not hasattr(result, "conservation")
    assert not hasattr(result, "scorer")
    assert not hasattr(result, "learning_state")
