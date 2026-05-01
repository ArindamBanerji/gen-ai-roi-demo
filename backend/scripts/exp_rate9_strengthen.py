"""
EXP-RATE-9+10+11: FRAMEWORK STRENGTHENING EXPERIMENTS
=======================================================
Three experiments that test the formal properties the framework needs:

RATE-9:  H-MONO — Does cumulative DK EVER drop below centroid?
         H-FLOOR — Does mixing DK with centroid guarantee safety?
RATE-10: H-CATCOMP — Per-category DK improvement ∝ log(N_c)?
RATE-11: H-DEPLOY — Full two-phase deployment end-to-end
         H-BRIER — Is Brier more monotonic than accuracy?

Run: cd backend && python scripts/exp_rate9_strengthen.py
Time: ~25 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_MAX = 8000
N_TEST = 500
FREEZE_AT = 500
DK_INTERVAL = 200
SEEDS_SHORT = [42, 123, 777]


def score_dk(fv, ci, centroids, weights):
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        sims.append(-np.sum(weights[ci, ai] * diff ** 2))
    sims = np.array(sims)
    return int(np.argmax(sims)), sims


def score_mixed(fv, ci, centroids, dk_weights, alpha):
    """Mixed scoring: alpha*DK + (1-alpha)*centroid."""
    sims_dk = []
    sims_cent = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        sims_dk.append(-np.sum(dk_weights[ci, ai] * diff ** 2))
        sims_cent.append(-np.sum(diff ** 2))
    sims_dk = np.array(sims_dk)
    sims_cent = np.array(sims_cent)
    # Normalize each to [0,1] range for mixing
    if sims_dk.max() != sims_dk.min():
        sims_dk_n = (sims_dk - sims_dk.min()) / (sims_dk.max() - sims_dk.min())
    else:
        sims_dk_n = np.ones(A) / A
    if sims_cent.max() != sims_cent.min():
        sims_cent_n = (sims_cent - sims_cent.min()) / (sims_cent.max() - sims_cent.min())
    else:
        sims_cent_n = np.ones(A) / A
    mixed = alpha * sims_dk_n + (1 - alpha) * sims_cent_n
    return int(np.argmax(mixed))


def dk_probs(sims):
    sims = sims - np.max(sims)
    e = np.exp(sims)
    return e / e.sum()


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
                                  if score_dk(fv, ci, centroids, weights)[0] == oa) / len(cat_decs)
                    for w_trial in [0.1, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0]:
                        trial_w = weights.copy()
                        trial_w[ci, ai, di] = w_trial
                        trial_acc = sum(1 for fv, oa in cat_decs
                                        if score_dk(fv, ci, centroids, trial_w)[0] == oa) / len(cat_decs)
                        if trial_acc > best_acc:
                            best_acc = trial_acc
                            best_w = w_trial
                    weights[ci, ai, di] = best_w
    return weights


def evaluate_dk(test_data, centroids, weights):
    correct = sum(1 for fv, ci, oa in test_data
                  if score_dk(fv, ci, centroids, weights)[0] == oa)
    return correct / len(test_data) * 100


def evaluate_mixed(test_data, centroids, weights, alpha):
    correct = sum(1 for fv, ci, oa in test_data
                  if score_mixed(fv, ci, centroids, weights, alpha) == oa)
    return correct / len(test_data) * 100


def compute_brier(test_data, centroids, weights):
    brier_sum = 0
    for fv, ci, oa in test_data:
        _, sims = score_dk(fv, ci, centroids, weights)
        probs = dk_probs(sims)
        for ai in range(A):
            brier_sum += (probs[ai] - (1 if ai == oa else 0)) ** 2
    return brier_sum / len(test_data)


def evaluate_per_category(test_data, centroids, weights):
    """Per-category accuracy."""
    cat_correct = {ci: 0 for ci in range(C)}
    cat_total = {ci: 0 for ci in range(C)}
    for fv, ci, oa in test_data:
        pred = score_dk(fv, ci, centroids, weights)[0]
        cat_total[ci] += 1
        if pred == oa:
            cat_correct[ci] += 1
    return {ci: (cat_correct[ci] / max(cat_total[ci], 1) * 100)
            for ci in range(C)}


def main():
    base_mu = get_base_centroids()

    # ══════════════════════════════════════════════════════
    # RATE-9: H-MONO + H-FLOOR
    # Does cumulative DK EVER drop below centroid?
    # Does mixing with centroid guarantee a safe floor?
    # ══════════════════════════════════════════════════════
    print("=" * 90)
    print("RATE-9: H-MONO (DK never below centroid?) + H-FLOOR (mixing safe?)")
    print("=" * 90)

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)

        scorer = make_scorer(base_mu.copy())
        all_decisions = []
        for n in range(1, N_MAX + 1):
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

        rng_test = np.random.default_rng(seed + 50000)
        test_data = []
        for _ in range(N_TEST):
            ci = int(rng_test.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_test.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng_test)
            test_data.append((fv, ci, oa))

        # Centroid baseline
        w_uniform = np.ones((C, A, D))
        cent_acc = evaluate_dk(test_data, frozen_mu, w_uniform)
        cent_brier = compute_brier(test_data, frozen_mu, w_uniform)

        print(f"\n  Seed {seed} (centroid baseline: {cent_acc:.1f}%, Brier={cent_brier:.4f}):")
        print(f"  {'N':>6s}  {'DK_cum':>7s}  {'>=cent?':>7s}  {'Brier':>8s}  "
              f"{'Mix.5':>6s}  {'Mix.7':>6s}  {'Mix1.0':>7s}  {'BestAlpha':>9s}")
        print(f"  {'-' * 65}")

        below_centroid_count = 0
        total_checkpoints = 0
        brier_prev = cent_brier
        brier_mono_count = 0

        for cp in range(DK_INTERVAL, N_MAX + 1, DK_INTERVAL):
            decs = all_decisions[:cp]
            w = estimate_dk(decs, frozen_mu, n_rounds=5)
            dk_acc = evaluate_dk(test_data, frozen_mu, w)
            dk_brier = compute_brier(test_data, frozen_mu, w)

            above = dk_acc >= cent_acc - 0.01
            if not above:
                below_centroid_count += 1
            total_checkpoints += 1

            if dk_brier <= brier_prev + 0.001:
                brier_mono_count += 1
            brier_prev = dk_brier

            # Test mixing at different alpha
            mix_5 = evaluate_mixed(test_data, frozen_mu, w, 0.5)
            mix_7 = evaluate_mixed(test_data, frozen_mu, w, 0.7)
            mix_10 = evaluate_mixed(test_data, frozen_mu, w, 1.0)

            # Find best alpha
            best_alpha = 0
            best_mix_acc = cent_acc
            for alpha in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
                mix_acc = evaluate_mixed(test_data, frozen_mu, w, alpha)
                if mix_acc > best_mix_acc:
                    best_mix_acc = mix_acc
                    best_alpha = alpha

            if cp % 1000 == 0 or not above:
                print(f"  {cp:>6d}  {dk_acc:>5.1f}%  {'YES' if above else 'NO':>7s}  "
                      f"{dk_brier:>8.4f}  {mix_5:>4.1f}%  {mix_7:>4.1f}%  "
                      f"{mix_10:>5.1f}%  {best_alpha:>7.1f}")

        print(f"\n  H-MONO: DK below centroid in {below_centroid_count}/{total_checkpoints} "
              f"checkpoints ({below_centroid_count/max(total_checkpoints,1)*100:.0f}%)")
        print(f"  H-BRIER monotonic: {brier_mono_count}/{total_checkpoints-1} "
              f"intervals ({brier_mono_count/max(total_checkpoints-1,1)*100:.0f}%)")
        print(f"  H-FLOOR: mixing at alpha=0.5 ALWAYS >= centroid? "
              f"(check Mix.5 column — all >= {cent_acc:.1f}%?)")

    # ══════════════════════════════════════════════════════
    # RATE-10: H-CATCOMP
    # Per-category DK improvement ∝ log(N_c)?
    # ══════════════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("RATE-10: H-CATCOMP (per-category improvement ∝ log(N_c)?)")
    print("=" * 90)

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)

        scorer = make_scorer(base_mu.copy())
        all_decisions = []
        cat_counts = {ci: 0 for ci in range(C)}

        for n in range(1, 4001):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            result = scorer.score(fv, ci)
            if n <= FREEZE_AT:
                scorer.update(fv, ci, result.action_index,
                              result.action_index == oa, oa)
            all_decisions.append((fv, ci, oa))
            cat_counts[ci] += 1

        frozen_mu = scorer.centroids.copy()

        rng_test = np.random.default_rng(seed + 50000)
        test_data = []
        for _ in range(N_TEST):
            ci = int(rng_test.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_test.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng_test)
            test_data.append((fv, ci, oa))

        # Centroid per-category accuracy
        cent_cat = evaluate_per_category(test_data, frozen_mu, np.ones((C, A, D)))

        # DK per-category accuracy
        w = estimate_dk(all_decisions, frozen_mu, n_rounds=5)
        dk_cat = evaluate_per_category(test_data, frozen_mu, w)

        print(f"\n  Seed {seed}:")
        print(f"  {'Category':>20s}  {'N_c':>5s}  {'log(N_c)':>8s}  "
              f"{'Cent':>6s}  {'DK':>6s}  {'Delta':>7s}")
        print(f"  {'-' * 60}")

        deltas = []
        log_ns = []
        for ci in range(C):
            nc = cat_counts[ci]
            log_nc = np.log(max(nc, 1))
            delta = dk_cat[ci] - cent_cat[ci]
            deltas.append(delta)
            log_ns.append(log_nc)
            print(f"  {CATEGORIES[ci]:>20s}  {nc:>5d}  {log_nc:>8.2f}  "
                  f"{cent_cat[ci]:>4.1f}%  {dk_cat[ci]:>4.1f}%  {delta:>+5.1f}pp")

        # Correlation between log(N_c) and delta
        if len(deltas) > 2:
            corr = np.corrcoef(log_ns, deltas)[0, 1]
            print(f"  Correlation(log(N_c), Delta): {corr:+.3f}")

    # ══════════════════════════════════════════════════════
    # RATE-11: H-DEPLOY — Full two-phase deployment
    # Phase A: learn means+variances simultaneously (N<500)
    # Phase B: freeze means, continue variances (N>500)
    # ══════════════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("RATE-11: H-DEPLOY (full two-phase deployment end-to-end)")
    print("=" * 90)

    strategies = {
        "ALL_FROZEN_500": "Learn means N<500, then freeze everything",
        "SPLIT_CUMUL": "Learn means N<500, then freeze means, learn DK from ALL data",
        "SIMULTANEOUS": "Learn means+DK N<500 simultaneously, then freeze means, continue DK",
        "DK_FROM_START": "DK from N=0 (no mean-only phase), freeze means at N=500",
    }

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng_base = np.random.default_rng(seed)

        rng_test = np.random.default_rng(seed + 50000)
        test_data = []
        for _ in range(N_TEST):
            ci = int(rng_test.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_test.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng_test)
            test_data.append((fv, ci, oa))

        print(f"\n  Seed {seed}:")
        print(f"  {'Strategy':>20s}  {'N=500':>6s}  {'N=1000':>6s}  {'N=2000':>6s}  "
              f"{'N=4000':>6s}  {'N=8000':>6s}")
        print(f"  {'-' * 55}")

        for strat_name, strat_desc in strategies.items():
            rng = np.random.default_rng(seed)
            scorer = make_scorer(base_mu.copy())
            all_decisions = []
            dk_weights = np.ones((C, A, D))

            checkpoints = {}

            for n in range(1, N_MAX + 1):
                ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                ta = true_action(gt, ci, fv)
                oa = noise_realistic(ta, ci, rng)
                result = scorer.score(fv, ci)
                correct = (result.action_index == oa)

                # Phase A: N <= 500
                if n <= FREEZE_AT:
                    scorer.update(fv, ci, result.action_index, correct, oa)
                    all_decisions.append((fv, ci, oa))

                    # SIMULTANEOUS and DK_FROM_START: also estimate DK during Phase A
                    if strat_name in ["SIMULTANEOUS", "DK_FROM_START"]:
                        if n % DK_INTERVAL == 0 and len(all_decisions) >= 100:
                            dk_weights = estimate_dk(all_decisions, scorer.centroids.copy(), n_rounds=3)

                else:
                    # Phase B: N > 500
                    all_decisions.append((fv, ci, oa))

                    if strat_name == "ALL_FROZEN_500":
                        pass  # frozen, use centroid
                    else:
                        # Re-estimate DK periodically
                        if n % DK_INTERVAL == 0:
                            frozen_mu = scorer.centroids.copy()
                            dk_weights = estimate_dk(all_decisions, frozen_mu, n_rounds=5)

                if n in [500, 1000, 2000, 4000, 8000]:
                    frozen_mu = scorer.centroids.copy()
                    if strat_name == "ALL_FROZEN_500":
                        acc = evaluate_dk(test_data, frozen_mu, np.ones((C, A, D)))
                    else:
                        acc = evaluate_dk(test_data, frozen_mu, dk_weights)
                    checkpoints[n] = acc

            print(f"  {strat_name:>20s}", end="")
            for n in [500, 1000, 2000, 4000, 8000]:
                if n in checkpoints:
                    print(f"  {checkpoints[n]:>4.1f}%", end="")
                else:
                    print(f"  {'—':>6s}", end="")
            print()

    # ══════════════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("H-MONO:    DK cumulative EVER below centroid? (want: NO or <5%)")
    print("H-FLOOR:   Mixing at alpha=0.5 always safe? (want: YES)")
    print("H-BRIER:   Brier more monotonic than accuracy? (want: YES)")
    print("H-CATCOMP: corr(log(N_c), Delta_c) > 0.3? (want: YES)")
    print("H-DEPLOY:  SPLIT_CUMUL or SIMULTANEOUS best at all checkpoints?")
    print("           DK_FROM_START helps or hurts Phase A?")

    print("\nDONE.")


if __name__ == "__main__":
    main()
