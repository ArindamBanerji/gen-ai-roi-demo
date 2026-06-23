"""
EXP-F5: V-OBSERVABILITY-MATRIX
=================================
For each available feedback signal, compute MI with GT direction.
Is the plant observable in magnitude? In direction?

Run: cd backend && python scripts/exp_f5_observability.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_RUN = 2000
N_EVAL = 500


def discretize(x, n_bins=10):
    """Discretize continuous values for MI computation."""
    percentiles = np.linspace(0, 100, n_bins + 1)
    bins = np.percentile(x, percentiles)
    bins[-1] += 1e-10
    return np.digitize(x, bins[:-1]) - 1


def mutual_information(x, y, n_bins=10):
    """Compute MI between two continuous variables via discretization."""
    x_d = discretize(x, n_bins)
    y_d = discretize(y, n_bins)

    # Joint distribution
    joint = np.zeros((n_bins, n_bins))
    for i in range(len(x)):
        xi = min(x_d[i], n_bins - 1)
        yi = min(y_d[i], n_bins - 1)
        joint[xi, yi] += 1
    joint /= joint.sum()

    # Marginals
    px = joint.sum(axis=1)
    py = joint.sum(axis=0)

    # MI
    mi = 0.0
    for i in range(n_bins):
        for j in range(n_bins):
            if joint[i, j] > 0 and px[i] > 0 and py[j] > 0:
                mi += joint[i, j] * np.log2(joint[i, j] / (px[i] * py[j]))
    return mi


def main():
    print("=" * 90)
    print("EXP-F5: V-OBSERVABILITY-MATRIX")
    print("=" * 90)

    base_mu = get_base_centroids()

    for seed in SEEDS[:3]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        scorer = make_scorer(base_mu.copy())
        rng = np.random.default_rng(seed + 50000)

        # Collect signals and GT for evaluation decisions
        signals = {
            'confidence': [],
            'entropy': [],
            'conf_gap': [],
            'distance': [],
            'override': [],
        }
        gt_magnitudes = []
        gt_directions = []  # cosine of GT direction with each factor axis

        for _ in range(N_EVAL):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            result = scorer.score(fv, ci)

            # Signals
            probs = np.array(result.probabilities)
            sorted_p = np.sort(probs)[::-1]

            signals['confidence'].append(result.confidence)
            entropy = -np.sum(probs * np.log(probs + 1e-10))
            signals['entropy'].append(entropy)
            signals['conf_gap'].append(sorted_p[0] - sorted_p[1])
            signals['distance'].append(np.linalg.norm(fv - scorer.centroids[ci, result.action_index]))
            signals['override'].append(0 if result.action_index == oa else 1)

            # GT direction for this (c, a)
            ai = result.action_index
            g = gt[ci, ai] - scorer.centroids[ci, ai]
            gt_magnitudes.append(np.linalg.norm(g))

            # Direction: cosine with each axis
            if np.linalg.norm(g) > 1e-10:
                g_norm = g / np.linalg.norm(g)
                gt_directions.append(g_norm)
            else:
                gt_directions.append(np.zeros(D))

        gt_magnitudes = np.array(gt_magnitudes)
        gt_directions = np.array(gt_directions)

        print(f"\n  Seed {seed}:")

        # MI with magnitude
        print(f"\n  MI(signal, |g|) -- can signals detect ERROR MAGNITUDE?")
        print(f"  {'Signal':>15s}  {'MI(magnitude)':>13s}")
        print(f"  {'-' * 30}")
        for name in signals:
            sig = np.array(signals[name])
            if len(set(sig)) < 3:
                mi = 0.0
            else:
                mi = mutual_information(sig, gt_magnitudes)
            print(f"  {name:>15s}  {mi:>11.4f}")

        # MI with direction (per-dimension)
        print(f"\n  MI(signal, g_i) -- can signals detect ERROR DIRECTION per dimension?")
        print(f"  {'Signal':>15s}", end="")
        for d in range(D):
            print(f"  {'dim_'+str(d):>7s}", end="")
        print(f"  {'mean':>7s}")
        print(f"  {'-' * 70}")

        for name in signals:
            sig = np.array(signals[name])
            print(f"  {name:>15s}", end="")
            mis = []
            for d in range(D):
                g_d = gt_directions[:, d]
                if len(set(sig)) < 3 or np.std(g_d) < 1e-10:
                    mi = 0.0
                else:
                    mi = mutual_information(sig, g_d)
                mis.append(mi)
                print(f"  {mi:>7.4f}", end="")
            print(f"  {np.mean(mis):>7.4f}")

        # Magnitude vs direction observability
        print(f"\n  SUMMARY:")
        mag_mis = []
        dir_mis = []
        for name in signals:
            sig = np.array(signals[name])
            if len(set(sig)) >= 3:
                mag_mis.append(mutual_information(sig, gt_magnitudes))
                d_mi = np.mean([mutual_information(sig, gt_directions[:, d])
                                for d in range(D) if np.std(gt_directions[:, d]) > 1e-10])
                dir_mis.append(d_mi)
        print(f"    Best magnitude MI: {max(mag_mis):.4f}")
        print(f"    Best direction MI: {max(dir_mis):.4f}")
        print(f"    Magnitude MORE observable? {'YES' if max(mag_mis) > max(dir_mis) else 'NO'}")

    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("Q1: Any signal MI > 0.1 with GT direction?")
    print("Q2: Is magnitude more observable than direction?")
    print("Q3: Is the best signal the same for all seeds?")

    print("\nDONE.")


if __name__ == "__main__":
    main()
