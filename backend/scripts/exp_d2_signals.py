"""
EXP-D2: FEEDBACK SIGNAL COMPARISON
=====================================
Fix architecture (gated + velocity gain), vary feedback signal.

Run: cd backend && python scripts/exp_d2_signals.py
Time: ~20 min
"""

import numpy as np
from collections import deque
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N = 2000
CHECKPOINTS = [200, 500, 1000, 2000]
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


def run_signal_test(seed, signal_name, gt, start_mu, coupled=True):
    rng = np.random.default_rng(seed)
    scorer = make_scorer(start_mu.copy())
    initial_scorer = make_scorer(start_mu.copy())
    ca_counts = np.zeros((C, A))
    override_windows = {ci: deque(maxlen=50) for ci in range(C)}
    prev_mu = scorer.centroids.copy()
    velocity = 0.01

    lc = 0
    updates = 0
    all_confs, all_corrects = [], []
    cp = {}

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

        # Update velocity every 50
        if n % 50 == 0:
            velocity = np.linalg.norm(scorer.centroids - prev_mu) / 50
            prev_mu = scorer.centroids.copy()

        # Compute signal
        use_scorer = scorer if coupled else initial_scorer
        use_result = use_scorer.score(fv, ci) if not coupled else result

        should_update = False
        if signal_name == "confidence":
            should_update = use_result.confidence <= 0.60
        elif signal_name == "raw_distance":
            dists = [np.linalg.norm(fv - use_scorer.centroids[ci, ai]) for ai in range(A)]
            should_update = min(dists) > 0.15
        elif signal_name == "entropy":
            probs = np.clip(np.array(use_result.probabilities), 1e-10, 1.0)
            H = -np.sum(probs * np.log(probs))
            should_update = H > 0.5 * np.log(A)
        elif signal_name == "conf_gap":
            probs = np.array(use_result.probabilities)
            sp = np.sort(probs)[::-1]
            gap = sp[0] - sp[1] if len(sp) > 1 else sp[0]
            should_update = gap < 0.30
        elif signal_name == "override_rate":
            or_val = np.mean(override_windows[ci]) if len(override_windows[ci]) > 5 else 0.5
            should_update = or_val > 0.20
        elif signal_name == "velocity":
            should_update = velocity > 0.001
        elif signal_name == "none":
            should_update = True  # always update (raw SGD)

        if should_update:
            # Velocity-based gain
            eta_min, eta_max = 0.005, 0.10
            sigmoid_val = 1.0 / (1.0 + np.exp(-500 * (velocity - 0.001)))
            eta = eta_min + (eta_max - eta_min) * sigmoid_val
            n_ca = ca_counts[ci, oa]
            decay = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
            scale = (eta / 0.05) * decay

            mu_ca = scorer.centroids[ci, oa]
            eff_fv = mu_ca + max(scale, 0.005) * (fv - mu_ca)
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
            ca_counts[ci, oa] += 1
            updates += 1

        if n in CHECKPOINTS:
            confs = np.array(all_confs)
            corrs = np.array(all_corrects)
            cp[n] = {
                'acc': lc / n * 100,
                'ece': compute_ece(confs, corrs),
                'rate': updates / n * 100,
            }

    return cp


def main():
    print("=" * 80)
    print("EXP-D2: FEEDBACK SIGNAL COMPARISON")
    print("=" * 80)

    base_mu = get_base_centroids()
    signals = ["confidence", "raw_distance", "entropy", "conf_gap",
               "override_rate", "velocity", "none"]

    # Calibrated prior
    print(f"\n  CALIBRATED PRIOR:")
    print(f"  {'Signal':>15s}  {'Acc@2000':>8s}  {'ECE@2000':>8s}  {'Rate%':>6s}")
    print(f"  {'-' * 42}")

    cal_results = {}
    for sig in signals:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_signal_test(seed, sig, gt, base_mu)
            runs.append(r)
        acc = np.mean([r[N]['acc'] for r in runs])
        ece = np.mean([r[N]['ece'] for r in runs])
        rate = np.mean([r[N]['rate'] for r in runs])
        cal_results[sig] = {'acc': acc, 'ece': ece, 'rate': rate}
        print(f"  {sig:>15s}  {acc:>6.1f}%  {ece:>8.4f}  {rate:>5.1f}%")

    # Generic prior
    print(f"\n  GENERIC PRIOR:")
    print(f"  {'Signal':>15s}  {'Acc@2000':>8s}  {'ECE@2000':>8s}")
    print(f"  {'-' * 35}")

    generic = np.full((C, A, D), 0.5)
    gen_results = {}
    for sig in signals:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_signal_test(seed, sig, gt, generic)
            runs.append(r)
        acc = np.mean([r[N]['acc'] for r in runs])
        ece = np.mean([r[N]['ece'] for r in runs])
        gen_results[sig] = {'acc': acc, 'ece': ece}
        print(f"  {sig:>15s}  {acc:>6.1f}%  {ece:>8.4f}")

    # Coupling test
    print(f"\n  COUPLING TEST (live vs frozen, calibrated):")
    print(f"  {'Signal':>15s}  {'Live':>6s}  {'Frozen':>6s}  {'Diff':>6s}  {'Coupled?':>8s}")
    print(f"  {'-' * 50}")

    for sig in signals:
        if sig == "none":
            continue
        live_runs = []
        frozen_runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r_live = run_signal_test(seed, sig, gt, base_mu, coupled=True)
            r_frozen = run_signal_test(seed, sig, gt, base_mu, coupled=False)
            live_runs.append(r_live)
            frozen_runs.append(r_frozen)

        live_acc = np.mean([r[N]['acc'] for r in live_runs])
        frozen_acc = np.mean([r[N]['acc'] for r in frozen_runs])
        diff = abs(live_acc - frozen_acc)
        print(f"  {sig:>15s}  {live_acc:5.1f}%  {frozen_acc:5.1f}%  {diff:4.1f}pp  "
              f"{'YES' if diff > 0.5 else 'NO'}")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    best_acc = max(signals, key=lambda s: cal_results[s]['acc'])
    best_ece = min(signals, key=lambda s: cal_results[s]['ece'])
    print(f"Q1: Best accuracy signal: {best_acc} ({cal_results[best_acc]['acc']:.1f}%)")
    print(f"Q2: Best ECE signal: {best_ece} ({cal_results[best_ece]['ece']:.4f})")
    best_gen = max(signals, key=lambda s: gen_results[s]['acc'])
    print(f"Q3: Best from generic: {best_gen} ({gen_results[best_gen]['acc']:.1f}%)")

    print("\nDONE.")


if __name__ == "__main__":
    main()
