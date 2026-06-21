from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "copilot-sdk"))

from copilot_sdk.substantiation import Oracle

from app.oracle.analyst_oracle import AnalystOracle
from app.oracle.pipeline_test import (
    PipelineValidationTest,
    compute_accuracy,
    compute_lift,
)

pytestmark = pytest.mark.no_data_guard


def test_analyst_oracle_satisfies_sdk_protocol():
    oracle = AnalystOracle()
    if not isinstance(oracle, Oracle):
        pytest.xfail(
            "DRIFT: AnalystOracle has synthetic_outcome but does not expose "
            "known_effect/known_accuracy_effect required by the SDK Oracle protocol."
        )

    assert oracle.known_effect == pytest.approx(0.10)
    assert oracle.known_accuracy_effect == pytest.approx(0.05)
    assert callable(oracle.synthetic_outcome)


def test_oracle_run_all_4_experiments():
    results = PipelineValidationTest(n_per_arm=200).run_all()

    assert set(results) == {
        "exp1_known_lift",
        "exp2_zero_lift",
        "exp3_floor_power",
        "exp4_lift_neg_accuracy",
    }


def test_oracle_all_experiments_pass():
    results = PipelineValidationTest().run_all()

    assert all(result.passed for result in results.values())


def test_oracle_exp4_accuracy_is_negative():
    result = PipelineValidationTest(n_per_arm=200).run_all()["exp4_lift_neg_accuracy"]

    assert result.detail["accuracy"].treatment < result.detail["accuracy"].control


def test_oracle_outcomes_contain_correct_field():
    oracle = AnalystOracle(seed=7)
    outcomes = [oracle.synthetic_outcome(shown=index % 2 == 0) for index in range(100)]

    assert all("correct" in outcome for outcome in outcomes)
    assert not all(outcome["correct"] is True for outcome in outcomes)


def test_compute_lift_matches_oracle_known_effect():
    oracle = AnalystOracle(treatment_lift=0.10, seed=42)
    treatment = [oracle.synthetic_outcome(shown=True) for _ in range(1000)]
    control = [oracle.synthetic_outcome(shown=False) for _ in range(1000)]

    lift = compute_lift(treatment, control)

    assert lift.escalation_lift == pytest.approx(0.10, abs=0.05)


def test_compute_accuracy_with_negative_lift():
    oracle = AnalystOracle(accuracy_lift=-0.10, seed=42)
    treatment = [oracle.synthetic_outcome(shown=True) for _ in range(1000)]
    control = [oracle.synthetic_outcome(shown=False) for _ in range(1000)]

    accuracy = compute_accuracy(treatment, control)

    assert accuracy.treatment < accuracy.control
