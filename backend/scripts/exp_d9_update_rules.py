"""
EXP-D9: ALTERNATIVE UPDATE RULES
===================================
All candidates use mu += scale*(fv - mu). What if the update
rule itself is the limitation?

Tests: momentum, direction-only, robust median, exponential MA.

Run: cd backend && python scripts/exp_d9_update_rules.py
Time: ~20 min
"""

import numpy as np
from collections import deque
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N = 5000
SEEDS_SHORT = [42, 123, 777]


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


def run_update_rule(seed, rule_name, gt, base_mu):
    rng = np.random.default_rng(seed)
    scorer = make_scorer(base_mu.copy())
    ca_counts = np.zeros((C, A))

    # Rule-specific state
    momentum = np.zeros_like(scorer.centroids)  # for momentum rule
    ema_centroids = scorer.centroids.copy()  # for EMA rule
    recent_fvs = {(ci, ai): deque(maxlen=10) for ci in range(C) for ai in range(A)}

    lc = 0
    all_confs, all_corrects = [], []
    checkpoints = {}

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc += 1
        all_confs.append(result.confidence)
        all_corrects.append(1.0 if correct else 0.0)

        ai = oa
        n_ca = ca_counts[ci, ai]
        mu_ca = scorer.centroids[ci, ai].copy()
        delta = fv - mu_ca

        if rule_name == "standard":
            # mu += eta * (fv - mu) with sqrt decay
            scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
            eff_fv = mu_ca + max(scale, 0.005) * delta
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)

        elif rule_name == "momentum":
            # mu += eta * delta + beta * momentum
            beta = 0.7
            scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
            momentum[ci, ai] = beta * momentum[ci, ai] + (1 - beta) * delta
            update = max(scale, 0.005) * momentum[ci, ai]
            eff_fv = mu_ca + update
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)

        elif rule_name == "direction_only":
            # Normalize direction, fixed step size
            step_size = 0.005  # fixed small step
            if np.linalg.norm(delta) > 1e-8:
                direction = delta / np.linalg.norm(delta)
                eff_fv = mu_ca + step_size * direction
            else:
                eff_fv = fv
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)

        elif rule_name == "median_batch":
            # Accumulate, update with median every 5 samples
            recent_fvs[(ci, ai)].append(fv.copy())
            if len(recent_fvs[(ci, ai)]) >= 5:
                batch = np.array(list(recent_fvs[(ci, ai)]))
                median_fv = np.median(batch, axis=0)
                scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
                eff_fv = mu_ca + max(scale, 0.005) * (median_fv - mu_ca)
                scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
                recent_fvs[(ci, ai)].clear()

        elif rule_name == "ema":
            # Exponential moving average of observations
            alpha = 0.02
            ema_centroids[ci, ai] = (1 - alpha) * ema_centroids[ci, ai] + alpha * fv
            # Use EMA as the update target
            scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
            eff_fv = mu_ca + max(scale, 0.005) * (ema_centroids[ci, ai] - mu_ca)
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)

        elif rule_name == "per_dim":
            # Different learning rate per dimension based on variance
            recent_fvs[(ci, ai)].append(fv.copy())
            if len(recent_fvs[(ci, ai)]) >= 3:
                batch = np.array(list(recent_fvs[(ci, ai)]))
                dim_var = np.var(batch, axis=0) + 1e-8
                # Lower eta for high-variance dimensions (noisy signal)
                dim_scale = 1.0 / (1.0 + dim_var * 100)
                scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
                eff_fv = mu_ca + max(scale, 0.005) * dim_scale * delta
            else:
                scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
                eff_fv = mu_ca + max(scale, 0.005) * delta
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)

        elif rule_name == "gated_standard":
            # Standard with confidence gate (the pipeline's gate only)
            if result.confidence <= 0.60:
                scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
                eff_fv = mu_ca + max(scale, 0.005) * delta
                scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)

        ca_counts[ci, ai] += 1

        if n in [200, 500, 1000, 2000, 5000]:
            confs = np.array(all_confs)
            corrs = np.array(all_corrects)
            checkpoints[n] = {
                'acc': lc / n * 100,
                'ece': compute_ece(confs, corrs),
            }

    return checkpoints


def main():
    print("=" * 80)
    print("EXP-D9: ALTERNATIVE UPDATE RULES")
    print("=" * 80)

    base_mu = get_base_centroids()
    rules = ["standard", "momentum", "direction_only", "median_batch",
             "ema", "per_dim", "gated_standard"]

    # Calibrated prior
    print(f"\n  CALIBRATED PRIOR:")
    print(f"  {'Rule':>16s}  {'Acc@2000':>8s}  {'ECE@2000':>8s}  {'Acc@5000':>8s}  {'ECE@5000':>8s}  {'Drift':>7s}")
    print(f"  {'-' * 65}")

    for rule in rules:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_update_rule(seed, rule, gt, base_mu)
            runs.append(r)
        acc_2k = np.mean([r[2000]['acc'] for r in runs])
        ece_2k = np.mean([r[2000]['ece'] for r in runs])
        acc_5k = np.mean([r[5000]['acc'] for r in runs])
        ece_5k = np.mean([r[5000]['ece'] for r in runs])
        drift = acc_5k - acc_2k
        print(f"  {rule:>16s}  {acc_2k:>6.1f}%  {ece_2k:>8.4f}  "
              f"{acc_5k:>6.1f}%  {ece_5k:>8.4f}  {drift:>+5.1f}pp")

    # Generic prior (cold start)
    print(f"\n  GENERIC PRIOR:")
    print(f"  {'Rule':>16s}  {'Acc@200':>7s}  {'Acc@2000':>8s}")
    print(f"  {'-' * 35}")

    generic = np.full((C, A, D), 0.5)
    for rule in rules:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_update_rule(seed, rule, gt, generic)
            runs.append(r)
        acc_200 = np.mean([r[200]['acc'] for r in runs])
        acc_2000 = np.mean([r[2000]['acc'] for r in runs])
        print(f"  {rule:>16s}  {acc_200:>5.1f}%  {acc_2000:>6.1f}%")

    print("\nDONE.")


if __name__ == "__main__":
    main()
