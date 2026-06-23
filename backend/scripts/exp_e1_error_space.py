"""
EXP-E1: ERROR SPACE DECOMPOSITION
=====================================
Decompose total error into:
  epsilon_noise:      Oracle noise (irreducible)
  epsilon_boundary:   Centroid on wrong side of boundary (controllable)
  epsilon_structural: True boundary isn't Voronoi (model limit)
  epsilon_capacity:   Centroids don't span full factor space (representation limit)

Also computes:
  - Bayes error (minimum achievable with perfect centroids + given noise)
  - Confusion matrix structure
  - Controllable error fraction
  - Error as function of plant parameters

Run: cd backend && python scripts/exp_e1_error_space.py
Time: ~25 min
"""

import numpy as np
from collections import Counter
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, FREQ_NOISE, ADJACENT
)

SEEDS_SHORT = [42, 123, 777]
N_PROBE = 10000


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
    print("EXP-E1: ERROR SPACE DECOMPOSITION")
    print("=" * 90)

    base_mu = get_base_centroids()

    # ═══════════════════════════════════════════════
    # SECTION 1: BAYES ERROR (perfect centroids + noise)
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 1: BAYES ERROR -- minimum achievable with PERFECT centroids")
    print("Error floor set by oracle noise alone")
    print(f"{'=' * 90}")

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed + 50000)

        # Score with GT centroids (perfect placement)
        scorer_perfect = make_scorer(gt.copy())
        # Score with expert prior
        scorer_prior = make_scorer(base_mu.copy())

        perfect_correct = 0
        prior_correct = 0
        noiseless_correct = 0
        oracle_matches_gt = 0
        total = 0

        per_cat = {ci: {'perfect': 0, 'prior': 0, 'noiseless': 0,
                        'oracle_match': 0, 'total': 0} for ci in range(C)}

        for _ in range(N_PROBE):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)

            # True action (nearest GT centroid, no noise)
            ta = true_action(gt, ci, fv)
            # Oracle action (with noise)
            oa = noise_realistic(ta, ci, rng)

            # Perfect scorer (GT centroids) vs oracle
            r_perfect = scorer_perfect.score(fv, ci)
            if r_perfect.action_index == oa:
                perfect_correct += 1
                per_cat[ci]['perfect'] += 1

            # Prior scorer vs oracle
            r_prior = scorer_prior.score(fv, ci)
            if r_prior.action_index == oa:
                prior_correct += 1
                per_cat[ci]['prior'] += 1

            # Noiseless: GT scorer vs TRUE action (no oracle noise)
            if r_perfect.action_index == ta:
                noiseless_correct += 1
                per_cat[ci]['noiseless'] += 1

            # Does oracle match GT?
            if oa == ta:
                oracle_matches_gt += 1
                per_cat[ci]['oracle_match'] += 1

            per_cat[ci]['total'] += 1
            total += 1

        perfect_acc = perfect_correct / total * 100
        prior_acc = prior_correct / total * 100
        noiseless_acc = noiseless_correct / total * 100
        oracle_match = oracle_matches_gt / total * 100

        print(f"\n  Seed {seed}:")
        print(f"    Noiseless + GT centroids:  {noiseless_acc:.1f}% (theoretical max)")
        print(f"    GT centroids + noise:      {perfect_acc:.1f}% (Bayes error = {100-perfect_acc:.1f}%)")
        print(f"    Expert prior + noise:      {prior_acc:.1f}% (current system)")
        print(f"    Oracle matches GT:         {oracle_match:.1f}%")
        print(f"")
        print(f"    ERROR DECOMPOSITION:")
        print(f"      epsilon_noise     = {100-perfect_acc:.1f}pp  (oracle disagrees with GT scorer)")
        print(f"      epsilon_centroid  = {perfect_acc - prior_acc:.1f}pp  (prior disagrees with GT)")
        print(f"      epsilon_total     = {100-prior_acc:.1f}pp")
        print(f"      CONTROLLABLE fraction: {(perfect_acc - prior_acc)/(100-prior_acc)*100:.0f}%"
              if (100-prior_acc) > 0 else "      CONTROLLABLE fraction: 0%")

        # Per-category breakdown
        print(f"\n    PER-CATEGORY:")
        print(f"    {'Category':>20s}  {'NoiseFloor':>10s}  {'PriorErr':>8s}  {'Controllable':>12s}  {'Frac':>5s}")
        print(f"    {'-' * 60}")
        for ci in range(C):
            t = per_cat[ci]['total']
            if t == 0:
                continue
            perfect_a = per_cat[ci]['perfect'] / t * 100
            prior_a = per_cat[ci]['prior'] / t * 100
            noiseless_a = per_cat[ci]['noiseless'] / t * 100
            noise_err = 100 - perfect_a
            centroid_err = perfect_a - prior_a
            total_err = 100 - prior_a
            frac = centroid_err / total_err * 100 if total_err > 0 else 0
            print(f"    {CATEGORIES[ci]:>20s}  {noise_err:>8.1f}pp  {total_err:>6.1f}pp  "
                  f"{centroid_err:>10.1f}pp  {frac:>4.0f}%")

    # ═══════════════════════════════════════════════
    # SECTION 2: CONFUSION MATRIX
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 2: CONFUSION MATRIX (expert prior, with oracle noise)")
    print(f"{'=' * 90}")

    for seed in SEEDS_SHORT[:1]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        scorer = make_scorer(base_mu.copy())
        rng = np.random.default_rng(seed + 50000)

        # Overall confusion matrix (predicted × oracle)
        confusion = np.zeros((A, A), dtype=int)  # [predicted, oracle]
        # Also: predicted × TRUE (no noise)
        confusion_noiseless = np.zeros((A, A), dtype=int)

        for _ in range(N_PROBE):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            result = scorer.score(fv, ci)
            confusion[result.action_index, oa] += 1
            confusion_noiseless[result.action_index, ta] += 1

        print(f"\n  Seed {seed} -- Predicted vs Oracle (with noise):")
        print(f"  {'Predicted':>12s}", end="")
        for ai in range(A):
            print(f"  {ACTIONS[ai][:8]:>8s}", end="")
        print(f"  {'Total':>6s}  {'Acc':>5s}")
        for pi in range(A):
            row_total = confusion[pi].sum()
            acc = confusion[pi, pi] / row_total * 100 if row_total > 0 else 0
            print(f"  {ACTIONS[pi][:12]:>12s}", end="")
            for oi in range(A):
                print(f"  {confusion[pi, oi]:>8d}", end="")
            print(f"  {row_total:>6d}  {acc:>4.0f}%")

        print(f"\n  Predicted vs TRUE action (noiseless):")
        print(f"  {'Predicted':>12s}", end="")
        for ai in range(A):
            print(f"  {ACTIONS[ai][:8]:>8s}", end="")
        print()
        for pi in range(A):
            print(f"  {ACTIONS[pi][:12]:>12s}", end="")
            for ti in range(A):
                print(f"  {confusion_noiseless[pi, ti]:>8d}", end="")
            print()

        # Error directionality: which (true→predicted) pairs dominate?
        print(f"\n  Top error pairs (true -> predicted):")
        errors = []
        for ti in range(A):
            for pi in range(A):
                if ti != pi and confusion_noiseless[pi, ti] > 0:
                    errors.append((ACTIONS[ti], ACTIONS[pi], confusion_noiseless[pi, ti]))
        errors.sort(key=lambda x: -x[2])
        for true_a, pred_a, count in errors[:10]:
            print(f"    {true_a:>12s} -> {pred_a:>12s}: {count:>5d} errors")

    # ═══════════════════════════════════════════════
    # SECTION 3: ERROR BY GEOMETRY
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 3: ERROR GEOMETRY -- boundary vs structural vs noise")
    print(f"{'=' * 90}")

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        scorer_prior = make_scorer(base_mu.copy())
        scorer_gt = make_scorer(gt.copy())
        rng = np.random.default_rng(seed + 50000)

        n_noise_error = 0        # GT scorer wrong because oracle noise
        n_boundary_error = 0     # Prior scorer wrong, GT scorer right (controllable)
        n_both_wrong = 0         # Both scorers wrong (structural or extreme noise)
        n_correct = 0
        n_total = 0

        boundary_errors_by_dist = []

        for _ in range(N_PROBE):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)

            r_gt = scorer_gt.score(fv, ci)
            r_prior = scorer_prior.score(fv, ci)

            gt_correct = (r_gt.action_index == oa)
            prior_correct = (r_prior.action_index == oa)

            if prior_correct:
                n_correct += 1
            elif gt_correct and not prior_correct:
                n_boundary_error += 1
                # Boundary distance for this error
                dists = [np.linalg.norm(fv - base_mu[ci, ai]) for ai in range(A)]
                sd = np.sort(dists)
                bd = (sd[1] - sd[0]) / 2
                boundary_errors_by_dist.append(bd)
            elif not gt_correct and not prior_correct:
                n_both_wrong += 1
            elif not gt_correct and prior_correct:
                # Prior accidentally right when GT scorer is wrong (noise artifact)
                n_noise_error += 1
                n_correct += 1  # count as correct for prior

            n_total += 1

        print(f"\n  Seed {seed}:")
        print(f"    Correct (prior agrees with oracle):           {n_correct:>5d} ({n_correct/n_total*100:.1f}%)")
        print(f"    epsilon_boundary (GT right, prior wrong):           {n_boundary_error:>5d} ({n_boundary_error/n_total*100:.1f}%)")
        print(f"    epsilon_noise (both wrong -- oracle noise):          {n_both_wrong:>5d} ({n_both_wrong/n_total*100:.1f}%)")
        print(f"    epsilon_total:                                      {(n_boundary_error+n_both_wrong)/n_total*100:.1f}%")
        print(f"    CONTROLLABLE (epsilon_boundary / epsilon_total):          "
              f"{n_boundary_error/(n_boundary_error+n_both_wrong)*100:.0f}%"
              if (n_boundary_error+n_both_wrong) > 0 else "    N/A")

        if boundary_errors_by_dist:
            bds = np.array(boundary_errors_by_dist)
            print(f"    Boundary errors -- distance to boundary:")
            print(f"      mean={bds.mean():.4f} median={np.median(bds):.4f}")
            for thresh in [0.01, 0.02, 0.05, 0.10]:
                frac = (bds < thresh).mean() * 100
                print(f"      < {thresh:.2f}: {frac:.0f}% of boundary errors")

    # ═══════════════════════════════════════════════
    # SECTION 4: ERROR AS FUNCTION OF SEPARATION
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 4: ERROR COMPONENTS vs GT-PRIOR SEPARATION")
    print(f"{'=' * 90}")
    print(f"  {'Sep':>6s}  {'epsilon_total':>7s}  {'epsilon_noise':>7s}  {'epsilon_boundary':>10s}  "
          f"{'epsilon_both':>7s}  {'Controllable':>12s}  {'Bayes':>6s}")
    print(f"  {'-' * 65}")

    separations = [0.0, 0.10, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00]
    for sep in separations:
        totals = {'correct': 0, 'boundary': 0, 'both_wrong': 0, 'total': 0, 'bayes_err': 0}

        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            if sep == 0:
                prior = gt.copy()
            else:
                rng_s = np.random.default_rng(seed + 3000)
                direction = rng_s.normal(0, 1, gt.shape)
                direction = direction / np.linalg.norm(direction) * sep
                prior = np.clip(gt + direction, 0, 1)

            scorer_gt = make_scorer(gt.copy())
            scorer_prior = make_scorer(prior)
            rng = np.random.default_rng(seed + 50000)

            for _ in range(5000):
                ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                ta = true_action(gt, ci, fv)
                oa = noise_realistic(ta, ci, rng)

                r_gt = scorer_gt.score(fv, ci)
                r_prior = scorer_prior.score(fv, ci)

                gt_correct = (r_gt.action_index == oa)
                prior_correct = (r_prior.action_index == oa)

                if not gt_correct:
                    totals['bayes_err'] += 1

                if prior_correct:
                    totals['correct'] += 1
                elif gt_correct:
                    totals['boundary'] += 1
                else:
                    totals['both_wrong'] += 1

                totals['total'] += 1

        t = totals['total']
        e_total = (totals['boundary'] + totals['both_wrong']) / t * 100
        e_noise = totals['both_wrong'] / t * 100
        e_boundary = totals['boundary'] / t * 100
        bayes = totals['bayes_err'] / t * 100
        controllable = e_boundary / e_total * 100 if e_total > 0 else 0

        print(f"  {sep:>6.2f}  {e_total:>5.1f}pp  {e_noise:>5.1f}pp  {e_boundary:>8.1f}pp  "
              f"{e_noise:>5.1f}pp  {controllable:>10.0f}%  {bayes:>5.1f}%")

    # ═══════════════════════════════════════════════
    # SECTION 5: CAPACITY ERROR — d-dimensional limit
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 5: CAPACITY ERROR -- does low effective dimensionality cause errors?")
    print(f"{'=' * 90}")

    for seed in SEEDS_SHORT[:1]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed + 50000)

        # Score with FULL-rank GT centroids
        scorer_gt = make_scorer(gt.copy())

        # Create PROJECTED GT: project onto 2D subspace per category
        gt_projected = gt.copy()
        for ci in range(C):
            centered = gt[ci] - gt[ci].mean(axis=0)
            U, S, Vh = np.linalg.svd(centered, full_matrices=False)
            # Keep only top 2 components
            k = 2
            reconstructed = U[:, :k] @ np.diag(S[:k]) @ Vh[:k, :]
            gt_projected[ci] = reconstructed + gt[ci].mean(axis=0)

        scorer_projected = make_scorer(gt_projected.copy())

        full_correct = 0
        proj_correct = 0
        total = 0

        for _ in range(N_PROBE):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)

            r_full = scorer_gt.score(fv, ci)
            r_proj = scorer_projected.score(fv, ci)

            if r_full.action_index == ta:
                full_correct += 1
            if r_proj.action_index == ta:
                proj_correct += 1
            total += 1

        print(f"\n  Seed {seed}:")
        print(f"    Full-rank GT accuracy (noiseless):    {full_correct/total*100:.1f}%")
        print(f"    2D-projected GT accuracy (noiseless): {proj_correct/total*100:.1f}%")
        print(f"    epsilon_capacity (lost by projection):      {(full_correct-proj_correct)/total*100:.1f}pp")
        print(f"    Projection preserves {proj_correct/full_correct*100:.1f}% of decisions")

    # ═══════════════════════════════════════════════
    # SECTION 6: ERROR BUDGET SUMMARY
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 6: ERROR BUDGET (production operating point, sep~=0.8)")
    print(f"{'=' * 90}")

    # Use average across seeds at production separation
    budget = {'noise': [], 'boundary': [], 'total': []}
    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        scorer_gt = make_scorer(gt.copy())
        scorer_prior = make_scorer(base_mu.copy())
        rng = np.random.default_rng(seed + 50000)

        n_b, n_bw, n_t = 0, 0, 0
        for _ in range(N_PROBE):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)

            gt_c = scorer_gt.score(fv, ci).action_index == oa
            prior_c = scorer_prior.score(fv, ci).action_index == oa

            if not prior_c and gt_c:
                n_b += 1
            if not prior_c and not gt_c:
                n_bw += 1
            n_t += 1

        budget['boundary'].append(n_b / n_t * 100)
        budget['noise'].append(n_bw / n_t * 100)
        budget['total'].append((n_b + n_bw) / n_t * 100)

    print(f"""
    +-------------------------------------------------+
    |  TOTAL ERROR:        {np.mean(budget['total']):>5.1f}pp                      |
    |  +-- epsilon_noise:        {np.mean(budget['noise']):>5.1f}pp  (IRREDUCIBLE)       |
    |  +-- epsilon_boundary:     {np.mean(budget['boundary']):>5.1f}pp  (CONTROLLABLE)    |
    |                                                 |
    |  Controllable fraction: {np.mean(budget['boundary'])/np.mean(budget['total'])*100:>4.0f}%                  |
    |  Max achievable acc:    {100-np.mean(budget['noise']):>5.1f}%                 |
    |  Current acc:           {100-np.mean(budget['total']):>5.1f}%                 |
    |  Room to improve:       {np.mean(budget['boundary']):>5.1f}pp                 |
    +-------------------------------------------------+
    """)

    print("DONE.")


if __name__ == "__main__":
    main()
