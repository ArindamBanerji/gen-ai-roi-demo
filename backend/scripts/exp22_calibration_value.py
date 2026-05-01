"""
EXP-22: V-CALIBRATION-VALUE
=============================
What is ECE improvement worth in auto-approve economics?

Run: cd backend && python scripts/exp22_calibration_value.py
Time: ~10 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF
)

N_CONVERGE = 2000
N_TEST = 1000
AUTO_THRESHOLDS = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]


def run_calibration_value(seed, use_pipeline):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)

    scorer = make_scorer()
    pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                   category_weights=CATEGORY_WEIGHTS) if use_pipeline else None

    # Phase 1: Converge
    for n in range(1, N_CONVERGE + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if use_pipeline:
            pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)
        else:
            pass  # STATIC: never update

    # Phase 2: Test auto-approve at various thresholds
    threshold_results = {t: {'total': 0, 'approved': 0, 'approved_correct': 0,
                              'not_approved': 0, 'not_approved_correct': 0}
                         for t in AUTO_THRESHOLDS}

    for n in range(1, N_TEST + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)

        for t in AUTO_THRESHOLDS:
            tr = threshold_results[t]
            tr['total'] += 1
            if result.confidence > t:
                tr['approved'] += 1
                if correct:
                    tr['approved_correct'] += 1
            else:
                tr['not_approved'] += 1
                if correct:
                    tr['not_approved_correct'] += 1

    # Compute precision/recall per threshold
    output = {}
    for t in AUTO_THRESHOLDS:
        tr = threshold_results[t]
        recall = tr['approved'] / tr['total'] if tr['total'] > 0 else 0
        precision = tr['approved_correct'] / tr['approved'] if tr['approved'] > 0 else 0
        false_approve = 1 - precision if tr['approved'] > 0 else 0
        output[t] = {
            'recall': recall * 100,  # % auto-approved
            'precision': precision * 100,  # accuracy on approved
            'false_approve': false_approve * 100,
        }
    return output


def main():
    print("=" * 80)
    print("EXP-22: V-CALIBRATION-VALUE (Auto-Approve Economics)")
    print("=" * 80)

    for label, use_pipe in [("PIPELINE", True), ("STATIC", False)]:
        all_results = [run_calibration_value(s, use_pipe) for s in SEEDS]
        print(f"\n  {label} (after {N_CONVERGE} convergence decisions):")
        print(f"  {'Threshold':>10s}  {'Recall(%)':>10s}  {'Precision(%)':>13s}  {'FalseAppr(%)':>13s}")
        print(f"  {'-' * 50}")

        for t in AUTO_THRESHOLDS:
            recalls = [r[t]['recall'] for r in all_results]
            precs = [r[t]['precision'] for r in all_results]
            fas = [r[t]['false_approve'] for r in all_results]
            print(f"  {t:>10.2f}  {np.mean(recalls):>8.1f}%  {np.mean(precs):>11.1f}%  {np.mean(fas):>11.1f}%")

        if label == "PIPELINE":
            pipe_results = all_results
        else:
            static_results = all_results

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    # Q1: At 95% precision, PIPELINE auto-approves more?
    for t in AUTO_THRESHOLDS:
        pipe_prec = np.mean([r[t]['precision'] for r in pipe_results])
        if pipe_prec >= 95:
            pipe_recall_at_95 = np.mean([r[t]['recall'] for r in pipe_results])
            break
    else:
        pipe_recall_at_95 = 0
        t = None

    for t2 in AUTO_THRESHOLDS:
        static_prec = np.mean([r[t2]['precision'] for r in static_results])
        if static_prec >= 95:
            static_recall_at_95 = np.mean([r[t2]['recall'] for r in static_results])
            break
    else:
        static_recall_at_95 = 0

    gap = pipe_recall_at_95 - static_recall_at_95
    print(f"Q1: At 95% precision: PIPELINE auto-approves {pipe_recall_at_95:.1f}% "
          f"vs STATIC {static_recall_at_95:.1f}% ({'YES' if gap > 0 else 'NO'}, gap={gap:+.1f}pp)")

    # Q2: At 60% recall, which has higher precision?
    for t in AUTO_THRESHOLDS:
        pipe_rec = np.mean([r[t]['recall'] for r in pipe_results])
        if pipe_rec <= 60:
            pipe_prec_at_60 = np.mean([r[t]['precision'] for r in pipe_results])
            break
    else:
        pipe_prec_at_60 = np.mean([r[AUTO_THRESHOLDS[-1]]['precision'] for r in pipe_results])

    for t2 in AUTO_THRESHOLDS:
        stat_rec = np.mean([r[t2]['recall'] for r in static_results])
        if stat_rec <= 60:
            static_prec_at_60 = np.mean([r[t2]['precision'] for r in static_results])
            break
    else:
        static_prec_at_60 = np.mean([r[AUTO_THRESHOLDS[-1]]['precision'] for r in static_results])

    print(f"Q2: At ~60% recall: PIPELINE precision {pipe_prec_at_60:.1f}% "
          f"vs STATIC {static_prec_at_60:.1f}%")

    # Q3/Q4: Threshold for 60% auto-approve with <5% error
    for t in AUTO_THRESHOLDS:
        pipe_rec = np.mean([r[t]['recall'] for r in pipe_results])
        pipe_fa = np.mean([r[t]['false_approve'] for r in pipe_results])
        if pipe_rec >= 60 and pipe_fa < 5:
            print(f"Q3: PIPELINE achieves 60% auto-approve with <5% error at threshold={t}")
            break
    else:
        print(f"Q3: PIPELINE cannot achieve 60% auto-approve with <5% error")

    for t in AUTO_THRESHOLDS:
        stat_rec = np.mean([r[t]['recall'] for r in static_results])
        stat_fa = np.mean([r[t]['false_approve'] for r in static_results])
        if stat_rec >= 60 and stat_fa < 5:
            print(f"Q4: STATIC achieves 60% auto-approve with <5% error at threshold={t}")
            break
    else:
        print(f"Q4: STATIC cannot achieve 60% auto-approve with <5% error (impossible)")

    print("\nDONE.")


if __name__ == "__main__":
    main()
