"""
EXP-12: V-WEIGHT-DIFFERENT-PRIOR
==================================
Does the weight trajectory depend on initial state?

Run: cd backend && python scripts/exp12_different_prior.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF
)

N = 4000
WINDOW = 100


def run_prior_test(seed, prior, gt):
    rng = np.random.default_rng(seed)
    s_pipe = make_scorer(prior)
    s_raw = make_scorer(prior)
    s_static = make_scorer(prior)
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
            timeline.append({'n': n, 'w_pipe': lc_p/n*100 - lc_r/n*100,
                             'w_cent': lc_p/n*100 - lc_s/n*100})

    return timeline


def main():
    print("=" * 80)
    print("EXP-12: V-WEIGHT-DIFFERENT-PRIOR")
    print("=" * 80)

    base_mu = get_base_centroids()
    rng_shift = np.random.default_rng(77777)

    priors = {
        "calibrated": base_mu.copy(),
        "shifted_0.10": np.clip(base_mu + rng_shift.normal(0, 1, base_mu.shape) /
                                np.linalg.norm(rng_shift.normal(0, 1, base_mu.shape)) * 0.10, 0, 1),
        "shifted_0.30": np.clip(base_mu + rng_shift.normal(0, 1, base_mu.shape) /
                                np.linalg.norm(rng_shift.normal(0, 1, base_mu.shape)) * 0.30, 0, 1),
    }

    for seed in SEEDS[:3]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        print(f"\n  Seed {seed}:")
        print(f"  {'N':>6s}", end="")
        for p in priors:
            print(f"  {p[:12]+'_wp':>14s}", end="")
        print()
        print(f"  {'-' * 50}")

        results = {p: run_prior_test(seed, prior, gt) for p, prior in priors.items()}
        n_pts = len(list(results.values())[0])

        for i in range(n_pts):
            n = list(results.values())[0][i]['n']
            print(f"  {n:>6d}", end="")
            for p in priors:
                print(f"  {results[p][i]['w_pipe']:>+12.1f}pp", end="")
            print()

    # Convergence check
    print(f"\n{'=' * 80}")
    print("Do trajectories converge regardless of prior?")
    print("=" * 80)

    gt = build_gt(np.random.default_rng(42), base_mu)
    results = {p: run_prior_test(42, prior, gt) for p, prior in priors.items()}
    n_pts = len(list(results.values())[0])

    for i in range(n_pts):
        n = list(results.values())[0][i]['n']
        vals = [results[p][i]['w_pipe'] for p in priors]
        spread = max(vals) - min(vals)
        print(f"  N={n:>5d}: spread={spread:.1f}pp "
              f"{'CONVERGED' if spread < 1.0 else 'DIVERGENT'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
