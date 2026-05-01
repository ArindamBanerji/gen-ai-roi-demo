"""
EXP-H4: OPPORTUNITY-WEIGHTED + SEPARATION SWEEP
===================================================
HE7: Does allocating updates by controllable error (not volume) help?
HE8: Does the D6 winner capture >50% of controllable error at sep>1.0?

Run: cd backend && python scripts/exp_h4_opportunity.py
Time: ~20 min
"""

import numpy as np
from collections import deque
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_RUN = 2000
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


def compute_error_budget(scorer, scorer_gt, gt, rng, N=1000):
    """Measure per-category controllable error."""
    cat_boundary = np.zeros(C)
    cat_total = np.zeros(C)
    for _ in range(N):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        gt_c = scorer_gt.score(fv, ci).action_index == oa
        pr_c = scorer.score(fv, ci).action_index == oa
        cat_total[ci] += 1
        if gt_c and not pr_c:
            cat_boundary[ci] += 1
    return cat_boundary, cat_total


def run_opportunity_weighted(seed, strategy, gt, start_mu):
    rng = np.random.default_rng(seed)
    scorer = make_scorer(start_mu.copy())
    scorer_gt = make_scorer(gt.copy())
    ca_counts = np.zeros((C, A))
    override_windows = {ci: deque(maxlen=50) for ci in range(C)}
    mode = {ci: "LEARN" for ci in range(C)}

    # Estimate initial controllable error per category
    rng_budget = np.random.default_rng(seed + 40000)
    cat_boundary, cat_total = compute_error_budget(scorer, scorer_gt, gt, rng_budget)
    cat_error_rate = cat_boundary / np.maximum(cat_total, 1)

    # Opportunity weights: proportional to controllable error rate
    opportunity_weights = cat_error_rate / np.maximum(cat_error_rate.sum(), 0.01)

    lc = 0
    all_confs, all_corrects = [], []

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
        override_windows[ci].append(0 if correct else 1)

        ai = oa
        n_ca = ca_counts[ci, ai]
        mu_ca = scorer.centroids[ci, ai]
        update = fv - mu_ca

        if strategy == "STATIC":
            pass

        elif strategy == "VOLUME_WEIGHTED":
            # Standard: η proportional to volume (implicit in SGD)
            scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
            eff_fv = mu_ca + max(scale, 0.005) * update
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
            ca_counts[ci, ai] += 1

        elif strategy == "OPPORTUNITY_WEIGHTED":
            # η boosted for high-error categories, reduced for low-error
            opp_weight = opportunity_weights[ci] / max(CATEGORY_WEIGHTS[ci], 0.01)
            opp_weight = np.clip(opp_weight, 0.1, 5.0)
            scale = opp_weight / np.sqrt(1.0 + n_ca / 50.0)
            eff_fv = mu_ca + max(scale, 0.005) * update
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
            ca_counts[ci, ai] += 1

        elif strategy == "OVERRIDE_WEIGHTED":
            # η proportional to recent override rate (adaptive opportunity)
            or_val = np.mean(override_windows[ci]) if len(override_windows[ci]) > 10 else 0.2
            scale = (0.5 + or_val * 3.0) / np.sqrt(1.0 + n_ca / 50.0)
            eff_fv = mu_ca + max(scale, 0.005) * update
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
            ca_counts[ci, ai] += 1

        elif strategy == "D6_WINNER":
            # confidence + dual_rate + hysteresis + global
            or_val = np.mean(override_windows[ci]) if len(override_windows[ci]) > 5 else 0.5
            if mode[ci] == "PRESERVE" and or_val > 0.25:
                mode[ci] = "LEARN"
            elif mode[ci] == "LEARN" and or_val < 0.10:
                mode[ci] = "PRESERVE"

            if result.confidence <= 0.60:
                if mode[ci] == "LEARN":
                    base_rate = 1.6
                else:
                    base_rate = 0.1
                decay = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
                scale = base_rate * decay
                eff_fv = mu_ca + max(scale, 0.005) * update
                scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
                ca_counts[ci, ai] += 1

        elif strategy == "GATED":
            if result.confidence <= 0.60:
                scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
                eff_fv = mu_ca + max(scale, 0.005) * update
                scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
                ca_counts[ci, ai] += 1

        # Re-estimate opportunity weights periodically
        if n % 500 == 0 and strategy == "OPPORTUNITY_WEIGHTED":
            rng_rebudget = np.random.default_rng(seed + 40000 + n)
            cat_boundary, cat_total = compute_error_budget(scorer, scorer_gt, gt, rng_rebudget, 500)
            cat_error_rate = cat_boundary / np.maximum(cat_total, 1)
            opportunity_weights = cat_error_rate / np.maximum(cat_error_rate.sum(), 0.01)

    confs = np.array(all_confs)
    corrs = np.array(all_corrects)
    return {'acc': lc / N_RUN * 100, 'ece': compute_ece(confs, corrs)}


def main():
    print("=" * 80)
    print("EXP-H4: OPPORTUNITY-WEIGHTED + SEPARATION SWEEP")
    print("=" * 80)

    base_mu = get_base_centroids()
    strategies = ["STATIC", "VOLUME_WEIGHTED", "OPPORTUNITY_WEIGHTED",
                  "OVERRIDE_WEIGHTED", "D6_WINNER", "GATED"]

    # PART A: Opportunity weighting (calibrated)
    print(f"\n{'=' * 80}")
    print("PART A: Opportunity-weighted allocation (calibrated prior)")
    print(f"{'=' * 80}")
    print(f"  {'Strategy':>22s}  {'Acc':>6s}  {'ECE':>8s}")
    print(f"  {'-' * 40}")

    for strat in strategies:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_opportunity_weighted(seed, strat, gt, base_mu)
            runs.append(r)
        acc = np.mean([r['acc'] for r in runs])
        ece = np.mean([r['ece'] for r in runs])
        print(f"  {strat:>22s}  {acc:5.1f}%  {ece:8.4f}")

    # PART B: Wrong category test
    print(f"\n  WRONG CATEGORY (insider_threat shifted 0.3):")
    print(f"  {'Strategy':>22s}  {'Acc':>6s}")
    print(f"  {'-' * 30}")

    for strat in strategies:
        accs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            wrong_mu = base_mu.copy()
            rng_w = np.random.default_rng(seed + 5000)
            direction = rng_w.normal(0, 1, (A, D))
            direction = direction / np.linalg.norm(direction) * 0.3
            wrong_mu[4] += direction
            wrong_mu = np.clip(wrong_mu, 0, 1)
            r = run_opportunity_weighted(seed, strat, gt, wrong_mu)
            accs.append(r['acc'])
        print(f"  {strat:>22s}  {np.mean(accs):5.1f}%")

    # PART C: D6 winner at different separations (HE8)
    print(f"\n{'=' * 80}")
    print("PART C: D6 winner vs baselines at different separations")
    print(f"{'=' * 80}")
    print(f"  {'Sep':>6s}  {'Static':>7s}  {'Gated':>7s}  {'D6Win':>7s}  {'OppWt':>7s}  "
          f"{'Controllable':>12s}  {'D6_capture':>10s}")
    print(f"  {'-' * 70}")

    for sep in [0.25, 0.50, 0.75, 1.00, 1.50, 2.00]:
        results = {}
        for strat in ["STATIC", "GATED", "D6_WINNER", "OPPORTUNITY_WEIGHTED"]:
            accs = []
            for seed in SEEDS_SHORT:
                gt = build_gt(np.random.default_rng(seed), base_mu)
                if sep == 0:
                    prior = gt.copy()
                else:
                    rng_s = np.random.default_rng(seed + 3000)
                    direction = rng_s.normal(0, 1, gt.shape)
                    direction = direction / np.linalg.norm(direction) * sep
                    prior = np.clip(gt + direction, 0, 1)
                r = run_opportunity_weighted(seed, strat, gt, prior)
                accs.append(r['acc'])
            results[strat] = np.mean(accs)

        # Estimate controllable error at this separation
        # From E1 §4: approximately linear ε_boundary ≈ 11.5 * sep
        est_controllable = min(sep * 11.5, 25.0)
        d6_captured = results["D6_WINNER"] - results["STATIC"]
        capture_pct = d6_captured / est_controllable * 100 if est_controllable > 0 else 0

        print(f"  {sep:>6.2f}  {results['STATIC']:>5.1f}%  {results['GATED']:>5.1f}%  "
              f"{results['D6_WINNER']:>5.1f}%  {results['OPPORTUNITY_WEIGHTED']:>5.1f}%  "
              f"{est_controllable:>10.1f}pp  {capture_pct:>8.0f}%")

    print("\nDONE.")


if __name__ == "__main__":
    main()
