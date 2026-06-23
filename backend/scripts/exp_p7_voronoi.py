"""
EXP-P7: VORONOI GEOMETRY
===========================
The centroid tensor defines a Voronoi tessellation per category.
The STRUCTURE of this tessellation (cell sizes, centroid spacing,
action overlap) determines what the controller can achieve.

Measures:
1. Inter-centroid distances within each category
2. Decision boundary geometry
3. How updates at one centroid affect OTHER centroids' cells
4. The "effective dimensionality" of the centroid arrangement

Run: cd backend && python scripts/exp_p7_voronoi.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action
)

SEEDS_SHORT = [42, 123, 777]
N_PROBE = 10000


def main():
    print("=" * 90)
    print("EXP-P7: VORONOI GEOMETRY")
    print("=" * 90)

    base_mu = get_base_centroids()

    # ═══════════════════════════════════════════════
    # SECTION 1: CENTROID STRUCTURE
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 1: CENTROID STRUCTURE (expert prior)")
    print(f"{'=' * 90}")

    for ci in range(C):
        print(f"\n  Category: {CATEGORIES[ci]} (vol={CATEGORY_WEIGHTS[ci]*100:.0f}%)")

        # Pairwise distances between action centroids
        dists = np.zeros((A, A))
        for a1 in range(A):
            for a2 in range(A):
                dists[a1, a2] = np.linalg.norm(base_mu[ci, a1] - base_mu[ci, a2])

        print(f"    Pairwise centroid distances:")
        print(f"    {'':>12s}", end="")
        for ai in range(A):
            print(f"  {ACTIONS[ai][:8]:>8s}", end="")
        print()
        for a1 in range(A):
            print(f"    {ACTIONS[a1][:12]:>12s}", end="")
            for a2 in range(A):
                print(f"  {dists[a1, a2]:>8.4f}", end="")
            print()

        # Min/max/mean separation
        upper = dists[np.triu_indices(A, k=1)]
        print(f"    Min separation: {upper.min():.4f}")
        print(f"    Max separation: {upper.max():.4f}")
        print(f"    Mean separation: {upper.mean():.4f}")

        # Effective dimensionality (how many dimensions the centroids span)
        centered = base_mu[ci] - base_mu[ci].mean(axis=0)
        if centered.shape[0] > 1:
            svd = np.linalg.svd(centered, compute_uv=False)
            svd_norm = svd / svd.sum() if svd.sum() > 0 else svd
            eff_dim = np.exp(-np.sum(svd_norm * np.log(svd_norm + 1e-10)))
            print(f"    Effective dimensionality: {eff_dim:.2f} / {D}")
            print(f"    Singular values: {np.round(svd, 4)}")

    # ═══════════════════════════════════════════════
    # SECTION 2: GT vs PRIOR STRUCTURE
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 2: GT vs PRIOR -- does GT have the same Voronoi structure?")
    print(f"{'=' * 90}")

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        print(f"\n  Seed {seed}:")

        for ci in range(C):
            # Prior separations
            prior_dists = []
            gt_dists = []
            alignment = []
            for a1 in range(A):
                for a2 in range(a1 + 1, A):
                    pd = np.linalg.norm(base_mu[ci, a1] - base_mu[ci, a2])
                    gd = np.linalg.norm(gt[ci, a1] - gt[ci, a2])
                    prior_dists.append(pd)
                    gt_dists.append(gd)

                    # Alignment: is the direction from a1→a2 the same in prior and GT?
                    dir_prior = base_mu[ci, a2] - base_mu[ci, a1]
                    dir_gt = gt[ci, a2] - gt[ci, a1]
                    if np.linalg.norm(dir_prior) > 0 and np.linalg.norm(dir_gt) > 0:
                        cos_sim = np.dot(dir_prior, dir_gt) / (
                            np.linalg.norm(dir_prior) * np.linalg.norm(dir_gt))
                        alignment.append(cos_sim)

            print(f"    {CATEGORIES[ci]:>20s}: prior_sep={np.mean(prior_dists):.4f} "
                  f"gt_sep={np.mean(gt_dists):.4f} "
                  f"alignment={np.mean(alignment):.4f}")

    # ═══════════════════════════════════════════════
    # SECTION 3: VORONOI CELL VOLUMES
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 3: VORONOI CELL VOLUMES (Monte Carlo)")
    print(f"{'=' * 90}")

    for seed in SEEDS_SHORT[:1]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed + 80000)

        print(f"\n  Seed {seed}:")
        for ci in range(C):
            # Sample N_PROBE random points, count which cell they fall in
            cell_counts_prior = np.zeros(A)
            cell_counts_gt = np.zeros(A)

            for _ in range(N_PROBE):
                fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)

                # Prior cells
                dists_p = [np.linalg.norm(fv - base_mu[ci, ai]) for ai in range(A)]
                cell_counts_prior[np.argmin(dists_p)] += 1

                # GT cells
                dists_g = [np.linalg.norm(fv - gt[ci, ai]) for ai in range(A)]
                cell_counts_gt[np.argmin(dists_g)] += 1

            vols_p = cell_counts_prior / N_PROBE
            vols_g = cell_counts_gt / N_PROBE

            # Cell mismatch: what fraction of points are in different cells?
            rng2 = np.random.default_rng(seed + 90000)
            mismatches = 0
            for _ in range(N_PROBE):
                fv = np.clip(rng2.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                dp = [np.linalg.norm(fv - base_mu[ci, ai]) for ai in range(A)]
                dg = [np.linalg.norm(fv - gt[ci, ai]) for ai in range(A)]
                if np.argmin(dp) != np.argmin(dg):
                    mismatches += 1

            mismatch_pct = mismatches / N_PROBE * 100

            print(f"    {CATEGORIES[ci]:>20s}: "
                  f"prior_vols={np.round(vols_p, 3)} "
                  f"gt_vols={np.round(vols_g, 3)} "
                  f"cell_mismatch={mismatch_pct:.1f}%")

    # ═══════════════════════════════════════════════
    # SECTION 4: CROSS-ACTION COUPLING
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 4: CROSS-ACTION COUPLING")
    print("Moving centroid a1 -- how much does action a2's cell change?")
    print(f"{'=' * 90}")

    seed = 42
    gt = build_gt(np.random.default_rng(seed), base_mu)
    rng = np.random.default_rng(seed + 100000)

    for ci in [0, 4]:  # dominant and rare category
        print(f"\n  Category: {CATEGORIES[ci]}")
        print(f"  Move action a1 by eps=0.05, measure cell volume change for all actions:")
        print(f"  {'Moved':>10s}", end="")
        for ai in range(A):
            print(f"  {'DeltaVol_'+ACTIONS[ai][:4]:>10s}", end="")
        print()

        for a_moved in range(A):
            # Perturb one centroid
            perturbed = base_mu.copy()
            direction = rng.normal(0, 1, D)
            direction = direction / np.linalg.norm(direction) * 0.05
            perturbed[ci, a_moved] += direction

            # Measure cell volumes before and after
            vol_before = np.zeros(A)
            vol_after = np.zeros(A)
            rng_sample = np.random.default_rng(seed + 110000)
            for _ in range(5000):
                fv = np.clip(rng_sample.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                db = [np.linalg.norm(fv - base_mu[ci, ai]) for ai in range(A)]
                da = [np.linalg.norm(fv - perturbed[ci, ai]) for ai in range(A)]
                vol_before[np.argmin(db)] += 1
                vol_after[np.argmin(da)] += 1

            vol_before /= 5000
            vol_after /= 5000
            delta_vol = vol_after - vol_before

            print(f"  {ACTIONS[a_moved][:10]:>10s}", end="")
            for ai in range(A):
                print(f"  {delta_vol[ai]*100:>+8.1f}%", end="")
            print()

    # ═══════════════════════════════════════════════
    # SECTION 5: WHERE IS THE IMPROVEMENT?
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 5: Where does the +1-6pp improvement from moving toward GT come from?")
    print(f"{'=' * 90}")

    for seed in SEEDS_SHORT[:2]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed + 50000)

        # Sample queries, classify with prior and with 20%-toward-GT
        moved20 = base_mu + 0.20 * (gt - base_mu)

        flipped = {ci: np.zeros(A) for ci in range(C)}
        total_per_cat = np.zeros(C)

        for _ in range(N_PROBE):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            total_per_cat[ci] += 1

            dp = [np.linalg.norm(fv - base_mu[ci, ai]) for ai in range(A)]
            dm = [np.linalg.norm(fv - moved20[ci, ai]) for ai in range(A)]

            action_prior = np.argmin(dp)
            action_moved = np.argmin(dm)

            if action_prior != action_moved:
                # Which action gained this query?
                flipped[ci][action_moved] += 1

        print(f"\n  Seed {seed}: queries that FLIP when moving 20% toward GT:")
        for ci in range(C):
            if total_per_cat[ci] > 0:
                print(f"    {CATEGORIES[ci]:>20s}: ", end="")
                for ai in range(A):
                    print(f"{ACTIONS[ai][:4]}={flipped[ci][ai]:.0f} ", end="")
                total_flip = sum(flipped[ci])
                print(f"  total={total_flip:.0f} ({total_flip/total_per_cat[ci]*100:.1f}%)")

    print("\nDONE.")


if __name__ == "__main__":
    main()
