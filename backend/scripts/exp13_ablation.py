"""
EXP-13: V-MECHANISM-ABLATION-LIFECYCLE
=======================================
Are the three pipeline stages additive or synergistic?

Run: cd backend && python scripts/exp13_ablation.py
Time: ~30 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, THETA_CONF, K_BATCH, SIGMA_BAR
)
from collections import Counter

N = 4000
WINDOW = 50
SEEDS_SHORT = [42, 123, 777]


def run_config(seed, gate=False, batch=False, scale=False):
    """Run with selectable mechanism stages."""
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)

    scorer = make_scorer()
    cat_weights = CATEGORY_WEIGHTS
    mean_weight = 1 / C

    buffers = {}
    counts = np.zeros((C, A))
    lc = 0
    timeline = []

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=cat_weights))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc += 1

        # Stage 1: Confidence gate
        if gate and result.confidence > THETA_CONF:
            if n % WINDOW == 0:
                timeline.append({'n': n, 'acc': lc / n * 100})
            continue  # blocked

        ai_target = oa

        if batch:
            # Stage 2: Batch accumulation + significance
            key = (ci, ai_target)
            if key not in buffers:
                buffers[key] = []
            buffers[key].append({'fv': fv.copy(), 'correct': correct})

            if len(buffers[key]) >= K_BATCH:
                buf = buffers[key]
                confirmed = [b for b in buf if b['correct']]
                K_total = len(buf)
                buffers[key] = []
                counts[ci, ai_target] += K_total

                if len(confirmed) == 0:
                    if n % WINDOW == 0:
                        timeline.append({'n': n, 'acc': lc / n * 100})
                    continue

                K_conf = len(confirmed)
                mu_cur = scorer.centroids[ci, ai_target]
                d_bar = np.mean([b['fv'] - mu_cur for b in confirmed], axis=0)
                magnitude = np.linalg.norm(d_bar)
                tau = SIGMA_BAR / np.sqrt(K_conf)

                if magnitude <= tau:
                    if n % WINDOW == 0:
                        timeline.append({'n': n, 'acc': lc / n * 100})
                    continue

                mean_fv = np.mean([b['fv'] for b in confirmed], axis=0)

                if scale:
                    # Stage 3: Precision + volume scaling
                    N_ca = counts[ci, ai_target]
                    precision = K_total / (N_ca + K_total)
                    vol_scale = np.sqrt(mean_weight / cat_weights[ci])
                    vol_scale = np.clip(vol_scale, 0.1, 3.0)
                    combined = np.clip(precision * vol_scale, 0.01, 1.0)
                    effective_fv = mu_cur + combined * (mean_fv - mu_cur)
                else:
                    effective_fv = mean_fv

                gt_actions = [b['correct'] for b in confirmed]
                r2 = scorer.score(effective_fv.astype(np.float64), ci)
                scorer.update(effective_fv.astype(np.float64), ci,
                              r2.action_index, r2.action_index == oa, oa)
            # else: buffer not full, wait
        else:
            # No batching — direct update
            if scale:
                counts[ci, ai_target] += 1
                N_ca = counts[ci, ai_target]
                precision = 1.0 / (N_ca + 1.0)
                vol_scale = np.sqrt(mean_weight / cat_weights[ci])
                vol_scale = np.clip(vol_scale, 0.1, 3.0)
                combined = np.clip(precision * vol_scale, 0.01, 1.0)
                mu_cur = scorer.centroids[ci, ai_target]
                effective_fv = mu_cur + combined * (fv - mu_cur)
                scorer.update(effective_fv.astype(np.float64), ci,
                              result.action_index, correct, oa)
            else:
                scorer.update(fv, ci, result.action_index, correct, oa)

        if n % WINDOW == 0:
            timeline.append({'n': n, 'acc': lc / n * 100})

    return timeline


def main():
    print("=" * 80)
    print("EXP-13: V-MECHANISM-ABLATION-LIFECYCLE")
    print("=" * 80)

    configs = [
        ("RAW (none)", False, False, False),
        ("GATE only", True, False, False),
        ("BATCH only", False, True, False),
        ("SCALE only", False, False, True),
        ("GATE+BATCH", True, True, False),
        ("GATE+SCALE", True, False, True),
        ("ALL THREE", True, True, True),
    ]

    results = {}
    for label, g, b, s in configs:
        tls = [run_config(seed, gate=g, batch=b, scale=s) for seed in SEEDS_SHORT]
        results[label] = tls
        print(f"  {label} done")

    # Find common timeline length
    n_points = min(len(tl) for tls in results.values() for tl in tls)

    # Results at key checkpoints
    print(f"\n{'=' * 80}")
    print("ACCURACY AT KEY CHECKPOINTS")
    print(f"{'=' * 80}")

    checkpoints_idx = [i for i in range(n_points) if results["RAW (none)"][0][i]['n'] in
                       [200, 500, 1000, 2000, 4000]]

    print(f"  {'N':>6s}", end="")
    for label, _, _, _ in configs:
        print(f"  {label[:12]:>12s}", end="")
    print()
    print(f"  {'-' * 100}")

    for i in checkpoints_idx:
        n = results["RAW (none)"][0][i]['n']
        print(f"  {n:>6d}", end="")
        for label, _, _, _ in configs:
            accs = [tl[i]['acc'] for tl in results[label] if i < len(tl)]
            print(f"  {np.mean(accs):10.1f}%", end="")
        print()

    # Interaction terms at N=4000
    print(f"\n{'=' * 80}")
    print(f"INTERACTION ANALYSIS AT N={results['RAW (none)'][0][-1]['n']}")
    print(f"{'=' * 80}")

    idx = n_points - 1
    raw_acc = np.mean([tl[idx]['acc'] for tl in results["RAW (none)"]])
    gate_acc = np.mean([tl[idx]['acc'] for tl in results["GATE only"]])
    batch_acc = np.mean([tl[idx]['acc'] for tl in results["BATCH only"]])
    scale_acc = np.mean([tl[idx]['acc'] for tl in results["SCALE only"]])
    gb_acc = np.mean([tl[idx]['acc'] for tl in results["GATE+BATCH"]])
    gs_acc = np.mean([tl[idx]['acc'] for tl in results["GATE+SCALE"]])
    all_acc = np.mean([tl[idx]['acc'] for tl in results["ALL THREE"]])

    e_gate = gate_acc - raw_acc
    e_batch = batch_acc - raw_acc
    e_scale = scale_acc - raw_acc

    i_gb = (gb_acc - raw_acc) - e_gate - e_batch
    i_gs = (gs_acc - raw_acc) - e_gate - e_scale

    i_all = (all_acc - raw_acc) - e_gate - e_batch - e_scale - i_gb - i_gs

    print(f"  Individual effects (vs RAW {raw_acc:.1f}%):")
    print(f"    e_gate  = {e_gate:+.1f}pp")
    print(f"    e_batch = {e_batch:+.1f}pp")
    print(f"    e_scale = {e_scale:+.1f}pp")
    print(f"  Pairwise interactions:")
    print(f"    i_gate_batch = {i_gb:+.1f}pp {'(SYNERGY)' if i_gb > 0.5 else '(ANTAGONISM)' if i_gb < -0.5 else '(ADDITIVE)'}")
    print(f"    i_gate_scale = {i_gs:+.1f}pp {'(SYNERGY)' if i_gs > 0.5 else '(ANTAGONISM)' if i_gs < -0.5 else '(ADDITIVE)'}")
    print(f"  Three-way interaction:")
    print(f"    i_all = {i_all:+.1f}pp")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    print(f"Q1: Pairwise interactions > 0.5pp? "
          f"gate_batch={i_gb:+.1f}pp gate_scale={i_gs:+.1f}pp "
          f"{'YES' if abs(i_gb) > 0.5 or abs(i_gs) > 0.5 else 'NO (additive)'}")
    print(f"Q2: Three-way interaction > 0.5pp? {i_all:+.1f}pp "
          f"{'YES' if abs(i_all) > 0.5 else 'NO'}")
    print(f"Q3: Sign: {'SYNERGY' if i_gb + i_gs > 0 else 'ANTAGONISM' if i_gb + i_gs < 0 else 'NEUTRAL'}")
    print(f"Q4: Largest individual effect: ", end="")
    effects = [("GATE", e_gate), ("BATCH", e_batch), ("SCALE", e_scale)]
    effects.sort(key=lambda x: abs(x[1]), reverse=True)
    print(f"{effects[0][0]} ({effects[0][1]:+.1f}pp)")

    print("\nDONE.")


if __name__ == "__main__":
    main()
