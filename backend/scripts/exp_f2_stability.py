"""
EXP-F2: V-STABILITY-BOUNDARY
===============================
Map the stability diagram: V vs rho.
Find the exact rho threshold where V crosses zero.

Run: cd backend && python scripts/exp_f2_stability.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_RUN = 2000
SEEDS_SHORT = [42, 123, 777]


def main():
    print("=" * 90)
    print("EXP-F2: V-STABILITY-BOUNDARY")
    print("=" * 90)

    base_mu = get_base_centroids()
    rho_targets = [0.0, 0.05, 0.10, 0.20, 0.30, 0.50, 0.70, 0.90, 1.00]

    print(f"\n  {'rho_target':>10s}  {'V_start':>8s}  {'V_end':>8s}  {'DeltaV':>8s}  "
          f"{'V/step':>8s}  {'Stable?':>7s}  {'Acc':>6s}")
    print(f"  {'-' * 65}")

    for rho_target in rho_targets:
        v_starts, v_ends, accs_all = [], [], []

        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            scorer = make_scorer(base_mu.copy())
            rng = np.random.default_rng(seed)
            rng_dir = np.random.default_rng(seed + 30000)

            V_start = float(np.sum((scorer.centroids - gt) ** 2))
            lc = 0

            for n in range(1, N_RUN + 1):
                ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                ta = true_action(gt, ci, fv)
                oa = noise_realistic(ta, ci, rng)
                result = scorer.score(fv, ci)
                correct = (result.action_index == oa)
                if correct: lc += 1

                # Construct update with controlled alignment ρ
                ai = oa
                gt_dir = gt[ci, ai] - scorer.centroids[ci, ai]
                raw_update = fv - scorer.centroids[ci, ai]

                if np.linalg.norm(gt_dir) > 1e-10 and np.linalg.norm(raw_update) > 1e-10:
                    # Component along GT
                    gt_unit = gt_dir / np.linalg.norm(gt_dir)
                    along_gt = np.dot(raw_update, gt_unit)

                    # Random orthogonal component
                    orth = raw_update - along_gt * gt_unit
                    if np.linalg.norm(orth) > 1e-10:
                        orth_unit = orth / np.linalg.norm(orth)
                    else:
                        rand_vec = rng_dir.normal(0, 1, D)
                        orth = rand_vec - np.dot(rand_vec, gt_unit) * gt_unit
                        orth_unit = orth / np.linalg.norm(orth) if np.linalg.norm(orth) > 0 else np.zeros(D)

                    # Compose: ρ fraction along GT, (1-ρ) fraction orthogonal
                    mag = np.linalg.norm(raw_update)
                    controlled = (rho_target * gt_unit + np.sqrt(1 - rho_target**2) * orth_unit) * mag

                    eta = 0.05
                    scorer.centroids[ci, ai] += eta * controlled
                else:
                    scorer.update(fv, ci, result.action_index, correct, oa)

            V_end = float(np.sum((scorer.centroids - gt) ** 2))
            v_starts.append(V_start)
            v_ends.append(V_end)
            accs_all.append(lc / N_RUN * 100)

        mean_vs = np.mean(v_starts)
        mean_ve = np.mean(v_ends)
        mean_dv = mean_ve - mean_vs
        v_dot = mean_dv / N_RUN
        stable = mean_dv <= 0
        acc = np.mean(accs_all)

        print(f"  {rho_target:>10.2f}  {mean_vs:>8.4f}  {mean_ve:>8.4f}  "
              f"{mean_dv:>+8.4f}  {v_dot:>+8.6f}  {'YES' if stable else 'NO':>7s}  "
              f"{acc:>4.1f}%")

    # Find crossover
    print(f"\n  CROSSOVER ANALYSIS:")
    print(f"  The rho threshold where V crosses zero is between the")
    print(f"  last unstable and first stable entries above.")

    # Also: compute theoretical η* = 2‖g‖²/(‖g‖²+Σσᵢ²)
    print(f"\n  THEORETICAL eta* COMPUTATION:")
    for seed in SEEDS_SHORT[:1]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        g = gt - base_mu
        g_norm_sq = np.sum(g ** 2)

        # Estimate σ² from factor distribution
        rng_est = np.random.default_rng(seed + 80000)
        noises = []
        for _ in range(1000):
            ci = int(rng_est.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_est.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            noise = fv - gt[ci, ta]
            noises.append(np.sum(noise ** 2))
        sigma_sq = np.mean(noises)

        eta_star = 2 * g_norm_sq / (g_norm_sq + sigma_sq)
        print(f"    ||g||^2 = {g_norm_sq:.4f}")
        print(f"    Sigmasigma_i^2 = {sigma_sq:.4f}")
        print(f"    eta* = 2||g||^2/(||g||^2+Sigmasigma_i^2) = {eta_star:.6f}")
        print(f"    Production eta = 0.05")
        print(f"    eta > eta*? {'YES (unstable)' if 0.05 > eta_star else 'NO (stable)'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
