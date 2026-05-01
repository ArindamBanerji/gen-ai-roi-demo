"""
EXP-SMOOTH-MONO: Does Direct Estimation Fix Monotonicity?
============================================================
RATE-1 showed coordinate descent oscillates badly (seed 777: -2.4pp
at N=16000). If the oscillation is caused by the ESTIMATOR (coordinate
descent finding different local optima) rather than the DATA, then
switching to direct variance estimation should produce a smooth,
monotonically improving learning curve.

This is the most important experiment for the framework:
if direct estimation IS monotonic, H-MONO holds and the "each
decision makes the GAE smarter" claim becomes substantially stronger.

Run: cd backend && python scripts/exp_smooth_mono.py
Time: ~10 min
"""

import sys
import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_MAX = 8000
N_TEST = 500
FREEZE_AT = 500
DK_INTERVAL = 200
SEEDS_SHORT = [42, 123, 777]


def score_shrunk(fv, ci, centroids, dk_weights, alpha):
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        w_tilde = alpha * dk_weights[ci, ai] + (1 - alpha) * 1.0
        sims.append(-np.sum(w_tilde * diff ** 2))
    return int(np.argmax(sims))


def estimate_dk_direct(decisions, centroids, regularization=0.01):
    """Direct MLE: w_i = 1/sigma_hat^2_i, normalized to max=1."""
    weights = np.ones((C, A, D))
    by_ca = {}
    for fv, ci, oa in decisions:
        key = (ci, oa)
        if key not in by_ca:
            by_ca[key] = []
        by_ca[key].append(fv)
    for ci in range(C):
        for ai in range(A):
            key = (ci, ai)
            if key not in by_ca or len(by_ca[key]) < 5:
                continue
            fvs = np.array(by_ca[key])
            mu = centroids[ci, ai]
            residuals = fvs - mu
            sigma2 = np.mean(residuals ** 2, axis=0) + regularization
            w = 1.0 / sigma2
            if w.max() > 0:
                w = w / w.max()
            weights[ci, ai] = w
    return weights


def evaluate_shrunk(test_data, centroids, dk_weights, alpha):
    return sum(1 for fv, ci, oa in test_data
               if score_shrunk(fv, ci, centroids, dk_weights, alpha) == oa) / len(test_data) * 100


def collect_and_freeze(gt, seed, N):
    rng = np.random.default_rng(seed)
    scorer = make_scorer(get_base_centroids().copy())
    decs = []
    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        result = scorer.score(fv, ci)
        if n <= FREEZE_AT:
            scorer.update(fv, ci, result.action_index, result.action_index == oa, oa)
        decs.append((fv, ci, oa))
    return decs, scorer.centroids.copy()


def make_test(gt, seed):
    rng = np.random.default_rng(seed + 50000)
    test = []
    for _ in range(N_TEST):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        test.append((fv, ci, oa))
    return test


def main():
    base_mu = get_base_centroids()

    print("=" * 80, flush=True)
    print("EXP-SMOOTH-MONO: Monotonicity Under Direct Estimation", flush=True)
    print("Every 200 decisions, N=8000, 3 seeds", flush=True)
    print("=" * 80, flush=True)

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        decs, frozen_mu = collect_and_freeze(gt, seed, N_MAX)
        test_data = make_test(gt, seed)

        cent_acc = sum(1 for fv, ci, oa in test_data
                       if score_shrunk(fv, ci, frozen_mu, np.ones((C, A, D)), 0.0) == oa
                       ) / N_TEST * 100

        print(f"\nSeed {seed} (centroid: {cent_acc:.1f}%):", flush=True)
        print(f"{'N':>6s}  {'Pure DK':>7s}  {'Shr.3':>6s}  {'Shr.5':>6s}  "
              f"{'Shr.7':>6s}  {'>=C(.5)?':>8s}  {'mono(.5)?':>9s}", flush=True)
        print("-" * 60, flush=True)

        prev_shr5 = cent_acc
        below_cent = 0
        non_mono = 0
        total = 0

        for cp in range(DK_INTERVAL, N_MAX + 1, DK_INTERVAL):
            w_dk = estimate_dk_direct(decs[:cp], frozen_mu)

            pure_dk = evaluate_shrunk(test_data, frozen_mu, w_dk, 1.0)
            shr3 = evaluate_shrunk(test_data, frozen_mu, w_dk, 0.3)
            shr5 = evaluate_shrunk(test_data, frozen_mu, w_dk, 0.5)
            shr7 = evaluate_shrunk(test_data, frozen_mu, w_dk, 0.7)

            above_cent = shr5 >= cent_acc - 0.01
            mono = shr5 >= prev_shr5 - 0.01

            if not above_cent:
                below_cent += 1
            if not mono and total > 0:
                non_mono += 1
            total += 1

            if cp % 1000 == 0 or not above_cent or not mono:
                print(f"{cp:>6d}  {pure_dk:>5.1f}%  {shr3:>4.1f}%  {shr5:>4.1f}%  "
                      f"{shr7:>4.1f}%  {'Y' if above_cent else 'N':>8s}  "
                      f"{'Y' if mono else 'DIP':>9s}", flush=True)

            prev_shr5 = shr5

        print(f"\n  SUMMARY:", flush=True)
        print(f"  Below centroid (shr@0.5): {below_cent}/{total} "
              f"({below_cent/max(total,1)*100:.0f}%)", flush=True)
        print(f"  Non-monotonic (shr@0.5):  {non_mono}/{total-1} "
              f"({non_mono/max(total-1,1)*100:.0f}%)", flush=True)

    print(f"\n{'='*80}", flush=True)
    print("BINARY QUESTIONS", flush=True)
    print("Q1: Below-centroid rate < 5% for all seeds? (H-MONO under direct)", flush=True)
    print("Q2: Non-monotonic rate < 15%? (smoother than coordinate descent?)", flush=True)
    print("Q3: Direct+shrinkage more stable than coord+shrinkage (RATE-9)?", flush=True)
    print("\nDONE.", flush=True)


if __name__ == "__main__":
    main()
