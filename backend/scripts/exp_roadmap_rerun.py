"""
EXP-ROADMAP-RERUN: Roadmap experiments with COORDINATE DESCENT
================================================================
The direct estimation versions were invalid. Re-run with coord descent.
Uses subsampled coord descent (max_per_cat=400) for speed.

Run: cd backend && python scripts/exp_roadmap_rerun.py
Time: ~20-25 min
"""

import sys
import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS, ADJACENT,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

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
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        w_tilde = alpha * dk_weights[ci, ai] + (1 - alpha) * 1.0
        sims.append(-np.sum(w_tilde * diff ** 2))
    return int(np.argmax(sims))


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


def eval_shrunk(test_data, centroids, dk_w, alpha):
    return sum(1 for fv, ci, oa in test_data
               if score_shrunk(fv, ci, centroids, dk_w, alpha) == oa) / len(test_data) * 100


def eval_pure(test_data, centroids, weights):
    return sum(1 for fv, ci, oa in test_data
               if score_dk(fv, ci, centroids, weights) == oa) / len(test_data) * 100


def collect_freeze(gt, seed, N, sigma=0.15):
    rng = np.random.default_rng(seed)
    scorer = make_scorer(get_base_centroids().copy())
    decs = []
    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, sigma, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        r = scorer.score(fv, ci)
        if n <= FREEZE_AT:
            scorer.update(fv, ci, r.action_index, r.action_index == oa, oa)
        decs.append((fv, ci, oa))
    return decs, scorer.centroids.copy()


def make_test(gt, seed, sigma=0.15):
    rng = np.random.default_rng(seed + 50000)
    test = []
    for _ in range(N_TEST):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, sigma, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        test.append((fv, ci, oa))
    return test


def novelty_dnn(fv, ci, oa, prior, max_look=300):
    same_ca = [f for f, c, a in prior[-max_look:] if c == ci and a == oa]
    if len(same_ca) == 0:
        return 1.0
    return min(np.linalg.norm(fv - f) for f in same_ca)


def main():
    base_mu = get_base_centroids()

    # ════════════════════════════════════════
    # 1. NOVELTY-LARGE: Larger GT shifts
    # ════════════════════════════════════════
    print("=" * 80, flush=True)
    print("1. NOVELTY-LARGE (coord descent): shifts at delta=0.05-0.25", flush=True)
    print("=" * 80, flush=True)

    N_INJ = 6000
    SHIFT_AT = [2000, 4000]

    for delta in [0.05, 0.10, 0.15, 0.25]:
        accs_a, accs_b = [], []
        for seed in SEEDS_SHORT:
            gt_orig = build_gt(np.random.default_rng(seed), base_mu)

            # A: no shift
            print(f"  delta={delta:.2f} seed={seed} A...", end="", flush=True)
            decs_a, fm_a = collect_freeze(gt_orig, seed, N_INJ)
            test_a = make_test(gt_orig, seed)
            w_a = estimate_dk_coord(decs_a, fm_a)
            acc_a = eval_shrunk(test_a, fm_a, w_a, 0.5)

            # B: with shifts
            print(f" B...", end="", flush=True)
            rng_b = np.random.default_rng(seed)
            scorer_b = make_scorer(base_mu.copy())
            decs_b = []
            gt_b = gt_orig.copy()
            for n in range(1, N_INJ + 1):
                if n in SHIFT_AT:
                    sr = np.random.default_rng(seed + n)
                    sd = sr.normal(0, 1, gt_b.shape)
                    gt_b = np.clip(gt_b + sd / np.linalg.norm(sd) * delta, 0, 1)
                ci = int(rng_b.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng_b.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                ta = true_action(gt_b, ci, fv)
                oa = noise_realistic(ta, ci, rng_b)
                r = scorer_b.score(fv, ci)
                if n <= FREEZE_AT:
                    scorer_b.update(fv, ci, r.action_index, r.action_index == oa, oa)
                decs_b.append((fv, ci, oa))
            fm_b = scorer_b.centroids.copy()
            test_b = make_test(gt_b, seed)
            w_b = estimate_dk_coord(decs_b, fm_b)
            acc_b = eval_shrunk(test_b, fm_b, w_b, 0.5)

            accs_a.append(acc_a)
            accs_b.append(acc_b)
            print(f" done", flush=True)

        print(f"  delta={delta:.2f}: A(fixed)={np.mean(accs_a):.1f}%  "
              f"B(shift)={np.mean(accs_b):.1f}%  "
              f"B-A={np.mean(accs_b)-np.mean(accs_a):+.1f}pp", flush=True)

    # ════════════════════════════════════════
    # 2. DK-NOISE: DK at 4 noise levels
    # ════════════════════════════════════════
    print(f"\n{'='*80}", flush=True)
    print("2. DK-NOISE (coord descent): 4 oracle noise levels", flush=True)
    print("=" * 80, flush=True)

    for noise_mult in [0.33, 1.0, 1.67, 3.33]:
        label = f"{noise_mult*15:.0f}%"
        results = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            rng = np.random.default_rng(seed)
            scorer = make_scorer(base_mu.copy())
            decs = []

            print(f"  noise~{label} seed={seed}...", end="", flush=True)
            for n in range(1, 4001):
                ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                ta = true_action(gt, ci, fv)
                base_rate = {0: 0.08, 1: 0.12, 2: 0.15, 3: 0.18, 4: 0.22, 5: 0.22}[ci]
                adj_rate = min(base_rate * noise_mult, 0.90)
                if rng.random() < adj_rate:
                    nbrs = ADJACENT.get(ta, [])
                    oa = int(rng.choice(nbrs)) if nbrs else int(rng.choice([a for a in range(4) if a != ta]))
                else:
                    oa = ta
                r = scorer.score(fv, ci)
                if n <= FREEZE_AT:
                    scorer.update(fv, ci, r.action_index, r.action_index == oa, oa)
                decs.append((fv, ci, oa))

            fm = scorer.centroids.copy()
            test = make_test(gt, seed)
            cent_acc = eval_pure(test, fm, np.ones((C, A, D)))
            w = estimate_dk_coord(decs, fm)
            dk_acc = eval_shrunk(test, fm, w, 0.5)
            results.append((cent_acc, dk_acc))
            print(f" done", flush=True)

        mc = np.mean([r[0] for r in results])
        md = np.mean([r[1] for r in results])
        print(f"  noise~{label:>4s}: cent={mc:.1f}%  DK@0.5={md:.1f}%  "
              f"gain={md-mc:+.1f}pp", flush=True)

    # ════════════════════════════════════════
    # 3. WINDOW-1: Accumulation vs window under shift
    # ════════════════════════════════════════
    print(f"\n{'='*80}", flush=True)
    print("3. WINDOW-1 (coord descent): accumulation vs window under shift", flush=True)
    print("=" * 80, flush=True)

    N_WIN = 6000
    SHIFT_N = 3000
    SHIFT_DELTA = 0.15

    for seed in SEEDS_SHORT:
        gt_orig = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)
        scorer = make_scorer(base_mu.copy())
        decs = []
        gt_curr = gt_orig.copy()

        for n in range(1, N_WIN + 1):
            if n == SHIFT_N:
                sr = np.random.default_rng(seed + n)
                sd = sr.normal(0, 1, gt_curr.shape)
                gt_curr = np.clip(gt_curr + sd / np.linalg.norm(sd) * SHIFT_DELTA, 0, 1)
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt_curr, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            r = scorer.score(fv, ci)
            if n <= FREEZE_AT:
                scorer.update(fv, ci, r.action_index, r.action_index == oa, oa)
            decs.append((fv, ci, oa))
        fm = scorer.centroids.copy()

        test = make_test(gt_curr, seed)

        print(f"\n  Seed {seed} (shift at N={SHIFT_N}, delta={SHIFT_DELTA}):", flush=True)
        print(f"  {'N':>6s}  {'All':>6s}  {'Win1k':>6s}  {'Best':>6s}", flush=True)
        print(f"  {'-'*30}", flush=True)

        for cp in [2000, 3000, 3500, 4000, 5000, 6000]:
            d_all = decs[:cp]
            d_win = decs[max(0, cp-1000):cp]

            print(f"  N={cp}...", end="", flush=True)
            w_all = estimate_dk_coord(d_all, fm)
            a_all = eval_shrunk(test, fm, w_all, 0.5)

            w_win = estimate_dk_coord(d_win, fm)
            a_win = eval_shrunk(test, fm, w_win, 0.5)

            best = "All" if a_all >= a_win else "Win"
            marker = " <SHIFT" if cp == 3000 else ""
            print(f"\r  {cp:>6d}  {a_all:>4.1f}%  {a_win:>4.1f}%  "
                  f"{best:>6s}{marker}", flush=True)

    # ════════════════════════════════════════
    # 4. NOVELTY-TRIGGER (coord descent)
    # ════════════════════════════════════════
    print(f"\n{'='*80}", flush=True)
    print("4. NOVELTY-TRIGGER (coord descent): triggered vs fixed", flush=True)
    print("=" * 80, flush=True)

    N_TRIG = 4000
    FIXED_INTERVAL = 500  # every 500 to keep coord descent manageable

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        decs, fm = collect_freeze(gt, seed, N_TRIG)
        test = make_test(gt, seed)
        cent_acc = eval_pure(test, fm, np.ones((C, A, D)))

        # Strategy A: fixed every 500
        print(f"  Seed {seed} fixed...", end="", flush=True)
        n_reest_a = 0
        for cp in range(FIXED_INTERVAL, N_TRIG + 1, FIXED_INTERVAL):
            w_a = estimate_dk_coord(decs[:cp], fm)
            n_reest_a += 1
        acc_a = eval_shrunk(test, fm, w_a, 0.5)

        # Strategy B: novelty-triggered (check every 250, trigger when mean d_nn > 0.23)
        print(f" novelty...", end="", flush=True)
        n_reest_b = 0
        w_b = np.ones((C, A, D))
        last_reest = 0
        CHECK_INTERVAL = 250

        for n in range(CHECK_INTERVAL, N_TRIG + 1, CHECK_INTERVAL):
            batch = decs[max(0, n - CHECK_INTERVAL):n]
            prior = decs[:max(0, n - CHECK_INTERVAL)]
            if prior:
                dnns = [novelty_dnn(fv, ci, oa, prior) for fv, ci, oa in batch[:20]]
                mean_dnn = np.mean(dnns)
            else:
                mean_dnn = 1.0

            should_reest = mean_dnn > 0.22 and (n - last_reest) >= 400
            if should_reest or n == N_TRIG:
                w_b = estimate_dk_coord(decs[:n], fm)
                n_reest_b += 1
                last_reest = n

        acc_b = eval_shrunk(test, fm, w_b, 0.5)

        print(f"\r  Seed {seed}: fixed={acc_a:.1f}% ({n_reest_a} reest)  "
              f"novelty={acc_b:.1f}% ({n_reest_b} reest)  "
              f"savings={n_reest_a - n_reest_b}", flush=True)

    print(f"\n{'='*80}", flush=True)
    print("BINARY QUESTIONS", flush=True)
    print("1: At what delta does shift make B different from A?", flush=True)
    print("2: Does noise reduction amplify DK gain (R1 x R3)?", flush=True)
    print("3: Does window recover faster than full after shift?", flush=True)
    print("4: Does novelty-trigger match fixed with fewer reest?", flush=True)
    print("\nDONE.", flush=True)


if __name__ == "__main__":
    main()
