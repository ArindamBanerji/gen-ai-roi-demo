"""
EXP-15: V-NO-UPDATE-CONTROL
=============================
Is the pipeline just a fancy way of freezing centroids?

Run: cd backend && python scripts/exp15_no_update.py
Time: ~10 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF
)

N = 5000
CHECKPOINTS = [50, 200, 500, 1000, 2000, 5000]


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


def run_strategy(seed, strategy):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)

    scorer = make_scorer()
    static = make_scorer()

    pipeline = None
    if strategy == "PIPELINE":
        pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                       category_weights=CATEGORY_WEIGHTS)

    # GATED_ONLY: confidence gate but no batch/scaling
    gate_only_scorer = make_scorer() if strategy == "GATED_ONLY" else None

    lc = {s: 0 for s in ["learn", "static"]}
    all_confs = []
    all_corrects = []
    cp = {}

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        if strategy == "STATIC":
            result = scorer.score(fv, ci)
            correct = (result.action_index == oa)
            if correct: lc["learn"] += 1
            # Never update
        elif strategy == "PIPELINE":
            result = scorer.score(fv, ci)
            correct = (result.action_index == oa)
            if correct: lc["learn"] += 1
            pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)
        elif strategy == "GATED_ONLY":
            result = gate_only_scorer.score(fv, ci)
            correct = (result.action_index == oa)
            if correct: lc["learn"] += 1
            # Only update if confidence <= threshold (gate only, no batch/scaling)
            if result.confidence <= THETA_CONF:
                gate_only_scorer.update(fv, ci, result.action_index, correct, oa)
        elif strategy == "RAW_SGD":
            result = scorer.score(fv, ci)
            correct = (result.action_index == oa)
            if correct: lc["learn"] += 1
            scorer.update(fv, ci, result.action_index, correct, oa)

        sr = static.score(fv, ci)
        if sr.action_index == oa: lc["static"] += 1

        all_confs.append(result.confidence)
        all_corrects.append(1.0 if correct else 0.0)

        if n in CHECKPOINTS:
            confs = np.array(all_confs)
            corrs = np.array(all_corrects)
            ece = compute_ece(confs, corrs)
            update_count = 0
            if strategy == "PIPELINE" and pipeline:
                update_count = pipeline.stats['updates']
            elif strategy == "GATED_ONLY":
                update_count = n  # approximate — all that pass gate
            elif strategy == "RAW_SGD":
                update_count = n
            cp[n] = {
                'acc': lc["learn"] / n * 100,
                'static': lc["static"] / n * 100,
                'ece': ece,
                'updates': update_count,
            }

    return cp


def main():
    print("=" * 80)
    print("EXP-15: V-NO-UPDATE-CONTROL")
    print("Is the pipeline just a fancy way of freezing centroids?")
    print("=" * 80)

    strategies = ["STATIC", "PIPELINE", "GATED_ONLY", "RAW_SGD"]
    all_results = {s: [] for s in strategies}

    for s in strategies:
        for seed in SEEDS:
            r = run_strategy(seed, s)
            all_results[s].append(r)
        print(f"  {s} done")

    # Results table
    print(f"\n{'=' * 80}")
    print(f"{'N':>6s}", end="")
    for s in strategies:
        print(f"  {s + '_acc':>14s} {s + '_ECE':>10s}", end="")
    print()
    print("-" * 106)

    for n in CHECKPOINTS:
        print(f"{n:>6d}", end="")
        for s in strategies:
            accs = [r[n]['acc'] for r in all_results[s]]
            eces = [r[n]['ece'] for r in all_results[s]]
            print(f"  {np.mean(accs):12.1f}% {np.mean(eces):10.4f}", end="")
        print()

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    pipe_acc = np.mean([r[N]['acc'] for r in all_results["PIPELINE"]])
    static_acc = np.mean([r[N]['acc'] for r in all_results["STATIC"]])
    gated_acc = np.mean([r[N]['acc'] for r in all_results["GATED_ONLY"]])

    pipe_ece = np.mean([r[N]['ece'] for r in all_results["PIPELINE"]])
    static_ece = np.mean([r[N]['ece'] for r in all_results["STATIC"]])

    gap = abs(pipe_acc - static_acc)
    print(f"Q1: PIPELINE within 0.5pp of STATIC? pipe={pipe_acc:.1f}% static={static_acc:.1f}% "
          f"gap={gap:.1f}pp {'YES' if gap < 0.5 else 'NO'}")
    print(f"Q2: PIPELINE ECE better than STATIC? pipe={pipe_ece:.4f} static={static_ece:.4f} "
          f"{'YES' if pipe_ece < static_ece else 'NO'}")

    gated_gap = abs(gated_acc - pipe_acc)
    print(f"Q3: GATED_ONLY within 0.5pp of PIPELINE? gated={gated_acc:.1f}% pipe={pipe_acc:.1f}% "
          f"gap={gated_gap:.1f}pp {'YES' if gated_gap < 0.5 else 'NO'}")

    # Q4: When does RAW cross below STATIC?
    crossover = "never"
    for n in CHECKPOINTS:
        raw_acc = np.mean([r[n]['acc'] for r in all_results["RAW_SGD"]])
        sta_acc = np.mean([r[n]['acc'] for r in all_results["STATIC"]])
        if raw_acc < sta_acc:
            crossover = str(n)
            break
    print(f"Q4: RAW_SGD crosses below STATIC at N={crossover}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
