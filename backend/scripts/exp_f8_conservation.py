"""
EXP-F8: V-ERROR-CONSERVATION
===============================
Test whether ε_boundary is conserved under centroid perturbations
at the operating point. Is the operating point a saddle, minimum,
or generic point on the error landscape?

Run: cd backend && python scripts/exp_f8_conservation.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_TEST = 500
N_PERTURBATIONS = 50


def count_boundary_errors(scorer, gt, test_queries):
    """Count boundary errors (scorer wrong, GT scorer right) on fixed test set."""
    scorer_gt = make_scorer(gt.copy())
    n_boundary = 0
    n_total = 0
    for ci, fv, oa in test_queries:
        gt_c = scorer_gt.score(fv, ci).action_index == oa
        pr_c = scorer.score(fv, ci).action_index == oa
        if gt_c and not pr_c:
            n_boundary += 1
        n_total += 1
    return n_boundary, n_total


def main():
    print("=" * 90)
    print("EXP-F8: V-ERROR-CONSERVATION")
    print("=" * 90)

    base_mu = get_base_centroids()
    magnitudes = [0.001, 0.005, 0.01, 0.02, 0.05, 0.10]

    for seed in SEEDS[:3]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed + 50000)

        # Fixed test set
        test_queries = []
        for _ in range(N_TEST):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            test_queries.append((ci, fv, oa))

        # Baseline errors
        scorer_base = make_scorer(base_mu.copy())
        base_errors, _ = count_boundary_errors(scorer_base, gt, test_queries)
        base_rate = base_errors / N_TEST * 100

        print(f"\n  Seed {seed}: baseline ε_boundary = {base_rate:.1f}pp ({base_errors}/{N_TEST})")
        print(f"\n  {'Magnitude':>10s}  {'Mean_Δε':>8s}  {'Std_Δε':>8s}  {'%Positive':>9s}  "
              f"{'%Negative':>9s}  {'%Zero':>6s}  {'Conservation?':>13s}")
        print(f"  {'-' * 70}")

        for mag in magnitudes:
            deltas = []
            n_positive = 0
            n_negative = 0
            n_zero = 0

            rng_pert = np.random.default_rng(seed + 60000 + int(mag * 10000))
            for p in range(N_PERTURBATIONS):
                direction = rng_pert.normal(0, 1, base_mu.shape)
                direction = direction / np.linalg.norm(direction) * mag
                perturbed = np.clip(base_mu + direction, 0, 1)

                scorer_pert = make_scorer(perturbed)
                pert_errors, _ = count_boundary_errors(scorer_pert, gt, test_queries)
                delta = (pert_errors - base_errors) / N_TEST * 100

                deltas.append(delta)
                if delta > 0.01:
                    n_positive += 1
                elif delta < -0.01:
                    n_negative += 1
                else:
                    n_zero += 1

            mean_d = np.mean(deltas)
            std_d = np.std(deltas)
            conserved = abs(mean_d) < 0.5

            print(f"  {mag:>10.3f}  {mean_d:>+6.2f}pp  {std_d:>6.2f}pp  "
                  f"{n_positive/N_PERTURBATIONS*100:>7.0f}%  "
                  f"{n_negative/N_PERTURBATIONS*100:>7.0f}%  "
                  f"{n_zero/N_PERTURBATIONS*100:>4.0f}%  "
                  f"{'YES' if conserved else 'NO'}")

        # Directional analysis at mag=0.05
        print(f"\n  DIRECTIONAL ANALYSIS (mag=0.05):")
        print(f"  Does a gradient direction exist?")

        rng_dir = np.random.default_rng(seed + 70000)
        best_delta = 0
        best_dir = None
        worst_delta = 0
        worst_dir = None

        for p in range(N_PERTURBATIONS):
            direction = rng_dir.normal(0, 1, base_mu.shape)
            direction = direction / np.linalg.norm(direction) * 0.05
            perturbed = np.clip(base_mu + direction, 0, 1)
            scorer_pert = make_scorer(perturbed)
            pert_errors, _ = count_boundary_errors(scorer_pert, gt, test_queries)
            delta = (pert_errors - base_errors) / N_TEST * 100

            if delta < best_delta:
                best_delta = delta
                best_dir = direction.copy()
            if delta > worst_delta:
                worst_delta = delta
                worst_dir = direction.copy()

        print(f"    Best direction:  Δε = {best_delta:+.2f}pp")
        print(f"    Worst direction: Δε = {worst_delta:+.2f}pp")
        print(f"    Range: {worst_delta - best_delta:.2f}pp")

        # Compare best direction to GT direction
        if best_dir is not None:
            gt_dir = gt - base_mu
            gt_dir_flat = gt_dir.flatten()
            best_dir_flat = best_dir.flatten()
            if np.linalg.norm(gt_dir_flat) > 0 and np.linalg.norm(best_dir_flat) > 0:
                cosine = np.dot(gt_dir_flat, best_dir_flat) / (
                    np.linalg.norm(gt_dir_flat) * np.linalg.norm(best_dir_flat))
                print(f"    cos(best_direction, GT_direction) = {cosine:+.4f}")

        # Toward GT: does moving toward GT reduce ε_boundary?
        gt_direction = gt - base_mu
        for frac in [0.01, 0.05, 0.10, 0.20]:
            moved = base_mu + frac * gt_direction
            scorer_moved = make_scorer(moved)
            moved_errors, _ = count_boundary_errors(scorer_moved, gt, test_queries)
            delta = (moved_errors - base_errors) / N_TEST * 100
            print(f"    {frac*100:.0f}% toward GT: Δε = {delta:+.2f}pp")

    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("Q1: Is mean(Δε_boundary) < 0.5pp across all perturbations?")
    print("Q2: Does std(Δε_boundary) increase with magnitude?")
    print("Q3: Is there a consistent gradient direction?")
    print("Q4: How does gradient direction compare to GT direction?")

    print("\nDONE.")


if __name__ == "__main__":
    main()
