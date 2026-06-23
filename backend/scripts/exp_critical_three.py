"""
EXP-CRITICAL: THREE FRAMEWORK-STRENGTHENING EXPERIMENTS
=========================================================
These three experiments address the most important gaps in the framework.
If they work, the framework becomes substantially more defensible.

1. DIRECT: Direct variance estimation vs coordinate descent
   (Is the mathematically correct estimator better than the heuristic?)

2. ALPHA: James-Stein alpha* computation from data
   (What is the OPTIMAL shrinkage intensity at each checkpoint?)

3. CONSERV: Conservation law behavior under DK learning
   (Does conservation fire spuriously during DK re-estimation?)

Run: cd backend && python scripts/exp_critical_three.py
Time: ~20-25 min
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
SEEDS_SHORT = [42, 123, 777]


def score_dk(fv, ci, centroids, weights):
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        sims.append(-np.sum(weights[ci, ai] * diff ** 2))
    return int(np.argmax(sims))


def score_shrunk(fv, ci, centroids, dk_weights, alpha):
    """Score with shrinkage: w_tilde = alpha*w_dk + (1-alpha)*1."""
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        w_tilde = alpha * dk_weights[ci, ai] + (1 - alpha) * 1.0
        sims.append(-np.sum(w_tilde * diff ** 2))
    return int(np.argmax(sims))


def evaluate(test_data, centroids, weights):
    return sum(1 for fv, ci, oa in test_data
               if score_dk(fv, ci, centroids, weights) == oa) / len(test_data) * 100


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


# ════════════════════════════════════════════════════
# ESTIMATOR 1: Coordinate descent (current method)
# ════════════════════════════════════════════════════

def estimate_dk_coord(decisions, centroids, n_rounds=5, max_per_cat=400):
    by_cat = {ci: [] for ci in range(C)}
    for fv, ci_d, oa in decisions:
        by_cat[ci_d].append((fv, oa))
    weights = np.ones((C, A, D))
    for r in range(n_rounds):
        for ci in range(C):
            cat_decs = by_cat[ci]
            if len(cat_decs) < 10:
                continue
            if len(cat_decs) > max_per_cat:
                rng_sub = np.random.default_rng(42 + ci + r)
                idx = rng_sub.choice(len(cat_decs), max_per_cat, replace=False)
                cat_decs = [cat_decs[i] for i in idx]
            for ai in range(A):
                for di in range(D):
                    best_w = weights[ci, ai, di]
                    best_acc = sum(1 for fv, oa in cat_decs
                                  if score_dk(fv, ci, centroids, weights) == oa) / len(cat_decs)
                    for w_trial in [0.1, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0]:
                        trial_w = weights.copy()
                        trial_w[ci, ai, di] = w_trial
                        trial_acc = sum(1 for fv, oa in cat_decs
                                        if score_dk(fv, ci, centroids, trial_w) == oa) / len(cat_decs)
                        if trial_acc > best_acc:
                            best_acc = trial_acc
                            best_w = w_trial
                    weights[ci, ai, di] = best_w
    return weights


# ════════════════════════════════════════════════════
# ESTIMATOR 2: Direct variance estimation (MLE)
# ════════════════════════════════════════════════════

def estimate_dk_direct(decisions, centroids, regularization=0.01):
    """
    Direct MLE: w_i = 1/sigma_hat^2_i

    For each (c, a, i):
      Collect decisions where category = c and observed_action = a
      Compute residuals r_i = f_i - mu_i(c, a)
      sigma_hat^2_i = mean(r_i^2) + regularization
      w_i = 1 / sigma_hat^2_i

    Then normalize: w[c,a,:] = w[c,a,:] / max(w[c,a,:])
    (consistent with existing DiagonalKernel normalization)
    """
    weights = np.ones((C, A, D))

    # Group decisions by (c, a)
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
            residuals = fvs - mu  # shape (N_ca, D)
            sigma2 = np.mean(residuals ** 2, axis=0) + regularization  # shape (D,)
            w = 1.0 / sigma2
            # Normalize to max=1 (consistent with DiagonalKernel)
            if w.max() > 0:
                w = w / w.max()
            weights[ci, ai] = w

    return weights


# ════════════════════════════════════════════════════
# ESTIMATOR 3: Direct with Ledoit-Wolf shrinkage
# ════════════════════════════════════════════════════

def estimate_dk_ledoit_wolf(decisions, centroids, target_variance=None):
    """
    Ledoit-Wolf shrinkage applied to per-dimension variance estimates.

    sigma_hat^2_shrunk = beta * target + (1 - beta) * sigma_hat^2

    where target = mean(sigma_hat^2) across dimensions (shrink toward average)
    and beta is the optimal Ledoit-Wolf intensity.
    """
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
            if key not in by_ca or len(by_ca[key]) < 10:
                continue
            fvs = np.array(by_ca[key])
            mu = centroids[ci, ai]
            residuals = fvs - mu
            n = len(fvs)

            # Sample variance per dimension
            sigma2 = np.mean(residuals ** 2, axis=0)  # shape (D,)

            # Target: grand mean variance (shrink toward uniform importance)
            target = np.mean(sigma2) * np.ones(D)

            # Ledoit-Wolf optimal shrinkage intensity
            # beta = sum of estimation variance / sum of squared deviation from target
            # Simplified: beta ~ p / (n * sum((sigma2 - target)^2 / target^2))
            r4 = np.mean(residuals ** 4, axis=0)  # fourth moment
            estimation_var = (r4 - sigma2 ** 2) / n  # variance of variance estimate
            sum_est_var = np.sum(estimation_var)
            sum_dev_sq = np.sum((sigma2 - target) ** 2)

            if sum_dev_sq > 0:
                beta = min(1.0, max(0.0, sum_est_var / sum_dev_sq))
            else:
                beta = 1.0  # no deviation from target, full shrinkage

            sigma2_shrunk = beta * target + (1 - beta) * sigma2
            sigma2_shrunk = np.maximum(sigma2_shrunk, 0.001)  # floor

            w = 1.0 / sigma2_shrunk
            if w.max() > 0:
                w = w / w.max()
            weights[ci, ai] = w

    return weights


def main():
    base_mu = get_base_centroids()
    checkpoints = [500, 1000, 2000, 3000, 4000, 6000, 8000]

    # ════════════════════════════════════════════════════
    # EXPERIMENT 1: DIRECT vs COORDINATE DESCENT
    # ════════════════════════════════════════════════════
    print("=" * 80, flush=True)
    print("EXP-DIRECT: Direct Variance vs Coordinate Descent vs Ledoit-Wolf", flush=True)
    print("=" * 80, flush=True)

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        decs, frozen_mu = collect_and_freeze(gt, seed, N_MAX)
        test_data = make_test(gt, seed)
        cent_acc = evaluate(test_data, frozen_mu, np.ones((C, A, D)))

        print(f"\nSeed {seed} (centroid: {cent_acc:.1f}%):", flush=True)
        print(f"{'N':>6s}  {'Coord':>6s}  {'Direct':>7s}  {'L-W':>6s}  "
              f"{'Shr.5C':>6s}  {'Shr.5D':>6s}  {'Shr.5L':>6s}  {'>=C?':>4s}", flush=True)
        print("-" * 55, flush=True)

        for cp in checkpoints:
            d = decs[:cp]
            print(f"  N={cp}...", end="", flush=True)

            # Coordinate descent
            w_coord = estimate_dk_coord(d, frozen_mu)
            acc_coord = evaluate(test_data, frozen_mu, w_coord)

            # Direct MLE
            w_direct = estimate_dk_direct(d, frozen_mu)
            acc_direct = evaluate(test_data, frozen_mu, w_direct)

            # Ledoit-Wolf
            w_lw = estimate_dk_ledoit_wolf(d, frozen_mu)
            acc_lw = evaluate(test_data, frozen_mu, w_lw)

            # Shrinkage at alpha=0.5 for each
            shr_coord = evaluate_shrunk(test_data, frozen_mu, w_coord, 0.5)
            shr_direct = evaluate_shrunk(test_data, frozen_mu, w_direct, 0.5)
            shr_lw = evaluate_shrunk(test_data, frozen_mu, w_lw, 0.5)

            above = min(shr_coord, shr_direct, shr_lw) >= cent_acc - 0.01

            print(f"\r{cp:>6d}  {acc_coord:>4.1f}%  {acc_direct:>5.1f}%  {acc_lw:>4.1f}%  "
                  f"{shr_coord:>4.1f}%  {shr_direct:>4.1f}%  {shr_lw:>4.1f}%  "
                  f"{'Y' if above else 'N':>4s}", flush=True)

        # Weight comparison at N=4000
        w_c = estimate_dk_coord(decs[:4000], frozen_mu)
        w_d = estimate_dk_direct(decs[:4000], frozen_mu)
        w_l = estimate_dk_ledoit_wolf(decs[:4000], frozen_mu)
        print(f"\n  Weight comparison at N=4000:", flush=True)
        print(f"  {'':>20s}  {'Coord':>6s}  {'Direct':>7s}  {'L-W':>7s}", flush=True)
        for ci in range(min(2, C)):
            for ai in range(min(2, A)):
                print(f"  c={CATEGORIES[ci][:12]:>12s} a={ACTIONS[ai][:4]:>4s}:", end="", flush=True)
                for di in range(D):
                    pass  # too verbose, just show summary stats
                print(f"  std={np.std(w_c[ci,ai]):.2f} {np.std(w_d[ci,ai]):.2f} "
                      f"{np.std(w_l[ci,ai]):.2f}", flush=True)

    # ════════════════════════════════════════════════════
    # EXPERIMENT 2: JAMES-STEIN α* COMPUTATION
    # ════════════════════════════════════════════════════
    print(f"\n{'='*80}", flush=True)
    print("EXP-ALPHA: James-Stein Optimal alpha* from Data", flush=True)
    print("=" * 80, flush=True)

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        decs, frozen_mu = collect_and_freeze(gt, seed, N_MAX)
        test_data = make_test(gt, seed)
        cent_acc = evaluate(test_data, frozen_mu, np.ones((C, A, D)))

        print(f"\nSeed {seed} (centroid: {cent_acc:.1f}%):", flush=True)
        print(f"{'N':>6s}  {'alpha*':>7s}  {'Acc@a*':>7s}  {'Acc@0.5':>7s}  "
              f"{'Acc@1.0':>7s}  {'a*>0.5?':>7s}", flush=True)
        print("-" * 50, flush=True)

        for cp in checkpoints:
            d = decs[:cp]
            print(f"  N={cp}...", end="", flush=True)

            # Bootstrap: estimate DK weights 10 times with resampled data
            n_boot = 10
            boot_weights = []
            for b in range(n_boot):
                rng_boot = np.random.default_rng(seed * 1000 + cp + b)
                indices = rng_boot.choice(len(d), len(d), replace=True)
                d_boot = [d[i] for i in indices]
                w_boot = estimate_dk_direct(d_boot, frozen_mu)
                boot_weights.append(w_boot.flatten())

            boot_weights = np.array(boot_weights)  # (n_boot, C*A*D)

            # Mean estimate and estimation variance
            w_mean = boot_weights.mean(axis=0)
            sigma2_w = boot_weights.var(axis=0).mean()  # mean estimation variance

            # Distance from uniform
            dist_from_uniform_sq = np.sum((w_mean - 1.0) ** 2)

            # James-Stein alpha*
            p = len(w_mean)  # 144
            if dist_from_uniform_sq > 0:
                alpha_star = max(0.0, 1.0 - (p * sigma2_w) / dist_from_uniform_sq)
            else:
                alpha_star = 0.0

            # Evaluate at alpha*, alpha=0.5, alpha=1.0
            w_dk = estimate_dk_direct(d, frozen_mu)
            acc_star = evaluate_shrunk(test_data, frozen_mu, w_dk, alpha_star)
            acc_05 = evaluate_shrunk(test_data, frozen_mu, w_dk, 0.5)
            acc_10 = evaluate_shrunk(test_data, frozen_mu, w_dk, 1.0)

            better = alpha_star > 0.5

            print(f"\r{cp:>6d}  {alpha_star:>6.3f}  {acc_star:>5.1f}%  {acc_05:>5.1f}%  "
                  f"{acc_10:>5.1f}%  {'YES' if better else 'no':>7s}", flush=True)

    # ════════════════════════════════════════════════════
    # EXPERIMENT 3: CONSERVATION UNDER DK LEARNING
    # ════════════════════════════════════════════════════
    print(f"\n{'='*80}", flush=True)
    print("EXP-CONSERV: Conservation Law Under DK Learning", flush=True)
    print("=" * 80, flush=True)

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        decs, frozen_mu = collect_and_freeze(gt, seed, N_MAX)
        test_data = make_test(gt, seed)

        # Compute V (fixed — means are frozen)
        gt_centroids = gt  # approximate
        V = np.sum((frozen_mu - gt_centroids) ** 2)

        # Conservation: alpha_q * q * V >= theta_min
        theta_min = 0.467
        alpha_q = 1.0  # simplification

        print(f"\nSeed {seed} (V={V:.4f}):", flush=True)
        print(f"{'N':>6s}  {'q(cent)':>7s}  {'q(shr)':>7s}  {'a*q*V_c':>8s}  "
              f"{'a*q*V_s':>8s}  {'theta':>6s}  {'Safe?':>5s}", flush=True)
        print("-" * 55, flush=True)

        # Rolling accuracy window
        rolling_window = 400
        correct_cent = []
        correct_shrunk = []

        # Simulate scoring with centroid vs shrunk DK
        rng_cons = np.random.default_rng(seed + 70000)
        for n in range(1, 2001):
            ci = int(rng_cons.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_cons.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng_cons)

            # Centroid scoring
            cent_pred = score_dk(fv, ci, frozen_mu, np.ones((C, A, D)))
            correct_cent.append(1 if cent_pred == oa else 0)

            # Shrunk DK scoring (re-estimate at intervals)
            if n <= FREEZE_AT:
                w_dk = np.ones((C, A, D))
            else:
                # Use DK from accumulated training data
                w_dk = estimate_dk_direct(decs[:n], frozen_mu)

            shrunk_pred = score_shrunk(fv, ci, frozen_mu, w_dk, 0.5)
            correct_shrunk.append(1 if shrunk_pred == oa else 0)

        # Compute rolling q at checkpoints
        for cp in [200, 400, 600, 800, 1000, 1500, 2000]:
            start = max(0, cp - rolling_window)
            q_cent = np.mean(correct_cent[start:cp])
            q_shrunk = np.mean(correct_shrunk[start:cp])

            cons_cent = alpha_q * q_cent * V
            cons_shrunk = alpha_q * q_shrunk * V

            safe_cent = cons_cent >= theta_min
            safe_shrunk = cons_shrunk >= theta_min

            print(f"{cp:>6d}  {q_cent:>5.3f}  {q_shrunk:>6.3f}  {cons_cent:>7.4f}  "
                  f"{cons_shrunk:>7.4f}  {theta_min:>5.3f}  "
                  f"{'Y' if safe_shrunk else 'N':>5s}", flush=True)

        # Summary
        q_final_cent = np.mean(correct_cent[-400:])
        q_final_shrunk = np.mean(correct_shrunk[-400:])
        print(f"  Final q: centroid={q_final_cent:.3f} shrunk={q_final_shrunk:.3f} "
              f"delta={q_final_shrunk-q_final_cent:+.3f}", flush=True)
        print(f"  Conservation: strengthened={q_final_shrunk >= q_final_cent}", flush=True)

    # ════════════════════════════════════════════════════
    # SUMMARY
    # ════════════════════════════════════════════════════
    print(f"\n{'='*80}", flush=True)
    print("BINARY QUESTIONS", flush=True)
    print("EXP-DIRECT:", flush=True)
    print("  Q1: Does direct estimation match or beat coordinate descent?", flush=True)
    print("  Q2: Does Ledoit-Wolf beat raw direct estimation?", flush=True)
    print("  Q3: Does shrinkage at 0.5 stay safe for ALL estimators?", flush=True)
    print("EXP-ALPHA:", flush=True)
    print("  Q4: Does alpha* increase monotonically with N?", flush=True)
    print("  Q5: Is alpha* > 0.5 at large N?", flush=True)
    print("  Q6: Does acc@alpha* beat acc@0.5?", flush=True)
    print("EXP-CONSERV:", flush=True)
    print("  Q7: Does conservation fire during normal DK learning?", flush=True)
    print("  Q8: Is q(shrunk) >= q(centroid) at all checkpoints?", flush=True)
    print("\nDONE.", flush=True)


if __name__ == "__main__":
    main()
