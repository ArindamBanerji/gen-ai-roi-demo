"""
EXP-RATE-2+5: FACTOR PRECISION + OVERLAP FUNCTION
====================================================
RATE-2: How does factor precision interact with DK over time?
RATE-5: The overlap function h(sigma) at 10 sigma levels.

Run: cd backend && python scripts/exp_rate25_overlap.py
Time: ~20 min
"""

import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_TRAIN = 2000
N_TEST = 500
SEEDS_SHORT = [42, 123, 777]
FREEZE_AT = 500


def score_dk(fv, ci, centroids, weights):
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        sims.append(-np.sum(weights[ci, ai] * diff ** 2))
    return int(np.argmax(sims))


def estimate_dk(decisions, centroids, n_rounds=5):
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


def collect_at_sigma(gt, seed, N, sigma):
    """Collect N decisions with specific factor noise level."""
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    scorer = make_scorer(base_mu.copy())
    decisions = []
    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, sigma, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        result = scorer.score(fv, ci)
        if n <= FREEZE_AT:
            scorer.update(fv, ci, result.action_index,
                          result.action_index == oa, oa)
        decisions.append((fv, ci, oa))
    return decisions, scorer.centroids.copy()


def main():
    base_mu = get_base_centroids()

    # ══════════════════════════════════════════════════════
    # RATE-5: OVERLAP FUNCTION h(sigma)
    # ══════════════════════════════════════════════════════
    print("=" * 90)
    print("RATE-5: OVERLAP FUNCTION h(sigma)")
    print("DK gain vs MLP gain at each sigma level")
    print("=" * 90)

    sigmas = [0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.14, 0.16, 0.18, 0.20]

    print(f"\n  {'sigma':>6s}  {'Cent':>6s}  {'DK':>6s}  {'MLP_b':>6s}  "
          f"{'DK_gain':>7s}  {'MLP_gain':>8s}  {'h(sigma)':>8s}  {'Regime':>10s}")
    print(f"  {'-' * 70}")

    dk_gains_at_prod = []  # for normalizing h(sigma)
    all_results = {}

    for sigma in sigmas:
        cent_accs, dk_accs, mlp_accs = [], [], []

        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            decs, frozen_mu = collect_at_sigma(gt, seed, N_TRAIN, sigma)

            # Test data at same sigma
            rng_test = np.random.default_rng(seed + 50000)
            test_data = []
            for _ in range(N_TEST):
                ci = int(rng_test.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng_test.normal(0.5, sigma, D), 0, 1).astype(np.float64)
                ta = true_action(gt, ci, fv)
                oa = noise_realistic(ta, ci, rng_test)
                test_data.append((fv, ci, oa))

            # Centroid
            scorer = make_scorer(frozen_mu)
            cent_acc = sum(1 for fv, ci, oa in test_data
                          if scorer.score(fv, ci).action_index == oa) / N_TEST * 100

            # DK
            dk_w = estimate_dk(decs, frozen_mu, n_rounds=5)
            dk_acc = sum(1 for fv, ci, oa in test_data
                         if score_dk(fv, ci, frozen_mu, dk_w) == oa) / N_TEST * 100

            # Bounded MLP
            X_train = np.array([np.concatenate([fv, np.eye(C)[ci]]) for fv, ci, oa in decs])
            y_train = np.array([oa for fv, ci, oa in decs])
            cent_preds_train = np.array([scorer.score(fv, ci).action_index for fv, ci, oa in decs])
            feat_train = np.column_stack([X_train, np.eye(A)[cent_preds_train]])

            X_test = np.array([np.concatenate([fv, np.eye(C)[ci]]) for fv, ci, oa in test_data])
            y_test = np.array([oa for fv, ci, oa in test_data])
            cent_preds_test = np.array([scorer.score(fv, ci).action_index for fv, ci, oa in test_data])
            feat_test = np.column_stack([X_test, np.eye(A)[cent_preds_test]])

            mlp = MLPClassifier(hidden_layer_sizes=(32,), max_iter=1000, random_state=seed)
            mlp.fit(feat_train, y_train)
            mlp_preds = mlp.predict(feat_test)

            # Bound
            gaps = []
            for fv, ci, oa in test_data:
                result = scorer.score(fv, ci)
                probs = np.array(result.probabilities)
                sp = np.sort(probs)[::-1]
                gaps.append(sp[0] - sp[1])
            gaps = np.array(gaps)

            bounded = cent_preds_test.copy()
            for i in range(N_TEST):
                if mlp_preds[i] != cent_preds_test[i] and gaps[i] <= 0.30:
                    bounded[i] = mlp_preds[i]
            mlp_acc = accuracy_score(y_test, bounded) * 100

            cent_accs.append(cent_acc)
            dk_accs.append(dk_acc)
            mlp_accs.append(mlp_acc)

        mc = np.mean(cent_accs)
        md = np.mean(dk_accs)
        mm = np.mean(mlp_accs)
        dk_gain = md - mc
        mlp_gain = mm - mc

        all_results[sigma] = {'cent': mc, 'dk': md, 'mlp': mm,
                              'dk_gain': dk_gain, 'mlp_gain': mlp_gain}

        if abs(sigma - 0.15) < 0.005:
            dk_gain_prod = dk_gain

    # Compute h(sigma) normalized to production
    dk_gain_prod = all_results.get(0.14, all_results.get(0.16, {'dk_gain': 1}))['dk_gain']
    if dk_gain_prod == 0:
        dk_gain_prod = 1

    for sigma in sigmas:
        r = all_results[sigma]
        h = r['dk_gain'] / max(abs(dk_gain_prod), 0.01)
        regime = "DK dominates" if r['dk_gain'] > r['mlp_gain'] + 0.5 else (
                 "MLP dominates" if r['mlp_gain'] > r['dk_gain'] + 0.5 else "similar")
        print(f"  {sigma:>6.2f}  {r['cent']:>4.1f}%  {r['dk']:>4.1f}%  {r['mlp']:>4.1f}%  "
              f"{r['dk_gain']:>+5.1f}pp  {r['mlp_gain']:>+6.1f}pp  {h:>7.2f}  {regime:>10s}")

    # ══════════════════════════════════════════════════════
    # RATE-2: FACTOR PRECISION TRAJECTORY
    # ══════════════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("RATE-2: FACTOR PRECISION TRAJECTORY")
    print("What happens when sigma improves over time (simulating graph enrichment)?")
    print("=" * 90)

    N_TRAJECTORY = 4000
    gammas = [0.1, 0.2, 0.3, 0.5]
    sigma_base = 0.15
    N0 = 500

    for gamma in gammas:
        print(f"\n  Gamma={gamma} (sigma_eff = {sigma_base} * ({N0}/({N0}+N))^{gamma}):")
        print(f"  {'N':>6s}  {'sigma_eff':>9s}  {'DK_acc':>7s}  {'Cent_acc':>8s}  {'DK_gain':>7s}")
        print(f"  {'-' * 45}")

        accs_dk, accs_cent = [], []
        for seed in SEEDS_SHORT[:1]:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            rng = np.random.default_rng(seed)
            scorer = make_scorer(base_mu.copy())
            decisions = []

            for n in range(1, N_TRAJECTORY + 1):
                sigma_eff = sigma_base * (N0 / (N0 + n)) ** gamma
                ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng.normal(0.5, sigma_eff, D), 0, 1).astype(np.float64)
                ta = true_action(gt, ci, fv)
                oa = noise_realistic(ta, ci, rng)
                result = scorer.score(fv, ci)
                if n <= FREEZE_AT:
                    scorer.update(fv, ci, result.action_index,
                                  result.action_index == oa, oa)
                decisions.append((fv, ci, oa))

            frozen_mu = scorer.centroids.copy()

            for cp in [500, 1000, 2000, 3000, 4000]:
                sigma_at_cp = sigma_base * (N0 / (N0 + cp)) ** gamma

                rng_test = np.random.default_rng(seed + 50000)
                test_data = []
                for _ in range(N_TEST):
                    ci = int(rng_test.choice(C, p=CATEGORY_WEIGHTS))
                    fv = np.clip(rng_test.normal(0.5, sigma_at_cp, D), 0, 1).astype(np.float64)
                    ta = true_action(gt, ci, fv)
                    oa = noise_realistic(ta, ci, rng_test)
                    test_data.append((fv, ci, oa))

                dk_w = estimate_dk(decisions[:cp], frozen_mu, n_rounds=5)
                dk_acc = sum(1 for fv, ci, oa in test_data
                             if score_dk(fv, ci, frozen_mu, dk_w) == oa) / N_TEST * 100
                cent_acc = sum(1 for fv, ci, oa in test_data
                               if make_scorer(frozen_mu).score(fv, ci).action_index == oa) / N_TEST * 100

                print(f"  {cp:>6d}  {sigma_at_cp:>9.4f}  {dk_acc:>5.1f}%  {cent_acc:>6.1f}%  "
                      f"{dk_acc - cent_acc:>+5.1f}pp")

    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("RATE-5:")
    print("  Q1: h(sigma) smoothly decreasing as sigma decreases?")
    print("  Q2: At what sigma does DK gain reach 0?")
    print("  Q3: DK and MLP attenuation same shape?")
    print("RATE-2:")
    print("  Q4: Does improving sigma + DK beat either alone?")
    print("  Q5: At what gamma does graph enrichment dominate DK?")

    print("\nDONE.")


if __name__ == "__main__":
    main()
