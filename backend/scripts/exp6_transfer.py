"""
EXP-6: V-CENTROID-TRANSFER
============================
Question: Is the centroid tensor transferable between deployments?

Run: cd backend && python scripts/exp6_transfer.py
Time: ~10 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, run_learning_loop
)

FIRM_B_SHIFT = 0.10  # Frobenius distance between Firm A and B GTs
N_FIRM_A = 2000
N_FIRM_B = 500
CHECKPOINTS = [10, 25, 50, 100, 200, 500]


def main():
    print("=" * 75)
    print("EXP-6: V-CENTROID-TRANSFER")
    print(f"Firm B GT shifted {FIRM_B_SHIFT} Frobenius from Firm A GT")
    print("=" * 75)

    base_mu = get_base_centroids()

    all_results = {cond: [] for cond in ["A_generic", "B_transfer", "C_own_prior"]}

    for seed in SEEDS:
        rng_a = np.random.default_rng(seed)
        gt_a = build_gt(rng_a, base_mu)

        # Phase 1: Run Firm A to convergence
        r_a = run_learning_loop(gt_a, base_mu, N_FIRM_A, [N_FIRM_A], seed,
                                 use_pipeline=True, return_scorer=True)
        firm_a_centroids = r_a['scorer'].centroids.copy()

        # Generate Firm B GT (shifted from Firm A)
        rng_shift = np.random.default_rng(seed + 7000)
        direction = rng_shift.normal(0, 1, gt_a.shape)
        direction = direction / np.linalg.norm(direction) * FIRM_B_SHIFT
        gt_b = gt_a + direction

        # Condition A: Generic prior (0.5 everywhere)
        generic_prior = np.full((C, A, D), 0.5)
        r_generic = run_learning_loop(gt_b, generic_prior, N_FIRM_B,
                                       CHECKPOINTS, seed, use_pipeline=True)
        all_results["A_generic"].append(r_generic['checkpoints'])

        # Condition B: Transfer from Firm A
        r_transfer = run_learning_loop(gt_b, firm_a_centroids, N_FIRM_B,
                                        CHECKPOINTS, seed, use_pipeline=True)
        all_results["B_transfer"].append(r_transfer['checkpoints'])

        # Condition C: Firm B's own calibrated prior (base_mu perturbed toward gt_b)
        # Simulate: prior is halfway between base_mu and gt_b
        own_prior = (base_mu + gt_b) / 2
        r_own = run_learning_loop(gt_b, own_prior, N_FIRM_B,
                                   CHECKPOINTS, seed, use_pipeline=True)
        all_results["C_own_prior"].append(r_own['checkpoints'])

        print(f"  Seed {seed} done")

    # ═══ RESULTS TABLE ═══
    print(f"\n{'=' * 75}")
    print("ACCURACY TRAJECTORIES (mean across 5 seeds)")
    print(f"{'=' * 75}")
    print(f"  {'N':>6s}  {'A_generic':>10s}  {'B_transfer':>11s}  {'C_own_prior':>12s}  {'B-A':>6s}  {'B-C':>6s}")
    print(f"  {'-' * 60}")

    for n in CHECKPOINTS:
        a_vals = [r[n]['learn'] for r in all_results["A_generic"]]
        b_vals = [r[n]['learn'] for r in all_results["B_transfer"]]
        c_vals = [r[n]['learn'] for r in all_results["C_own_prior"]]

        a_m, b_m, c_m = np.mean(a_vals), np.mean(b_vals), np.mean(c_vals)
        print(f"  {n:>6d}  {a_m:8.1f}%  {b_m:9.1f}%  {c_m:10.1f}%  "
              f"{b_m - a_m:+4.1f}pp  {b_m - c_m:+4.1f}pp")

    # ═══ BINARY QUESTIONS ═══
    print(f"\n{'=' * 75}")
    print("BINARY QUESTIONS")
    print(f"{'=' * 75}")

    # Q1: Transfer beats generic at N=50?
    a_50 = np.mean([r[50]['learn'] for r in all_results["A_generic"]])
    b_50 = np.mean([r[50]['learn'] for r in all_results["B_transfer"]])
    gap = b_50 - a_50
    print(f"Q1: Transfer vs generic at N=50: {b_50:.1f}% vs {a_50:.1f}% "
          f"({'YES' if gap > 0 else 'NO'}, gap={gap:+.1f}pp)")

    # Q2: Transfer beats generic at N=500?
    a_500 = np.mean([r[500]['learn'] for r in all_results["A_generic"]])
    b_500 = np.mean([r[500]['learn'] for r in all_results["B_transfer"]])
    gap = b_500 - a_500
    print(f"Q2: Transfer vs generic at N=500: {b_500:.1f}% vs {a_500:.1f}% "
          f"({'YES' if gap > 0 else 'NO'}, gap={gap:+.1f}pp)")

    # Q3: N at which generic catches up to transfer
    catchup = "never"
    for n in CHECKPOINTS:
        a_n = np.mean([r[n]['learn'] for r in all_results["A_generic"]])
        b_n = np.mean([r[n]['learn'] for r in all_results["B_transfer"]])
        if a_n >= b_n - 1.0:  # within 1pp
            catchup = str(n)
            break
    print(f"Q3: Generic catches up to transfer at N={catchup}")

    # Q4: Transfer within 2pp of own-prior at N=50?
    c_50 = np.mean([r[50]['learn'] for r in all_results["C_own_prior"]])
    gap = abs(b_50 - c_50)
    print(f"Q4: Transfer vs own-prior at N=50: {b_50:.1f}% vs {c_50:.1f}% "
          f"(gap={gap:.1f}pp, {'YES' if gap < 2.0 else 'NO'} within 2pp)")

    # Money number
    if catchup != "never":
        print(f"\nMONEY NUMBER: A similar firm's centroid tensor gives you "
              f"{catchup} decisions of head-start.")
    else:
        print(f"\nMONEY NUMBER: Transfer advantage persists through N=500. "
              f"The head-start exceeds the evaluation window.")

    print("\nDONE.")


if __name__ == "__main__":
    main()
