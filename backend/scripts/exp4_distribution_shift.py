"""
EXP-4: V-DISTRIBUTION-SHIFT
=============================
Question: Can the system adapt when the environment changes?

Run: cd backend && python scripts/exp4_distribution_shift.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF, SIGMA_BAR
)

N_PRE = 1000
N_POST = 1000
SHIFT_MAGNITUDES = [0.05, 0.10, 0.15, 0.25]
POST_CHECKPOINTS = [10, 25, 50, 100, 200, 500, 1000]


def run_shift_exp(seed, delta, use_pipeline):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)

    scorer = make_scorer()
    pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                   category_weights=CATEGORY_WEIGHTS) if use_pipeline else None

    # Phase 1: converge
    lc_pre = 0
    for n in range(1, N_PRE + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc_pre += 1
        if use_pipeline:
            pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)
        else:
            scorer.update(fv, ci, result.action_index, correct, oa)

    pre_acc = lc_pre / N_PRE * 100
    pre_update_rate = pipeline.update_rate if pipeline else 1.0

    # Phase 2: shift GT
    direction = rng.normal(0, 1, gt.shape)
    direction = direction / np.linalg.norm(direction) * delta
    gt_shifted = gt + direction

    # Reset pipeline stats for post-shift measurement
    if pipeline:
        pipeline.stats = {'gate_blocked': 0, 'gate_passed': 0,
                          'batch_total': 0, 'batch_sig': 0,
                          'batch_rej': 0, 'updates': 0}

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
        if use_pipeline:
            pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)
        else:
            scorer.update(fv, ci, result.action_index, correct, oa)

        if n in POST_CHECKPOINTS:
            cp[n] = lc_post / n * 100

    post_update_rate = pipeline.update_rate if pipeline else 1.0

    return {
        'pre_acc': pre_acc,
        'post_checkpoints': cp,
        'pre_update_rate': pre_update_rate,
        'post_update_rate': post_update_rate,
    }


def main():
    print("=" * 75)
    print("EXP-4: V-DISTRIBUTION-SHIFT")
    print("=" * 75)

    for label, use_pipe in [("LEARN_pipeline", True), ("LEARN_raw", False)]:
        print(f"\n{'=' * 75}")
        print(f"STRATEGY: {label}")
        print(f"{'=' * 75}")

        for delta in SHIFT_MAGNITUDES:
            all_r = [run_shift_exp(s, delta, use_pipe) for s in SEEDS]

            pre_acc = np.mean([r['pre_acc'] for r in all_r])
            print(f"\n  δ={delta:.2f} (pre-shift acc: {pre_acc:.1f}%)")
            print(f"  {'N_post':>6s}  {'Accuracy':>8s}  {'Δ from pre':>10s}")
            print(f"  {'-' * 30}")

            recovery_n = "never"
            for n in POST_CHECKPOINTS:
                vals = [r['post_checkpoints'][n] for r in all_r]
                m = np.mean(vals)
                gap = m - pre_acc
                if gap >= -2.0 and recovery_n == "never":
                    recovery_n = str(n)
                print(f"  {n:>6d}  {m:6.1f}%  {gap:+8.1f}pp")

            print(f"  Recovery to within 2pp of pre-shift: N={recovery_n}")

            if use_pipe:
                pre_ur = np.mean([r['pre_update_rate'] for r in all_r])
                post_ur = np.mean([r['post_update_rate'] for r in all_r])
                ratio = post_ur / pre_ur if pre_ur > 0 else float('inf')
                print(f"  Update rate: pre={pre_ur:.3f}, post={post_ur:.3f}, ratio={ratio:.1f}x")

    # ═══ BINARY QUESTIONS (at δ=0.15) ═══
    print(f"\n{'=' * 75}")
    print("BINARY QUESTIONS (δ=0.15)")
    print(f"{'=' * 75}")

    pipe_r = [run_shift_exp(s, 0.15, True) for s in SEEDS]
    raw_r = [run_shift_exp(s, 0.15, False) for s in SEEDS]

    pre_ur = np.mean([r['pre_update_rate'] for r in pipe_r])
    post_ur = np.mean([r['post_update_rate'] for r in pipe_r])
    print(f"Q1: Pipeline update rate increases post-shift? "
          f"pre={pre_ur:.3f} post={post_ur:.3f} "
          f"{'YES' if post_ur > pre_ur * 1.2 else 'NO'} ({post_ur/pre_ur:.1f}x)")

    pipe_200 = np.mean([r['post_checkpoints'][200] for r in pipe_r])
    pipe_pre = np.mean([r['pre_acc'] for r in pipe_r])
    print(f"Q2: Pipeline recovers within 200? "
          f"acc@200={pipe_200:.1f}% vs pre={pipe_pre:.1f}% "
          f"{'YES' if pipe_200 >= pipe_pre - 2.0 else 'NO'}")

    raw_200 = np.mean([r['post_checkpoints'][200] for r in raw_r])
    raw_pre = np.mean([r['pre_acc'] for r in raw_r])
    pipe_gap = pipe_200 - pipe_pre
    raw_gap = raw_200 - raw_pre
    print(f"Q3: Raw SGD vs pipeline recovery at N=200: "
          f"raw={raw_gap:+.1f}pp pipe={pipe_gap:+.1f}pp "
          f"{'FASTER' if raw_gap > pipe_gap else 'SLOWER' if raw_gap < pipe_gap else 'SAME'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
