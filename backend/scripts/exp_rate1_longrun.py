"""
EXP-RATE-1+3+4: V-DK-LONG-RUN + CALIBRATION + MONOTONICITY
==============================================================
Combined experiment:
  RATE-1: DK learning curve to N=16000 (asymptotic behavior)
  RATE-3: ECE + Brier at each checkpoint (right metric)
  RATE-4: Monotonicity of DK re-estimation (claim qualifier)

Run: cd backend && python scripts/exp_rate1_longrun.py
Time: ~30 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_MAX = 16000
N_TEST = 500
FREEZE_AT = 500
DK_INTERVAL = 200
SEEDS_SHORT = [42, 123, 777]


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
                                  if score_dk(fv, ci, centroids, weights)[0] == oa) / len(cat_decs)
                    for w_trial in [0.1, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0]:
                        trial_w = weights.copy()
                        trial_w[ci, ai, di] = w_trial
                        trial_acc = sum(1 for fv, oa in cat_decs
                                        if score_dk(fv, ci, centroids, trial_w)[0] == oa) / len(cat_decs)
                        if trial_acc > best_acc:
                            best_acc = trial_acc
                            best_w = w_trial
                    weights[ci, ai, di] = best_w
    return weights


def compute_brier_ece(test_data, centroids, weights):
    """Compute accuracy, ECE, and Brier score."""
    corrects = []
    confs = []
    brier_sum = 0
    n = len(test_data)

    for fv, ci, oa in test_data:
        pred, sims = score_dk(fv, ci, centroids, weights)
        probs = dk_probs(sims)
        conf = float(probs[pred])
        correct = (pred == oa)

        corrects.append(1 if correct else 0)
        confs.append(conf)

        # Brier: sum of (p_a - indicator(a=oa))^2
        for ai in range(A):
            brier_sum += (probs[ai] - (1 if ai == oa else 0)) ** 2

    acc = np.mean(corrects) * 100
    brier = brier_sum / n

    # ECE
    confs_arr = np.array(confs)
    corrs_arr = np.array(corrects)
    n_bins = 10
    bounds = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        lo, hi = bounds[i], bounds[i + 1]
        mask = (confs_arr >= lo) & (confs_arr < hi) if i < n_bins - 1 else (confs_arr >= lo) & (confs_arr <= hi)
        count = mask.sum()
        if count == 0:
            continue
        ece += (count / n) * abs(corrs_arr[mask].mean() - confs_arr[mask].mean())

    return acc, ece, brier


def compute_d_nn(fv, ci, oa, prior_decisions):
    """Distance to nearest prior decision in same (c,a)."""
    same_ca = [f for f, c, a in prior_decisions if c == ci and a == oa]
    if len(same_ca) == 0:
        return 1.0  # maximum novelty
    dists = [np.linalg.norm(fv - f) for f in same_ca]
    return min(dists)


def main():
    print("=" * 90)
    print("EXP-RATE-1+3+4: DK LONG RUN + CALIBRATION + MONOTONICITY")
    print("=" * 90)

    base_mu = get_base_centroids()

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)

        # Collect all decisions
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
        cent_acc, cent_ece, cent_brier = compute_brier_ece(test_data, frozen_mu, w_uniform)

        print(f"\n  Seed {seed} (centroid: acc={cent_acc:.1f}% ECE={cent_ece:.4f} Brier={cent_brier:.4f}):")
        print(f"\n  RATE-1: DK LEARNING CURVE")
        print(f"  {'N':>6s}  {'Acc':>6s}  {'ECE':>8s}  {'Brier':>8s}  {'DK-Cent':>7s}  "
              f"{'d_nn':>6s}  {'monotonic':>9s}")
        print(f"  {'-' * 60}")

        # DK re-estimation at every interval
        prev_acc = cent_acc
        all_accs = []
        all_eces = []
        all_briers = []
        dips = 0
        max_dip = 0
        dip_recovered = []

        checkpoints_to_print = {500, 1000, 2000, 4000, 6000, 8000, 12000, 16000}

        for cp in range(DK_INTERVAL, N_MAX + 1, DK_INTERVAL):
            decs = all_decisions[:cp]
            w = estimate_dk(decs, frozen_mu, n_rounds=5)
            acc, ece, brier = compute_brier_ece(test_data, frozen_mu, w)

            # Mean d_nn for this window
            window = all_decisions[max(0, cp - DK_INTERVAL):cp]
            prior = all_decisions[:max(0, cp - DK_INTERVAL)]
            if len(prior) > 0:
                d_nns = [compute_d_nn(fv, ci, oa, prior) for fv, ci, oa in window[:50]]
                mean_dnn = np.mean(d_nns)
            else:
                mean_dnn = 1.0

            # Monotonicity tracking
            if acc < prev_acc - 0.01:
                dips += 1
                dip_mag = prev_acc - acc
                max_dip = max(max_dip, dip_mag)

            all_accs.append(acc)
            all_eces.append(ece)
            all_briers.append(brier)

            mono = "+" if acc >= prev_acc - 0.01 else f"DIP {prev_acc - acc:.1f}"

            if cp in checkpoints_to_print:
                print(f"  {cp:>6d}  {acc:>4.1f}%  {ece:>8.4f}  {brier:>8.4f}  "
                      f"{acc - cent_acc:>+5.1f}pp  {mean_dnn:>5.3f}  {mono:>9s}")

            prev_acc = acc

        # RATE-4: Monotonicity summary
        total_intervals = len(all_accs) - 1
        mono_violations = dips
        print(f"\n  RATE-4: MONOTONICITY")
        print(f"    Total DK re-estimations: {total_intervals}")
        print(f"    Non-monotonic (dips):    {mono_violations} ({mono_violations/max(total_intervals,1)*100:.0f}%)")
        print(f"    Max single dip:          {max_dip:.1f}pp")

        # RATE-3: Which metric is most monotonic?
        acc_mono = sum(1 for i in range(1, len(all_accs)) if all_accs[i] >= all_accs[i-1] - 0.01)
        ece_mono = sum(1 for i in range(1, len(all_eces)) if all_eces[i] <= all_eces[i-1] + 0.001)
        brier_mono = sum(1 for i in range(1, len(all_briers)) if all_briers[i] <= all_briers[i-1] + 0.001)
        print(f"\n  RATE-3: METRIC MONOTONICITY")
        print(f"    Accuracy monotonic: {acc_mono}/{total_intervals} ({acc_mono/max(total_intervals,1)*100:.0f}%)")
        print(f"    ECE monotonic:      {ece_mono}/{total_intervals} ({ece_mono/max(total_intervals,1)*100:.0f}%)")
        print(f"    Brier monotonic:    {brier_mono}/{total_intervals} ({brier_mono/max(total_intervals,1)*100:.0f}%)")

        # Fit learning curve models
        Ns = np.array([(i + 1) * DK_INTERVAL for i in range(len(all_accs))])
        accs_arr = np.array(all_accs)

        # Log fit: acc = a + b*ln(N)
        log_N = np.log(Ns)
        A_log = np.column_stack([np.ones_like(log_N), log_N])
        try:
            params_log = np.linalg.lstsq(A_log, accs_arr, rcond=None)[0]
            pred_log = A_log @ params_log
            sse_log = np.sum((accs_arr - pred_log) ** 2)
        except:
            sse_log = 1e10

        # Saturating fit: acc = a - b/N
        inv_N = 1.0 / Ns
        A_sat = np.column_stack([np.ones_like(inv_N), inv_N])
        try:
            params_sat = np.linalg.lstsq(A_sat, accs_arr, rcond=None)[0]
            pred_sat = A_sat @ params_sat
            sse_sat = np.sum((accs_arr - pred_sat) ** 2)
        except:
            sse_sat = 1e10

        # Power law fit: acc = a + b*N^c, linearized as acc = a + b*N^0.3
        pow_N = Ns ** 0.3
        A_pow = np.column_stack([np.ones_like(pow_N), pow_N])
        try:
            params_pow = np.linalg.lstsq(A_pow, accs_arr, rcond=None)[0]
            pred_pow = A_pow @ params_pow
            sse_pow = np.sum((accs_arr - pred_pow) ** 2)
        except:
            sse_pow = 1e10

        k = 2  # number of parameters
        n_pts = len(accs_arr)
        aic_log = n_pts * np.log(sse_log / n_pts + 1e-10) + 2 * k
        aic_sat = n_pts * np.log(sse_sat / n_pts + 1e-10) + 2 * k
        aic_pow = n_pts * np.log(sse_pow / n_pts + 1e-10) + 2 * k

        best_model = ["LOG", "SATURATING", "POWER"][np.argmin([aic_log, aic_sat, aic_pow])]
        print(f"\n  RATE-1: CURVE FIT")
        print(f"    AIC log:       {aic_log:.1f}")
        print(f"    AIC saturating: {aic_sat:.1f}")
        print(f"    AIC power:     {aic_pow:.1f}")
        print(f"    Best model:    {best_model}")

        # Extrapolation
        if best_model == "LOG":
            pred_32k = params_log[0] + params_log[1] * np.log(32000)
            print(f"    Predicted at N=32000: {pred_32k:.1f}%")

    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("Q1: DK accuracy at N=16000 > N=4000?")
    print("Q2: Marginal still positive at N=16000?")
    print("Q3: Best fitting model (log/saturating/power)?")
    print("Q4: Non-monotonic fraction < 10%?")
    print("Q5: Most reliably monotonic metric?")
    print("Q6: Correlation(d_nn, DeltaPerf)?")

    print("\nDONE.")


if __name__ == "__main__":
    main()
