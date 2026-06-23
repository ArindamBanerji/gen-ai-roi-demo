"""
G7: BOOSTED PERTURBATION CONVERGENCE
=======================================
The perturbation theory framework predicts that multiple rounds
of bounded correction should converge:

Round 0: f_0 = centroid (Voronoi)
Round 1: f_1 = f_0 + delta_1 (trained on f_0 residuals, |delta_1| <= epsilon_1)
Round 2: f_2 = f_1 + delta_2 (trained on f_1 residuals, |delta_2| <= epsilon_2)
Round 3: f_3 = f_2 + delta_3 (trained on f_2 residuals, |delta_3| <= epsilon_3)

Tests:
1. Does accuracy improve with each round?
2. Do residual errors decrease? (convergence)
3. Does the total perturbation Sigma|delta| stay bounded?
4. What's the convergence RATE? (geometric? logarithmic?)

Run: cd backend && python scripts/exp_g7_boosting.py
Time: ~15 min
"""

import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_TRAIN = 2000
N_TEST = 500


def main():
    print("=" * 90)
    print("G7: BOOSTED PERTURBATION CONVERGENCE")
    print("Does multi-round correction converge?")
    print("=" * 90)

    base_mu = get_base_centroids()
    scorer = make_scorer(base_mu.copy())

    max_rounds = 5
    eps_schedule = [0.30, 0.20, 0.15, 0.10, 0.08]  # decreasing epsilon per round

    for seed in SEEDS[:3]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)

        # Collect data
        X_all, y_all, c_all = [], [], []
        for n in range(N_TRAIN + N_TEST):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            features = np.concatenate([fv, np.eye(C)[ci]])
            X_all.append(features)
            y_all.append(oa)
            c_all.append(ci)

        X_all = np.array(X_all)
        y_all = np.array(y_all)
        c_all = np.array(c_all)
        X_train, X_test = X_all[:N_TRAIN], X_all[N_TRAIN:]
        y_train, y_test = y_all[:N_TRAIN], y_all[N_TRAIN:]
        c_test = c_all[N_TRAIN:]

        print(f"\n  Seed {seed}:")
        print(f"  {'Round':>6s}  {'epsilon_max':>6s}  {'Acc':>6s}  {'Residual':>8s}  "
              f"{'Delta_round':>8s}  {'Cumulative':>10s}  {'BND_fix':>7s}  {'BND_cre':>7s}")
        print(f"  {'-' * 70}")

        # Round 0: centroid baseline
        current_preds_train = np.array([
            scorer.score(X_train[i, :D], int(np.argmax(X_train[i, D:]))).action_index
            for i in range(N_TRAIN)])
        current_preds_test = np.array([
            scorer.score(X_test[i, :D], int(np.argmax(X_test[i, D:]))).action_index
            for i in range(N_TEST)])

        # Compute gaps for bounding
        test_gaps = []
        for i in range(N_TEST):
            fv = X_test[i, :D]
            ci = int(np.argmax(X_test[i, D:]))
            result = scorer.score(fv, ci)
            probs = np.array(result.probabilities)
            sp = np.sort(probs)[::-1]
            test_gaps.append(sp[0] - sp[1])
        test_gaps = np.array(test_gaps)

        base_acc = accuracy_score(y_test, current_preds_test) * 100
        base_errors = (current_preds_test != y_test).sum()
        print(f"  {'0':>6s}  {'--':>6s}  {base_acc:>4.1f}%  {base_errors:>8d}  "
              f"{'--':>8s}  {'--':>10s}  {'--':>7s}  {'--':>7s}")

        # Accumulated corrections per test sample
        total_correction = np.zeros(N_TEST)  # magnitude of total perturbation
        final_preds = current_preds_test.copy()
        prev_acc = base_acc

        corrections = []  # list of (mlp, round_preds_for_train)

        for round_num in range(1, max_rounds + 1):
            eps_max = eps_schedule[round_num - 1] if round_num - 1 < len(eps_schedule) else 0.05

            # Current residual errors (what the system gets wrong NOW)
            residual_errors_train = (current_preds_train != y_train).sum()
            residual_errors_test = (final_preds != y_test).sum()

            if residual_errors_train < 5:
                print(f"  {round_num:>6d}  {eps_max:>6.2f}  -- (too few residual errors to train)")
                break

            # Build features for this round's MLP
            # Include previous round predictions as features
            feat_train = np.column_stack([X_train, np.eye(A)[current_preds_train]])
            feat_test = np.column_stack([X_test, np.eye(A)[final_preds]])

            # Train MLP on CURRENT residuals
            mlp = MLPClassifier(hidden_layer_sizes=(32,), max_iter=1000,
                                random_state=seed + round_num * 100)
            mlp.fit(feat_train, y_train)
            mlp_preds_test = mlp.predict(feat_test)
            mlp_preds_train = mlp.predict(feat_train)

            # Apply bounded correction
            round_preds = final_preds.copy()
            bnd_fixed = 0
            bnd_created = 0

            for i in range(N_TEST):
                if mlp_preds_test[i] != final_preds[i]:
                    # Check if this correction is within ε_max of remaining gap
                    # The "remaining gap" after previous corrections is the
                    # effective gap from the current predictions
                    # Use original centroid gap as proxy (conservative)
                    if test_gaps[i] <= eps_max + total_correction[i]:
                        old_correct = (final_preds[i] == y_test[i])
                        round_preds[i] = mlp_preds_test[i]
                        new_correct = (round_preds[i] == y_test[i])
                        total_correction[i] += eps_max
                        if not old_correct and new_correct:
                            bnd_fixed += 1
                        elif old_correct and not new_correct:
                            bnd_created += 1

            round_acc = accuracy_score(y_test, round_preds) * 100
            delta = round_acc - prev_acc
            cumulative = round_acc - base_acc
            new_residual = (round_preds != y_test).sum()

            print(f"  {round_num:>6d}  {eps_max:>6.2f}  {round_acc:>4.1f}%  {new_residual:>8d}  "
                  f"{delta:>+6.1f}pp  {cumulative:>+8.1f}pp  {bnd_fixed:>7d}  {bnd_created:>7d}")

            final_preds = round_preds.copy()
            prev_acc = round_acc

            # Update training predictions for next round
            round_train_preds = current_preds_train.copy()
            for i in range(N_TRAIN):
                if mlp_preds_train[i] != current_preds_train[i]:
                    round_train_preds[i] = mlp_preds_train[i]
            current_preds_train = round_train_preds

    # CONVERGENCE ANALYSIS
    print(f"\n{'=' * 90}")
    print("CONVERGENCE ANALYSIS")
    print("=" * 90)
    print("Does each round add less than the previous? (geometric convergence)")
    print("Does the residual error monotonically decrease?")
    print("Does the total perturbation stay bounded?")

    # Compare to single-round unbounded MLP
    print(f"\n  COMPARISON: Multi-round boosted vs single-round unbounded")
    for seed in SEEDS[:3]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)

        X_all, y_all, c_all = [], [], []
        for n in range(N_TRAIN + N_TEST):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            features = np.concatenate([fv, np.eye(C)[ci]])
            X_all.append(features)
            y_all.append(oa)
            c_all.append(ci)

        X_all = np.array(X_all)
        y_all = np.array(y_all)
        X_train, X_test = X_all[:N_TRAIN], X_all[N_TRAIN:]
        y_train, y_test = y_all[:N_TRAIN], y_all[N_TRAIN:]

        # Single MLP (unbounded)
        cent_train = np.array([scorer.score(X_train[i, :D],
                               int(np.argmax(X_train[i, D:]))).action_index
                               for i in range(N_TRAIN)])
        cent_test = np.array([scorer.score(X_test[i, :D],
                              int(np.argmax(X_test[i, D:]))).action_index
                              for i in range(N_TEST)])
        feat_tr = np.column_stack([X_train, np.eye(A)[cent_train]])
        feat_te = np.column_stack([X_test, np.eye(A)[cent_test]])

        mlp_single = MLPClassifier(hidden_layer_sizes=(32,), max_iter=1000,
                                    random_state=seed)
        mlp_single.fit(feat_tr, y_train)
        single_preds = mlp_single.predict(feat_te)
        single_acc = accuracy_score(y_test, single_preds) * 100
        base_acc = accuracy_score(y_test, cent_test) * 100

        print(f"    Seed {seed}: centroid={base_acc:.1f}% single_MLP={single_acc:.1f}% "
              f"(see boosted results above for comparison)")

    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("Q1: Does each round add positive improvement?")
    print("Q2: Do improvements decrease geometrically? (Delta_round2 < Delta_round1)")
    print("Q3: Does multi-round boosted match single-round unbounded?")
    print("Q4: What fraction of the MLP ceiling is captured by 3 rounds of bounded correction?")

    print("\nDONE.")


if __name__ == "__main__":
    main()
