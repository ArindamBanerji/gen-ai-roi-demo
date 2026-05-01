"""
EXP-C1: V-CLEAN-ECE
=====================
Resolves CONFUSION 1: What is the TRUE ECE comparison?
All strategies implemented fresh with verified labels.

Run: cd backend && python scripts/exp_c1_clean_ece.py
Time: ~10 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF
)

N = 5000
CHECKPOINTS = [0, 50, 200, 500, 1000, 2000, 5000]


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


def run_strategy(seed, strategy_name, gt, base_mu):
    """Each strategy implemented independently. No shared state."""
    rng = np.random.default_rng(seed)

    # Each gets its OWN scorer from the SAME base_mu
    scorer = make_scorer(base_mu.copy())

    # Per-category-action counts for decay strategies
    ca_counts = np.zeros((C, A))

    # Pipeline for PIPELINE strategy
    pipeline = None
    if strategy_name == "PIPELINE":
        pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                       category_weights=CATEGORY_WEIGHTS)

    lc = 0
    all_confs = []
    all_corrects = []
    cp = {}

    # N=0 checkpoint: measure before any decisions
    # Score 100 random alerts without updating
    rng_check = np.random.default_rng(seed + 99999)
    check_confs = []
    check_corrects = []
    for _ in range(100):
        ci = int(rng_check.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng_check.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng_check)
        result = scorer.score(fv, ci)
        check_confs.append(result.confidence)
        check_corrects.append(1.0 if result.action_index == oa else 0.0)
    cp[0] = {
        'acc': np.mean(check_corrects) * 100,
        'ece': compute_ece(np.array(check_confs), np.array(check_corrects)),
        'conf_sep': 0.0,
        'updates': 0,
    }

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

        # Strategy-specific update
        if strategy_name == "STATIC":
            pass  # NEVER update. Centroids frozen.

        elif strategy_name == "PIPELINE":
            pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)

        elif strategy_name == "RAW_SGD":
            scorer.update(fv, ci, result.action_index, correct, oa)

        elif strategy_name == "GATE_DECAY":
            # Confidence gate + sqrt decay, no batch, no volume scaling
            if result.confidence <= THETA_CONF:
                ai_target = oa
                n_ca = ca_counts[ci, ai_target]
                scale = 1.0 / np.sqrt(1.0 + n_ca / 10.0)
                scale = max(scale, 0.01)
                mu_ca = scorer.centroids[ci, ai_target]
                effective_fv = mu_ca + scale * (fv - mu_ca)
                scorer.update(effective_fv.astype(np.float64), ci,
                              result.action_index, correct, oa)
                ca_counts[ci, ai_target] += 1

        elif strategy_name == "SQRT_DECAY":
            # Sqrt decay only, no gate, no batch
            ai_target = oa
            n_ca = ca_counts[ci, ai_target]
            scale = 1.0 / np.sqrt(1.0 + n_ca / 10.0)
            scale = max(scale, 0.01)
            mu_ca = scorer.centroids[ci, ai_target]
            effective_fv = mu_ca + scale * (fv - mu_ca)
            scorer.update(effective_fv.astype(np.float64), ci,
                          result.action_index, correct, oa)
            ca_counts[ci, ai_target] += 1

        if n in CHECKPOINTS:
            confs = np.array(all_confs)
            corrs = np.array(all_corrects)
            ece = compute_ece(confs, corrs)
            correct_mask = corrs == 1.0
            incorrect_mask = corrs == 0.0
            conf_correct = confs[correct_mask].mean() if correct_mask.sum() > 0 else 0
            conf_incorrect = confs[incorrect_mask].mean() if incorrect_mask.sum() > 0 else 0

            cp[n] = {
                'acc': lc / n * 100,
                'ece': ece,
                'conf_sep': conf_correct - conf_incorrect,
                'updates': int(ca_counts.sum()) if strategy_name != "PIPELINE" else
                           (pipeline.stats['updates'] if pipeline else 0),
            }

    return cp


def main():
    print("=" * 80)
    print("EXP-C1: V-CLEAN-ECE (Verified Labels)")
    print("=" * 80)

    base_mu = get_base_centroids()
    strategies = ["STATIC", "PIPELINE", "RAW_SGD", "GATE_DECAY", "SQRT_DECAY"]
    all_results = {s: [] for s in strategies}

    for seed in SEEDS:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        for s in strategies:
            r = run_strategy(seed, s, gt, base_mu)
            all_results[s].append(r)
        print(f"  Seed {seed} done")

    # VERIFICATION: N=0 values must be identical across strategies
    print(f"\n{'=' * 80}")
    print("VERIFICATION: N=0 (before any updates)")
    print(f"{'=' * 80}")
    for s in strategies:
        acc_0 = np.mean([r[0]['acc'] for r in all_results[s]])
        ece_0 = np.mean([r[0]['ece'] for r in all_results[s]])
        print(f"  {s:>15s}: acc={acc_0:.1f}% ECE={ece_0:.4f}")

    # Main results table
    print(f"\n{'=' * 80}")
    print("CLEAN ECE COMPARISON")
    print(f"{'=' * 80}")

    for n in [n for n in CHECKPOINTS if n > 0]:
        print(f"\n  N={n}:")
        print(f"  {'Strategy':>15s}  {'Accuracy':>8s}  {'ECE':>8s}  {'ConfSep':>8s}  {'Updates':>7s}")
        print(f"  {'-' * 52}")
        for s in strategies:
            acc = np.mean([r[n]['acc'] for r in all_results[s]])
            ece = np.mean([r[n]['ece'] for r in all_results[s]])
            sep = np.mean([r[n]['conf_sep'] for r in all_results[s]])
            upd = np.mean([r[n]['updates'] for r in all_results[s]])
            print(f"  {s:>15s}  {acc:>6.1f}%  {ece:>8.4f}  {sep:>8.4f}  {upd:>5.0f}")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    final = {s: {'acc': np.mean([r[N]['acc'] for r in all_results[s]]),
                 'ece': np.mean([r[N]['ece'] for r in all_results[s]])}
             for s in strategies}

    best_ece = min(strategies, key=lambda s: final[s]['ece'])
    best_acc = max(strategies, key=lambda s: final[s]['acc'])
    print(f"Q1: Best ECE at N={N}: {best_ece} ({final[best_ece]['ece']:.4f})")
    print(f"Q2: Best accuracy at N={N}: {best_acc} ({final[best_acc]['acc']:.1f}%)")

    # Q3: Does STATIC ECE stay constant?
    static_eces = [np.mean([r[n]['ece'] for r in all_results["STATIC"]])
                   for n in CHECKPOINTS if n > 0]
    ece_range = max(static_eces) - min(static_eces)
    print(f"Q3: STATIC ECE constant? range={ece_range:.4f} "
          f"{'YES' if ece_range < 0.005 else 'NO'}")

    # Q4: Pareto dominant strategy?
    pareto = True
    for s in strategies:
        if s == best_acc:
            continue
        if final[s]['acc'] >= final[best_acc]['acc'] and final[s]['ece'] <= final[best_acc]['ece']:
            if final[s]['acc'] > final[best_acc]['acc'] or final[s]['ece'] < final[best_acc]['ece']:
                pareto = False
                break
    # Check if any strategy dominates on BOTH
    dominant = None
    for s in strategies:
        dominates_all = True
        for s2 in strategies:
            if s == s2:
                continue
            if final[s]['acc'] < final[s2]['acc'] or final[s]['ece'] > final[s2]['ece']:
                dominates_all = False
                break
        if dominates_all:
            dominant = s
            break
    print(f"Q4: Pareto-dominant strategy? {'YES: ' + dominant if dominant else 'NO (tradeoff exists)'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
