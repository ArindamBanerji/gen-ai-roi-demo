"""
EXP-C2: V-ACCURACY-ECE-TRADEOFF
=================================
Resolves CONFUSION 2+3: Is the accuracy-ECE tradeoff inherent?
Sweeps update rate to map the Pareto frontier.

Run: cd backend && python scripts/exp_c2_pareto.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, THETA_CONF, K_BATCH
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


def run_gated(seed, theta, gt, base_mu):
    """Gate-controlled update rate. theta=1.0 = STATIC."""
    rng = np.random.default_rng(seed)
    scorer = make_scorer(base_mu.copy())
    lc = 0
    updates = 0
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

        if result.confidence <= theta:
            scorer.update(fv, ci, result.action_index, correct, oa)
            updates += 1

    confs = np.array(all_confs)
    corrs = np.array(all_corrects)
    return {
        'acc': lc / N * 100,
        'ece': compute_ece(confs, corrs),
        'update_rate': updates / N * 100,
        'type': 'gated',
        'param': theta,
    }


def run_decay(seed, n0, gt, base_mu):
    """Sqrt-decay controlled update rate. n0 controls decay speed."""
    rng = np.random.default_rng(seed)
    scorer = make_scorer(base_mu.copy())
    ca_counts = np.zeros((C, A))
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

        ai_target = oa
        n_ca = ca_counts[ci, ai_target]
        scale = 1.0 / np.sqrt(1.0 + n_ca / n0)
        scale = max(scale, 0.001)
        mu_ca = scorer.centroids[ci, ai_target]
        effective_fv = mu_ca + scale * (fv - mu_ca)
        scorer.update(effective_fv.astype(np.float64), ci,
                      result.action_index, correct, oa)
        ca_counts[ci, ai_target] += 1

    confs = np.array(all_confs)
    corrs = np.array(all_corrects)
    return {
        'acc': lc / N * 100,
        'ece': compute_ece(confs, corrs),
        'update_rate': 100.0,  # always updates
        'type': 'decay',
        'param': n0,
    }


def main():
    print("=" * 80)
    print("EXP-C2: V-ACCURACY-ECE-TRADEOFF (Pareto Frontier)")
    print("=" * 80)

    base_mu = get_base_centroids()

    THETA_VALUES = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 1.00]
    N0_VALUES = [5, 10, 25, 50, 100, 500, 2000]

    all_points = []

    # Gated sweep
    for theta in THETA_VALUES:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            runs.append(run_gated(seed, theta, gt, base_mu))
        point = {
            'label': f'gate_{theta:.2f}',
            'acc': np.mean([r['acc'] for r in runs]),
            'ece': np.mean([r['ece'] for r in runs]),
            'rate': np.mean([r['update_rate'] for r in runs]),
            'type': 'gated',
        }
        all_points.append(point)
        print(f"  gate theta={theta:.2f} done")

    # Decay sweep
    for n0 in N0_VALUES:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            runs.append(run_decay(seed, n0, gt, base_mu))
        point = {
            'label': f'decay_n0={n0}',
            'acc': np.mean([r['acc'] for r in runs]),
            'ece': np.mean([r['ece'] for r in runs]),
            'rate': 100.0,
            'type': 'decay',
        }
        all_points.append(point)
        print(f"  decay n0={n0} done")

    # Add baselines
    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
    # Static is gate_1.00 already. Raw SGD:
    runs = []
    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)
        scorer = make_scorer(base_mu.copy())
        lc = 0
        confs, corrs = [], []
        for n in range(1, N + 1):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            result = scorer.score(fv, ci)
            correct = (result.action_index == oa)
            if correct: lc += 1
            confs.append(result.confidence)
            corrs.append(1.0 if correct else 0.0)
            scorer.update(fv, ci, result.action_index, correct, oa)
        runs.append({'acc': lc/N*100, 'ece': compute_ece(np.array(confs), np.array(corrs))})
    all_points.append({
        'label': 'RAW_SGD',
        'acc': np.mean([r['acc'] for r in runs]),
        'ece': np.mean([r['ece'] for r in runs]),
        'rate': 100.0, 'type': 'baseline',
    })

    # Full pipeline
    runs = []
    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)
        scorer = make_scorer(base_mu.copy())
        pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                       category_weights=CATEGORY_WEIGHTS)
        lc = 0
        confs, corrs = [], []
        for n in range(1, N + 1):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            result = scorer.score(fv, ci)
            correct = (result.action_index == oa)
            if correct: lc += 1
            confs.append(result.confidence)
            corrs.append(1.0 if correct else 0.0)
            pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)
        runs.append({'acc': lc/N*100, 'ece': compute_ece(np.array(confs), np.array(corrs))})
    all_points.append({
        'label': 'PIPELINE',
        'acc': np.mean([r['acc'] for r in runs]),
        'ece': np.mean([r['ece'] for r in runs]),
        'rate': 1.5, 'type': 'baseline',
    })

    # Results table
    print(f"\n{'=' * 80}")
    print("PARETO FRONTIER DATA")
    print(f"{'=' * 80}")
    print(f"  {'Label':>20s}  {'Type':>7s}  {'Acc':>6s}  {'ECE':>8s}  {'Rate%':>6s}")
    print(f"  {'-' * 55}")

    all_points.sort(key=lambda p: p['ece'])
    for p in all_points:
        print(f"  {p['label']:>20s}  {p['type']:>7s}  {p['acc']:5.1f}%  {p['ece']:8.4f}  {p['rate']:5.1f}%")

    # Pareto frontier identification
    print(f"\n{'=' * 80}")
    print("PARETO FRONTIER (non-dominated points)")
    print(f"{'=' * 80}")

    pareto = []
    for p in all_points:
        dominated = False
        for q in all_points:
            if q is p:
                continue
            if q['acc'] >= p['acc'] and q['ece'] <= p['ece']:
                if q['acc'] > p['acc'] or q['ece'] < p['ece']:
                    dominated = True
                    break
        if not dominated:
            pareto.append(p)
            print(f"  {p['label']:>20s}  acc={p['acc']:.1f}%  ECE={p['ece']:.4f}")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    print(f"Q1: Pareto-dominant strategy? {'YES: ' + pareto[0]['label'] if len(pareto) == 1 else 'NO (tradeoff)'}")

    if len(pareto) > 1:
        accs = [p['acc'] for p in pareto]
        eces = [p['ece'] for p in pareto]
        if max(accs) - min(accs) > 0 and max(eces) - min(eces) > 0:
            slope = (max(accs) - min(accs)) / (max(eces) - min(eces))
            print(f"Q2: Tradeoff slope: {slope:.1f}pp accuracy per 0.01 ECE")

    gated_pareto = [p for p in pareto if p['type'] == 'gated']
    decay_pareto = [p for p in pareto if p['type'] == 'decay']
    print(f"Q3: Gated and decay on same frontier? "
          f"gated: {len(gated_pareto)} points, decay: {len(decay_pareto)} points "
          f"{'SAME' if gated_pareto and decay_pareto else 'DIFF'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
