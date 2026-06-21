from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from statistics import NormalDist
from typing import Any, Sequence

from app.oracle.analyst_oracle import AnalystOracle


@dataclass(frozen=True)
class LiftResult:
    treatment_rate: float
    control_rate: float
    escalation_lift: float


@dataclass(frozen=True)
class AccuracyResult:
    treatment: float
    control: float


@dataclass(frozen=True)
class ExperimentResult:
    name: str
    expected_lift: float
    measured_lift: float
    passed: bool
    detail: Any


class PipelineValidationTest:
    """Run oracle through the measurement pipeline.

    4 experiments, each with a known ground truth:
    1. Known positive lift -> pipeline recovers it
    2. Zero lift -> pipeline reports no signal
    3. Floor power analysis -> minimum N for detection
    4. Positive lift + negative accuracy -> gate rejects
    """

    def __init__(self, n_per_arm: int = 500, seed: int = 42) -> None:
        self._n = int(n_per_arm)
        self._seed = seed

    def run_all(self) -> dict[str, ExperimentResult]:
        return {
            "exp1_known_lift": self._exp1_known_lift(),
            "exp2_zero_lift": self._exp2_zero_lift(),
            "exp3_floor_power": self._exp3_floor_power(),
            "exp4_lift_neg_accuracy": self._exp4_lift_neg_accuracy(),
        }

    def _exp1_known_lift(self) -> ExperimentResult:
        """Oracle: lift=0.10. Pipeline must recover about 0.10."""
        oracle = AnalystOracle(treatment_lift=0.10, seed=self._seed)
        treatment, control = _sample_arms(oracle, self._n)
        lift = compute_lift(treatment, control)
        return ExperimentResult(
            name="known_lift",
            expected_lift=0.10,
            measured_lift=lift.escalation_lift,
            passed=abs(lift.escalation_lift - 0.10) < 0.05,
            detail=lift,
        )

    def _exp2_zero_lift(self) -> ExperimentResult:
        """Oracle: lift=0.0. Pipeline should report about 0.0."""
        oracle = AnalystOracle(treatment_lift=0.0, seed=self._seed)
        treatment, control = _sample_arms(oracle, self._n)
        lift = compute_lift(treatment, control)
        return ExperimentResult(
            name="zero_lift",
            expected_lift=0.0,
            measured_lift=lift.escalation_lift,
            passed=abs(lift.escalation_lift) < 0.03,
            detail=lift,
        )

    def _exp3_floor_power(self) -> ExperimentResult:
        """Minimum N to detect 5pp lift with gaussian noise.

        This is a FLOOR -- real N is higher due to overdispersion.
        """
        z_alpha = NormalDist().inv_cdf(0.975)
        z_beta = NormalDist().inv_cdf(0.80)
        p = 0.30
        delta = 0.05
        n_floor = ceil(((z_alpha + z_beta) ** 2 * 2 * p * (1 - p)) / (delta**2))
        return ExperimentResult(
            name="floor_power",
            expected_lift=0.05,
            measured_lift=0.0,
            passed=True,
            detail={
                "n_per_arm_floor": n_floor,
                "caveat": "gaussian lower bound; real N higher",
            },
        )

    def _exp4_lift_neg_accuracy(self) -> ExperimentResult:
        """Oracle: +lift but NEGATIVE accuracy effect.

        The decision gate must REJECT: positive lift is useless
        if treatment makes analysts LESS accurate.
        """
        oracle = AnalystOracle(
            treatment_lift=0.10,
            accuracy_lift=-0.10,
            seed=self._seed,
        )
        treatment, control = _sample_arms(oracle, self._n)
        lift = compute_lift(treatment, control)
        accuracy = compute_accuracy(treatment, control)
        gate_pass = lift.escalation_lift > 0 and accuracy.treatment >= accuracy.control
        return ExperimentResult(
            name="lift_neg_accuracy",
            expected_lift=0.10,
            measured_lift=lift.escalation_lift,
            passed=not gate_pass,
            detail={
                "lift": lift,
                "accuracy": accuracy,
                "gate_correctly_rejected": not gate_pass,
            },
        )


def compute_lift(treatment: Sequence[dict], control: Sequence[dict]) -> LiftResult:
    """Treatment escalation rate minus control."""
    _validate_nonempty_arms(treatment, control)
    t_rate = sum(1 for o in treatment if o["analyst_action"] == "escalate_tier2") / len(treatment)
    c_rate = sum(1 for o in control if o["analyst_action"] == "escalate_tier2") / len(control)
    return LiftResult(
        treatment_rate=t_rate,
        control_rate=c_rate,
        escalation_lift=t_rate - c_rate,
    )


def compute_accuracy(treatment: Sequence[dict], control: Sequence[dict]) -> AccuracyResult:
    """Treatment accuracy vs control accuracy."""
    _validate_nonempty_arms(treatment, control)
    t_acc = sum(1 for o in treatment if o["correct"]) / len(treatment)
    c_acc = sum(1 for o in control if o["correct"]) / len(control)
    return AccuracyResult(treatment=t_acc, control=c_acc)


def _sample_arms(oracle: AnalystOracle, n: int) -> tuple[list[dict], list[dict]]:
    treatment = [oracle.synthetic_outcome(shown=True) for _ in range(n)]
    control = [oracle.synthetic_outcome(shown=False) for _ in range(n)]
    return treatment, control


def _validate_nonempty_arms(treatment: Sequence[dict], control: Sequence[dict]) -> None:
    if not treatment or not control:
        raise ValueError("treatment and control arms must be non-empty")
