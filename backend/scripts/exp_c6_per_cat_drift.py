"""
EXP-C6: V-PER-CATEGORY-DRIFT
===============================
Additional hypothesis H7: Is raw SGD drift concentrated in the
dominant category, or uniformly distributed?

If credential_access (65%) accounts for >80% of Frobenius drift,
per-category control is the ONLY viable architecture.

Run: cd backend && python scripts/exp_c6_per_cat_drift.py
Time: ~10 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N = 5000
CHECKPOINTS = [500, 1000, 2000, 5000]


def run_drift_analysis(seed, gt, base_mu):
    rng = np.random.default_rng(seed)
    scorer = make_scorer(base_mu.copy())
    initial_mu = base_mu.copy()

    lc = 0
    per_cat_updates = np.zeros(C)
    cp = {}

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc += 1

        scorer.update(fv, ci, result.action_index, correct, oa)
        per_cat_updates[ci] += 1

        if n in CHECKPOINTS:
            # Per-category Frobenius drift from initial
            cat_drifts = {}
            total_drift_sq = 0
            for ci2 in range(C):
                drift = np.linalg.norm(scorer.centroids[ci2] - initial_mu[ci2])
                cat_drifts[ci2] = drift
                total_drift_sq += drift ** 2

            total_drift = np.sqrt(total_drift_sq)

            # Per-category accuracy
            # (approximation: score 100 random alerts per category)
            rng_check = np.random.default_rng(seed + n)
            cat_accs = {}
            for ci2 in range(C):
                correct_check = 0
                for _ in range(100):
                    fv_check = np.clip(rng_check.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                    ta_check = true_action(gt, ci2, fv_check)
                    result_check = scorer.score(fv_check, ci2)
                    if result_check.action_index == ta_check:
                        correct_check += 1
                cat_accs[ci2] = correct_check

            cp[n] = {
                'acc': lc / n * 100,
                'total_drift': total_drift,
                'cat_drifts': cat_drifts,
                'cat_accs': cat_accs,
                'cat_updates': per_cat_updates.copy(),
            }

    return cp


def main():
    print("=" * 80)
    print("EXP-C6: V-PER-CATEGORY-DRIFT (Raw SGD)")
    print("Does drift concentrate in the dominant category?")
    print("=" * 80)

    base_mu = get_base_centroids()
    all_results = [run_drift_analysis(s, build_gt(np.random.default_rng(s), base_mu), base_mu)
                   for s in SEEDS]
    print(f"  {len(SEEDS)} seeds done")

    # Per-category drift at each checkpoint
    for n in CHECKPOINTS:
        print(f"\n  N={n}:")
        print(f"  {'Category':>20s}  {'Vol%':>5s}  {'Drift':>8s}  {'Drift%':>7s}  "
              f"{'Updates':>7s}  {'Acc':>5s}")
        print(f"  {'-' * 60}")

        total_drift_sq = 0
        cat_data = {}
        for ci in range(C):
            drifts = [r[n]['cat_drifts'][ci] for r in all_results]
            updates = [r[n]['cat_updates'][ci] for r in all_results]
            accs = [r[n]['cat_accs'][ci] for r in all_results]
            mean_drift = np.mean(drifts)
            cat_data[ci] = {
                'drift': mean_drift,
                'updates': np.mean(updates),
                'acc': np.mean(accs),
            }
            total_drift_sq += mean_drift ** 2

        total_drift = np.sqrt(total_drift_sq)

        for ci in range(C):
            d = cat_data[ci]
            drift_pct = (d['drift'] ** 2 / total_drift_sq * 100) if total_drift_sq > 0 else 0
            print(f"  {CATEGORIES[ci]:>20s}  {CATEGORY_WEIGHTS[ci]*100:4.0f}%  "
                  f"{d['drift']:>8.4f}  {drift_pct:>5.1f}%  {d['updates']:>5.0f}  "
                  f"{d['acc']:>4.0f}%")

        print(f"  {'TOTAL':>20s}        {total_drift:>8.4f}")

    # H7 test
    print(f"\n{'=' * 80}")
    print("H7 TEST: Does credential_access account for >80% of drift?")
    print("=" * 80)

    n = N
    for ci in range(C):
        drifts = [r[n]['cat_drifts'][ci] for r in all_results]
        mean_drift = np.mean(drifts)
        total_drift_sq_components = sum(
            np.mean([r[n]['cat_drifts'][c] for r in all_results]) ** 2
            for c in range(C)
        )
        pct = mean_drift ** 2 / total_drift_sq_components * 100 if total_drift_sq_components > 0 else 0
        print(f"  {CATEGORIES[ci]:>20s}: {pct:.1f}% of total drift")

    ca_pct = np.mean([r[n]['cat_drifts'][0] for r in all_results]) ** 2
    total_sq = sum(np.mean([r[n]['cat_drifts'][c] for r in all_results]) ** 2 for c in range(C))
    ca_fraction = ca_pct / total_sq * 100 if total_sq > 0 else 0

    print(f"\n  H7: credential_access accounts for {ca_fraction:.1f}% of drift")
    print(f"  {'CONFIRMED' if ca_fraction > 80 else 'REFUTED'}: "
          f"{'Drift IS concentrated' if ca_fraction > 80 else 'Drift is distributed'}")

    # Drift vs volume correlation
    vols = np.array(CATEGORY_WEIGHTS)
    drifts = np.array([np.mean([r[n]['cat_drifts'][ci] for r in all_results]) for ci in range(C)])
    corr = np.corrcoef(vols, drifts)[0, 1]
    print(f"\n  corr(volume, drift) = {corr:+.4f}")
    print(f"  {'Drift proportional to volume' if corr > 0.8 else 'Drift NOT simply volume-proportional'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
