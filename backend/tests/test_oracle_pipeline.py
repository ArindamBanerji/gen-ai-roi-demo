from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from app.oracle.analyst_oracle import AnalystOracle


def run_oracle_experiment(oracle: AnalystOracle, n_per_arm: int = 200) -> dict[str, float | int]:
    """Run synthetic outcomes through treatment/control measurement arms."""
    treatment_outcomes = []
    control_outcomes = []

    for _ in range(n_per_arm):
        treatment_outcomes.append(oracle.synthetic_outcome(shown=True))
        control_outcomes.append(oracle.synthetic_outcome(shown=False))

    t_escalation = _escalation_rate(treatment_outcomes)
    c_escalation = _escalation_rate(control_outcomes)
    t_correct = _accuracy_rate(treatment_outcomes)
    c_correct = _accuracy_rate(control_outcomes)

    return {
        "lift": t_escalation - c_escalation,
        "accuracy_delta": t_correct - c_correct,
        "treatment_escalation": t_escalation,
        "control_escalation": c_escalation,
        "treatment_accuracy": t_correct,
        "control_accuracy": c_correct,
        "n_per_arm": n_per_arm,
    }


def test_exp1_positive_lift_recovery() -> None:
    oracle = AnalystOracle(treatment_lift=0.10, base_accuracy=0.70, accuracy_lift=0.05)

    result = run_oracle_experiment(oracle, n_per_arm=200)

    assert abs(float(result["lift"]) - oracle.known_effect) < 0.05


def test_exp2_null_effect_recovery() -> None:
    oracle = AnalystOracle(treatment_lift=0.0, base_accuracy=0.70, accuracy_lift=0.0)

    result = run_oracle_experiment(oracle, n_per_arm=200)

    assert abs(float(result["lift"])) < 0.03


def test_exp3_floor_power() -> None:
    """Gaussian lower-bound N per arm for 5pp lift at 80% power, alpha=0.05."""
    n_per_arm = floor_power_n_per_arm(p=0.5, effect=0.05, z_alpha=1.96, z_beta=0.84)
    expected_floor = 1568

    assert abs(n_per_arm - expected_floor) < 100, (
        f"Floor N={n_per_arm}, expected ~{expected_floor}"
    )
    print(f"Floor N per arm: {n_per_arm} (gaussian lower bound)")


def test_exp4_lift_positive_accuracy_negative_gate_rejects() -> None:
    oracle = AnalystOracle(treatment_lift=0.10, base_accuracy=0.70, accuracy_lift=-0.05)

    result = run_oracle_experiment(oracle, n_per_arm=200)
    gate_passes = float(result["lift"]) > 0 and float(result["accuracy_delta"]) >= 0

    assert float(result["lift"]) > 0.03
    assert float(result["accuracy_delta"]) < -0.02
    assert not gate_passes


def test_pipeline_results_artifact_shape(tmp_path: Path) -> None:
    results = build_scan3_results()
    artifact = tmp_path / "soc_oracle_plumb_results.json"

    artifact.write_text(json.dumps(results, indent=2), encoding="utf-8")
    loaded = json.loads(artifact.read_text(encoding="utf-8"))

    assert loaded["status"] == "CLOSED"
    assert len(loaded["experiments"]) == 4
    assert all(experiment["passed"] for experiment in loaded["experiments"])


def build_scan3_results() -> dict[str, Any]:
    exp1 = run_oracle_experiment(
        AnalystOracle(treatment_lift=0.10, base_accuracy=0.70, accuracy_lift=0.05),
        n_per_arm=200,
    )
    exp2 = run_oracle_experiment(
        AnalystOracle(treatment_lift=0.0, base_accuracy=0.70, accuracy_lift=0.0),
        n_per_arm=200,
    )
    exp4 = run_oracle_experiment(
        AnalystOracle(treatment_lift=0.10, base_accuracy=0.70, accuracy_lift=-0.05),
        n_per_arm=200,
    )
    exp4_gate_passes = float(exp4["lift"]) > 0 and float(exp4["accuracy_delta"]) >= 0
    floor_n = floor_power_n_per_arm(p=0.5, effect=0.05, z_alpha=1.96, z_beta=0.84)

    return {
        "status": "CLOSED",
        "analyst_oracle": {
            "known_effect": 0.10,
            "known_accuracy_effect": 0.05,
        },
        "experiments": [
            {
                "name": "exp1_positive_lift_recovery",
                "expected_lift": 0.10,
                "measured_lift": exp1["lift"],
                "passed": abs(float(exp1["lift"]) - 0.10) < 0.05,
                "detail": exp1,
            },
            {
                "name": "exp2_null_effect_recovery",
                "expected_lift": 0.0,
                "measured_lift": exp2["lift"],
                "passed": abs(float(exp2["lift"])) < 0.03,
                "detail": exp2,
            },
            {
                "name": "exp3_floor_power",
                "expected_lift": 0.05,
                "n_per_arm_floor": floor_n,
                "passed": floor_n > 0 and floor_n < 10_000,
                "detail": {"caveat": "gaussian lower bound; real N higher"},
            },
            {
                "name": "exp4_lift_positive_accuracy_negative_gate_rejects",
                "expected_lift": 0.10,
                "measured_lift": exp4["lift"],
                "accuracy_delta": exp4["accuracy_delta"],
                "gate": "REJECT" if not exp4_gate_passes else "PASS",
                "passed": not exp4_gate_passes,
                "detail": exp4,
            },
        ],
    }


def floor_power_n_per_arm(*, p: float, effect: float, z_alpha: float, z_beta: float) -> int:
    return math.ceil(2 * p * (1 - p) * ((z_alpha + z_beta) / effect) ** 2)


def _escalation_rate(outcomes: list[dict[str, Any]]) -> float:
    if not outcomes:
        raise ValueError("Empty outcome list - cannot compute escalation rate")
    return sum(1 for outcome in outcomes if _action(outcome) == "escalate_tier2") / len(outcomes)


def _accuracy_rate(outcomes: list[dict[str, Any]]) -> float:
    if not outcomes:
        raise ValueError("Empty outcome list - cannot compute accuracy rate")
    return sum(1 for outcome in outcomes if bool(outcome.get("correct", False))) / len(outcomes)


def _action(outcome: dict[str, Any]) -> str:
    return str(outcome.get("action") or outcome.get("analyst_action") or "")
