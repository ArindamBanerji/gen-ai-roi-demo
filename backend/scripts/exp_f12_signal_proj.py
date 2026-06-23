"""
EXP-F12: V-SIGNAL-PROJECTION
===============================
H1 showed centroid-subspace projection fails catastrophically.
Does SIGNAL-subspace projection work?
Does per-dimension SNR weighting (Wiener gains) work?

Computes signal subspace internally from GT (oracle) and
tests whether signal-aware updates outperform uniform updates.

Run: cd backend && python scripts/exp_f12_signal_proj.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_CALIBRATE = 500  # decisions to estimate signal subspace
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


def estimate_signal_subspace(scorer, gt, seed, N):
    """Estimate signal subspace from GT (oracle access in simulation)."""
    rng = np.random.default_rng(seed + 40000)
    signals = []
    gt_dirs = []

    for _ in range(N):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        ai = ta
        signal = fv - scorer.centroids[ci, ai]
        gt_dir = gt[ci, ai] - scorer.centroids[ci, ai]
        signals.append(signal)
        gt_dirs.append(gt_dir)

    signals = np.array(signals)
    gt_dirs = np.array(gt_dirs)
    noises = signals - gt_dirs

    # Per-dimension SNR
    snr = np.zeros(D)
    for i in range(D):
        g_mag = np.mean(np.abs(gt_dirs[:, i]))
        n_std = np.std(noises[:, i])
        snr[i] = g_mag / max(n_std, 1e-10)

    # Signal covariance eigenvectors
    sig_cov = np.cov(signals.T)
    eigenvals, eigenvecs = np.linalg.eigh(sig_cov)
    # Sort descending
    idx = np.argsort(eigenvals)[::-1]
    eigenvals = eigenvals[idx]
    eigenvecs = eigenvecs[:, idx]

    # GT covariance eigenvectors
    gt_cov = np.cov(gt_dirs.T)
    gt_eigenvals, gt_eigenvecs = np.linalg.eigh(gt_cov)
    gt_idx = np.argsort(gt_eigenvals)[::-1]
    gt_eigenvecs = gt_eigenvecs[:, gt_idx]

    # Centroid subspace
    centered = scorer.centroids.reshape(-1, D) - scorer.centroids.reshape(-1, D).mean(axis=0)
    _, _, Vh = np.linalg.svd(centered, full_matrices=False)
    centroid_vecs = Vh[:2].T

    return {
        'snr': snr,
        'signal_vecs': eigenvecs,
        'gt_vecs': gt_eigenvecs,
        'centroid_vecs': centroid_vecs,
    }


def run_with_projection(seed, strategy, gt, start_mu, sub_info=None, generic=False):
    """Run centroid learning with different projection strategies."""
    rng = np.random.default_rng(seed)
    if generic:
        mu_init = np.full_like(start_mu, 0.5)
    else:
        mu_init = start_mu.copy()
    scorer = make_scorer(mu_init)
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

        ai = oa
        n_ca = ca_counts[ci, ai]
        mu_ca = scorer.centroids[ci, ai]
        raw_update = fv - mu_ca
        decay = 1.0 / np.sqrt(1.0 + n_ca / 50.0)

        if strategy == "UNPROJECTED":
            update = raw_update
            eff_fv = mu_ca + max(decay, 0.005) * update
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)

        elif strategy == "SIGNAL_PROJ_K2" and sub_info:
            V = sub_info['signal_vecs'][:, :2]  # top 2
            proj = V @ (V.T @ raw_update)
            eff_fv = mu_ca + max(decay, 0.005) * proj
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)

        elif strategy == "SIGNAL_PROJ_K3" and sub_info:
            V = sub_info['signal_vecs'][:, :3]
            proj = V @ (V.T @ raw_update)
            eff_fv = mu_ca + max(decay, 0.005) * proj
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)

        elif strategy == "GT_PROJ_K2" and sub_info:
            V = sub_info['gt_vecs'][:, :2]  # oracle
            proj = V @ (V.T @ raw_update)
            eff_fv = mu_ca + max(decay, 0.005) * proj
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)

        elif strategy == "CENTROID_PROJ_K2" and sub_info:
            V = sub_info['centroid_vecs']  # (D, 2)
            proj = V @ (V.T @ raw_update)
            eff_fv = mu_ca + max(decay, 0.005) * proj
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)

        elif strategy == "PER_DIM_WIENER" and sub_info:
            # Wiener gains: η_i = SNR_i² / (1 + SNR_i²)
            snr = sub_info['snr']
            wiener_gains = snr ** 2 / (1 + snr ** 2)
            weighted_update = wiener_gains * raw_update
            eff_fv = mu_ca + max(decay, 0.005) * weighted_update
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)

        elif strategy == "PER_DIM_SNR_SCALED" and sub_info:
            # Scale each dimension by SNR (not Wiener — simpler)
            snr = sub_info['snr']
            snr_norm = snr / max(snr.max(), 1e-10)
            scaled_update = snr_norm * raw_update
            eff_fv = mu_ca + max(decay, 0.005) * scaled_update
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)

        elif strategy == "STATIC":
            pass

        else:
            # Fallback
            update = raw_update
            eff_fv = mu_ca + max(decay, 0.005) * update
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)

        ca_counts[ci, ai] += 1

    confs = np.array(all_confs)
    corrs = np.array(all_corrects)
    V_final = float(np.sum((scorer.centroids - gt) ** 2))
    return {
        'acc': lc / N_RUN * 100,
        'ece': compute_ece(confs, corrs),
        'V_final': V_final,
    }


def main():
    print("=" * 90)
    print("EXP-F12: V-SIGNAL-PROJECTION")
    print("Does SIGNAL-subspace projection beat centroid-subspace projection?")
    print("=" * 90)

    base_mu = get_base_centroids()
    strategies = ["STATIC", "UNPROJECTED", "SIGNAL_PROJ_K2", "SIGNAL_PROJ_K3",
                  "GT_PROJ_K2", "CENTROID_PROJ_K2",
                  "PER_DIM_WIENER", "PER_DIM_SNR_SCALED"]

    # CALIBRATED PRIOR
    print(f"\n{'=' * 90}")
    print("CALIBRATED PRIOR")
    print(f"{'=' * 90}")
    print(f"  {'Strategy':>20s}  {'Acc':>6s}  {'ECE':>8s}  {'V_final':>8s}  {'Delta vs unproj':>11s}")
    print(f"  {'-' * 60}")

    unproj_acc = 0
    for strat in strategies:
        accs, eces, vfs = [], [], []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            # Estimate subspaces
            scorer_est = make_scorer(base_mu.copy())
            sub_info = estimate_signal_subspace(scorer_est, gt, seed, N_CALIBRATE)
            r = run_with_projection(seed, strat, gt, base_mu, sub_info)
            accs.append(r['acc'])
            eces.append(r['ece'])
            vfs.append(r['V_final'])

        acc = np.mean(accs)
        ece = np.mean(eces)
        vf = np.mean(vfs)
        if strat == "UNPROJECTED":
            unproj_acc = acc
        delta = acc - unproj_acc if unproj_acc > 0 else 0
        print(f"  {strat:>20s}  {acc:>4.1f}%  {ece:>8.4f}  {vf:>8.4f}  {delta:>+9.1f}pp")

    # GENERIC PRIOR
    print(f"\n{'=' * 90}")
    print("GENERIC PRIOR (cold start)")
    print(f"{'=' * 90}")
    print(f"  {'Strategy':>20s}  {'Acc':>6s}")
    print(f"  {'-' * 30}")

    for strat in strategies:
        accs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            scorer_est = make_scorer(base_mu.copy())
            sub_info = estimate_signal_subspace(scorer_est, gt, seed, N_CALIBRATE)
            r = run_with_projection(seed, strat, gt, base_mu, sub_info, generic=True)
            accs.append(r['acc'])
        print(f"  {strat:>20s}  {np.mean(accs):>4.1f}%")

    # SEPARATION SWEEP
    print(f"\n{'=' * 90}")
    print("SEPARATION SWEEP (key strategies)")
    print(f"{'=' * 90}")
    key_strats = ["STATIC", "UNPROJECTED", "PER_DIM_WIENER", "GT_PROJ_K2"]
    print(f"  {'Sep':>6s}", end="")
    for s in key_strats:
        print(f"  {s[:12]:>12s}", end="")
    print()
    print(f"  {'-' * 60}")

    for sep in [0.50, 0.75, 1.00, 1.50]:
        results = {}
        for strat in key_strats:
            accs = []
            for seed in SEEDS_SHORT:
                gt = build_gt(np.random.default_rng(seed), base_mu)
                rng_s = np.random.default_rng(seed + 3000)
                direction = rng_s.normal(0, 1, gt.shape)
                direction = direction / np.linalg.norm(direction) * sep
                prior = np.clip(gt + direction, 0, 1)
                scorer_est = make_scorer(prior)
                sub_info = estimate_signal_subspace(scorer_est, gt, seed, N_CALIBRATE)
                r = run_with_projection(seed, strat, gt, prior, sub_info)
                accs.append(r['acc'])
            results[strat] = np.mean(accs)
        print(f"  {sep:>6.2f}", end="")
        for s in key_strats:
            print(f"  {results[s]:>10.1f}%", end="")
        print()

    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("Q1: Does SIGNAL_PROJ_K2 beat UNPROJECTED?")
    print("Q2: Does PER_DIM_WIENER beat UNPROJECTED?")
    print("Q3: Does GT_PROJ_K2 (oracle) substantially beat SIGNAL_PROJ_K2?")
    print("Q4: Does CENTROID_PROJ_K2 still fail (confirming H1)?")
    print("Q5: For GENERIC prior: does signal projection help cold start?")

    print("\nDONE.")


if __name__ == "__main__":
    main()
