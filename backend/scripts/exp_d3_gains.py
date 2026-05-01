"""
EXP-D3: GAIN FUNCTION COMPARISON
===================================
Fix architecture (open loop), vary gain function.

Run: cd backend && python scripts/exp_d3_gains.py
Time: ~20 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, FREQ_NOISE, ADJACENT
)

SEEDS_SHORT = [42, 123, 777]


def compute_ece(confs, corrects, n_bins=10):
    bounds = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    total = len(confs)
    if total == 0:
        return 0.0
    for i in range(n_bins):
        lo, hi = bounds[i], bounds[i + 1]
        mask = (confs >= lo) & (confs < hi) if i < n_bins - 1 else (confs >= lo) & (confs <= hi)
        count = mask.sum()
        if count == 0:
            continue
        ece += (count / total) * abs(corrects[mask].mean() - confs[mask].mean())
    return ece


def run_gain_test(seed, gain_name, gt, start_mu, N):
    rng = np.random.default_rng(seed)
    scorer = make_scorer(start_mu.copy())
    ca_counts = np.zeros((C, A))
    prev_mu = scorer.centroids.copy()
    velocity = 0.01
    mode = "LEARN"
    prev_acc = 0.5
    prev_delta_mu = np.zeros_like(scorer.centroids)

    lc = 0
    all_confs, all_corrects = [], []
    cp = {}

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc += 1
        all_confs.append(result.confidence)
        all_corrects.append(1.0 if correct else 0.0)

        if n % 50 == 0:
            velocity = np.linalg.norm(scorer.centroids - prev_mu) / 50
            prev_mu = scorer.centroids.copy()

        ai_target = oa
        n_ca = ca_counts[ci, ai_target]
        mu_ca = scorer.centroids[ci, ai_target]

        # Compute gain based on gain_name
        if gain_name == "fixed_005":
            scale = 1.0  # default eta
        elif gain_name == "inv_n":
            scale = 1.0 / (1.0 + n_ca / 50.0)
        elif gain_name == "inv_sqrt_n":
            scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
        elif gain_name == "velocity_based":
            sigmoid_val = 1.0 / (1.0 + np.exp(-500 * (velocity - 0.001)))
            scale = 0.1 + 1.9 * sigmoid_val  # 0.1x to 2.0x default
        elif gain_name == "override_based":
            override = 1.0 if not correct else 0.0
            scale = 0.1 + 1.9 * override  # 2x for overrides, 0.1x for confirms
        elif gain_name == "dual_rate":
            if n_ca < 50:
                scale = 1.6  # fast (0.08 effective)
            else:
                scale = 0.1  # slow (0.005 effective)
        elif gain_name == "lms_adaptive":
            # LMS: increase eta if update direction agrees with accuracy trend
            curr_acc = lc / n
            acc_improving = curr_acc > prev_acc
            direction = fv - mu_ca
            update_positive = np.dot(direction, prev_delta_mu[ci, ai_target]) > 0
            if acc_improving == update_positive:
                scale = min(ca_counts[ci, ai_target] * 0.01 + 1.0, 2.0)
            else:
                scale = max(1.0 - ca_counts[ci, ai_target] * 0.01, 0.1)
            prev_acc = curr_acc
            prev_delta_mu[ci, ai_target] = direction * 0.1

        scale = max(scale, 0.005)

        eff_fv = mu_ca + scale * (fv - mu_ca)
        scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
        ca_counts[ci, ai_target] += 1

        if n in [200, 500, 1000, 2000, 5000]:
            if n <= N:
                confs = np.array(all_confs)
                corrs = np.array(all_corrects)
                cp[n] = {
                    'acc': lc / n * 100,
                    'ece': compute_ece(confs, corrs),
                    'drift': (lc/n*100) - (cp.get(200, {}).get('acc', lc/n*100)) if n > 200 else 0,
                }

    return cp


def main():
    print("=" * 80)
    print("EXP-D3: GAIN FUNCTION COMPARISON")
    print("=" * 80)

    base_mu = get_base_centroids()
    gains = ["fixed_005", "inv_n", "inv_sqrt_n", "velocity_based",
             "override_based", "dual_rate", "lms_adaptive"]

    # Calibrated prior, N=5000
    print(f"\n  CALIBRATED PRIOR, N=5000:")
    print(f"  {'Gain':>16s}  {'Acc@2000':>8s}  {'ECE@2000':>8s}  {'Acc@5000':>8s}  "
          f"{'ECE@5000':>8s}  {'Drift':>7s}")
    print(f"  {'-' * 65}")

    for gain in gains:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_gain_test(seed, gain, gt, base_mu, 5000)
            runs.append(r)
        acc_2k = np.mean([r[2000]['acc'] for r in runs])
        ece_2k = np.mean([r[2000]['ece'] for r in runs])
        acc_5k = np.mean([r[5000]['acc'] for r in runs])
        ece_5k = np.mean([r[5000]['ece'] for r in runs])
        drift = np.mean([r[5000]['drift'] for r in runs if 'drift' in r.get(5000, {})])
        print(f"  {gain:>16s}  {acc_2k:>6.1f}%  {ece_2k:>8.4f}  "
              f"{acc_5k:>6.1f}%  {ece_5k:>8.4f}  {drift:>+5.1f}pp")

    # Lifecycle with shift
    print(f"\n  LIFECYCLE WITH SHIFT@1000, N=3000:")
    print(f"  {'Gain':>16s}  {'Pre@1000':>8s}  {'Post@1500':>9s}  {'Recovery':>8s}  {'Final@3000':>10s}")
    print(f"  {'-' * 55}")

    for gain in gains:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            gt_shifted = gt.copy()
            # Run pre-shift
            r_pre = run_gain_test(seed, gain, gt, base_mu, 1000)
            # Shift GT and continue (approximation: run full 3000 with shift at 1000)
            rng_shift = np.random.default_rng(seed + 3000)
            direction = rng_shift.normal(0, 1, gt.shape)
            direction = direction / np.linalg.norm(direction) * 0.50
            gt_shifted = gt + direction
            r_post = run_gain_test(seed, gain, gt_shifted, base_mu, 2000)
            runs.append({
                'pre': r_pre.get(1000, {}).get('acc', 0),
                'post': r_post.get(500, {}).get('acc', 0),
                'final': r_post.get(2000, {}).get('acc', 0),
            })
        pre = np.mean([r['pre'] for r in runs])
        post = np.mean([r['post'] for r in runs])
        final = np.mean([r['final'] for r in runs])
        print(f"  {gain:>16s}  {pre:>6.1f}%  {post:>7.1f}%  {post-pre:>+6.1f}pp  {final:>8.1f}%")

    print("\nDONE.")


if __name__ == "__main__":
    main()
