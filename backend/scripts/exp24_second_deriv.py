"""
EXP-24: V-SECOND-DERIVATIVE
==============================
Measure dw/dt and d2w/dt2. Are dynamics deterministic?

Run: cd backend && python scripts/exp24_second_deriv.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF, FREQ_NOISE, ADJACENT
)

N = 4000
WINDOW = 10  # fine-grained


def noise_with_quality(gt_a, ci, rng, noise_rate):
    if rng.random() < noise_rate:
        nbrs = ADJACENT.get(gt_a, [])
        if nbrs: return int(rng.choice(nbrs))
        wrong = [a for a in range(A) if a != gt_a]
        return int(rng.choice(wrong))
    return gt_a


def run_lifecycle_fine(seed):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)

    s_pipe = make_scorer()
    s_raw = make_scorer()
    s_static = make_scorer()
    pipeline = ThreeStagePipeline(s_pipe, K=K_BATCH, theta_conf=THETA_CONF,
                                   category_weights=CATEGORY_WEIGHTS)

    lc_p, lc_r, lc_s = 0, 0, 0
    noise_rate = 0.15
    timeline = []

    for n in range(1, N + 1):
        if n == 1001:
            direction = rng.normal(0, 1, gt.shape)
            direction = direction / np.linalg.norm(direction) * 0.15
            gt = gt + direction
        if n == 2001:
            noise_rate = 0.30
        if n == 3001:
            noise_rate = 0.15

        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_with_quality(ta, ci, rng, FREQ_NOISE.get(ci, noise_rate))

        rp = s_pipe.score(fv, ci)
        if rp.action_index == oa: lc_p += 1
        pipeline.process(fv, ci, rp.action_index, rp.action_index == oa, oa, rp.confidence)

        rr = s_raw.score(fv, ci)
        if rr.action_index == oa: lc_r += 1
        s_raw.update(fv, ci, rr.action_index, rr.action_index == oa, oa)

        rs = s_static.score(fv, ci)
        if rs.action_index == oa: lc_s += 1

        if n % WINDOW == 0:
            w_pipe = lc_p/n*100 - lc_r/n*100
            timeline.append({'n': n, 'w': w_pipe})

    return timeline


def main():
    print("=" * 80)
    print("EXP-24: V-SECOND-DERIVATIVE (fine-grained, window=10)")
    print("Events: shift@1000, noise_up@2000, restore@3000")
    print("=" * 80)

    all_tl = [run_lifecycle_fine(s) for s in SEEDS]
    n_pts = len(all_tl[0])

    # Compute derivatives
    # w(t), dw/dt, d2w/dt2 — per seed then average
    print(f"\n  Derivatives at event boundaries (+/- 50 decisions):")
    events = [("SHIFT", 1000), ("NOISE_UP", 2000), ("RESTORE", 3000)]

    for event_name, event_n in events:
        print(f"\n  === {event_name} at N={event_n} ===")
        print(f"  {'N':>5s}  {'w':>7s}  {'dw/dN':>10s}  {'d2w/dN2':>12s}  {'Var(dw)':>10s}")
        print(f"  {'-' * 50}")

        for target_n in range(event_n - 50, event_n + 60, WINDOW):
            idx = target_n // WINDOW - 1
            if idx < 1 or idx >= n_pts - 1:
                continue

            ws = [t[idx]['w'] for t in all_tl]
            dws = [(t[idx]['w'] - t[idx-1]['w']) / WINDOW for t in all_tl]

            d2ws = []
            if idx >= 2:
                for t in all_tl:
                    dw_now = (t[idx]['w'] - t[idx-1]['w']) / WINDOW
                    dw_prev = (t[idx-1]['w'] - t[idx-2]['w']) / WINDOW
                    d2ws.append((dw_now - dw_prev) / WINDOW)

            n_val = all_tl[0][idx]['n']
            print(f"  {n_val:>5d}  {np.mean(ws):>+5.1f}pp  {np.mean(dws):>+10.6f}  "
                  f"{np.mean(d2ws):>+12.8f}  {np.var(dws):>10.6f}" if d2ws else
                  f"  {n_val:>5d}  {np.mean(ws):>+5.1f}pp  {np.mean(dws):>+10.6f}  {'N/A':>12s}  {np.var(dws):>10.6f}")

    # Overall dw/dN consistency
    print(f"\n{'=' * 80}")
    print("dw/dN VARIANCE ACROSS SEEDS (is it deterministic?)")
    print(f"{'=' * 80}")

    for idx in range(1, n_pts, 50):
        n = all_tl[0][idx]['n']
        dws = [(t[idx]['w'] - t[idx-1]['w']) / WINDOW for t in all_tl]
        print(f"  N={n:>5d}: dw/dN variance = {np.var(dws):.6f} "
              f"{'DETERMINISTIC' if np.var(dws) < 0.001 else 'STOCHASTIC'}")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    # Q1: dw/dt approximately constant in each regime?
    regimes = [(200, 900, "pre-shift"), (1100, 1900, "post-shift"),
               (2100, 2900, "high-noise"), (3100, 3900, "restored")]
    for label, start, end in regimes:
        dws = []
        for t in all_tl:
            for idx in range(start // WINDOW, end // WINDOW):
                if idx > 0 and idx < len(t):
                    dws.append((t[idx]['w'] - t[idx-1]['w']) / WINDOW)
        if dws:
            print(f"  {label}: mean_dw={np.mean(dws):+.6f} std={np.std(dws):.6f} "
                  f"CV={np.std(dws)/abs(np.mean(dws)) if np.mean(dws) != 0 else float('inf'):.1f}")

    # Q4: Is dw/dt variance < 0.001 across seeds?
    late_vars = []
    for idx in range(n_pts - 50, n_pts):
        if idx > 0:
            dws = [(t[idx]['w'] - t[idx-1]['w']) / WINDOW for t in all_tl]
            late_vars.append(np.var(dws))
    mean_var = np.mean(late_vars) if late_vars else 0
    print(f"\nQ4: Late-stage dw/dN variance = {mean_var:.6f} "
          f"{'DETERMINISTIC' if mean_var < 0.001 else 'STOCHASTIC'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
