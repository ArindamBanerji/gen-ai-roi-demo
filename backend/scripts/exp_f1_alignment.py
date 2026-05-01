"""
EXP-F1: V-ALIGNMENT-TRAJECTORY
=================================
Track ρ (update-GT alignment) over 4000 decisions.
Does ρ decrease as centroids converge?
Is there a crossover at ρ = 0.5?
Is ρ_boundary > ρ_deep?

Run: cd backend && python scripts/exp_f1_alignment.py
Time: ~10 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_RUN = 4000
SEEDS_SHORT = [42, 123, 777]
WINDOW = 100  # compute ρ over rolling windows


def main():
    print("=" * 90)
    print("EXP-F1: V-ALIGNMENT-TRAJECTORY")
    print("=" * 90)

    base_mu = get_base_centroids()

    # ═══════════════════════════════════════════════
    # SECTION 1: ρ trajectory over 4000 decisions
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 1: ρ(t) over 4000 decisions")
    print(f"{'=' * 90}")

    checkpoints = list(range(WINDOW, N_RUN + 1, WINDOW))

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        scorer = make_scorer(base_mu.copy())
        rng = np.random.default_rng(seed)

        alignments = []
        V_vals = []
        accs_window = []
        rho_boundary = []  # ρ for confidence < 0.50
        rho_deep = []      # ρ for confidence > 0.80

        window_aligns = []
        window_aligns_bnd = []
        window_aligns_deep = []
        window_correct = 0
        window_total = 0

        print(f"\n  Seed {seed}:")
        print(f"  {'N':>6s}  {'ρ_all':>7s}  {'ρ_bnd':>7s}  {'ρ_deep':>7s}  "
              f"{'V':>8s}  {'Acc':>6s}  {'n_bnd':>5s}  {'n_deep':>6s}")
        print(f"  {'-' * 65}")

        for n in range(1, N_RUN + 1):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            result = scorer.score(fv, ci)
            correct = (result.action_index == oa)
            if correct:
                window_correct += 1
            window_total += 1

            # Compute alignment of this update with GT direction
            ai = oa
            update_dir = fv - scorer.centroids[ci, ai]
            gt_dir = gt[ci, ai] - scorer.centroids[ci, ai]

            if np.linalg.norm(update_dir) > 1e-10 and np.linalg.norm(gt_dir) > 1e-10:
                alignment = np.dot(update_dir, gt_dir) / (
                    np.linalg.norm(update_dir) * np.linalg.norm(gt_dir))
                window_aligns.append(alignment)

                if result.confidence < 0.50:
                    window_aligns_bnd.append(alignment)
                elif result.confidence > 0.80:
                    window_aligns_deep.append(alignment)

            # Apply SGD update
            scorer.update(fv, ci, result.action_index, correct, oa)

            if n in checkpoints:
                rho = np.mean(window_aligns) if window_aligns else 0
                rho_b = np.mean(window_aligns_bnd) if window_aligns_bnd else 0
                rho_d = np.mean(window_aligns_deep) if window_aligns_deep else 0
                V = float(np.sum((scorer.centroids - gt) ** 2))
                acc = window_correct / window_total * 100

                print(f"  {n:>6d}  {rho:>+7.4f}  {rho_b:>+7.4f}  {rho_d:>+7.4f}  "
                      f"{V:>8.4f}  {acc:>4.1f}%  {len(window_aligns_bnd):>5d}  "
                      f"{len(window_aligns_deep):>6d}")

                alignments.append(rho)
                V_vals.append(V)
                rho_boundary.append(rho_b)
                rho_deep.append(rho_d)

                # Reset windows
                window_aligns = []
                window_aligns_bnd = []
                window_aligns_deep = []
                window_correct = 0
                window_total = 0

    # ═══════════════════════════════════════════════
    # SECTION 2: ρ from GENERIC prior (cold start)
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 2: ρ from GENERIC prior (does ρ start high?)")
    print(f"{'=' * 90}")

    for seed in SEEDS_SHORT[:1]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        generic = np.full_like(base_mu, 0.5)
        scorer = make_scorer(generic)
        rng = np.random.default_rng(seed)

        print(f"\n  Seed {seed} (generic prior):")
        print(f"  {'N':>6s}  {'ρ':>7s}  {'V':>8s}  {'Acc':>6s}")
        print(f"  {'-' * 30}")

        window_aligns = []
        window_correct = 0
        window_total = 0

        for n in range(1, N_RUN + 1):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            result = scorer.score(fv, ci)
            correct = (result.action_index == oa)
            if correct:
                window_correct += 1
            window_total += 1

            ai = oa
            update_dir = fv - scorer.centroids[ci, ai]
            gt_dir = gt[ci, ai] - scorer.centroids[ci, ai]
            if np.linalg.norm(update_dir) > 1e-10 and np.linalg.norm(gt_dir) > 1e-10:
                alignment = np.dot(update_dir, gt_dir) / (
                    np.linalg.norm(update_dir) * np.linalg.norm(gt_dir))
                window_aligns.append(alignment)

            scorer.update(fv, ci, result.action_index, correct, oa)

            if n % WINDOW == 0:
                rho = np.mean(window_aligns) if window_aligns else 0
                V = float(np.sum((scorer.centroids - gt) ** 2))
                acc = window_correct / window_total * 100
                print(f"  {n:>6d}  {rho:>+7.4f}  {V:>8.4f}  {acc:>4.1f}%")
                window_aligns = []
                window_correct = 0
                window_total = 0

    # ═══════════════════════════════════════════════
    # SECTION 3: ρ after distribution shift
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 3: ρ after distribution shift at N=2000")
    print(f"{'=' * 90}")

    for seed in SEEDS_SHORT[:1]:
        gt_orig = build_gt(np.random.default_rng(seed), base_mu)
        scorer = make_scorer(base_mu.copy())
        rng = np.random.default_rng(seed)

        # Shift GT at N=2000
        gt_shifted = gt_orig.copy()
        shift_rng = np.random.default_rng(seed + 7000)
        shift_dir = shift_rng.normal(0, 1, gt_orig.shape)
        shift_dir = shift_dir / np.linalg.norm(shift_dir) * 0.5
        gt_shifted = np.clip(gt_orig + shift_dir, 0, 1)

        print(f"\n  Seed {seed} (shift at N=2000):")
        print(f"  {'N':>6s}  {'ρ':>7s}  {'V':>8s}  {'Event':>8s}")
        print(f"  {'-' * 35}")

        window_aligns = []

        for n in range(1, N_RUN + 1):
            gt = gt_orig if n <= 2000 else gt_shifted
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            result = scorer.score(fv, ci)

            ai = oa
            update_dir = fv - scorer.centroids[ci, ai]
            gt_dir = gt[ci, ai] - scorer.centroids[ci, ai]
            if np.linalg.norm(update_dir) > 1e-10 and np.linalg.norm(gt_dir) > 1e-10:
                alignment = np.dot(update_dir, gt_dir) / (
                    np.linalg.norm(update_dir) * np.linalg.norm(gt_dir))
                window_aligns.append(alignment)

            scorer.update(fv, ci, result.action_index, result.action_index == oa, oa)

            if n % WINDOW == 0:
                rho = np.mean(window_aligns) if window_aligns else 0
                V = float(np.sum((scorer.centroids - gt) ** 2))
                event = "SHIFT" if n == 2000 else ""
                print(f"  {n:>6d}  {rho:>+7.4f}  {V:>8.4f}  {event}")
                window_aligns = []

    # Binary questions
    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("Q1: Does ρ decrease as centroids converge? (see Section 1)")
    print("Q2: Is there a crossover at ρ = 0.5? (see Section 2)")
    print("Q3: Is ρ_boundary > ρ_deep? (see Section 1)")
    print("Q4: Does ρ increase after shift? (see Section 3)")

    print("\nDONE.")


if __name__ == "__main__":
    main()
