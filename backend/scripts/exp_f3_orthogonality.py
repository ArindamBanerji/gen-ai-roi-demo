"""
EXP-F3: V-ORTHOGONALITY-TEST
===============================
Direct test: are the error classes addressed by f₀, δ₁, δ₂ disjoint?

Tests error overlap between:
  A = errors of centroid (f₀)
  B = errors of centroid + DK (f₀ + δ₁)
  C = errors of centroid + DK + MLP (f₀ + δ₁ + δ₂)

Run: cd backend && python scripts/exp_f3_orthogonality.py
Time: ~20 min
"""

import numpy as np
from sklearn.neural_network import MLPClassifier
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_TRAIN = 1500
N_TEST = 500


def score_dk(fv, ci, centroids, weights):
    """Score with DiagonalKernel (weighted distance)."""
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        weighted_dist = np.sum(weights[ci, ai] * diff ** 2)
        sims.append(-weighted_dist)
    sims = np.array(sims, dtype=np.float64)
    return int(np.argmax(sims))


def learn_dk_weights(X_train, y_train, c_train, centroids, n_iter=50):
    """Learn per-(c,a,d) weights by gradient-free optimization."""
    weights = np.ones((C, A, D))
    best_weights = weights.copy()
    best_acc = 0

    rng = np.random.default_rng(42)
    for iteration in range(n_iter):
        # Random perturbation
        trial = weights + rng.normal(0, 0.1, weights.shape)
        trial = np.clip(trial, 0.1, 10.0)

        correct = 0
        for i in range(len(X_train)):
            fv = X_train[i, :D]
            ci = c_train[i]
            pred = score_dk(fv, ci, centroids, trial)
            if pred == y_train[i]:
                correct += 1
        acc = correct / len(X_train)

        if acc > best_acc:
            best_acc = acc
            best_weights = trial.copy()
            weights = trial.copy()

    return best_weights


def main():
    print("=" * 90)
    print("EXP-F3: V-ORTHOGONALITY-TEST")
    print("=" * 90)

    base_mu = get_base_centroids()

    for seed in SEEDS[:3]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)

        # Collect data
        X_all, y_all, c_all = [], [], []
        for n in range(1, N_TRAIN + N_TEST + 1):
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
        c_train, c_test = c_all[:N_TRAIN], c_all[N_TRAIN:]

        # ── CLASSIFIER A: Centroid (f₀) ──
        scorer = make_scorer(base_mu.copy())
        preds_f0 = []
        for i in range(N_TEST):
            fv = X_test[i, :D]
            ci = c_test[i]
            result = scorer.score(fv, ci)
            preds_f0.append(result.action_index)
        preds_f0 = np.array(preds_f0)
        errors_A = set(np.where(preds_f0 != y_test)[0])

        # ── CLASSIFIER B: DK (f₀ + δ₁) ──
        dk_weights = learn_dk_weights(X_train, y_train, c_train, base_mu, n_iter=100)
        preds_dk = []
        for i in range(N_TEST):
            fv = X_test[i, :D]
            ci = c_test[i]
            preds_dk.append(score_dk(fv, ci, base_mu, dk_weights))
        preds_dk = np.array(preds_dk)
        errors_B = set(np.where(preds_dk != y_test)[0])

        # ── CLASSIFIER C: DK + MLP residual (f₀ + δ₁ + δ₂) ──
        # Train MLP on DK residuals
        dk_preds_train = []
        for i in range(N_TRAIN):
            fv = X_train[i, :D]
            ci = c_train[i]
            dk_preds_train.append(score_dk(fv, ci, base_mu, dk_weights))
        dk_preds_train = np.array(dk_preds_train)

        # MLP features: factor vector + category one-hot + DK prediction one-hot
        mlp_features_train = np.column_stack([
            X_train, np.eye(A)[dk_preds_train]
        ])
        mlp_features_test = np.column_stack([
            X_test, np.eye(A)[preds_dk]
        ])

        mlp = MLPClassifier(hidden_layer_sizes=(32,), max_iter=1000, random_state=seed)
        mlp.fit(mlp_features_train, y_train)
        preds_mlp = mlp.predict(mlp_features_test)
        errors_C = set(np.where(preds_mlp != y_test)[0])

        # ── OVERLAP ANALYSIS ──
        print(f"\n  Seed {seed}:")
        print(f"    |A| (centroid errors):   {len(errors_A)}")
        print(f"    |B| (DK errors):         {len(errors_B)}")
        print(f"    |C| (DK+MLP errors):     {len(errors_C)}")

        if len(errors_A) > 0:
            overlap_AB = len(errors_A & errors_B) / len(errors_A)
            unique_to_A = len(errors_A - errors_B) / len(errors_A)
            new_in_B = len(errors_B - errors_A) / max(len(errors_B), 1)
            print(f"    overlap(A,B):           {overlap_AB:.2f} ({len(errors_A & errors_B)} shared)")
            print(f"    unique_to_A (DK fixes): {unique_to_A:.2f} ({len(errors_A - errors_B)} fixed)")
            print(f"    new_in_B (DK creates):  {new_in_B:.2f} ({len(errors_B - errors_A)} new)")

        if len(errors_B) > 0:
            overlap_BC = len(errors_B & errors_C) / len(errors_B)
            unique_to_B = len(errors_B - errors_C) / len(errors_B)
            new_in_C = len(errors_C - errors_B) / max(len(errors_C), 1)
            print(f"    overlap(B,C):           {overlap_BC:.2f} ({len(errors_B & errors_C)} shared)")
            print(f"    unique_to_B (RL fixes): {unique_to_B:.2f} ({len(errors_B - errors_C)} fixed)")
            print(f"    new_in_C (RL creates):  {new_in_C:.2f} ({len(errors_C - errors_B)} new)")

        # Irreducible errors (in ALL three)
        irreducible = errors_A & errors_B & errors_C
        print(f"    irreducible (A∩B∩C):    {len(irreducible)}")

        # Accuracy
        acc_A = (1 - len(errors_A) / N_TEST) * 100
        acc_B = (1 - len(errors_B) / N_TEST) * 100
        acc_C = (1 - len(errors_C) / N_TEST) * 100
        print(f"    Accuracy: f₀={acc_A:.1f}% → f₀+δ₁={acc_B:.1f}% → f₀+δ₁+δ₂={acc_C:.1f}%")

        # Geometric analysis of fixed vs inherited errors
        if len(errors_A - errors_B) > 5 and len(errors_A & errors_B) > 5:
            fixed = list(errors_A - errors_B)
            inherited = list(errors_A & errors_B)
            fixed_dists = [np.linalg.norm(X_test[i, :D] - base_mu[c_test[i], y_test[i]])
                           for i in fixed]
            inherited_dists = [np.linalg.norm(X_test[i, :D] - base_mu[c_test[i], y_test[i]])
                               for i in inherited]
            print(f"    Fixed errors mean dist:     {np.mean(fixed_dists):.4f}")
            print(f"    Inherited errors mean dist: {np.mean(inherited_dists):.4f}")

    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("Q1: overlap(A,B) > 0.80? (DK inherits most centroid errors)")
    print("Q2: new_in_B / |B| < 0.10? (DK doesn't create many new errors)")
    print("Q3: Are there irreducible errors no term fixes?")
    print("Q4: Do fixed errors have different geometry than inherited?")

    print("\nDONE.")


if __name__ == "__main__":
    main()
