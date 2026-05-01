"""
EXP-11: V-WEIGHT-DIFFERENT-N
==============================
What is w_pipeline(N_final)? Fit functional form.

Run: cd backend && python scripts/exp11_different_n.py
Time: ~20 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF
)

N_VALUES = [500, 1000, 2000, 4000, 8000]
SEEDS_SHORT = [42, 123, 777]


def run_to_n(seed, N_max):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)

    s_pipe = make_scorer()
    s_raw = make_scorer()
    s_static = make_scorer()
    pipeline = ThreeStagePipeline(s_pipe, K=K_BATCH, theta_conf=THETA_CONF,
                                   category_weights=CATEGORY_WEIGHTS)
    lc_p, lc_r, lc_s = 0, 0, 0

    for n in range(1, N_max + 1):
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

    return {
        'w_pipeline': lc_p/N_max*100 - lc_r/N_max*100,
        'w_centroid': lc_p/N_max*100 - lc_s/N_max*100,
        'acc_pipe': lc_p/N_max*100,
        'acc_raw': lc_r/N_max*100,
        'acc_static': lc_s/N_max*100,
    }


def main():
    print("=" * 80)
    print("EXP-11: V-WEIGHT-DIFFERENT-N")
    print("=" * 80)

    results = {}
    for N in N_VALUES:
        runs = [run_to_n(s, N) for s in SEEDS_SHORT]
        results[N] = {k: np.mean([r[k] for r in runs]) for k in runs[0]}
        print(f"  N={N} done")

    print(f"\n{'=' * 60}")
    print(f"  {'N':>6s}  {'w_pipeline':>10s}  {'w_centroid':>10s}  {'pipe':>6s}  {'raw':>6s}  {'static':>6s}")
    print(f"  {'-' * 55}")
    for N in N_VALUES:
        r = results[N]
        print(f"  {N:>6d}  {r['w_pipeline']:>+8.1f}pp  {r['w_centroid']:>+8.1f}pp  "
              f"{r['acc_pipe']:>5.1f}%  {r['acc_raw']:>5.1f}%  {r['acc_static']:>5.1f}%")

    # Fit models
    Ns = np.array(N_VALUES, dtype=float)
    ws = np.array([results[N]['w_pipeline'] for N in N_VALUES])

    # Linear: w = a + b*N
    if len(Ns) > 1:
        b_lin = np.polyfit(Ns, ws, 1)
        pred_lin = np.polyval(b_lin, Ns)
        rmse_lin = np.sqrt(np.mean((ws - pred_lin)**2))

        # Log: w = a + b*ln(N)
        b_log = np.polyfit(np.log(Ns), ws, 1)
        pred_log = np.polyval(b_log, np.log(Ns))
        rmse_log = np.sqrt(np.mean((ws - pred_log)**2))

        # Sqrt: w = a + b*sqrt(N)
        b_sqrt = np.polyfit(np.sqrt(Ns), ws, 1)
        pred_sqrt = np.polyval(b_sqrt, np.sqrt(Ns))
        rmse_sqrt = np.sqrt(np.mean((ws - pred_sqrt)**2))

        print(f"\n  Model fits:")
        print(f"    Linear w = {b_lin[1]:+.2f} + {b_lin[0]:+.6f}*N  RMSE={rmse_lin:.3f}")
        print(f"    Log    w = {b_log[1]:+.2f} + {b_log[0]:+.2f}*ln(N)  RMSE={rmse_log:.3f}")
        print(f"    Sqrt   w = {b_sqrt[1]:+.2f} + {b_sqrt[0]:+.4f}*sqrt(N)  RMSE={rmse_sqrt:.3f}")
        print(f"    Best: {'LINEAR' if rmse_lin <= rmse_log and rmse_lin <= rmse_sqrt else 'LOG' if rmse_log <= rmse_sqrt else 'SQRT'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
