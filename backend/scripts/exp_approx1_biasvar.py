"""
EXP-APPROX-1: V-BIAS-VARIANCE-BY-ORDER
=========================================
For each order k = {0 (centroid), 1 (DK), MLP-bounded, MLP-unbounded}:
  For each N = {200, 500, 1000, 2000, 5000}:
    Train 10 times with different data samples
    Bias^2 = (mean_accuracy - oracle_accuracy)^2
    Variance = std(accuracy) across samples

Determines: optimal order for given dataset size.
Predicts: N_cross_01 (when DK beats centroid) and N_cross_1inf (when MLP beats DK).

Run: cd backend && python scripts/exp_approx1_biasvar.py
Time: ~20 min
"""

import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_TEST = 500
N_BOOTSTRAP = 10


def score_dk(fv, ci, centroids, weights):
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        sims.append(-np.sum(weights[ci, ai] * diff ** 2))
    return int(np.argmax(sims))


def estimate_dk_weights(X, y, c, centroids, n_rounds=5):
    weights = np.ones((C, A, D))
    for _ in range(n_rounds):
        for ci in range(C):
            for ai in range(A):
                for di in range(D):
                    mask = c == ci
                    if mask.sum() < 10:
                        continue
                    indices = np.where(mask)[0]
                    best_w = weights[ci, ai, di]
                    best_acc = sum(1 for i in indices
                                  if score_dk(X[i, :D], ci, centroids, weights) == y[i]) / len(indices)
                    for w_trial in [0.1, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0]:
                        trial_w = weights.copy()
                        trial_w[ci, ai, di] = w_trial
                        trial_acc = sum(1 for i in indices
                                        if score_dk(X[i, :D], ci, centroids, trial_w) == y[i]) / len(indices)
                        if trial_acc > best_acc:
                            best_acc = trial_acc
                            best_w = w_trial
                    weights[ci, ai, di] = best_w
    return weights


def evaluate_order(order, X_train, y_train, c_train, X_test, y_test, c_test,
                   centroids, eps_max=0.30, seed=42):
    """Evaluate a specific order on train/test data."""
    scorer = make_scorer(centroids.copy())

    if order == "ORDER_0":
        preds = np.array([scorer.score(X_test[i, :D], c_test[i]).action_index
                          for i in range(len(X_test))])

    elif order == "ORDER_1":
        w = estimate_dk_weights(X_train, y_train, c_train, centroids, n_rounds=5)
        preds = np.array([score_dk(X_test[i, :D], c_test[i], centroids, w)
                          for i in range(len(X_test))])

    elif order == "MLP_BOUNDED":
        cent_train = np.array([scorer.score(X_train[i, :D], c_train[i]).action_index
                               for i in range(len(X_train))])
        cent_test = np.array([scorer.score(X_test[i, :D], c_test[i]).action_index
                              for i in range(len(X_test))])
        feat_tr = np.column_stack([X_train, np.eye(A)[cent_train]])
        feat_te = np.column_stack([X_test, np.eye(A)[cent_test]])
        mlp = MLPClassifier(hidden_layer_sizes=(32,), max_iter=1000, random_state=seed)
        mlp.fit(feat_tr, y_train)
        mlp_preds = mlp.predict(feat_te)
        # Bounded
        gaps = []
        for i in range(len(X_test)):
            result = scorer.score(X_test[i, :D], c_test[i])
            probs = np.array(result.probabilities)
            sp = np.sort(probs)[::-1]
            gaps.append(sp[0] - sp[1])
        gaps = np.array(gaps)
        preds = cent_test.copy()
        for i in range(len(X_test)):
            if mlp_preds[i] != cent_test[i] and gaps[i] <= eps_max:
                preds[i] = mlp_preds[i]

    elif order == "MLP_UNBOUNDED":
        mlp = MLPClassifier(hidden_layer_sizes=(32,), max_iter=1000, random_state=seed)
        mlp.fit(X_train, y_train)
        preds = mlp.predict(X_test)

    return accuracy_score(y_test, preds) * 100


def main():
    print("=" * 90)
    print("EXP-APPROX-1: BIAS-VARIANCE BY ORDER")
    print("=" * 90)

    base_mu = get_base_centroids()
    train_sizes = [200, 500, 1000, 2000, 4000]
    orders = ["ORDER_0", "ORDER_1", "MLP_BOUNDED", "MLP_UNBOUNDED"]

    for gt_seed in [42, 123]:
        gt = build_gt(np.random.default_rng(gt_seed), base_mu)

        # Large pool for sampling
        rng_pool = np.random.default_rng(gt_seed + 1000)
        pool_size = 6000
        X_pool, y_pool, c_pool = [], [], []
        for _ in range(pool_size):
            ci = int(rng_pool.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_pool.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng_pool)
            features = np.concatenate([fv, np.eye(C)[ci]])
            X_pool.append(features)
            y_pool.append(oa)
            c_pool.append(ci)
        X_pool = np.array(X_pool)
        y_pool = np.array(y_pool)
        c_pool = np.array(c_pool)

        # Fixed test set
        X_test = X_pool[5000:]
        y_test = y_pool[5000:]
        c_test = c_pool[5000:]

        # Oracle accuracy (MLP on large clean data)
        rng_oracle = np.random.default_rng(gt_seed + 2000)
        X_oracle, y_oracle = [], []
        for _ in range(5000):
            ci = int(rng_oracle.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_oracle.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            features = np.concatenate([fv, np.eye(C)[ci]])
            X_oracle.append(features)
            y_oracle.append(ta)  # clean labels
        X_oracle = np.array(X_oracle)
        y_oracle = np.array(y_oracle)

        mlp_oracle = MLPClassifier(hidden_layer_sizes=(64,), max_iter=2000, random_state=gt_seed)
        mlp_oracle.fit(X_oracle, y_oracle)
        oracle_preds = mlp_oracle.predict(X_test)
        oracle_acc = accuracy_score(y_test, oracle_preds) * 100

        print(f"\n  GT seed {gt_seed} (oracle accuracy: {oracle_acc:.1f}%):")
        print(f"\n  {'N':>6s}", end="")
        for order in orders:
            print(f"  {'Mean':>6s} {'Std':>5s} {'Bias^2':>6s}", end="")
        print()
        print(f"  {'-' * 80}")

        results = {}
        for N in train_sizes:
            row = {}
            for order in orders:
                accs = []
                for b in range(N_BOOTSTRAP):
                    # Sample N from pool (with replacement for bootstrap)
                    rng_b = np.random.default_rng(gt_seed * 1000 + N * 100 + b)
                    idx = rng_b.choice(5000, size=min(N, 5000), replace=False)
                    X_tr = X_pool[idx]
                    y_tr = y_pool[idx]
                    c_tr = c_pool[idx]

                    acc = evaluate_order(order, X_tr, y_tr, c_tr, X_test, y_test, c_test,
                                         base_mu, seed=gt_seed * 100 + b)
                    accs.append(acc)

                mean_acc = np.mean(accs)
                std_acc = np.std(accs)
                bias_sq = (oracle_acc - mean_acc) ** 2 / 10000  # normalized

                row[order] = {'mean': mean_acc, 'std': std_acc, 'bias_sq': bias_sq}

            print(f"  {N:>6d}", end="")
            for order in orders:
                r = row[order]
                print(f"  {r['mean']:>4.1f}% {r['std']:>4.1f} {r['bias_sq']:>5.2f}", end="")
            print()
            results[N] = row

        # Crossing points
        print(f"\n  CROSSING ANALYSIS:")
        for N in train_sizes:
            o0 = results[N]["ORDER_0"]["mean"]
            o1 = results[N]["ORDER_1"]["mean"]
            mlp_b = results[N]["MLP_BOUNDED"]["mean"]
            mlp_u = results[N]["MLP_UNBOUNDED"]["mean"]
            best = max(o0, o1, mlp_b, mlp_u)
            best_name = ["ORDER_0", "ORDER_1", "MLP_BOUNDED", "MLP_UNBOUNDED"][
                [o0, o1, mlp_b, mlp_u].index(best)]
            print(f"    N={N:>5d}: O0={o0:.1f} O1={o1:.1f} MLB={mlp_b:.1f} MLU={mlp_u:.1f} "
                  f"-> best={best_name} ({best:.1f}%)")

    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("Q1: At what N does Order 1 beat Order 0? (N_cross_01)")
    print("Q2: At what N does MLP beat Order 1? (N_cross_1inf)")
    print("Q3: Does variance increase with order (bias-variance tradeoff)?")
    print("Q4: Is MLP_BOUNDED always <= MLP_UNBOUNDED in variance?")

    print("\nDONE.")


if __name__ == "__main__":
    main()
