"""
EXP-ORDER-2: V-ORDER-DIMENSIONALITY-INTERACTION
===================================================
The untested quadrant: high order (DK) + high dimensionality (enriched init).

Four conditions:
  A: Standard centroid (eff_dim ~2, Order 0)    -> baseline
  B: DK on standard (eff_dim ~2, Order 1)       -> G8 result
  C: Rich init centroid (eff_dim ~4, Order 0)    -> H3 result
  D: DK on rich init (eff_dim ~4, Order 1)       -> UNTESTED

If D > max(B, C): synergistic interaction
If D ~= max(B, C): one dominates, no interaction

Run: cd backend && python scripts/exp_order2_interaction.py
Time: ~20 min
"""

import numpy as np
from sklearn.metrics import accuracy_score
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_TRAIN = 2000
N_TEST = 500
SEEDS_SHORT = [42, 123, 777]


def score_dk(fv, ci, centroids, weights):
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        sims.append(-np.sum(weights[ci, ai] * diff ** 2))
    return int(np.argmax(sims))


def estimate_dk_weights(decisions, centroids, n_rounds=6):
    weights = np.ones((C, A, D))
    for round_num in range(n_rounds):
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


def enrich_init(base_mu, seed, noise_scale=0.08):
    rng = np.random.default_rng(seed + 20000)
    enriched = base_mu.copy()
    for ci in range(C):
        for ai in range(A):
            enriched[ci, ai] += rng.normal(0, noise_scale, D)
    return np.clip(enriched, 0, 1)


def effective_dim(centroids):
    dims = []
    for ci in range(C):
        centered = centroids[ci] - centroids[ci].mean(axis=0)
        svd = np.linalg.svd(centered, compute_uv=False)
        if svd.sum() > 0:
            p = svd / svd.sum()
            dims.append(np.exp(-np.sum(p * np.log(p + 1e-10))))
    return np.mean(dims)


def main():
    print("=" * 90)
    print("EXP-ORDER-2: ORDER x DIMENSIONALITY INTERACTION")
    print("=" * 90)

    base_mu = get_base_centroids()

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)

        # Collect training data
        decisions = []
        for n in range(N_TRAIN):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            decisions.append((fv, ci, oa))

        # Test set
        rng_test = np.random.default_rng(seed + 50000)
        test_data = []
        for _ in range(N_TEST):
            ci = int(rng_test.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_test.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng_test)
            test_data.append((fv, ci, oa))

        # Condition A: Standard centroid, Order 0
        scorer_a = make_scorer(base_mu.copy())
        acc_a = sum(1 for fv, ci, oa in test_data
                    if scorer_a.score(fv, ci).action_index == oa) / N_TEST * 100
        dim_a = effective_dim(base_mu)

        # Condition B: Standard centroid, Order 1 (DK)
        print(f"\n  Seed {seed}: calibrating DK (standard init)...")
        w_b = estimate_dk_weights(decisions, base_mu, n_rounds=6)
        acc_b = sum(1 for fv, ci, oa in test_data
                    if score_dk(fv, ci, base_mu, w_b) == oa) / N_TEST * 100

        # Condition C: Enriched centroid, Order 0
        enriched = enrich_init(base_mu, seed, noise_scale=0.08)
        scorer_c = make_scorer(enriched)
        acc_c = sum(1 for fv, ci, oa in test_data
                    if scorer_c.score(fv, ci).action_index == oa) / N_TEST * 100
        dim_c = effective_dim(enriched)

        # Condition D: Enriched centroid, Order 1 (DK)
        print(f"  Seed {seed}: calibrating DK (enriched init)...")
        w_d = estimate_dk_weights(decisions, enriched, n_rounds=6)
        acc_d = sum(1 for fv, ci, oa in test_data
                    if score_dk(fv, ci, enriched, w_d) == oa) / N_TEST * 100

        # Results
        print(f"\n  Seed {seed}:")
        print(f"  {'Condition':>25s}  {'EffDim':>6s}  {'Order':>5s}  {'Acc':>6s}  {'Delta vs A':>7s}")
        print(f"  {'-' * 55}")
        print(f"  {'A: Standard, Order 0':>25s}  {dim_a:>6.2f}  {'0':>5s}  {acc_a:>4.1f}%  {'--':>7s}")
        print(f"  {'B: Standard, Order 1':>25s}  {dim_a:>6.2f}  {'1':>5s}  {acc_b:>4.1f}%  {acc_b-acc_a:>+5.1f}pp")
        print(f"  {'C: Enriched, Order 0':>25s}  {dim_c:>6.2f}  {'0':>5s}  {acc_c:>4.1f}%  {acc_c-acc_a:>+5.1f}pp")
        print(f"  {'D: Enriched, Order 1':>25s}  {dim_c:>6.2f}  {'1':>5s}  {acc_d:>4.1f}%  {acc_d-acc_a:>+5.1f}pp")

        # Decompose
        order_effect = acc_b - acc_a
        dim_effect = acc_c - acc_a
        total_effect = acc_d - acc_a
        interaction = total_effect - order_effect - dim_effect

        print(f"\n  DECOMPOSITION:")
        print(f"    Order effect (B-A):       {order_effect:+.1f}pp")
        print(f"    Dimensionality effect (C-A): {dim_effect:+.1f}pp")
        print(f"    Interaction (D-A-B-C+A):  {interaction:+.1f}pp "
              f"({'SYNERGISTIC' if interaction > 0.5 else 'REDUNDANT' if interaction < -0.5 else 'ADDITIVE'})")
        print(f"    D vs max(B,C):            {acc_d - max(acc_b, acc_c):+.1f}pp")

    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("Q1: D > max(B, C)? (interaction is synergistic)")
    print("Q2: D approaches MLP ceiling (85.0%)?")
    print("Q3: Interaction term > 0? (positive = synergy)")

    print("\nDONE.")


if __name__ == "__main__":
    main()
