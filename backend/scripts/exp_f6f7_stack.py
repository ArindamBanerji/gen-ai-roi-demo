"""
EXP-F6+F7: V-STACK-DEPENDENCIES + V-NOISE-SENSITIVITY
========================================================
F6: Does DK provide a better base for RL?
F7: Does each term have different noise sensitivity?

Combined into one script for efficiency.

Run: cd backend && python scripts/exp_f6f7_stack.py
Time: ~20 min
"""

import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, FREQ_NOISE, ADJACENT
)

N_TRAIN = 1500
N_TEST = 500
A = 4


def score_dk(fv, ci, centroids, weights):
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        sims.append(-np.sum(weights[ci, ai] * diff ** 2))
    return int(np.argmax(sims))


def learn_dk_weights(X, y, c, centroids, n_iter=100):
    weights = np.ones((C, A, D))
    best_weights = weights.copy()
    best_acc = 0
    rng = np.random.default_rng(42)
    for _ in range(n_iter):
        trial = weights + rng.normal(0, 0.1, weights.shape)
        trial = np.clip(trial, 0.1, 10.0)
        correct = sum(1 for i in range(len(X))
                      if score_dk(X[i, :D], c[i], centroids, trial) == y[i])
        acc = correct / len(X)
        if acc > best_acc:
            best_acc = acc
            best_weights = trial.copy()
            weights = trial.copy()
    return best_weights


def noise_realistic_scaled(gt_a, ci, rng, noise_scale=1.0):
    """Oracle noise with adjustable scale."""
    rate = FREQ_NOISE.get(ci, 0.15) * noise_scale
    rate = min(rate, 0.95)
    if rng.random() < rate:
        nbrs = ADJACENT.get(gt_a, [])
        if nbrs:
            return int(rng.choice(nbrs))
        wrong = [a for a in range(A) if a != gt_a]
        return int(rng.choice(wrong))
    return gt_a


def run_stack(seed, noise_scale=1.0):
    """Run the full stack at a given noise level."""
    base_mu = get_base_centroids()
    gt = build_gt(np.random.default_rng(seed), base_mu)
    rng = np.random.default_rng(seed)

    X_all, y_all, c_all = [], [], []
    for n in range(1, N_TRAIN + N_TEST + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic_scaled(ta, ci, rng, noise_scale)
        features = np.concatenate([fv, np.eye(C)[ci]])
        X_all.append(features)
        y_all.append(oa)
        c_all.append(ci)

    X_all = np.array(X_all)
    y_all = np.array(y_all)
    c_all = np.array(c_all)
    X_train, X_test = X_all[:N_TRAIN], X_all[N_TRAIN:]
    y_train, y_test = y_all[:N_TRAIN], y_all[N_TRAIN:]
    c_train, c_test = c_all[:N_TRAIN], c_all[N_TRAIN:]

    # f₀: centroid
    scorer = make_scorer(base_mu.copy())
    preds_f0 = np.array([scorer.score(X_test[i, :D], c_test[i]).action_index
                          for i in range(N_TEST)])
    acc_f0 = accuracy_score(y_test, preds_f0) * 100

    # f₀ + δ₁: DK
    dk_weights = learn_dk_weights(X_train, y_train, c_train, base_mu)
    preds_dk = np.array([score_dk(X_test[i, :D], c_test[i], base_mu, dk_weights)
                          for i in range(N_TEST)])
    acc_dk = accuracy_score(y_test, preds_dk) * 100

    # f₀ + δ₂: RL on centroid residuals (skip DK)
    preds_f0_train = np.array([scorer.score(X_train[i, :D], c_train[i]).action_index
                                for i in range(N_TRAIN)])
    mlp_skip = MLPClassifier(hidden_layer_sizes=(32,), max_iter=1000, random_state=seed)
    feat_train_skip = np.column_stack([X_train, np.eye(A)[preds_f0_train]])
    feat_test_skip = np.column_stack([X_test, np.eye(A)[preds_f0]])
    mlp_skip.fit(feat_train_skip, y_train)
    preds_skip = mlp_skip.predict(feat_test_skip)
    acc_skip = accuracy_score(y_test, preds_skip) * 100

    # f₀ + δ₁ + δ₂: RL on DK residuals (full stack)
    dk_preds_train = np.array([score_dk(X_train[i, :D], c_train[i], base_mu, dk_weights)
                                for i in range(N_TRAIN)])
    mlp_full = MLPClassifier(hidden_layer_sizes=(32,), max_iter=1000, random_state=seed)
    feat_train_full = np.column_stack([X_train, np.eye(A)[dk_preds_train]])
    feat_test_full = np.column_stack([X_test, np.eye(A)[preds_dk]])
    mlp_full.fit(feat_train_full, y_train)
    preds_full = mlp_full.predict(feat_test_full)
    acc_full = accuracy_score(y_test, preds_full) * 100

    # Residual structure analysis
    # Are DK residuals more structured than centroid residuals?
    dk_errors = np.where(preds_dk != y_test)[0]
    f0_errors = np.where(preds_f0 != y_test)[0]

    return {
        'f0': acc_f0, 'dk': acc_dk,
        'skip': acc_skip,  # f₀+δ₂
        'full': acc_full,  # f₀+δ₁+δ₂
        'dk_errors': len(dk_errors),
        'f0_errors': len(f0_errors),
    }


def main():
    print("=" * 90)
    print("EXP-F6+F7: STACK DEPENDENCIES + NOISE SENSITIVITY")
    print("=" * 90)

    # ══ F6: Stack dependencies ══
    print(f"\n{'=' * 90}")
    print("F6: Does DK provide a better base for RL?")
    print(f"{'=' * 90}")
    print(f"  {'Seed':>6s}  {'f₀':>6s}  {'f₀+δ₁':>7s}  {'f₀+δ₂':>7s}  {'f₀+δ₁+δ₂':>9s}  "
          f"{'DK helps RL':>11s}")
    print(f"  {'-' * 55}")

    for seed in SEEDS[:3]:
        r = run_stack(seed, noise_scale=1.0)
        dk_helps = r['full'] > r['skip']
        gap_str = f"+{r['full']-r['skip']:.1f}pp" if dk_helps else "NO"
        print(f"  {seed:>6d}  {r['f0']:>4.1f}%  {r['dk']:>5.1f}%  {r['skip']:>5.1f}%  "
              f"{r['full']:>7.1f}%  {gap_str:>11s}")

    # ══ F7: Noise sensitivity ══
    print(f"\n{'=' * 90}")
    print("F7: Noise sensitivity by term")
    print(f"{'=' * 90}")
    noise_levels = [0.0, 0.25, 0.50, 1.00, 1.50, 2.00]

    print(f"  {'Noise':>6s}  {'f₀':>6s}  {'f₀+δ₁':>7s}  {'f₀+δ₁+δ₂':>9s}  "
          f"{'Δ(δ₁)':>7s}  {'Δ(δ₂)':>7s}  {'δ₂ more sensitive?':>18s}")
    print(f"  {'-' * 65}")

    baseline_results = {}
    for noise in noise_levels:
        results = {'f0': [], 'dk': [], 'full': []}
        for seed in SEEDS[:3]:
            r = run_stack(seed, noise_scale=noise)
            results['f0'].append(r['f0'])
            results['dk'].append(r['dk'])
            results['full'].append(r['full'])

        f0 = np.mean(results['f0'])
        dk = np.mean(results['dk'])
        full = np.mean(results['full'])

        delta_dk = dk - f0  # marginal gain from DK
        delta_rl = full - dk  # marginal gain from RL

        if noise == 0.0:
            baseline_results = {'f0': f0, 'dk': dk, 'full': full,
                                'delta_dk': delta_dk, 'delta_rl': delta_rl}

        # Compare marginal gains to baseline
        if baseline_results:
            dk_degradation = baseline_results['delta_dk'] - delta_dk
            rl_degradation = baseline_results['delta_rl'] - delta_rl
            more_sensitive = rl_degradation > dk_degradation
        else:
            more_sensitive = False

        print(f"  {noise:>6.2f}  {f0:>4.1f}%  {dk:>5.1f}%  {full:>7.1f}%  "
              f"{delta_dk:>+5.1f}pp  {delta_rl:>+5.1f}pp  "
              f"{'YES' if more_sensitive and noise > 0 else '':>18s}")

    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("F6-Q1: f₀+δ₁+δ₂ > f₀+δ₂? (DK helps RL)")
    print("F6-Q2: Are DK residuals more structured?")
    print("F7-Q1: Does δ₂ degrade more than δ₁ at high noise?")
    print("F7-Q2: At noise=0, does f₀+δ₁+δ₂ approach Bayes floor?")

    print("\nDONE.")


if __name__ == "__main__":
    main()
