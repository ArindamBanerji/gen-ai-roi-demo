"""
EXP-33: V-LYAPUNOV-CANDIDATE
==============================
Empirical stability proof via Lyapunov function V = ||mu - mu*||^2.

Run: cd backend && python scripts/exp33_lyapunov.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF
)

N = 4000
WINDOW = 10


def run_lyapunov(seed, strategy):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)

    scorer = make_scorer()
    pipeline = None
    if strategy == "PIPELINE":
        pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                       category_weights=CATEGORY_WEIGHTS)

    # V(t) = ||mu(t) - mu*||^2 (Frobenius squared)
    trajectory = []

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)

        if strategy == "PIPELINE":
            pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)
        elif strategy == "RAW_SGD":
            scorer.update(fv, ci, result.action_index, correct, oa)

        if n % WINDOW == 0:
            V = float(np.sum((scorer.centroids - gt) ** 2))  # Frobenius squared
            trajectory.append({'n': n, 'V': V})

    return trajectory


def main():
    print("=" * 80)
    print("EXP-33: V-LYAPUNOV-CANDIDATE")
    print("V(t) = ||mu(t) - mu*||^2 (Frobenius distance squared from GT)")
    print("=" * 80)

    strategies = ["PIPELINE", "RAW_SGD", "STATIC"]
    all_traj = {s: [] for s in strategies}

    for s in strategies:
        for seed in SEEDS:
            t = run_lyapunov(seed, s)
            all_traj[s].append(t)
        print(f"  {s} done")

    n_points = len(all_traj["PIPELINE"][0])

    # V(t) trajectory
    print(f"\n{'=' * 80}")
    print("V(t) = ||mu - mu*||^2 (mean across 5 seeds)")
    print(f"{'=' * 80}")
    print(f"  {'N':>5s}  {'V_pipe':>10s}  {'V_raw':>10s}  {'V_static':>10s}  "
          f"{'dV_pipe':>10s}  {'dV_raw':>10s}")
    print(f"  {'-' * 60}")

    prev_V = {s: None for s in strategies}
    for i in range(0, n_points, 10):  # every 100 decisions
        n = all_traj["PIPELINE"][0][i]['n']
        line = f"  {n:>5d}"
        dVs = {}
        for s in strategies:
            V = np.mean([t[i]['V'] for t in all_traj[s]])
            line += f"  {V:>10.6f}"
            if prev_V[s] is not None:
                dV = (V - prev_V[s]) / (WINDOW * 10)  # per decision
                dVs[s] = dV
            prev_V[s] = V

        if dVs:
            line += f"  {dVs.get('PIPELINE', 0):>+10.6f}  {dVs.get('RAW_SGD', 0):>+10.6f}"
        print(line)

    # V_dot analysis
    print(f"\n{'=' * 80}")
    print("V_dot (dV/dN) by regime")
    print(f"{'=' * 80}")

    regimes = [
        ("Early (N=10-100)", 0, 10),
        ("Converging (100-500)", 10, 50),
        ("Steady (500-2000)", 50, 200),
        ("Late (2000-4000)", 200, 400),
    ]

    for label, i_start, i_end in regimes:
        i_end = min(i_end, n_points)
        for s in ["PIPELINE", "RAW_SGD"]:
            dVs = []
            for i in range(max(1, i_start), i_end):
                for t in all_traj[s]:
                    V_now = t[i]['V']
                    V_prev = t[i - 1]['V']
                    dV = (V_now - V_prev) / WINDOW
                    dVs.append(dV)
            if dVs:
                mean_dV = np.mean(dVs)
                neg_frac = sum(1 for d in dVs if d <= 0) / len(dVs) * 100
                print(f"  {label:>25s} {s:>10s}: mean_dV={mean_dV:+.8f} "
                      f"neg_frac={neg_frac:.0f}%")

    # Energy dissipation
    print(f"\n{'=' * 80}")
    print("ENERGY DISSIPATION D(t) = V_dot(raw) - V_dot(pipeline)")
    print(f"{'=' * 80}")

    for i in range(10, n_points, 20):
        n = all_traj["PIPELINE"][0][i]['n']
        if i < 1:
            continue
        pipe_dVs = []
        raw_dVs = []
        for t in all_traj["PIPELINE"]:
            pipe_dVs.append((t[i]['V'] - t[i-1]['V']) / WINDOW)
        for t in all_traj["RAW_SGD"]:
            raw_dVs.append((t[i]['V'] - t[i-1]['V']) / WINDOW)
        D = np.mean(raw_dVs) - np.mean(pipe_dVs)
        print(f"  N={n:>4d}: D={D:+.8f} "
              f"{'(pipeline absorbing noise)' if D > 0 else '(raw doing better)'}")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    # Q1: V_dot(pipeline) <= 0 for all t > 100?
    pipe_positive = 0
    pipe_total = 0
    for i in range(10, n_points):
        for t in all_traj["PIPELINE"]:
            dV = (t[i]['V'] - t[i-1]['V']) / WINDOW
            pipe_total += 1
            if dV > 0:
                pipe_positive += 1
    frac_neg = (pipe_total - pipe_positive) / pipe_total * 100 if pipe_total > 0 else 0
    print(f"Q1: V_dot(pipeline) <= 0 for t>100? neg_frac={frac_neg:.0f}% "
          f"{'YES (Lyapunov confirmed)' if frac_neg > 90 else 'NO (not always decreasing)'}")

    # Q2: V_dot(raw) > 0 for t > N*?
    raw_positive_late = 0
    raw_total_late = 0
    for i in range(100, n_points):
        for t in all_traj["RAW_SGD"]:
            dV = (t[i]['V'] - t[i-1]['V']) / WINDOW
            raw_total_late += 1
            if dV > 0:
                raw_positive_late += 1
    frac_pos = raw_positive_late / raw_total_late * 100 if raw_total_late > 0 else 0
    print(f"Q2: V_dot(raw) > 0 for late t? pos_frac={frac_pos:.0f}% "
          f"{'YES (raw diverging)' if frac_pos > 50 else 'NO'}")

    # Q3: D(t) increases with N?
    early_Ds = []
    late_Ds = []
    for i in range(10, n_points):
        for j, t_p in enumerate(all_traj["PIPELINE"]):
            t_r = all_traj["RAW_SGD"][j]
            dV_p = (t_p[i]['V'] - t_p[i-1]['V']) / WINDOW
            dV_r = (t_r[i]['V'] - t_r[i-1]['V']) / WINDOW
            D = dV_r - dV_p
            if t_p[i]['n'] < 1000:
                early_Ds.append(D)
            else:
                late_Ds.append(D)
    if early_Ds and late_Ds:
        print(f"Q3: D increases? early_D={np.mean(early_Ds):+.8f} "
              f"late_D={np.mean(late_Ds):+.8f} "
              f"{'YES' if np.mean(late_Ds) > np.mean(early_Ds) else 'NO'}")

    # Q4: Steady-state V(pipeline)
    steady_V = np.mean([t[-1]['V'] for t in all_traj["PIPELINE"]])
    print(f"Q4: Steady-state V(pipeline) = {steady_V:.6f}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
