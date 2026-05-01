"""
EXP-REPARAM-1: V-BOUNDARY-PARAMETERIZATION
=============================================
Instead of updating centroids (μ ← μ + η(f-μ)), parameterize
the classifier by its boundary hyperplanes and learn those directly.

The ρ negativity may be a PARAMETERIZATION artifact, not fundamental.
If boundary-parameterized updates have ρ > 0 at the operating point,
the learning-stability tension is RESOLVABLE through reparameterization.

Run: cd backend && python scripts/exp_reparam1_boundary.py
Time: ~20 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_RUN = 4000
N_TEST = 500
SEEDS_SHORT = [42, 123, 777]
WINDOW = 200


class BoundaryClassifier:
    """Classifier parameterized by boundary hyperplanes, not centroids.
    
    For each (c, a1, a2) pair: boundary = {x : <n, x> = b}
    Decision: for query x in category c, the action is determined
    by which side of each boundary x falls on.
    """

    def __init__(self, centroids):
        """Initialize boundaries from centroid positions."""
        self.C = centroids.shape[0]
        self.A = centroids.shape[1]
        self.D = centroids.shape[2]

        # For each (c, a1, a2): store (normal, offset)
        self.normals = {}
        self.offsets = {}
        for ci in range(self.C):
            for a1 in range(self.A):
                for a2 in range(a1 + 1, self.A):
                    # Perpendicular bisector of μ₁ and μ₂
                    diff = centroids[ci, a2] - centroids[ci, a1]
                    midpoint = (centroids[ci, a1] + centroids[ci, a2]) / 2
                    norm = np.linalg.norm(diff)
                    if norm > 1e-10:
                        n = diff / norm
                    else:
                        n = np.zeros(self.D)
                        n[0] = 1.0
                    b = np.dot(n, midpoint)
                    self.normals[(ci, a1, a2)] = n.copy()
                    self.offsets[(ci, a1, a2)] = b

    def score(self, fv, ci):
        """Score by pairwise boundary voting."""
        votes = np.zeros(self.A)
        for a1 in range(self.A):
            for a2 in range(a1 + 1, self.A):
                n = self.normals[(ci, a1, a2)]
                b = self.offsets[(ci, a1, a2)]
                proj = np.dot(n, fv) - b
                if proj < 0:
                    votes[a1] += 1  # fv is on a1's side
                else:
                    votes[a2] += 1  # fv is on a2's side
        return int(np.argmax(votes))

    def update_boundary(self, fv, ci, predicted, correct_action, eta=0.01):
        """Update the boundary between predicted and correct action."""
        if predicted == correct_action:
            return

        a1, a2 = min(predicted, correct_action), max(predicted, correct_action)
        n = self.normals[(ci, a1, a2)]
        b = self.offsets[(ci, a1, a2)]

        # fv is on the WRONG side — push boundary toward fv
        proj = np.dot(n, fv) - b

        # Determine push direction
        if correct_action == a1 and proj > 0:
            # fv should be on a1 side (negative proj) but is on a2 side (positive proj)
            # Increase b to push boundary toward a2 side
            self.offsets[(ci, a1, a2)] += eta * abs(proj)
        elif correct_action == a2 and proj < 0:
            # fv should be on a2 side (positive proj) but is on a1 side (negative proj)
            # Decrease b to push boundary toward a1 side
            self.offsets[(ci, a1, a2)] -= eta * abs(proj)

        # Also slightly rotate normal toward the error direction
        error_dir = fv - (n * b)  # rough direction of the misclassified point
        if np.linalg.norm(error_dir) > 1e-10:
            # Small rotation of normal
            n_new = n + eta * 0.1 * error_dir / np.linalg.norm(error_dir)
            n_new = n_new / np.linalg.norm(n_new)
            self.normals[(ci, a1, a2)] = n_new


def compute_gt_boundaries(gt):
    """Compute GT boundary parameters from GT centroids."""
    C_dim, A_dim, D_dim = gt.shape
    normals = {}
    offsets = {}
    for ci in range(C_dim):
        for a1 in range(A_dim):
            for a2 in range(a1 + 1, A_dim):
                diff = gt[ci, a2] - gt[ci, a1]
                midpoint = (gt[ci, a1] + gt[ci, a2]) / 2
                norm = np.linalg.norm(diff)
                if norm > 1e-10:
                    n = diff / norm
                else:
                    n = np.zeros(D_dim)
                    n[0] = 1.0
                b = np.dot(n, midpoint)
                normals[(ci, a1, a2)] = n
                offsets[(ci, a1, a2)] = b
    return normals, offsets


def main():
    print("=" * 90)
    print("EXP-REPARAM-1: BOUNDARY PARAMETERIZATION")
    print("Does learning boundaries directly have better ρ than learning centroids?")
    print("=" * 90)

    base_mu = get_base_centroids()

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        gt_normals, gt_offsets = compute_gt_boundaries(gt)
        rng = np.random.default_rng(seed)

        # ── CENTROID PARAMETERIZATION ──
        scorer_c = make_scorer(base_mu.copy())
        rho_centroid_windows = []
        acc_centroid_windows = []
        window_aligns_c = []
        window_correct_c = 0
        window_total_c = 0

        # ── BOUNDARY PARAMETERIZATION ──
        bclf = BoundaryClassifier(base_mu)
        rho_boundary_windows = []
        acc_boundary_windows = []
        window_aligns_b = []
        window_correct_b = 0
        window_total_b = 0

        print(f"\n  Seed {seed}:")
        print(f"  {'N':>6s}  {'ρ_centroid':>10s}  {'ρ_boundary':>10s}  "
              f"{'Acc_cent':>8s}  {'Acc_bnd':>7s}  {'V_cent':>8s}")
        print(f"  {'-' * 60}")

        for n in range(1, N_RUN + 1):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)

            # ── Centroid update + alignment ──
            result_c = scorer_c.score(fv, ci)
            correct_c = (result_c.action_index == oa)
            if correct_c: window_correct_c += 1
            window_total_c += 1

            ai = oa
            update_c = fv - scorer_c.centroids[ci, ai]
            gt_dir_c = gt[ci, ai] - scorer_c.centroids[ci, ai]
            if np.linalg.norm(update_c) > 1e-10 and np.linalg.norm(gt_dir_c) > 1e-10:
                align_c = np.dot(update_c, gt_dir_c) / (
                    np.linalg.norm(update_c) * np.linalg.norm(gt_dir_c))
                window_aligns_c.append(align_c)

            scorer_c.update(fv, ci, result_c.action_index, correct_c, oa)

            # ── Boundary update + alignment ──
            pred_b = bclf.score(fv, ci)
            correct_b = (pred_b == oa)
            if correct_b: window_correct_b += 1
            window_total_b += 1

            # Alignment for boundary: is the boundary update aligned with GT boundary?
            if pred_b != oa:
                a1, a2 = min(pred_b, oa), max(pred_b, oa)
                if (ci, a1, a2) in bclf.normals and (ci, a1, a2) in gt_normals:
                    # Direction of boundary update (offset change)
                    curr_offset = bclf.offsets[(ci, a1, a2)]
                    gt_offset = gt_offsets[(ci, a1, a2)]
                    offset_error = gt_offset - curr_offset
                    proj = np.dot(bclf.normals[(ci, a1, a2)], fv) - curr_offset

                    # Is the update pushing offset TOWARD gt_offset?
                    if abs(proj) > 1e-10 and abs(offset_error) > 1e-10:
                        # Update direction
                        if oa == a1 and proj > 0:
                            update_dir = +1  # increasing b
                        elif oa == a2 and proj < 0:
                            update_dir = -1  # decreasing b
                        else:
                            update_dir = 0
                        gt_dir_b = np.sign(offset_error)
                        if update_dir != 0:
                            window_aligns_b.append(update_dir * gt_dir_b)

            bclf.update_boundary(fv, ci, pred_b, oa, eta=0.01)

            if n % WINDOW == 0:
                rho_c = np.mean(window_aligns_c) if window_aligns_c else 0
                rho_b = np.mean(window_aligns_b) if window_aligns_b else 0
                acc_c = window_correct_c / window_total_c * 100
                acc_b = window_correct_b / window_total_b * 100
                V_c = float(np.sum((scorer_c.centroids - gt) ** 2))

                rho_centroid_windows.append(rho_c)
                rho_boundary_windows.append(rho_b)

                print(f"  {n:>6d}  {rho_c:>+10.4f}  {rho_b:>+10.4f}  "
                      f"{acc_c:>6.1f}%  {acc_b:>5.1f}%  {V_c:>8.4f}")

                window_aligns_c = []
                window_aligns_b = []
                window_correct_c = 0
                window_correct_b = 0
                window_total_c = 0
                window_total_b = 0

        # Summary
        if rho_centroid_windows and rho_boundary_windows:
            late_rho_c = np.mean(rho_centroid_windows[-5:])
            late_rho_b = np.mean(rho_boundary_windows[-5:])
            print(f"\n    Late-stage ρ (last 1000 decisions):")
            print(f"      Centroid parameterization: {late_rho_c:+.4f}")
            print(f"      Boundary parameterization: {late_rho_b:+.4f}")
            print(f"      Boundary better? {'YES' if late_rho_b > late_rho_c else 'NO'} "
                  f"(Δρ = {late_rho_b - late_rho_c:+.4f})")

    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("Q1: Is ρ_boundary > ρ_centroid at convergence?")
    print("Q2: Is ρ_boundary > 0.08 at any point N > 500?")
    print("Q3: Does boundary-parameterized accuracy exceed centroid accuracy?")
    print("Q4: Is the ρ negativity fundamental or parameterization-dependent?")

    print("\nDONE.")


if __name__ == "__main__":
    main()
