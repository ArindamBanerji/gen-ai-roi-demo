"""RL Phase 0 synthetic conservation-bounded bandit validation.

This script validates the planned MVP posterior shape: Beta posteriors per
(category, action) cell. The environment is therefore stationary per category,
not a continuous feature-dependent optimum.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import numpy as np


N_CATEGORIES = 3
N_ACTIONS = 4
N_STEPS = 5000
EPSILON_BASE = 0.05
TARGET_HEADROOM = 10.0
SEED = 42


SUCCESS_PROBS = np.array(
    [
        [0.82, 0.55, 0.42, 0.35],
        [0.44, 0.78, 0.50, 0.38],
        [0.36, 0.48, 0.80, 0.45],
    ],
    dtype=float,
)


def compute_exploration_rate(
    margin: float,
    epsilon_base: float = EPSILON_BASE,
    target_headroom: float = TARGET_HEADROOM,
) -> float:
    if margin <= 0:
        return 0.0
    return epsilon_base * min(margin / target_headroom, 1.0)


def margin_for_step(step: int) -> float:
    """Healthy -> disruption -> zero/near-zero -> recovery phases."""
    pct = step / N_STEPS
    if pct < 0.35:
        return 12.0
    if pct < 0.50:
        return 4.0
    if pct < 0.65:
        return 0.0
    if pct < 0.80:
        return -1.0
    return 9.0


@dataclass
class BanditResult:
    regret: float
    bound: float
    total_explored: int
    blocked_steps: int
    margin_nonpositive_explored: int
    posterior_best_rate: float
    margin_rate_correlation: float


def _argmax(values) -> int:
    return int(np.argmax(np.asarray(values, dtype=float)))


def run(seed: int = SEED, steps: int = N_STEPS) -> BanditResult:
    random.seed(seed)
    np.random.seed(seed)

    alphas = np.ones((N_CATEGORIES, N_ACTIONS), dtype=float)
    betas = np.ones((N_CATEGORIES, N_ACTIONS), dtype=float)
    true_best = np.argmax(SUCCESS_PROBS, axis=1)
    regret = 0.0
    total_explored = 0
    blocked_steps = 0
    margin_nonpositive_explored = 0
    margins: list[float] = []
    rates: list[float] = []

    for step in range(steps):
        category = step % N_CATEGORIES
        margin = margin_for_step(step)
        rate = compute_exploration_rate(margin)
        margins.append(margin)
        rates.append(rate)

        if margin <= 0 and rate != 0.0:
            raise AssertionError("exploration rate must be zero when margin <= 0")

        posterior_means = alphas[category] / (alphas[category] + betas[category])
        action = _argmax(posterior_means)

        explored_this_step = False
        if rate > 0 and random.random() < rate:
            samples = [
                random.betavariate(alphas[category, a], betas[category, a])
                for a in range(N_ACTIONS)
            ]
            action = _argmax(samples)
            explored_this_step = True
            total_explored += 1
        elif margin <= 0:
            blocked_steps += 1

        if margin <= 0 and explored_this_step:
            margin_nonpositive_explored += 1

        reward = 1 if random.random() < SUCCESS_PROBS[category, action] else 0
        alphas[category, action] += reward
        betas[category, action] += 1 - reward

        optimal_prob = SUCCESS_PROBS[category, true_best[category]]
        regret += float(optimal_prob - SUCCESS_PROBS[category, action])

    posterior_best = np.argmax(alphas / (alphas + betas), axis=1)
    posterior_best_rate = float(np.mean(posterior_best == true_best))
    positive = np.array([m > 0 for m in margins], dtype=bool)
    corr = float(np.corrcoef(np.array(margins)[positive], np.array(rates)[positive])[0, 1])
    bound = 2.5 * math.sqrt(steps)

    return BanditResult(
        regret=regret,
        bound=bound,
        total_explored=total_explored,
        blocked_steps=blocked_steps,
        margin_nonpositive_explored=margin_nonpositive_explored,
        posterior_best_rate=posterior_best_rate,
        margin_rate_correlation=corr,
    )


def validate(result: BanditResult) -> None:
    if result.regret > result.bound:
        raise AssertionError(
            f"cumulative regret {result.regret:.2f} exceeds bound {result.bound:.2f}"
        )
    if result.posterior_best_rate < 1.0:
        raise AssertionError(
            f"posterior did not rank every true best action first: {result.posterior_best_rate:.2%}"
        )
    if result.total_explored <= 0:
        raise AssertionError("expected at least one exploration")
    if result.margin_nonpositive_explored != 0:
        raise AssertionError(
            f"expected zero exploration during margin<=0, got {result.margin_nonpositive_explored}"
        )
    if result.blocked_steps <= 0:
        raise AssertionError("expected margin<=0 phases to block exploration")
    if result.margin_rate_correlation < 0.95:
        raise AssertionError(
            f"margin/rate correlation too low: {result.margin_rate_correlation:.4f}"
        )


def main() -> None:
    result = run()
    validate(result)
    print(f"Steps: {N_STEPS}")
    print(f"cumulative regret: {result.regret:.4f}")
    print(f"bound: {result.bound:.4f}")
    print(f"optimal selection / posterior best action rate: {result.posterior_best_rate:.2%}")
    print(f"total explored: {result.total_explored}")
    print(f"exploration count during margin <= 0: {result.margin_nonpositive_explored}")
    print(f"margin-rate correlation: {result.margin_rate_correlation:.4f}")
    print("ALL VALIDATIONS PASSED")


if __name__ == "__main__":
    main()
