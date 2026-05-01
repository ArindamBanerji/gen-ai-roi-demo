"""
EXP-16: V-KENDALL-INVESTIGATION
==================================
Is ranking degradation real or a softmax saturation artifact?

Run: cd backend && python scripts/exp16_kendall.py
Time: ~10 min
"""

import numpy as np
from scipy.stats import kendalltau
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF
)

N = 2000
CHECKPOINTS = [50, 200, 500, 1000, 2000]


def run_kendall(seed, use_pipeline):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)
    scorer = make_scorer()
    pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                   category_weights=CATEGORY_WEIGHTS) if use_pipeline else None

    all_tau_full = []
    all_tau_top2 = []
    all_top1_conf = []
    cp = {}

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)

        if use_pipeline:
            pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)
        else:
            pass  # STATIC

        # Every 10th decision: compute tau
        if n % 10 == 0:
            probs = np.array(result.probabilities)
            gt_dists = np.array([np.linalg.norm(fv - gt[ci, ai]) for ai in range(A)])

            sys_rank = np.argsort(-probs)
            gt_rank = np.argsort(gt_dists)

            tau_full, _ = kendalltau(sys_rank, gt_rank)
            if np.isnan(tau_full): tau_full = 0.0
            all_tau_full.append(tau_full)

            # Top-2 agreement
            top2_agree = 1.0 if sys_rank[0] == gt_rank[0] and sys_rank[1] == gt_rank[1] else 0.0
            all_tau_top2.append(top2_agree)

            all_top1_conf.append(float(np.max(probs)))

        if n in CHECKPOINTS:
            cp[n] = {
                'tau_full': np.mean(all_tau_full) if all_tau_full else 0,
                'tau_top2': np.mean(all_tau_top2) if all_tau_top2 else 0,
                'top1_conf': np.mean(all_top1_conf) if all_top1_conf else 0,
                'max_prob_mean': np.mean(all_top1_conf[-20:]) if len(all_top1_conf) >= 20 else np.mean(all_top1_conf) if all_top1_conf else 0,
            }

    return cp


def main():
    print("=" * 80)
    print("EXP-16: V-KENDALL-INVESTIGATION")
    print("=" * 80)

    for label, use_pipe in [("PIPELINE", True), ("STATIC", False)]:
        all_r = [run_kendall(s, use_pipe) for s in SEEDS]
        print(f"\n  {label}:")
        print(f"  {'N':>6s}  {'tau_full':>8s}  {'top2_agr':>8s}  {'top1_conf':>9s}  {'max_prob':>8s}")
        print(f"  {'-' * 45}")

        for n in CHECKPOINTS:
            tf = np.mean([r[n]['tau_full'] for r in all_r])
            t2 = np.mean([r[n]['tau_top2'] for r in all_r])
            tc = np.mean([r[n]['top1_conf'] for r in all_r])
            mp = np.mean([r[n]['max_prob_mean'] for r in all_r])
            print(f"  {n:>6d}  {tf:>8.4f}  {t2:>8.4f}  {tc:>9.4f}  {mp:>8.4f}")

        if label == "PIPELINE":
            pipe_r = all_r
        else:
            static_r = all_r

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    pipe_conf_50 = np.mean([r[50]['top1_conf'] for r in pipe_r])
    pipe_conf_2000 = np.mean([r[2000]['top1_conf'] for r in pipe_r])
    print(f"Q1: Top-1 conf increases? {pipe_conf_50:.4f} -> {pipe_conf_2000:.4f} "
          f"{'YES' if pipe_conf_2000 > pipe_conf_50 else 'NO'}")

    pipe_top2_50 = np.mean([r[50]['tau_top2'] for r in pipe_r])
    pipe_top2_2000 = np.mean([r[2000]['tau_top2'] for r in pipe_r])
    print(f"Q2: Top-2 agreement stable? {pipe_top2_50:.4f} -> {pipe_top2_2000:.4f} "
          f"{'STABLE' if abs(pipe_top2_2000 - pipe_top2_50) < 0.05 else 'DEGRADING' if pipe_top2_2000 < pipe_top2_50 else 'IMPROVING'}")

    static_tau_50 = np.mean([r[50]['tau_full'] for r in static_r])
    static_tau_2000 = np.mean([r[2000]['tau_full'] for r in static_r])
    print(f"Q3: STATIC tau also degrades? {static_tau_50:.4f} -> {static_tau_2000:.4f} "
          f"{'YES' if static_tau_2000 < static_tau_50 - 0.02 else 'NO'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
