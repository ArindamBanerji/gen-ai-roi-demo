"""
EXP-20: V-LARGER-SHIFTS
=========================
Where do shifts actually cross decision boundaries?

Run: cd backend && python scripts/exp20_larger_shifts.py
Time: ~10 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF
)

SHIFTS = [0.25, 0.50, 0.75, 1.00, 1.50]
N_PRE = 1000
N_POST = 2000
POST_CHECKS = [10, 50, 100, 200, 500, 1000, 2000]
SEEDS_SHORT = [42, 123, 777]


def run_shift(seed, delta, strategy):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)
    scorer = make_scorer()
    static = make_scorer()
    pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                   category_weights=CATEGORY_WEIGHTS) if strategy == "PIPELINE" else None

    lc_pre = 0
    for n in range(1, N_PRE + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc_pre += 1
        if strategy == "PIPELINE":
            pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)
        elif strategy == "RAW_SGD":
            scorer.update(fv, ci, result.action_index, correct, oa)

    pre_acc = lc_pre / N_PRE * 100

    # Shift
    direction = rng.normal(0, 1, gt.shape)
    direction = direction / np.linalg.norm(direction) * delta
    gt_shifted = gt + direction

    lc_post = 0
    cp = {}
    for n in range(1, N_POST + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt_shifted, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc_post += 1
        if strategy == "PIPELINE":
            pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)
        elif strategy == "RAW_SGD":
            scorer.update(fv, ci, result.action_index, correct, oa)

        if n in POST_CHECKS:
            cp[n] = lc_post / n * 100

    return {'pre': pre_acc, 'post': cp}


def main():
    print("=" * 80)
    print("EXP-20: V-LARGER-SHIFTS")
    print("=" * 80)

    for strategy in ["PIPELINE", "RAW_SGD", "STATIC"]:
        print(f"\n  {strategy}:")
        print(f"  {'delta':>6s}  {'pre':>6s}", end="")
        for n in POST_CHECKS:
            print(f"  {'N='+str(n):>7s}", end="")
        print()
        print(f"  {'-' * 75}")

        for delta in SHIFTS:
            runs = [run_shift(s, delta, strategy) for s in SEEDS_SHORT]
            pre = np.mean([r['pre'] for r in runs])
            print(f"  {delta:>6.2f}  {pre:5.1f}%", end="")
            for n in POST_CHECKS:
                acc = np.mean([r['post'][n] for r in runs])
                gap = acc - pre
                print(f"  {gap:>+5.1f}pp", end="")
            print()

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    for delta in SHIFTS:
        pipe_runs = [run_shift(s, delta, "PIPELINE") for s in SEEDS_SHORT]
        pre = np.mean([r['pre'] for r in pipe_runs])
        post_10 = np.mean([r['post'][10] for r in pipe_runs])
        drop = pre - post_10
        if drop > 2:
            print(f"Q1: Visible drop (>2pp) first at delta={delta} (drop={drop:.1f}pp)")
            break
    else:
        print(f"Q1: No visible drop at any tested delta")

    # Q4: Pipeline prevents recovery at large delta?
    for delta in [0.75, 1.00, 1.50]:
        pipe_1000 = np.mean([run_shift(s, delta, "PIPELINE") for s in SEEDS_SHORT[:1]][0]['post'].get(1000, 0))
        raw_1000 = np.mean([run_shift(s, delta, "RAW_SGD") for s in SEEDS_SHORT[:1]][0]['post'].get(1000, 0))
        if raw_1000 > pipe_1000 + 2:
            print(f"Q4: Raw recovers better than pipeline at delta={delta}: "
                  f"raw={raw_1000:.1f}% pipe={pipe_1000:.1f}%")

    print("\nDONE.")


if __name__ == "__main__":
    main()
