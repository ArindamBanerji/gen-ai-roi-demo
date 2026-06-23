"""
EXP-F9: V-SIGNAL-DECOMPOSITION
=================================
The foundational signal characterization experiment.
Per-dimension SNR, signal covariance, subspace alignment.
Also includes F10 (dynamics) and F11 (conditioning) as sections.

Run: cd backend && python scripts/exp_f9_signal.py
Time: ~20 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_RUN = 2000
N_EVAL = 500
SEEDS_SHORT = [42, 123, 777]


def compute_signal_stats(records):
    """Compute SNR profile, covariance, subspace from decision records."""
    if len(records) < 10:
        return None

    signals = np.array([r['signal'] for r in records])
    gt_dirs = np.array([r['gt_dir'] for r in records])
    noises = signals - gt_dirs  # n = s - g = (f - mu) - (mu* - mu) = f - mu*

    # Per-dimension SNR
    snr_per_dim = np.zeros(D)
    for i in range(D):
        g_mag = np.mean(np.abs(gt_dirs[:, i]))
        n_std = np.std(noises[:, i])
        snr_per_dim[i] = g_mag / max(n_std, 1e-10)

    # Signal covariance
    sig_cov = np.cov(signals.T) if signals.shape[0] > D else np.eye(D)
    sig_eigenvals = np.linalg.eigvalsh(sig_cov)[::-1]

    # GT covariance
    gt_cov = np.cov(gt_dirs.T) if gt_dirs.shape[0] > D else np.eye(D)
    gt_eigenvals = np.linalg.eigvalsh(gt_cov)[::-1]

    # Subspace alignment (top-2 of signal vs top-2 of GT)
    _, sig_vecs = np.linalg.eigh(sig_cov)
    sig_top2 = sig_vecs[:, -2:]  # top 2 eigenvectors
    _, gt_vecs = np.linalg.eigh(gt_cov)
    gt_top2 = gt_vecs[:, -2:]

    # Subspace alignment: Frobenius inner product of projectors
    P_sig = sig_top2 @ sig_top2.T
    P_gt = gt_top2 @ gt_top2.T
    alignment = np.trace(P_sig @ P_gt) / 2  # normalized to [0, 1]

    # Centroid subspace (from P7)
    # Not available here — compute from base_mu if needed

    # Effective dimensionality
    if sig_eigenvals.sum() > 0:
        p = sig_eigenvals / sig_eigenvals.sum()
        eff_dim = np.exp(-np.sum(p * np.log(p + 1e-10)))
    else:
        eff_dim = 1.0

    return {
        'snr': snr_per_dim,
        'sig_eigenvals': sig_eigenvals,
        'gt_eigenvals': gt_eigenvals,
        'alignment': alignment,
        'eff_dim': eff_dim,
        'n_records': len(records),
        'mean_gt_mag': np.mean([np.linalg.norm(r['gt_dir']) for r in records]),
    }


def main():
    print("=" * 90)
    print("EXP-F9: V-SIGNAL-DECOMPOSITION")
    print("=" * 90)

    base_mu = get_base_centroids()

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        scorer = make_scorer(base_mu.copy())
        rng = np.random.default_rng(seed)

        # Run to convergence, collecting records in windows
        all_records = []
        window_records = {
            'W1 (0-200)': [],
            'W2 (200-500)': [],
            'W3 (500-1000)': [],
            'W4 (1500-2000)': [],
        }

        for n in range(1, N_RUN + 1):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            result = scorer.score(fv, ci)
            correct = (result.action_index == oa)
            is_override = (result.action_index != oa)

            ai = oa  # use oracle action for GT direction
            signal = fv - scorer.centroids[ci, ai]
            gt_dir = gt[ci, ai] - scorer.centroids[ci, ai]

            record = {
                'signal': signal, 'gt_dir': gt_dir,
                'ci': ci, 'ai': ai, 'correct': correct,
                'is_override': is_override,
                'confidence': result.confidence,
                'fv': fv,
            }

            if n <= 200:
                window_records['W1 (0-200)'].append(record)
            elif n <= 500:
                window_records['W2 (200-500)'].append(record)
            elif n <= 1000:
                window_records['W3 (500-1000)'].append(record)
            elif n >= 1500:
                window_records['W4 (1500-2000)'].append(record)
                all_records.append(record)

            scorer.update(fv, ci, result.action_index, correct, oa)

        print(f"\n{'=' * 90}")
        print(f"Seed {seed}")
        print(f"{'=' * 90}")

        # ══ TABLE 1: Per-dimension SNR profile (steady state) ══
        stats = compute_signal_stats(all_records)
        print(f"\n  TABLE 1: Per-dimension SNR profile (N=1500-2000)")
        print(f"  {'Dim':>5s}  {'SNR':>8s}  {'|g_i|':>8s}")
        print(f"  {'-' * 25}")
        for i in range(D):
            g_mag = np.mean([abs(r['gt_dir'][i]) for r in all_records])
            print(f"  {i:>5d}  {stats['snr'][i]:>8.4f}  {g_mag:>8.5f}")
        snr_ratio = max(stats['snr']) / max(min(stats['snr']), 1e-10)
        print(f"\n  SNR concentration: max/min = {snr_ratio:.1f}")
        print(f"  Top-2 SNR fraction: {np.sum(np.sort(stats['snr'])[-2:]**2) / np.sum(stats['snr']**2):.2f}")

        # ══ TABLE 2: Per-category × per-dimension SNR ══
        print(f"\n  TABLE 2: Per-category x per-dimension SNR")
        print(f"  {'Category':>20s}", end="")
        for d in range(D):
            print(f"  {'d'+str(d):>6s}", end="")
        print(f"  {'mean':>6s}")
        print(f"  {'-' * 65}")

        for ci in range(C):
            cat_records = [r for r in all_records if r['ci'] == ci]
            if len(cat_records) < 10:
                continue
            cat_stats = compute_signal_stats(cat_records)
            if cat_stats is None:
                continue
            print(f"  {CATEGORIES[ci]:>20s}", end="")
            for d in range(D):
                print(f"  {cat_stats['snr'][d]:>6.3f}", end="")
            print(f"  {np.mean(cat_stats['snr']):>6.3f}")

        # ══ TABLE 3: Signal covariance eigenspectrum ══
        print(f"\n  TABLE 3: Signal covariance eigenspectrum")
        print(f"  Eigenvalues: {np.round(stats['sig_eigenvals'], 6)}")
        print(f"  Explained:   {np.round(stats['sig_eigenvals'] / stats['sig_eigenvals'].sum() * 100, 1)}%")
        print(f"  Effective dimensionality: {stats['eff_dim']:.2f}")

        # ══ TABLE 4: GT covariance eigenspectrum ══
        print(f"\n  TABLE 4: GT covariance eigenspectrum")
        print(f"  Eigenvalues: {np.round(stats['gt_eigenvals'], 6)}")
        gt_explained = stats['gt_eigenvals'] / max(stats['gt_eigenvals'].sum(), 1e-10)
        print(f"  Explained:   {np.round(gt_explained * 100, 1)}%")

        # ══ TABLE 5: Subspace alignment ══
        print(f"\n  TABLE 5: Subspace alignment")
        print(f"  cos(signal_top2, gt_top2) = {stats['alignment']:.4f}")

        # Centroid subspace alignment
        centered = base_mu.reshape(-1, D) - base_mu.reshape(-1, D).mean(axis=0)
        _, _, Vh = np.linalg.svd(centered, full_matrices=False)
        centroid_top2 = Vh[:2].T
        P_centroid = centroid_top2 @ centroid_top2.T
        _, sig_vecs = np.linalg.eigh(np.cov(np.array([r['signal'] for r in all_records]).T))
        P_sig = sig_vecs[:, -2:] @ sig_vecs[:, -2:].T
        align_centroid = np.trace(P_sig @ P_centroid) / 2
        print(f"  cos(signal_top2, centroid_top2) = {align_centroid:.4f}")

        # ══ SECTION F10: Signal dynamics across windows ══
        print(f"\n  SIGNAL DYNAMICS (F10):")
        print(f"  {'Window':>15s}  {'N':>5s}  {'SNR_mean':>8s}  {'EffDim':>6s}  "
              f"{'|g|_mean':>8s}  {'Alignment':>9s}")
        print(f"  {'-' * 60}")

        for wname, wrecords in window_records.items():
            if len(wrecords) < 10:
                continue
            ws = compute_signal_stats(wrecords)
            if ws:
                print(f"  {wname:>15s}  {ws['n_records']:>5d}  {np.mean(ws['snr']):>8.4f}  "
                      f"{ws['eff_dim']:>6.2f}  {ws['mean_gt_mag']:>8.5f}  {ws['alignment']:>9.4f}")

        # ══ SECTION F11: Signal conditioned on decision type ══
        print(f"\n  CONDITIONED SIGNAL (F11):")

        groups = {
            'CORRECT': [r for r in all_records if r['correct']],
            'INCORRECT': [r for r in all_records if not r['correct']],
            'BOUNDARY (<0.50)': [r for r in all_records if r['confidence'] < 0.50],
            'DEEP (>0.80)': [r for r in all_records if r['confidence'] > 0.80],
            'OVERRIDE': [r for r in all_records if r['is_override']],
            'CONFIRM': [r for r in all_records if not r['is_override']],
            'DOMINANT (cred)': [r for r in all_records if r['ci'] == 0],
            'RARE (ins+cloud)': [r for r in all_records if r['ci'] in [4, 5]],
        }

        print(f"  {'Group':>20s}  {'N':>5s}", end="")
        for d in range(D):
            print(f"  {'SNR_'+str(d):>6s}", end="")
        print(f"  {'mean':>6s}")
        print(f"  {'-' * 70}")

        for gname, grecords in groups.items():
            if len(grecords) < 10:
                gs = None
            else:
                gs = compute_signal_stats(grecords)
            if gs:
                print(f"  {gname:>20s}  {gs['n_records']:>5d}", end="")
                for d in range(D):
                    print(f"  {gs['snr'][d]:>6.3f}", end="")
                print(f"  {np.mean(gs['snr']):>6.3f}")

    # Binary questions
    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("Q1: Is SNR profile concentrated (max/min > 5)?")
    print("Q2: Is SNR profile category-dependent?")
    print("Q3: Signal effective dimensionality?")
    print("Q4: Is signal subspace aligned with GT subspace?")
    print("Q5: Is signal subspace aligned with centroid subspace?")
    print("F10-Q1: Does SNR decrease as centroids converge?")
    print("F10-Q2: Do all dimensions lose SNR equally?")
    print("F11-Q1: Override SNR != confirm SNR?")
    print("F11-Q2: Boundary signal more concentrated than deep?")
    print("F11-Q3: Rare categories higher SNR than dominant?")

    print("\nDONE.")


if __name__ == "__main__":
    main()
