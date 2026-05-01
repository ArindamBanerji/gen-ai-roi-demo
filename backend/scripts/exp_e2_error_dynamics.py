"""
EXP-E2: ERROR DYNAMICS AND REACHABILITY
==========================================
E1 tells us WHAT errors exist. E2 asks:
  - Can the controller REACH the controllable errors?
  - Does fixing one error CREATE another?
  - How does the error budget change over time?
  - What is the NET error reduction per update?

Run: cd backend && python scripts/exp_e2_error_dynamics.py
Time: ~20 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

SEEDS_SHORT = [42, 123, 777]
N_RUN = 2000
N_PROBE = 3000


def compute_error_budget(scorer, scorer_gt, gt, seed, N):
    """Measure ε_boundary and ε_noise at current centroid position."""
    rng = np.random.default_rng(seed)
    n_boundary = 0
    n_noise = 0
    n_total = 0

    for _ in range(N):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        gt_correct = (scorer_gt.score(fv, ci).action_index == oa)
        prior_correct = (scorer.score(fv, ci).action_index == oa)

        if not prior_correct and gt_correct:
            n_boundary += 1
        if not prior_correct and not gt_correct:
            n_noise += 1
        n_total += 1

    return {
        'e_boundary': n_boundary / n_total * 100,
        'e_noise': n_noise / n_total * 100,
        'e_total': (n_boundary + n_noise) / n_total * 100,
        'acc': (1 - (n_boundary + n_noise) / n_total) * 100,
    }


def main():
    print("=" * 90)
    print("EXP-E2: ERROR DYNAMICS AND REACHABILITY")
    print("=" * 90)

    base_mu = get_base_centroids()

    # ═══════════════════════════════════════════════
    # SECTION 1: ERROR BUDGET OVER TIME
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 1: How does the error budget change as the controller operates?")
    print(f"{'=' * 90}")

    checkpoints = [0, 50, 100, 200, 500, 1000, 2000]

    for strategy_name in ["GATED", "SQRT_DECAY", "RAW_SGD"]:
        print(f"\n  STRATEGY: {strategy_name}")
        print(f"  {'N':>6s}  {'ε_total':>7s}  {'ε_bound':>7s}  {'ε_noise':>7s}  "
              f"{'Controllable%':>13s}  {'Acc':>5s}")
        print(f"  {'-' * 55}")

        for seed in SEEDS_SHORT[:1]:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            scorer_gt = make_scorer(gt.copy())
            scorer = make_scorer(base_mu.copy())
            ca_counts = np.zeros((C, A))
            rng = np.random.default_rng(seed)

            # Checkpoint 0
            budget = compute_error_budget(scorer, scorer_gt, gt, seed + 90000, N_PROBE)
            ctrl_frac = budget['e_boundary'] / budget['e_total'] * 100 if budget['e_total'] > 0 else 0
            print(f"  {0:>6d}  {budget['e_total']:>5.1f}pp  {budget['e_boundary']:>5.1f}pp  "
                  f"{budget['e_noise']:>5.1f}pp  {ctrl_frac:>11.0f}%  {budget['acc']:>4.1f}%")

            for n in range(1, N_RUN + 1):
                ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                ta = true_action(gt, ci, fv)
                oa = noise_realistic(ta, ci, rng)
                result = scorer.score(fv, ci)
                correct = (result.action_index == oa)

                if strategy_name == "GATED":
                    if result.confidence <= 0.60:
                        ai = oa
                        n_ca = ca_counts[ci, ai]
                        scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
                        mu_ca = scorer.centroids[ci, ai]
                        eff_fv = mu_ca + max(scale, 0.005) * (fv - mu_ca)
                        scorer.update(eff_fv.astype(np.float64), ci,
                                      result.action_index, correct, oa)
                        ca_counts[ci, ai] += 1
                elif strategy_name == "SQRT_DECAY":
                    ai = oa
                    n_ca = ca_counts[ci, ai]
                    scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
                    mu_ca = scorer.centroids[ci, ai]
                    eff_fv = mu_ca + max(scale, 0.005) * (fv - mu_ca)
                    scorer.update(eff_fv.astype(np.float64), ci,
                                  result.action_index, correct, oa)
                    ca_counts[ci, ai] += 1
                elif strategy_name == "RAW_SGD":
                    scorer.update(fv, ci, result.action_index, correct, oa)

                if n in checkpoints and n > 0:
                    budget = compute_error_budget(scorer, scorer_gt, gt, seed + 90000, N_PROBE)
                    ctrl_frac = budget['e_boundary'] / budget['e_total'] * 100 if budget['e_total'] > 0 else 0
                    print(f"  {n:>6d}  {budget['e_total']:>5.1f}pp  {budget['e_boundary']:>5.1f}pp  "
                          f"{budget['e_noise']:>5.1f}pp  {ctrl_frac:>11.0f}%  {budget['acc']:>4.1f}%")

    # ═══════════════════════════════════════════════
    # SECTION 2: PER-UPDATE ERROR CREATION/DESTRUCTION
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 2: Does fixing one error create another?")
    print("Measure errors BEFORE and AFTER each update")
    print(f"{'=' * 90}")

    for seed in SEEDS_SHORT[:1]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        scorer = make_scorer(base_mu.copy())
        rng = np.random.default_rng(seed)

        net_fixed = 0
        net_created = 0
        updates_measured = 0

        # Track a fixed test set
        rng_test = np.random.default_rng(seed + 80000)
        test_queries = []
        for _ in range(500):
            ci = int(rng_test.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_test.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            test_queries.append((ci, fv, ta))

        def count_errors():
            errs = 0
            for ci, fv, ta in test_queries:
                r = scorer.score(fv, ci)
                if r.action_index != ta:
                    errs += 1
            return errs

        prev_errors = count_errors()

        for n in range(1, 500 + 1):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            result = scorer.score(fv, ci)
            correct = (result.action_index == oa)

            if result.confidence <= 0.60:
                # Before update
                errors_before = count_errors()

                # Apply update
                scorer.update(fv, ci, result.action_index, correct, oa)
                updates_measured += 1

                # After update
                errors_after = count_errors()

                delta = errors_after - errors_before
                if delta < 0:
                    net_fixed += abs(delta)
                elif delta > 0:
                    net_created += delta

                if updates_measured <= 20 or updates_measured % 50 == 0:
                    print(f"    Update {updates_measured:>4d}: errors {errors_before} → {errors_after} "
                          f"(Δ={delta:+d})")

        print(f"\n    Summary ({updates_measured} updates measured):")
        print(f"      Total errors fixed:   {net_fixed}")
        print(f"      Total errors created: {net_created}")
        print(f"      Net:                  {net_fixed - net_created:+d}")
        print(f"      Fix rate:             {net_fixed/updates_measured:.2f} per update")
        print(f"      Create rate:          {net_created/updates_measured:.2f} per update")
        print(f"      Net rate:             {(net_fixed-net_created)/updates_measured:+.3f} per update")

    # ═══════════════════════════════════════════════
    # SECTION 3: UPDATE DIRECTION ANALYSIS
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 3: Is the average update direction aligned with GT direction?")
    print(f"{'=' * 90}")

    for seed in SEEDS_SHORT[:1]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        scorer = make_scorer(base_mu.copy())
        rng = np.random.default_rng(seed)

        # Collect update directions per (c,a)
        update_dirs = {(ci, ai): [] for ci in range(C) for ai in range(A)}
        gt_dirs = {}
        for ci in range(C):
            for ai in range(A):
                gt_dir = gt[ci, ai] - base_mu[ci, ai]
                if np.linalg.norm(gt_dir) > 0:
                    gt_dirs[(ci, ai)] = gt_dir / np.linalg.norm(gt_dir)
                else:
                    gt_dirs[(ci, ai)] = np.zeros(D)

        for n in range(1, N_RUN + 1):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            result = scorer.score(fv, ci)

            # Record the update direction (f - mu)
            ai = oa
            update_dir = fv - scorer.centroids[ci, ai]
            if np.linalg.norm(update_dir) > 0:
                update_dirs[(ci, ai)].append(update_dir / np.linalg.norm(update_dir))

            scorer.update(fv, ci, result.action_index, result.action_index == oa, oa)

        print(f"\n  Seed {seed}: alignment of mean update direction with GT direction")
        print(f"  {'Category':>20s}  {'Action':>10s}  {'N_updates':>9s}  {'Alignment':>9s}  "
              f"{'|GT_dir|':>8s}")
        print(f"  {'-' * 65}")

        alignments = []
        for ci in range(C):
            for ai in range(A):
                dirs = update_dirs[(ci, ai)]
                if len(dirs) > 5:
                    mean_dir = np.mean(dirs, axis=0)
                    if np.linalg.norm(mean_dir) > 0:
                        mean_dir_norm = mean_dir / np.linalg.norm(mean_dir)
                        alignment = np.dot(mean_dir_norm, gt_dirs[(ci, ai)])
                        alignments.append(alignment)
                        gt_dist = np.linalg.norm(gt[ci, ai] - base_mu[ci, ai])
                        print(f"  {CATEGORIES[ci]:>20s}  {ACTIONS[ai]:>10s}  {len(dirs):>9d}  "
                              f"{alignment:>+9.4f}  {gt_dist:>8.4f}")

        if alignments:
            print(f"\n    Mean alignment across all (c,a): {np.mean(alignments):+.4f}")
            print(f"    Positive alignment (toward GT): {sum(1 for a in alignments if a > 0)}/{len(alignments)}")
            print(f"    Strong alignment (>0.3): {sum(1 for a in alignments if a > 0.3)}/{len(alignments)}")

    # ═══════════════════════════════════════════════
    # SECTION 4: SUBSPACE PROJECTION
    # ═══════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("SECTION 4: How much update energy lands in the useful 2D subspace?")
    print(f"{'=' * 90}")

    for seed in SEEDS_SHORT[:1]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)

        # Compute the 2D subspace per category (from P7)
        subspace_bases = {}
        for ci in range(C):
            centered = base_mu[ci] - base_mu[ci].mean(axis=0)
            U, S, Vh = np.linalg.svd(centered, full_matrices=False)
            subspace_bases[ci] = Vh[:2]  # top 2 right singular vectors

        in_subspace_energy = 0
        total_energy = 0
        n_updates = 0

        scorer = make_scorer(base_mu.copy())
        for n in range(1, N_RUN + 1):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            result = scorer.score(fv, ci)
            correct = (result.action_index == oa)

            ai = oa
            update = fv - scorer.centroids[ci, ai]
            update_energy = np.linalg.norm(update) ** 2
            total_energy += update_energy

            # Project onto 2D subspace
            proj = subspace_bases[ci] @ update  # 2-vector
            proj_energy = np.linalg.norm(proj) ** 2
            in_subspace_energy += proj_energy
            n_updates += 1

            scorer.update(fv, ci, result.action_index, correct, oa)

        frac = in_subspace_energy / total_energy * 100 if total_energy > 0 else 0
        print(f"\n  Seed {seed}:")
        print(f"    Total update energy:     {total_energy:.4f}")
        print(f"    In 2D subspace:          {in_subspace_energy:.4f} ({frac:.1f}%)")
        print(f"    Wasted (orthogonal):     {total_energy - in_subspace_energy:.4f} ({100-frac:.1f}%)")
        print(f"    Fraction wasted:         {100-frac:.1f}%")

    print("\nDONE.")


if __name__ == "__main__":
    main()
