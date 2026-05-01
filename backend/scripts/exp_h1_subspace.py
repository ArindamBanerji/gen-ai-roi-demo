"""
EXP-H1: SUBSPACE PROJECTION
==============================
HE1: Does projecting updates onto the 2D centroid subspace
double effective signal and improve accuracy?

E2 showed 60.1% of update energy is wasted in orthogonal
dimensions. This experiment tests the fix directly.

Run: cd backend && python scripts/exp_h1_subspace.py
Time: ~15 min
"""

import numpy as np
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


def compute_subspace_bases(centroids):
    """Compute the 2D subspace per category from centroid arrangement."""
    bases = {}
    for ci in range(C):
        centered = centroids[ci] - centroids[ci].mean(axis=0)
        U, S, Vh = np.linalg.svd(centered, full_matrices=False)
        bases[ci] = Vh[:min(2, len(S))]  # top 2 right singular vectors
    return bases


def project_update(update, bases, ci):
    """Project update onto the category's centroid subspace."""
    B = bases[ci]  # shape (2, D)
    coeffs = B @ update  # project
    projected = B.T @ coeffs  # reconstruct in original space
    return projected


def run_experiment(seed, strategy, gt, start_mu, generic=False):
    rng = np.random.default_rng(seed)
    if generic:
        mu_init = np.full_like(start_mu, 0.5)
    else:
        mu_init = start_mu.copy()

    scorer = make_scorer(mu_init)
    bases = compute_subspace_bases(start_mu)  # bases from EXPERT prior structure
    ca_counts = np.zeros((C, A))

    lc = 0
    all_confs, all_corrects = [], []
    in_sub_energy, total_energy = 0, 0

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

        ai = oa
        n_ca = ca_counts[ci, ai]
        mu_ca = scorer.centroids[ci, ai]
        raw_update = fv - mu_ca

        if strategy == "STANDARD":
            scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
            eff_fv = mu_ca + max(scale, 0.005) * raw_update
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)

        elif strategy == "PROJECTED":
            proj_update = project_update(raw_update, bases, ci)
            scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
            eff_fv = mu_ca + max(scale, 0.005) * proj_update
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)

        elif strategy == "PROJECTED_BOOSTED":
            # Project AND boost by 1/fraction_in_subspace to maintain total energy
            proj_update = project_update(raw_update, bases, ci)
            proj_norm = np.linalg.norm(proj_update)
            raw_norm = np.linalg.norm(raw_update)
            if proj_norm > 0 and raw_norm > 0:
                boost = raw_norm / proj_norm  # restore original magnitude
                proj_update = proj_update * boost
            scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
            eff_fv = mu_ca + max(scale, 0.005) * proj_update
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)

        elif strategy == "GATED":
            if result.confidence <= 0.60:
                scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
                eff_fv = mu_ca + max(scale, 0.005) * raw_update
                scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)

        elif strategy == "GATED_PROJECTED":
            if result.confidence <= 0.60:
                proj_update = project_update(raw_update, bases, ci)
                scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
                eff_fv = mu_ca + max(scale, 0.005) * proj_update
                scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)

        elif strategy == "STATIC":
            pass

        # Track energy
        total_energy += np.linalg.norm(raw_update) ** 2
        proj = project_update(raw_update, bases, ci)
        in_sub_energy += np.linalg.norm(proj) ** 2

        ca_counts[ci, ai] += 1

    confs = np.array(all_confs)
    corrs = np.array(all_corrects)
    return {
        'acc': lc / N_RUN * 100,
        'ece': compute_ece(confs, corrs),
        'sub_frac': in_sub_energy / total_energy * 100 if total_energy > 0 else 0,
    }


def main():
    print("=" * 80)
    print("EXP-H1: SUBSPACE PROJECTION")
    print("Does projecting onto 2D centroid manifold improve accuracy?")
    print("=" * 80)

    base_mu = get_base_centroids()
    strategies = ["STATIC", "STANDARD", "PROJECTED", "PROJECTED_BOOSTED",
                  "GATED", "GATED_PROJECTED"]

    # CALIBRATED PRIOR
    print(f"\n  CALIBRATED PRIOR:")
    print(f"  {'Strategy':>20s}  {'Acc':>6s}  {'ECE':>8s}  {'Sub%':>5s}")
    print(f"  {'-' * 45}")

    for strat in strategies:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_experiment(seed, strat, gt, base_mu)
            runs.append(r)
        acc = np.mean([r['acc'] for r in runs])
        ece = np.mean([r['ece'] for r in runs])
        sub = np.mean([r['sub_frac'] for r in runs])
        print(f"  {strat:>20s}  {acc:5.1f}%  {ece:8.4f}  {sub:4.0f}%")

    # GENERIC PRIOR (cold start)
    print(f"\n  GENERIC PRIOR:")
    print(f"  {'Strategy':>20s}  {'Acc':>6s}")
    print(f"  {'-' * 30}")

    for strat in strategies:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_experiment(seed, strat, gt, base_mu, generic=True)
            runs.append(r)
        acc = np.mean([r['acc'] for r in runs])
        print(f"  {strat:>20s}  {acc:5.1f}%")

    # SEPARATION SWEEP
    print(f"\n  SEPARATION SWEEP (projected vs standard):")
    print(f"  {'Sep':>6s}  {'Static':>7s}  {'Standard':>8s}  {'Projected':>9s}  "
          f"{'Std-Stat':>8s}  {'Proj-Stat':>9s}  {'Proj-Std':>8s}")
    print(f"  {'-' * 65}")

    for sep in [0.25, 0.50, 0.75, 1.00, 1.50]:
        results = {}
        for strat in ["STATIC", "STANDARD", "PROJECTED"]:
            accs = []
            for seed in SEEDS_SHORT:
                gt = build_gt(np.random.default_rng(seed), base_mu)
                rng_s = np.random.default_rng(seed + 3000)
                direction = rng_s.normal(0, 1, gt.shape)
                direction = direction / np.linalg.norm(direction) * sep
                prior = np.clip(gt + direction, 0, 1)
                r = run_experiment(seed, strat, gt, prior)
                accs.append(r['acc'])
            results[strat] = np.mean(accs)

        s, st, p = results["STATIC"], results["STANDARD"], results["PROJECTED"]
        print(f"  {sep:>6.2f}  {s:>5.1f}%  {st:>6.1f}%  {p:>7.1f}%  "
              f"{st-s:>+6.1f}pp  {p-s:>+7.1f}pp  {p-st:>+6.1f}pp")

    print("\nDONE.")


if __name__ == "__main__":
    main()
