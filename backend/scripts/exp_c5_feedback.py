"""
EXP-C5: V-FEEDBACK-COUPLING-SWEEP
====================================
Resolves CONFUSION 6: Is EVERY feedback signal blind, or just confidence?

Tests 5 feedback signals. For each: coupling test (live vs frozen)
and performance comparison.

Run: cd backend && python scripts/exp_c5_feedback.py
Time: ~15 min
"""

import numpy as np
from collections import deque
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, THETA_CONF
)

N = 2000
CHECKPOINTS = [200, 500, 1000, 2000]


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


def run_feedback_test(seed, signal_name, coupled, gt, base_mu):
    """
    signal_name: which signal gates updates
    coupled: True = live signal, False = frozen at N=0 distribution
    """
    rng = np.random.default_rng(seed)
    scorer = make_scorer(base_mu.copy())
    initial_scorer = make_scorer(base_mu.copy())  # frozen copy

    # Override tracking per category (rolling window of 50)
    override_windows = {ci: deque(maxlen=50) for ci in range(C)}

    lc = 0
    updates = 0
    all_confs, all_corrects = [], []
    cp = {}

    # Compute initial signal thresholds from first 200 decisions
    # (calibration phase — update everything, just record signals)
    calibration_signals = {signal_name: []}

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        # Score with current (live) scorer
        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc += 1

        all_confs.append(result.confidence)
        all_corrects.append(1.0 if correct else 0.0)

        # Track override rate
        override_windows[ci].append(0 if correct else 1)

        # Compute signal value
        if coupled:
            live_result = result
        else:
            live_result = initial_scorer.score(fv, ci)

        if signal_name == "confidence":
            signal_val = live_result.confidence
            should_update = signal_val <= THETA_CONF  # low confidence = update
        elif signal_name == "raw_distance":
            # Distance to closest centroid (lower = more certain = block)
            dists = [np.linalg.norm(fv - scorer.centroids[ci, ai])
                     for ai in range(A)]
            signal_val = min(dists)
            if coupled:
                should_update = signal_val > 0.15  # far from centroid = uncertain
            else:
                dists_init = [np.linalg.norm(fv - initial_scorer.centroids[ci, ai])
                              for ai in range(A)]
                should_update = min(dists_init) > 0.15
        elif signal_name == "entropy":
            probs = np.array(live_result.probabilities)
            probs = np.clip(probs, 1e-10, 1.0)
            signal_val = -np.sum(probs * np.log(probs))
            max_entropy = np.log(A)
            should_update = signal_val > 0.5 * max_entropy  # high entropy = uncertain
        elif signal_name == "conf_gap":
            probs = np.array(live_result.probabilities)
            sorted_p = np.sort(probs)[::-1]
            signal_val = sorted_p[0] - sorted_p[1] if len(sorted_p) > 1 else sorted_p[0]
            should_update = signal_val < 0.3  # small gap = uncertain
        elif signal_name == "override_rate":
            or_val = np.mean(override_windows[ci]) if len(override_windows[ci]) > 5 else 0.5
            signal_val = or_val
            should_update = or_val > 0.20  # high override rate = system wrong

        # Update only if signal says "uncertain/wrong"
        if should_update:
            scorer.update(fv, ci, result.action_index, correct, oa)
            updates += 1

        if n in CHECKPOINTS:
            confs = np.array(all_confs)
            corrs = np.array(all_corrects)
            cp[n] = {
                'acc': lc / n * 100,
                'ece': compute_ece(confs, corrs),
                'updates': updates,
                'update_rate': updates / n * 100,
            }

    return cp


def main():
    print("=" * 80)
    print("EXP-C5: V-FEEDBACK-COUPLING-SWEEP")
    print("=" * 80)

    base_mu = get_base_centroids()
    signals = ["confidence", "raw_distance", "entropy", "conf_gap", "override_rate"]

    # TEST A: Coupling (live vs frozen)
    print(f"\n{'=' * 80}")
    print("TEST A: COUPLING (live vs frozen feedback)")
    print(f"{'=' * 80}")

    coupling_results = {}
    for sig in signals:
        live_results = []
        frozen_results = []
        for seed in SEEDS:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r_live = run_feedback_test(seed, sig, coupled=True, gt=gt, base_mu=base_mu)
            r_frozen = run_feedback_test(seed, sig, coupled=False, gt=gt, base_mu=base_mu)
            live_results.append(r_live)
            frozen_results.append(r_frozen)

        live_acc = np.mean([r[N]['acc'] for r in live_results])
        frozen_acc = np.mean([r[N]['acc'] for r in frozen_results])
        live_ece = np.mean([r[N]['ece'] for r in live_results])
        frozen_ece = np.mean([r[N]['ece'] for r in frozen_results])
        diff_acc = abs(live_acc - frozen_acc)
        has_coupling = diff_acc > 0.5

        coupling_results[sig] = {
            'live_acc': live_acc, 'frozen_acc': frozen_acc,
            'live_ece': live_ece, 'frozen_ece': frozen_ece,
            'diff': diff_acc, 'coupling': has_coupling,
        }

        print(f"  {sig:>15s}: live={live_acc:.1f}% frozen={frozen_acc:.1f}% "
              f"diff={diff_acc:.1f}pp {'COUPLING' if has_coupling else 'BLIND'}")
        print(f"  {sig} done")

    # TEST B: Performance comparison (which signal is best?)
    print(f"\n{'=' * 80}")
    print("TEST B: PERFORMANCE (which gated controller is best?)")
    print(f"{'=' * 80}")
    print(f"  {'Signal':>15s}  {'Acc@2000':>8s}  {'ECE@2000':>8s}  {'Rate%':>6s}  {'Coupling?':>9s}")
    print(f"  {'-' * 55}")

    for sig in signals:
        all_r = []
        for seed in SEEDS:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_feedback_test(seed, sig, coupled=True, gt=gt, base_mu=base_mu)
            all_r.append(r)

        acc = np.mean([r[N]['acc'] for r in all_r])
        ece = np.mean([r[N]['ece'] for r in all_r])
        rate = np.mean([r[N]['update_rate'] for r in all_r])
        coupling = coupling_results[sig]['coupling']
        print(f"  {sig:>15s}  {acc:>6.1f}%  {ece:>8.4f}  {rate:>5.1f}%  "
              f"{'YES' if coupling else 'NO'}")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    any_coupling = any(v['coupling'] for v in coupling_results.values())
    coupled_signals = [k for k, v in coupling_results.items() if v['coupling']]
    print(f"Q1: Any signal shows coupling? {'YES: ' + ', '.join(coupled_signals) if any_coupling else 'NO (all blind)'}")

    best_acc_sig = max(signals, key=lambda s: coupling_results[s]['live_acc'])
    print(f"Q2: Best accuracy signal: {best_acc_sig} ({coupling_results[best_acc_sig]['live_acc']:.1f}%)")

    best_ece_sig = min(signals, key=lambda s: coupling_results[s]['live_ece'])
    print(f"Q3: Best ECE signal: {best_ece_sig} ({coupling_results[best_ece_sig]['live_ece']:.4f})")

    if not any_coupling:
        print(f"Q4: ALL signals blind → plant landscape is flat at operating point. CONFIRMED.")
    else:
        print(f"Q4: Coupling exists for {coupled_signals} → plant is NOT flat for these signals.")

    print("\nDONE.")


if __name__ == "__main__":
    main()
