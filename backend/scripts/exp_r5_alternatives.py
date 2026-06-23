"""
EXP-R5: V-CENTROID-VS-ALTERNATIVES
=====================================
THE definitive test: how much accuracy do centroids leave on the table
compared to more expressive classifiers on the SAME data?

Run: cd backend && python scripts/exp_r5_alternatives.py
Time: ~20 min
"""

import numpy as np
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, log_loss
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_TRAIN = 1500
N_TEST = 500


def compute_ece(probs, y_true, n_bins=10):
    bounds = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    confs = np.max(probs, axis=1)
    preds = np.argmax(probs, axis=1)
    corrects = (preds == y_true).astype(float)
    total = len(confs)
    for i in range(n_bins):
        lo, hi = bounds[i], bounds[i + 1]
        mask = (confs >= lo) & (confs < hi) if i < n_bins - 1 else (confs >= lo) & (confs <= hi)
        if mask.sum() == 0:
            continue
        ece += (mask.sum() / total) * abs(corrects[mask].mean() - confs[mask].mean())
    return ece


def main():
    print("=" * 80)
    print("EXP-R5: V-CENTROID-VS-ALTERNATIVES")
    print("The definitive representational limit test")
    print("=" * 80)

    base_mu = get_base_centroids()

    all_results = {name: {'acc': [], 'ece': []} for name in
                   ["centroid", "knn_5", "logistic", "random_forest", "mlp_small"]}
    per_cat_results = {name: {ci: [] for ci in range(C)} for name in all_results}

    for seed in SEEDS:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)

        # Collect training data
        X_train, y_train, c_train = [], [], []
        X_test, y_test, c_test = [], [], []

        for n in range(1, N_TRAIN + N_TEST + 1):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)

            # Include category as feature (one-hot)
            features = np.concatenate([fv, np.eye(C)[ci]])

            if n <= N_TRAIN:
                X_train.append(features)
                y_train.append(oa)
                c_train.append(ci)
            else:
                X_test.append(features)
                y_test.append(oa)
                c_test.append(ci)

        X_train = np.array(X_train)
        y_train = np.array(y_train)
        X_test = np.array(X_test)
        y_test = np.array(y_test)
        c_test = np.array(c_test)

        # CENTROID: use production scorer
        scorer = make_scorer(base_mu.copy())
        centroid_preds = []
        centroid_probs = []
        for i in range(len(X_test)):
            fv = X_test[i, :D]
            ci = int(np.argmax(X_test[i, D:]))
            result = scorer.score(fv, ci)
            centroid_preds.append(result.action_index)
            centroid_probs.append(result.probabilities)
        centroid_acc = accuracy_score(y_test, centroid_preds)
        centroid_ece = compute_ece(np.array(centroid_probs), y_test)
        all_results["centroid"]['acc'].append(centroid_acc * 100)
        all_results["centroid"]['ece'].append(centroid_ece)
        for ci in range(C):
            mask = c_test == ci
            if mask.sum() > 0:
                cat_acc = accuracy_score(y_test[mask], np.array(centroid_preds)[mask])
                per_cat_results["centroid"][ci].append(cat_acc * 100)

        # Other classifiers
        classifiers = {
            "knn_5": KNeighborsClassifier(n_neighbors=5),
            "logistic": LogisticRegression(max_iter=1000, random_state=seed),
            "random_forest": RandomForestClassifier(n_estimators=100, random_state=seed),
            "mlp_small": MLPClassifier(hidden_layer_sizes=(32,), max_iter=500,
                                       random_state=seed),
        }

        for name, clf in classifiers.items():
            try:
                clf.fit(X_train, y_train)
                preds = clf.predict(X_test)
                probs = clf.predict_proba(X_test)

                # Ensure probs has all A columns
                if probs.shape[1] < A:
                    full_probs = np.zeros((len(X_test), A))
                    for i, c in enumerate(clf.classes_):
                        full_probs[:, c] = probs[:, i]
                    probs = full_probs

                acc = accuracy_score(y_test, preds) * 100
                ece = compute_ece(probs, y_test)
                all_results[name]['acc'].append(acc)
                all_results[name]['ece'].append(ece)

                for ci in range(C):
                    mask = c_test == ci
                    if mask.sum() > 0:
                        cat_acc = accuracy_score(y_test[mask], preds[mask]) * 100
                        per_cat_results[name][ci].append(cat_acc)

            except Exception as e:
                print(f"    {name} failed: {e}")
                all_results[name]['acc'].append(0)
                all_results[name]['ece'].append(1.0)

        print(f"  Seed {seed} done")

    # Results
    print(f"\n{'=' * 80}")
    print("OVERALL RESULTS (mean across seeds)")
    print(f"{'=' * 80}")
    print(f"  {'Classifier':>15s}  {'Accuracy':>8s}  {'ECE':>8s}  {'Delta vs centroid':>13s}")
    print(f"  {'-' * 50}")

    centroid_mean = np.mean(all_results["centroid"]['acc'])
    for name in ["centroid", "knn_5", "logistic", "random_forest", "mlp_small"]:
        acc = np.mean(all_results[name]['acc'])
        ece = np.mean(all_results[name]['ece'])
        delta = acc - centroid_mean
        print(f"  {name:>15s}  {acc:>6.1f}%  {ece:>8.4f}  {delta:>+11.1f}pp")

    # Per-category breakdown
    print(f"\n{'=' * 80}")
    print("PER-CATEGORY ACCURACY")
    print(f"{'=' * 80}")
    print(f"  {'Category':>20s}", end="")
    for name in ["centroid", "knn_5", "logistic", "random_forest", "mlp_small"]:
        print(f"  {name[:8]:>8s}", end="")
    print()
    print(f"  {'-' * 65}")

    for ci in range(C):
        print(f"  {CATEGORIES[ci]:>20s}", end="")
        for name in ["centroid", "knn_5", "logistic", "random_forest", "mlp_small"]:
            accs = per_cat_results[name][ci]
            if accs:
                print(f"  {np.mean(accs):>6.1f}%", end="")
            else:
                print(f"  {'N/A':>8s}", end="")
        print()

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    best_name = max(all_results, key=lambda n: np.mean(all_results[n]['acc']))
    best_acc = np.mean(all_results[best_name]['acc'])
    gap = best_acc - centroid_mean

    print(f"Q1: Any classifier beats centroid by >3pp? "
          f"Best: {best_name} ({best_acc:.1f}%), gap={gap:+.1f}pp "
          f"{'YES' if gap > 3 else 'NO'}")
    print(f"Q2: Best achievable accuracy: {best_acc:.1f}%")

    best_ece_name = min(all_results, key=lambda n: np.mean(all_results[n]['ece']))
    best_ece = np.mean(all_results[best_ece_name]['ece'])
    centroid_ece = np.mean(all_results["centroid"]['ece'])
    print(f"Q3: Any beats centroid on ECE? Best: {best_ece_name} ({best_ece:.4f}) "
          f"vs centroid ({centroid_ece:.4f}) "
          f"{'YES' if best_ece < centroid_ece - 0.005 else 'NO'}")

    # Gap concentration
    max_cat_gap = 0
    max_cat_name = ""
    for ci in range(C):
        c_accs = per_cat_results["centroid"][ci]
        b_accs = per_cat_results[best_name][ci]
        if c_accs and b_accs:
            g = np.mean(b_accs) - np.mean(c_accs)
            if g > max_cat_gap:
                max_cat_gap = g
                max_cat_name = CATEGORIES[ci]
    print(f"Q5: Gap concentrated? Largest per-cat gap: {max_cat_name} ({max_cat_gap:+.1f}pp)")

    print("\nDONE.")


if __name__ == "__main__":
    main()
