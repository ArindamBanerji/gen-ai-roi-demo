"""
EXP-H3: TRANSLATION UPDATE + RICH INITIALIZATION
====================================================
HE4: Does a uniform category shift beat per-action SGD?
HE6: Does higher effective d initialization help?

Prior-GT alignment is 0.90-0.97 -- the constellation has the right
shape but wrong position. Tests whether a TRANSLATION (uniform
shift across all actions in a category) works better than
per-action SGD.

Also tests whether initializing centroids with higher effective
dimensionality reduces the 5.8pp capacity error.

Run: cd backend && python scripts/exp_h3_translation.py
Time: ~20 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_RUN = 2000
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


def enrich_initialization(base_mu, seed, noise_scale=0.05):
    """Add per-action noise in ALL dimensions to increase effective d."""
    rng = np.random.default_rng(seed + 20000)
    enriched = base_mu.copy()
    for ci in range(C):
        for ai in range(A):
            enriched[ci, ai] += rng.normal(0, noise_scale, D)
    return np.clip(enriched, 0, 1)


def run_experiment(seed, strategy, gt, start_mu):
    rng = np.random.default_rng(seed)
    scorer = make_scorer(start_mu.copy())
    ca_counts = np.zeros((C, A))

    # For translation update: accumulate per-category shift
    cat_shift_buffer = {ci: [] for ci in range(C)}
    K_TRANSLATE = 20  # batch size for translation estimate

    lc = 0
    all_confs, all_corrects = [], []

    for n in range(1, N_RUN + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc += 1
        all_confs.append(result.confidence)
        all_corrects.append(1.0 if correct else 0.0)

        ai = oa

        if strategy == "STATIC":
            pass

        elif strategy == "PER_ACTION_SGD":
            n_ca = ca_counts[ci, ai]
            scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
            mu_ca = scorer.centroids[ci, ai]
            eff_fv = mu_ca + max(scale, 0.005) * (fv - mu_ca)
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
            ca_counts[ci, ai] += 1

        elif strategy == "TRANSLATION":
            # Accumulate updates for category, apply uniform shift
            delta = fv - scorer.centroids[ci, ai]
            cat_shift_buffer[ci].append(delta)

            if len(cat_shift_buffer[ci]) >= K_TRANSLATE:
                mean_shift = np.mean(cat_shift_buffer[ci], axis=0)
                n_cat = sum(ca_counts[ci])
                scale = 1.0 / np.sqrt(1.0 + n_cat / (50.0 * A))
                # Apply SAME shift to ALL actions in this category
                for a in range(A):
                    scorer.centroids[ci, a] += max(scale, 0.005) * mean_shift * 0.05
                cat_shift_buffer[ci] = []
                ca_counts[ci, :] += K_TRANSLATE / A

        elif strategy == "TRANSLATION_GATED":
            # Only accumulate near-boundary queries
            if result.confidence <= 0.60:
                delta = fv - scorer.centroids[ci, ai]
                cat_shift_buffer[ci].append(delta)

                if len(cat_shift_buffer[ci]) >= K_TRANSLATE:
                    mean_shift = np.mean(cat_shift_buffer[ci], axis=0)
                    n_cat = sum(ca_counts[ci])
                    scale = 1.0 / np.sqrt(1.0 + n_cat / (50.0 * A))
                    for a in range(A):
                        scorer.centroids[ci, a] += max(scale, 0.005) * mean_shift * 0.05
                    cat_shift_buffer[ci] = []
                    ca_counts[ci, :] += K_TRANSLATE / A

        elif strategy == "HYBRID":
            # Translation for category shift + per-action for boundary tuning
            delta = fv - scorer.centroids[ci, ai]
            cat_shift_buffer[ci].append(delta * 0.5)

            # Per-action (half weight)
            n_ca = ca_counts[ci, ai]
            scale = 0.5 / np.sqrt(1.0 + n_ca / 50.0)
            mu_ca = scorer.centroids[ci, ai]
            eff_fv = mu_ca + max(scale, 0.005) * (fv - mu_ca)
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)

            if len(cat_shift_buffer[ci]) >= K_TRANSLATE:
                mean_shift = np.mean(cat_shift_buffer[ci], axis=0)
                n_cat = sum(ca_counts[ci])
                t_scale = 0.5 / np.sqrt(1.0 + n_cat / (50.0 * A))
                for a in range(A):
                    scorer.centroids[ci, a] += max(t_scale, 0.005) * mean_shift * 0.05
                cat_shift_buffer[ci] = []

            ca_counts[ci, ai] += 1

    confs = np.array(all_confs)
    corrs = np.array(all_corrects)
    return {'acc': lc / N_RUN * 100, 'ece': compute_ece(confs, corrs)}


def main():
    print("=" * 80)
    print("EXP-H3: TRANSLATION UPDATE + RICH INITIALIZATION")
    print("=" * 80)

    base_mu = get_base_centroids()
    strategies = ["STATIC", "PER_ACTION_SGD", "TRANSLATION",
                  "TRANSLATION_GATED", "HYBRID"]

    # PART A: Translation vs per-action
    print(f"\n{'=' * 80}")
    print("PART A: Translation vs per-action SGD (calibrated prior)")
    print(f"{'=' * 80}")
    print(f"  {'Strategy':>20s}  {'Acc':>6s}  {'ECE':>8s}")
    print(f"  {'-' * 38}")

    for strat in strategies:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_experiment(seed, strat, gt, base_mu)
            runs.append(r)
        acc = np.mean([r['acc'] for r in runs])
        ece = np.mean([r['ece'] for r in runs])
        print(f"  {strat:>20s}  {acc:5.1f}%  {ece:8.4f}")

    # Separation sweep
    print(f"\n  SEPARATION SWEEP:")
    print(f"  {'Sep':>6s}  {'Static':>7s}  {'PerAct':>7s}  {'Transl':>7s}  {'Hybrid':>7s}")
    print(f"  {'-' * 40}")
    for sep in [0.50, 0.75, 1.00, 1.50]:
        results = {}
        for strat in ["STATIC", "PER_ACTION_SGD", "TRANSLATION", "HYBRID"]:
            accs = []
            for seed in SEEDS_SHORT:
                gt = build_gt(np.random.default_rng(seed), base_mu)
                rng_s = np.random.default_rng(seed + 3000)
                direction = rng_s.normal(0, 1, gt.shape)
                direction = direction / np.linalg.norm(direction) * sep
                prior = np.clip(gt + direction, 0, 1)
                r = run_experiment(seed, strat, gt, prior)
                accs.append(r['acc'])
            results[strat] = np.mean(accs)
        print(f"  {sep:>6.2f}  {results['STATIC']:>5.1f}%  {results['PER_ACTION_SGD']:>5.1f}%  "
              f"{results['TRANSLATION']:>5.1f}%  {results['HYBRID']:>5.1f}%")

    # PART B: Rich initialization
    print(f"\n{'=' * 80}")
    print("PART B: Rich initialization (higher effective d)")
    print(f"{'=' * 80}")

    for noise_scale in [0.0, 0.02, 0.05, 0.10, 0.20]:
        accs_static, accs_sgd = [], []
        eff_dims = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            enriched = enrich_initialization(base_mu, seed, noise_scale)

            # Measure effective d
            for ci in range(C):
                centered = enriched[ci] - enriched[ci].mean(axis=0)
                svd = np.linalg.svd(centered, compute_uv=False)
                svd_norm = svd / svd.sum() if svd.sum() > 0 else svd
                ed = np.exp(-np.sum(svd_norm * np.log(svd_norm + 1e-10)))
                eff_dims.append(ed)

            r_s = run_experiment(seed, "STATIC", gt, enriched)
            r_d = run_experiment(seed, "PER_ACTION_SGD", gt, enriched)
            accs_static.append(r_s['acc'])
            accs_sgd.append(r_d['acc'])

        print(f"  noise={noise_scale:.2f}: eff_d={np.mean(eff_dims):.2f}  "
              f"static={np.mean(accs_static):.1f}%  sgd={np.mean(accs_sgd):.1f}%  "
              f"gap={np.mean(accs_sgd)-np.mean(accs_static):+.1f}pp")

    print("\nDONE.")


if __name__ == "__main__":
    main()
