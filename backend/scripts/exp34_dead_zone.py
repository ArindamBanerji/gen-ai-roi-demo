"""
EXP-34: V-DEAD-ZONE-CHARACTERIZATION
======================================
Is the accuracy ceiling explained by the dead zone width tau = sigma/sqrt(K)?

Run: cd backend && python scripts/exp34_dead_zone.py
Time: ~10 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, THETA_CONF, SIGMA_BAR
)

N = 5000
WINDOW = 10
K_VALUES = [5, 10, 20, 50]


def run_dead_zone(seed, K):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)

    scorer = make_scorer()
    pipeline = ThreeStagePipeline(scorer, K=K, theta_conf=THETA_CONF,
                                   category_weights=CATEGORY_WEIGHTS)

    tau = SIGMA_BAR / np.sqrt(K)
    lc = 0
    trajectory = []

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc += 1

        pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)

        if n % WINDOW == 0:
            e = np.linalg.norm(scorer.centroids - gt)  # Frobenius distance
            trajectory.append({'n': n, 'error': e, 'acc': lc / n * 100})

    return {'trajectory': trajectory, 'tau': tau,
            'sig_rate': pipeline.stats['batch_sig'] / max(pipeline.stats['batch_total'], 1)}


def main():
    print("=" * 80)
    print("EXP-34: V-DEAD-ZONE-CHARACTERIZATION")
    print(f"sigma_bar = {SIGMA_BAR:.4f}")
    print("=" * 80)

    for K in K_VALUES:
        tau = SIGMA_BAR / np.sqrt(K)
        print(f"\n  K={K}, tau = {SIGMA_BAR:.4f}/sqrt({K}) = {tau:.4f}")
        print(f"  {'N':>6s}  {'error':>8s}  {'acc':>6s}  {'e/tau':>6s}")
        print(f"  {'-' * 35}")

        all_r = [run_dead_zone(s, K) for s in SEEDS]

        n_points = len(all_r[0]['trajectory'])
        for i in range(0, n_points, 50):  # every 500 decisions
            n = all_r[0]['trajectory'][i]['n']
            errors = [r['trajectory'][i]['error'] for r in all_r]
            accs = [r['trajectory'][i]['acc'] for r in all_r]
            mean_e = np.mean(errors)
            print(f"  {n:>6d}  {mean_e:>8.4f}  {np.mean(accs):5.1f}%  {mean_e/tau:>5.2f}")

        # Steady-state error
        steady_errors = []
        for r in all_r:
            for pt in r['trajectory']:
                if pt['n'] > 2000:
                    steady_errors.append(pt['error'])

        mean_steady = np.mean(steady_errors)
        std_steady = np.std(steady_errors)
        sig_rate = np.mean([r['sig_rate'] for r in all_r])

        print(f"\n  Steady-state (N>2000): error={mean_steady:.4f} +/- {std_steady:.4f}")
        print(f"  tau={tau:.4f}, error/tau={mean_steady/tau:.2f}")
        print(f"  Significance rate: {sig_rate*100:.0f}%")

    # Cross-K comparison
    print(f"\n{'=' * 80}")
    print("CROSS-K COMPARISON AT N=5000")
    print(f"{'=' * 80}")
    print(f"  {'K':>4s}  {'tau':>8s}  {'error':>8s}  {'e/tau':>6s}  {'acc':>6s}  {'sig_rate':>9s}")
    print(f"  {'-' * 50}")

    k_results = {}
    for K in K_VALUES:
        tau = SIGMA_BAR / np.sqrt(K)
        all_r = [run_dead_zone(s, K) for s in SEEDS]
        errors = [r['trajectory'][-1]['error'] for r in all_r]
        accs = [r['trajectory'][-1]['acc'] for r in all_r]
        sig_rate = np.mean([r['sig_rate'] for r in all_r])
        mean_e = np.mean(errors)
        k_results[K] = {'tau': tau, 'error': mean_e, 'acc': np.mean(accs)}
        print(f"  {K:>4d}  {tau:>8.4f}  {mean_e:>8.4f}  {mean_e/tau:>5.2f}  "
              f"{np.mean(accs):5.1f}%  {sig_rate*100:>7.0f}%")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    # Q1: Periodic oscillation?
    r_k10 = [run_dead_zone(s, 10) for s in SEEDS]
    errors = []
    for r in r_k10:
        errors.extend([pt['error'] for pt in r['trajectory'] if pt['n'] > 2000])
    if len(errors) > 10:
        # Check autocorrelation at lag 1
        e = np.array(errors)
        e_centered = e - np.mean(e)
        if len(e_centered) > 1:
            autocorr = np.correlate(e_centered, e_centered, 'full')
            autocorr = autocorr[len(autocorr)//2:]
            autocorr = autocorr / autocorr[0] if autocorr[0] > 0 else autocorr
            lag1 = autocorr[1] if len(autocorr) > 1 else 0
            print(f"Q1: Periodic oscillation? autocorr_lag1={lag1:.3f} "
                  f"{'YES' if lag1 > 0.3 else 'NO'}")

    # Q2: Steady-state error ≈ tau?
    e_10 = k_results[10]['error']
    tau_10 = k_results[10]['tau']
    ratio = e_10 / tau_10
    print(f"Q2: error ~= tau? error={e_10:.4f} tau={tau_10:.4f} "
          f"ratio={ratio:.2f} {'YES' if 0.5 < ratio < 2.0 else 'NO'}")

    # Q3: Dead zone ratio
    # What fraction of batch signals are near the threshold?
    print(f"Q3: (Dead zone ratio measured via significance rate above)")

    # Key finding: does increasing K reduce error?
    e_5 = k_results[5]['error']
    e_50 = k_results[50]['error']
    ratio_improvement = e_5 / e_50 if e_50 > 0 else 0
    tau_ratio = k_results[5]['tau'] / k_results[50]['tau']
    print(f"\n  KEY: Does increasing K reduce error?")
    print(f"  K=5 error={e_5:.4f}, K=50 error={e_50:.4f}, improvement={ratio_improvement:.2f}x")
    print(f"  tau ratio (K=5/K=50) = {tau_ratio:.2f}x")
    print(f"  If error tracks tau: improvement should be ~{tau_ratio:.1f}x, "
          f"got {ratio_improvement:.1f}x")

    print("\nDONE.")


if __name__ == "__main__":
    main()
