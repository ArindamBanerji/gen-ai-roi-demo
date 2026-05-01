"""
EXP-RATE-6+7+8: NOVELTY MEASUREMENT + INJECTION + COMPARISON
================================================================
Three experiments that validate the novelty model:

RATE-6: Does novelty correlate with DK improvement?
RATE-7: Does injected novelty restart the learning curve?
RATE-8: Which novelty measure is best?

Run: cd backend && python scripts/exp_rate67_novelty.py
Time: ~25 min
"""

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


def score_dk(fv, ci, centroids, weights):
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        sims.append(-np.sum(weights[ci, ai] * diff ** 2))
    return int(np.argmax(sims))


def estimate_dk(decisions, centroids, n_rounds=5):
    weights = np.ones((C, A, D))
    for _ in range(n_rounds):
        for ci in range(C):
            for ai in range(A):
                for di in range(D):
                    cat_decs = [(fv, oa) for fv, cat, oa in decisions if cat == ci]
                    if len(cat_decs) < 10:
                        continue
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
    correct = sum(1 for fv, ci, oa in test_data
                  if score_dk(fv, ci, centroids, weights) == oa)
    return correct / len(test_data) * 100


def collect_decisions(gt, seed, N, frozen_mu=None):
    """Collect N decisions, freezing means at FREEZE_AT."""
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    scorer = make_scorer(base_mu.copy())
    decisions = []
    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        result = scorer.score(fv, ci)
        if n <= FREEZE_AT:
            scorer.update(fv, ci, result.action_index,
                          result.action_index == oa, oa)
        decisions.append((fv, ci, oa))
    return decisions, scorer.centroids.copy()


# ══════════════════════════════════════════════════════
# NOVELTY MEASURES
# ══════════════════════════════════════════════════════

def novelty_n1_dnn(fv, ci, oa, prior_decisions):
    """N1: Distance to nearest prior decision in same (c,a)."""
    same_ca = [f for f, c, a in prior_decisions if c == ci and a == oa]
    if len(same_ca) == 0:
        return 1.0
    dists = [np.linalg.norm(fv - f) for f in same_ca[-200:]]  # limit for speed
    d_nn = min(dists)
    d_typical = np.median(dists) if len(dists) > 1 else 1.0
    return 1 - np.exp(-d_nn / max(d_typical, 0.01))


def novelty_n3_density(fv, ci, oa, prior_decisions, bandwidth=0.1):
    """N3: Information-theoretic (kernel density)."""
    same_ca = [f for f, c, a in prior_decisions if c == ci and a == oa]
    if len(same_ca) < 5:
        return 1.0
    # Use last 200 for speed
    recent = same_ca[-200:]
    dists = [np.linalg.norm(fv - f) for f in recent]
    # Gaussian KDE
    log_density = np.log(np.mean([np.exp(-d ** 2 / (2 * bandwidth ** 2)) for d in dists]) + 1e-10)
    # Normalize to [0, 1]: low density = high novelty
    return np.clip(-log_density / 10, 0, 1)


def novelty_n5_zscore(fv, ci, oa, prior_decisions):
    """N5: Max per-dimension z-score."""
    same_ca = np.array([f for f, c, a in prior_decisions if c == ci and a == oa])
    if len(same_ca) < 5:
        return 1.0
    mu = same_ca.mean(axis=0)
    sigma = same_ca.std(axis=0) + 1e-10
    z = np.abs(fv - mu) / sigma
    return float(np.clip(np.max(z) / 5, 0, 1))


def novelty_n_count(ci, oa, prior_decisions):
    """Simple: 1/N_{c,a} count-based novelty."""
    n_ca = sum(1 for f, c, a in prior_decisions if c == ci and a == oa)
    return 1.0 / (1.0 + n_ca / 50.0)


def main():
    base_mu = get_base_centroids()

    # ══════════════════════════════════════════════════════
    # RATE-6+8: NOVELTY MEASUREMENT + COMPARISON
    # ══════════════════════════════════════════════════════
    print("=" * 90)
    print("RATE-6+8: NOVELTY MEASUREMENT + COMPARISON")
    print("Does novelty correlate with DK improvement?")
    print("=" * 90)

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        decisions, frozen_mu = collect_decisions(gt, seed, N_MAX)

        # Test data
        rng_test = np.random.default_rng(seed + 50000)
        test_data = []
        for _ in range(N_TEST):
            ci = int(rng_test.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_test.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng_test)
            test_data.append((fv, ci, oa))

        # DK re-estimation at each interval, with novelty tracking
        print(f"\n  Seed {seed}:")
        print(f"  {'Window':>8s}  {'DK_acc':>7s}  {'DeltaP':>7s}  {'d_nn':>6s}  "
              f"{'z_max':>6s}  {'1/N_ca':>6s}  {'density':>7s}  {'novel%':>7s}")
        print(f"  {'-' * 65}")

        window_metrics = []
        prev_acc = None

        for cp in range(DK_INTERVAL, min(N_MAX, 4001), DK_INTERVAL):
            decs = decisions[:cp]
            w = estimate_dk(decs, frozen_mu, n_rounds=5)
            acc = evaluate_dk(test_data, frozen_mu, w)

            # Compute novelty for this window's decisions
            window = decisions[cp - DK_INTERVAL:cp]
            prior = decisions[:cp - DK_INTERVAL]

            d_nns, z_maxes, counts, densities = [], [], [], []
            for fv, ci, oa in window[:100]:  # sample for speed
                d_nns.append(novelty_n1_dnn(fv, ci, oa, prior))
                z_maxes.append(novelty_n5_zscore(fv, ci, oa, prior))
                counts.append(novelty_n_count(ci, oa, prior))
                densities.append(novelty_n3_density(fv, ci, oa, prior))

            mean_dnn = np.mean(d_nns)
            mean_z = np.mean(z_maxes)
            mean_count = np.mean(counts)
            mean_density = np.mean(densities)
            novel_frac = np.mean([1 if d > 0.3 else 0 for d in d_nns])

            delta_p = acc - prev_acc if prev_acc is not None else 0
            prev_acc = acc

            window_metrics.append({
                'cp': cp, 'acc': acc, 'delta_p': delta_p,
                'dnn': mean_dnn, 'z_max': mean_z,
                'count': mean_count, 'density': mean_density,
                'novel_frac': novel_frac,
            })

            print(f"  {cp:>8d}  {acc:>5.1f}%  {delta_p:>+5.1f}pp  {mean_dnn:>5.3f}  "
                  f"{mean_z:>5.3f}  {mean_count:>5.3f}  {mean_density:>6.3f}  {novel_frac*100:>5.0f}%")

        # Correlation analysis
        if len(window_metrics) > 5:
            deltas = np.array([m['delta_p'] for m in window_metrics[1:]])  # skip first
            dnns = np.array([m['dnn'] for m in window_metrics[1:]])
            zs = np.array([m['z_max'] for m in window_metrics[1:]])
            cnts = np.array([m['count'] for m in window_metrics[1:]])
            dens = np.array([m['density'] for m in window_metrics[1:]])
            nfrac = np.array([m['novel_frac'] for m in window_metrics[1:]])

            print(f"\n  CORRELATION WITH DeltaPerf:")
            measures = {'d_nn': dnns, 'z_max': zs, '1/N_ca': cnts,
                        'density': dens, 'novel_frac': nfrac}
            for name, vals in measures.items():
                if np.std(vals) > 0 and np.std(deltas) > 0:
                    corr = np.corrcoef(vals, deltas)[0, 1]
                    # Rank correlation
                    rank_v = np.argsort(np.argsort(vals))
                    rank_d = np.argsort(np.argsort(deltas))
                    rank_corr = np.corrcoef(rank_v, rank_d)[0, 1]
                    print(f"    {name:>12s}: Pearson={corr:+.3f} Spearman={rank_corr:+.3f}")

            # Novelty trajectory
            print(f"\n  NOVELTY TRAJECTORY (d_nn over time):")
            for m in window_metrics[::4]:
                bar = "#" * int(m['dnn'] * 50)
                print(f"    N={m['cp']:>5d}: d_nn={m['dnn']:.3f} {bar}")

    # ══════════════════════════════════════════════════════
    # RATE-7: NOVELTY INJECTION
    # ══════════════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("RATE-7: NOVELTY INJECTION")
    print("Does injected novelty restart the DK learning curve?")
    print("=" * 90)

    SHIFT_MAG = 0.05
    SHIFT_AT = [2000, 4000, 6000]

    for seed in SEEDS_SHORT:
        gt_orig = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)

        # Collect decisions with NO shift (Condition A)
        scorer_a = make_scorer(base_mu.copy())
        decs_a = []
        for n in range(1, N_MAX + 1):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt_orig, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            result = scorer_a.score(fv, ci)
            if n <= FREEZE_AT:
                scorer_a.update(fv, ci, result.action_index,
                                result.action_index == oa, oa)
            decs_a.append((fv, ci, oa))
        frozen_mu_a = scorer_a.centroids.copy()

        # Collect decisions WITH shifts (Condition B)
        rng_b = np.random.default_rng(seed)
        scorer_b = make_scorer(base_mu.copy())
        decs_b = []
        gt_current = gt_orig.copy()
        for n in range(1, N_MAX + 1):
            # Apply shifts
            if n in SHIFT_AT:
                shift_rng = np.random.default_rng(seed + n)
                shift_dir = shift_rng.normal(0, 1, gt_current.shape)
                shift_dir = shift_dir / np.linalg.norm(shift_dir) * SHIFT_MAG
                gt_current = np.clip(gt_current + shift_dir, 0, 1)

            ci = int(rng_b.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_b.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt_current, ci, fv)
            oa = noise_realistic(ta, ci, rng_b)
            result = scorer_b.score(fv, ci)
            if n <= FREEZE_AT:
                scorer_b.update(fv, ci, result.action_index,
                                result.action_index == oa, oa)
            decs_b.append((fv, ci, oa))
        frozen_mu_b = scorer_b.centroids.copy()

        # Test data (use CURRENT gt for condition B at each checkpoint)
        rng_test = np.random.default_rng(seed + 50000)
        test_orig = []
        for _ in range(N_TEST):
            ci = int(rng_test.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_test.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt_orig, ci, fv)
            oa = noise_realistic(ta, ci, rng_test)
            test_orig.append((fv, ci, oa))

        # Evaluate both conditions at checkpoints
        print(f"\n  Seed {seed}:")
        print(f"  {'N':>6s}  {'A (fixed)':>9s}  {'B (shifts)':>10s}  {'B-A':>6s}  "
              f"{'d_nn_A':>6s}  {'d_nn_B':>6s}  {'Event':>8s}")
        print(f"  {'-' * 60}")

        for cp in range(DK_INTERVAL, N_MAX + 1, DK_INTERVAL):
            w_a = estimate_dk(decs_a[:cp], frozen_mu_a, n_rounds=4)
            acc_a = evaluate_dk(test_orig, frozen_mu_a, w_a)

            # For B: use test data against CURRENT gt at this checkpoint
            gt_at_cp = gt_orig.copy()
            for s in SHIFT_AT:
                if cp >= s:
                    sr = np.random.default_rng(seed + s)
                    sd = sr.normal(0, 1, gt_at_cp.shape)
                    sd = sd / np.linalg.norm(sd) * SHIFT_MAG
                    gt_at_cp = np.clip(gt_at_cp + sd, 0, 1)

            rng_test_b = np.random.default_rng(seed + 50000)
            test_b = []
            for _ in range(N_TEST):
                ci = int(rng_test_b.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng_test_b.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                ta = true_action(gt_at_cp, ci, fv)
                oa = noise_realistic(ta, ci, rng_test_b)
                test_b.append((fv, ci, oa))

            w_b = estimate_dk(decs_b[:cp], frozen_mu_b, n_rounds=4)
            acc_b = evaluate_dk(test_b, frozen_mu_b, w_b)

            # d_nn for each condition
            prior_a = decs_a[:max(0, cp - DK_INTERVAL)]
            window_a = decs_a[max(0, cp - DK_INTERVAL):cp]
            dnn_a = np.mean([novelty_n1_dnn(fv, ci, oa, prior_a)
                             for fv, ci, oa in window_a[:30]]) if prior_a else 1.0

            prior_b = decs_b[:max(0, cp - DK_INTERVAL)]
            window_b = decs_b[max(0, cp - DK_INTERVAL):cp]
            dnn_b = np.mean([novelty_n1_dnn(fv, ci, oa, prior_b)
                             for fv, ci, oa in window_b[:30]]) if prior_b else 1.0

            event = ""
            if cp in SHIFT_AT:
                event = f"SHIFT"
            elif cp - DK_INTERVAL in SHIFT_AT:
                event = "post"

            if cp % 1000 == 0 or event:
                print(f"  {cp:>6d}  {acc_a:>7.1f}%  {acc_b:>8.1f}%  {acc_b - acc_a:>+4.1f}pp  "
                      f"{dnn_a:>5.3f}  {dnn_b:>5.3f}  {event:>8s}")

        # Summary
        # Final comparison
        w_a_final = estimate_dk(decs_a, frozen_mu_a, n_rounds=5)
        acc_a_final = evaluate_dk(test_orig, frozen_mu_a, w_a_final)

        rng_test_bf = np.random.default_rng(seed + 50000)
        test_bf = []
        gt_final = gt_orig.copy()
        for s in SHIFT_AT:
            sr = np.random.default_rng(seed + s)
            sd = sr.normal(0, 1, gt_final.shape)
            sd = sd / np.linalg.norm(sd) * SHIFT_MAG
            gt_final = np.clip(gt_final + sd, 0, 1)
        for _ in range(N_TEST):
            ci = int(rng_test_bf.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_test_bf.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt_final, ci, fv)
            oa = noise_realistic(ta, ci, rng_test_bf)
            test_bf.append((fv, ci, oa))

        w_b_final = estimate_dk(decs_b, frozen_mu_b, n_rounds=5)
        acc_b_final = evaluate_dk(test_bf, frozen_mu_b, w_b_final)

        print(f"\n  FINAL (N={N_MAX}):")
        print(f"    Condition A (fixed GT):  {acc_a_final:.1f}%")
        print(f"    Condition B (3 shifts):  {acc_b_final:.1f}%")
        print(f"    B - A:                   {acc_b_final - acc_a_final:+.1f}pp")

    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("RATE-6:")
    print("  Q1: d_nn correlates positively with DeltaPerf?")
    print("  Q2: d_nn decreases over time (novelty exhausts)?")
    print("  Q3: Best novelty predictor of DeltaPerf?")
    print("RATE-7:")
    print("  Q4: After each shift, DK accuracy recovers within 500 decisions?")
    print("  Q5: At N=8000, Condition B > Condition A?")
    print("  Q6: d_nn spikes at shift points?")
    print("RATE-8:")
    print("  Q7: Any novelty measure has corr > 0.30 with DeltaPerf?")
    print("  Q8: Best measure consistent across seeds?")

    print("\nDONE.")


if __name__ == "__main__":
    main()
