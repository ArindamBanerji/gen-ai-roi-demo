"""
EXP-25: V-EFFECTIVE-PARAMETERS
================================
Directly measure the effective parameters at each checkpoint.

Run: cd backend && python scripts/exp25_effective_params.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF, SIGMA_BAR
)

N = 4000
WINDOW = 50


def run_effective_params(seed):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)

    scorer = make_scorer()
    pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                   category_weights=CATEGORY_WEIGHTS)

    prev_mu = scorer.centroids.copy()
    window_decisions = 0
    window_gated = 0
    window_passed = 0
    window_confs = []
    lc = 0
    timeline = []

    # Track per-window pipeline stats
    prev_pipe_updates = 0
    prev_pipe_sig = 0
    prev_pipe_total = 0

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc += 1

        window_confs.append(result.confidence)
        window_decisions += 1

        if result.confidence > THETA_CONF:
            window_gated += 1
        else:
            window_passed += 1

        pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)

        if n % WINDOW == 0:
            # Effective gate threshold
            confs = np.array(window_confs)
            gate_rejection = window_gated / window_decisions if window_decisions > 0 else 0
            theta_eff = np.percentile(confs, gate_rejection * 100) if len(confs) > 0 else THETA_CONF

            # Effective update rate
            new_updates = pipeline.stats['updates'] - prev_pipe_updates
            new_sig = pipeline.stats['batch_sig'] - prev_pipe_sig
            new_total = pipeline.stats['batch_total'] - prev_pipe_total
            sig_rate = new_sig / new_total if new_total > 0 else 0

            # Effective learning rate (centroid motion)
            mu_motion = np.linalg.norm(scorer.centroids - prev_mu)
            eta_eff = mu_motion / WINDOW  # per decision

            # Accuracy and other state
            acc = lc / n * 100
            mean_conf = np.mean(confs)
            pct_above_80 = np.mean(confs > 0.80) * 100
            pct_above_60 = np.mean(confs > 0.60) * 100
            frobenius = float(np.linalg.norm(scorer.centroids - base_mu))

            timeline.append({
                'n': n, 'acc': acc,
                'theta_eff': theta_eff,
                'gate_rejection': gate_rejection * 100,
                'sig_rate': sig_rate * 100,
                'eta_eff': eta_eff,
                'mean_conf': mean_conf,
                'pct_above_80': pct_above_80,
                'pct_above_60': pct_above_60,
                'frobenius': frobenius,
                'updates_in_window': new_updates,
            })

            # Reset window
            prev_mu = scorer.centroids.copy()
            prev_pipe_updates = pipeline.stats['updates']
            prev_pipe_sig = pipeline.stats['batch_sig']
            prev_pipe_total = pipeline.stats['batch_total']
            window_decisions = 0
            window_gated = 0
            window_passed = 0
            window_confs = []

    return timeline


def main():
    print("=" * 80)
    print("EXP-25: V-EFFECTIVE-PARAMETERS")
    print("=" * 80)

    all_tl = [run_effective_params(s) for s in SEEDS]
    print(f"  {len(SEEDS)} seeds done")

    n_points = len(all_tl[0])

    # Effective parameter trajectories
    print(f"\n{'=' * 80}")
    print("EFFECTIVE PARAMETER TRAJECTORIES (mean across seeds)")
    print(f"{'=' * 80}")
    print(f"  {'N':>5s}  {'acc':>5s}  {'theta_eff':>9s}  {'gate_rej%':>9s}  "
          f"{'sig_rate%':>9s}  {'eta_eff':>10s}  {'mean_conf':>9s}  {'%>0.80':>6s}  {'%>0.60':>6s}")
    print(f"  {'-' * 85}")

    for i in range(0, n_points, 4):  # every 200 decisions
        n = all_tl[0][i]['n']
        vals = {k: np.mean([t[i][k] for t in all_tl])
                for k in ['acc', 'theta_eff', 'gate_rejection', 'sig_rate',
                           'eta_eff', 'mean_conf', 'pct_above_80', 'pct_above_60']}
        print(f"  {n:>5d}  {vals['acc']:4.1f}%  {vals['theta_eff']:>9.4f}  "
              f"{vals['gate_rejection']:>7.1f}%  {vals['sig_rate']:>7.1f}%  "
              f"{vals['eta_eff']:>10.8f}  {vals['mean_conf']:>9.4f}  "
              f"{vals['pct_above_80']:>5.1f}%  {vals['pct_above_60']:>5.1f}%")

    # Correlation analysis
    print(f"\n{'=' * 80}")
    print("CORRELATION: state variables vs pipeline contribution")
    print(f"{'=' * 80}")

    # Collect all (state, pipeline_contrib) pairs
    # Use pipeline_contrib ≈ eta_eff (centroid motion) as proxy
    state_vars = ['acc', 'mean_conf', 'pct_above_80', 'gate_rejection', 'frobenius']
    target = 'eta_eff'

    all_states = {v: [] for v in state_vars}
    all_targets = []

    for tl in all_tl:
        for pt in tl:
            for v in state_vars:
                all_states[v].append(pt[v])
            all_targets.append(pt[target])

    target_arr = np.array(all_targets)
    for v in state_vars:
        state_arr = np.array(all_states[v])
        if np.std(state_arr) > 0 and np.std(target_arr) > 0:
            r = np.corrcoef(state_arr, target_arr)[0, 1]
            print(f"  corr({v}, {target}) = {r:+.4f}")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    # Q1: theta_eff increases monotonically?
    early_theta = np.mean([all_tl[s][1]['theta_eff'] for s in range(len(SEEDS))])
    late_theta = np.mean([all_tl[s][-1]['theta_eff'] for s in range(len(SEEDS))])
    print(f"Q1: theta_eff monotonic? early={early_theta:.4f} late={late_theta:.4f} "
          f"{'YES' if late_theta > early_theta else 'NO'}")

    # Q2: eta_eff decreases monotonically?
    early_eta = np.mean([all_tl[s][1]['eta_eff'] for s in range(len(SEEDS))])
    late_eta = np.mean([all_tl[s][-1]['eta_eff'] for s in range(len(SEEDS))])
    print(f"Q2: eta_eff decreases? early={early_eta:.8f} late={late_eta:.8f} "
          f"{'YES' if late_eta < early_eta else 'NO'}")

    # Q5: Does eta_eff/eta_nominal converge?
    # eta_nominal for dominant category at N=4000: eta * K/(N+K) * sqrt(V_mean/V_cat)
    N_dom = 4000 * 0.65  # approximate decisions for dominant category
    eta_nominal = 0.05 * K_BATCH / (N_dom + K_BATCH) * np.sqrt((1/C) / 0.65)
    ratio = late_eta / eta_nominal if eta_nominal > 0 else 0
    print(f"Q5: eta_eff/eta_nominal converges? eta_eff={late_eta:.8f} "
          f"eta_nominal={eta_nominal:.8f} ratio={ratio:.2f}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
