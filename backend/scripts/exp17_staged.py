"""
EXP-17: V-STAGED-ACTIVATION
=============================
Does raw SGD → pipeline switching fix cold start from generic prior?

Run: cd backend && python scripts/exp17_staged.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF
)

N = 2000
CHECKPOINTS = [50, 100, 200, 500, 1000, 2000]
SWITCH_POINTS = [50, 100, 200]
VELOCITY_THRESHOLD = 0.005


def run_staged(seed, switch_mode):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)

    # Start from GENERIC prior
    generic = np.full((C, A, D), 0.5)
    scorer = make_scorer(generic)

    pipeline = None
    pipeline_active = False
    switch_n = None

    if switch_mode == "PIPELINE_ALWAYS":
        pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                       category_weights=CATEGORY_WEIGHTS)
        pipeline_active = True
    elif switch_mode == "RAW_ALWAYS":
        pass  # never switch
    elif switch_mode == "STAGED_VELOCITY":
        pass  # switch based on velocity
    elif switch_mode.startswith("STAGED_"):
        fixed_n = int(switch_mode.split("_")[1])
        switch_n = fixed_n

    lc = 0
    prev_mu = scorer.centroids.copy()
    cp = {}

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc += 1

        # Check for velocity-based switch
        if switch_mode == "STAGED_VELOCITY" and not pipeline_active and n % 10 == 0 and n > 20:
            velocity = np.linalg.norm(scorer.centroids - prev_mu) / 10
            prev_mu = scorer.centroids.copy()
            if velocity < VELOCITY_THRESHOLD:
                pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                               category_weights=CATEGORY_WEIGHTS)
                pipeline_active = True
                switch_n = n

        # Check for fixed-N switch
        if switch_n is not None and not pipeline_active and n >= switch_n:
            if switch_mode.startswith("STAGED_") and switch_mode != "STAGED_VELOCITY":
                pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                               category_weights=CATEGORY_WEIGHTS)
                pipeline_active = True

        # Update
        if pipeline_active and pipeline:
            pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)
        elif switch_mode != "PIPELINE_ALWAYS":
            scorer.update(fv, ci, result.action_index, correct, oa)

        if n % 10 == 0:
            prev_mu = scorer.centroids.copy()

        if n in CHECKPOINTS:
            frob = float(np.linalg.norm(scorer.centroids - generic))
            cp[n] = {
                'acc': lc / n * 100,
                'frob': frob,
                'pipeline_active': pipeline_active,
            }

    return {'checkpoints': cp, 'actual_switch_n': switch_n if pipeline_active else None}


def main():
    print("=" * 80)
    print("EXP-17: V-STAGED-ACTIVATION (from GENERIC prior)")
    print("=" * 80)

    modes = ["PIPELINE_ALWAYS", "RAW_ALWAYS", "STAGED_50", "STAGED_100",
             "STAGED_200", "STAGED_VELOCITY"]
    all_results = {m: [] for m in modes}

    for m in modes:
        for seed in SEEDS:
            r = run_staged(seed, m)
            all_results[m].append(r)
        vel_switches = [r['actual_switch_n'] for r in all_results[m] if r['actual_switch_n']]
        extra = f" (switch at N={vel_switches})" if vel_switches else ""
        print(f"  {m} done{extra}")

    # Results table
    print(f"\n{'=' * 80}")
    print(f"{'N':>6s}", end="")
    for m in modes:
        label = m[:12]
        print(f"  {label:>12s}", end="")
    print()
    print("-" * 80)

    for n in CHECKPOINTS:
        print(f"{n:>6d}", end="")
        for m in modes:
            accs = [r['checkpoints'][n]['acc'] for r in all_results[m]]
            print(f"  {np.mean(accs):10.1f}%", end="")
        print()

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    pipe_always = np.mean([r['checkpoints'][N]['acc'] for r in all_results["PIPELINE_ALWAYS"]])
    raw_always = np.mean([r['checkpoints'][N]['acc'] for r in all_results["RAW_ALWAYS"]])

    best_staged = None
    best_staged_acc = 0
    for m in ["STAGED_50", "STAGED_100", "STAGED_200", "STAGED_VELOCITY"]:
        acc = np.mean([r['checkpoints'][N]['acc'] for r in all_results[m]])
        if acc > best_staged_acc:
            best_staged_acc = acc
            best_staged = m

    beats_both = best_staged_acc > pipe_always and best_staged_acc > raw_always
    print(f"Q1: Any STAGED beats both PIPELINE_ALWAYS ({pipe_always:.1f}%) "
          f"and RAW_ALWAYS ({raw_always:.1f}%)? "
          f"{'YES' if beats_both else 'NO'} — best: {best_staged} at {best_staged_acc:.1f}%")

    print(f"Q2: Best switchover: {best_staged} ({best_staged_acc:.1f}%)")

    vel_acc = np.mean([r['checkpoints'][N]['acc'] for r in all_results["STAGED_VELOCITY"]])
    staged_100_acc = np.mean([r['checkpoints'][N]['acc'] for r in all_results["STAGED_100"]])
    print(f"Q3: Velocity-based ({vel_acc:.1f}%) vs fixed STAGED_100 ({staged_100_acc:.1f}%): "
          f"{'VELOCITY WINS' if vel_acc > staged_100_acc else 'FIXED WINS'}")

    print(f"Q4: Best staged from GENERIC at N={N}: {best_staged_acc:.1f}%")

    print("\nDONE.")


if __name__ == "__main__":
    main()
