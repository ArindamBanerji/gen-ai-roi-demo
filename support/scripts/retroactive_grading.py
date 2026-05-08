"""Dry-run validation for RL graded reward compatibility.

The deployment gate uses a bounded graded-quality signal, not signed reward,
because signed rewards intentionally apply asymmetric penalties for economics.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from statistics import mean

import numpy as np


PASS_THRESHOLD = 0.95
WARNING_THRESHOLD = 0.90
DEFAULT_PENALTY_RATIO = 20.0


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_severity_weights() -> dict[str, dict[str, float]]:
    path = _repo_root() / "support" / "setup" / "soc_severity_weights.json"
    with path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return {
        str(category): {"base": float(values.get("base", 0.50))}
        for category, values in raw.items()
        if isinstance(values, dict)
    }


def _severity(category: str, severity_weights: dict[str, dict[str, float]]) -> float:
    return float(severity_weights.get(category, {}).get("base", 0.50))


def compute_graded_reward(
    outcome: bool,
    category: str,
    severity_weights: dict[str, dict[str, float]],
    penalty_ratio: float = DEFAULT_PENALTY_RATIO,
) -> float:
    severity = _severity(category, severity_weights)
    return severity if bool(outcome) else -float(penalty_ratio) * severity


def compute_graded_quality(
    outcome: bool,
    category: str,
    severity_weights: dict[str, dict[str, float]],
) -> float:
    return _severity(category, severity_weights) if bool(outcome) else 0.0


def rolling_accuracy(outcomes: list[bool], window: int = 400) -> list[float]:
    return rolling_mean([1.0 if outcome else 0.0 for outcome in outcomes], window=window)


def rolling_mean(values: list[float], window: int = 400) -> list[float]:
    if not values:
        return []
    result: list[float] = []
    for index in range(len(values)):
        start = max(0, index + 1 - window)
        result.append(float(mean(values[start:index + 1])))
    return result


def correlation_after_warmup(a: list[float], b: list[float], warmup: int = 400) -> float:
    if len(a) != len(b):
        raise ValueError("series lengths must match")
    if len(a) < 2:
        return 1.0
    start = min(int(warmup), max(0, len(a) - 2))
    a_arr = np.asarray(a[start:], dtype=float)
    b_arr = np.asarray(b[start:], dtype=float)
    if a_arr.size < 2 or float(np.std(a_arr)) == 0.0 or float(np.std(b_arr)) == 0.0:
        return 1.0 if np.allclose(a_arr, b_arr) else 0.0
    return float(np.corrcoef(a_arr, b_arr)[0, 1])


def run_validation(decisions: int = 4860, seed: int = 42) -> dict:
    rng = random.Random(seed)
    weights = load_severity_weights()
    categories = list(weights) or ["credential_access"]

    outcomes: list[bool] = []
    categories_seen: list[str] = []
    signed_rewards: list[float] = []
    quality_values: list[float] = []
    max_severity = max((_severity(category, weights) for category in categories), default=1.0)

    for index in range(int(decisions)):
        category = categories[index % len(categories)]
        base_accuracy = 0.74 + 0.08 * ((index // max(1, len(categories))) % 5) / 4.0
        outcome = rng.random() < base_accuracy
        categories_seen.append(category)
        outcomes.append(outcome)
        signed_rewards.append(compute_graded_reward(outcome, category, weights))
        quality_values.append(compute_graded_quality(outcome, category, weights) / max_severity)

    binary_q = rolling_accuracy(outcomes)
    graded_quality = rolling_mean(quality_values)
    signed_reward_mean = rolling_mean(signed_rewards)

    quality_correlation = correlation_after_warmup(graded_quality, binary_q)
    signed_correlation = correlation_after_warmup(signed_reward_mean, binary_q)
    if quality_correlation >= PASS_THRESHOLD:
        tier = "PASS"
    elif quality_correlation >= WARNING_THRESHOLD:
        tier = "WARNING"
    else:
        tier = "FAIL"

    return {
        "decisions": int(decisions),
        "category_count": len(set(categories_seen)),
        "accuracy": sum(1 for outcome in outcomes if outcome) / len(outcomes) if outcomes else 0.0,
        "binary_quality_correlation": quality_correlation,
        "signed_reward_correlation": signed_correlation,
        "tier": tier,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dry-run RL retroactive grading validation")
    parser.add_argument("--decisions", type=int, default=4860)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    result = run_validation(decisions=args.decisions, seed=args.seed)
    print(f"decisions: {result['decisions']}")
    print(f"category count: {result['category_count']}")
    print(f"accuracy: {result['accuracy']:.4f}")
    print(f"binary_q/graded_quality correlation: {result['binary_quality_correlation']:.4f}")
    print(f"signed_reward correlation: {result['signed_reward_correlation']:.4f}")
    print(f"tier: {result['tier']}")
    if result["tier"] == "FAIL":
        return 1
    if result["tier"] == "PASS":
        print("ALL VALIDATIONS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
