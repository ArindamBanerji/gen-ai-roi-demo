"""
EXP-9: V-WEIGHT-PER-SEED
==========================
Is the weight trajectory deterministic or path-dependent?

Run: cd backend && python scripts/exp9_per_seed.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF
)

N = 4000
WINDOW = 50


def run_per_seed(seed):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)

    s_pipe = make_scorer()
    s_raw = make_scorer()
    s_static = make_scorer()
    pipeline = ThreeStagePipeline(s_pipe, K=K_BATCH, theta_conf=THETA_CONF,
                                   category_weights=CATEGORY_WEIGHTS)

    lc_p, lc_r, lc_s = 0, 0, 0
    timeline = []

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        rp = s_pipe.score(fv, ci)
        if rp.action_index == oa: lc_p += 1
        pipeline.process(fv, ci, rp.action_index, rp.action_index == oa, oa, rp.confidence)

        rr = s_raw.score(fv, ci)
        if rr.action_index == oa: lc_r += 1
        s_raw.update(fv, ci, rr.action_index, rr.action_index == oa, oa)

        rs = s_static.score(fv, ci)
        if rs.action_index == oa: lc_s += 1

        if n % WINDOW == 0:
            ap, ar, ast = lc_p/n*100, lc_r/n*100, lc_s/n*100
            timeline.append({'n': n, 'w_pipeline': ap - ar, 'w_centroid': ap - ast,
                             'acc_pipe': ap, 'acc_raw': ar})

    return timeline


def main():
    print("=" * 80)
    print("EXP-9: V-WEIGHT-PER-SEED (5 individual trajectories)")
    print("=" * 80)

    all_tl = {s: run_per_seed(s) for s in SEEDS}
    n_points = len(list(all_tl.values())[0])

    # Per-seed w_pipeline at key checkpoints
    print(f"\n  w_pipeline (pipe_acc - raw_acc) per seed:")
    print(f"  {'N':>5s}", end="")
    for s in SEEDS:
        print(f"  {'seed_'+str(s):>10s}", end="")
    print(f"  {'mean':>8s}  {'std':>6s}  {'spread':>7s}")
    print(f"  {'-' * 75}")

    for i in range(0, n_points, 10):
        n = list(all_tl.values())[0][i]['n']
        vals = [all_tl[s][i]['w_pipeline'] for s in SEEDS]
        print(f"  {n:>5d}", end="")
        for s in SEEDS:
            print(f"  {all_tl[s][i]['w_pipeline']:>+8.1f}pp", end="")
        print(f"  {np.mean(vals):>+6.1f}pp  {np.std(vals):>5.1f}  {max(vals)-min(vals):>5.1f}pp")

    # Variance over time
    print(f"\n{'=' * 80}")
    print("VARIANCE OF w_pipeline ACROSS SEEDS")
    print(f"{'=' * 80}")
    print(f"  {'N':>5s}  {'Var':>8s}  {'Std':>8s}  {'Spread':>8s}")
    print(f"  {'-' * 35}")

    for i in range(0, n_points, 4):
        n = list(all_tl.values())[0][i]['n']
        vals = [all_tl[s][i]['w_pipeline'] for s in SEEDS]
        print(f"  {n:>5d}  {np.var(vals):>8.2f}  {np.std(vals):>8.2f}  {max(vals)-min(vals):>6.1f}pp")

    # Do all seeds show same monotonic trend?
    print(f"\n{'=' * 80}")
    print("MONOTONICITY CHECK: Does w_pipeline increase for each seed?")
    print(f"{'=' * 80}")
    for s in SEEDS:
        early = np.mean([all_tl[s][i]['w_pipeline'] for i in range(5, 15)])
        late = np.mean([all_tl[s][i]['w_pipeline'] for i in range(n_points-10, n_points)])
        increases = late > early
        print(f"  seed {s}: early={early:+.1f}pp late={late:+.1f}pp {'INCREASES' if increases else 'DECREASES'}")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    late_stds = [np.std([all_tl[s][i]['w_pipeline'] for s in SEEDS])
                 for i in range(n_points-20, n_points)]
    print(f"Q1: Var(w_pipeline) at late stage: mean_std={np.mean(late_stds):.2f}pp")
    print(f"    Deterministic (<1pp std)? {'YES' if np.mean(late_stds) < 1.0 else 'NO'}")

    all_increase = all(
        np.mean([all_tl[s][i]['w_pipeline'] for i in range(n_points-10, n_points)]) >
        np.mean([all_tl[s][i]['w_pipeline'] for i in range(5, 15)])
        for s in SEEDS
    )
    print(f"Q2: All seeds show same trend? {'YES' if all_increase else 'NO'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
