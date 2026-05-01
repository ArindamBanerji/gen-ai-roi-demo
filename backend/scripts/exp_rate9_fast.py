"""
EXP-RATE-9-FAST: FRAMEWORK STRENGTHENING (optimized)
======================================================
H-MONO, H-FLOOR, H-CATCOMP, H-DEPLOY — with fast DK calibration.

Run: cd backend && python scripts/exp_rate9_fast.py
Time: ~15 min
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


def score_mixed(fv, ci, centroids, dk_weights, alpha):
    sims_dk, sims_cent = [], []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        sims_dk.append(-np.sum(dk_weights[ci, ai] * diff ** 2))
        sims_cent.append(-np.sum(diff ** 2))
    sims_dk = np.array(sims_dk, dtype=np.float64)
    sims_cent = np.array(sims_cent, dtype=np.float64)
    r_dk = sims_dk.max() - sims_dk.min()
    r_c = sims_cent.max() - sims_cent.min()
    sims_dk_n = (sims_dk - sims_dk.min()) / max(r_dk, 1e-10)
    sims_cent_n = (sims_cent - sims_cent.min()) / max(r_c, 1e-10)
    return int(np.argmax(alpha * sims_dk_n + (1 - alpha) * sims_cent_n))


def estimate_dk_fast(decisions, centroids, n_rounds=5, max_per_cat=400):
    by_cat = {ci: [] for ci in range(C)}
    for fv, ci_d, oa in decisions:
        by_cat[ci_d].append((fv, oa))
    weights = np.ones((C, A, D))
    for _ in range(n_rounds):
        for ci in range(C):
            cat_decs = by_cat[ci]
            if len(cat_decs) < 10:
                continue
            if len(cat_decs) > max_per_cat:
                rng_sub = np.random.default_rng(42 + ci + _)
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


def evaluate_dk(test_data, centroids, weights):
    return sum(1 for fv, ci, oa in test_data
               if score_dk(fv, ci, centroids, weights) == oa) / len(test_data) * 100


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
    checkpoints = [500, 1000, 2000, 3000, 4000, 6000, 8000]

    # ════════════════════════════════════════════════
    # RATE-9: H-MONO + H-FLOOR
    # ════════════════════════════════════════════════
    print("=" * 80, flush=True)
    print("RATE-9: H-MONO + H-FLOOR", flush=True)
    print("=" * 80, flush=True)

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        decs, frozen_mu = collect_and_freeze(gt, seed, N_MAX)
        test_data = make_test(gt, seed)

        cent_acc = evaluate_dk(test_data, frozen_mu, np.ones((C, A, D)))
        print(f"\nSeed {seed} (centroid: {cent_acc:.1f}%)", flush=True)
        print(f"{'N':>6s}  {'DK':>6s}  {'>=C?':>5s}  {'Mix.5':>6s}  {'Mix.7':>6s}  {'BestA':>5s}", flush=True)
        print("-" * 40, flush=True)

        below = 0
        for cp in checkpoints:
            print(f"  calibrating N={cp}...", end="", flush=True)
            w = estimate_dk_fast(decs[:cp], frozen_mu, n_rounds=5, max_per_cat=400)
            dk_acc = evaluate_dk(test_data, frozen_mu, w)
            above = dk_acc >= cent_acc - 0.01

            mix5 = sum(1 for fv, ci, oa in test_data
                       if score_mixed(fv, ci, frozen_mu, w, 0.5) == oa) / N_TEST * 100
            mix7 = sum(1 for fv, ci, oa in test_data
                       if score_mixed(fv, ci, frozen_mu, w, 0.7) == oa) / N_TEST * 100

            # Best alpha
            best_a, best_acc = 0, cent_acc
            for alpha in [0.0, 0.3, 0.5, 0.7, 0.9, 1.0]:
                a = sum(1 for fv, ci, oa in test_data
                        if score_mixed(fv, ci, frozen_mu, w, alpha) == oa) / N_TEST * 100
                if a > best_acc:
                    best_acc, best_a = a, alpha

            if not above:
                below += 1

            print(f"\r{cp:>6d}  {dk_acc:>4.1f}%  {'Y' if above else 'N':>5s}  "
                  f"{mix5:>4.1f}%  {mix7:>4.1f}%  {best_a:>4.1f}", flush=True)

        print(f"H-MONO: {below}/{len(checkpoints)} below centroid", flush=True)

    # ════════════════════════════════════════════════
    # RATE-10: H-CATCOMP
    # ════════════════════════════════════════════════
    print(f"\n{'='*80}", flush=True)
    print("RATE-10: H-CATCOMP", flush=True)
    print("=" * 80, flush=True)

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        decs, frozen_mu = collect_and_freeze(gt, seed, 4000)
        test_data = make_test(gt, seed)

        cat_counts = {ci: sum(1 for _, c, _ in decs if c == ci) for ci in range(C)}
        cent_cat = {}
        dk_cat = {}
        w = estimate_dk_fast(decs, frozen_mu, n_rounds=5, max_per_cat=400)

        for ci in range(C):
            ci_test = [(fv, c, oa) for fv, c, oa in test_data if c == ci]
            if len(ci_test) == 0:
                continue
            cent_cat[ci] = sum(1 for fv, c, oa in ci_test
                               if score_dk(fv, c, frozen_mu, np.ones((C, A, D))) == oa) / len(ci_test) * 100
            dk_cat[ci] = sum(1 for fv, c, oa in ci_test
                              if score_dk(fv, c, frozen_mu, w) == oa) / len(ci_test) * 100

        print(f"\nSeed {seed}:", flush=True)
        print(f"{'Category':>20s}  {'N_c':>5s}  {'Cent':>6s}  {'DK':>6s}  {'Delta':>7s}", flush=True)
        deltas, log_ns = [], []
        for ci in range(C):
            if ci in cent_cat:
                d = dk_cat[ci] - cent_cat[ci]
                ln = np.log(max(cat_counts[ci], 1))
                deltas.append(d)
                log_ns.append(ln)
                print(f"{CATEGORIES[ci]:>20s}  {cat_counts[ci]:>5d}  "
                      f"{cent_cat[ci]:>4.1f}%  {dk_cat[ci]:>4.1f}%  {d:>+5.1f}pp", flush=True)
        if len(deltas) > 2:
            corr = np.corrcoef(log_ns, deltas)[0, 1]
            print(f"corr(log(N_c), Delta): {corr:+.3f}", flush=True)

    # ════════════════════════════════════════════════
    # RATE-11: H-DEPLOY
    # ════════════════════════════════════════════════
    print(f"\n{'='*80}", flush=True)
    print("RATE-11: H-DEPLOY (full two-phase deployment)", flush=True)
    print("=" * 80, flush=True)

    deploy_cps = [500, 1000, 2000, 4000, 8000]

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        test_data = make_test(gt, seed)

        print(f"\nSeed {seed}:", flush=True)
        print(f"{'Strategy':>18s}", end="", flush=True)
        for n in deploy_cps:
            print(f"  {'N='+str(n):>7s}", end="")
        print(flush=True)
        print("-" * 60, flush=True)

        for strat in ["ALL_FROZEN", "SPLIT_CUMUL", "DK_FROM_START"]:
            rng = np.random.default_rng(seed)
            scorer = make_scorer(base_mu.copy())
            all_decs = []
            dk_w = np.ones((C, A, D))
            results = {}

            print(f"{strat:>18s}", end="", flush=True)

            for n in range(1, N_MAX + 1):
                ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                ta = true_action(gt, ci, fv)
                oa = noise_realistic(ta, ci, rng)
                result = scorer.score(fv, ci)
                if n <= FREEZE_AT:
                    scorer.update(fv, ci, result.action_index,
                                  result.action_index == oa, oa)
                all_decs.append((fv, ci, oa))

                if n in deploy_cps:
                    fm = scorer.centroids.copy()
                    if strat == "ALL_FROZEN":
                        acc = evaluate_dk(test_data, fm, np.ones((C, A, D)))
                    elif strat == "SPLIT_CUMUL":
                        if n > FREEZE_AT:
                            dk_w = estimate_dk_fast(all_decs, fm, n_rounds=5, max_per_cat=400)
                        acc = evaluate_dk(test_data, fm, dk_w)
                    elif strat == "DK_FROM_START":
                        dk_w = estimate_dk_fast(all_decs, fm, n_rounds=5, max_per_cat=400)
                        acc = evaluate_dk(test_data, fm, dk_w)
                    print(f"  {acc:>5.1f}%", end="", flush=True)

            print(flush=True)

    print(f"\n{'='*80}", flush=True)
    print("BINARY QUESTIONS", flush=True)
    print("H-MONO:    DK below centroid at any checkpoint?", flush=True)
    print("H-FLOOR:   Mix at 0.5 always >= centroid?", flush=True)
    print("H-CATCOMP: corr(log(N_c), Delta) > 0.3?", flush=True)
    print("H-DEPLOY:  SPLIT_CUMUL best at N=4000+?", flush=True)
    print("\nDONE.", flush=True)


if __name__ == "__main__":
    main()
