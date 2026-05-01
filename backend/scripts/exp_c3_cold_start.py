"""
EXP-C3: V-COLD-START-CEILING
===============================
Resolves CONFUSION 4: Can ANY controller learn from generic prior?

Run: cd backend && python scripts/exp_c3_cold_start.py
Time: ~10 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF
)

N = 2000
CHECKPOINTS = [50, 100, 200, 500, 1000, 2000]


def run_cold_start(seed, strategy, gt):
    rng = np.random.default_rng(seed)
    generic = np.full((C, A, D), 0.5)
    scorer = make_scorer(generic)
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
        elif strategy.startswith("RAW_"):
            eta_name = strategy.split("_")[1]
            eta = float(eta_name) / 100.0  # RAW_005 = 0.05
            # Scale fv to simulate different eta
            ai_target = oa
            mu_ca = scorer.centroids[ci, ai_target]
            scale = eta / 0.05
            effective_fv = mu_ca + scale * (fv - mu_ca)
            scorer.update(effective_fv.astype(np.float64), ci,
                          result.action_index, correct, oa)
        elif strategy == "SQRT_FAST":
            # eta_0=0.20, n_0=10
            ai_target = oa
            n_ca = ca_counts[ci, ai_target]
            scale = 4.0 / np.sqrt(1.0 + n_ca / 10.0)  # 4x = 0.20/0.05
            scale = max(scale, 0.01)
            mu_ca = scorer.centroids[ci, ai_target]
            effective_fv = mu_ca + scale * (fv - mu_ca)
            scorer.update(effective_fv.astype(np.float64), ci,
                          result.action_index, correct, oa)
            ca_counts[ci, ai_target] += 1
        elif strategy == "SQRT_SLOW":
            # eta_0=0.05, n_0=100
            ai_target = oa
            n_ca = ca_counts[ci, ai_target]
            scale = 1.0 / np.sqrt(1.0 + n_ca / 100.0)
            scale = max(scale, 0.01)
            mu_ca = scorer.centroids[ci, ai_target]
            effective_fv = mu_ca + scale * (fv - mu_ca)
            scorer.update(effective_fv.astype(np.float64), ci,
                          result.action_index, correct, oa)
            ca_counts[ci, ai_target] += 1

        if n in CHECKPOINTS:
            cp[n] = lc / n * 100

    return cp


def main():
    print("=" * 80)
    print("EXP-C3: V-COLD-START-CEILING (from GENERIC prior)")
    print("=" * 80)

    base_mu = get_base_centroids()
    strategies = ["RAW_005", "RAW_010", "RAW_020", "SQRT_FAST",
                  "SQRT_SLOW", "PIPELINE", "STATIC"]

    results = {s: [] for s in strategies}
    for seed in SEEDS:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        for s in strategies:
            r = run_cold_start(seed, s, gt)
            results[s].append(r)
        print(f"  Seed {seed} done")

    # Results table
    print(f"\n{'=' * 80}")
    print(f"  {'N':>6s}", end="")
    for s in strategies:
        print(f"  {s[:10]:>10s}", end="")
    print()
    print(f"  {'-' * 80}")

    for n in CHECKPOINTS:
        print(f"  {n:>6d}", end="")
        for s in strategies:
            acc = np.mean([r[n] for r in results[s]])
            print(f"  {acc:>8.1f}%", end="")
        print()

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    any_above_60 = False
    for s in strategies:
        acc_2000 = np.mean([r[N] for r in results[s]])
        if acc_2000 > 60:
            any_above_60 = True
            print(f"Q1: {s} reaches {acc_2000:.1f}% > 60% at N={N}")

    if not any_above_60:
        print(f"Q1: NO strategy reaches >60% from generic at N={N}")

    best_200 = max(strategies, key=lambda s: np.mean([r[200] for r in results[s]]))
    acc_200 = np.mean([r[200] for r in results[best_200]])
    print(f"Q2: Best at N=200 (shadow mode exit): {best_200} at {acc_200:.1f}%")

    # Q3: Higher eta always helps?
    raw_strats = ["RAW_005", "RAW_010", "RAW_020"]
    raw_accs = {s: np.mean([r[N] for r in results[s]]) for s in raw_strats}
    monotonic = raw_accs["RAW_005"] < raw_accs["RAW_010"] < raw_accs["RAW_020"]
    print(f"Q3: Higher eta always helps? RAW_005={raw_accs['RAW_005']:.1f}% "
          f"RAW_010={raw_accs['RAW_010']:.1f}% RAW_020={raw_accs['RAW_020']:.1f}% "
          f"{'YES' if monotonic else 'NO'}")

    # Q4: At what eta does raw SGD start degrading?
    # Check at N=2000 vs N=200
    for s in raw_strats:
        acc_200 = np.mean([r[200] for r in results[s]])
        acc_2000 = np.mean([r[N] for r in results[s]])
        if acc_2000 < acc_200 - 1.0:
            print(f"Q4: {s} degrades (200: {acc_200:.1f}% -> 2000: {acc_2000:.1f}%)")

    print("\nDONE.")


if __name__ == "__main__":
    main()
