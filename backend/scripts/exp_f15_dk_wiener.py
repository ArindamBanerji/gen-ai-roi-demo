"""
EXP-F15: V-DK-WIENER-UNIFICATION
====================================
Key architectural prediction: DK weights (for scoring) and
Wiener gains (for updating) are mathematically related:

  DK weight:    w_i ∝ 1/σ_i²     (weight inversely by noise)
  Wiener gain:  η_i = g_i²/(g_i² + σ_i²)

Both depend on per-dimension noise σ_i². If we learn DK weights
from analyst decisions, we SIMULTANEOUSLY get update gains.

Tests:
  1. DK-for-scoring + uniform-update (standard DK deployment)
  2. DK-for-scoring + DK-derived-update (the unification)
  3. Wiener-for-update + Euclidean-scoring (update only)
  4. Full unification: DK-scoring + Wiener-update

If config 4 > config 1 AND config 4 > config 3:
  the unification IS a single deployment, not two.

Run: cd backend && python scripts/exp_f15_dk_wiener.py
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


def learn_dk_weights_from_data(scorer, gt, seed, N=1000):
    """Learn approximate DK weights from oracle access."""
    rng = np.random.default_rng(seed + 20000)

    # Estimate per-dimension noise variance from factor distribution
    per_dim_sigma2 = np.zeros(D)
    per_dim_counts = np.zeros(D)
    per_dim_signal = np.zeros(D)

    for _ in range(N):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        ai = ta

        noise = fv - gt[ci, ai]  # f - μ*
        signal = gt[ci, ai] - scorer.centroids[ci, ai]  # μ* - μ

        for i in range(D):
            per_dim_sigma2[i] += noise[i] ** 2
            per_dim_signal[i] += signal[i] ** 2
            per_dim_counts[i] += 1

    per_dim_sigma2 /= np.maximum(per_dim_counts, 1)
    per_dim_signal /= np.maximum(per_dim_counts, 1)

    # DK weights: w_i ∝ 1/σ_i² (Mahalanobis)
    dk_weights = 1.0 / np.maximum(per_dim_sigma2, 1e-6)
    dk_weights /= dk_weights.mean()  # normalize

    # Wiener gains: η_i = g_i²/(g_i² + σ_i²)
    snr2 = per_dim_signal / np.maximum(per_dim_sigma2, 1e-6)
    wiener_gains = snr2 / (1 + snr2)

    # DK-derived Wiener gains (from DK weights alone, without signal estimate)
    # If w_i = 1/σ_i², then σ_i² = 1/w_i
    # Wiener gain ≈ η_i ∝ w_i × g_i² (need signal estimate too)
    # Without signal: use dk_weights as relative update gains
    dk_derived_gains = dk_weights / dk_weights.max()

    return {
        'dk_weights': dk_weights,
        'wiener_gains': wiener_gains,
        'dk_derived_gains': dk_derived_gains,
        'sigma2': per_dim_sigma2,
        'signal2': per_dim_signal,
        'snr': np.sqrt(snr2),
    }


def score_dk(fv, ci, centroids, dk_weights):
    """Score with per-dimension weights (DK)."""
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        sims.append(-np.sum(dk_weights * diff ** 2))
    sims = np.array(sims)
    sims -= np.max(sims)
    probs = np.exp(sims)
    probs /= probs.sum()
    action = int(np.argmax(probs))
    confidence = float(probs[action])
    return action, confidence, probs


def run_config(seed, config, gt, start_mu, learned):
    """
    Configs:
      STATIC: no updates
      EUCLID_UNIFORM: Euclidean scoring + uniform η
      DK_UNIFORM: DK scoring + uniform η
      EUCLID_WIENER: Euclidean scoring + Wiener η_i
      DK_WIENER: DK scoring + Wiener η_i (full unification)
      DK_DKDERIVED: DK scoring + DK-derived η_i (without signal estimate)
    """
    rng = np.random.default_rng(seed)
    scorer = make_scorer(start_mu.copy())
    ca_counts = np.zeros((C, A))
    lc = 0
    all_confs, all_corrects = [], []

    use_dk_scoring = config in ["DK_UNIFORM", "DK_WIENER", "DK_DKDERIVED"]
    dk_w = learned['dk_weights'] if use_dk_scoring else np.ones(D)
    update_gains = np.ones(D)
    if config == "EUCLID_WIENER" or config == "DK_WIENER":
        update_gains = learned['wiener_gains']
    elif config == "DK_DKDERIVED":
        update_gains = learned['dk_derived_gains']

    for n in range(1, N_RUN + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        # Score
        if use_dk_scoring:
            action, conf, probs = score_dk(fv, ci, scorer.centroids, dk_w)
        else:
            result = scorer.score(fv, ci)
            action = result.action_index
            conf = result.confidence

        correct = (action == oa)
        if correct: lc += 1
        all_confs.append(conf)
        all_corrects.append(1.0 if correct else 0.0)

        if config == "STATIC":
            pass
        else:
            ai = oa
            n_ca = ca_counts[ci, ai]
            mu_ca = scorer.centroids[ci, ai]
            raw_update = fv - mu_ca
            decay = 1.0 / np.sqrt(1.0 + n_ca / 50.0)

            weighted_update = update_gains * raw_update
            eff_fv = mu_ca + max(decay, 0.005) * weighted_update
            scorer.update(eff_fv.astype(np.float64), ci, action, correct, oa)
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
    print("EXP-F15: V-DK-WIENER-UNIFICATION")
    print("Do DK scoring weights improve update efficiency?")
    print("=" * 90)

    base_mu = get_base_centroids()
    configs = ["STATIC", "EUCLID_UNIFORM", "DK_UNIFORM",
               "EUCLID_WIENER", "DK_WIENER", "DK_DKDERIVED"]

    # CALIBRATED PRIOR
    print(f"\n  CALIBRATED PRIOR:")
    print(f"  {'Config':>15s}  {'Acc':>6s}  {'ECE':>8s}  {'V_final':>8s}  {'Scoring':>10s}  {'Update':>10s}")
    print(f"  {'-' * 65}")

    for config in configs:
        accs, eces, vfs = [], [], []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            scorer_est = make_scorer(base_mu.copy())
            learned = learn_dk_weights_from_data(scorer_est, gt, seed)
            r = run_config(seed, config, gt, base_mu, learned)
            accs.append(r['acc'])
            eces.append(r['ece'])
            vfs.append(r['V_final'])

        acc, ece, vf = np.mean(accs), np.mean(eces), np.mean(vfs)
        scoring = "DK" if "DK" in config else "Euclid"
        updating = "Wiener" if "WIENER" in config else ("DK-der" if "DKDERIVED" in config else "Uniform")
        if config == "STATIC":
            scoring, updating = "—", "—"
        print(f"  {config:>15s}  {acc:>4.1f}%  {ece:>8.4f}  {vf:>8.4f}  {scoring:>10s}  {updating:>10s}")

    # Learned weights analysis
    print(f"\n  LEARNED WEIGHTS ANALYSIS (seed 42):")
    gt = build_gt(np.random.default_rng(42), base_mu)
    scorer_est = make_scorer(base_mu.copy())
    learned = learn_dk_weights_from_data(scorer_est, gt, 42)

    print(f"    Per-dim σ²:         {np.round(learned['sigma2'], 5)}")
    print(f"    Per-dim signal²:    {np.round(learned['signal2'], 5)}")
    print(f"    Per-dim SNR:        {np.round(learned['snr'], 4)}")
    print(f"    DK weights (1/σ²):  {np.round(learned['dk_weights'], 3)}")
    print(f"    Wiener gains:       {np.round(learned['wiener_gains'], 4)}")
    print(f"    DK-derived gains:   {np.round(learned['dk_derived_gains'], 4)}")

    # Correlation between DK weights and Wiener gains
    corr = np.corrcoef(learned['dk_weights'], learned['wiener_gains'])[0, 1]
    print(f"\n    Correlation(DK_weights, Wiener_gains): {corr:+.4f}")
    print(f"    (If high: DK and Wiener are measuring the same thing)")

    # V_final comparison (stability)
    print(f"\n  STABILITY CHECK:")
    print(f"  Config with lowest V_final (most stable) and its accuracy:")
    for config in configs:
        accs, vfs = [], []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            scorer_est = make_scorer(base_mu.copy())
            learned = learn_dk_weights_from_data(scorer_est, gt, seed)
            r = run_config(seed, config, gt, base_mu, learned)
            accs.append(r['acc'])
            vfs.append(r['V_final'])
        print(f"    {config:>15s}: V_final={np.mean(vfs):.4f}, acc={np.mean(accs):.1f}%")

    print(f"\n{'=' * 90}")
    print("BINARY QUESTIONS")
    print("=" * 90)
    print("Q1: DK_WIENER > DK_UNIFORM? (Wiener update helps on top of DK scoring)")
    print("Q2: DK_WIENER > EUCLID_WIENER? (DK scoring helps on top of Wiener update)")
    print("Q3: DK_WIENER > both individual improvements? (synergy)")
    print("Q4: corr(DK_weights, Wiener_gains) > 0.7? (same underlying quantity)")
    print("Q5: DK_WIENER has lower V_final than EUCLID_UNIFORM? (more stable)")

    print("\nDONE.")


if __name__ == "__main__":
    main()
