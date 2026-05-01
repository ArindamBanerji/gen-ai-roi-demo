"""
EXP-R3: V-FACTOR-INTERACTION
===============================
Do factor interactions (f_i × f_j) predict errors that
individual factors can't?

Run: cd backend && python scripts/exp_r3_interaction.py
Time: ~15 min
"""

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_CONVERGE = 1500
N_EVAL = 500


def main():
    print("=" * 80)
    print("EXP-R3: V-FACTOR-INTERACTION")
    print("=" * 80)

    base_mu = get_base_centroids()
    all_aucs = {'linear': [], 'interaction': [], 'quadratic': []}

    for seed in SEEDS:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        scorer = make_scorer(base_mu.copy())
        rng = np.random.default_rng(seed)

        # Skip convergence phase
        for _ in range(N_CONVERGE):
            rng.random()  # advance RNG

        # Collect evaluation decisions
        X_linear = []
        y = []

        for _ in range(N_EVAL):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)

            result = scorer.score(fv, ci)
            correct = 1 if result.action_index == ta else 0

            X_linear.append(fv.tolist() + [ci])
            y.append(correct)

        X_lin = np.array(X_linear)
        y = np.array(y)

        if len(set(y)) < 2:
            print(f"  Seed {seed}: all same class, skipping")
            continue

        # Model 1: Linear (f only)
        X1 = X_lin

        # Model 2: + interactions (f_i × f_j)
        interactions = []
        for i in range(D):
            for j in range(i + 1, D):
                interactions.append(X_lin[:, i] * X_lin[:, j])
        X2 = np.column_stack([X1] + interactions)

        # Model 3: + quadratic (f_i²)
        quadratics = [X_lin[:, i] ** 2 for i in range(D)]
        X3 = np.column_stack([X2] + quadratics)

        # Cross-validated AUC
        for name, X in [("linear", X1), ("interaction", X2), ("quadratic", X3)]:
            try:
                lr = LogisticRegression(max_iter=1000, random_state=seed)
                scores = cross_val_score(lr, X, y, cv=5, scoring='roc_auc')
                auc = np.mean(scores)
                all_aucs[name].append(auc)
            except Exception as e:
                all_aucs[name].append(0.5)

        print(f"  Seed {seed}: linear={all_aucs['linear'][-1]:.4f} "
              f"interaction={all_aucs['interaction'][-1]:.4f} "
              f"quadratic={all_aucs['quadratic'][-1]:.4f}")

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY (mean AUC across seeds)")
    print(f"{'=' * 80}")
    for name in ['linear', 'interaction', 'quadratic']:
        aucs = all_aucs[name]
        if aucs:
            print(f"  {name:>15s}: AUC = {np.mean(aucs):.4f} ± {np.std(aucs):.4f}")

    if all_aucs['linear'] and all_aucs['interaction']:
        delta_int = np.mean(all_aucs['interaction']) - np.mean(all_aucs['linear'])
        delta_quad = np.mean(all_aucs['quadratic']) - np.mean(all_aucs['interaction'])
        print(f"\n  Interaction improvement: ΔAUC = {delta_int:+.4f}")
        print(f"  Quadratic improvement:  ΔAUC = {delta_quad:+.4f}")

    # Identify strongest interaction
    print(f"\n  Top interaction pairs (from last seed):")
    if len(X2) > 0:
        try:
            lr = LogisticRegression(max_iter=1000)
            lr.fit(X2, y)
            coefs = lr.coef_[0]
            # Interaction coefficients start after D+1 (linear + category)
            int_start = D + 1
            int_pairs = []
            idx = int_start
            for i in range(D):
                for j in range(i + 1, D):
                    int_pairs.append((i, j, abs(coefs[idx])))
                    idx += 1
            int_pairs.sort(key=lambda x: -x[2])
            for i, j, coef in int_pairs[:5]:
                print(f"    f{i} × f{j}: |coef| = {coef:.4f}")
        except Exception:
            pass

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)
    if all_aucs['linear'] and all_aucs['interaction']:
        print(f"Q1: Interactions improve AUC > 0.02? ΔAUC={delta_int:+.4f} "
              f"{'YES' if delta_int > 0.02 else 'NO'}")
        print(f"Q2: Quadratic improves over interaction? ΔAUC={delta_quad:+.4f} "
              f"{'YES' if delta_quad > 0.02 else 'NO'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
