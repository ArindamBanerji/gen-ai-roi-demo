"""
EXP-R2: V-MULTIMODALITY-TEST
===============================
Do any (c,a) classes have multimodal factor distributions?
If yes, the single centroid averages over subtypes.

Run: cd backend && python scripts/exp_r2_multimodality.py
Time: ~15 min
"""

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_COLLECT = 5000


def dip_test_simple(data):
    """Simplified dip test: compare sorted data spacing to uniform."""
    if len(data) < 10:
        return 1.0  # not enough data
    sorted_d = np.sort(data)
    n = len(sorted_d)
    uniform = np.linspace(sorted_d[0], sorted_d[-1], n)
    max_diff = np.max(np.abs(sorted_d - uniform))
    # Approximate p-value (higher dip = more multimodal)
    dip_stat = max_diff / (sorted_d[-1] - sorted_d[0]) if sorted_d[-1] > sorted_d[0] else 0
    # Rough calibration: dip > 0.05 suggests multimodality
    return dip_stat


def main():
    print("=" * 80)
    print("EXP-R2: V-MULTIMODALITY-TEST")
    print("=" * 80)

    base_mu = get_base_centroids()

    all_results = []

    for seed in SEEDS[:3]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)

        # Collect factor vectors per (c,a)
        ca_factors = {(ci, ai): [] for ci in range(C) for ai in range(A)}

        for _ in range(N_COLLECT):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            ca_factors[(ci, ta)].append(fv.copy())

        print(f"\n  Seed {seed}:")
        print(f"  {'Category':>20s}  {'Action':>10s}  {'N':>5s}  {'Dip':>6s}  "
              f"{'Silh_k2':>7s}  {'VarRatio':>8s}  {'Multimodal?':>11s}")
        print(f"  {'-' * 75}")

        for ci in range(C):
            for ai in range(A):
                factors = ca_factors[(ci, ai)]
                if len(factors) < 30:
                    continue

                X = np.array(factors)
                n = len(X)

                # Dip test on first principal component
                centered = X - X.mean(axis=0)
                if centered.shape[0] > 1:
                    U, S, Vh = np.linalg.svd(centered, full_matrices=False)
                    pc1 = centered @ Vh[0]
                    dip = dip_test_simple(pc1)
                else:
                    dip = 0

                # Silhouette with k=2
                if n >= 10:
                    km = KMeans(n_clusters=2, random_state=seed, n_init=5)
                    labels = km.fit_predict(X)
                    if len(set(labels)) > 1:
                        silh = silhouette_score(X, labels)
                    else:
                        silh = -1
                else:
                    silh = -1

                # Variance ratio
                if n >= 10 and silh > -1:
                    c0 = X[labels == 0]
                    c1 = X[labels == 1]
                    if len(c0) > 1 and len(c1) > 1:
                        between = np.linalg.norm(c0.mean(axis=0) - c1.mean(axis=0))
                        within = (np.mean([np.linalg.norm(x - c0.mean(axis=0)) for x in c0]) +
                                  np.mean([np.linalg.norm(x - c1.mean(axis=0)) for x in c1])) / 2
                        var_ratio = between / max(within, 0.001)
                    else:
                        var_ratio = 0
                else:
                    var_ratio = 0

                multimodal = dip > 0.05 and silh > 0.30
                result = {
                    'ci': ci, 'ai': ai, 'n': n, 'dip': dip,
                    'silh': silh, 'var_ratio': var_ratio, 'multimodal': multimodal
                }
                all_results.append(result)

                print(f"  {CATEGORIES[ci]:>20s}  {ACTIONS[ai]:>10s}  {n:>5d}  "
                      f"{dip:>6.3f}  {silh:>7.3f}  {var_ratio:>8.2f}  "
                      f"{'YES' if multimodal else 'no'}")

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")

    multimodal_pairs = [r for r in all_results if r['multimodal']]
    print(f"  Multimodal (c,a) pairs: {len(multimodal_pairs)} / {len(all_results)}")

    if multimodal_pairs:
        print(f"  Multimodal pairs:")
        for r in multimodal_pairs:
            print(f"    {CATEGORIES[r['ci']]:>20s} × {ACTIONS[r['ai']]:>10s}: "
                  f"dip={r['dip']:.3f} silh={r['silh']:.3f}")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)
    print(f"Q1: Any (c,a) pairs show multimodality? "
          f"{'YES: ' + str(len(multimodal_pairs)) + ' pairs' if multimodal_pairs else 'NO'}")
    print(f"Q3: Would k=2 centroids help? "
          f"{'(see silhouette scores above)' if multimodal_pairs else 'N/A — single prototype adequate'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
