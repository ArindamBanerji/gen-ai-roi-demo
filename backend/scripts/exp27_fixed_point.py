"""
EXP-27: V-FIXED-POINT-ANALYSIS
=================================
Does the feedback loop converge to a unique fixed point?

Run: cd backend && python scripts/exp27_fixed_point.py
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


def run_fixed_point(seed, prior, gt):
    rng = np.random.default_rng(seed)

    scorer = make_scorer(prior)
    pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                   category_weights=CATEGORY_WEIGHTS)

    lc = 0
    prev_mu = scorer.centroids.copy()
    window_confs = []
    window_gated = 0
    window_total = 0
    timeline = []
    prev_updates = 0

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc += 1

        window_confs.append(result.confidence)
        window_total += 1
        if result.confidence > THETA_CONF:
            window_gated += 1

        pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)

        if n % WINDOW == 0:
            confs = np.array(window_confs)
            gate_rej = window_gated / window_total if window_total > 0 else 0
            eta_eff = np.linalg.norm(scorer.centroids - prev_mu) / WINDOW
            new_updates = pipeline.stats['updates'] - prev_updates
            sig_rate = pipeline.stats['batch_sig'] / max(pipeline.stats['batch_total'], 1)

            timeline.append({
                'n': n,
                'acc': lc / n * 100,
                'gate_rej': gate_rej,
                'eta_eff': eta_eff,
                'mean_conf': np.mean(confs),
                'sig_rate': sig_rate,
                'updates': new_updates,
            })

            prev_mu = scorer.centroids.copy()
            prev_updates = pipeline.stats['updates']
            window_confs = []
            window_gated = 0
            window_total = 0

    return timeline


def main():
    print("=" * 80)
    print("EXP-27: V-FIXED-POINT-ANALYSIS")
    print("=" * 80)

    base_mu = get_base_centroids()

    # Three similar initial conditions
    priors = {}
    priors["calibrated"] = base_mu.copy()

    # Transfer from Firm A (slightly different)
    rng_t = np.random.default_rng(99999)
    shift = rng_t.normal(0, 1, base_mu.shape)
    shift = shift / np.linalg.norm(shift) * 0.05
    priors["shifted_0.05"] = np.clip(base_mu + shift, 0, 1)

    # Another shift
    shift2 = rng_t.normal(0, 1, base_mu.shape)
    shift2 = shift2 / np.linalg.norm(shift2) * 0.10
    priors["shifted_0.10"] = np.clip(base_mu + shift2, 0, 1)

    # Run each prior with 3 different GTs
    gt_seeds = [42, 123, 777]

    print(f"\n  Testing convergence across 3 priors x 3 GTs = 9 trajectories")

    for gt_seed in gt_seeds:
        gt = build_gt(np.random.default_rng(gt_seed), base_mu)
        print(f"\n  GT seed {gt_seed}:")

        results = {}
        for prior_name, prior in priors.items():
            tl = run_fixed_point(gt_seed, prior, gt)
            results[prior_name] = tl

        # Compare effective parameters at N=4000
        print(f"    {'Prior':>15s}  {'acc':>5s}  {'gate_rej':>8s}  {'eta_eff':>10s}  {'mean_conf':>9s}  {'sig_rate':>8s}")
        print(f"    {'-' * 60}")

        for prior_name, tl in results.items():
            pt = tl[-1]  # last checkpoint
            print(f"    {prior_name:>15s}  {pt['acc']:4.1f}%  {pt['gate_rej']*100:6.1f}%  "
                  f"{pt['eta_eff']:.8f}  {pt['mean_conf']:.4f}  {pt['sig_rate']*100:6.1f}%")

    # Convergence analysis: do all 3 priors reach the same effective params?
    print(f"\n{'=' * 80}")
    print("CONVERGENCE ANALYSIS")
    print(f"{'=' * 80}")

    # For each GT, compare the spread across priors at each checkpoint
    gt = build_gt(np.random.default_rng(42), base_mu)
    all_tl = {p: run_fixed_point(42, prior, gt) for p, prior in priors.items()}

    n_points = min(len(tl) for tl in all_tl.values())
    print(f"  {'N':>5s}  {'acc_spread':>10s}  {'conf_spread':>11s}  {'eta_spread':>10s}  {'Merged?':>8s}")
    print(f"  {'-' * 50}")

    for i in range(0, n_points, 10):  # every 500 decisions
        n = all_tl["calibrated"][i]['n']
        accs = [all_tl[p][i]['acc'] for p in priors]
        confs = [all_tl[p][i]['mean_conf'] for p in priors]
        etas = [all_tl[p][i]['eta_eff'] for p in priors]

        acc_spread = max(accs) - min(accs)
        conf_spread = max(confs) - min(confs)
        eta_spread = max(etas) - min(etas)
        merged = acc_spread < 1.0 and conf_spread < 0.05

        print(f"  {n:>5d}  {acc_spread:>8.1f}pp  {conf_spread:>9.4f}  "
              f"{eta_spread:>10.8f}  {'YES' if merged else 'NO'}")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    # Q1: Do all priors converge to same effective params by N=4000?
    final_accs = [all_tl[p][-1]['acc'] for p in priors]
    final_confs = [all_tl[p][-1]['mean_conf'] for p in priors]
    acc_spread = max(final_accs) - min(final_accs)
    conf_spread = max(final_confs) - min(final_confs)
    converge = acc_spread < 1.0 and conf_spread < 0.05
    print(f"Q1: Unique fixed point? acc_spread={acc_spread:.1f}pp "
          f"conf_spread={conf_spread:.4f} {'YES' if converge else 'NO'}")

    # Q2: At what N do trajectories merge?
    merge_n = "never"
    for i in range(n_points):
        accs = [all_tl[p][i]['acc'] for p in priors]
        if max(accs) - min(accs) < 1.0:
            merge_n = str(all_tl["calibrated"][i]['n'])
            break
    print(f"Q2: Trajectories merge at N={merge_n}")

    # Q3: Monotonic or oscillatory convergence?
    cal_accs = [all_tl["calibrated"][i]['acc'] for i in range(n_points)]
    diffs = [abs(cal_accs[i+1] - cal_accs[i]) for i in range(len(cal_accs)-1)]
    # Count sign changes in accuracy differences
    signs = [1 if cal_accs[i+1] > cal_accs[i] else -1 for i in range(len(cal_accs)-1)]
    sign_changes = sum(1 for i in range(len(signs)-1) if signs[i] != signs[i+1])
    print(f"Q3: Convergence type: {sign_changes} sign changes "
          f"{'OSCILLATORY' if sign_changes > len(signs) * 0.3 else 'MONOTONIC'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
