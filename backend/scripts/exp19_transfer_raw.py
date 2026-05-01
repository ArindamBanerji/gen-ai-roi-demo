"""
EXP-19: V-TRANSFER-WITHOUT-PIPELINE
=====================================
Disentangle transfer value from pipeline cold-start masking.

Run: cd backend && python scripts/exp19_transfer_raw.py
Time: ~10 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, run_learning_loop
)

FIRM_B_SHIFT = 0.10
N_FIRM_A = 2000
N_FIRM_B = 2000
CHECKPOINTS = [50, 100, 200, 500, 1000, 2000]


def main():
    print("=" * 80)
    print("EXP-19: V-TRANSFER-WITHOUT-PIPELINE")
    print(f"Firm B GT shifted {FIRM_B_SHIFT} Frobenius from Firm A")
    print("=" * 80)

    base_mu = get_base_centroids()
    conditions = ["generic_raw", "generic_pipeline",
                  "transfer_raw", "transfer_pipeline",
                  "own_prior_raw", "own_prior_pipeline"]
    all_results = {c: [] for c in conditions}

    for seed in SEEDS:
        rng_a = np.random.default_rng(seed)
        gt_a = build_gt(rng_a, base_mu)

        # Phase 1: Firm A converges
        r_a = run_learning_loop(gt_a, base_mu, N_FIRM_A, [N_FIRM_A],
                                 seed, use_pipeline=True, return_scorer=True)
        firm_a_mu = r_a['scorer'].centroids.copy()

        # Firm B GT
        rng_shift = np.random.default_rng(seed + 7000)
        direction = rng_shift.normal(0, 1, gt_a.shape)
        direction = direction / np.linalg.norm(direction) * FIRM_B_SHIFT
        gt_b = gt_a + direction

        generic = np.full((C, A, D), 0.5)
        own_prior = (base_mu + gt_b) / 2

        priors = {
            "generic": generic,
            "transfer": firm_a_mu,
            "own_prior": own_prior,
        }

        for prior_name, prior in priors.items():
            for use_pipe in [False, True]:
                label = f"{prior_name}_{'pipeline' if use_pipe else 'raw'}"
                r = run_learning_loop(gt_b, prior, N_FIRM_B, CHECKPOINTS,
                                       seed, use_pipeline=use_pipe)
                all_results[label].append(r['checkpoints'])

        print(f"  Seed {seed} done")

    # Results table
    print(f"\n{'=' * 80}")
    print(f"{'N':>6s}", end="")
    for c in conditions:
        print(f"  {c[:14]:>14s}", end="")
    print()
    print("-" * 96)

    for n in CHECKPOINTS:
        print(f"{n:>6d}", end="")
        for c in conditions:
            accs = [r[n]['learn'] for r in all_results[c]]
            print(f"  {np.mean(accs):12.1f}%", end="")
        print()

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    # Q1: transfer_raw vs generic_raw at N=50
    tr_50 = np.mean([r[50]['learn'] for r in all_results["transfer_raw"]])
    gr_50 = np.mean([r[50]['learn'] for r in all_results["generic_raw"]])
    print(f"Q1: transfer_raw ({tr_50:.1f}%) vs generic_raw ({gr_50:.1f}%) at N=50: "
          f"gap={tr_50 - gr_50:+.1f}pp")

    # Q2: transfer_raw vs generic_raw at N=2000
    tr_2k = np.mean([r[2000]['learn'] for r in all_results["transfer_raw"]])
    gr_2k = np.mean([r[2000]['learn'] for r in all_results["generic_raw"]])
    print(f"Q2: transfer_raw ({tr_2k:.1f}%) vs generic_raw ({gr_2k:.1f}%) at N=2000: "
          f"gap={tr_2k - gr_2k:+.1f}pp (TRUE transfer value)")

    # Q3: Does raw SGD degrade transfer centroids?
    tr_raw_50 = np.mean([r[50]['learn'] for r in all_results["transfer_raw"]])
    tr_raw_2k = np.mean([r[2000]['learn'] for r in all_results["transfer_raw"]])
    degrades = tr_raw_2k < tr_raw_50 - 1.0
    print(f"Q3: Raw SGD degrades transfer? {tr_raw_50:.1f}%@50 -> {tr_raw_2k:.1f}%@2000 "
          f"{'YES' if degrades else 'NO'} (drift={tr_raw_2k - tr_raw_50:+.1f}pp)")

    # Q4: Pipeline value ON TOP of transfer
    tr_pipe_2k = np.mean([r[2000]['learn'] for r in all_results["transfer_pipeline"]])
    pipe_on_transfer = tr_pipe_2k - tr_2k
    print(f"Q4: Pipeline on top of transfer: pipe={tr_pipe_2k:.1f}% raw={tr_2k:.1f}% "
          f"gap={pipe_on_transfer:+.1f}pp")

    if degrades:
        print(f"\n  >>> Transfer + pipeline = preserve transfer value")
        print(f"  >>> Transfer + raw SGD = eventually degrades transfer")
    else:
        print(f"\n  >>> Transfer alone is sufficient (raw SGD doesn't degrade)")

    print("\nDONE.")


if __name__ == "__main__":
    main()
