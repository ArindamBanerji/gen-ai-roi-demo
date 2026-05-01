"""
EXP-H2: BOUNDARY-TARGETED CONTROLLER
=======================================
HE2: Is investigate-monitor the sole useful control target?
HE3: Does boundary targeting improve the coin-flip rate?

Tests: controller that ONLY adjusts the inv-mon boundary,
with per-update fix/create measurement.

Run: cd backend && python scripts/exp_h2_boundary.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_RUN = 2000
SEEDS_SHORT = [42, 123, 777]
# investigate=1, monitor=3 in ACTIONS
INV_IDX = 1
MON_IDX = 3


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


def run_boundary_test(seed, strategy, gt, start_mu):
    rng = np.random.default_rng(seed)
    scorer = make_scorer(start_mu.copy())
    ca_counts = np.zeros((C, A))

    # Fixed test set for per-update measurement
    rng_test = np.random.default_rng(seed + 80000)
    test_queries = []
    for _ in range(500):
        ci = int(rng_test.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng_test.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        test_queries.append((ci, fv, ta))

    def count_errors():
        return sum(1 for ci, fv, ta in test_queries
                   if scorer.score(fv, ci).action_index != ta)

    lc = 0
    all_confs, all_corrects = [], []
    net_fixed, net_created, updates_done = 0, 0, 0

    for n in range(1, N_RUN + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc += 1
        all_confs.append(result.confidence)
        all_corrects.append(1.0 if correct else 0.0)

        should_update = False
        ai = oa

        if strategy == "ALL_ACTIONS":
            # Standard sqrt decay on all actions
            should_update = True

        elif strategy == "INV_MON_ONLY":
            # Only update if the oracle action is investigate or monitor
            should_update = (ai == INV_IDX or ai == MON_IDX)

        elif strategy == "BOUNDARY_MARGIN":
            # Only update if query is near the inv-mon boundary
            d_inv = np.linalg.norm(fv - scorer.centroids[ci, INV_IDX])
            d_mon = np.linalg.norm(fv - scorer.centroids[ci, MON_IDX])
            margin = abs(d_inv - d_mon) / 2
            should_update = margin < 0.05

        elif strategy == "BOUNDARY_ALL":
            # Update near ANY boundary, not just inv-mon
            dists = [np.linalg.norm(fv - scorer.centroids[ci, a]) for a in range(A)]
            sd = np.sort(dists)
            margin = (sd[1] - sd[0]) / 2
            should_update = margin < 0.05

        elif strategy == "GATED":
            should_update = result.confidence <= 0.60

        elif strategy == "STATIC":
            should_update = False

        if should_update:
            errors_before = count_errors() if updates_done < 200 else -1

            n_ca = ca_counts[ci, ai]
            scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
            mu_ca = scorer.centroids[ci, ai]
            eff_fv = mu_ca + max(scale, 0.005) * (fv - mu_ca)
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
            ca_counts[ci, ai] += 1
            updates_done += 1

            if errors_before >= 0:
                errors_after = count_errors()
                delta = errors_after - errors_before
                if delta < 0:
                    net_fixed += abs(delta)
                elif delta > 0:
                    net_created += delta

    confs = np.array(all_confs)
    corrs = np.array(all_corrects)
    fix_rate = net_fixed / max(min(updates_done, 200), 1)
    create_rate = net_created / max(min(updates_done, 200), 1)

    return {
        'acc': lc / N_RUN * 100,
        'ece': compute_ece(confs, corrs),
        'updates': updates_done,
        'fix_rate': fix_rate,
        'create_rate': create_rate,
        'net_rate': fix_rate - create_rate,
    }


def main():
    print("=" * 80)
    print("EXP-H2: BOUNDARY-TARGETED CONTROLLER")
    print("=" * 80)

    base_mu = get_base_centroids()
    strategies = ["STATIC", "ALL_ACTIONS", "INV_MON_ONLY",
                  "BOUNDARY_MARGIN", "BOUNDARY_ALL", "GATED"]

    # CALIBRATED PRIOR
    print(f"\n  CALIBRATED PRIOR:")
    print(f"  {'Strategy':>18s}  {'Acc':>6s}  {'ECE':>8s}  {'Updates':>7s}  "
          f"{'Fix/upd':>7s}  {'Cre/upd':>7s}  {'Net/upd':>7s}")
    print(f"  {'-' * 70}")

    for strat in strategies:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_boundary_test(seed, strat, gt, base_mu)
            runs.append(r)
        acc = np.mean([r['acc'] for r in runs])
        ece = np.mean([r['ece'] for r in runs])
        upd = np.mean([r['updates'] for r in runs])
        fix = np.mean([r['fix_rate'] for r in runs])
        cre = np.mean([r['create_rate'] for r in runs])
        net = np.mean([r['net_rate'] for r in runs])
        print(f"  {strat:>18s}  {acc:5.1f}%  {ece:8.4f}  {upd:>5.0f}  "
              f"{fix:>7.3f}  {cre:>7.3f}  {net:>+7.3f}")

    # SEPARATION SWEEP
    print(f"\n  SEPARATION SWEEP:")
    print(f"  {'Sep':>6s}  {'Static':>7s}  {'AllAct':>7s}  {'InvMon':>7s}  {'BdryMar':>7s}  {'Gated':>7s}")
    print(f"  {'-' * 45}")

    for sep in [0.50, 0.75, 1.00, 1.50]:
        results = {}
        for strat in ["STATIC", "ALL_ACTIONS", "INV_MON_ONLY", "BOUNDARY_MARGIN", "GATED"]:
            accs = []
            for seed in SEEDS_SHORT:
                gt = build_gt(np.random.default_rng(seed), base_mu)
                rng_s = np.random.default_rng(seed + 3000)
                direction = rng_s.normal(0, 1, gt.shape)
                direction = direction / np.linalg.norm(direction) * sep
                prior = np.clip(gt + direction, 0, 1)
                r = run_boundary_test(seed, strat, gt, prior)
                accs.append(r['acc'])
            results[strat] = np.mean(accs)
        print(f"  {sep:>6.2f}  {results['STATIC']:>5.1f}%  {results['ALL_ACTIONS']:>5.1f}%  "
              f"{results['INV_MON_ONLY']:>5.1f}%  {results['BOUNDARY_MARGIN']:>5.1f}%  "
              f"{results['GATED']:>5.1f}%")

    print("\nDONE.")


if __name__ == "__main__":
    main()
