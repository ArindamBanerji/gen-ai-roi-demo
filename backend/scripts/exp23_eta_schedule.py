"""
EXP-23: V-ETA-SCHEDULE
========================
Is the pipeline over-engineered? Does decaying eta solve the problem simply?

THIS IS THE STOP-GATE EXPERIMENT. If decaying eta matches the pipeline,
the three-stage design is unnecessary complexity.

Run: cd backend && python scripts/exp23_eta_schedule.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF, SIGMA_BAR
)

N = 5000
CHECKPOINTS = [200, 500, 1000, 2000, 5000]


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


def run_eta_strategy(seed, strategy):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)

    scorer = make_scorer()
    static = make_scorer()

    pipeline = None
    if strategy == "PIPELINE":
        pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                       category_weights=CATEGORY_WEIGHTS)

    # Per-category-action decision counts (for decaying eta)
    ca_counts = np.zeros((C, A))
    lc = 0
    all_confs = []
    all_corrects = []
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

        # Strategy-specific update
        if strategy == "RAW_FIXED":
            scorer.update(fv, ci, result.action_index, correct, oa)

        elif strategy == "PIPELINE":
            pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)

        elif strategy == "DECAYING_ETA":
            # eta(n) = 0.05 / (1 + n_ca / 100) per (c,a) pair
            # We can't change ProfileScorer's internal eta,
            # so we scale the factor vector toward the centroid
            ai_target = oa
            n_ca = ca_counts[ci, ai_target]
            scale = 1.0 / (1.0 + n_ca / 100.0)
            scale = max(scale, 0.01)  # floor
            mu_ca = scorer.centroids[ci, ai_target]
            effective_fv = mu_ca + scale * (fv - mu_ca)
            scorer.update(effective_fv.astype(np.float64), ci,
                          result.action_index, correct, oa)
            ca_counts[ci, ai_target] += 1

        elif strategy == "SQRT_DECAY":
            # eta(n) = 0.05 / sqrt(1 + n_ca / 10)
            ai_target = oa
            n_ca = ca_counts[ci, ai_target]
            scale = 1.0 / np.sqrt(1.0 + n_ca / 10.0)
            scale = max(scale, 0.01)
            mu_ca = scorer.centroids[ci, ai_target]
            effective_fv = mu_ca + scale * (fv - mu_ca)
            scorer.update(effective_fv.astype(np.float64), ci,
                          result.action_index, correct, oa)
            ca_counts[ci, ai_target] += 1

        elif strategy == "GATE_PLUS_DECAY":
            # Confidence gate + decaying eta (no batch, no scaling)
            if result.confidence <= THETA_CONF:
                ai_target = oa
                n_ca = ca_counts[ci, ai_target]
                scale = 1.0 / (1.0 + n_ca / 100.0)
                scale = max(scale, 0.01)
                mu_ca = scorer.centroids[ci, ai_target]
                effective_fv = mu_ca + scale * (fv - mu_ca)
                scorer.update(effective_fv.astype(np.float64), ci,
                              result.action_index, correct, oa)
                ca_counts[ci, ai_target] += 1

        sr = static.score(fv, ci)

        if n in CHECKPOINTS:
            confs = np.array(all_confs)
            corrs = np.array(all_corrects)
            cp[n] = {
                'acc': lc / n * 100,
                'ece': compute_ece(confs, corrs),
                'drift': (lc / n * 100) - (lc / min(n, 200) * 100) if n > 200 else 0,
            }

    return cp


def main():
    print("=" * 80)
    print("EXP-23: V-ETA-SCHEDULE (STOP GATE EXPERIMENT)")
    print("If decaying eta matches pipeline, redesign before continuing.")
    print("=" * 80)

    strategies = ["RAW_FIXED", "DECAYING_ETA", "SQRT_DECAY",
                  "PIPELINE", "GATE_PLUS_DECAY"]
    all_results = {s: [] for s in strategies}

    for s in strategies:
        for seed in SEEDS:
            r = run_eta_strategy(seed, s)
            all_results[s].append(r)
        print(f"  {s} done")

    # Results table
    print(f"\n{'=' * 80}")
    print("ACCURACY at each checkpoint (mean across 5 seeds)")
    print(f"{'=' * 80}")
    print(f"  {'N':>6s}", end="")
    for s in strategies:
        print(f"  {s[:14]:>14s}", end="")
    print()
    print(f"  {'-' * 80}")

    for n in CHECKPOINTS:
        print(f"  {n:>6d}", end="")
        for s in strategies:
            accs = [r[n]['acc'] for r in all_results[s]]
            print(f"  {np.mean(accs):12.1f}%", end="")
        print()

    # ECE table
    print(f"\n{'=' * 80}")
    print("ECE at each checkpoint")
    print(f"{'=' * 80}")
    print(f"  {'N':>6s}", end="")
    for s in strategies:
        print(f"  {s[:14]:>14s}", end="")
    print()
    print(f"  {'-' * 80}")

    for n in CHECKPOINTS:
        print(f"  {n:>6d}", end="")
        for s in strategies:
            eces = [r[n]['ece'] for r in all_results[s]]
            print(f"  {np.mean(eces):14.4f}", end="")
        print()

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS (STOP GATE)")
    print("=" * 80)

    pipe_acc = np.mean([r[N]['acc'] for r in all_results["PIPELINE"]])
    pipe_ece = np.mean([r[N]['ece'] for r in all_results["PIPELINE"]])

    for s in ["DECAYING_ETA", "SQRT_DECAY", "GATE_PLUS_DECAY"]:
        acc = np.mean([r[N]['acc'] for r in all_results[s]])
        ece = np.mean([r[N]['ece'] for r in all_results[s]])
        acc_match = abs(acc - pipe_acc) < 0.5
        ece_match = abs(ece - pipe_ece) < 0.01
        print(f"  {s}: acc={acc:.1f}% (pipe={pipe_acc:.1f}%, match={'YES' if acc_match else 'NO'}) "
              f"ECE={ece:.4f} (pipe={pipe_ece:.4f}, match={'YES' if ece_match else 'NO'})")

    # Q3: Does GATE_PLUS_DECAY match pipeline?
    gpd_acc = np.mean([r[N]['acc'] for r in all_results["GATE_PLUS_DECAY"]])
    gpd_ece = np.mean([r[N]['ece'] for r in all_results["GATE_PLUS_DECAY"]])
    acc_match = abs(gpd_acc - pipe_acc) < 0.5
    ece_match = abs(gpd_ece - pipe_ece) < 0.01

    print(f"\n  CRITICAL Q3: GATE_PLUS_DECAY matches full PIPELINE?")
    print(f"    Accuracy: {'YES' if acc_match else 'NO'} ({gpd_acc:.1f}% vs {pipe_acc:.1f}%)")
    print(f"    ECE:      {'YES' if ece_match else 'NO'} ({gpd_ece:.4f} vs {pipe_ece:.4f})")

    if acc_match and ece_match:
        print(f"\n  >>> STOP GATE TRIGGERED: GATE_PLUS_DECAY matches pipeline.")
        print(f"  >>> Batch significance + fairness scaling are UNNECESSARY.")
        print(f"  >>> Redesign: confidence gate + decaying eta = two mechanisms.")
    elif acc_match and not ece_match:
        print(f"\n  >>> Accuracy matches but ECE differs. Pipeline's batch mechanism")
        print(f"  >>> contributes to calibration. Keep if calibration matters.")
    else:
        print(f"\n  >>> Pipeline complexity JUSTIFIED — simpler alternatives don't match.")

    # Q4: Best accuracy × ECE tradeoff
    print(f"\n  Q4: Best accuracy x ECE tradeoff at N={N}:")
    for s in strategies:
        acc = np.mean([r[N]['acc'] for r in all_results[s]])
        ece = np.mean([r[N]['ece'] for r in all_results[s]])
        # Lower ECE is better, higher acc is better
        score = acc * (1 - ece)  # simple composite
        print(f"    {s:>18s}: acc={acc:.1f}% ECE={ece:.4f} composite={score:.1f}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
