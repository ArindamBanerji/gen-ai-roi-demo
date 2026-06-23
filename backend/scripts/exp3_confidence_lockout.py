"""
EXP-3: V-CONFIDENCE-LOCKOUT
============================
Question: Does the confidence gate prevent self-correction from a wrong prior?

Run: cd backend && python scripts/exp3_confidence_lockout.py
Time: ~10 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, run_learning_loop,
    K_BATCH, THETA_CONF
)

N = 2000
CHECKPOINTS = [50, 100, 200, 500, 1000, 2000]
WRONG_CAT = 4  # insider_threat
WRONG_SHIFT = 0.3


def make_wrong_prior(base_mu, rng):
    """Shift insider_threat centroids 0.3 Frobenius from correct position."""
    prior = base_mu.copy()
    direction = rng.normal(0, 1, (A, D))
    direction = direction / np.linalg.norm(direction) * WRONG_SHIFT
    prior[WRONG_CAT] += direction
    return np.clip(prior, 0, 1)


def run_lockout_exp(seed, use_pipeline):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)
    wrong_prior = make_wrong_prior(base_mu, np.random.default_rng(seed + 5000))

    scorer = make_scorer(wrong_prior)
    pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                   category_weights=CATEGORY_WEIGHTS) if use_pipeline else None

    wrong_cat_correct = 0
    wrong_cat_total = 0
    other_correct = 0
    other_total = 0
    first_gate_open_n = None
    consecutive_overrides = 0
    max_consecutive = 0
    cp = {}

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)

        if ci == WRONG_CAT:
            wrong_cat_total += 1
            if correct:
                wrong_cat_correct += 1
                consecutive_overrides = 0
            else:
                consecutive_overrides += 1
                max_consecutive = max(max_consecutive, consecutive_overrides)

            # Track when gate first opens for wrong category
            if use_pipeline and first_gate_open_n is None:
                if result.confidence <= THETA_CONF:
                    first_gate_open_n = n
        else:
            other_total += 1
            if correct:
                other_correct += 1

        if use_pipeline:
            pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)
        else:
            scorer.update(fv, ci, result.action_index, correct, oa)

        if n in CHECKPOINTS:
            wc_acc = wrong_cat_correct / wrong_cat_total * 100 if wrong_cat_total > 0 else 0
            oc_acc = other_correct / other_total * 100 if other_total > 0 else 0
            frob = float(np.linalg.norm(scorer.centroids[WRONG_CAT] - gt[WRONG_CAT]))
            cp[n] = {
                'wrong_cat_acc': wc_acc,
                'other_acc': oc_acc,
                'frob_from_gt': frob,
                'wrong_cat_n': wrong_cat_total,
            }

    return {
        'checkpoints': cp,
        'first_gate_open': first_gate_open_n,
        'max_consecutive_overrides': max_consecutive,
        'pipeline_stats': pipeline.stats if pipeline else None,
    }


def main():
    print("=" * 75)
    print("EXP-3: V-CONFIDENCE-LOCKOUT")
    print(f"Wrong category: {CATEGORIES[WRONG_CAT]}, shift: {WRONG_SHIFT} Frobenius")
    print("=" * 75)

    for label, use_pipe in [("LEARN_pipeline", True), ("LEARN_raw", False)]:
        print(f"\n  {label}:")
        print(f"  {'N':>6s}  {'WrongCat%':>9s}  {'OtherCat%':>9s}  {'Frob->GT':>8s}  {'WrongN':>6s}")
        print(f"  {'-' * 50}")

        all_r = [run_lockout_exp(s, use_pipe) for s in SEEDS]

        for n in CHECKPOINTS:
            wc = [r['checkpoints'][n]['wrong_cat_acc'] for r in all_r]
            oc = [r['checkpoints'][n]['other_acc'] for r in all_r]
            fr = [r['checkpoints'][n]['frob_from_gt'] for r in all_r]
            wn = [r['checkpoints'][n]['wrong_cat_n'] for r in all_r]
            print(f"  {n:>6d}  {np.mean(wc):7.1f}%  {np.mean(oc):7.1f}%  "
                  f"{np.mean(fr):7.4f}  {int(np.mean(wn)):>6d}")

        if use_pipe:
            gate_opens = [r['first_gate_open'] for r in all_r]
            max_overrides = [r['max_consecutive_overrides'] for r in all_r]
            print(f"\n  Gate first opens for wrong cat at N: {gate_opens}")
            print(f"  Max consecutive overrides before gate opens: {max_overrides}")
            pipeline_r = all_r

        raw_r = all_r if not use_pipe else None

    # ═══ BINARY QUESTIONS ═══
    print(f"\n{'=' * 75}")
    print("BINARY QUESTIONS")
    print(f"{'=' * 75}")

    pipe_wc_2000 = np.mean([r['checkpoints'][2000]['wrong_cat_acc'] for r in pipeline_r])
    pipe_frob_2000 = np.mean([r['checkpoints'][2000]['frob_from_gt'] for r in pipeline_r])
    pipe_frob_50 = np.mean([r['checkpoints'][50]['frob_from_gt'] for r in pipeline_r])

    # Correction = frob decreases
    corrects_pipe = pipe_frob_2000 < pipe_frob_50

    print(f"Q1: Pipeline corrects wrong category? "
          f"Frob: {pipe_frob_50:.4f}->{pipe_frob_2000:.4f} "
          f"{'YES' if corrects_pipe else 'NO'}")

    if raw_r:
        raw_wc_2000 = np.mean([r['checkpoints'][2000]['wrong_cat_acc'] for r in raw_r])
        raw_frob_2000 = np.mean([r['checkpoints'][2000]['frob_from_gt'] for r in raw_r])
        raw_frob_50 = np.mean([r['checkpoints'][50]['frob_from_gt'] for r in raw_r])
        corrects_raw = raw_frob_2000 < raw_frob_50
        print(f"Q2: Raw SGD corrects wrong category? "
              f"Frob: {raw_frob_50:.4f}->{raw_frob_2000:.4f} "
              f"{'YES' if corrects_raw else 'NO'}")

    gate_opens_valid = [g for g in gate_opens if g is not None]
    if gate_opens_valid:
        print(f"Q3: Overrides before gate opens: {np.mean(max_overrides):.0f} mean")
    else:
        print(f"Q3: Gate NEVER opens for wrong category (confidence stays > {THETA_CONF})")

    print(f"Q4: Wrong cat accuracy at N=2000: pipeline={pipe_wc_2000:.1f}%")

    print("\nDONE.")


if __name__ == "__main__":
    main()
