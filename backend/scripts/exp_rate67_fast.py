"""
EXP-RATE-67-FAST: NOVELTY MEASUREMENT + INJECTION (optimized)
================================================================
RATE-6: Does novelty correlate with DK improvement?
RATE-7: Does novelty injection restart the learning curve?

Key optimization: DK calibration capped at 400/category.
Prints each checkpoint as it completes.

Run: cd backend && python scripts/exp_rate67_fast.py
Time: ~15-20 min
"""

import sys
import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_MAX = 6000
N_TEST = 500
FREEZE_AT = 500
DK_INTERVAL = 500  # less frequent than 200 for speed
SEEDS_SHORT = [42, 123, 777]


def score_dk(fv, ci, centroids, weights):
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        sims.append(-np.sum(weights[ci, ai] * diff ** 2))
    return int(np.argmax(sims))


def estimate_dk_fast(decisions, centroids, n_rounds=5, max_per_cat=400):
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


def evaluate_dk(test_data, centroids, weights):
    return sum(1 for fv, ci, oa in test_data
               if score_dk(fv, ci, centroids, weights) == oa) / len(test_data) * 100


def novelty_dnn(fv, ci, oa, prior, max_look=300):
    same_ca = [f for f, c, a in prior[-max_look:] if c == ci and a == oa]
    if len(same_ca) == 0:
        return 1.0
    return min(np.linalg.norm(fv - f) for f in same_ca)


def novelty_zscore(fv, ci, oa, prior, max_look=300):
    same_ca = np.array([f for f, c, a in prior[-max_look:] if c == ci and a == oa])
    if len(same_ca) < 5:
        return 1.0
    mu = same_ca.mean(axis=0)
    sigma = same_ca.std(axis=0) + 1e-10
    return float(np.max(np.abs(fv - mu) / sigma))


def novelty_count(ci, oa, prior):
    n_ca = sum(1 for _, c, a in prior if c == ci and a == oa)
    return 1.0 / (1.0 + n_ca / 50.0)


def main():
    base_mu = get_base_centroids()

    # ════════════════════════════════════════════
    # RATE-6: NOVELTY vs DK IMPROVEMENT
    # ════════════════════════════════════════════
    print("=" * 80, flush=True)
    print("RATE-6: NOVELTY vs DK IMPROVEMENT", flush=True)
    print("=" * 80, flush=True)

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)

        scorer = make_scorer(base_mu.copy())
        all_decs = []
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
        frozen_mu = scorer.centroids.copy()

        rng_test = np.random.default_rng(seed + 50000)
        test_data = [(
            np.clip(rng_test.normal(0.5, 0.15, D), 0, 1).astype(np.float64),
            int(rng_test.choice(C, p=CATEGORY_WEIGHTS)),
            None  # placeholder
        ) for _ in range(N_TEST)]
        # Fix: need proper test data
        rng_test = np.random.default_rng(seed + 50000)
        test_data = []
        for _ in range(N_TEST):
            ci = int(rng_test.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_test.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng_test)
            test_data.append((fv, ci, oa))

        print(f"\nSeed {seed}:", flush=True)
        print(f"{'N':>6s}  {'DK':>6s}  {'DeltaP':>7s}  {'d_nn':>6s}  {'z_max':>6s}  {'1/Nca':>6s}", flush=True)
        print("-" * 45, flush=True)

        prev_acc = None
        window_data = []

        for cp in range(DK_INTERVAL, N_MAX + 1, DK_INTERVAL):
            print(f"  cal N={cp}...", end="", flush=True)
            w = estimate_dk_fast(all_decs[:cp], frozen_mu, n_rounds=5, max_per_cat=400)
            acc = evaluate_dk(test_data, frozen_mu, w)

            # Novelty for this window
            window = all_decs[cp - DK_INTERVAL:cp]
            prior = all_decs[:cp - DK_INTERVAL]
            sample = window[:50]

            dnns = [novelty_dnn(fv, ci, oa, prior) for fv, ci, oa in sample]
            zs = [novelty_zscore(fv, ci, oa, prior) for fv, ci, oa in sample]
            cnts = [novelty_count(ci, oa, prior) for fv, ci, oa in sample]

            delta = acc - prev_acc if prev_acc is not None else 0
            prev_acc = acc

            window_data.append({
                'cp': cp, 'delta': delta,
                'dnn': np.mean(dnns), 'z': np.mean(zs), 'cnt': np.mean(cnts)
            })

            print(f"\r{cp:>6d}  {acc:>4.1f}%  {delta:>+5.1f}pp  "
                  f"{np.mean(dnns):>5.3f}  {np.mean(zs):>5.2f}  {np.mean(cnts):>5.3f}", flush=True)

        # Correlations
        if len(window_data) > 3:
            ds = np.array([w['delta'] for w in window_data[1:]])
            for metric in ['dnn', 'z', 'cnt']:
                vals = np.array([w[metric] for w in window_data[1:]])
                if np.std(vals) > 0 and np.std(ds) > 0:
                    corr = np.corrcoef(vals, ds)[0, 1]
                    print(f"  corr({metric}, DeltaP) = {corr:+.3f}", flush=True)

    # ════════════════════════════════════════════
    # RATE-7: NOVELTY INJECTION
    # ════════════════════════════════════════════
    print(f"\n{'='*80}", flush=True)
    print("RATE-7: NOVELTY INJECTION", flush=True)
    print("Does shifting GT restart the DK learning curve?", flush=True)
    print("=" * 80, flush=True)

    SHIFT_MAG = 0.05
    SHIFT_POINTS = [2000, 4000]
    N_INJECT = 6000

    for seed in SEEDS_SHORT:
        gt_orig = build_gt(np.random.default_rng(seed), base_mu)

        # Condition A: no shifts
        rng_a = np.random.default_rng(seed)
        scorer_a = make_scorer(base_mu.copy())
        decs_a = []
        for n in range(1, N_INJECT + 1):
            ci = int(rng_a.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_a.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt_orig, ci, fv)
            oa = noise_realistic(ta, ci, rng_a)
            r = scorer_a.score(fv, ci)
            if n <= FREEZE_AT:
                scorer_a.update(fv, ci, r.action_index, r.action_index == oa, oa)
            decs_a.append((fv, ci, oa))
        fm_a = scorer_a.centroids.copy()

        # Condition B: shifts at 2000, 4000
        rng_b = np.random.default_rng(seed)
        scorer_b = make_scorer(base_mu.copy())
        decs_b = []
        gt_b = gt_orig.copy()
        for n in range(1, N_INJECT + 1):
            if n in SHIFT_POINTS:
                sr = np.random.default_rng(seed + n)
                sd = sr.normal(0, 1, gt_b.shape)
                gt_b = np.clip(gt_b + sd / np.linalg.norm(sd) * SHIFT_MAG, 0, 1)
            ci = int(rng_b.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_b.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt_b, ci, fv)
            oa = noise_realistic(ta, ci, rng_b)
            r = scorer_b.score(fv, ci)
            if n <= FREEZE_AT:
                scorer_b.update(fv, ci, r.action_index, r.action_index == oa, oa)
            decs_b.append((fv, ci, oa))
        fm_b = scorer_b.centroids.copy()

        # Test against original GT (Condition A) and final shifted GT (Condition B)
        rng_test = np.random.default_rng(seed + 50000)
        test_orig = []
        for _ in range(N_TEST):
            ci = int(rng_test.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_test.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt_orig, ci, fv)
            oa = noise_realistic(ta, ci, rng_test)
            test_orig.append((fv, ci, oa))

        rng_test2 = np.random.default_rng(seed + 50000)
        test_shifted = []
        for _ in range(N_TEST):
            ci = int(rng_test2.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_test2.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt_b, ci, fv)
            oa = noise_realistic(ta, ci, rng_test2)
            test_shifted.append((fv, ci, oa))

        print(f"\nSeed {seed}:", flush=True)
        print(f"{'N':>6s}  {'A(fix)':>7s}  {'B(shift)':>8s}  {'B-A':>6s}  {'Event':>8s}", flush=True)
        print("-" * 40, flush=True)

        for cp in range(DK_INTERVAL, N_INJECT + 1, DK_INTERVAL):
            print(f"  cal N={cp}...", end="", flush=True)
            w_a = estimate_dk_fast(decs_a[:cp], fm_a, n_rounds=4, max_per_cat=400)
            acc_a = evaluate_dk(test_orig, fm_a, w_a)

            w_b = estimate_dk_fast(decs_b[:cp], fm_b, n_rounds=4, max_per_cat=400)
            acc_b = evaluate_dk(test_shifted, fm_b, w_b)

            event = "SHIFT" if cp in SHIFT_POINTS else ""
            print(f"\r{cp:>6d}  {acc_a:>5.1f}%  {acc_b:>6.1f}%  {acc_b-acc_a:>+4.1f}pp  "
                  f"{event:>8s}", flush=True)

    print(f"\n{'='*80}", flush=True)
    print("BINARY QUESTIONS", flush=True)
    print("RATE-6: Any novelty metric corr > 0.30 with DeltaPerf?", flush=True)
    print("RATE-7: Condition B > Condition A at N=6000?", flush=True)
    print("RATE-7: d_nn spikes at shift points?", flush=True)
    print("\nDONE.", flush=True)


if __name__ == "__main__":
    main()
