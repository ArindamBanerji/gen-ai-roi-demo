"""
EXP-7: V-REGIME-TRANSITIONS
==============================
Question: How do mechanism contributions change across regimes?

Run: cd backend && python scripts/exp7_regime_transitions.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF, SIGMA_BAR
)

N_TOTAL = 4000
WINDOW = 50  # measure every 50 decisions
SHIFT_DELTA = 0.15
NOISE_HIGH = 0.30
NOISE_NORMAL = 0.15


def classify_regime(velocity, prev_velocity, accuracy_trend):
    """Classify regime from centroid velocity."""
    if prev_velocity is not None and velocity > 2 * prev_velocity and velocity > 0.005:
        return "R4_shift"
    if velocity > 0.01:
        return "R1_cold"
    if velocity > 0.001:
        return "R2_converging"
    return "R3_steady"


def run_lifecycle(seed):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)

    # Three scorers: pipeline, raw, static
    scorer_pipe = make_scorer()
    scorer_raw = make_scorer()
    scorer_static = make_scorer()

    pipeline = ThreeStagePipeline(scorer_pipe, K=K_BATCH, theta_conf=THETA_CONF,
                                   category_weights=CATEGORY_WEIGHTS)

    lc_pipe, lc_raw, lc_static = 0, 0, 0
    prev_mu_pipe = scorer_pipe.centroids.copy()
    prev_velocity = None

    timeline = []

    current_oracle_noise = NOISE_NORMAL

    for n in range(1, N_TOTAL + 1):
        # ═══ EVENTS ═══
        if n == 1001:
            # Distribution shift at N=1000
            direction = rng.normal(0, 1, gt.shape)
            direction = direction / np.linalg.norm(direction) * SHIFT_DELTA
            gt = gt + direction

        if n == 2001:
            # Quality drop at N=2000
            current_oracle_noise = NOISE_HIGH

        if n == 3001:
            # Quality restore at N=3000
            current_oracle_noise = NOISE_NORMAL

        # ═══ DECISION ═══
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng, noise_rate=current_oracle_noise)

        # Pipeline scorer
        r_pipe = scorer_pipe.score(fv, ci)
        pipe_correct = (r_pipe.action_index == oa)
        if pipe_correct: lc_pipe += 1
        pipeline.process(fv, ci, r_pipe.action_index, pipe_correct, oa, r_pipe.confidence)

        # Raw scorer
        r_raw = scorer_raw.score(fv, ci)
        raw_correct = (r_raw.action_index == oa)
        if raw_correct: lc_raw += 1
        scorer_raw.update(fv, ci, r_raw.action_index, raw_correct, oa)

        # Static scorer
        r_static = scorer_static.score(fv, ci)
        if r_static.action_index == oa: lc_static += 1

        # ═══ WINDOW METRICS ═══
        if n % WINDOW == 0:
            # Accuracy (cumulative to this point)
            acc_pipe = lc_pipe / n * 100
            acc_raw = lc_raw / n * 100
            acc_static = lc_static / n * 100

            # Frobenius velocity
            velocity = np.linalg.norm(scorer_pipe.centroids - prev_mu_pipe) / WINDOW
            prev_mu_pipe = scorer_pipe.centroids.copy()

            # Regime classification
            regime = classify_regime(velocity, prev_velocity, None)
            prev_velocity = velocity

            # Pipeline update rate (reset for this window)
            total_gate = pipeline.stats['gate_blocked'] + pipeline.stats['gate_passed']
            update_rate = pipeline.stats['updates'] / total_gate if total_gate > 0 else 0

            # Contributions
            learn_contrib = acc_pipe - acc_static  # what learning adds
            pipeline_contrib = acc_pipe - acc_raw   # what filtering adds

            timeline.append({
                'n': n,
                'acc_pipe': acc_pipe,
                'acc_raw': acc_raw,
                'acc_static': acc_static,
                'velocity': velocity,
                'regime': regime,
                'update_rate': update_rate,
                'learn_contrib': learn_contrib,
                'pipeline_contrib': pipeline_contrib,
                'oracle_noise': current_oracle_noise,
            })

    return timeline


def main():
    print("=" * 75)
    print("EXP-7: V-REGIME-TRANSITIONS (4000-decision lifecycle)")
    print("Events: N=1000 shift, N=2000 quality drop, N=3000 restore")
    print("=" * 75)

    all_timelines = [run_lifecycle(s) for s in SEEDS]
    print(f"  {len(SEEDS)} seeds done")

    # ═══ TIME SERIES ═══
    print(f"\n{'=' * 100}")
    print("TIME SERIES (mean across seeds)")
    print(f"{'=' * 100}")
    print(f"  {'N':>5s}  {'Pipe':>6s}  {'Raw':>6s}  {'Static':>6s}  "
          f"{'L_contr':>7s}  {'P_contr':>7s}  {'Vel':>8s}  {'Rate':>6s}  {'Regime':>12s}  {'Event':>10s}")
    print(f"  {'-' * 95}")

    n_points = len(all_timelines[0])
    for i in range(n_points):
        n = all_timelines[0][i]['n']

        vals = {k: np.mean([t[i][k] for t in all_timelines])
                for k in ['acc_pipe', 'acc_raw', 'acc_static', 'velocity',
                           'update_rate', 'learn_contrib', 'pipeline_contrib']}

        # Most common regime
        regimes = [t[i]['regime'] for t in all_timelines]
        regime = max(set(regimes), key=regimes.count)

        event = ""
        if n == 1000: event = "<- SHIFT"
        elif n == 2000: event = "<- NOISEup"
        elif n == 3000: event = "<- RESTORE"

        print(f"  {n:>5d}  {vals['acc_pipe']:5.1f}%  {vals['acc_raw']:5.1f}%  "
              f"{vals['acc_static']:5.1f}%  {vals['learn_contrib']:+5.1f}pp  "
              f"{vals['pipeline_contrib']:+5.1f}pp  {vals['velocity']:.6f}  "
              f"{vals['update_rate']*100:4.1f}%  {regime:>12s}  {event}")

    # ═══ WEIGHT DECOMPOSITION TABLE ═══
    print(f"\n{'=' * 90}")
    print("WEIGHT DECOMPOSITION BY REGIME WINDOW")
    print(f"{'=' * 90}")
    print(f"  {'Window':>20s}  {'N range':>12s}  {'w_centroid':>10s}  {'w_pipeline':>10s}  {'w_residual':>10s}")
    print(f"  {'-' * 70}")

    windows = [
        ("R1 (cold start)", 0, 100),
        ("R2 (converging)", 100, 300),
        ("R3 (steady)", 300, 1000),
        ("R4 (shift)", 1000, 1200),
        ("R2 (recovery)", 1200, 1500),
        ("R3 (re-steady)", 1500, 2000),
        ("Quality drop", 2000, 2200),
        ("Adapted", 2200, 3000),
        ("Restored", 3000, 3500),
        ("Final steady", 3500, 4000),
    ]

    for label, n_start, n_end in windows:
        # Find timeline entries in this window
        lc_vals = []
        pc_vals = []
        for i in range(n_points):
            n = all_timelines[0][i]['n']
            if n_start < n <= n_end:
                lc = np.mean([t[i]['learn_contrib'] for t in all_timelines])
                pc = np.mean([t[i]['pipeline_contrib'] for t in all_timelines])
                lc_vals.append(lc)
                pc_vals.append(pc)

        if lc_vals:
            mean_lc = np.mean(lc_vals)
            mean_pc = np.mean(pc_vals)
            total = abs(mean_lc) + abs(mean_pc) if (abs(mean_lc) + abs(mean_pc)) > 0 else 1
            w_cent = mean_lc / total if total > 0 else 0
            w_pipe = mean_pc / total if total > 0 else 0
            w_res = 1 - abs(w_cent) - abs(w_pipe)
            print(f"  {label:>20s}  {n_start:>5d}-{n_end:>5d}  "
                  f"{w_cent:+8.2f}  {w_pipe:+8.2f}  {w_res:+8.2f}")

    # ═══ BINARY QUESTIONS ═══
    print(f"\n{'=' * 75}")
    print("BINARY QUESTIONS")
    print(f"{'=' * 75}")

    # Q1: Do weights change across regimes?
    # Compare steady-state (300-1000) vs shift (1000-1200)
    steady_lc = []
    shift_lc = []
    for i in range(n_points):
        n = all_timelines[0][i]['n']
        lc = np.mean([t[i]['learn_contrib'] for t in all_timelines])
        if 300 < n <= 1000: steady_lc.append(lc)
        if 1000 < n <= 1200: shift_lc.append(lc)

    if steady_lc and shift_lc:
        change = abs(np.mean(shift_lc) - np.mean(steady_lc))
        print(f"Q1: Weights change R3->R4? steady_lc={np.mean(steady_lc):+.2f}pp "
              f"shift_lc={np.mean(shift_lc):+.2f}pp change={change:.2f}pp "
              f"{'YES' if change > 0.5 else 'NO'}")

    # Q2: w_centroid increases within 50 decisions of shift?
    shift_window = []
    pre_shift = []
    for i in range(n_points):
        n = all_timelines[0][i]['n']
        lc = np.mean([t[i]['learn_contrib'] for t in all_timelines])
        if 950 < n <= 1000: pre_shift.append(lc)
        if 1000 < n <= 1050: shift_window.append(lc)

    if pre_shift and shift_window:
        increases = np.mean(shift_window) > np.mean(pre_shift)
        print(f"Q2: w_centroid increases post-shift? pre={np.mean(pre_shift):+.2f}pp "
              f"post={np.mean(shift_window):+.2f}pp {'YES' if increases else 'NO'}")

    # Q3: Conservation fires within 100 decisions of quality drop?
    # Proxy: does accuracy drop > 5pp in window 2000-2100?
    pre_drop = []
    post_drop = []
    for i in range(n_points):
        n = all_timelines[0][i]['n']
        acc = np.mean([t[i]['acc_pipe'] for t in all_timelines])
        if 1900 < n <= 2000: pre_drop.append(acc)
        if 2000 < n <= 2100: post_drop.append(acc)

    if pre_drop and post_drop:
        drop = np.mean(pre_drop) - np.mean(post_drop)
        print(f"Q3: Quality drop detected? acc drop={drop:+.1f}pp "
              f"{'YES (visible)' if drop > 2.0 else 'NO (too gradual)'}")

    # Q4: System returns to pre-drop accuracy within 200 decisions of restore?
    pre_drop_acc = np.mean(pre_drop) if pre_drop else 0
    restore_window = []
    for i in range(n_points):
        n = all_timelines[0][i]['n']
        acc = np.mean([t[i]['acc_pipe'] for t in all_timelines])
        if 3000 < n <= 3200: restore_window.append(acc)

    if restore_window:
        recovered = np.mean(restore_window) >= pre_drop_acc - 2.0
        print(f"Q4: Recovery within 200 of restore? "
              f"acc@3200={np.mean(restore_window):.1f}% vs pre-drop={pre_drop_acc:.1f}% "
              f"{'YES' if recovered else 'NO'}")

    # Q5: Any regime where raw beats pipeline?
    raw_wins = []
    for i in range(n_points):
        n = all_timelines[0][i]['n']
        pc = np.mean([t[i]['pipeline_contrib'] for t in all_timelines])
        if pc < -0.5:  # pipeline hurts by >0.5pp
            raw_wins.append((n, pc))

    if raw_wins:
        print(f"Q5: Raw beats pipeline? YES at N={[r[0] for r in raw_wins[:5]]}...")
    else:
        print(f"Q5: Raw beats pipeline? NO -- pipeline never hurts by >0.5pp")

    print("\nDONE.")


if __name__ == "__main__":
    main()
