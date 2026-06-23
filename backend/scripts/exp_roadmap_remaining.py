"""
EXP-ROADMAP-REMAINING: Five experiments from roadmap session
================================================================
All use direct variance estimation (fast -- no coordinate descent).

1. NOVELTY-LARGE: Larger GT shifts (delta=0.10, 0.15, 0.25)
2. DK-NOISE: DK learning curve at 4 noise levels
3. NOVELTY-TRIGGER: Novelty-triggered vs fixed-schedule re-estimation
4. PHASE-1: Phase transition alternatives (accuracy vs velocity vs novelty)
5. WINDOW-1: Accumulation vs sliding window under distribution shift

Run: cd backend && python scripts/exp_roadmap_remaining.py
Time: ~15-20 min (all use direct estimation, no coord descent)
"""

import sys
import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_TEST = 500
FREEZE_AT = 500
SEEDS_SHORT = [42, 123, 777]


def estimate_dk_direct(decisions, centroids, reg=0.01):
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
            sigma2 = np.mean((fvs - mu) ** 2, axis=0) + reg
            w = 1.0 / sigma2
            if w.max() > 0:
                w = w / w.max()
            weights[ci, ai] = w
    return weights


def estimate_dk_windowed(decisions, centroids, window_size, reg=0.01):
    """Direct estimation on last window_size decisions only."""
    return estimate_dk_direct(decisions[-window_size:], centroids, reg)


def estimate_dk_decay(decisions, centroids, half_life=1000, reg=0.01):
    """Direct estimation with exponential decay weighting."""
    weights = np.ones((C, A, D))
    by_ca = {}
    N = len(decisions)
    for idx, (fv, ci, oa) in enumerate(decisions):
        key = (ci, oa)
        if key not in by_ca:
            by_ca[key] = []
        age = N - idx
        weight = np.exp(-age * np.log(2) / half_life)
        by_ca[key].append((fv, weight))
    for ci in range(C):
        for ai in range(A):
            key = (ci, ai)
            if key not in by_ca or len(by_ca[key]) < 5:
                continue
            fvs = np.array([fv for fv, w in by_ca[key]])
            ws = np.array([w for fv, w in by_ca[key]])
            mu = centroids[ci, ai]
            r2 = (fvs - mu) ** 2
            sigma2 = np.average(r2, axis=0, weights=ws) + reg
            w = 1.0 / sigma2
            if w.max() > 0:
                w = w / w.max()
            weights[ci, ai] = w
    return weights


def score_shrunk(fv, ci, centroids, dk_weights, alpha):
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        w_tilde = alpha * dk_weights[ci, ai] + (1 - alpha) * 1.0
        sims.append(-np.sum(w_tilde * diff ** 2))
    return int(np.argmax(sims))


def eval_shrunk(test_data, centroids, dk_w, alpha):
    return sum(1 for fv, ci, oa in test_data
               if score_shrunk(fv, ci, centroids, dk_w, alpha) == oa) / len(test_data) * 100


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
    print("1. NOVELTY-LARGE: GT shifts at delta = 0.10, 0.15, 0.25", flush=True)
    print("=" * 80, flush=True)

    N_INJ = 6000
    SHIFT_AT = [2000, 4000]

    for delta in [0.05, 0.10, 0.15, 0.25]:
        accs_a, accs_b = [], []
        for seed in SEEDS_SHORT:
            gt_orig = build_gt(np.random.default_rng(seed), base_mu)

            # A: no shift
            decs_a, fm_a = collect_freeze(gt_orig, seed, N_INJ)
            test_a = make_test(gt_orig, seed)
            w_a = estimate_dk_direct(decs_a, fm_a)
            acc_a = eval_shrunk(test_a, fm_a, w_a, 0.5)

            # B: with shifts
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
            w_b = estimate_dk_direct(decs_b, fm_b)
            acc_b = eval_shrunk(test_b, fm_b, w_b, 0.5)

            accs_a.append(acc_a)
            accs_b.append(acc_b)

        print(f"  delta={delta:.2f}: A(fixed)={np.mean(accs_a):.1f}%  "
              f"B(shift)={np.mean(accs_b):.1f}%  "
              f"B-A={np.mean(accs_b)-np.mean(accs_a):+.1f}pp", flush=True)

    # ════════════════════════════════════════
    # 2. DK-NOISE: DK at 4 noise levels
    # ════════════════════════════════════════
    print(f"\n{'='*80}", flush=True)
    print("2. DK-NOISE: DK learning curve at 4 oracle noise levels", flush=True)
    print("=" * 80, flush=True)

    noise_levels = [0.05, 0.15, 0.25, 0.50]
    # We simulate different noise by adjusting the FREQ_NOISE rates
    # For simplicity: multiply all category noise rates by a factor

    for noise_mult in [0.33, 1.0, 1.67, 3.33]:  # ~5%, 15%, 25%, 50% avg
        label = f"{noise_mult*15:.0f}%"
        accs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            rng = np.random.default_rng(seed)
            scorer = make_scorer(base_mu.copy())
            decs = []
            for n in range(1, 4001):
                ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                ta = true_action(gt, ci, fv)
                # Adjusted noise
                base_rate = {0: 0.08, 1: 0.12, 2: 0.15, 3: 0.18, 4: 0.22, 5: 0.22}[ci]
                adj_rate = min(base_rate * noise_mult, 0.90)
                if rng.random() < adj_rate:
                    from exp_shared import ADJACENT
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
            cent_acc = eval_shrunk(test, fm, np.ones((C, A, D)), 0.0)
            w = estimate_dk_direct(decs, fm)
            dk_acc = eval_shrunk(test, fm, w, 0.5)
            accs.append((cent_acc, dk_acc))

        mc = np.mean([a[0] for a in accs])
        md = np.mean([a[1] for a in accs])
        print(f"  noise~{label:>4s}: cent={mc:.1f}%  DK@0.5={md:.1f}%  "
              f"gain={md-mc:+.1f}pp", flush=True)

    # ════════════════════════════════════════
    # 3. NOVELTY-TRIGGER: Triggered vs fixed
    # ════════════════════════════════════════
    print(f"\n{'='*80}", flush=True)
    print("3. NOVELTY-TRIGGER: Novelty-triggered vs fixed-schedule re-estimation", flush=True)
    print("=" * 80, flush=True)

    N_TRIG = 4000
    FIXED_INTERVAL = 200

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        decs, fm = collect_freeze(gt, seed, N_TRIG)
        test = make_test(gt, seed)

        # Strategy A: fixed every 200
        n_reest_a = 0
        best_acc_a = 0
        for cp in range(FIXED_INTERVAL, N_TRIG + 1, FIXED_INTERVAL):
            w = estimate_dk_direct(decs[:cp], fm)
            n_reest_a += 1
        acc_a = eval_shrunk(test, fm, w, 0.5)

        # Strategy B: novelty-triggered (re-estimate when mean d_nn > 0.25 for batch)
        n_reest_b = 0
        novelty_accum = 0
        last_reest = 0
        w_b = np.ones((C, A, D))
        for n in range(FIXED_INTERVAL, N_TRIG + 1, 50):  # check every 50
            batch = decs[max(0, n - 50):n]
            prior = decs[:max(0, n - 50)]
            if prior:
                dnns = [novelty_dnn(fv, ci, oa, prior) for fv, ci, oa in batch[:20]]
                mean_dnn = np.mean(dnns)
            else:
                mean_dnn = 1.0
            novelty_accum += mean_dnn * len(batch)
            if novelty_accum / max(n - last_reest, 1) > 0.22 and n - last_reest >= 100:
                w_b = estimate_dk_direct(decs[:n], fm)
                n_reest_b += 1
                novelty_accum = 0
                last_reest = n
        if last_reest < N_TRIG:
            w_b = estimate_dk_direct(decs, fm)
            n_reest_b += 1
        acc_b = eval_shrunk(test, fm, w_b, 0.5)

        print(f"  Seed {seed}: fixed={acc_a:.1f}% ({n_reest_a} reest)  "
              f"novelty={acc_b:.1f}% ({n_reest_b} reest)  "
              f"savings={n_reest_a - n_reest_b} fewer", flush=True)

    # ════════════════════════════════════════
    # 4. PHASE-1: Phase transition alternatives
    # ════════════════════════════════════════
    print(f"\n{'='*80}", flush=True)
    print("4. PHASE-1: Phase transition criteria comparison", flush=True)
    print("=" * 80, flush=True)

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)
        scorer = make_scorer(base_mu.copy())

        rolling_acc = []
        centroid_velocities = []
        prev_mu = scorer.centroids.copy()

        trigger_acc = None
        trigger_vel = None
        trigger_count = None

        for n in range(1, 2001):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            r = scorer.score(fv, ci)
            correct = (r.action_index == oa)
            scorer.update(fv, ci, r.action_index, correct, oa)

            rolling_acc.append(1 if correct else 0)

            # Track centroid velocity
            vel = np.linalg.norm(scorer.centroids - prev_mu)
            centroid_velocities.append(vel)
            prev_mu = scorer.centroids.copy()

            # Criterion A: rolling accuracy > 0.80 for 200 decisions
            if trigger_acc is None and n >= 200:
                if np.mean(rolling_acc[-200:]) > 0.80:
                    trigger_acc = n

            # Criterion B: centroid velocity < 0.001 for 200 decisions
            if trigger_vel is None and n >= 200:
                if np.mean(centroid_velocities[-200:]) < 0.001:
                    trigger_vel = n

            # Criterion C: per-pair count > 100 (simplified: total > 500)
            if trigger_count is None and n >= 500:
                trigger_count = n

        print(f"  Seed {seed}:", flush=True)
        print(f"    Accuracy > 0.80 triggers at N = {trigger_acc or 'never'}", flush=True)
        print(f"    Velocity < 0.001 triggers at N = {trigger_vel or 'never'}", flush=True)
        print(f"    Count > 500 triggers at N = {trigger_count or 'never'}", flush=True)
        if trigger_acc:
            print(f"    Rolling acc at trigger: {np.mean(rolling_acc[trigger_acc-200:trigger_acc]):.3f}", flush=True)
        if trigger_vel:
            print(f"    Mean velocity at trigger: {np.mean(centroid_velocities[trigger_vel-200:trigger_vel]):.5f}", flush=True)

    # ════════════════════════════════════════
    # 5. WINDOW-1: Accumulation vs window under shift
    # ════════════════════════════════════════
    print(f"\n{'='*80}", flush=True)
    print("5. WINDOW-1: Accumulation vs window vs decay under shift", flush=True)
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

        # Test against POST-SHIFT gt
        test = make_test(gt_curr, seed)

        print(f"\n  Seed {seed} (shift at N={SHIFT_N}, delta={SHIFT_DELTA}):", flush=True)
        print(f"  {'N':>6s}  {'All':>6s}  {'Win1k':>6s}  {'Decay':>6s}  {'Best':>6s}", flush=True)
        print(f"  {'-'*35}", flush=True)

        for cp in [1000, 2000, 3000, 3500, 4000, 5000, 6000]:
            d = decs[:cp]
            w_all = estimate_dk_direct(d, fm)
            w_win = estimate_dk_windowed(d, fm, window_size=1000)
            w_dec = estimate_dk_decay(d, fm, half_life=1000)

            a_all = eval_shrunk(test, fm, w_all, 0.5)
            a_win = eval_shrunk(test, fm, w_win, 0.5)
            a_dec = eval_shrunk(test, fm, w_dec, 0.5)

            best = ["All", "Win", "Dec"][np.argmax([a_all, a_win, a_dec])]
            marker = " <SHIFT" if cp == 3000 else ""
            print(f"  {cp:>6d}  {a_all:>4.1f}%  {a_win:>4.1f}%  {a_dec:>4.1f}%  "
                  f"{best:>6s}{marker}", flush=True)

    print(f"\n{'='*80}", flush=True)
    print("BINARY QUESTIONS", flush=True)
    print("1: At what delta does shift restart DK learning?", flush=True)
    print("2: Does noise reduction amplify DK gain (R1 x R3)?", flush=True)
    print("3: Does novelty-trigger match fixed with fewer re-estimations?", flush=True)
    print("4: Which phase criterion triggers first?", flush=True)
    print("5: Does window/decay recover faster than full accumulation after shift?", flush=True)
    print("\nDONE.", flush=True)


if __name__ == "__main__":
    main()
