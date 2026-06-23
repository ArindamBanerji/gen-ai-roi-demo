"""
EXP-D8: CANDIDATE PARAMETER SENSITIVITY
==========================================
Do the new candidates have parameters with LEVERAGE?
Unlike the current pipeline (EXP-5: 0.4pp spread across 20 configs),
can we tune the candidates to trade accuracy for ECE?

Run: cd backend && python scripts/exp_d8_sensitivity.py
Time: ~25 min
"""

import numpy as np
from collections import deque
from exp_shared import (
    C, A, D, CATEGORIES, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N = 2000
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


def run_parameterized(seed, controller_name, params, gt, base_mu):
    rng = np.random.default_rng(seed)
    scorer = make_scorer(base_mu.copy())
    ca_counts = np.zeros((C, A))
    override_windows = {ci: deque(maxlen=50) for ci in range(C)}
    mode = {ci: "LEARN" for ci in range(C)}
    prev_mu = scorer.centroids.copy()
    velocity = 0.01

    lc = 0
    all_confs, all_corrects = [], []

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

        if n % 50 == 0:
            velocity = np.linalg.norm(scorer.centroids - prev_mu) / 50
            prev_mu = scorer.centroids.copy()

        ai = oa
        n_ca = ca_counts[ci, ai]

        if controller_name == "A_decay":
            # Param: n0 (decay timescale)
            n0 = params['n0']
            scale = 1.0 / np.sqrt(1.0 + n_ca / n0)
            scale = max(scale, 0.005)
        elif controller_name == "C_dual":
            # Params: theta_high, theta_low, eta_fast, eta_slow
            or_val = np.mean(override_windows[ci]) if len(override_windows[ci]) > 5 else 0.5
            if mode[ci] == "PRESERVE" and or_val > params['theta_high']:
                mode[ci] = "LEARN"
            elif mode[ci] == "LEARN" and or_val < params['theta_low']:
                mode[ci] = "PRESERVE"
            eta = params['eta_fast'] if mode[ci] == "LEARN" else params['eta_slow']
            decay = 1.0 / np.sqrt(1.0 + n_ca / 100.0)
            scale = (eta / 0.05) * decay
            scale = max(scale, 0.005)
        elif controller_name == "E_cascade":
            # Param: ece_target
            # Simplified: adjust eta based on running ECE vs target
            if len(all_confs) > 50:
                recent_ece = compute_ece(
                    np.array(all_confs[-100:]), np.array(all_corrects[-100:]), 5)
                e = params['ece_target'] - recent_ece
                eta = np.clip(0.05 + params['kp'] * e, 0.001, 0.15)
            else:
                eta = 0.05
            decay = 1.0 / (1.0 + n_ca / 100.0)
            scale = (eta / 0.05) * decay
            scale = max(scale, 0.001)

        mu_ca = scorer.centroids[ci, ai]
        eff_fv = mu_ca + scale * (fv - mu_ca)
        scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
        ca_counts[ci, ai] += 1

    confs = np.array(all_confs)
    corrs = np.array(all_corrects)
    return {'acc': lc / N * 100, 'ece': compute_ece(confs, corrs)}


def main():
    print("=" * 80)
    print("EXP-D8: CANDIDATE PARAMETER SENSITIVITY")
    print("=" * 80)

    base_mu = get_base_centroids()

    # CANDIDATE A: Sweep n0 (decay timescale)
    print(f"\n  CANDIDATE A (Decay-Only): sweep n0")
    print(f"  {'n0':>6s}  {'Acc':>6s}  {'ECE':>8s}")
    print(f"  {'-' * 25}")
    a_results = []
    for n0 in [5, 10, 25, 50, 100, 200, 500, 1000]:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_parameterized(seed, "A_decay", {'n0': n0}, gt, base_mu)
            runs.append(r)
        acc = np.mean([r['acc'] for r in runs])
        ece = np.mean([r['ece'] for r in runs])
        a_results.append({'n0': n0, 'acc': acc, 'ece': ece})
        print(f"  {n0:>6d}  {acc:5.1f}%  {ece:8.4f}")
    a_spread = max(r['acc'] for r in a_results) - min(r['acc'] for r in a_results)
    print(f"  Accuracy spread: {a_spread:.1f}pp")

    # CANDIDATE C: Sweep theta_high/theta_low
    print(f"\n  CANDIDATE C (Dual-Mode): sweep theta_high x eta_fast")
    print(f"  {'theta_hi':>8s}  {'eta_fast':>8s}  {'Acc':>6s}  {'ECE':>8s}")
    print(f"  {'-' * 35}")
    c_results = []
    for th in [0.15, 0.20, 0.25, 0.30, 0.40]:
        for ef in [0.04, 0.08, 0.12, 0.20]:
            runs = []
            for seed in SEEDS_SHORT:
                gt = build_gt(np.random.default_rng(seed), base_mu)
                r = run_parameterized(seed, "C_dual",
                                      {'theta_high': th, 'theta_low': th * 0.4,
                                       'eta_fast': ef, 'eta_slow': 0.005}, gt, base_mu)
                runs.append(r)
            acc = np.mean([r['acc'] for r in runs])
            ece = np.mean([r['ece'] for r in runs])
            c_results.append({'th': th, 'ef': ef, 'acc': acc, 'ece': ece})
            print(f"  {th:>8.2f}  {ef:>8.2f}  {acc:5.1f}%  {ece:8.4f}")
    c_spread = max(r['acc'] for r in c_results) - min(r['acc'] for r in c_results)
    print(f"  Accuracy spread: {c_spread:.1f}pp")

    # CANDIDATE E: Sweep ece_target
    print(f"\n  CANDIDATE E (Cascade ECE): sweep ece_target x kp")
    print(f"  {'ece_tgt':>8s}  {'kp':>6s}  {'Acc':>6s}  {'ECE':>8s}")
    print(f"  {'-' * 32}")
    e_results = []
    for tgt in [0.03, 0.05, 0.08, 0.12, 0.20]:
        for kp in [0.2, 0.5, 1.0, 2.0]:
            runs = []
            for seed in SEEDS_SHORT:
                gt = build_gt(np.random.default_rng(seed), base_mu)
                r = run_parameterized(seed, "E_cascade",
                                      {'ece_target': tgt, 'kp': kp}, gt, base_mu)
                runs.append(r)
            acc = np.mean([r['acc'] for r in runs])
            ece = np.mean([r['ece'] for r in runs])
            e_results.append({'tgt': tgt, 'kp': kp, 'acc': acc, 'ece': ece})
            print(f"  {tgt:>8.2f}  {kp:>6.1f}  {acc:5.1f}%  {ece:8.4f}")
    e_spread = max(r['acc'] for r in e_results) - min(r['acc'] for r in e_results)
    print(f"  Accuracy spread: {e_spread:.1f}pp")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    print(f"Q1: Candidate A has leverage? spread={a_spread:.1f}pp "
          f"{'YES' if a_spread > 1.0 else 'NO (same as current pipeline)'}")
    print(f"Q2: Candidate C has leverage? spread={c_spread:.1f}pp "
          f"{'YES' if c_spread > 1.0 else 'NO'}")
    print(f"Q3: Candidate E has leverage? spread={e_spread:.1f}pp "
          f"{'YES' if e_spread > 1.0 else 'NO'}")

    # Does any candidate show accuracy-ECE tradeoff via parameters?
    for name, results in [("A", a_results), ("C", c_results), ("E", e_results)]:
        accs = [r['acc'] for r in results]
        eces = [r['ece'] for r in results]
        if np.std(accs) > 0 and np.std(eces) > 0:
            corr = np.corrcoef(accs, eces)[0, 1]
            print(f"Q4_{name}: acc-ECE correlation = {corr:+.3f} "
                  f"{'TRADEOFF' if corr > 0.3 else 'INDEPENDENT' if abs(corr) < 0.3 else 'ALIGNED'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
