"""
EXP-CENTROID: Four experiments characterizing T_0 (the centroid)
================================================================
These address the centroid characterization gap: T_0 is the foundation
that T_1\T_0 builds on, but we haven't quantified the foundation's
properties or its interaction with Phase 2.

1. FOUNDATION: How sensitive is DK improvement to centroid quality?
2. CONVERGENCE: Per-dimension convergence geometry of T_0
3. STABILITY: How many decisions flip when centroids are perturbed?
4. LIFTING: How much dimensionality does DK actually add?

Run: cd backend && python scripts/exp_centroid_char.py
Time: ~15-20 min (all use coord descent at 400/cat)
"""

import sys
import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_TEST = 500
FREEZE_AT = 500
SEEDS_SHORT = [42, 123, 777]


def score_dk(fv, ci, centroids, weights):
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        sims.append(-np.sum(weights[ci, ai] * diff ** 2))
    return int(np.argmax(sims))


def score_shrunk(fv, ci, centroids, dk_weights, alpha):
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        w_tilde = alpha * dk_weights[ci, ai] + (1 - alpha) * 1.0
        sims.append(-np.sum(w_tilde * diff ** 2))
    return int(np.argmax(sims))


def estimate_dk_coord(decisions, centroids, n_rounds=5, max_per_cat=400):
    by_cat = {ci: [] for ci in range(C)}
    for fv, ci_d, oa in decisions:
        by_cat[ci_d].append((fv, oa))
    weights = np.ones((C, A, D))
    for r in range(n_rounds):
        for ci in range(C):
            cat_decs = by_cat[ci]
            if len(cat_decs) < 10:
                continue
            if len(cat_decs) > max_per_cat:
                rng_sub = np.random.default_rng(42 + ci + r)
                idx = rng_sub.choice(len(cat_decs), max_per_cat, replace=False)
                cat_decs = [cat_decs[i] for i in idx]
            for ai in range(A):
                for di in range(D):
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


def eval_pure(test_data, centroids, weights):
    return sum(1 for fv, ci, oa in test_data
               if score_dk(fv, ci, centroids, weights) == oa) / len(test_data) * 100


def eval_shrunk(test_data, centroids, dk_w, alpha):
    return sum(1 for fv, ci, oa in test_data
               if score_shrunk(fv, ci, centroids, dk_w, alpha) == oa) / len(test_data) * 100


def make_test(gt, seed):
    rng = np.random.default_rng(seed + 50000)
    test = []
    for _ in range(N_TEST):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        test.append((fv, ci, oa))
    return test


def main():
    base_mu = get_base_centroids()

    # ════════════════════════════════════════════════════
    # 1. FOUNDATION: DK improvement vs centroid quality
    # ════════════════════════════════════════════════════
    print("=" * 80, flush=True)
    print("1. FOUNDATION: How sensitive is DK to centroid quality?", flush=True)
    print("=" * 80, flush=True)

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        test_data = make_test(gt, seed)

        # Collect decisions for DK estimation (always from same stream)
        rng = np.random.default_rng(seed)
        all_decs = []
        scorer_full = make_scorer(base_mu.copy())
        for n in range(1, 4001):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            r = scorer_full.score(fv, ci)
            scorer_full.update(fv, ci, r.action_index, r.action_index == oa, oa)
            all_decs.append((fv, ci, oa))

        # Five centroid qualities
        conditions = {}

        # (a) Perfect: μ = GT
        conditions["perfect"] = gt.copy()

        # (b) Good: after 500 decisions from calibrated prior (standard)
        scorer_good = make_scorer(base_mu.copy())
        rng_g = np.random.default_rng(seed)
        for n in range(1, 501):
            ci = int(rng_g.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_g.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng_g)
            r = scorer_good.score(fv, ci)
            scorer_good.update(fv, ci, r.action_index, r.action_index == oa, oa)
        conditions["good_N500"] = scorer_good.centroids.copy()

        # (c) Early: after 200 decisions (premature freeze)
        scorer_early = make_scorer(base_mu.copy())
        rng_e = np.random.default_rng(seed)
        for n in range(1, 201):
            ci = int(rng_e.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_e.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng_e)
            r = scorer_early.score(fv, ci)
            scorer_early.update(fv, ci, r.action_index, r.action_index == oa, oa)
        conditions["early_N200"] = scorer_early.centroids.copy()

        # (d) Expert only: no Phase 1 at all
        conditions["expert_prior"] = base_mu.copy()

        # (e) Random
        rng_r = np.random.default_rng(seed + 99999)
        conditions["random"] = np.clip(rng_r.uniform(0.2, 0.8, (C, A, D)), 0, 1)

        print(f"\n  Seed {seed}:", flush=True)
        print(f"  {'Condition':>15s}  {'||mu-mu*||':>8s}  {'Cent':>6s}  {'DK':>6s}  "
              f"{'Shr.5':>6s}  {'DK gain':>7s}  {'Shr gain':>8s}", flush=True)
        print(f"  {'-'*60}", flush=True)

        for name, mu in conditions.items():
            dist = np.sqrt(np.sum((mu - gt) ** 2))
            cent_acc = eval_pure(test_data, mu, np.ones((C, A, D)))

            print(f"  {name:>15s}  {dist:>7.3f}  {cent_acc:>4.1f}%  ", end="", flush=True)
            w = estimate_dk_coord(all_decs, mu)
            dk_acc = eval_pure(test_data, mu, w)
            shr_acc = eval_shrunk(test_data, mu, w, 0.5)

            print(f"{dk_acc:>4.1f}%  {shr_acc:>4.1f}%  "
                  f"{dk_acc - cent_acc:>+5.1f}pp  {shr_acc - cent_acc:>+6.1f}pp", flush=True)

    # ════════════════════════════════════════════════════
    # 2. CONVERGENCE: Per-dimension convergence of T₀
    # ════════════════════════════════════════════════════
    print(f"\n{'='*80}", flush=True)
    print("2. CONVERGENCE: Per-dimension centroid convergence", flush=True)
    print("=" * 80, flush=True)

    for seed in SEEDS_SHORT[:1]:  # 1 seed for detail
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)
        scorer = make_scorer(base_mu.copy())

        checkpoints = [50, 100, 200, 300, 500, 750, 1000, 1500, 2000]
        print(f"\n  Seed {seed}:", flush=True)
        print(f"  {'N':>6s}", end="", flush=True)
        for di in range(D):
            print(f"  {'d'+str(di):>6s}", end="")
        print(f"  {'total':>7s}  {'acc':>5s}", flush=True)
        print(f"  {'-'*60}", flush=True)

        for n in range(1, 2001):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            r = scorer.score(fv, ci)
            scorer.update(fv, ci, r.action_index, r.action_index == oa, oa)

            if n in checkpoints:
                mu_curr = scorer.centroids
                # Per-dimension distance to GT (averaged across all c,a pairs)
                per_dim_err = np.sqrt(np.mean((mu_curr - gt) ** 2, axis=(0, 1)))
                total_err = np.sqrt(np.sum((mu_curr - gt) ** 2))

                # Quick accuracy
                rng_t = np.random.default_rng(seed + 50000)
                correct = 0
                for _ in range(200):
                    ci_t = int(rng_t.choice(C, p=CATEGORY_WEIGHTS))
                    fv_t = np.clip(rng_t.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                    ta_t = true_action(gt, ci_t, fv_t)
                    oa_t = noise_realistic(ta_t, ci_t, rng_t)
                    if scorer.score(fv_t, ci_t).action_index == oa_t:
                        correct += 1
                acc = correct / 200 * 100

                print(f"  {n:>6d}", end="", flush=True)
                for di in range(D):
                    print(f"  {per_dim_err[di]:>5.3f}", end="")
                print(f"  {total_err:>6.3f}  {acc:>3.0f}%", flush=True)

    # ════════════════════════════════════════════════════
    # 3. STABILITY: Voronoi partition sensitivity
    # ════════════════════════════════════════════════════
    print(f"\n{'='*80}", flush=True)
    print("3. STABILITY: How many decisions flip when centroids are perturbed?", flush=True)
    print("=" * 80, flush=True)

    perturbations = [0.01, 0.02, 0.05, 0.10, 0.15, 0.20]

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        # Use converged centroids (N=500)
        rng = np.random.default_rng(seed)
        scorer = make_scorer(base_mu.copy())
        for n in range(1, 501):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            r = scorer.score(fv, ci)
            scorer.update(fv, ci, r.action_index, r.action_index == oa, oa)
        mu_conv = scorer.centroids.copy()

        # Score 500 test decisions at converged centroids
        test_data = make_test(gt, seed)
        base_actions = [score_dk(fv, ci, mu_conv, np.ones((C, A, D))) for fv, ci, oa in test_data]

        print(f"\n  Seed {seed}:", flush=True)
        print(f"  {'delta':>7s}  {'flipped':>7s}  {'flip%':>6s}  {'acc_base':>8s}  {'acc_pert':>8s}", flush=True)
        print(f"  {'-'*40}", flush=True)

        base_acc = sum(1 for i, (fv, ci, oa) in enumerate(test_data)
                       if base_actions[i] == oa) / N_TEST * 100

        for delta in perturbations:
            n_trials = 5
            total_flipped = 0
            total_acc = 0
            for trial in range(n_trials):
                rng_p = np.random.default_rng(seed * 100 + trial)
                noise = rng_p.normal(0, delta, mu_conv.shape)
                mu_pert = np.clip(mu_conv + noise, 0, 1)

                pert_actions = [score_dk(fv, ci, mu_pert, np.ones((C, A, D)))
                                for fv, ci, oa in test_data]
                flipped = sum(1 for i in range(N_TEST) if pert_actions[i] != base_actions[i])
                acc = sum(1 for i, (fv, ci, oa) in enumerate(test_data)
                          if pert_actions[i] == oa) / N_TEST * 100
                total_flipped += flipped
                total_acc += acc

            avg_flip = total_flipped / n_trials
            avg_acc = total_acc / n_trials
            print(f"  {delta:>7.2f}  {avg_flip:>5.0f}  {avg_flip/N_TEST*100:>4.1f}%  "
                  f"{base_acc:>6.1f}%  {avg_acc:>6.1f}%", flush=True)

    # ════════════════════════════════════════════════════
    # 4. LIFTING: How much dimensionality does DK add?
    # ════════════════════════════════════════════════════
    print(f"\n{'='*80}", flush=True)
    print("4. LIFTING: Effective dimensionality at Order 0 vs Order 1", flush=True)
    print("=" * 80, flush=True)

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)
        scorer = make_scorer(base_mu.copy())
        decs = []
        for n in range(1, 4001):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            r = scorer.score(fv, ci)
            if n <= FREEZE_AT:
                scorer.update(fv, ci, r.action_index, r.action_index == oa, oa)
            decs.append((fv, ci, oa))
        fm = scorer.centroids.copy()

        print(f"  cal DK seed={seed}...", end="", flush=True)
        w_dk = estimate_dk_coord(decs, fm)

        # Centroid effective dimensionality (per category)
        print(f"\r\n  Seed {seed}:", flush=True)
        print(f"  {'Category':>20s}  {'Cent eff_dim':>12s}  {'DK eff_dim':>10s}  "
              f"{'Lift':>6s}  {'w range':>10s}", flush=True)
        print(f"  {'-'*65}", flush=True)

        for ci in range(C):
            # Centroid eff_dim: based on variance of centroid positions across actions
            mu_cat = fm[ci]  # shape (A, D)
            mu_var = np.var(mu_cat, axis=0)  # variance of mean across actions, per dim
            if mu_var.sum() > 0:
                mu_var_norm = mu_var / mu_var.sum()
                cent_eff_dim = np.exp(-np.sum(mu_var_norm * np.log(mu_var_norm + 1e-10)))
            else:
                cent_eff_dim = 1.0

            # DK eff_dim: based on weight variance across actions per dim
            w_cat = w_dk[ci]  # shape (A, D)
            # Effective boundary dimensionality: dimensions where weights DIFFER across actions
            w_range = np.max(w_cat, axis=0) - np.min(w_cat, axis=0)  # per dim
            w_range_norm = w_range / (w_range.sum() + 1e-10)
            dk_eff_dim = np.exp(-np.sum(w_range_norm * np.log(w_range_norm + 1e-10)))

            w_min = w_cat.min()
            w_max = w_cat.max()

            print(f"  {CATEGORIES[ci]:>20s}  {cent_eff_dim:>10.2f}  {dk_eff_dim:>10.2f}  "
                  f"{dk_eff_dim - cent_eff_dim:>+5.2f}  [{w_min:.1f}-{w_max:.1f}]", flush=True)

    print(f"\n{'='*80}", flush=True)
    print("BINARY QUESTIONS", flush=True)
    print("FOUNDATION:", flush=True)
    print("  Q1: Does DK gain decrease as centroid quality worsens?", flush=True)
    print("  Q2: Can DK compensate for poor centroids (gain>0 at 'random')?", flush=True)
    print("  Q3: Is expert_prior sufficient for DK (no Phase 1 needed)?", flush=True)
    print("CONVERGENCE:", flush=True)
    print("  Q4: Do all dimensions converge at similar rate?", flush=True)
    print("  Q5: Which dimension converges first/last?", flush=True)
    print("STABILITY:", flush=True)
    print("  Q6: At delta=0.02, what % of decisions flip?", flush=True)
    print("  Q7: Is the partition sensitive (>5% flip at delta=0.05)?", flush=True)
    print("LIFTING:", flush=True)
    print("  Q8: Does DK increase eff_dim for any category?", flush=True)
    print("  Q9: Which category gets the most dimensionality lift?", flush=True)
    print("\nDONE.", flush=True)


if __name__ == "__main__":
    main()
