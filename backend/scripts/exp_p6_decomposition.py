"""
EXP-P6: PLANT DECOMPOSITION
===============================
The plant is a composition: distance -> square -> scale -> softmax -> argmax.
Accuracy depends on argmax (discontinuous). Confidence depends on softmax
(saturated). These are DIFFERENT functions of mu.

This experiment measures:
1. How far queries sit from Voronoi boundaries (boundary proximity)
2. What fraction of queries are "near boundary" vs "deep inside cell"
3. How the composition chain affects each signal at each stage
4. Controller leverage as a function of boundary proximity

Uses PRODUCTION ProfileScorer throughout.

Run: cd backend && python scripts/exp_p6_decomposition.py
Time: ~25 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

SEEDS_SHORT = [42, 123, 777]
N_PROBE = 5000
N_RUN = 2000


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


def analyze_boundaries(scorer, gt, seed, N):
    """For each query, measure distance to nearest Voronoi boundary."""
    rng = np.random.default_rng(seed)
    mu = scorer.centroids

    boundary_distances = []
    is_correct = []
    confidences = []
    margin_ratios = []  # d_second / d_first

    for _ in range(N):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)

        # Distances to all action centroids
        dists = np.array([np.linalg.norm(fv - mu[ci, ai]) for ai in range(A)])
        sorted_idx = np.argsort(dists)
        d_first = dists[sorted_idx[0]]  # closest centroid
        d_second = dists[sorted_idx[1]]  # second closest

        # Distance to boundary ≈ (d_second - d_first) / 2
        # (boundary is the perpendicular bisector of the two centroids)
        boundary_dist = (d_second - d_first) / 2

        result = scorer.score(fv, ci)
        correct = (result.action_index == ta)

        boundary_distances.append(boundary_dist)
        is_correct.append(correct)
        confidences.append(result.confidence)
        margin_ratios.append(d_second / d_first if d_first > 0 else 1.0)

    return {
        'boundary_dists': np.array(boundary_distances),
        'is_correct': np.array(is_correct),
        'confidences': np.array(confidences),
        'margin_ratios': np.array(margin_ratios),
    }


def run_production_controller(seed, strategy, gt, start_mu):
    """Run with PRODUCTION ProfileScorer."""
    rng = np.random.default_rng(seed)
    scorer = make_scorer(start_mu.copy())
    ca_counts = np.zeros((C, A))
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

        if strategy == "STATIC":
            pass
        elif strategy == "SQRT_DECAY":
            ai = oa
            n_ca = ca_counts[ci, ai]
            scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
            mu_ca = scorer.centroids[ci, ai]
            eff_fv = mu_ca + max(scale, 0.005) * (fv - mu_ca)
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
            ca_counts[ci, ai] += 1
        elif strategy == "GATED":
            if result.confidence <= 0.60:
                ai = oa
                n_ca = ca_counts[ci, ai]
                scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
                mu_ca = scorer.centroids[ci, ai]
                eff_fv = mu_ca + max(scale, 0.005) * (fv - mu_ca)
                scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
                ca_counts[ci, ai] += 1
        elif strategy == "RAW_SGD":
            scorer.update(fv, ci, result.action_index, correct, oa)

    confs = np.array(all_confs)
    corrs = np.array(all_corrects)
    return {'acc': lc / N_RUN * 100, 'ece': compute_ece(confs, corrs)}


def main():
    print("=" * 90)
    print("EXP-P6: PLANT DECOMPOSITION")
    print("Composition chain: distance -> square -> scale -> softmax -> argmax")
    print("=" * 90)

    base_mu = get_base_centroids()

    # ═══════════════════════════════════════════════
    # SECTION 1: BOUNDARY PROXIMITY ANALYSIS
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 1: BOUNDARY PROXIMITY (how far are queries from Voronoi boundaries?)")
    print(f"{'=' * 90}")

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        scorer = make_scorer(base_mu.copy())
        data = analyze_boundaries(scorer, gt, seed + 50000, N_PROBE)

        bd = data['boundary_dists']
        correct_mask = data['is_correct']
        confs = data['confidences']
        margins = data['margin_ratios']

        print(f"\n  Seed {seed}:")
        print(f"    Accuracy: {correct_mask.mean()*100:.1f}%")
        print(f"    Boundary distance: mean={bd.mean():.4f} median={np.median(bd):.4f} "
              f"std={bd.std():.4f}")
        print(f"    Margin ratio (d2/d1): mean={margins.mean():.3f} median={np.median(margins):.3f}")

        # Distribution of boundary distances
        thresholds = [0.01, 0.02, 0.05, 0.10, 0.20, 0.50]
        print(f"    Fraction of queries near boundary:")
        for t in thresholds:
            frac = (bd < t).mean() * 100
            near_acc = correct_mask[bd < t].mean() * 100 if (bd < t).sum() > 0 else 0
            far_acc = correct_mask[bd >= t].mean() * 100 if (bd >= t).sum() > 0 else 0
            print(f"      d_boundary < {t:.2f}: {frac:.1f}% of queries, "
                  f"acc_near={near_acc:.1f}% acc_far={far_acc:.1f}%")

        # Confidence vs boundary distance
        print(f"    Confidence vs boundary distance (binned):")
        for lo, hi in [(0, 0.02), (0.02, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.50), (0.50, 1.0)]:
            mask = (bd >= lo) & (bd < hi)
            if mask.sum() > 10:
                print(f"      d in [{lo:.2f}, {hi:.2f}): "
                      f"conf={confs[mask].mean():.4f} acc={correct_mask[mask].mean()*100:.1f}% "
                      f"n={mask.sum()}")

    # ═══════════════════════════════════════════════
    # SECTION 2: COMPOSITION CHAIN SENSITIVITY
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 2: COMPOSITION CHAIN SENSITIVITY")
    print("How does a centroid perturbation propagate through each stage?")
    print(f"{'=' * 90}")

    for seed in SEEDS_SHORT[:1]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        scorer = make_scorer(base_mu.copy())

        eps_values = [0.001, 0.005, 0.01, 0.05, 0.10]
        print(f"\n  Seed {seed}:")
        print(f"  {'eps':>7s}  {'Delta_dist':>8s}  {'Delta_dist^2':>8s}  {'Delta_logit':>8s}  "
              f"{'Delta_prob':>8s}  {'Delta_conf':>8s}  {'Delta_action':>8s}  {'Delta_acc':>7s}")
        print(f"  {'-' * 72}")

        for eps in eps_values:
            delta_dists, delta_dist2s, delta_logits = [], [], []
            delta_probs, delta_confs = [], []
            delta_actions = 0
            total = 0

            rng = np.random.default_rng(seed + 60000)
            rng_dir = np.random.default_rng(seed + 70000)
            direction = rng_dir.normal(0, 1, base_mu.shape)
            direction = direction / np.linalg.norm(direction) * eps
            perturbed = base_mu + direction
            scorer_p = make_scorer(perturbed)

            for _ in range(2000):
                ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)

                # Original distances
                dists_orig = np.array([np.linalg.norm(fv - base_mu[ci, ai]) for ai in range(A)])
                dists_pert = np.array([np.linalg.norm(fv - perturbed[ci, ai]) for ai in range(A)])

                # Stage by stage
                delta_dists.append(np.mean(np.abs(dists_pert - dists_orig)))
                delta_dist2s.append(np.mean(np.abs(dists_pert**2 - dists_orig**2)))

                logits_orig = -dists_orig**2
                logits_pert = -dists_pert**2
                delta_logits.append(np.mean(np.abs(logits_pert - logits_orig)))

                r_orig = scorer.score(fv, ci)
                r_pert = scorer_p.score(fv, ci)
                delta_probs.append(np.mean(np.abs(
                    np.array(r_pert.probabilities) - np.array(r_orig.probabilities))))
                delta_confs.append(abs(r_pert.confidence - r_orig.confidence))

                if r_orig.action_index != r_pert.action_index:
                    delta_actions += 1
                total += 1

            print(f"  {eps:>7.3f}  {np.mean(delta_dists):>8.5f}  "
                  f"{np.mean(delta_dist2s):>8.5f}  {np.mean(delta_logits):>8.5f}  "
                  f"{np.mean(delta_probs):>8.5f}  {np.mean(delta_confs):>8.5f}  "
                  f"{delta_actions/total*100:>6.1f}%  "
                  f"{'(see P4)':>7s}")

    # ═══════════════════════════════════════════════
    # SECTION 3: WHERE DO ERRORS LIVE?
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 3: ERROR GEOGRAPHY -- where do wrong decisions concentrate?")
    print(f"{'=' * 90}")

    for seed in SEEDS_SHORT[:2]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        scorer = make_scorer(base_mu.copy())
        data = analyze_boundaries(scorer, gt, seed + 50000, N_PROBE)

        bd = data['boundary_dists']
        correct = data['is_correct']
        errors = ~correct

        print(f"\n  Seed {seed}: {errors.sum()} errors out of {N_PROBE}")

        if errors.sum() > 0:
            error_bd = bd[errors]
            correct_bd = bd[correct]
            print(f"    Error boundary distance: mean={error_bd.mean():.4f} "
                  f"median={np.median(error_bd):.4f}")
            print(f"    Correct boundary distance: mean={correct_bd.mean():.4f} "
                  f"median={np.median(correct_bd):.4f}")
            print(f"    Errors are {correct_bd.mean()/error_bd.mean():.1f}x further from "
                  f"boundary than correct decisions" if error_bd.mean() < correct_bd.mean()
                  else f"    Errors are {error_bd.mean()/correct_bd.mean():.1f}x CLOSER to "
                  f"boundary than correct decisions")

            # What fraction of errors are within reach of a small centroid move?
            for reach in [0.01, 0.02, 0.05, 0.10, 0.20]:
                fixable = (error_bd < reach).sum()
                print(f"    Errors with d_boundary < {reach:.2f} (fixable by mu move of ~{reach:.2f}): "
                      f"{fixable}/{errors.sum()} ({fixable/errors.sum()*100:.0f}%)")

    # ═══════════════════════════════════════════════
    # SECTION 4: PRODUCTION SCORER — SEPARATION SWEEP
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 4: PRODUCTION ProfileScorer -- controller leverage vs separation")
    print("(Replaces P4/P5 with production scorer)")
    print(f"{'=' * 90}")

    separations = [0.0, 0.10, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00]
    strategies = ["STATIC", "GATED", "SQRT_DECAY", "RAW_SGD"]

    print(f"  {'Sep':>6s}  {'%NearBdry':>9s}", end="")
    for s in strategies:
        print(f"  {s[:8]:>8s}", end="")
    print(f"  {'Gated-S':>7s}  {'Decay-S':>7s}  {'Raw-S':>6s}")
    print(f"  {'-' * 85}")

    for sep in separations:
        results = {s: [] for s in strategies}
        near_bdry_pcts = []

        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            if sep == 0:
                prior = gt.copy()
            else:
                rng_s = np.random.default_rng(seed + 3000)
                direction = rng_s.normal(0, 1, gt.shape)
                direction = direction / np.linalg.norm(direction) * sep
                prior = np.clip(gt + direction, 0, 1)

            # Boundary proximity at this separation
            scorer_check = make_scorer(prior)
            bd_data = analyze_boundaries(scorer_check, gt, seed + 50000, 1000)
            near_bdry_pcts.append((bd_data['boundary_dists'] < 0.05).mean() * 100)

            for strategy in strategies:
                r = run_production_controller(seed, strategy, gt, prior)
                results[strategy].append(r['acc'])

        near_pct = np.mean(near_bdry_pcts)
        accs = {s: np.mean(results[s]) for s in strategies}
        s_acc = accs["STATIC"]
        print(f"  {sep:>6.2f}  {near_pct:>7.1f}%", end="")
        for s in strategies:
            print(f"  {accs[s]:>6.1f}%", end="")
        print(f"  {accs['GATED']-s_acc:>+5.1f}pp  {accs['SQRT_DECAY']-s_acc:>+5.1f}pp  "
              f"{accs['RAW_SGD']-s_acc:>+4.1f}pp")

    # ═══════════════════════════════════════════════
    # SECTION 5: BOUNDARY-AWARE CONTROLLER
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 5: BOUNDARY-AWARE -- only update queries near boundaries")
    print(f"{'=' * 90}")

    for sep in [0.50, 0.75, 1.00, 1.50]:
        results = {'STATIC': [], 'GATED': [], 'BOUNDARY_AWARE': []}

        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            rng_s = np.random.default_rng(seed + 3000)
            direction = rng_s.normal(0, 1, gt.shape)
            direction = direction / np.linalg.norm(direction) * sep
            prior = np.clip(gt + direction, 0, 1)

            # Standard controllers
            for strategy in ["STATIC", "GATED"]:
                r = run_production_controller(seed, strategy, gt, prior)
                results[strategy].append(r['acc'])

            # Boundary-aware: only update when margin ratio < threshold
            rng = np.random.default_rng(seed)
            scorer = make_scorer(prior.copy())
            ca_counts = np.zeros((C, A))
            lc = 0
            for n in range(1, N_RUN + 1):
                ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                ta = true_action(gt, ci, fv)
                oa = noise_realistic(ta, ci, rng)
                result = scorer.score(fv, ci)
                correct = (result.action_index == oa)
                if correct: lc += 1

                # Compute margin
                dists = np.array([np.linalg.norm(fv - scorer.centroids[ci, ai])
                                  for ai in range(A)])
                sorted_d = np.sort(dists)
                margin = (sorted_d[1] - sorted_d[0]) / 2

                # Only update if near boundary (margin < 0.05)
                if margin < 0.05:
                    ai = oa
                    n_ca = ca_counts[ci, ai]
                    scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
                    mu_ca = scorer.centroids[ci, ai]
                    eff_fv = mu_ca + max(scale, 0.005) * (fv - mu_ca)
                    scorer.update(eff_fv.astype(np.float64), ci,
                                  result.action_index, correct, oa)
                    ca_counts[ci, ai] += 1

            results['BOUNDARY_AWARE'].append(lc / N_RUN * 100)

        accs = {s: np.mean(results[s]) for s in results}
        print(f"  sep={sep:.2f}: Static={accs['STATIC']:.1f}%  Gated={accs['GATED']:.1f}%  "
              f"BoundaryAware={accs['BOUNDARY_AWARE']:.1f}%  "
              f"BA-Static={accs['BOUNDARY_AWARE']-accs['STATIC']:+.1f}pp")

    # ═══════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)

    # Use first seed for binary questions
    gt = build_gt(np.random.default_rng(42), base_mu)
    scorer = make_scorer(base_mu.copy())
    data = analyze_boundaries(scorer, gt, 42 + 50000, N_PROBE)

    near_5pct = (data['boundary_dists'] < 0.05).mean() * 100
    errors = ~data['is_correct']
    if errors.sum() > 0:
        error_near = (data['boundary_dists'][errors] < 0.05).mean() * 100
    else:
        error_near = 0

    print(f"Q1: What fraction of queries are near boundary (<0.05)? {near_5pct:.1f}%")
    print(f"Q2: What fraction of ERRORS are near boundary? {error_near:.0f}%")
    print(f"Q3: Does boundary-aware controller outperform gated? (see Section 5)")

    print("\nDONE.")


if __name__ == "__main__":
    main()
