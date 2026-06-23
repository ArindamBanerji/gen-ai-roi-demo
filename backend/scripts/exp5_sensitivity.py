"""
EXP-5: V-PIPELINE-SENSITIVITY
===============================
Question: How sensitive is the pipeline to parameter choices?

Run: cd backend && python scripts/exp5_sensitivity.py
Time: ~20 min (60 runs x 2000 decisions)
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline
)

THETA_VALUES = [0.40, 0.50, 0.60, 0.70, 0.80]
K_VALUES = [5, 10, 20, 50]
SEEDS_SHORT = [42, 123, 777]  # 3 seeds for sweep
N = 2000


def run_sweep_single(seed, theta, K):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)
    scorer = make_scorer()
    static = make_scorer()
    pipeline = ThreeStagePipeline(scorer, K=K, theta_conf=theta,
                                   category_weights=CATEGORY_WEIGHTS)

    lc, sc = 0, 0
    acc_200, acc_2000 = 0, 0

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        lr = scorer.score(fv, ci)
        correct = (lr.action_index == oa)
        if correct: lc += 1

        pipeline.process(fv, ci, lr.action_index, correct, oa, lr.confidence)

        sr = static.score(fv, ci)
        if sr.action_index == oa: sc += 1

        if n == 200: acc_200 = lc / n * 100
        if n == N: acc_2000 = lc / n * 100

    static_acc = sc / N * 100
    drift = acc_2000 - acc_200
    update_rate = pipeline.update_rate

    return {
        'acc_200': acc_200, 'acc_2000': acc_2000,
        'static': static_acc, 'drift': drift,
        'ls_gap': acc_2000 - static_acc,
        'update_rate': update_rate,
    }


def main():
    print("=" * 75)
    print("EXP-5: V-PIPELINE-SENSITIVITY (theta_conf x K sweep)")
    print(f"3 seeds, {len(THETA_VALUES)} x {len(K_VALUES)} = {len(THETA_VALUES) * len(K_VALUES)} configs")
    print("=" * 75)

    results = {}
    total = len(THETA_VALUES) * len(K_VALUES)
    done = 0

    for theta in THETA_VALUES:
        for K in K_VALUES:
            runs = [run_sweep_single(s, theta, K) for s in SEEDS_SHORT]
            results[(theta, K)] = {
                'acc': np.mean([r['acc_2000'] for r in runs]),
                'drift': np.mean([r['drift'] for r in runs]),
                'ls_gap': np.mean([r['ls_gap'] for r in runs]),
                'update_rate': np.mean([r['update_rate'] for r in runs]),
            }
            done += 1
            if done % 5 == 0:
                print(f"  {done}/{total} configs done...")

    # ═══ HEATMAP: ACCURACY ═══
    print(f"\n{'=' * 75}")
    print("HEATMAP: Accuracy at N=2000")
    print(f"{'=' * 75}")
    print(f"{'theta_conf':>8s}", end="")
    for K in K_VALUES:
        print(f"  {'K=' + str(K):>8s}", end="")
    print()
    for theta in THETA_VALUES:
        print(f"  {theta:.2f}  ", end="")
        for K in K_VALUES:
            print(f"  {results[(theta, K)]['acc']:6.1f}%", end="")
        print()

    # ═══ HEATMAP: DRIFT ═══
    print(f"\n{'=' * 75}")
    print("HEATMAP: Drift (N=200 -> N=2000)")
    print(f"{'=' * 75}")
    print(f"{'theta_conf':>8s}", end="")
    for K in K_VALUES:
        print(f"  {'K=' + str(K):>8s}", end="")
    print()
    for theta in THETA_VALUES:
        print(f"  {theta:.2f}  ", end="")
        for K in K_VALUES:
            d = results[(theta, K)]['drift']
            marker = " [OK]" if d >= -1.0 else " [FAIL]"
            print(f"  {d:+5.1f}pp{marker}", end="")
        print()

    # ═══ HEATMAP: UPDATE RATE ═══
    print(f"\n{'=' * 75}")
    print("HEATMAP: Update rate (% of decisions -> centroid update)")
    print(f"{'=' * 75}")
    print(f"{'theta_conf':>8s}", end="")
    for K in K_VALUES:
        print(f"  {'K=' + str(K):>8s}", end="")
    print()
    for theta in THETA_VALUES:
        print(f"  {theta:.2f}  ", end="")
        for K in K_VALUES:
            print(f"  {results[(theta, K)]['update_rate'] * 100:6.1f}%", end="")
        print()

    # ═══ HEATMAP: LEARN-STATIC GAP ═══
    print(f"\n{'=' * 75}")
    print("HEATMAP: LEARN - STATIC at N=2000")
    print(f"{'=' * 75}")
    print(f"{'theta_conf':>8s}", end="")
    for K in K_VALUES:
        print(f"  {'K=' + str(K):>8s}", end="")
    print()
    for theta in THETA_VALUES:
        print(f"  {theta:.2f}  ", end="")
        for K in K_VALUES:
            g = results[(theta, K)]['ls_gap']
            marker = " [OK]" if g > 0 else " [FAIL]"
            print(f"  {g:+5.1f}pp{marker}", end="")
        print()

    # ═══ PARETO FRONTIER ═══
    print(f"\n{'=' * 75}")
    print("PARETO FRONTIER: Max accuracy where drift >= -1.0pp")
    print(f"{'=' * 75}")
    pareto = [(k, v) for k, v in results.items() if v['drift'] >= -1.0]
    if pareto:
        pareto.sort(key=lambda x: -x[1]['acc'])
        for (theta, K), v in pareto[:5]:
            print(f"  theta={theta:.2f} K={K:>2d}: acc={v['acc']:.1f}% drift={v['drift']:+.1f}pp "
                  f"L-S={v['ls_gap']:+.1f}pp rate={v['update_rate']*100:.1f}%")
    else:
        print("  No config achieves drift >= -1.0pp")

    # ═══ BINARY QUESTIONS ═══
    print(f"\n{'=' * 75}")
    print("BINARY QUESTIONS")
    print(f"{'=' * 75}")

    # Q1: Accuracy varies < 1pp across θ_conf?
    for K in K_VALUES:
        accs = [results[(t, K)]['acc'] for t in THETA_VALUES]
        spread = max(accs) - min(accs)
        print(f"Q1 (K={K}): Accuracy spread across theta_conf: {spread:.1f}pp "
              f"{'ROBUST' if spread < 1.0 else 'SENSITIVE'}")

    # Q2: Accuracy varies < 1pp across K?
    for theta in THETA_VALUES:
        accs = [results[(theta, K)]['acc'] for K in K_VALUES]
        spread = max(accs) - min(accs)
        print(f"Q2 (theta={theta}): Accuracy spread across K: {spread:.1f}pp "
              f"{'ROBUST' if spread < 1.0 else 'SENSITIVE'}")

    # Q3: Clear optimal?
    best = max(pareto, key=lambda x: x[1]['acc']) if pareto else None
    if best:
        print(f"Q3: Best config: theta={best[0][0]:.2f} K={best[0][1]} "
              f"(acc={best[1]['acc']:.1f}%, drift={best[1]['drift']:+.1f}pp)")
    else:
        print("Q3: No config meets drift threshold")

    # Q4: Any config with drift > 0?
    positive = [(k, v) for k, v in results.items() if v['drift'] > 0]
    if positive:
        print(f"Q4: {len(positive)} configs with positive drift (learning NEVER hurts):")
        for (t, K), v in sorted(positive, key=lambda x: -x[1]['acc'])[:3]:
            print(f"     theta={t:.2f} K={K}: drift={v['drift']:+.1f}pp acc={v['acc']:.1f}%")
    else:
        print("Q4: NO config achieves positive drift")

    print("\nDONE.")


if __name__ == "__main__":
    main()
