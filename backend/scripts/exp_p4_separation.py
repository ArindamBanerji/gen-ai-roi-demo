"""
EXP-P4: GT-PRIOR SEPARATION
==============================
How much does the starting distance from GT determine
the controller's leverage? If the prior is already 95%
correct, there's nothing to learn. If it's 60% correct,
there's room.

Systematically varies the Frobenius distance between
prior and GT, measures landscape gradient and controller
improvement at each distance.

Run: cd backend && python scripts/exp_p4_separation.py
Time: ~20 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

SEEDS_SHORT = [42, 123, 777]
N_RUN = 2000
N_TEST = 1000
SEPARATIONS = [0.0, 0.10, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00]


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


def make_prior_at_distance(gt, distance, seed):
    """Create a prior that's exactly `distance` Frobenius from GT."""
    rng = np.random.default_rng(seed)
    if distance == 0:
        return gt.copy()
    direction = rng.normal(0, 1, gt.shape)
    direction = direction / np.linalg.norm(direction) * distance
    return np.clip(gt + direction, 0, 1)


def measure_accuracy(scorer, gt, seed, N):
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


def run_at_separation(seed, separation, strategy):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(np.random.default_rng(seed), base_mu)
    prior = make_prior_at_distance(gt, separation, seed + 3000)
    scorer = make_scorer(prior)
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

        if strategy == "STATIC":
            pass
        elif strategy == "SQRT_DECAY":
            ai = oa
            n_ca = ca_counts[ci, ai]
            scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
            mu_ca = scorer.centroids[ci, ai]
            eff_fv = mu_ca + max(scale, 0.005) * (fv - mu_ca)
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
            ca_counts[ci, ai] += 1
        elif strategy == "GATED":
            if result.confidence <= 0.60:
                ai = oa
                n_ca = ca_counts[ci, ai]
                scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
                mu_ca = scorer.centroids[ci, ai]
                eff_fv = mu_ca + max(scale, 0.005) * (fv - mu_ca)
                scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
                ca_counts[ci, ai] += 1
        elif strategy == "RAW_SGD":
            scorer.update(fv, ci, result.action_index, correct, oa)

    confs = np.array(all_confs)
    corrs = np.array(all_corrects)
    return {'acc': lc / N_RUN * 100, 'ece': compute_ece(confs, corrs)}


def main():
    print("=" * 80)
    print("EXP-P4: GT-PRIOR SEPARATION")
    print("=" * 80)

    base_mu = get_base_centroids()

    # LANDSCAPE per separation
    print(f"\n{'=' * 80}")
    print("LANDSCAPE: gradient and room-to-improve at each separation")
    print(f"{'=' * 80}")
    print(f"  {'Sep':>6s}  {'BaseAcc':>7s}  {'Conf':>6s}  {'|Deltaacc|@0.05':>11s}  "
          f"{'10%->GT':>7s}  {'50%->GT':>7s}  {'RoomToGT':>8s}")
    print(f"  {'-' * 60}")

    for sep in SEPARATIONS:
        base_accs, base_confs = [], []
        delta_accs = []
        toward_10, toward_50 = [], []

        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            prior = make_prior_at_distance(gt, sep, seed + 3000)
            scorer = make_scorer(prior)
            acc_base, conf_base = measure_accuracy(scorer, gt, seed + 50000, N_TEST)
            base_accs.append(acc_base)
            base_confs.append(conf_base)

            # Random perturbation
            for d in range(3):
                rng_dir = np.random.default_rng(seed * 1000 + d)
                direction = rng_dir.normal(0, 1, prior.shape)
                direction = direction / np.linalg.norm(direction) * 0.05
                scorer_p = make_scorer(prior + direction)
                acc_p, _ = measure_accuracy(scorer_p, gt, seed + 50000, N_TEST)
                delta_accs.append(abs(acc_p - acc_base))

            # Toward GT
            if sep > 0:
                moved10 = prior + 0.10 * (gt - prior)
                scorer10 = make_scorer(moved10)
                a10, _ = measure_accuracy(scorer10, gt, seed + 50000, N_TEST)
                toward_10.append(a10 - acc_base)

                moved50 = prior + 0.50 * (gt - prior)
                scorer50 = make_scorer(moved50)
                a50, _ = measure_accuracy(scorer50, gt, seed + 50000, N_TEST)
                toward_50.append(a50 - acc_base)
            else:
                toward_10.append(0)
                toward_50.append(0)

        room = 100.0 - np.mean(base_accs)
        print(f"  {sep:>6.2f}  {np.mean(base_accs):>5.1f}%  {np.mean(base_confs):>6.4f}  "
              f"{np.mean(delta_accs):>9.2f}pp  {np.mean(toward_10):>+5.1f}pp  "
              f"{np.mean(toward_50):>+5.1f}pp  {room:>6.1f}pp")

    # CONTROLLER LEVERAGE per separation
    print(f"\n{'=' * 80}")
    print("CONTROLLER LEVERAGE at each separation")
    print(f"{'=' * 80}")
    print(f"  {'Sep':>6s}  {'Static':>7s}  {'Gated':>7s}  {'Decay':>7s}  {'Raw':>7s}  "
          f"{'Gated-Stat':>10s}  {'Decay-Stat':>10s}  {'Raw-Stat':>9s}")
    print(f"  {'-' * 75}")

    for sep in SEPARATIONS:
        results = {}
        for strategy in ["STATIC", "GATED", "SQRT_DECAY", "RAW_SGD"]:
            accs = []
            for seed in SEEDS_SHORT:
                r = run_at_separation(seed, sep, strategy)
                accs.append(r['acc'])
            results[strategy] = np.mean(accs)

        s = results["STATIC"]
        g = results["GATED"]
        d = results["SQRT_DECAY"]
        r = results["RAW_SGD"]
        print(f"  {sep:>6.2f}  {s:>5.1f}%  {g:>5.1f}%  {d:>5.1f}%  {r:>5.1f}%  "
              f"{g-s:>+8.1f}pp  {d-s:>+8.1f}pp  {r-s:>+7.1f}pp")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    # At what separation does the controller start helping?
    for sep in SEPARATIONS:
        results = {}
        for strategy in ["STATIC", "SQRT_DECAY"]:
            accs = [run_at_separation(s, sep, strategy)['acc'] for s in SEEDS_SHORT]
            results[strategy] = np.mean(accs)
        if results["SQRT_DECAY"] > results["STATIC"] + 1.0:
            print(f"Q1: Controller starts helping at separation={sep}")
            break
    else:
        print(f"Q1: Controller never helps by >1pp")

    print("\nDONE.")


if __name__ == "__main__":
    main()
