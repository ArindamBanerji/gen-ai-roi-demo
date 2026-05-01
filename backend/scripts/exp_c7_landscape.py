"""
EXP-C7: V-ACCURACY-LANDSCAPE
===============================
Resolves Q1+Q2 from analysis: Is the accuracy landscape flat near
the operating point? Is the confidence signal informative?

Perturbs centroids in random and targeted directions and measures
accuracy response. If d(accuracy)/d(mu) ~ 0, no controller can
improve accuracy. The ceiling is geometric, not controller-limited.

Run: cd backend && python scripts/exp_c7_landscape.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

EPSILON_VALUES = [0.001, 0.005, 0.01, 0.05, 0.10, 0.20, 0.50]
N_TEST = 2000
N_DIRECTIONS = 10  # random perturbation directions per epsilon


def measure_accuracy(scorer, gt, seed, N):
    """Score N random alerts, return accuracy and mean confidence."""
    rng = np.random.default_rng(seed)
    correct = 0
    confs = []
    for _ in range(N):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        result = scorer.score(fv, ci)
        if result.action_index == ta:
            correct += 1
        confs.append(result.confidence)
    return correct / N * 100, np.mean(confs)


def main():
    print("=" * 80)
    print("EXP-C7: V-ACCURACY-LANDSCAPE")
    print("Is the accuracy surface flat near the operating point?")
    print("=" * 80)

    base_mu = get_base_centroids()

    all_gradients = {eps: [] for eps in EPSILON_VALUES}

    for seed in SEEDS[:3]:
        gt = build_gt(np.random.default_rng(seed), base_mu)

        # Baseline accuracy at the expert prior
        scorer_base = make_scorer(base_mu.copy())
        acc_base, conf_base = measure_accuracy(scorer_base, gt, seed + 50000, N_TEST)

        print(f"\n  Seed {seed}: baseline acc={acc_base:.1f}%, conf={conf_base:.4f}")

        for eps in EPSILON_VALUES:
            acc_deltas = []
            conf_deltas = []

            for d in range(N_DIRECTIONS):
                # Random perturbation
                rng_dir = np.random.default_rng(seed * 1000 + d)
                direction = rng_dir.normal(0, 1, base_mu.shape)
                direction = direction / np.linalg.norm(direction) * eps

                perturbed_mu = base_mu.copy() + direction
                scorer_pert = make_scorer(perturbed_mu)
                acc_pert, conf_pert = measure_accuracy(scorer_pert, gt, seed + 50000, N_TEST)

                acc_deltas.append(acc_pert - acc_base)
                conf_deltas.append(conf_pert - conf_base)

            mean_delta_acc = np.mean(np.abs(acc_deltas))
            mean_delta_conf = np.mean(np.abs(conf_deltas))
            gradient_estimate = mean_delta_acc / eps if eps > 0 else 0

            all_gradients[eps].append({
                'delta_acc': mean_delta_acc,
                'delta_conf': mean_delta_conf,
                'gradient': gradient_estimate,
                'max_delta_acc': max(np.abs(acc_deltas)),
            })

    # Results table
    print(f"\n{'=' * 80}")
    print("SENSITIVITY: |d(accuracy)/d(mu)| at different perturbation magnitudes")
    print(f"{'=' * 80}")
    print(f"  {'epsilon':>8s}  {'|delta_acc|':>11s}  {'|delta_conf|':>12s}  "
          f"{'gradient':>10s}  {'max_delta':>10s}")
    print(f"  {'-' * 60}")

    for eps in EPSILON_VALUES:
        data = all_gradients[eps]
        da = np.mean([d['delta_acc'] for d in data])
        dc = np.mean([d['delta_conf'] for d in data])
        gr = np.mean([d['gradient'] for d in data])
        mx = np.mean([d['max_delta_acc'] for d in data])
        print(f"  {eps:>8.3f}  {da:>9.2f}pp  {dc:>10.4f}  {gr:>10.1f}  {mx:>8.2f}pp")

    # Toward GT perturbation
    print(f"\n{'=' * 80}")
    print("TARGETED: Perturbation TOWARD GT (should help accuracy)")
    print(f"{'=' * 80}")

    for seed in SEEDS[:3]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        scorer_base = make_scorer(base_mu.copy())
        acc_base, _ = measure_accuracy(scorer_base, gt, seed + 50000, N_TEST)

        direction_to_gt = gt - base_mu
        dist_to_gt = np.linalg.norm(direction_to_gt)
        direction_to_gt_normalized = direction_to_gt / dist_to_gt

        print(f"\n  Seed {seed}: dist_to_GT={dist_to_gt:.4f}, baseline={acc_base:.1f}%")
        print(f"  {'step':>8s}  {'acc':>6s}  {'delta':>7s}  {'frac_of_dist':>13s}")
        print(f"  {'-' * 40}")

        for frac in [0.01, 0.05, 0.10, 0.20, 0.50, 1.00]:
            step = frac * dist_to_gt
            moved_mu = base_mu + frac * direction_to_gt
            scorer_moved = make_scorer(moved_mu)
            acc_moved, _ = measure_accuracy(scorer_moved, gt, seed + 50000, N_TEST)
            print(f"  {step:>8.4f}  {acc_moved:>5.1f}%  {acc_moved - acc_base:>+5.1f}pp  {frac*100:>11.0f}%")

    # Confidence sensitivity
    print(f"\n{'=' * 80}")
    print("OBSERVABILITY: d(confidence)/d(mu)")
    print(f"{'=' * 80}")

    for eps in [0.01, 0.05, 0.10]:
        data = all_gradients[eps]
        dc = np.mean([d['delta_conf'] for d in data])
        da = np.mean([d['delta_acc'] for d in data])
        ratio = dc / da if da > 0 else 0
        print(f"  eps={eps:.3f}: |delta_conf|={dc:.4f}, |delta_acc|={da:.2f}pp, "
              f"conf_per_acc_pp={ratio:.4f}")

    # MI proxy: does confidence change predict accuracy change direction?
    print(f"\n  Mutual information proxy:")
    for eps in [0.05, 0.10]:
        agreements = 0
        total = 0
        for data in all_gradients[eps]:
            # Not directly available at this level — report gradient ratio instead
            pass
        da = np.mean([d['delta_acc'] for d in all_gradients[eps]])
        dc = np.mean([d['delta_conf'] for d in all_gradients[eps]])
        print(f"  eps={eps}: acc_change={da:.2f}pp conf_change={dc:.4f} "
              f"{'INFORMATIVE' if dc > 0.005 else 'BLIND'}")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    grad_at_01 = np.mean([d['gradient'] for d in all_gradients[0.01]])
    grad_at_05 = np.mean([d['gradient'] for d in all_gradients[0.05]])
    print(f"Q1: Accuracy landscape flat? gradient@0.01={grad_at_01:.1f} "
          f"gradient@0.05={grad_at_05:.1f} "
          f"{'YES (flat)' if grad_at_05 < 5.0 else 'NO (gradient exists)'}")

    dc_01 = np.mean([d['delta_conf'] for d in all_gradients[0.01]])
    print(f"Q2: Confidence informative? delta_conf@0.01={dc_01:.5f} "
          f"{'YES' if dc_01 > 0.001 else 'NO (blind)'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
