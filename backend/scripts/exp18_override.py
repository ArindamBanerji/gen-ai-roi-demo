"""
EXP-18: V-OVERRIDE-BYPASS
===========================
Should analyst overrides bypass the confidence gate?

Run: cd backend && python scripts/exp18_override.py
Time: ~10 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF
)

N = 2000
CHECKPOINTS = [50, 200, 500, 1000, 2000]
WRONG_CAT = 4
WRONG_SHIFT = 0.3


def make_wrong_prior(base_mu, rng):
    prior = base_mu.copy()
    direction = rng.normal(0, 1, (A, D))
    direction = direction / np.linalg.norm(direction) * WRONG_SHIFT
    prior[WRONG_CAT] += direction
    return np.clip(prior, 0, 1)


def run_override_test(seed, mode):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)
    wrong_prior = make_wrong_prior(base_mu, np.random.default_rng(seed + 5000))

    scorer = make_scorer(wrong_prior)
    pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                   category_weights=CATEGORY_WEIGHTS)

    # For BOOST mode, use lower threshold for overrides
    THETA_BOOST = 0.30

    wc_correct, wc_total = 0, 0
    other_correct, other_total = 0, 0
    cp = {}

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        is_override = not correct  # analyst disagrees with system

        if ci == WRONG_CAT:
            wc_total += 1
            if correct: wc_correct += 1
        else:
            other_total += 1
            if correct: other_correct += 1

        if mode == "STANDARD":
            pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)
        elif mode == "OVERRIDE_BYPASS":
            if is_override:
                # Override bypasses gate entirely
                pipeline.process(fv, ci, result.action_index, correct, oa, 0.0)  # force through
            else:
                pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)
        elif mode == "OVERRIDE_BOOST":
            if is_override:
                pipeline.process(fv, ci, result.action_index, correct, oa,
                                 min(result.confidence, THETA_BOOST))  # lower threshold
            else:
                pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)

        if n in CHECKPOINTS:
            wc_acc = wc_correct / wc_total * 100 if wc_total > 0 else 0
            oc_acc = other_correct / other_total * 100 if other_total > 0 else 0
            frob = float(np.linalg.norm(scorer.centroids[WRONG_CAT] - gt[WRONG_CAT]))
            cp[n] = {'wc_acc': wc_acc, 'other_acc': oc_acc, 'frob': frob,
                      'updates': pipeline.stats['updates']}

    return cp


def main():
    print("=" * 80)
    print("EXP-18: V-OVERRIDE-BYPASS")
    print(f"Wrong category: {CATEGORIES[WRONG_CAT]}")
    print("=" * 80)

    modes = ["STANDARD", "OVERRIDE_BYPASS", "OVERRIDE_BOOST"]

    for mode in modes:
        all_r = [run_override_test(s, mode) for s in SEEDS]
        print(f"\n  {mode}:")
        print(f"  {'N':>6s}  {'WrongCat%':>9s}  {'OtherCat%':>9s}  {'Frob':>8s}  {'Updates':>7s}")
        print(f"  {'-' * 45}")
        for n in CHECKPOINTS:
            wc = np.mean([r[n]['wc_acc'] for r in all_r])
            oc = np.mean([r[n]['other_acc'] for r in all_r])
            fr = np.mean([r[n]['frob'] for r in all_r])
            up = np.mean([r[n]['updates'] for r in all_r])
            print(f"  {n:>6d}  {wc:>7.1f}%  {oc:>7.1f}%  {fr:>8.4f}  {up:>5.0f}")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    std_r = [run_override_test(s, "STANDARD") for s in SEEDS]
    byp_r = [run_override_test(s, "OVERRIDE_BYPASS") for s in SEEDS]
    bst_r = [run_override_test(s, "OVERRIDE_BOOST") for s in SEEDS]

    std_wc = np.mean([r[N]['wc_acc'] for r in std_r])
    byp_wc = np.mean([r[N]['wc_acc'] for r in byp_r])
    bst_wc = np.mean([r[N]['wc_acc'] for r in bst_r])
    print(f"Q1: Bypass corrects faster? std={std_wc:.1f}% bypass={byp_wc:.1f}% "
          f"{'YES' if byp_wc > std_wc + 1 else 'NO'}")

    std_oc = np.mean([r[N]['other_acc'] for r in std_r])
    byp_oc = np.mean([r[N]['other_acc'] for r in byp_r])
    print(f"Q2: Bypass hurts other categories? std={std_oc:.1f}% bypass={byp_oc:.1f}% "
          f"{'YES' if byp_oc < std_oc - 1 else 'NO'}")

    print(f"Q3: Boost achieves correction? boost={bst_wc:.1f}% vs std={std_wc:.1f}% "
          f"{'YES' if bst_wc > std_wc + 1 else 'NO'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
