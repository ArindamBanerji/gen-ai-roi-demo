"""
EXP-2: V-CONFIDENCE-CALIBRATION
================================
Question: Does centroid learning improve the system BEYOND accuracy?
Measures: ECE, confidence separation, Kendall's tau rank agreement.

Run: cd backend && python scripts/exp2_confidence_cal.py
Time: ~10 min
"""

import numpy as np
from scipy.stats import kendalltau
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, SIGMA_BAR, K_BATCH, THETA_CONF
)

N = 2000
CHECKPOINTS = [50, 200, 500, 1000, 2000]


def compute_ece(confidences, corrects, n_bins=10):
    """Expected Calibration Error."""
    bin_bounds = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    total = len(confidences)
    if total == 0:
        return 0.0
    for i in range(n_bins):
        lo, hi = bin_bounds[i], bin_bounds[i + 1]
        mask = (confidences >= lo) & (confidences < hi)
        if i == n_bins - 1:
            mask = (confidences >= lo) & (confidences <= hi)
        count = mask.sum()
        if count == 0:
            continue
        bin_acc = corrects[mask].mean()
        bin_conf = confidences[mask].mean()
        ece += (count / total) * abs(bin_acc - bin_conf)
    return ece


def compute_kendall_tau(scorer, gt, fv, ci):
    """Kendall's tau between system's action ranking and GT ranking."""
    # System's probability ranking
    result = scorer.score(fv, ci)
    sys_probs = np.array(result.probabilities)

    # GT ranking: distance to GT centroids (smaller = better = higher rank)
    gt_dists = np.array([np.linalg.norm(fv - gt[ci, ai]) for ai in range(A)])
    gt_rank = np.argsort(gt_dists)  # closest first

    # System rank: highest probability first
    sys_rank = np.argsort(-sys_probs)

    tau, _ = kendalltau(sys_rank, gt_rank)
    return tau if not np.isnan(tau) else 0.0


def run_calibration_exp(seed, use_pipeline=True):
    """Run one seed, return metrics at each checkpoint."""
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)
    scorer = make_scorer()
    pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                   category_weights=CATEGORY_WEIGHTS) if use_pipeline else None

    all_conf = []
    all_correct = []
    all_tau = []
    metrics = {}

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)

        all_conf.append(result.confidence)
        all_correct.append(1.0 if correct else 0.0)

        # Kendall's τ (sample every 10th to save time)
        if n % 10 == 0:
            tau = compute_kendall_tau(scorer, gt, fv, ci)
            all_tau.append(tau)

        # Update
        if use_pipeline:
            pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)
        else:
            scorer.update(fv, ci, result.action_index, correct, oa)

        if n in CHECKPOINTS:
            confs = np.array(all_conf)
            corrs = np.array(all_correct)

            correct_mask = corrs == 1.0
            incorrect_mask = corrs == 0.0

            mean_conf_correct = confs[correct_mask].mean() if correct_mask.sum() > 0 else 0
            mean_conf_incorrect = confs[incorrect_mask].mean() if incorrect_mask.sum() > 0 else 0

            metrics[n] = {
                'accuracy': corrs.mean() * 100,
                'ece': compute_ece(confs, corrs),
                'mean_conf_correct': mean_conf_correct,
                'mean_conf_incorrect': mean_conf_incorrect,
                'conf_separation': mean_conf_correct - mean_conf_incorrect,
                'kendall_tau': np.mean(all_tau) if all_tau else 0.0,
            }

    return metrics


def main():
    print("=" * 75)
    print("EXP-2: V-CONFIDENCE-CALIBRATION")
    print("=" * 75)

    for label, use_pipe in [("LEARN_pipeline", True), ("STATIC_baseline", False)]:
        print(f"\n{'=' * 75}")
        print(f"STRATEGY: {label}")
        print(f"{'=' * 75}")

        all_metrics = [run_calibration_exp(s, use_pipeline=(label == "LEARN_pipeline"))
                       for s in SEEDS]

        print(f"  {'N':>6s}  {'Acc':>6s}  {'ECE':>6s}  {'Conf|C':>7s}  {'Conf|W':>7s}  {'Sep':>6s}  {'tau':>6s}")
        print(f"  {'-' * 55}")

        for n in CHECKPOINTS:
            accs = [m[n]['accuracy'] for m in all_metrics]
            eces = [m[n]['ece'] for m in all_metrics]
            cc = [m[n]['mean_conf_correct'] for m in all_metrics]
            ci = [m[n]['mean_conf_incorrect'] for m in all_metrics]
            sep = [m[n]['conf_separation'] for m in all_metrics]
            tau = [m[n]['kendall_tau'] for m in all_metrics]

            print(f"  {n:>6d}  {np.mean(accs):5.1f}%  {np.mean(eces):.4f}  "
                  f"{np.mean(cc):.4f}  {np.mean(ci):.4f}  {np.mean(sep):.4f}  "
                  f"{np.mean(tau):.4f}")

        # Store for binary questions
        if label == "LEARN_pipeline":
            learn_metrics = all_metrics
        else:
            static_metrics = all_metrics

    # ═══ BINARY QUESTIONS ═══
    print(f"\n{'=' * 75}")
    print("BINARY QUESTIONS")
    print(f"{'=' * 75}")

    # Q1: ECE decreases N=50 → N=2000?
    ece_50 = np.mean([m[50]['ece'] for m in learn_metrics])
    ece_2000 = np.mean([m[2000]['ece'] for m in learn_metrics])
    print(f"Q1: ECE at N=50: {ece_50:.4f}, N=2000: {ece_2000:.4f}")
    print(f"    Decreases? {'YES' if ece_2000 < ece_50 else 'NO'} (Delta={ece_2000 - ece_50:.4f})")

    # Q2: Confidence separation increases?
    sep_50 = np.mean([m[50]['conf_separation'] for m in learn_metrics])
    sep_2000 = np.mean([m[2000]['conf_separation'] for m in learn_metrics])
    print(f"Q2: Separation at N=50: {sep_50:.4f}, N=2000: {sep_2000:.4f}")
    print(f"    Increases? {'YES' if sep_2000 > sep_50 else 'NO'} (Delta={sep_2000 - sep_50:.4f})")

    # Q3: Kendall's τ increases?
    tau_50 = np.mean([m[50]['kendall_tau'] for m in learn_metrics])
    tau_2000 = np.mean([m[2000]['kendall_tau'] for m in learn_metrics])
    print(f"Q3: tau at N=50: {tau_50:.4f}, N=2000: {tau_2000:.4f}")
    print(f"    Increases? {'YES' if tau_2000 > tau_50 else 'NO'} (Delta={tau_2000 - tau_50:.4f})")

    # Q4: Q1-Q3 improve between N=500 and N=2000 (plateau region)?
    ece_500 = np.mean([m[500]['ece'] for m in learn_metrics])
    sep_500 = np.mean([m[500]['conf_separation'] for m in learn_metrics])
    tau_500 = np.mean([m[500]['kendall_tau'] for m in learn_metrics])
    ece_improves = ece_2000 < ece_500
    sep_improves = sep_2000 > sep_500
    tau_improves = tau_2000 > tau_500
    any_improve = ece_improves or sep_improves or tau_improves
    print(f"Q4: In plateau (N=500->2000): ECE improves={ece_improves}, "
          f"Sep improves={sep_improves}, tau improves={tau_improves}")
    print(f"    Any improve? {'YES' if any_improve else 'NO'}")

    # Q5: LEARN ECE < STATIC ECE at N=2000?
    learn_ece = np.mean([m[2000]['ece'] for m in learn_metrics])
    static_ece = np.mean([m[2000]['ece'] for m in static_metrics])
    print(f"Q5: LEARN ECE={learn_ece:.4f}, STATIC ECE={static_ece:.4f}")
    print(f"    LEARN < STATIC? {'YES' if learn_ece < static_ece else 'NO'} "
          f"(Delta={learn_ece - static_ece:.4f})")

    print("\nDONE.")


if __name__ == "__main__":
    main()
