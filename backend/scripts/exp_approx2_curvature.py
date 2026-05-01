"""
EXP-APPROX-2: V-BOUNDARY-CURVATURE
=====================================
Measure the curvature of decision boundaries at each approximation order.

The approximation theory claims:
  Order 0 (centroid): κ = 0 (flat hyperplane)
  Order 1 (DK):       κ > 0 (quadric surface)
  Order ∞ (MLP):      κ >> 0 (arbitrary curvature)

Measure the actual curvature by sampling along the boundary
and computing local deviation from linearity.

Run: cd backend && python scripts/exp_approx2_curvature.py
Time: ~15 min
"""

import numpy as np
from sklearn.neural_network import MLPClassifier
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_TRAIN = 2000
N_BOUNDARY_SAMPLES = 200


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


def find_boundary_point(scorer_func, ci, a1, a2, rng, max_iter=50):
    """Find a point on the boundary between actions a1 and a2 using bisection."""
    # Sample two points classified differently
    for _ in range(100):
        p1 = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        p2 = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        if scorer_func(p1, ci) == a1 and scorer_func(p2, ci) == a2:
            break
        if scorer_func(p1, ci) == a2 and scorer_func(p2, ci) == a1:
            p1, p2 = p2, p1
            break
    else:
        return None

    # Bisect to find boundary
    for _ in range(max_iter):
        mid = (p1 + p2) / 2
        if scorer_func(mid, ci) == a1:
            p1 = mid
        else:
            p2 = mid
    return (p1 + p2) / 2


def estimate_curvature(boundary_points):
    """Estimate boundary curvature from sampled boundary points.
    
    Fit a hyperplane to the points, then measure mean squared
    deviation from that hyperplane. Higher deviation = more curvature.
    """
    if len(boundary_points) < D + 2:
        return 0.0, 0.0

    pts = np.array(boundary_points)
    centroid = pts.mean(axis=0)
    centered = pts - centroid

    # Fit hyperplane via SVD
    U, S, Vh = np.linalg.svd(centered, full_matrices=False)
    normal = Vh[-1]  # last right singular vector = normal to best-fit hyperplane

    # Project onto normal: residual from hyperplane
    projections = centered @ normal
    msd = np.mean(projections ** 2)
    max_dev = np.max(np.abs(projections))

    return msd, max_dev


def main():
    print("=" * 90)
    print("EXP-APPROX-2: BOUNDARY CURVATURE QUANTIFICATION")
    print("=" * 90)

    base_mu = get_base_centroids()
    scorer = make_scorer(base_mu.copy())

    for seed in SEEDS[:3]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)

        # Collect training data
        X_all, y_all, c_all = [], [], []
        for _ in range(N_TRAIN):
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

        # Train DK
        dk_weights = estimate_dk_weights(X_all, y_all, c_all, base_mu, n_rounds=5)

        # Train MLP
        cent_preds = np.array([scorer.score(X_all[i, :D], c_all[i]).action_index
                               for i in range(N_TRAIN)])
        feat = np.column_stack([X_all, np.eye(A)[cent_preds]])
        mlp = MLPClassifier(hidden_layer_sizes=(32,), max_iter=1000, random_state=seed)
        mlp.fit(feat, y_all)

        # GT scorer
        gt_scorer = make_scorer(gt.copy())

        # Define scorer functions for each order
        def score_order0(fv, ci):
            return scorer.score(fv, ci).action_index

        def score_order1(fv, ci):
            return score_dk(fv, ci, base_mu, dk_weights)

        def score_mlp(fv, ci):
            cent_pred = scorer.score(fv, ci).action_index
            features = np.concatenate([fv, np.eye(C)[ci]])
            feat = np.concatenate([features, np.eye(A)[cent_pred]])
            return int(mlp.predict(feat.reshape(1, -1))[0])

        def score_gt(fv, ci):
            return gt_scorer.score(fv, ci).action_index

        # For the dominant boundary: investigate (1) vs monitor (3)
        # in credential_access (0)
        ci_target = 0
        a1, a2 = 1, 3  # investigate vs monitor

        print(f"\n  Seed {seed}: Boundary investigate↔monitor in credential_access")

        orders = {
            "ORDER_0 (centroid)": score_order0,
            "ORDER_1 (DK)": score_order1,
            "MLP": score_mlp,
            "GT": score_gt,
        }

        rng_bnd = np.random.default_rng(seed + 30000)

        print(f"\n  {'Order':>25s}  {'MSD':>10s}  {'MaxDev':>10s}  {'N_found':>7s}  {'Curvature':>12s}")
        print(f"  {'-' * 70}")

        curvatures = {}
        for order_name, score_func in orders.items():
            boundary_pts = []
            for _ in range(N_BOUNDARY_SAMPLES):
                bp = find_boundary_point(score_func, ci_target, a1, a2, rng_bnd)
                if bp is not None:
                    boundary_pts.append(bp)

            if len(boundary_pts) > D + 2:
                msd, max_dev = estimate_curvature(boundary_pts)
                curvatures[order_name] = msd
                label = "FLAT" if msd < 0.0001 else ("LOW" if msd < 0.001 else "HIGH")
                print(f"  {order_name:>25s}  {msd:>10.6f}  {max_dev:>10.6f}  "
                      f"{len(boundary_pts):>7d}  {label:>12s}")
            else:
                print(f"  {order_name:>25s}  — (only {len(boundary_pts)} boundary points found)")

        # How much GT curvature does each order capture?
        if "GT" in curvatures and curvatures["GT"] > 0:
            print(f"\n  CURVATURE CAPTURE (fraction of GT curvature):")
            gt_curv = curvatures["GT"]
            for name in ["ORDER_0 (centroid)", "ORDER_1 (DK)", "MLP"]:
                if name in curvatures:
                    frac = curvatures[name] / gt_curv
                    print(f"    {name:>25s}: {frac:.2f} ({curvatures[name]/gt_curv*100:.0f}% of GT)")

        # Also measure for other category-action boundaries
        print(f"\n  CURVATURE ACROSS BOUNDARIES (Order 0 vs GT):")
        print(f"  {'Category':>20s}  {'Pair':>15s}  {'κ_centroid':>10s}  {'κ_GT':>10s}  {'Ratio':>6s}")
        print(f"  {'-' * 65}")

        for ci in range(min(C, 4)):
            for a1_b in range(A):
                for a2_b in range(a1_b + 1, A):
                    rng_b2 = np.random.default_rng(seed + ci * 100 + a1_b * 10 + a2_b)
                    pts_c = []
                    pts_g = []
                    for _ in range(100):
                        bp_c = find_boundary_point(score_order0, ci, a1_b, a2_b, rng_b2)
                        if bp_c is not None:
                            pts_c.append(bp_c)
                        bp_g = find_boundary_point(score_gt, ci, a1_b, a2_b, rng_b2)
                        if bp_g is not None:
                            pts_g.append(bp_g)

                    if len(pts_c) > D + 2 and len(pts_g) > D + 2:
                        msd_c, _ = estimate_curvature(pts_c)
                        msd_g, _ = estimate_curvature(pts_g)
                        ratio = msd_c / max(msd_g, 1e-10)
                        pair = f"{ACTIONS[a1_b][:4]}-{ACTIONS[a2_b][:4]}"
                        print(f"  {CATEGORIES[ci]:>20s}  {pair:>15s}  "
                              f"{msd_c:>10.6f}  {msd_g:>10.6f}  {ratio:>5.2f}")

    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("Q1: Is κ_centroid ≈ 0 (flat boundary confirmed)?")
    print("Q2: Is κ_DK > κ_centroid (DK adds curvature)?")
    print("Q3: Is κ_MLP > κ_DK (MLP adds MORE curvature)?")
    print("Q4: What fraction of κ_GT does each order capture?")

    print("\nDONE.")


if __name__ == "__main__":
    main()
