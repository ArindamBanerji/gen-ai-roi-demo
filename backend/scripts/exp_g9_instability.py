"""
G9: PER-PARAMETER INSTABILITY
=================================
F1 showed AGGREGATE ρ ≈ -0.07 at the calibrated operating point.
But ρ is the MEAN of 144 per-parameter alignments.

If some parameters have ρ > 0.08 (learning) while most have ρ < 0
(degrading), a SELECTIVE FREEZE controller that continues updating
the learning parameters could outperform global STATIC.

Tests:
1. Per-(c,a,i) alignment ρ distribution
2. Per-(c,a) alignment ρ distribution
3. Selective freeze controller vs global STATIC
4. Observable proxy: drift + accuracy → instability detection

Run: cd backend && python scripts/exp_g9_instability.py
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


def main():
    print("=" * 90)
    print("G9: PER-PARAMETER INSTABILITY")
    print("Is ρ negative for ALL parameters, or just most?")
    print("=" * 90)

    base_mu = get_base_centroids()

    # ═══════════════════════════════════════════════════
    # SECTION 1: Per-(c,a,i) alignment distribution
    # ═══════════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 1: Per-parameter ρ distribution at convergence (N=2000-4000)")
    print(f"{'=' * 90}")

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        scorer = make_scorer(base_mu.copy())
        rng = np.random.default_rng(seed)

        # Per-(c,a,i) alignment accumulator
        rho_accum = {(ci, ai, di): [] for ci in range(C) for ai in range(A) for di in range(D)}

        for n in range(1, N_RUN + 1):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            result = scorer.score(fv, ci)
            correct = (result.action_index == oa)

            ai = oa
            for di in range(D):
                update_i = fv[di] - scorer.centroids[ci, ai, di]
                gt_dir_i = gt[ci, ai, di] - scorer.centroids[ci, ai, di]
                if abs(update_i) > 1e-10 and abs(gt_dir_i) > 1e-10:
                    alignment_i = update_i * gt_dir_i / (abs(update_i) * abs(gt_dir_i))
                    if n > 2000:  # only steady-state
                        rho_accum[(ci, ai, di)].append(alignment_i)

            scorer.update(fv, ci, result.action_index, correct, oa)

        # Compute per-parameter ρ
        rho_per_param = {}
        for key, vals in rho_accum.items():
            if len(vals) > 10:
                rho_per_param[key] = np.mean(vals)

        rho_values = list(rho_per_param.values())

        print(f"\n  Seed {seed}: {len(rho_values)} parameters with data")
        print(f"    Aggregate ρ:   {np.mean(rho_values):+.4f}")
        print(f"    Median ρ:      {np.median(rho_values):+.4f}")
        print(f"    Std ρ:         {np.std(rho_values):.4f}")
        print(f"    Min ρ:         {min(rho_values):+.4f}")
        print(f"    Max ρ:         {max(rho_values):+.4f}")

        # Distribution
        n_positive = sum(1 for r in rho_values if r > 0)
        n_above_threshold = sum(1 for r in rho_values if r > 0.08)
        n_strongly_negative = sum(1 for r in rho_values if r < -0.20)
        print(f"    ρ > 0:         {n_positive}/{len(rho_values)} ({n_positive/len(rho_values)*100:.0f}%)")
        print(f"    ρ > 0.08:      {n_above_threshold}/{len(rho_values)} ({n_above_threshold/len(rho_values)*100:.0f}%)")
        print(f"    ρ < -0.20:     {n_strongly_negative}/{len(rho_values)} ({n_strongly_negative/len(rho_values)*100:.0f}%)")

        # Per-(c,a) aggregated ρ
        print(f"\n    Per-(c,a) alignment:")
        print(f"    {'Category':>20s}  {'Action':>10s}  {'ρ':>8s}  {'N_updates':>9s}  {'Status':>10s}")
        print(f"    {'-' * 65}")

        for ci in range(C):
            for ai in range(A):
                ca_rhos = [rho_per_param.get((ci, ai, di), 0) for di in range(D)
                           if (ci, ai, di) in rho_per_param]
                if ca_rhos:
                    ca_rho = np.mean(ca_rhos)
                    n_updates = sum(len(rho_accum[(ci, ai, di)]) for di in range(D))
                    status = "LEARNING" if ca_rho > 0.08 else ("neutral" if ca_rho > 0 else "DEGRADING")
                    print(f"    {CATEGORIES[ci]:>20s}  {ACTIONS[ai]:>10s}  "
                          f"{ca_rho:>+8.4f}  {n_updates:>9d}  {status:>10s}")

        # Which dimensions are learning vs degrading?
        print(f"\n    Per-dimension (averaged across categories):")
        for di in range(D):
            dim_rhos = [rho_per_param.get((ci, ai, di), 0)
                        for ci in range(C) for ai in range(A)
                        if (ci, ai, di) in rho_per_param]
            if dim_rhos:
                print(f"      Dim {di}: ρ = {np.mean(dim_rhos):+.4f} "
                      f"(positive: {sum(1 for r in dim_rhos if r > 0)}/{len(dim_rhos)})")

    # ═══════════════════════════════════════════════════
    # SECTION 2: Selective freeze controller
    # ═══════════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 2: Selective freeze controller")
    print("Freeze parameters where drift is high AND accuracy is declining")
    print(f"{'=' * 90}")

    strategies = {
        "GLOBAL_STATIC": "freeze all",
        "GLOBAL_UPDATE": "update all (sqrt decay)",
        "SELECTIVE_ORACLE": "freeze where ρ < 0.08 (oracle — knows GT)",
        "SELECTIVE_DRIFT": "freeze where drift is high AND q declining (observable)",
    }

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng_base = np.random.default_rng(seed)

        # First pass: compute oracle ρ per (c,a)
        scorer_oracle = make_scorer(base_mu.copy())
        rng_o = np.random.default_rng(seed)
        rho_oracle = {}

        for n in range(1, 2001):
            ci = int(rng_o.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_o.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng_o)
            result = scorer_oracle.score(fv, ci)

            ai = oa
            update = fv - scorer_oracle.centroids[ci, ai]
            gt_dir = gt[ci, ai] - scorer_oracle.centroids[ci, ai]
            if np.linalg.norm(update) > 1e-10 and np.linalg.norm(gt_dir) > 1e-10:
                alignment = np.dot(update, gt_dir) / (np.linalg.norm(update) * np.linalg.norm(gt_dir))
                if (ci, ai) not in rho_oracle:
                    rho_oracle[(ci, ai)] = []
                rho_oracle[(ci, ai)].append(alignment)

            scorer_oracle.update(fv, ci, result.action_index, result.action_index == oa, oa)

        rho_ca = {k: np.mean(v[-50:]) for k, v in rho_oracle.items() if len(v) > 20}

        # Run each strategy
        print(f"\n  Seed {seed}:")
        print(f"  {'Strategy':>20s}  {'Acc@2000':>8s}  {'Acc@4000':>8s}  {'V@4000':>8s}  {'Frozen%':>7s}")
        print(f"  {'-' * 55}")

        for strat_name in strategies:
            scorer = make_scorer(base_mu.copy())
            rng = np.random.default_rng(seed)
            ca_counts = np.zeros((C, A))
            ca_accuracy_window = {(ci, ai): [] for ci in range(C) for ai in range(A)}
            ca_drift = {(ci, ai): np.zeros(D) for ci in range(C) for ai in range(A)}
            ca_prev_mu = {(ci, ai): base_mu[ci, ai].copy() for ci in range(C) for ai in range(A)}
            frozen_params = set()

            lc = 0
            checkpoints = {}

            for n in range(1, N_RUN + 1):
                ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                ta = true_action(gt, ci, fv)
                oa = noise_realistic(ta, ci, rng)
                result = scorer.score(fv, ci)
                correct = (result.action_index == oa)
                if correct: lc += 1

                ai = oa
                ca_accuracy_window[(ci, ai)].append(1 if correct else 0)
                if len(ca_accuracy_window[(ci, ai)]) > 100:
                    ca_accuracy_window[(ci, ai)].pop(0)

                should_update = False

                if strat_name == "GLOBAL_STATIC":
                    should_update = False

                elif strat_name == "GLOBAL_UPDATE":
                    should_update = True

                elif strat_name == "SELECTIVE_ORACLE":
                    ca_rho = rho_ca.get((ci, ai), -0.10)
                    should_update = ca_rho > 0.08

                elif strat_name == "SELECTIVE_DRIFT":
                    # Observable: freeze if drift is high and accuracy declining
                    if n > 500 and len(ca_accuracy_window[(ci, ai)]) >= 50:
                        drift_mag = np.linalg.norm(
                            scorer.centroids[ci, ai] - ca_prev_mu[(ci, ai)])
                        recent_acc = np.mean(ca_accuracy_window[(ci, ai)][-50:])
                        older_acc = np.mean(ca_accuracy_window[(ci, ai)][:50]) if len(
                            ca_accuracy_window[(ci, ai)]) >= 100 else recent_acc

                        if drift_mag > 0.02 and recent_acc < older_acc - 0.05:
                            should_update = False  # freeze — drifting and degrading
                        elif drift_mag < 0.01 and recent_acc > 0.75:
                            should_update = False  # freeze — converged
                        else:
                            should_update = True
                    else:
                        should_update = True  # early: always update

                if should_update:
                    n_ca = ca_counts[ci, ai]
                    scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
                    mu_ca = scorer.centroids[ci, ai]
                    eff_fv = mu_ca + max(scale, 0.005) * (fv - mu_ca)
                    scorer.update(eff_fv.astype(np.float64), ci,
                                  result.action_index, correct, oa)
                    ca_counts[ci, ai] += 1

                # Track drift
                if n % 200 == 0:
                    for ci2 in range(C):
                        for ai2 in range(A):
                            ca_prev_mu[(ci2, ai2)] = scorer.centroids[ci2, ai2].copy()

                if n in [2000, 4000]:
                    checkpoints[n] = lc / n * 100

            V = float(np.sum((scorer.centroids - gt) ** 2))
            total_params = C * A
            frozen = sum(1 for ci in range(C) for ai in range(A)
                         if ca_counts[ci, ai] == 0) if strat_name != "GLOBAL_UPDATE" else 0
            frozen_pct = frozen / total_params * 100 if strat_name != "GLOBAL_STATIC" else 100

            print(f"  {strat_name:>20s}  {checkpoints.get(2000, 0):>6.1f}%  "
                  f"{checkpoints.get(4000, 0):>6.1f}%  {V:>8.4f}  {frozen_pct:>5.0f}%")

    # ═══════════════════════════════════════════════════
    # SECTION 3: Instability tensor decomposition
    # ═══════════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 3: Can we decompose instability into signal + noise components?")
    print(f"{'=' * 90}")

    for seed in SEEDS_SHORT[:1]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        scorer = make_scorer(base_mu.copy())
        rng = np.random.default_rng(seed)

        # Run 2000 decisions, tracking per-parameter V changes
        V_per_param_start = np.zeros((C, A, D))
        for ci in range(C):
            for ai in range(A):
                for di in range(D):
                    V_per_param_start[ci, ai, di] = (base_mu[ci, ai, di] - gt[ci, ai, di]) ** 2

        for n in range(1, 2001):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            result = scorer.score(fv, ci)
            scorer.update(fv, ci, result.action_index, result.action_index == oa, oa)

        V_per_param_end = np.zeros((C, A, D))
        for ci in range(C):
            for ai in range(A):
                for di in range(D):
                    V_per_param_end[ci, ai, di] = (scorer.centroids[ci, ai, di] - gt[ci, ai, di]) ** 2

        delta_V = V_per_param_end - V_per_param_start

        # How many parameters improved vs degraded?
        n_improved = (delta_V < 0).sum()
        n_degraded = (delta_V > 0).sum()
        n_unchanged = (delta_V == 0).sum()

        print(f"\n  Seed {seed}: Per-parameter ΔV after 2000 decisions:")
        print(f"    Improved (ΔV < 0):   {n_improved}/{delta_V.size} ({n_improved/delta_V.size*100:.0f}%)")
        print(f"    Degraded (ΔV > 0):   {n_degraded}/{delta_V.size} ({n_degraded/delta_V.size*100:.0f}%)")
        print(f"    Mean ΔV:             {delta_V.mean():+.6f}")
        print(f"    Mean |ΔV| improved:  {delta_V[delta_V < 0].mean():.6f}" if n_improved > 0 else "")
        print(f"    Mean |ΔV| degraded:  {delta_V[delta_V > 0].mean():.6f}" if n_degraded > 0 else "")

        # Which (c,a) pairs improved vs degraded?
        print(f"\n    Per-(c,a) ΔV:")
        print(f"    {'Category':>20s}  {'Action':>10s}  {'ΔV':>10s}  {'Status':>10s}")
        print(f"    {'-' * 55}")
        for ci in range(C):
            for ai in range(A):
                ca_delta = delta_V[ci, ai].sum()
                status = "IMPROVED" if ca_delta < -0.001 else ("DEGRADED" if ca_delta > 0.001 else "stable")
                print(f"    {CATEGORIES[ci]:>20s}  {ACTIONS[ai]:>10s}  {ca_delta:>+10.6f}  {status:>10s}")

    # BINARY QUESTIONS
    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("Q1: Is ρ > 0 for ANY (c,a) pair at convergence?")
    print("Q2: Does selective oracle freeze beat global static?")
    print("Q3: Does selective drift (observable) approximate oracle freeze?")
    print("Q4: What fraction of parameters are improving (ΔV < 0)?")
    print("Q5: Are the improving parameters concentrated in specific categories?")

    print("\nDONE.")


if __name__ == "__main__":
    main()
