"""
EXP-14: V-PIPELINE-INTERNAL
==============================
Which internal pipeline mechanism dominates at each regime?

Run: cd backend && python scripts/exp14_internal.py
Time: ~20 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF, SIGMA_BAR
)
from collections import Counter

N = 4000
WINDOW = 200
SEEDS_SHORT = [42, 123, 777]


def run_pipeline_variant(seed, gt, no_gate=False, no_batch=False, no_scale=False):
    """Run pipeline with one stage removed."""
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    scorer = make_scorer()
    cat_weights = CATEGORY_WEIGHTS
    mean_weight = 1/C
    buffers = {}
    counts = np.zeros((C, A))
    lc = 0
    timeline = []

    theta = 1.0 if no_gate else THETA_CONF  # 1.0 = never blocks
    K = 1 if no_batch else K_BATCH  # 1 = no batching

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=cat_weights))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc += 1

        if result.confidence > theta:
            if n % WINDOW == 0:
                timeline.append({'n': n, 'acc': lc/n*100})
            continue

        ai_target = oa
        key = (ci, ai_target)
        if key not in buffers:
            buffers[key] = []
        buffers[key].append({'fv': fv.copy(), 'correct': correct})

        if len(buffers[key]) >= K:
            buf = buffers[key]
            confirmed = [b for b in buf if b['correct']]
            K_total = len(buf)
            buffers[key] = []
            counts[ci, ai_target] += K_total

            if len(confirmed) == 0:
                if n % WINDOW == 0:
                    timeline.append({'n': n, 'acc': lc/n*100})
                continue

            K_conf = len(confirmed)
            mu_cur = scorer.centroids[ci, ai_target]

            if not no_batch and K > 1:
                d_bar = np.mean([b['fv'] - mu_cur for b in confirmed], axis=0)
                if np.linalg.norm(d_bar) <= SIGMA_BAR / np.sqrt(K_conf):
                    if n % WINDOW == 0:
                        timeline.append({'n': n, 'acc': lc/n*100})
                    continue

            mean_fv = np.mean([b['fv'] for b in confirmed], axis=0)

            if not no_scale:
                N_ca = counts[ci, ai_target]
                precision = K_total / (N_ca + K_total)
                vol_scale = np.clip(np.sqrt(mean_weight / cat_weights[ci]), 0.1, 3.0)
                combined = np.clip(precision * vol_scale, 0.01, 1.0)
                effective_fv = mu_cur + combined * (mean_fv - mu_cur)
            else:
                effective_fv = mean_fv

            r2 = scorer.score(effective_fv.astype(np.float64), ci)
            scorer.update(effective_fv.astype(np.float64), ci,
                          r2.action_index, r2.action_index == oa, oa)

        if n % WINDOW == 0:
            timeline.append({'n': n, 'acc': lc/n*100})

    return timeline


def main():
    print("=" * 80)
    print("EXP-14: V-PIPELINE-INTERNAL DECOMPOSITION")
    print("=" * 80)

    base_mu = get_base_centroids()

    configs = [
        ("FULL (all 3)", False, False, False),
        ("NO_GATE (stages 2+3)", True, False, False),
        ("NO_BATCH (stages 1+3)", False, True, False),
        ("NO_SCALE (stages 1+2)", False, False, True),
    ]

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        print(f"\n  Seed {seed}:")
        print(f"  {'N':>6s}", end="")
        for label, _, _, _ in configs:
            print(f"  {label[:14]:>14s}", end="")
        print()
        print(f"  {'-' * 65}")

        results = {}
        for label, ng, nb, ns in configs:
            tl = run_pipeline_variant(seed, gt, no_gate=ng, no_batch=nb, no_scale=ns)
            results[label] = tl

        n_pts = min(len(tl) for tl in results.values())
        for i in range(n_pts):
            n = list(results.values())[0][i]['n']
            print(f"  {n:>6d}", end="")
            for label, _, _, _ in configs:
                if i < len(results[label]):
                    print(f"  {results[label][i]['acc']:>12.1f}%", end="")
                else:
                    print(f"  {'N/A':>14s}", end="")
            print()

    # Marginal contributions at N=4000
    print(f"\n{'=' * 80}")
    print("MARGINAL STAGE CONTRIBUTIONS (mean across seeds)")
    print(f"{'=' * 80}")

    gt = build_gt(np.random.default_rng(42), base_mu)
    all_results = {}
    for label, ng, nb, ns in configs:
        tls = [run_pipeline_variant(s, build_gt(np.random.default_rng(s), base_mu),
               no_gate=ng, no_batch=nb, no_scale=ns) for s in SEEDS_SHORT]
        all_results[label] = np.mean([tl[-1]['acc'] for tl in tls])

    full = all_results["FULL (all 3)"]
    print(f"  FULL:     {full:.1f}%")
    for label, _, _, _ in configs[1:]:
        acc = all_results[label]
        contrib = full - acc
        stage = label.split("(")[0].strip()
        print(f"  {label}: {acc:.1f}% -> {stage} contributes {contrib:+.1f}pp")

    print("\nDONE.")


if __name__ == "__main__":
    main()
