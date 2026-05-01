"""
EXP-8: V-WEIGHT-NO-EVENTS
===========================
Same as EXP-7 but with NO events. Does the weight trajectory
still show the same pattern without shift/quality-drop/restore?

Run: cd backend && python scripts/exp8_no_events.py
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


def run_no_events(seed):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)

    scorer_pipe = make_scorer()
    scorer_raw = make_scorer()
    scorer_static = make_scorer()

    pipeline = ThreeStagePipeline(scorer_pipe, K=K_BATCH, theta_conf=THETA_CONF,
                                   category_weights=CATEGORY_WEIGHTS)

    lc_pipe, lc_raw, lc_static = 0, 0, 0
    timeline = []

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        r_p = scorer_pipe.score(fv, ci)
        if r_p.action_index == oa: lc_pipe += 1
        pipeline.process(fv, ci, r_p.action_index, r_p.action_index == oa, oa, r_p.confidence)

        r_r = scorer_raw.score(fv, ci)
        if r_r.action_index == oa: lc_raw += 1
        scorer_raw.update(fv, ci, r_r.action_index, r_r.action_index == oa, oa)

        r_s = scorer_static.score(fv, ci)
        if r_s.action_index == oa: lc_static += 1

        if n % WINDOW == 0:
            ap = lc_pipe / n * 100
            ar = lc_raw / n * 100
            ast = lc_static / n * 100
            learn_c = ap - ast
            pipe_c = ap - ar
            timeline.append({
                'n': n, 'acc_pipe': ap, 'acc_raw': ar, 'acc_static': ast,
                'learn_contrib': learn_c, 'pipeline_contrib': pipe_c,
            })

    return timeline


def main():
    print("=" * 80)
    print("EXP-8: V-WEIGHT-NO-EVENTS (steady environment, no shift/quality changes)")
    print("=" * 80)

    all_tl = [run_no_events(s) for s in SEEDS]
    print(f"  {len(SEEDS)} seeds done")

    n_points = len(all_tl[0])

    print(f"\n{'=' * 80}")
    print("TIME SERIES (mean across seeds)")
    print(f"{'=' * 80}")
    print(f"  {'N':>5s}  {'Pipe':>6s}  {'Raw':>6s}  {'Static':>6s}  {'L_contr':>7s}  {'P_contr':>7s}")
    print(f"  {'-' * 45}")

    for i in range(n_points):
        n = all_tl[0][i]['n']
        vals = {k: np.mean([t[i][k] for t in all_tl])
                for k in ['acc_pipe', 'acc_raw', 'acc_static', 'learn_contrib', 'pipeline_contrib']}
        print(f"  {n:>5d}  {vals['acc_pipe']:5.1f}%  {vals['acc_raw']:5.1f}%  "
              f"{vals['acc_static']:5.1f}%  {vals['learn_contrib']:+5.1f}pp  "
              f"{vals['pipeline_contrib']:+5.1f}pp")

    # Weight decomposition (same windows as EXP-7)
    print(f"\n{'=' * 80}")
    print("WEIGHT DECOMPOSITION (no events)")
    print(f"{'=' * 80}")

    windows = [
        ("Early (0-100)", 0, 100),
        ("Converging (100-300)", 100, 300),
        ("Steady (300-1000)", 300, 1000),
        ("Steady (1000-2000)", 1000, 2000),
        ("Late (2000-3000)", 2000, 3000),
        ("Final (3000-4000)", 3000, 4000),
    ]

    print(f"  {'Window':>25s}  {'w_centroid':>10s}  {'w_pipeline':>10s}")
    print(f"  {'-' * 50}")

    for label, n_start, n_end in windows:
        lcs = []
        pcs = []
        for i in range(n_points):
            n = all_tl[0][i]['n']
            if n_start < n <= n_end:
                lcs.append(np.mean([t[i]['learn_contrib'] for t in all_tl]))
                pcs.append(np.mean([t[i]['pipeline_contrib'] for t in all_tl]))
        if lcs:
            ml = np.mean(lcs)
            mp = np.mean(pcs)
            total = abs(ml) + abs(mp) if (abs(ml) + abs(mp)) > 0 else 1
            print(f"  {label:>25s}  {ml/total:+8.2f}  {mp/total:+8.2f}")

    # Compare with EXP-7 trajectory
    print(f"\n{'=' * 80}")
    print("COMPARISON: No events vs EXP-7 (with events)")
    print("Read the pipeline_contrib column at comparable N values")
    print(f"{'=' * 80}")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    early_pc = np.mean([all_tl[s][5]['pipeline_contrib'] for s in range(len(SEEDS))])
    late_pc = np.mean([all_tl[s][-1]['pipeline_contrib'] for s in range(len(SEEDS))])
    print(f"Q1: Pipeline contrib grows without events? "
          f"N=300: {early_pc:+.1f}pp N=4000: {late_pc:+.1f}pp "
          f"{'YES' if late_pc > early_pc + 0.5 else 'NO'}")

    # Does raw SGD degrade without events?
    raw_500 = np.mean([all_tl[s][9]['acc_raw'] for s in range(len(SEEDS))])
    raw_4000 = np.mean([all_tl[s][-1]['acc_raw'] for s in range(len(SEEDS))])
    print(f"Q2: Raw degrades without events? N=500: {raw_500:.1f}% N=4000: {raw_4000:.1f}% "
          f"{'YES' if raw_4000 < raw_500 - 1.0 else 'NO'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
