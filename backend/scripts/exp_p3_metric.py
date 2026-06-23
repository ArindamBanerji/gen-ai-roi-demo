"""
EXP-P3: DISTANCE METRIC / SCORING FUNCTION
=============================================
The scoring function maps centroids to decisions. Current:
softmax(-||f - mu||^2). What if the metric is wrong?

Tests: Euclidean, cosine, Mahalanobis, linear (dot product),
and RBF with different bandwidth.

Run: cd backend && python scripts/exp_p3_metric.py
Time: ~20 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic
)

SEEDS_SHORT = [42, 123, 777]
N_RUN = 2000
N_TEST = 1000


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


def score_metric(fv, ci, centroids, metric):
    """Score with different metrics."""
    if metric == "euclidean":
        sims = [-np.linalg.norm(fv - centroids[ci, ai]) ** 2 for ai in range(A)]
    elif metric == "cosine":
        sims = []
        for ai in range(A):
            mu = centroids[ci, ai]
            norm_fv = np.linalg.norm(fv)
            norm_mu = np.linalg.norm(mu)
            if norm_fv > 0 and norm_mu > 0:
                sims.append(np.dot(fv, mu) / (norm_fv * norm_mu))
            else:
                sims.append(0.0)
    elif metric == "dot_product":
        sims = [np.dot(fv, centroids[ci, ai]) for ai in range(A)]
    elif metric == "rbf_narrow":
        gamma = 10.0
        sims = [-gamma * np.linalg.norm(fv - centroids[ci, ai]) ** 2 for ai in range(A)]
    elif metric == "rbf_wide":
        gamma = 0.5
        sims = [-gamma * np.linalg.norm(fv - centroids[ci, ai]) ** 2 for ai in range(A)]
    elif metric == "manhattan":
        sims = [-np.sum(np.abs(fv - centroids[ci, ai])) for ai in range(A)]
    elif metric == "weighted_euclidean":
        # Weight dimensions by inverse variance (approximate Mahalanobis)
        # Use fixed weights: emphasize first 3 dimensions
        weights = np.array([2.0, 2.0, 2.0, 0.5, 0.5, 0.5])
        if len(weights) != D:
            weights = np.ones(D)
        sims = [-np.sum(weights * (fv - centroids[ci, ai]) ** 2) for ai in range(A)]

    sims = np.array(sims, dtype=np.float64)
    sims -= np.max(sims)
    probs = np.exp(sims)
    probs /= probs.sum()
    action = int(np.argmax(probs))
    confidence = float(probs[action])
    return action, confidence, probs


def measure_with_metric(centroids, gt, seed, N, metric):
    rng = np.random.default_rng(seed)
    correct = 0
    confs = []
    for _ in range(N):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        action, conf, _ = score_metric(fv, ci, centroids, metric)
        if action == ta:
            correct += 1
        confs.append(conf)
    return correct / N * 100, np.mean(confs)


def run_with_metric(seed, metric, strategy="SQRT_DECAY"):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(np.random.default_rng(seed), base_mu)
    centroids = base_mu.copy()
    ca_counts = np.zeros((C, A))
    lc = 0
    all_confs, all_corrects = [], []

    for n in range(1, N_RUN + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        action, conf, probs = score_metric(fv, ci, centroids, metric)
        correct = (action == oa)
        if correct: lc += 1
        all_confs.append(conf)
        all_corrects.append(1.0 if correct else 0.0)

        if strategy == "STATIC":
            pass
        elif strategy == "SQRT_DECAY":
            ai = oa
            n_ca = ca_counts[ci, ai]
            scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
            centroids[ci, ai] += max(scale, 0.005) * 0.05 * (fv - centroids[ci, ai])
            ca_counts[ci, ai] += 1
        elif strategy == "GATED":
            if conf <= 0.60:
                ai = oa
                n_ca = ca_counts[ci, ai]
                scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
                centroids[ci, ai] += max(scale, 0.005) * 0.05 * (fv - centroids[ci, ai])
                ca_counts[ci, ai] += 1

    confs = np.array(all_confs)
    corrs = np.array(all_corrects)
    return {'acc': lc / N_RUN * 100, 'ece': compute_ece(confs, corrs),
            'mean_conf': np.mean(confs)}


def main():
    print("=" * 80)
    print("EXP-P3: DISTANCE METRIC / SCORING FUNCTION")
    print("=" * 80)

    metrics = ["euclidean", "cosine", "dot_product", "rbf_narrow",
               "rbf_wide", "manhattan", "weighted_euclidean"]
    base_mu = get_base_centroids()

    # LANDSCAPE per metric
    print(f"\n{'=' * 80}")
    print("LANDSCAPE ANALYSIS per metric")
    print(f"{'=' * 80}")
    print(f"  {'Metric':>18s}  {'BaseAcc':>7s}  {'Conf':>6s}  {'|Deltaacc|@0.05':>11s}  "
          f"{'|Deltaconf|@0.05':>12s}  {'10%->GT':>7s}  {'50%->GT':>7s}")
    print(f"  {'-' * 75}")

    for metric in metrics:
        base_accs, base_confs = [], []
        delta_accs, delta_confs = [], []
        toward_10, toward_50 = [], []

        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            acc_base, conf_base = measure_with_metric(base_mu, gt, seed + 50000, N_TEST, metric)
            base_accs.append(acc_base)
            base_confs.append(conf_base)

            for d in range(5):
                rng_dir = np.random.default_rng(seed * 1000 + d)
                direction = rng_dir.normal(0, 1, base_mu.shape)
                direction = direction / np.linalg.norm(direction) * 0.05
                acc_pert, conf_pert = measure_with_metric(base_mu + direction, gt,
                                                          seed + 50000, N_TEST, metric)
                delta_accs.append(abs(acc_pert - acc_base))
                delta_confs.append(abs(conf_pert - conf_base))

            moved10 = base_mu + 0.10 * (gt - base_mu)
            a10, _ = measure_with_metric(moved10, gt, seed + 50000, N_TEST, metric)
            toward_10.append(a10 - acc_base)

            moved50 = base_mu + 0.50 * (gt - base_mu)
            a50, _ = measure_with_metric(moved50, gt, seed + 50000, N_TEST, metric)
            toward_50.append(a50 - acc_base)

        print(f"  {metric:>18s}  {np.mean(base_accs):>5.1f}%  {np.mean(base_confs):>6.4f}  "
              f"{np.mean(delta_accs):>9.2f}pp  {np.mean(delta_confs):>10.5f}  "
              f"{np.mean(toward_10):>+5.1f}pp  {np.mean(toward_50):>+5.1f}pp")

    # CONTROLLER LEVERAGE per metric
    print(f"\n{'=' * 80}")
    print("CONTROLLER LEVERAGE per metric")
    print(f"{'=' * 80}")
    print(f"  {'Metric':>18s}  {'Static':>7s}  {'Gated':>7s}  {'Decay':>7s}  "
          f"{'Gated-Stat':>10s}  {'Decay-Stat':>10s}")
    print(f"  {'-' * 65}")

    for metric in metrics:
        static_a, gated_a, decay_a = [], [], []
        for seed in SEEDS_SHORT:
            r_s = run_with_metric(seed, metric, "STATIC")
            r_g = run_with_metric(seed, metric, "GATED")
            r_d = run_with_metric(seed, metric, "SQRT_DECAY")
            static_a.append(r_s['acc'])
            gated_a.append(r_g['acc'])
            decay_a.append(r_d['acc'])

        s, g, dd = np.mean(static_a), np.mean(gated_a), np.mean(decay_a)
        print(f"  {metric:>18s}  {s:>5.1f}%  {g:>5.1f}%  {dd:>5.1f}%  "
              f"{g-s:>+8.1f}pp  {dd-s:>+8.1f}pp")

    print("\nDONE.")


if __name__ == "__main__":
    main()
