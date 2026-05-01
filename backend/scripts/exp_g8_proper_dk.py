"""
G8: PROPERLY CALIBRATED DK
=============================
F3-F6 showed DK "doesn't help." But DK weights were learned by
random perturbation with 100 iterations — a crude optimization.

The DK scoring function s = -Σ wᵢ(xᵢ-μᵢ)² produces QUADRIC
boundaries when different actions have different weights.
This IS curvature — the representation has the capacity.
The question is whether PROPER calibration unlocks it.

Tests:
1. DK with gradient-based calibration (not random search)
2. Per-(c,a) DK weights (not shared weights)
3. Full-covariance (Mahalanobis) as upper bound
4. Compare: properly-calibrated DK vs MLP

If proper DK captures 2-3pp of the 4.5pp MLP gap:
  → DK IS the right intermediate term
  → The series IS f₀ + δ₁(σ²) + δ₂(MLP)
  → F3-F6 were testing the calibration, not the representation

Run: cd backend && python scripts/exp_g8_proper_dk.py
Time: ~20 min
"""

import numpy as np
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_TRAIN = 2000
N_TEST = 500


def score_dk_per_ca(fv, ci, centroids, weights_per_ca):
    """Score with per-(c,a) DK weights — each action has its own axis weighting."""
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        w = weights_per_ca[ci, ai]  # shape (D,)
        sims.append(-np.sum(w * diff ** 2))
    sims = np.array(sims)
    return int(np.argmax(sims))


def calibrate_dk_gradient(X_train, y_train, c_train, centroids, n_iter=500, lr=0.01):
    """Gradient-based DK weight calibration using finite differences."""
    weights = np.ones((C, A, D))
    best_weights = weights.copy()
    best_acc = 0

    for iteration in range(n_iter):
        # Evaluate current accuracy
        correct = 0
        for i in range(len(X_train)):
            fv = X_train[i, :D]
            ci = c_train[i]
            pred = score_dk_per_ca(fv, ci, centroids, weights)
            if pred == y_train[i]:
                correct += 1
        acc = correct / len(X_train)

        if acc > best_acc:
            best_acc = acc
            best_weights = weights.copy()

        # Compute gradient via finite differences for each weight
        grad = np.zeros_like(weights)
        eps = 0.05
        for ci in range(C):
            for ai in range(A):
                for di in range(D):
                    weights_plus = weights.copy()
                    weights_plus[ci, ai, di] += eps
                    weights_minus = weights.copy()
                    weights_minus[ci, ai, di] -= eps

                    # Subsample for speed
                    mask = c_train == ci
                    if mask.sum() < 10:
                        continue
                    indices = np.where(mask)[0][:200]

                    acc_plus = sum(1 for i in indices
                                  if score_dk_per_ca(X_train[i, :D], ci, centroids,
                                                     weights_plus) == y_train[i]) / len(indices)
                    acc_minus = sum(1 for i in indices
                                   if score_dk_per_ca(X_train[i, :D], ci, centroids,
                                                      weights_minus) == y_train[i]) / len(indices)

                    grad[ci, ai, di] = (acc_plus - acc_minus) / (2 * eps)

        # Update weights
        weights += lr * grad
        weights = np.clip(weights, 0.01, 100.0)

        if iteration % 100 == 0:
            print(f"      Iter {iteration}: acc={acc*100:.1f}% best={best_acc*100:.1f}%")

    return best_weights


def calibrate_dk_coordinate(X_train, y_train, c_train, centroids, n_rounds=10):
    """Coordinate descent DK calibration — optimize one weight at a time."""
    weights = np.ones((C, A, D))

    for round_num in range(n_rounds):
        improved = False
        for ci in range(C):
            for ai in range(A):
                for di in range(D):
                    # Try several values for this one weight
                    best_w = weights[ci, ai, di]
                    mask = c_train == ci
                    if mask.sum() < 10:
                        continue
                    indices = np.where(mask)[0]

                    best_local_acc = sum(1 for i in indices
                                         if score_dk_per_ca(X_train[i, :D], ci, centroids,
                                                            weights) == y_train[i]) / len(indices)

                    for w_trial in [0.1, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]:
                        weights_trial = weights.copy()
                        weights_trial[ci, ai, di] = w_trial
                        trial_acc = sum(1 for i in indices
                                        if score_dk_per_ca(X_train[i, :D], ci, centroids,
                                                           weights_trial) == y_train[i]) / len(indices)
                        if trial_acc > best_local_acc:
                            best_local_acc = trial_acc
                            best_w = w_trial
                            improved = True

                    weights[ci, ai, di] = best_w

        # Evaluate full accuracy
        correct = sum(1 for i in range(len(X_train))
                      if score_dk_per_ca(X_train[i, :D], c_train[i], centroids,
                                         weights) == y_train[i])
        if round_num % 3 == 0:
            print(f"      Round {round_num}: acc={correct/len(X_train)*100:.1f}%")

        if not improved:
            break

    return weights


def main():
    print("=" * 90)
    print("G8: PROPERLY CALIBRATED DK")
    print("Does gradient-based DK capture curvature that random search missed?")
    print("=" * 90)

    base_mu = get_base_centroids()
    scorer = make_scorer(base_mu.copy())

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
        c_train, c_test = c_all[:N_TRAIN], c_all[N_TRAIN:]

        print(f"\n  Seed {seed}:")

        # 1. Centroid baseline
        cent_preds = np.array([scorer.score(X_test[i, :D], c_test[i]).action_index
                               for i in range(N_TEST)])
        cent_acc = accuracy_score(y_test, cent_preds) * 100

        # 2. DK with random search (F3-F6 approach)
        print(f"    Calibrating DK (random search, 100 iter)...")
        from exp_shared import get_base_centroids as gbc
        weights_random = np.ones((C, A, D))
        best_random_acc = 0
        rng_r = np.random.default_rng(42)
        for _ in range(100):
            trial = weights_random + rng_r.normal(0, 0.1, weights_random.shape)
            trial = np.clip(trial, 0.1, 10.0)
            correct = sum(1 for i in range(N_TRAIN)
                          if score_dk_per_ca(X_train[i, :D], c_train[i], base_mu,
                                             trial) == y_train[i])
            if correct / N_TRAIN > best_random_acc:
                best_random_acc = correct / N_TRAIN
                weights_random = trial.copy()
        dk_random_preds = np.array([score_dk_per_ca(X_test[i, :D], c_test[i], base_mu,
                                                     weights_random) for i in range(N_TEST)])
        dk_random_acc = accuracy_score(y_test, dk_random_preds) * 100

        # 3. DK with coordinate descent
        print(f"    Calibrating DK (coordinate descent)...")
        weights_coord = calibrate_dk_coordinate(X_train, y_train, c_train, base_mu, n_rounds=6)
        dk_coord_preds = np.array([score_dk_per_ca(X_test[i, :D], c_test[i], base_mu,
                                                    weights_coord) for i in range(N_TEST)])
        dk_coord_acc = accuracy_score(y_test, dk_coord_preds) * 100

        # 4. QDA (full-covariance Gaussian — maximum quadric capacity)
        try:
            qda = QuadraticDiscriminantAnalysis()
            qda.fit(X_train, y_train)
            qda_preds = qda.predict(X_test)
            qda_acc = accuracy_score(y_test, qda_preds) * 100
        except Exception:
            qda_acc = 0

        # 5. MLP (from R5 — discriminative baseline)
        mlp = MLPClassifier(hidden_layer_sizes=(32,), max_iter=1000, random_state=seed)
        mlp.fit(X_train, y_train)
        mlp_preds = mlp.predict(X_test)
        mlp_acc = accuracy_score(y_test, mlp_preds) * 100

        # 6. DK + MLP (DK as base, MLP as correction)
        dk_preds_train = np.array([score_dk_per_ca(X_train[i, :D], c_train[i], base_mu,
                                                    weights_coord) for i in range(N_TRAIN)])
        feat_train = np.column_stack([X_train, np.eye(A)[dk_preds_train]])
        feat_test = np.column_stack([X_test, np.eye(A)[dk_coord_preds]])
        mlp_on_dk = MLPClassifier(hidden_layer_sizes=(32,), max_iter=1000, random_state=seed)
        mlp_on_dk.fit(feat_train, y_train)
        dk_mlp_preds = mlp_on_dk.predict(feat_test)
        dk_mlp_acc = accuracy_score(y_test, dk_mlp_preds) * 100

        # 7. MLP on centroid (for comparison)
        cent_preds_train = np.array([scorer.score(X_train[i, :D], c_train[i]).action_index
                                     for i in range(N_TRAIN)])
        feat_tr_c = np.column_stack([X_train, np.eye(A)[cent_preds_train]])
        feat_te_c = np.column_stack([X_test, np.eye(A)[cent_preds]])
        mlp_on_cent = MLPClassifier(hidden_layer_sizes=(32,), max_iter=1000, random_state=seed)
        mlp_on_cent.fit(feat_tr_c, y_train)
        cent_mlp_preds = mlp_on_cent.predict(feat_te_c)
        cent_mlp_acc = accuracy_score(y_test, cent_mlp_preds) * 100

        # Results
        print(f"\n    RESULTS:")
        print(f"    {'Method':>25s}  {'Acc':>6s}  {'Δ vs centroid':>13s}  {'Params':>8s}  {'Boundary':>12s}")
        print(f"    {'-' * 70}")
        results = [
            ("Centroid (f₀)", cent_acc, 144, "hyperplane"),
            ("DK random (F3-F6)", dk_random_acc, 288, "quadric*"),
            ("DK coordinate descent", dk_coord_acc, 288, "quadric"),
            ("QDA (full covariance)", qda_acc, 648, "quadric"),
            ("MLP (discriminative)", mlp_acc, 700, "arbitrary"),
            ("Centroid + MLP", cent_mlp_acc, 844, "arbitrary"),
            ("DK_coord + MLP", dk_mlp_acc, 988, "arbitrary"),
        ]
        for name, acc, params, boundary in results:
            print(f"    {name:>25s}  {acc:>4.1f}%  {acc-cent_acc:>+11.1f}pp  {params:>8d}  {boundary:>12s}")

        # Weight analysis
        print(f"\n    DK WEIGHT ANALYSIS (coordinate descent):")
        for ci in range(min(C, 3)):
            print(f"      {CATEGORIES[ci]:>20s}:", end="")
            for ai in range(A):
                w = weights_coord[ci, ai]
                print(f"  {ACTIONS[ai][:4]}=[{','.join(f'{v:.1f}' for v in w)}]", end="")
            print()

    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("Q1: Does properly-calibrated DK beat random-search DK by >1pp?")
    print("Q2: Does DK_coord capture >1pp of the MLP's 4.5pp gap?")
    print("Q3: Does QDA (full covariance) beat DK_coord? (quadric capacity)")
    print("Q4: Does DK_coord + MLP beat Centroid + MLP? (DK helps MLP)")
    print("Q5: Are DK weights category-dependent? (different axes matter for different categories)")

    print("\nDONE.")


if __name__ == "__main__":
    main()
