"""
EXP-30: V-PHASE-PORTRAIT
==========================
Plot the system trajectory in state space.
Reveals fixed points, basins of attraction, limit cycles.

Run: cd backend && python scripts/exp30_phase_portrait.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF
)

N = 4000
WINDOW = 10  # record every 10 decisions


def run_trajectory(seed, strategy):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)

    scorer = make_scorer()
    static = make_scorer()
    pipeline = None
    if strategy == "PIPELINE":
        pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                       category_weights=CATEGORY_WEIGHTS)

    lc = 0
    prev_mu = scorer.centroids.copy()
    trajectory = []

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc += 1

        if strategy == "PIPELINE":
            pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)
        elif strategy == "RAW_SGD":
            scorer.update(fv, ci, result.action_index, correct, oa)
        # STATIC: no update

        if n % WINDOW == 0:
            acc = lc / n * 100
            velocity = np.linalg.norm(scorer.centroids - prev_mu) / WINDOW
            mean_conf = result.confidence  # approximate: last decision's confidence
            prev_mu = scorer.centroids.copy()

            trajectory.append({
                'n': n, 'acc': acc, 'vel': velocity, 'conf': mean_conf,
            })

    return trajectory


def main():
    print("=" * 80)
    print("EXP-30: V-PHASE-PORTRAIT")
    print("=" * 80)

    strategies = ["PIPELINE", "RAW_SGD", "STATIC"]
    all_traj = {s: [] for s in strategies}

    for s in strategies:
        for seed in SEEDS:
            t = run_trajectory(seed, s)
            all_traj[s].append(t)
        print(f"  {s} done ({len(SEEDS)} seeds)")

    n_points = len(all_traj["PIPELINE"][0])

    # Phase portrait A: (accuracy, velocity)
    print(f"\n{'=' * 80}")
    print("PHASE A: (accuracy, velocity) -- convergence dynamics")
    print(f"{'=' * 80}")
    print(f"  {'N':>5s}  {'P_acc':>6s}  {'P_vel':>10s}  {'R_acc':>6s}  {'R_vel':>10s}  {'S_acc':>6s}")
    print(f"  {'-' * 55}")

    # Sample every 20th point (every 200 decisions)
    for i in range(0, n_points, 20):
        n = all_traj["PIPELINE"][0][i]['n']
        p_acc = np.mean([t[i]['acc'] for t in all_traj["PIPELINE"]])
        p_vel = np.mean([t[i]['vel'] for t in all_traj["PIPELINE"]])
        r_acc = np.mean([t[i]['acc'] for t in all_traj["RAW_SGD"]])
        r_vel = np.mean([t[i]['vel'] for t in all_traj["RAW_SGD"]])
        s_acc = np.mean([t[i]['acc'] for t in all_traj["STATIC"]])
        print(f"  {n:>5d}  {p_acc:5.1f}%  {p_vel:.8f}  {r_acc:5.1f}%  {r_vel:.8f}  {s_acc:5.1f}%")

    # Phase portrait B: (accuracy, confidence)
    print(f"\n{'=' * 80}")
    print("PHASE B: (accuracy, confidence) -- feedback gain structure")
    print(f"{'=' * 80}")
    print(f"  {'N':>5s}  {'P_acc':>6s}  {'P_conf':>7s}  {'R_acc':>6s}  {'R_conf':>7s}")
    print(f"  {'-' * 40}")

    for i in range(0, n_points, 20):
        n = all_traj["PIPELINE"][0][i]['n']
        p_acc = np.mean([t[i]['acc'] for t in all_traj["PIPELINE"]])
        p_conf = np.mean([t[i]['conf'] for t in all_traj["PIPELINE"]])
        r_acc = np.mean([t[i]['acc'] for t in all_traj["RAW_SGD"]])
        r_conf = np.mean([t[i]['conf'] for t in all_traj["RAW_SGD"]])
        print(f"  {n:>5d}  {p_acc:5.1f}%  {p_conf:.4f}  {r_acc:5.1f}%  {r_conf:.4f}")

    # Fixed point analysis
    print(f"\n{'=' * 80}")
    print("FIXED POINT ANALYSIS (last 1000 decisions)")
    print(f"{'=' * 80}")

    for s in strategies:
        late_accs = []
        late_vels = []
        late_confs = []
        for t in all_traj[s]:
            for pt in t:
                if pt['n'] > 3000:
                    late_accs.append(pt['acc'])
                    late_vels.append(pt['vel'])
                    late_confs.append(pt['conf'])

        print(f"  {s}:")
        print(f"    acc:  {np.mean(late_accs):.1f}% +/- {np.std(late_accs):.2f}")
        print(f"    vel:  {np.mean(late_vels):.8f} +/- {np.std(late_vels):.8f}")
        print(f"    conf: {np.mean(late_confs):.4f} +/- {np.std(late_confs):.4f}")

    # Variance across seeds at key points
    print(f"\n{'=' * 80}")
    print("TRAJECTORY VARIANCE (across 5 seeds)")
    print(f"{'=' * 80}")
    for i in [0, 10, 50, 100, 200, 399]:  # N=10, 100, 500, 1000, 2000, 4000
        if i >= n_points:
            continue
        n = all_traj["PIPELINE"][0][i]['n']
        p_accs = [t[i]['acc'] for t in all_traj["PIPELINE"]]
        p_vels = [t[i]['vel'] for t in all_traj["PIPELINE"]]
        print(f"  N={n:>4d}: acc_spread={max(p_accs)-min(p_accs):.1f}pp  "
              f"vel_spread={max(p_vels)-min(p_vels):.8f}")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    # Q1: Single fixed point?
    p_spread = np.std([t[-1]['acc'] for t in all_traj["PIPELINE"]])
    print(f"Q1: Single fixed point? acc_std={p_spread:.2f}pp "
          f"{'YES' if p_spread < 1.0 else 'NO'}")

    # Q2: Limit cycle?
    # Check if late-stage velocity oscillates
    late_vels = []
    for t in all_traj["PIPELINE"]:
        vels = [pt['vel'] for pt in t if pt['n'] > 2000]
        late_vels.extend(vels)
    vel_std = np.std(late_vels)
    vel_mean = np.mean(late_vels)
    cv = vel_std / vel_mean if vel_mean > 0 else 0
    print(f"Q2: Limit cycle? vel_CV={cv:.2f} "
          f"{'YES (oscillating)' if cv > 1.0 else 'NO (stable)'}")

    # Q3: Raw SGD diverges?
    r_late = [t[-1]['acc'] for t in all_traj["RAW_SGD"]]
    p_late = [t[-1]['acc'] for t in all_traj["PIPELINE"]]
    diverges = np.mean(r_late) < np.mean(p_late) - 2.0
    print(f"Q3: Raw SGD different topology? raw={np.mean(r_late):.1f}% "
          f"pipe={np.mean(p_late):.1f}% {'YES' if diverges else 'NO'}")

    # Q4: Feedback gain constant or varies?
    early_confs = [t[5]['conf'] for t in all_traj["PIPELINE"]]  # N=50
    late_confs = [t[-1]['conf'] for t in all_traj["PIPELINE"]]  # N=4000
    conf_change = abs(np.mean(late_confs) - np.mean(early_confs))
    print(f"Q4: Feedback gain: early_conf={np.mean(early_confs):.4f} "
          f"late_conf={np.mean(late_confs):.4f} change={conf_change:.4f} "
          f"{'VARIES' if conf_change > 0.02 else 'CONST'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
