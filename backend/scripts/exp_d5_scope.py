"""
EXP-D5: SCOPE COMPARISON
===========================
Global vs per-category vs per-(c,a) vs clustered controller scope.

Run: cd backend && python scripts/exp_d5_scope.py
Time: ~15 min
"""

import numpy as np
from collections import deque
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N = 2000
CHECKPOINTS = [200, 500, 1000, 2000]
WRONG_CAT = 4
WRONG_SHIFT = 0.3


def make_wrong_prior(base_mu, seed):
    prior = base_mu.copy()
    rng = np.random.default_rng(seed + 5000)
    direction = rng.normal(0, 1, (A, D))
    direction = direction / np.linalg.norm(direction) * WRONG_SHIFT
    prior[WRONG_CAT] += direction
    return np.clip(prior, 0, 1)


def run_scoped(seed, scope, gt, start_mu):
    rng = np.random.default_rng(seed)
    scorer = make_scorer(start_mu.copy())
    ca_counts = np.zeros((C, A))
    override_windows = {ci: deque(maxlen=50) for ci in range(C)}

    # Per-scope parameters
    if scope == "global":
        # One theta, one eta for all
        theta = 0.60
        eta_base = 0.05
    elif scope == "per_category":
        # Per-category theta and eta (initialized same, will diverge via override rate)
        theta_per_cat = np.full(C, 0.60)
        eta_per_cat = np.full(C, 0.05)
    elif scope == "per_ca":
        # Per (c,a) pair
        theta_per_ca = np.full((C, A), 0.60)
        eta_per_ca = np.full((C, A), 0.05)
    elif scope == "clustered":
        # 3 clusters: high volume (0), medium (1,2), rare (3,4,5)
        cluster_map = {0: 'high', 1: 'mid', 2: 'mid', 3: 'rare', 4: 'rare', 5: 'rare'}
        cluster_theta = {'high': 0.70, 'mid': 0.60, 'rare': 0.40}
        cluster_eta = {'high': 0.03, 'mid': 0.05, 'rare': 0.08}

    lc = 0
    wc_correct, wc_total = 0, 0
    other_correct, other_total = 0, 0
    cp = {}

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc += 1
        override_windows[ci].append(0 if correct else 1)

        if ci == WRONG_CAT:
            wc_total += 1
            if correct: wc_correct += 1
        else:
            other_total += 1
            if correct: other_correct += 1

        # Determine theta and eta based on scope
        if scope == "global":
            theta_eff = theta
            eta_eff = eta_base
        elif scope == "per_category":
            theta_eff = theta_per_cat[ci]
            eta_eff = eta_per_cat[ci]
            # Adapt per-category: lower theta (more updates) for high-override categories
            if n % 100 == 0:
                for cci in range(C):
                    or_val = np.mean(override_windows[cci]) if len(override_windows[cci]) > 10 else 0.2
                    theta_per_cat[cci] = np.clip(0.80 - or_val * 2.0, 0.30, 0.90)
                    eta_per_cat[cci] = np.clip(0.02 + or_val * 0.15, 0.01, 0.10)
        elif scope == "per_ca":
            theta_eff = theta_per_ca[ci, oa]
            eta_eff = eta_per_ca[ci, oa]
            # Adapt per (c,a)
            if n % 200 == 0:
                for cci in range(C):
                    or_val = np.mean(override_windows[cci]) if len(override_windows[cci]) > 10 else 0.2
                    for aai in range(A):
                        theta_per_ca[cci, aai] = np.clip(0.80 - or_val * 2.0, 0.30, 0.90)
                        eta_per_ca[cci, aai] = np.clip(0.02 + or_val * 0.15, 0.01, 0.10)
        elif scope == "clustered":
            cluster = cluster_map[ci]
            theta_eff = cluster_theta[cluster]
            eta_eff = cluster_eta[cluster]

        # Gate
        if result.confidence > theta_eff:
            if n in CHECKPOINTS:
                wc_acc = wc_correct / wc_total * 100 if wc_total > 0 else 0
                oc_acc = other_correct / other_total * 100 if other_total > 0 else 0
                cp[n] = {'acc': lc/n*100, 'wc_acc': wc_acc, 'other_acc': oc_acc}
            continue

        # Update with scope-specific eta
        n_ca = ca_counts[ci, oa]
        decay = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
        scale = (eta_eff / 0.05) * decay
        mu_ca = scorer.centroids[ci, oa]
        eff_fv = mu_ca + max(scale, 0.005) * (fv - mu_ca)
        scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
        ca_counts[ci, oa] += 1

        if n in CHECKPOINTS:
            wc_acc = wc_correct / wc_total * 100 if wc_total > 0 else 0
            oc_acc = other_correct / other_total * 100 if other_total > 0 else 0
            cp[n] = {'acc': lc/n*100, 'wc_acc': wc_acc, 'other_acc': oc_acc}

    return cp


def main():
    print("=" * 80)
    print("EXP-D5: SCOPE COMPARISON")
    print("=" * 80)

    base_mu = get_base_centroids()
    scopes = ["global", "per_category", "per_ca", "clustered"]

    # With wrong category
    print(f"\n  WITH WRONG CATEGORY (insider_threat shifted {WRONG_SHIFT}):")
    print(f"  {'Scope':>15s}  {'Overall@2000':>12s}  {'WrongCat':>8s}  {'Other':>6s}")
    print(f"  {'-' * 45}")

    for scope in scopes:
        runs = []
        for seed in SEEDS:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            wrong_mu = make_wrong_prior(base_mu, seed)
            r = run_scoped(seed, scope, gt, wrong_mu)
            runs.append(r)

        acc = np.mean([r[N]['acc'] for r in runs if N in r])
        wc = np.mean([r[N]['wc_acc'] for r in runs if N in r])
        oc = np.mean([r[N]['other_acc'] for r in runs if N in r])
        print(f"  {scope:>15s}  {acc:>10.1f}%  {wc:>6.1f}%  {oc:>5.1f}%")

    # Calibrated prior (no wrong category)
    print(f"\n  CALIBRATED PRIOR (no wrong category):")
    print(f"  {'Scope':>15s}  {'Overall@2000':>12s}")
    print(f"  {'-' * 30}")

    for scope in scopes:
        runs = []
        for seed in SEEDS:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_scoped(seed, scope, gt, base_mu)
            runs.append(r)
        acc = np.mean([r[N]['acc'] for r in runs if N in r])
        print(f"  {scope:>15s}  {acc:>10.1f}%")

    # Per-category breakdown for clustered scope
    print(f"\n  CLUSTERED SCOPE -- per-category accuracy (wrong cat setup):")
    runs = []
    for seed in SEEDS:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        wrong_mu = make_wrong_prior(base_mu, seed)
        r = run_scoped(seed, "clustered", gt, wrong_mu)
        runs.append(r)

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    # Recompute for binary questions
    scope_results = {}
    for scope in scopes:
        runs = []
        for seed in SEEDS:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            wrong_mu = make_wrong_prior(base_mu, seed)
            r = run_scoped(seed, scope, gt, wrong_mu)
            runs.append(r)
        scope_results[scope] = {
            'acc': np.mean([r[N]['acc'] for r in runs if N in r]),
            'wc': np.mean([r[N]['wc_acc'] for r in runs if N in r]),
            'oc': np.mean([r[N]['other_acc'] for r in runs if N in r]),
        }

    global_wc = scope_results['global']['wc']
    percat_wc = scope_results['per_category']['wc']
    perca_wc = scope_results['per_ca']['wc']
    clustered_wc = scope_results['clustered']['wc']

    print(f"Q1: Per-category improves wrong cat? global={global_wc:.1f}% "
          f"per_cat={percat_wc:.1f}% gap={percat_wc-global_wc:+.1f}pp")
    print(f"Q2: Per-(c,a) improves further? per_ca={perca_wc:.1f}% "
          f"gap_vs_global={perca_wc-global_wc:+.1f}pp")
    print(f"Q3: Clustered sufficient? clustered={clustered_wc:.1f}% "
          f"vs per_cat={percat_wc:.1f}% gap={clustered_wc-percat_wc:+.1f}pp")

    # Does per-category hurt other categories?
    global_oc = scope_results['global']['oc']
    percat_oc = scope_results['per_category']['oc']
    print(f"Q4: Per-category hurts others? global_other={global_oc:.1f}% "
          f"percat_other={percat_oc:.1f}% {'YES' if percat_oc < global_oc - 1 else 'NO'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
