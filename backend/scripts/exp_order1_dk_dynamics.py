"""
EXP-ORDER-1: V-DK-LEARNING-DYNAMICS
======================================
THE critical experiment: does variance estimation have different
learning dynamics than mean estimation?

Fisher information predicts:
  Mean: I_μ = 1/σ²  → SNR → 0 at convergence → ρ_mean < 0
  Variance: I_σ² = 1/(2σ⁴) → SNR may NOT go to zero
  
If ρ_variance > 0.08 at the operating point:
  → DK weights compound from analyst decisions
  → "Compounding intelligence" includes the centroid itself (Order 1)
  → Architecture: freeze means, continue learning variances

Run: cd backend && python scripts/exp_order1_dk_dynamics.py
Time: ~20 min
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


def score_dk(fv, ci, centroids, weights):
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        sims.append(-np.sum(weights[ci, ai] * diff ** 2))
    return int(np.argmax(sims))


def estimate_dk_weights(decisions, centroids, n_rounds=5):
    """Estimate DK weights from a batch of decisions via coordinate descent."""
    weights = np.ones((C, A, D))

    for round_num in range(n_rounds):
        for ci in range(C):
            for ai in range(A):
                for di in range(D):
                    # Get decisions for this category
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


def compute_optimal_dk_weights(gt, centroids, seed, N=5000):
    """Compute 'GT-optimal' DK weights using large clean dataset."""
    rng = np.random.default_rng(seed + 99000)
    decisions = []
    for _ in range(N):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        decisions.append((fv, ci, ta))
    return estimate_dk_weights(decisions, centroids, n_rounds=8)


def main():
    print("=" * 90)
    print("EXP-ORDER-1: V-DK-LEARNING-DYNAMICS")
    print("Does ρ_variance > 0.08 at the operating point?")
    print("=" * 90)

    base_mu = get_base_centroids()

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)

        # Compute GT-optimal DK weights (oracle)
        print(f"\n  Seed {seed}: computing GT-optimal DK weights...")
        w_optimal = compute_optimal_dk_weights(gt, base_mu, seed)

        # Collect decisions in windows
        all_decisions = []
        for n in range(1, N_RUN + 1):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            all_decisions.append((fv, ci, oa))

        # At each checkpoint: estimate DK weights from recent window
        checkpoints = [200, 500, 1000, 1500, 2000, 3000, 4000]
        window_size = 400

        print(f"\n  {'N':>6s}  {'ρ_var':>7s}  {'DK_acc':>7s}  {'Cent_acc':>8s}  "
              f"{'DK-Cent':>7s}  {'w_dist_to_opt':>13s}  {'Cumul_DK':>9s}")
        print(f"  {'-' * 70}")

        for cp in checkpoints:
            if cp < window_size:
                continue

            # Estimate DK weights from RECENT window
            recent = all_decisions[cp - window_size:cp]
            w_recent = estimate_dk_weights(recent, base_mu, n_rounds=5)

            # Estimate DK weights from EARLIER window
            if cp >= 2 * window_size:
                earlier = all_decisions[cp - 2 * window_size:cp - window_size]
                w_earlier = estimate_dk_weights(earlier, base_mu, n_rounds=5)
            else:
                w_earlier = np.ones((C, A, D))

            # Estimate DK weights from ALL accumulated decisions
            cumul = all_decisions[:cp]
            w_cumul = estimate_dk_weights(cumul, base_mu, n_rounds=5)

            # Compute ρ_variance: alignment between weight CHANGE and
            # direction toward optimal weights
            weight_change = (w_recent - w_earlier).flatten()
            direction_to_optimal = (w_optimal - w_earlier).flatten()

            if np.linalg.norm(weight_change) > 1e-10 and np.linalg.norm(direction_to_optimal) > 1e-10:
                rho_var = np.dot(weight_change, direction_to_optimal) / (
                    np.linalg.norm(weight_change) * np.linalg.norm(direction_to_optimal))
            else:
                rho_var = 0.0

            # DK accuracy on held-out test
            rng_test = np.random.default_rng(seed + 50000)
            dk_correct, cent_correct, total = 0, 0, 0
            scorer = make_scorer(base_mu.copy())
            for _ in range(N_TEST):
                ci = int(rng_test.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng_test.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                ta = true_action(gt, ci, fv)
                oa = noise_realistic(ta, ci, rng_test)

                dk_pred = score_dk(fv, ci, base_mu, w_recent)
                cent_pred = scorer.score(fv, ci).action_index

                if dk_pred == oa: dk_correct += 1
                if cent_pred == oa: cent_correct += 1
                total += 1

            dk_acc = dk_correct / total * 100
            cent_acc = cent_correct / total * 100

            # Cumulative DK accuracy
            cumul_dk_correct = sum(1 for _ in range(N_TEST)
                                   if True)  # placeholder
            rng_test2 = np.random.default_rng(seed + 50000)
            cumul_correct = 0
            for _ in range(N_TEST):
                ci = int(rng_test2.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng_test2.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                ta = true_action(gt, ci, fv)
                oa = noise_realistic(ta, ci, rng_test2)
                if score_dk(fv, ci, base_mu, w_cumul) == oa:
                    cumul_correct += 1
            cumul_dk_acc = cumul_correct / N_TEST * 100

            w_dist = np.linalg.norm((w_recent - w_optimal).flatten())

            print(f"  {cp:>6d}  {rho_var:>+7.4f}  {dk_acc:>5.1f}%  {cent_acc:>6.1f}%  "
                  f"{dk_acc - cent_acc:>+5.1f}pp  {w_dist:>11.4f}  {cumul_dk_acc:>7.1f}%")

        # Weight trajectory analysis
        print(f"\n  DK WEIGHT CONVERGENCE (distance to optimal over time):")
        dists = []
        for cp in checkpoints:
            if cp < window_size:
                continue
            recent = all_decisions[cp - window_size:cp]
            w = estimate_dk_weights(recent, base_mu, n_rounds=5)
            d = np.linalg.norm((w - w_optimal).flatten())
            dists.append((cp, d))
            print(f"    N={cp}: dist_to_optimal = {d:.4f}")

        if len(dists) >= 2:
            decreasing = all(dists[i][1] >= dists[i + 1][1] for i in range(len(dists) - 1))
            print(f"    Monotonically decreasing? {'YES (converging)' if decreasing else 'NO (oscillating)'}")

    # COMPARISON: ρ_variance vs ρ_mean
    print(f"\n{'=' * 90}")
    print("COMPARISON: ρ_variance vs ρ_mean (from F1)")
    print(f"{'=' * 90}")
    print(f"  F1 showed ρ_mean ≈ -0.05 to -0.13 at convergence (N>500)")
    print(f"  If ρ_variance above is consistently > 0.08:")
    print(f"    → Variance estimation HAS different learning dynamics")
    print(f"    → The centroid DOES compound through Order 1 parameters")
    print(f"  If ρ_variance is also negative or near zero:")
    print(f"    → ALL centroid learning stops at convergence")
    print(f"    → Compounding is only through the MLP correction")

    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("Q1: Is ρ_variance > 0.08 at any checkpoint N ≥ 1000?")
    print("Q2: Does DK accuracy improve with N (compounding)?")
    print("Q3: Does cumulative DK beat recent-window DK (data accumulation helps)?")
    print("Q4: Do DK weights converge toward optimal (dist_to_optimal decreasing)?")
    print("Q5: Is ρ_variance qualitatively different from ρ_mean?")

    print("\nDONE.")


if __name__ == "__main__":
    main()
