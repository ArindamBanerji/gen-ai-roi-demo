from __future__ import annotations

import pytest

from app.oracle import (
    AnalystOracle,
    PipelineValidationTest,
    compute_accuracy,
    compute_lift,
)

pytestmark = pytest.mark.no_data_guard


def test_oracle_deterministic() -> None:
    first = [AnalystOracle(seed=7).synthetic_outcome(shown=True) for _ in range(5)]
    second = [AnalystOracle(seed=7).synthetic_outcome(shown=True) for _ in range(5)]

    assert first == second


def test_oracle_treatment_has_higher_rate() -> None:
    oracle = AnalystOracle(treatment_lift=0.15, seed=42)
    treatment = [oracle.synthetic_outcome(shown=True) for _ in range(2_000)]
    control = [oracle.synthetic_outcome(shown=False) for _ in range(2_000)]

    assert compute_lift(treatment, control).escalation_lift > 0.10


def test_oracle_correct_is_modeled() -> None:
    oracle = AnalystOracle(base_accuracy=0.70, accuracy_lift=0.0, seed=42)
    outcomes = [oracle.synthetic_outcome(shown=True) for _ in range(200)]

    assert any(outcome["correct"] for outcome in outcomes)
    assert any(not outcome["correct"] for outcome in outcomes)


def test_oracle_outcome_fields() -> None:
    outcome = AnalystOracle(seed=42).synthetic_outcome(shown=True)

    assert set(outcome) == {
        "analyst_action",
        "was_override",
        "quality_signal",
        "correct",
    }
    assert isinstance(outcome["was_override"], bool)
    assert outcome["quality_signal"] in {0.0, 1.0}


def test_oracle_zero_lift() -> None:
    oracle = AnalystOracle(treatment_lift=0.0, seed=42)
    treatment = [oracle.synthetic_outcome(shown=True) for _ in range(3_000)]
    control = [oracle.synthetic_outcome(shown=False) for _ in range(3_000)]

    assert abs(compute_lift(treatment, control).escalation_lift) < 0.03


def test_exp1_known_lift_recovered() -> None:
    result = PipelineValidationTest(n_per_arm=1_000, seed=42)._exp1_known_lift()

    assert result.passed is True
    assert result.measured_lift == pytest.approx(0.10, abs=0.05)


def test_exp2_zero_lift_no_signal() -> None:
    result = PipelineValidationTest(n_per_arm=1_000, seed=42)._exp2_zero_lift()

    assert result.passed is True
    assert result.measured_lift == pytest.approx(0.0, abs=0.03)


def test_exp3_floor_power_computed() -> None:
    result = PipelineValidationTest()._exp3_floor_power()

    assert result.passed is True
    assert result.detail["n_per_arm_floor"] > 0
    assert "gaussian lower bound" in result.detail["caveat"]


def test_exp4_gate_rejects_neg_accuracy() -> None:
    result = PipelineValidationTest(n_per_arm=1_000, seed=42)._exp4_lift_neg_accuracy()

    assert result.passed is True
    assert result.detail["gate_correctly_rejected"] is True
    assert result.detail["accuracy"].treatment < result.detail["accuracy"].control


def test_run_all_4_experiments() -> None:
    results = PipelineValidationTest(n_per_arm=1_000, seed=42).run_all()

    assert set(results) == {
        "exp1_known_lift",
        "exp2_zero_lift",
        "exp3_floor_power",
        "exp4_lift_neg_accuracy",
    }
    assert all(result.passed for result in results.values())


def test_compute_lift_basic() -> None:
    treatment = [
        {"analyst_action": "escalate_tier2"},
        {"analyst_action": "dismiss"},
        {"analyst_action": "escalate_tier2"},
        {"analyst_action": "dismiss"},
    ]
    control = [
        {"analyst_action": "dismiss"},
        {"analyst_action": "dismiss"},
        {"analyst_action": "escalate_tier2"},
        {"analyst_action": "dismiss"},
    ]

    result = compute_lift(treatment, control)

    assert result.treatment_rate == 0.50
    assert result.control_rate == 0.25
    assert result.escalation_lift == 0.25


def test_compute_accuracy_basic() -> None:
    treatment = [{"correct": True}, {"correct": True}, {"correct": False}]
    control = [{"correct": True}, {"correct": False}, {"correct": False}]

    result = compute_accuracy(treatment, control)

    assert result.treatment == pytest.approx(2 / 3)
    assert result.control == pytest.approx(1 / 3)


def test_compute_lift_zero() -> None:
    treatment = [{"analyst_action": "escalate_tier2"}, {"analyst_action": "dismiss"}]
    control = [{"analyst_action": "escalate_tier2"}, {"analyst_action": "dismiss"}]

    assert compute_lift(treatment, control).escalation_lift == 0.0
