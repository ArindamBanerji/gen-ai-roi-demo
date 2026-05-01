"""
EXP-REPARAM-2: V-SPLIT-ORDER-LEARNING
========================================
Separate mean learning and variance learning with different strategies.

STRATEGY SPLIT:
  Means μ[c,a,i]: FROZEN after N=500
  DK weights w[c,a,i]: re-estimated from rolling window every 200 decisions

Compare to:
  ALL-FROZEN: η = 0 after N=500
  ALL-LEARNING: pipeline continues for everything
  SPLIT: freeze means, continue learning variances

If SPLIT beats ALL-FROZEN: variance learning adds value after mean convergence.
If SPLIT beats ALL-LEARNING: the split is the right architecture.

Run: cd backend && python scripts/exp_reparam2_split.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_RUN = 4000
N_TEST = 500
SEEDS_SHORT = [42, 123, 777]
FREEZE_AT = 500
DK_WINDOW = 500
DK_REESTIMATE_EVERY = 200


def score_dk(fv, ci, centroids, weights):
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        sims.append(-np.sum(weights[ci, ai] * diff ** 2))
    return int(np.argmax(sims))


def estimate_dk_from_decisions(decisions, centroids, n_rounds=4):
    """Estimate DK weights from a list of (fv, ci, oa) decisions."""
    weights = np.ones((C, A, D))
    for _ in range(n_rounds):
        for ci in range(C):
            for ai in range(A):
                for di in range(D):
                    cat_decs = [(fv, oa) for fv, cat, oa in decisions if cat == ci]
                    if len(cat_decs) < 10:
                        continue
                    best_w = weights[ci, ai, di]
                    best_acc = sum(1 for fv, oa in cat_decs
                                  if score_dk(fv, ci, centroids, weights) == oa) / len(cat_decs)
                    for w_trial in [0.1, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0]:
                        trial_w = weights.copy()
                        trial_w[ci, ai, di] = w_trial
                        trial_acc = sum(1 for fv, oa in cat_decs
                                        if score_dk(fv, ci, centroids, trial_w) == oa) / len(cat_decs)
                        if trial_acc > best_acc:
                            best_acc = trial_acc
                            best_w = w_trial
                    weights[ci, ai, di] = best_w
    return weights


def run_strategy(strategy, seed, gt, base_mu):
    """Run a learning strategy over N_RUN decisions."""
    rng = np.random.default_rng(seed)
    scorer = make_scorer(base_mu.copy())
    ca_counts = np.zeros((C, A))

    # For SPLIT strategy: accumulate decisions for DK estimation
    decision_buffer = []
    current_dk_weights = np.ones((C, A, D))
    frozen_centroids = None

    checkpoints = {}
    lc = 0

    for n in range(1, N_RUN + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        if strategy == "ALL_FROZEN":
            if n <= FREEZE_AT:
                result = scorer.score(fv, ci)
                correct = (result.action_index == oa)
                if correct: lc += 1
                scorer.update(fv, ci, result.action_index, correct, oa)
                ca_counts[ci, oa] += 1
            else:
                result = scorer.score(fv, ci)
                correct = (result.action_index == oa)
                if correct: lc += 1

        elif strategy == "ALL_LEARNING":
            result = scorer.score(fv, ci)
            correct = (result.action_index == oa)
            if correct: lc += 1
            scorer.update(fv, ci, result.action_index, correct, oa)
            ca_counts[ci, oa] += 1

        elif strategy == "SPLIT":
            # Phase 1: learn everything up to FREEZE_AT
            if n <= FREEZE_AT:
                result = scorer.score(fv, ci)
                correct = (result.action_index == oa)
                if correct: lc += 1
                scorer.update(fv, ci, result.action_index, correct, oa)
                ca_counts[ci, oa] += 1
                decision_buffer.append((fv, ci, oa))

                if n == FREEZE_AT:
                    frozen_centroids = scorer.centroids.copy()
            else:
                # Phase 2: freeze means, score with DK
                decision_buffer.append((fv, ci, oa))
                # Keep only last DK_WINDOW decisions
                if len(decision_buffer) > DK_WINDOW:
                    decision_buffer = decision_buffer[-DK_WINDOW:]

                # Re-estimate DK weights periodically
                if (n - FREEZE_AT) % DK_REESTIMATE_EVERY == 0 and len(decision_buffer) >= 100:
                    current_dk_weights = estimate_dk_from_decisions(
                        decision_buffer, frozen_centroids, n_rounds=4)

                # Score with DK on frozen centroids
                pred = score_dk(fv, ci, frozen_centroids, current_dk_weights)
                correct = (pred == oa)
                if correct: lc += 1

        elif strategy == "SPLIT_CUMULATIVE":
            # Same as SPLIT but DK uses ALL accumulated decisions, not just window
            if n <= FREEZE_AT:
                result = scorer.score(fv, ci)
                correct = (result.action_index == oa)
                if correct: lc += 1
                scorer.update(fv, ci, result.action_index, correct, oa)
                ca_counts[ci, oa] += 1
                decision_buffer.append((fv, ci, oa))

                if n == FREEZE_AT:
                    frozen_centroids = scorer.centroids.copy()
            else:
                decision_buffer.append((fv, ci, oa))

                if (n - FREEZE_AT) % DK_REESTIMATE_EVERY == 0 and len(decision_buffer) >= 100:
                    current_dk_weights = estimate_dk_from_decisions(
                        decision_buffer, frozen_centroids, n_rounds=4)

                pred = score_dk(fv, ci, frozen_centroids, current_dk_weights)
                correct = (pred == oa)
                if correct: lc += 1

        if n in [500, 1000, 1500, 2000, 3000, 4000]:
            checkpoints[n] = lc / n * 100

    V_final = float(np.sum((scorer.centroids - gt) ** 2)) if strategy != "SPLIT" else (
        float(np.sum((frozen_centroids - gt) ** 2)) if frozen_centroids is not None else 0)

    return checkpoints, V_final


def main():
    print("=" * 90)
    print("EXP-REPARAM-2: SPLIT ORDER LEARNING")
    print(f"Freeze means at N={FREEZE_AT}, continue learning variances")
    print("=" * 90)

    base_mu = get_base_centroids()
    strategies = ["ALL_FROZEN", "ALL_LEARNING", "SPLIT", "SPLIT_CUMULATIVE"]

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        print(f"\n  Seed {seed}:")
        print(f"  {'Strategy':>20s}  {'N=500':>6s}  {'N=1000':>6s}  {'N=1500':>6s}  "
              f"{'N=2000':>6s}  {'N=3000':>6s}  {'N=4000':>6s}  {'V_final':>7s}")
        print(f"  {'-' * 80}")

        for strat in strategies:
            print(f"  {strat:>20s}", end="", flush=True)
            cps, V = run_strategy(strat, seed, gt, base_mu)
            for n in [500, 1000, 1500, 2000, 3000, 4000]:
                if n in cps:
                    print(f"  {cps[n]:>4.1f}%", end="")
                else:
                    print(f"  {'—':>6s}", end="")
            print(f"  {V:>7.4f}")

    # DK learning curve: does DK accuracy improve with N?
    print(f"\n{'=' * 90}")
    print("DK LEARNING CURVE (variance learning over time)")
    print(f"{'=' * 90}")

    for seed in SEEDS_SHORT[:1]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)

        # Run centroid learning to convergence
        scorer = make_scorer(base_mu.copy())
        all_decisions = []
        for n in range(1, N_RUN + 1):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            result = scorer.score(fv, ci)
            if n <= FREEZE_AT:
                scorer.update(fv, ci, result.action_index,
                              result.action_index == oa, oa)
            all_decisions.append((fv, ci, oa))

        frozen_mu = scorer.centroids.copy()

        # DK accuracy at each accumulation point
        print(f"\n  Seed {seed}: DK accuracy vs accumulated decisions (means frozen at N={FREEZE_AT})")
        print(f"  {'N_accum':>8s}  {'DK_acc':>7s}  {'Cent_acc':>8s}  {'DK-Cent':>7s}")
        print(f"  {'-' * 35}")

        # Fixed test set
        rng_test = np.random.default_rng(seed + 50000)
        test_data = []
        for _ in range(N_TEST):
            ci = int(rng_test.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_test.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng_test)
            test_data.append((fv, ci, oa))

        cent_acc = sum(1 for fv, ci, oa in test_data
                       if make_scorer(frozen_mu).score(fv, ci).action_index == oa) / N_TEST * 100

        for n_accum in [200, 500, 1000, 1500, 2000, 3000, 4000]:
            decs = all_decisions[:n_accum]
            w = estimate_dk_from_decisions(decs, frozen_mu, n_rounds=5)
            dk_acc = sum(1 for fv, ci, oa in test_data
                         if score_dk(fv, ci, frozen_mu, w) == oa) / N_TEST * 100
            print(f"  {n_accum:>8d}  {dk_acc:>5.1f}%  {cent_acc:>6.1f}%  {dk_acc - cent_acc:>+5.1f}pp")

    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("Q1: Does SPLIT beat ALL_FROZEN at N=2000?")
    print("Q2: Does SPLIT beat ALL_LEARNING at N=2000?")
    print("Q3: Does DK accuracy improve from N=500 to N=4000?")
    print("Q4: Does SPLIT_CUMULATIVE beat SPLIT (data accumulation helps)?")

    print("\nDONE.")


if __name__ == "__main__":
    main()
