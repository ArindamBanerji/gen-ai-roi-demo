"""
EXP-C4: V-TRANSFER-WITH-CONTROLLERS
======================================
Resolves CONFUSION 5: Does a better controller close the transfer gap?

Run: cd backend && python scripts/exp_c4_transfer_ctrl.py
Time: ~10 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF
)

N = 2000
CHECKPOINTS = [50, 200, 500, 1000, 2000]
FIRM_B_SHIFT = 0.10


def run_with_controller(seed, prior, gt, strategy):
    rng = np.random.default_rng(seed)
    scorer = make_scorer(prior.copy())
    ca_counts = np.zeros((C, A))
    pipeline = None
    if strategy == "PIPELINE":
        pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                       category_weights=CATEGORY_WEIGHTS)
    lc = 0
    cp = {}

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc += 1

        if strategy == "STATIC":
            pass
        elif strategy == "PIPELINE":
            pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)
        elif strategy == "RAW_SGD":
            scorer.update(fv, ci, result.action_index, correct, oa)
        elif strategy == "GATE_DECAY":
            if result.confidence <= THETA_CONF:
                ai_target = oa
                n_ca = ca_counts[ci, ai_target]
                scale = 1.0 / np.sqrt(1.0 + n_ca / 10.0)
                mu_ca = scorer.centroids[ci, ai_target]
                effective_fv = mu_ca + max(scale, 0.01) * (fv - mu_ca)
                scorer.update(effective_fv.astype(np.float64), ci,
                              result.action_index, correct, oa)
                ca_counts[ci, ai_target] += 1
        elif strategy == "SQRT_DECAY":
            ai_target = oa
            n_ca = ca_counts[ci, ai_target]
            scale = 1.0 / np.sqrt(1.0 + n_ca / 10.0)
            mu_ca = scorer.centroids[ci, ai_target]
            effective_fv = mu_ca + max(scale, 0.01) * (fv - mu_ca)
            scorer.update(effective_fv.astype(np.float64), ci,
                          result.action_index, correct, oa)
            ca_counts[ci, ai_target] += 1

        if n in CHECKPOINTS:
            cp[n] = lc / n * 100

    return cp


def main():
    print("=" * 80)
    print("EXP-C4: V-TRANSFER-WITH-CONTROLLERS")
    print(f"Firm B GT shifted {FIRM_B_SHIFT} Frobenius from Firm A")
    print("=" * 80)

    base_mu = get_base_centroids()
    strategies = ["STATIC", "PIPELINE", "RAW_SGD", "GATE_DECAY", "SQRT_DECAY"]

    all_results = {f"{prior}_{strat}": [] for prior in ["transfer", "own_prior"]
                   for strat in strategies}

    for seed in SEEDS:
        rng_a = np.random.default_rng(seed)
        gt_a = build_gt(rng_a, base_mu)

        # Firm A converges
        from exp_shared import run_learning_loop
        r_a = run_learning_loop(gt_a, base_mu, 2000, [2000], seed,
                                 use_pipeline=True, return_scorer=True)
        firm_a_mu = r_a['scorer'].centroids.copy()

        # Firm B GT
        rng_shift = np.random.default_rng(seed + 7000)
        direction = rng_shift.normal(0, 1, gt_a.shape)
        direction = direction / np.linalg.norm(direction) * FIRM_B_SHIFT
        gt_b = gt_a + direction

        own_prior = (base_mu + gt_b) / 2

        for strat in strategies:
            r_xfer = run_with_controller(seed, firm_a_mu, gt_b, strat)
            all_results[f"transfer_{strat}"].append(r_xfer)

            r_own = run_with_controller(seed, own_prior, gt_b, strat)
            all_results[f"own_prior_{strat}"].append(r_own)

        print(f"  Seed {seed} done")

    # Results table
    print(f"\n{'=' * 80}")
    print(f"  {'Strategy':>15s}  {'Xfer@2000':>9s}  {'Own@2000':>9s}  {'Gap':>6s}")
    print(f"  {'-' * 45}")

    gaps = {}
    for strat in strategies:
        xfer = np.mean([r[N] for r in all_results[f"transfer_{strat}"]])
        own = np.mean([r[N] for r in all_results[f"own_prior_{strat}"]])
        gap = own - xfer
        gaps[strat] = gap
        print(f"  {strat:>15s}  {xfer:>7.1f}%  {own:>7.1f}%  {gap:>+4.1f}pp")

    # Trajectory comparison
    print(f"\n{'=' * 80}")
    print("TRAJECTORY (transfer prior)")
    print(f"{'=' * 80}")
    print(f"  {'N':>6s}", end="")
    for s in strategies:
        print(f"  {s[:10]:>10s}", end="")
    print()
    print(f"  {'-' * 60}")
    for n in CHECKPOINTS:
        print(f"  {n:>6d}", end="")
        for s in strategies:
            acc = np.mean([r[n] for r in all_results[f"transfer_{s}"]])
            print(f"  {acc:>8.1f}%", end="")
        print()

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    min_gap_strat = min(strategies, key=lambda s: gaps[s])
    print(f"Q1: Any strategy reduces gap below 2pp? "
          f"Best: {min_gap_strat} (gap={gaps[min_gap_strat]:+.1f}pp) "
          f"{'YES' if gaps[min_gap_strat] < 2.0 else 'NO'}")

    print(f"Q2: GATE_DECAY vs PIPELINE gap? "
          f"GD={gaps['GATE_DECAY']:+.1f}pp PIPE={gaps['PIPELINE']:+.1f}pp "
          f"{'GD BETTER' if gaps['GATE_DECAY'] < gaps['PIPELINE'] else 'PIPE BETTER'}")

    gap_range = max(gaps.values()) - min(gaps.values())
    print(f"Q3: Gap constant across strategies? range={gap_range:.1f}pp "
          f"{'YES (plant-determined)' if gap_range < 1.0 else 'NO (controller matters)'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
