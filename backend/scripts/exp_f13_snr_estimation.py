"""
EXP-F13: V-SNR-ESTIMATION
============================
The Wiener controller needs per-dimension SNR.
In simulation, we compute SNR from GT (oracle).
In production, GT is unknown.

Tests 5 estimation approaches:
  A. Velocity-based: SNR_i proportional to |centroid velocity in dim i| / sigma_i
  B. Override-based: SNR_i from override residuals per dim
  C. Rolling accuracy gradient: perturb dim i, measure acc change
  D. Confidence-conditioned: SNR_i from low-confidence decisions only
  E. Cross-validated: holdout accuracy change per dim perturbation

Measures correlation between estimated SNR and true (oracle) SNR.
If correlation > 0.7: estimation is viable for production.

Run: cd backend && python scripts/exp_f13_snr_estimation.py
Time: ~20 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_RUN = 2000
SEEDS_SHORT = [42, 123, 777]


def compute_oracle_snr(scorer, gt):
    """Oracle SNR from GT (simulation only)."""
    snr = np.zeros(D)
    rng = np.random.default_rng(99999)
    signals, gt_dirs = [], []
    for _ in range(1000):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        ai = ta
        s = fv - scorer.centroids[ci, ai]
        g = gt[ci, ai] - scorer.centroids[ci, ai]
        signals.append(s)
        gt_dirs.append(g)
    signals = np.array(signals)
    gt_dirs = np.array(gt_dirs)
    noises = signals - gt_dirs
    for i in range(D):
        snr[i] = np.mean(np.abs(gt_dirs[:, i])) / max(np.std(noises[:, i]), 1e-10)
    return snr


def main():
    print("=" * 90)
    print("EXP-F13: V-SNR-ESTIMATION")
    print("Can we estimate per-dimension SNR without knowing GT?")
    print("=" * 90)

    base_mu = get_base_centroids()

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        scorer = make_scorer(base_mu.copy())
        rng = np.random.default_rng(seed)

        # Track per-dimension centroid history + override residuals
        centroid_history = {(ci, ai): [base_mu[ci, ai].copy()]
                           for ci in range(C) for ai in range(A)}
        override_residuals = {(ci, ai): [] for ci in range(C) for ai in range(A)}
        low_conf_signals = {(ci, ai): [] for ci in range(C) for ai in range(A)}

        for n in range(1, N_RUN + 1):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            result = scorer.score(fv, ci)
            correct = (result.action_index == oa)

            ai = oa
            signal = fv - scorer.centroids[ci, ai]

            # Record for estimation
            if result.action_index != oa:  # override
                override_residuals[(ci, ai)].append(signal.copy())
            if result.confidence < 0.50:
                low_conf_signals[(ci, ai)].append(signal.copy())

            # Update
            scorer.update(fv, ci, result.action_index, correct, oa)
            centroid_history[(ci, ai)].append(scorer.centroids[ci, ai].copy())

        # ── ORACLE SNR ──
        oracle_snr = compute_oracle_snr(scorer, gt)

        # ── APPROACH A: Velocity-based ──
        vel_snr = np.zeros(D)
        vel_counts = np.zeros(D)
        for key, history in centroid_history.items():
            if len(history) > 10:
                arr = np.array(history)
                velocity = np.abs(np.diff(arr, axis=0))
                noise_est = np.std(arr[-100:], axis=0) if len(arr) > 100 else np.std(arr, axis=0)
                for i in range(D):
                    vel_snr[i] += np.mean(velocity[:, i]) / max(noise_est[i], 1e-10)
                    vel_counts[i] += 1
        vel_snr = vel_snr / np.maximum(vel_counts, 1)

        # ── APPROACH B: Override-based ──
        ovr_snr = np.zeros(D)
        ovr_counts = np.zeros(D)
        for key, residuals in override_residuals.items():
            if len(residuals) > 5:
                arr = np.array(residuals)
                for i in range(D):
                    ovr_snr[i] += abs(np.mean(arr[:, i])) / max(np.std(arr[:, i]), 1e-10)
                    ovr_counts[i] += 1
        ovr_snr = ovr_snr / np.maximum(ovr_counts, 1)

        # ── APPROACH C: Perturbation-based ──
        pert_snr = np.zeros(D)
        rng_pert = np.random.default_rng(seed + 50000)
        test_queries = []
        for _ in range(300):
            ci = int(rng_pert.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_pert.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            test_queries.append((ci, fv, ta))

        for dim in range(D):
            acc_plus, acc_minus = 0, 0
            eps = 0.02
            for ci, fv, ta in test_queries:
                # Perturb centroid in dim
                mu_plus = scorer.centroids.copy()
                mu_minus = scorer.centroids.copy()
                for ai in range(A):
                    mu_plus[ci, ai, dim] += eps
                    mu_minus[ci, ai, dim] -= eps

                s_plus = make_scorer(mu_plus)
                s_minus = make_scorer(mu_minus)
                if s_plus.score(fv, ci).action_index == ta: acc_plus += 1
                if s_minus.score(fv, ci).action_index == ta: acc_minus += 1

            grad = abs(acc_plus - acc_minus) / (2 * eps * len(test_queries))
            pert_snr[dim] = grad

        # ── APPROACH D: Low-confidence signals ──
        lc_snr = np.zeros(D)
        lc_counts = np.zeros(D)
        for key, sigs in low_conf_signals.items():
            if len(sigs) > 5:
                arr = np.array(sigs)
                for i in range(D):
                    lc_snr[i] += abs(np.mean(arr[:, i])) / max(np.std(arr[:, i]), 1e-10)
                    lc_counts[i] += 1
        lc_snr = lc_snr / np.maximum(lc_counts, 1)

        # ── CORRELATIONS WITH ORACLE ──
        estimates = {
            'A_velocity': vel_snr,
            'B_override': ovr_snr,
            'C_perturbation': pert_snr,
            'D_low_conf': lc_snr,
        }

        print(f"\n  Seed {seed}:")
        print(f"\n  Oracle SNR per dim: {np.round(oracle_snr, 4)}")
        print(f"\n  {'Approach':>15s}  {'Estimated SNR':>50s}  {'Corr':>6s}  {'Rank_corr':>9s}")
        print(f"  {'-' * 85}")

        for name, est in estimates.items():
            # Normalize for comparison
            est_norm = est / max(est.max(), 1e-10) * oracle_snr.max()
            corr = np.corrcoef(oracle_snr, est_norm)[0, 1] if np.std(est_norm) > 0 else 0

            # Rank correlation (Spearman)
            rank_oracle = np.argsort(np.argsort(oracle_snr))
            rank_est = np.argsort(np.argsort(est_norm))
            rank_corr = np.corrcoef(rank_oracle, rank_est)[0, 1] if np.std(rank_est) > 0 else 0

            print(f"  {name:>15s}  {np.round(est_norm, 4)}  {corr:>+6.3f}  {rank_corr:>+9.3f}")

        # ── WIENER GAINS FROM ESTIMATES ──
        print(f"\n  Wiener gains from each estimator:")
        print(f"  {'Approach':>15s}  {'Wiener gains':>50s}")
        print(f"  {'-' * 70}")

        oracle_wiener = oracle_snr ** 2 / (1 + oracle_snr ** 2)
        print(f"  {'ORACLE':>15s}  {np.round(oracle_wiener, 4)}")

        for name, est in estimates.items():
            est_norm = est / max(est.max(), 1e-10) * oracle_snr.max()
            wiener = est_norm ** 2 / (1 + est_norm ** 2)
            print(f"  {name:>15s}  {np.round(wiener, 4)}")

    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("Q1: Any estimator correlation > 0.7 with oracle?")
    print("Q2: Which estimator is best?")
    print("Q3: Do Wiener gains from estimates ~= oracle Wiener gains?")
    print("Q4: Is rank correlation better than Pearson? (captures ordering even if scale wrong)")

    print("\nDONE.")


if __name__ == "__main__":
    main()
