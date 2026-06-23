"""
EXP-R1: V-BOUNDARY-LINEARITY
===============================
Are errors concentrated at decision boundaries?
Are those boundaries nonlinear (can't be captured by Voronoi)?

Run: cd backend && python scripts/exp_r1_boundary_linearity.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_CONVERGE = 2000
N_EVAL = 500


def main():
    print("=" * 80)
    print("EXP-R1: V-BOUNDARY-LINEARITY")
    print("=" * 80)

    base_mu = get_base_centroids()

    bins_all = {'DEEP_CORRECT': 0, 'BOUNDARY_CORRECT': 0,
                'BOUNDARY_WRONG': 0, 'DEEP_WRONG': 0}
    boundary_wrong_details = []
    deep_wrong_details = []
    total_eval = 0

    for seed in SEEDS:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        scorer = make_scorer(base_mu.copy())
        rng = np.random.default_rng(seed)

        # Converge
        for n in range(1, N_CONVERGE + 1):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            # Use static (no updates during convergence phase for clean measurement)

        # Evaluate next N_EVAL decisions
        for _ in range(N_EVAL):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)

            result = scorer.score(fv, ci)
            probs = np.array(result.probabilities)
            sorted_p = np.sort(probs)[::-1]
            gap = sorted_p[0] - sorted_p[1]
            correct = (result.action_index == ta)

            if correct and gap > 0.30:
                bins_all['DEEP_CORRECT'] += 1
            elif correct and gap <= 0.30:
                bins_all['BOUNDARY_CORRECT'] += 1
            elif not correct and gap <= 0.30:
                bins_all['BOUNDARY_WRONG'] += 1
                boundary_wrong_details.append({
                    'ci': ci, 'gt': ta, 'pred': result.action_index,
                    'fv': fv.copy(), 'gap': gap, 'seed': seed
                })
            else:
                bins_all['DEEP_WRONG'] += 1
                deep_wrong_details.append({
                    'ci': ci, 'gt': ta, 'pred': result.action_index,
                    'fv': fv.copy(), 'gap': gap, 'seed': seed
                })
            total_eval += 1

        print(f"  Seed {seed} done")

    # Distribution across bins
    print(f"\n{'=' * 80}")
    print("BIN DISTRIBUTION")
    print(f"{'=' * 80}")
    for bin_name, count in bins_all.items():
        pct = count / total_eval * 100
        print(f"  {bin_name:>20s}: {count:>5d} ({pct:.1f}%)")

    total_errors = bins_all['BOUNDARY_WRONG'] + bins_all['DEEP_WRONG']
    boundary_error_frac = bins_all['BOUNDARY_WRONG'] / max(total_errors, 1) * 100
    deep_error_frac = bins_all['DEEP_WRONG'] / max(total_errors, 1) * 100

    print(f"\n  Total errors: {total_errors} ({total_errors/total_eval*100:.1f}%)")
    print(f"  Boundary errors: {boundary_error_frac:.0f}% of all errors")
    print(f"  Deep errors: {deep_error_frac:.0f}% of all errors")

    # BOUNDARY_WRONG analysis
    print(f"\n{'=' * 80}")
    print("BOUNDARY_WRONG ANALYSIS ({} errors)".format(len(boundary_wrong_details)))
    print(f"{'=' * 80}")

    if boundary_wrong_details:
        # By category
        from collections import Counter
        cat_counts = Counter(d['ci'] for d in boundary_wrong_details)
        pair_counts = Counter((CATEGORIES[d['ci']], ACTIONS[d['gt']], ACTIONS[d['pred']])
                              for d in boundary_wrong_details)

        print(f"  By category:")
        for ci in range(C):
            print(f"    {CATEGORIES[ci]:>20s}: {cat_counts.get(ci, 0)}")

        print(f"\n  Top error pairs (cat, true->pred):")
        for (cat, true_a, pred_a), count in pair_counts.most_common(10):
            print(f"    {cat:>20s}: {true_a:>12s} -> {pred_a:>12s}: {count}")

        # Geometric structure: PCA of boundary-wrong factor vectors
        fvs = np.array([d['fv'] for d in boundary_wrong_details])
        if len(fvs) > 5:
            mean_fv = fvs.mean(axis=0)
            centered = fvs - mean_fv
            U, S, Vh = np.linalg.svd(centered, full_matrices=False)
            explained = S ** 2 / (S ** 2).sum()
            print(f"\n  PCA of boundary-wrong factor vectors:")
            print(f"    Explained variance: {np.round(explained[:4] * 100, 1)}")
            print(f"    Top 2 components explain {explained[:2].sum()*100:.0f}%")
            structure = "CLUSTERED" if explained[0] > 0.50 else "SPREAD"
            print(f"    Structure: {structure}")

    # DEEP_WRONG analysis
    print(f"\n{'=' * 80}")
    print("DEEP_WRONG ANALYSIS ({} errors)".format(len(deep_wrong_details)))
    print(f"{'=' * 80}")

    if deep_wrong_details:
        cat_counts_deep = Counter(d['ci'] for d in deep_wrong_details)
        print(f"  By category:")
        for ci in range(C):
            print(f"    {CATEGORIES[ci]:>20s}: {cat_counts_deep.get(ci, 0)}")

        pair_counts_deep = Counter((CATEGORIES[d['ci']], ACTIONS[d['gt']], ACTIONS[d['pred']])
                                   for d in deep_wrong_details)
        print(f"\n  Top error pairs:")
        for (cat, true_a, pred_a), count in pair_counts_deep.most_common(10):
            print(f"    {cat:>20s}: {true_a:>12s} -> {pred_a:>12s}: {count}")

        gaps = [d['gap'] for d in deep_wrong_details]
        print(f"\n  Gap distribution: mean={np.mean(gaps):.3f} max={np.max(gaps):.3f}")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)
    print(f"Q1: >70% of errors in BOUNDARY bins? {boundary_error_frac:.0f}% "
          f"{'YES' if boundary_error_frac > 70 else 'NO'}")
    print(f"Q2: >20% of errors in DEEP_WRONG? {deep_error_frac:.0f}% "
          f"{'YES' if deep_error_frac > 20 else 'NO'}")
    print(f"Q3: BOUNDARY_WRONG show geometric structure? "
          f"{'(see PCA above)' if boundary_wrong_details else 'N/A'}")
    print(f"Q4: DEEP_WRONG concentrated in specific categories? "
          f"{'(see distribution above)' if deep_wrong_details else 'N/A'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
