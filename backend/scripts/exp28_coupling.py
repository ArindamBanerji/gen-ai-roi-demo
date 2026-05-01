"""
EXP-28: V-CROSS-MECHANISM-COUPLING
=====================================
Full 2^3 factorial design for mechanism interactions.

Run: cd backend && python scripts/exp28_coupling.py
Time: ~20 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF, SIGMA_BAR
)
from collections import Counter

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


def run_factorial(seed, gate, batch, scale):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)
    scorer = make_scorer()
    cat_weights = CATEGORY_WEIGHTS
    mean_weight = 1/C
    buffers = {}
    counts = np.zeros((C, A))
    lc = 0
    all_confs = []
    all_corrects = []

    theta = THETA_CONF if gate else 1.0
    K = K_BATCH if batch else 1

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=cat_weights))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc += 1
        all_confs.append(result.confidence)
        all_corrects.append(1.0 if correct else 0.0)

        if result.confidence > theta:
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
                continue

            K_conf = len(confirmed)
            mu_cur = scorer.centroids[ci, ai_target]

            if batch and K > 1:
                d_bar = np.mean([b['fv'] - mu_cur for b in confirmed], axis=0)
                if np.linalg.norm(d_bar) <= SIGMA_BAR / np.sqrt(K_conf):
                    continue

            mean_fv = np.mean([b['fv'] for b in confirmed], axis=0)

            if scale:
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

    confs = np.array(all_confs)
    corrs = np.array(all_corrects)
    return {'acc': lc / N * 100, 'ece': compute_ece(confs, corrs)}


def main():
    print("=" * 80)
    print("EXP-28: V-CROSS-MECHANISM-COUPLING (2^3 factorial)")
    print("=" * 80)

    # Full 2^3 factorial
    configs = []
    for g in [False, True]:
        for b in [False, True]:
            for s in [False, True]:
                label = f"{'G' if g else '-'}{'B' if b else '-'}{'S' if s else '-'}"
                configs.append((label, g, b, s))

    results = {}
    for label, g, b, s in configs:
        runs = [run_factorial(seed, g, b, s) for seed in SEEDS_SHORT]
        results[label] = {
            'acc': np.mean([r['acc'] for r in runs]),
            'ece': np.mean([r['ece'] for r in runs]),
        }
        print(f"  {label} done")

    # Factorial table
    print(f"\n{'=' * 80}")
    print("FACTORIAL TABLE")
    print(f"{'=' * 80}")
    print(f"  {'Config':>6s}  {'Gate':>4s}  {'Batch':>5s}  {'Scale':>5s}  {'Acc':>6s}  {'ECE':>8s}")
    print(f"  {'-' * 40}")
    for label, g, b, s in configs:
        r = results[label]
        print(f"  {label:>6s}  {'ON' if g else 'off':>4s}  {'ON' if b else 'off':>5s}  "
              f"{'ON' if s else 'off':>5s}  {r['acc']:5.1f}%  {r['ece']:8.4f}")

    # Main effects
    print(f"\n{'=' * 80}")
    print("MAIN EFFECTS (accuracy)")
    print(f"{'=' * 80}")

    raw = results['---']['acc']

    # Gate main effect
    gate_on = np.mean([results[l]['acc'] for l, g, b, s in configs if g])
    gate_off = np.mean([results[l]['acc'] for l, g, b, s in configs if not g])
    e_gate = gate_on - gate_off
    print(f"  Gate: ON={gate_on:.1f}% OFF={gate_off:.1f}% effect={e_gate:+.1f}pp")

    batch_on = np.mean([results[l]['acc'] for l, g, b, s in configs if b])
    batch_off = np.mean([results[l]['acc'] for l, g, b, s in configs if not b])
    e_batch = batch_on - batch_off
    print(f"  Batch: ON={batch_on:.1f}% OFF={batch_off:.1f}% effect={e_batch:+.1f}pp")

    scale_on = np.mean([results[l]['acc'] for l, g, b, s in configs if s])
    scale_off = np.mean([results[l]['acc'] for l, g, b, s in configs if not s])
    e_scale = scale_on - scale_off
    print(f"  Scale: ON={scale_on:.1f}% OFF={scale_off:.1f}% effect={e_scale:+.1f}pp")

    # Same for ECE
    print(f"\n  MAIN EFFECTS (ECE):")
    gate_on_ece = np.mean([results[l]['ece'] for l, g, b, s in configs if g])
    gate_off_ece = np.mean([results[l]['ece'] for l, g, b, s in configs if not g])
    print(f"  Gate: ON={gate_on_ece:.4f} OFF={gate_off_ece:.4f} effect={gate_on_ece-gate_off_ece:+.4f}")

    batch_on_ece = np.mean([results[l]['ece'] for l, g, b, s in configs if b])
    batch_off_ece = np.mean([results[l]['ece'] for l, g, b, s in configs if not b])
    print(f"  Batch: ON={batch_on_ece:.4f} OFF={batch_off_ece:.4f} effect={batch_on_ece-batch_off_ece:+.4f}")

    scale_on_ece = np.mean([results[l]['ece'] for l, g, b, s in configs if s])
    scale_off_ece = np.mean([results[l]['ece'] for l, g, b, s in configs if not s])
    print(f"  Scale: ON={scale_on_ece:.4f} OFF={scale_off_ece:.4f} effect={scale_on_ece-scale_off_ece:+.4f}")

    # Two-way interactions
    print(f"\n{'=' * 80}")
    print("TWO-WAY INTERACTIONS (accuracy)")
    print(f"{'=' * 80}")

    # GB interaction
    gb_11 = np.mean([results[l]['acc'] for l, g, b, s in configs if g and b])
    gb_10 = np.mean([results[l]['acc'] for l, g, b, s in configs if g and not b])
    gb_01 = np.mean([results[l]['acc'] for l, g, b, s in configs if not g and b])
    gb_00 = np.mean([results[l]['acc'] for l, g, b, s in configs if not g and not b])
    i_gb = (gb_11 - gb_10 - gb_01 + gb_00) / 4
    print(f"  Gate*Batch: {i_gb:+.2f}pp {'SYNERGY' if i_gb > 0.25 else 'ANTAGONISM' if i_gb < -0.25 else 'ADDITIVE'}")

    gs_11 = np.mean([results[l]['acc'] for l, g, b, s in configs if g and s])
    gs_10 = np.mean([results[l]['acc'] for l, g, b, s in configs if g and not s])
    gs_01 = np.mean([results[l]['acc'] for l, g, b, s in configs if not g and s])
    gs_00 = np.mean([results[l]['acc'] for l, g, b, s in configs if not g and not s])
    i_gs = (gs_11 - gs_10 - gs_01 + gs_00) / 4
    print(f"  Gate*Scale: {i_gs:+.2f}pp {'SYNERGY' if i_gs > 0.25 else 'ANTAGONISM' if i_gs < -0.25 else 'ADDITIVE'}")

    bs_11 = np.mean([results[l]['acc'] for l, g, b, s in configs if b and s])
    bs_10 = np.mean([results[l]['acc'] for l, g, b, s in configs if b and not s])
    bs_01 = np.mean([results[l]['acc'] for l, g, b, s in configs if not b and s])
    bs_00 = np.mean([results[l]['acc'] for l, g, b, s in configs if not b and not s])
    i_bs = (bs_11 - bs_10 - bs_01 + bs_00) / 4
    print(f"  Batch*Scale: {i_bs:+.2f}pp {'SYNERGY' if i_bs > 0.25 else 'ANTAGONISM' if i_bs < -0.25 else 'ADDITIVE'}")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    max_interaction = max(abs(i_gb), abs(i_gs), abs(i_bs))
    print(f"Q1: Pairwise interactions > 0.5pp? max={max_interaction:.2f}pp "
          f"{'YES' if max_interaction > 0.5 else 'NO'}")
    print(f"Q3: Net interaction sign: GB={i_gb:+.2f} GS={i_gs:+.2f} BS={i_bs:+.2f}")
    print(f"Q4: Largest main effect: ", end="")
    effects = [("GATE", e_gate), ("BATCH", e_batch), ("SCALE", e_scale)]
    effects.sort(key=lambda x: abs(x[1]), reverse=True)
    print(f"{effects[0][0]} ({effects[0][1]:+.1f}pp)")

    # Best config
    best = max(results.items(), key=lambda x: x[1]['acc'])
    print(f"\n  Best config by accuracy: {best[0]} ({best[1]['acc']:.1f}%)")
    best_ece = min(results.items(), key=lambda x: x[1]['ece'])
    print(f"  Best config by ECE: {best_ece[0]} ({best_ece[1]['ece']:.4f})")

    # Composite
    best_comp = max(results.items(), key=lambda x: x[1]['acc'] * (1 - x[1]['ece']))
    print(f"  Best composite: {best_comp[0]} (acc={best_comp[1]['acc']:.1f}% ECE={best_comp[1]['ece']:.4f})")

    print("\nDONE.")


if __name__ == "__main__":
    main()
