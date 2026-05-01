"""
EXP-H5: COMBINED IMPROVEMENTS
=================================
HE10: Does momentum + subspace projection solve cold start?
HE5: What is the stability-accuracy frontier for combined controllers?

Combines the best findings from all dimensions:
- Momentum update rule (D9: 62.6% from generic)
- Subspace projection (E2: 60% wasted energy)
- Boundary targeting (P6: 89% of errors near boundary)
- conf_gap gating (D2: 83.5%)
- Hysteresis switching (D4: best lifecycle)

Tests all combinations from calibrated AND generic prior.
Also measures Lyapunov stability to map the stability-accuracy frontier.

Run: cd backend && python scripts/exp_h5_combined.py
Time: ~25 min
"""

import numpy as np
from collections import deque
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_CAL = 2000
N_COLD = 2000
SEEDS_SHORT = [42, 123, 777]


def compute_ece(confs, corrects, n_bins=10):
    bounds = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    total = len(confs)
    if total == 0:
        return 0.0
    for i in range(n_bins):
        lo, hi = bounds[i], bounds[i + 1]
        mask = (confs >= lo) & (confs < hi) if i < n_bins - 1 else (confs >= lo) & (confs <= hi)
        count = mask.sum()
        if count == 0:
            continue
        ece += (count / total) * abs(corrects[mask].mean() - confs[mask].mean())
    return ece


def compute_subspace_bases(centroids):
    bases = {}
    for ci in range(C):
        centered = centroids[ci] - centroids[ci].mean(axis=0)
        U, S, Vh = np.linalg.svd(centered, full_matrices=False)
        bases[ci] = Vh[:min(2, len(S))]
    return bases


def project_update(update, bases, ci):
    B = bases[ci]
    coeffs = B @ update
    return B.T @ coeffs


def run_combined(seed, config, gt, start_mu, N):
    """
    config dict with keys:
      momentum: bool
      project: bool
      boundary_gate: bool
      conf_gate: bool
      hysteresis: bool
    """
    rng = np.random.default_rng(seed)
    scorer = make_scorer(start_mu.copy())
    bases = compute_subspace_bases(start_mu)
    ca_counts = np.zeros((C, A))
    momentum_buf = np.zeros_like(scorer.centroids)
    beta = 0.7
    override_windows = {ci: deque(maxlen=50) for ci in range(C)}
    mode = {ci: "LEARN" for ci in range(C)}

    lc = 0
    all_confs, all_corrects = [], []
    V_vals = []

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc += 1
        all_confs.append(result.confidence)
        all_corrects.append(1.0 if correct else 0.0)
        override_windows[ci].append(0 if correct else 1)

        # Gating
        should_update = True

        if config.get('conf_gate'):
            if result.confidence > 0.60:
                should_update = False

        if config.get('boundary_gate') and should_update:
            dists = [np.linalg.norm(fv - scorer.centroids[ci, a]) for a in range(A)]
            sd = np.sort(dists)
            margin = (sd[1] - sd[0]) / 2
            if margin > 0.05:
                should_update = False

        # Hysteresis mode switching
        if config.get('hysteresis'):
            or_val = np.mean(override_windows[ci]) if len(override_windows[ci]) > 5 else 0.5
            if mode[ci] == "PRESERVE" and or_val > 0.25:
                mode[ci] = "LEARN"
            elif mode[ci] == "LEARN" and or_val < 0.10:
                mode[ci] = "PRESERVE"

        if should_update:
            ai = oa
            n_ca = ca_counts[ci, ai]
            mu_ca = scorer.centroids[ci, ai]
            raw_update = fv - mu_ca

            # Projection
            if config.get('project'):
                update = project_update(raw_update, bases, ci)
            else:
                update = raw_update

            # Momentum
            if config.get('momentum'):
                momentum_buf[ci, ai] = beta * momentum_buf[ci, ai] + (1 - beta) * update
                update = momentum_buf[ci, ai]

            # Gain
            if config.get('hysteresis'):
                base_rate = 1.6 if mode[ci] == "LEARN" else 0.1
            else:
                base_rate = 1.0
            decay = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
            scale = base_rate * decay

            eff_fv = mu_ca + max(scale, 0.005) * update
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
            ca_counts[ci, ai] += 1

        # Lyapunov
        if n % 50 == 0:
            V = float(np.sum((scorer.centroids - gt) ** 2))
            V_vals.append(V)

    confs = np.array(all_confs)
    corrs = np.array(all_corrects)

    v_neg = sum(1 for i in range(1, len(V_vals)) if V_vals[i] <= V_vals[i-1])
    v_pct = v_neg / max(len(V_vals) - 1, 1) * 100

    return {
        'acc': lc / N * 100,
        'ece': compute_ece(confs, corrs),
        'lyap_pct': v_pct,
    }


def main():
    print("=" * 90)
    print("EXP-H5: COMBINED IMPROVEMENTS")
    print("=" * 90)

    base_mu = get_base_centroids()

    configs = [
        ("STATIC", {}),
        ("STANDARD", {}),  # plain sqrt decay
        ("MOMENTUM", {'momentum': True}),
        ("PROJECTED", {'project': True}),
        ("MOM+PROJ", {'momentum': True, 'project': True}),
        ("CONF_GATE", {'conf_gate': True}),
        ("BDRY_GATE", {'boundary_gate': True}),
        ("GATE+PROJ", {'conf_gate': True, 'project': True}),
        ("GATE+MOM", {'conf_gate': True, 'momentum': True}),
        ("GATE+MOM+PROJ", {'conf_gate': True, 'momentum': True, 'project': True}),
        ("FULL_COMBINED", {'conf_gate': True, 'momentum': True, 'project': True, 'hysteresis': True}),
        ("BDRY+MOM+PROJ", {'boundary_gate': True, 'momentum': True, 'project': True}),
    ]

    # CALIBRATED PRIOR
    print(f"\n{'=' * 90}")
    print("CALIBRATED PRIOR (N=2000)")
    print(f"{'=' * 90}")
    print(f"  {'Config':>18s}  {'Acc':>6s}  {'ECE':>8s}  {'Lyap%':>6s}  {'Acc-Static':>10s}")
    print(f"  {'-' * 55}")

    static_acc = 0
    for name, cfg in configs:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            if name == "STATIC":
                r = run_combined(seed, {}, gt, base_mu, N_CAL)
                r['acc'] = r['acc']  # static doesn't update
            elif name == "STANDARD":
                r = run_combined(seed, cfg, gt, base_mu, N_CAL)
            else:
                r = run_combined(seed, cfg, gt, base_mu, N_CAL)
            runs.append(r)

        acc = np.mean([r['acc'] for r in runs])
        ece = np.mean([r['ece'] for r in runs])
        lyap = np.mean([r['lyap_pct'] for r in runs])
        if name == "STATIC":
            static_acc = acc
        print(f"  {name:>18s}  {acc:5.1f}%  {ece:8.4f}  {lyap:4.0f}%  {acc-static_acc:>+8.1f}pp")

    # GENERIC PRIOR (cold start)
    print(f"\n{'=' * 90}")
    print("GENERIC PRIOR (cold start, N=2000)")
    print(f"{'=' * 90}")
    print(f"  {'Config':>18s}  {'Acc':>6s}")
    print(f"  {'-' * 28}")

    for name, cfg in configs:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            generic = np.full_like(base_mu, 0.5)
            r = run_combined(seed, cfg, gt, generic, N_COLD)
            runs.append(r)
        acc = np.mean([r['acc'] for r in runs])
        print(f"  {name:>18s}  {acc:5.1f}%")

    # STABILITY-ACCURACY FRONTIER (HE5)
    print(f"\n{'=' * 90}")
    print("STABILITY-ACCURACY FRONTIER (calibrated)")
    print(f"{'=' * 90}")
    print(f"  {'Config':>18s}  {'Accuracy':>8s}  {'Lyap%':>6s}  {'Stable?':>7s}")
    print(f"  {'-' * 45}")

    frontier = []
    for name, cfg in configs:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_combined(seed, cfg, gt, base_mu, N_CAL)
            runs.append(r)
        acc = np.mean([r['acc'] for r in runs])
        lyap = np.mean([r['lyap_pct'] for r in runs])
        stable = lyap > 90
        frontier.append((name, acc, lyap, stable))
        print(f"  {name:>18s}  {acc:>6.1f}%  {lyap:>4.0f}%  {'YES' if stable else 'NO'}")

    # Best stable controller
    stable_configs = [(n, a, l) for n, a, l, s in frontier if s]
    if stable_configs:
        best_stable = max(stable_configs, key=lambda x: x[1])
        print(f"\n  Best STABLE controller: {best_stable[0]} ({best_stable[1]:.1f}%)")

    # Best overall
    best_overall = max(frontier, key=lambda x: x[1])
    print(f"  Best OVERALL controller: {best_overall[0]} ({best_overall[1]:.1f}%)")

    print("\nDONE.")


if __name__ == "__main__":
    main()
