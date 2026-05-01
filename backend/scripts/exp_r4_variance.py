"""
EXP-R4: V-VARIANCE-INFORMATION
=================================
Does within-class variance carry decision information
that the centroid (mean) discards?

Run: cd backend && python scripts/exp_r4_variance.py
Time: ~10 min
"""

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_COLLECT = 3000
N_EVAL = 1000


def main():
    print("=" * 80)
    print("EXP-R4: V-VARIANCE-INFORMATION")
    print("=" * 80)

    base_mu = get_base_centroids()

    for seed in SEEDS[:3]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        scorer = make_scorer(base_mu.copy())
        rng = np.random.default_rng(seed)

        # Collect factor vectors per (c,a) to estimate variance
        ca_factors = {(ci, ai): [] for ci in range(C) for ai in range(A)}
        for _ in range(N_COLLECT):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            ca_factors[(ci, ta)].append(fv.copy())

        # Compute per-(c,a) statistics
        ca_mu = {}
        ca_sigma = {}
        for key, factors in ca_factors.items():
            if len(factors) >= 10:
                arr = np.array(factors)
                ca_mu[key] = arr.mean(axis=0)
                ca_sigma[key] = arr.std(axis=0) + 1e-8
            else:
                ca_mu[key] = base_mu[key[0], key[1]]
                ca_sigma[key] = np.ones(D) * 0.15

        # Evaluate: for each decision, compute features
        X_base = []  # distance only
        X_var = []   # distance + z_score + max_z + sigma_mean
        y = []

        for _ in range(N_EVAL):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            result = scorer.score(fv, ci)
            correct = 1 if result.action_index == ta else 0

            # Features for predicted action
            pred_a = result.action_index
            key = (ci, pred_a)
            mu = ca_mu.get(key, base_mu[ci, pred_a])
            sigma = ca_sigma.get(key, np.ones(D) * 0.15)

            distance = np.linalg.norm(fv - mu)
            z_scores = np.abs(fv - mu) / sigma
            max_z = np.max(z_scores)
            max_z_dim = int(np.argmax(z_scores))
            sigma_mean = np.mean(sigma)

            X_base.append([distance])
            X_var.append([distance, max_z, sigma_mean, np.mean(z_scores)])
            y.append(correct)

        X_base = np.array(X_base)
        X_var = np.array(X_var)
        y = np.array(y)

        if len(set(y)) < 2:
            print(f"  Seed {seed}: all same class, skipping")
            continue

        # Compare models
        try:
            auc_base = np.mean(cross_val_score(
                LogisticRegression(max_iter=500), X_base, y, cv=5, scoring='roc_auc'))
            auc_var = np.mean(cross_val_score(
                LogisticRegression(max_iter=500), X_var, y, cv=5, scoring='roc_auc'))
        except Exception:
            auc_base, auc_var = 0.5, 0.5

        print(f"\n  Seed {seed}:")
        print(f"    AUC(distance only): {auc_base:.4f}")
        print(f"    AUC(distance + variance): {auc_var:.4f}")
        print(f"    Improvement: {auc_var - auc_base:+.4f}")

        # Error concentration at high z-score
        errors = y == 0
        if errors.sum() > 0:
            z_errors = X_var[errors, 1]  # max_z for errors
            z_correct = X_var[~errors, 1]
            frac_high_z = (z_errors > 2.0).mean() * 100
            print(f"    Errors with max_z > 2: {frac_high_z:.0f}%")
            print(f"    Mean max_z: errors={z_errors.mean():.2f} correct={z_correct.mean():.2f}")

        # Per-dimension sigma variation
        all_sigmas = [ca_sigma[k] for k in ca_sigma if len(ca_factors[k]) >= 10]
        if all_sigmas:
            mean_sigma = np.mean(all_sigmas, axis=0)
            cv_sigma = np.std(mean_sigma) / np.mean(mean_sigma)
            print(f"    Per-dimension mean sigma: {np.round(mean_sigma, 4)}")
            print(f"    CV(sigma across dims): {cv_sigma:.3f}")
            print(f"    Highest sigma dimension: {int(np.argmax(mean_sigma))}")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)
    print(f"Q1: z_score predicts errors better than distance? (see ΔAUC above)")
    print(f"Q3: Per-dimension sigma varies significantly? (see CV above)")

    print("\nDONE.")


if __name__ == "__main__":
    main()
