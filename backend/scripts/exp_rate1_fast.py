"""
EXP-RATE-1-FAST: DK LONG RUN (optimized)
============================================
Key change: DK calibration subsamples to max 2000 decisions for
speed, even when cumulative data is larger. Tests whether the
PATTERN from more data helps even when calibration uses a sample.

Also: prints each checkpoint as it completes (no buffering).

Run: cd backend && python scripts/exp_rate1_fast.py
Time: ~15-20 min
"""

import sys
import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_MAX = 16000
N_TEST = 500
FREEZE_AT = 500
SEEDS_SHORT = [42, 123, 777]
DK_CAL_MAX = 2000  # subsample for DK calibration speed


def score_dk(fv, ci, centroids, weights):
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        sims.append(-np.sum(weights[ci, ai] * diff ** 2))
    sims = np.array(sims)
    return int(np.argmax(sims)), sims


def dk_probs(sims):
    sims = sims - np.max(sims)
    e = np.exp(sims)
    return e / e.sum()


def estimate_dk_fast(decisions, centroids, n_rounds=5, max_per_cat=400):
    """DK calibration with per-category subsampling for speed."""
    # Group by category
    by_cat = {ci: [] for ci in range(C)}
    for fv, ci_d, oa in decisions:
        by_cat[ci_d].append((fv, oa))

    weights = np.ones((C, A, D))
    for _ in range(n_rounds):
        for ci in range(C):
            cat_decs = by_cat[ci]
            if len(cat_decs) < 10:
                continue
            # Subsample if too large
            if len(cat_decs) > max_per_cat:
                rng_sub = np.random.default_rng(42 + ci)
                indices = rng_sub.choice(len(cat_decs), max_per_cat, replace=False)
                cat_decs_sub = [cat_decs[i] for i in indices]
            else:
                cat_decs_sub = cat_decs

            for ai in range(A):
                for di in range(D):
                    best_w = weights[ci, ai, di]
                    best_acc = sum(1 for fv, oa in cat_decs_sub
                                  if score_dk(fv, ci, centroids, weights)[0] == oa) / len(cat_decs_sub)
                    for w_trial in [0.1, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0]:
                        trial_w = weights.copy()
                        trial_w[ci, ai, di] = w_trial
                        trial_acc = sum(1 for fv, oa in cat_decs_sub
                                        if score_dk(fv, ci, centroids, trial_w)[0] == oa) / len(cat_decs_sub)
                        if trial_acc > best_acc:
                            best_acc = trial_acc
                            best_w = w_trial
                    weights[ci, ai, di] = best_w
    return weights


def evaluate_dk(test_data, centroids, weights):
    correct = sum(1 for fv, ci, oa in test_data
                  if score_dk(fv, ci, centroids, weights)[0] == oa)
    return correct / len(test_data) * 100


def compute_brier(test_data, centroids, weights):
    brier_sum = 0
    for fv, ci, oa in test_data:
        _, sims = score_dk(fv, ci, centroids, weights)
        probs = dk_probs(sims)
        for ai in range(A):
            brier_sum += (probs[ai] - (1 if ai == oa else 0)) ** 2
    return brier_sum / len(test_data)


def compute_d_nn_sample(window, prior, n_sample=30):
    """Mean d_nn for a sample from window."""
    if len(prior) == 0:
        return 1.0
    sample = window[:n_sample]
    d_nns = []
    for fv, ci, oa in sample:
        same_ca = [f for f, c, a in prior[-500:] if c == ci and a == oa]
        if len(same_ca) == 0:
            d_nns.append(1.0)
        else:
            d_nns.append(min(np.linalg.norm(fv - f) for f in same_ca))
    return np.mean(d_nns)


def main():
    base_mu = get_base_centroids()

    checkpoints = [500, 1000, 2000, 3000, 4000, 6000, 8000, 12000, 16000]

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)

        # Collect ALL decisions upfront
        print(f"\nSeed {seed}: collecting {N_MAX} decisions...", flush=True)
        scorer = make_scorer(base_mu.copy())
        all_decisions = []
        for n in range(1, N_MAX + 1):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            result = scorer.score(fv, ci)
            if n <= FREEZE_AT:
                scorer.update(fv, ci, result.action_index,
                              result.action_index == oa, oa)
            all_decisions.append((fv, ci, oa))

        frozen_mu = scorer.centroids.copy()

        # Test data
        rng_test = np.random.default_rng(seed + 50000)
        test_data = []
        for _ in range(N_TEST):
            ci = int(rng_test.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_test.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng_test)
            test_data.append((fv, ci, oa))

        # Centroid baseline
        w_uniform = np.ones((C, A, D))
        cent_acc = evaluate_dk(test_data, frozen_mu, w_uniform)
        cent_brier = compute_brier(test_data, frozen_mu, w_uniform)

        print(f"\nSeed {seed} (centroid: {cent_acc:.1f}%, Brier={cent_brier:.4f})", flush=True)
        print(f"{'N':>6s}  {'DK':>6s}  {'DK-C':>6s}  {'Brier':>8s}  {'d_nn':>6s}  {'Status':>8s}", flush=True)
        print(f"{'-'*45}", flush=True)

        prev_acc = cent_acc
        all_accs = []
        all_briers = []

        for cp in checkpoints:
            if cp > N_MAX:
                break

            print(f"  Calibrating DK at N={cp}...", end="", flush=True)
            decs = all_decisions[:cp]
            w = estimate_dk_fast(decs, frozen_mu, n_rounds=5, max_per_cat=400)
            dk_acc = evaluate_dk(test_data, frozen_mu, w)
            dk_brier = compute_brier(test_data, frozen_mu, w)

            # d_nn for last window
            window_start = max(0, cp - 500)
            window = all_decisions[window_start:cp]
            prior = all_decisions[:window_start]
            d_nn = compute_d_nn_sample(window, prior)

            above = dk_acc >= cent_acc - 0.01
            status = "OK" if above else "BELOW"

            all_accs.append(dk_acc)
            all_briers.append(dk_brier)

            print(f"\r{cp:>6d}  {dk_acc:>4.1f}%  {dk_acc-cent_acc:>+4.1f}pp  "
                  f"{dk_brier:>8.4f}  {d_nn:>5.3f}  {status:>8s}", flush=True)

            prev_acc = dk_acc

        # Monotonicity summary
        below = sum(1 for a in all_accs if a < cent_acc - 0.01)
        print(f"\nH-MONO: {below}/{len(all_accs)} checkpoints below centroid", flush=True)

        # Brier monotonicity
        brier_mono = sum(1 for i in range(1, len(all_briers))
                         if all_briers[i] <= all_briers[i-1] + 0.002)
        print(f"H-BRIER monotonic: {brier_mono}/{len(all_briers)-1} intervals", flush=True)

        # Curve fit
        Ns = np.array(checkpoints[:len(all_accs)])
        accs = np.array(all_accs)

        # Log: acc = a + b*ln(N)
        log_N = np.log(Ns)
        A_log = np.column_stack([np.ones_like(log_N), log_N])
        params_log = np.linalg.lstsq(A_log, accs, rcond=None)[0]
        sse_log = np.sum((accs - A_log @ params_log) ** 2)

        # Saturating: acc = a - b/N
        inv_N = 1.0 / Ns
        A_sat = np.column_stack([np.ones_like(inv_N), inv_N])
        params_sat = np.linalg.lstsq(A_sat, accs, rcond=None)[0]
        sse_sat = np.sum((accs - A_sat @ params_sat) ** 2)

        k = 2
        n_pts = len(accs)
        aic_log = n_pts * np.log(sse_log / n_pts + 1e-10) + 2 * k
        aic_sat = n_pts * np.log(sse_sat / n_pts + 1e-10) + 2 * k
        best = "LOG" if aic_log < aic_sat else "SATURATING"

        print(f"Curve fit: AIC_log={aic_log:.1f} AIC_sat={aic_sat:.1f} --> {best}", flush=True)
        if best == "LOG":
            pred_32k = params_log[0] + params_log[1] * np.log(32000)
            print(f"Log extrapolation to N=32000: {pred_32k:.1f}%", flush=True)

    print("\nDONE.", flush=True)


if __name__ == "__main__":
    main()
