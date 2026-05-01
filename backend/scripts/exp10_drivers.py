"""
EXP-10: V-WEIGHT-DRIVERS
==========================
Correlation between state variables and dw_pipeline/dN.

Run: cd backend && python scripts/exp10_drivers.py
Time: ~20 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF
)

N = 4000
WINDOW = 50


def run_drivers(seed):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)

    s_pipe = make_scorer()
    s_raw = make_scorer()
    s_static = make_scorer()
    pipeline = ThreeStagePipeline(s_pipe, K=K_BATCH, theta_conf=THETA_CONF,
                                   category_weights=CATEGORY_WEIGHTS)

    lc_p, lc_r, lc_s = 0, 0, 0
    prev_mu = s_pipe.centroids.copy()
    window_confs = []
    timeline = []

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        rp = s_pipe.score(fv, ci)
        if rp.action_index == oa: lc_p += 1
        pipeline.process(fv, ci, rp.action_index, rp.action_index == oa, oa, rp.confidence)
        window_confs.append(rp.confidence)

        rr = s_raw.score(fv, ci)
        if rr.action_index == oa: lc_r += 1
        s_raw.update(fv, ci, rr.action_index, rr.action_index == oa, oa)

        rs = s_static.score(fv, ci)
        if rs.action_index == oa: lc_s += 1

        if n % WINDOW == 0:
            w_pipe = lc_p/n*100 - lc_r/n*100
            vel = np.linalg.norm(s_pipe.centroids - prev_mu) / WINDOW
            confs = np.array(window_confs)
            raw_drift = float(np.linalg.norm(s_raw.centroids - base_mu))
            pipe_frob = float(np.linalg.norm(s_pipe.centroids - base_mu))

            timeline.append({
                'n': n, 'w_pipeline': w_pipe,
                'accuracy': lc_p/n*100, 'velocity': vel,
                'P_conf_above_60': np.mean(confs > 0.60)*100,
                'P_conf_above_80': np.mean(confs > 0.80)*100,
                'mean_conf': np.mean(confs),
                'raw_drift': raw_drift, 'pipe_frob': pipe_frob,
                'N': n,
            })
            prev_mu = s_pipe.centroids.copy()
            window_confs = []

    return timeline


def main():
    print("=" * 80)
    print("EXP-10: V-WEIGHT-DRIVERS")
    print("=" * 80)

    all_tl = [run_drivers(s) for s in SEEDS]
    print(f"  {len(SEEDS)} seeds done")

    # Flatten
    features = ['accuracy', 'velocity', 'P_conf_above_60', 'P_conf_above_80',
                'mean_conf', 'raw_drift', 'pipe_frob', 'N']
    target = 'w_pipeline'

    all_f = {f: [] for f in features}
    all_t = []
    all_dt = []  # dw/dN

    for tl in all_tl:
        for i, pt in enumerate(tl):
            for f in features:
                all_f[f].append(pt[f])
            all_t.append(pt[target])
            if i > 0:
                dw = (pt[target] - tl[i-1][target]) / WINDOW
                all_dt.append(dw)

    # Correlations with w_pipeline (level)
    print(f"\n{'=' * 80}")
    print(f"CORRELATION with w_pipeline (level)")
    print(f"{'=' * 80}")
    for f in features:
        arr = np.array(all_f[f])
        tar = np.array(all_t)
        if np.std(arr) > 0:
            r = np.corrcoef(arr, tar)[0, 1]
            print(f"  corr({f:>20s}, w_pipeline) = {r:+.4f}")

    # Correlations with dw/dN (rate of change)
    print(f"\n{'=' * 80}")
    print(f"CORRELATION with dw/dN (rate of change)")
    print(f"{'=' * 80}")
    dt_features = {f: [] for f in features}
    for tl in all_tl:
        for i in range(1, len(tl)):
            for f in features:
                dt_features[f].append(tl[i][f])

    dt_arr = np.array(all_dt)
    for f in features:
        arr = np.array(dt_features[f])
        if len(arr) == len(dt_arr) and np.std(arr) > 0 and np.std(dt_arr) > 0:
            r = np.corrcoef(arr, dt_arr)[0, 1]
            print(f"  corr({f:>20s}, dw/dN) = {r:+.4f}")

    # Best predictor
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    best_r = 0
    best_f = ""
    for f in features:
        arr = np.array(all_f[f])
        tar = np.array(all_t)
        if np.std(arr) > 0:
            r = abs(np.corrcoef(arr, tar)[0, 1])
            if r > best_r:
                best_r = r
                best_f = f
    print(f"Q1: Best predictor of w_pipeline: {best_f} (|r|={best_r:.4f})")
    print(f"Q2: Any |r| > 0.5? {'YES' if best_r > 0.5 else 'NO'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
