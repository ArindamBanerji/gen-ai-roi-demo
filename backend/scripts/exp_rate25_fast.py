"""
EXP-RATE-25-FAST: OVERLAP FUNCTION h(sigma) (optimized)
=========================================================
RATE-5: DK gain vs MLP gain at each sigma level.
RATE-2: Factor precision trajectory with DK.

Run: cd backend && python scripts/exp_rate25_fast.py
Time: ~15 min
"""

import sys
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
FREEZE_AT = 500
SEEDS_SHORT = [42, 123, 777]


def score_dk(fv, ci, centroids, weights):
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        sims.append(-np.sum(weights[ci, ai] * diff ** 2))
    return int(np.argmax(sims))


def estimate_dk_fast(decisions, centroids, n_rounds=5, max_per_cat=400):
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


def main():
    base_mu = get_base_centroids()

    # ════════════════════════════════════════
    # RATE-5: h(sigma) at 8 levels
    # ════════════════════════════════════════
    print("=" * 80, flush=True)
    print("RATE-5: OVERLAP FUNCTION h(sigma)", flush=True)
    print("=" * 80, flush=True)

    sigmas = [0.02, 0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20]

    print(f"{'sigma':>6s}  {'Cent':>6s}  {'DK':>6s}  {'MLP_b':>6s}  "
          f"{'DK_g':>6s}  {'MLP_g':>6s}  {'Regime':>12s}", flush=True)
    print("-" * 55, flush=True)

    for sigma in sigmas:
        print(f"  sigma={sigma:.2f}...", end="", flush=True)
        cent_accs, dk_accs, mlp_accs = [], [], []

        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            rng = np.random.default_rng(seed)
            scorer = make_scorer(base_mu.copy())
            decs = []

            for n in range(1, N_TRAIN + 1):
                ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng.normal(0.5, sigma, D), 0, 1).astype(np.float64)
                ta = true_action(gt, ci, fv)
                oa = noise_realistic(ta, ci, rng)
                r = scorer.score(fv, ci)
                if n <= FREEZE_AT:
                    scorer.update(fv, ci, r.action_index, r.action_index == oa, oa)
                decs.append((fv, ci, oa))
            fm = scorer.centroids.copy()

            rng_t = np.random.default_rng(seed + 50000)
            test = []
            for _ in range(N_TEST):
                ci = int(rng_t.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng_t.normal(0.5, sigma, D), 0, 1).astype(np.float64)
                ta = true_action(gt, ci, fv)
                oa = noise_realistic(ta, ci, rng_t)
                test.append((fv, ci, oa))

            # Centroid
            cent_acc = sum(1 for fv, ci, oa in test
                          if scorer.score(fv, ci).action_index == oa) / N_TEST * 100

            # DK
            dk_w = estimate_dk_fast(decs, fm, n_rounds=5, max_per_cat=400)
            dk_acc = sum(1 for fv, ci, oa in test
                         if score_dk(fv, ci, fm, dk_w) == oa) / N_TEST * 100

            # Bounded MLP
            X_tr = np.array([np.concatenate([fv, np.eye(C)[ci]]) for fv, ci, oa in decs])
            y_tr = np.array([oa for fv, ci, oa in decs])
            cp_tr = np.array([scorer.score(fv, ci).action_index for fv, ci, oa in decs])
            ft_tr = np.column_stack([X_tr, np.eye(A)[cp_tr]])

            X_te = np.array([np.concatenate([fv, np.eye(C)[ci]]) for fv, ci, oa in test])
            y_te = np.array([oa for fv, ci, oa in test])
            cp_te = np.array([scorer.score(fv, ci).action_index for fv, ci, oa in test])
            ft_te = np.column_stack([X_te, np.eye(A)[cp_te]])

            gaps = []
            for fv, ci, oa in test:
                r = scorer.score(fv, ci)
                p = np.array(r.probabilities)
                sp = np.sort(p)[::-1]
                gaps.append(sp[0] - sp[1])
            gaps = np.array(gaps)

            mlp = MLPClassifier(hidden_layer_sizes=(32,), max_iter=1000, random_state=seed)
            mlp.fit(ft_tr, y_tr)
            mp = mlp.predict(ft_te)
            bounded = cp_te.copy()
            for i in range(N_TEST):
                if mp[i] != cp_te[i] and gaps[i] <= 0.30:
                    bounded[i] = mp[i]
            mlp_acc = accuracy_score(y_te, bounded) * 100

            cent_accs.append(cent_acc)
            dk_accs.append(dk_acc)
            mlp_accs.append(mlp_acc)

        mc, md, mm = np.mean(cent_accs), np.mean(dk_accs), np.mean(mlp_accs)
        dk_g, mlp_g = md - mc, mm - mc
        regime = "DK wins" if dk_g > mlp_g + 0.5 else ("MLP wins" if mlp_g > dk_g + 0.5 else "similar")
        print(f"\r{sigma:>6.2f}  {mc:>4.1f}%  {md:>4.1f}%  {mm:>4.1f}%  "
              f"{dk_g:>+4.1f}pp  {mlp_g:>+4.1f}pp  {regime:>12s}", flush=True)

    # ════════════════════════════════════════
    # RATE-2: FACTOR PRECISION TRAJECTORY
    # ════════════════════════════════════════
    print(f"\n{'='*80}", flush=True)
    print("RATE-2: FACTOR PRECISION TRAJECTORY", flush=True)
    print("sigma improves over time: sigma_eff = 0.15 * (500/(500+N))^gamma", flush=True)
    print("=" * 80, flush=True)

    gammas = [0.1, 0.2, 0.3, 0.5]
    traj_cps = [500, 1000, 2000, 4000]

    for gamma in gammas:
        print(f"\nGamma={gamma}:", flush=True)
        print(f"{'N':>6s}  {'sigma':>6s}  {'Cent':>6s}  {'DK':>6s}  {'DK-C':>6s}", flush=True)

        for seed in SEEDS_SHORT[:1]:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            rng = np.random.default_rng(seed)
            scorer = make_scorer(base_mu.copy())
            decs = []

            for n in range(1, 4001):
                sig_eff = 0.15 * (500 / (500 + n)) ** gamma
                ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng.normal(0.5, sig_eff, D), 0, 1).astype(np.float64)
                ta = true_action(gt, ci, fv)
                oa = noise_realistic(ta, ci, rng)
                r = scorer.score(fv, ci)
                if n <= FREEZE_AT:
                    scorer.update(fv, ci, r.action_index, r.action_index == oa, oa)
                decs.append((fv, ci, oa))
            fm = scorer.centroids.copy()

            for cp in traj_cps:
                sig_at = 0.15 * (500 / (500 + cp)) ** gamma
                rng_t = np.random.default_rng(seed + 50000)
                test = []
                for _ in range(N_TEST):
                    ci = int(rng_t.choice(C, p=CATEGORY_WEIGHTS))
                    fv = np.clip(rng_t.normal(0.5, sig_at, D), 0, 1).astype(np.float64)
                    ta = true_action(gt, ci, fv)
                    oa = noise_realistic(ta, ci, rng_t)
                    test.append((fv, ci, oa))

                print(f"  cal N={cp}...", end="", flush=True)
                dk_w = estimate_dk_fast(decs[:cp], fm, n_rounds=5, max_per_cat=400)
                dk_acc = sum(1 for fv, ci, oa in test
                             if score_dk(fv, ci, fm, dk_w) == oa) / N_TEST * 100
                c_acc = sum(1 for fv, ci, oa in test
                            if make_scorer(fm).score(fv, ci).action_index == oa) / N_TEST * 100
                print(f"\r{cp:>6d}  {sig_at:>5.3f}  {c_acc:>4.1f}%  {dk_acc:>4.1f}%  "
                      f"{dk_acc-c_acc:>+4.1f}pp", flush=True)

    print(f"\n{'='*80}", flush=True)
    print("BINARY QUESTIONS", flush=True)
    print("RATE-5: h(sigma) smoothly decreasing?", flush=True)
    print("RATE-5: At what sigma does DK gain reach 0?", flush=True)
    print("RATE-2: Does improving sigma + DK beat either alone?", flush=True)
    print("\nDONE.", flush=True)


if __name__ == "__main__":
    main()
