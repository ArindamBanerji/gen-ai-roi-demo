"""
EXP-P2: FACTOR DIMENSIONALITY SWEEP
======================================
Does the number of factors (d) control how much accuracy
the centroid tensor can represent?

Current: d=6. If d=24 gives a steeper landscape and more
controller leverage, the bottleneck is representational capacity.

Run: cd backend && python scripts/exp_p2_dimensionality.py
Time: ~25 min
"""

import numpy as np

# We can't use make_scorer at different d values, so we build
# our own minimal scorer.

SEEDS_SHORT = [42, 123, 777]
D_VALUES = [2, 4, 6, 12, 24, 48]
C = 6
A = 4
N_RUN = 2000
N_TEST = 1000

CATEGORY_WEIGHTS = np.array([0.65, 0.12, 0.08, 0.06, 0.05, 0.04])
FREQ_NOISE = {0: 0.08, 1: 0.12, 2: 0.15, 3: 0.18, 4: 0.22, 5: 0.20}
ADJACENT = {0: [1], 1: [0, 2], 2: [1, 3], 3: [2]}


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


def build_gt_d(rng, d):
    """Build ground truth centroids in d dimensions."""
    base = rng.uniform(0.2, 0.8, (C, A, d))
    # Add structure: each category-action pair has a distinct centroid
    for ci in range(C):
        for ai in range(A):
            base[ci, ai] += rng.normal(0, 0.1, d)
    return np.clip(base, 0, 1)


def build_prior_d(gt, rng, shift_frac=0.3):
    """Expert prior shifted from GT."""
    noise = rng.normal(0, 1, gt.shape)
    noise = noise / np.linalg.norm(noise) * shift_frac * np.linalg.norm(gt)
    return np.clip(gt + noise, 0, 1)


def true_action_d(gt, ci, fv):
    dists = [np.linalg.norm(fv - gt[ci, ai]) for ai in range(A)]
    return int(np.argmin(dists))


def noise_realistic_d(gt_a, ci, rng):
    rate = FREQ_NOISE.get(ci, 0.15)
    if rng.random() < rate:
        nbrs = ADJACENT.get(gt_a, [])
        if nbrs:
            return int(rng.choice(nbrs))
        wrong = [a for a in range(A) if a != gt_a]
        return int(rng.choice(wrong))
    return gt_a


def score_d(fv, ci, centroids, temperature=1.0):
    d = centroids.shape[2]
    dists = np.array([np.linalg.norm(fv - centroids[ci, ai]) for ai in range(A)])
    logits = -dists ** 2 / temperature
    logits -= np.max(logits)
    probs = np.exp(logits)
    probs /= probs.sum()
    action = int(np.argmax(probs))
    confidence = float(probs[action])
    return action, confidence, probs


def measure_accuracy_d(centroids, gt, seed, N, d):
    rng = np.random.default_rng(seed)
    correct = 0
    confs = []
    for _ in range(N):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, d), 0, 1).astype(np.float64)
        ta = true_action_d(gt, ci, fv)
        action, conf, _ = score_d(fv, ci, centroids)
        if action == ta:
            correct += 1
        confs.append(conf)
    return correct / N * 100, np.mean(confs)


def run_learning_d(seed, d, strategy):
    rng = np.random.default_rng(seed)
    gt = build_gt_d(np.random.default_rng(seed), d)
    prior = build_prior_d(gt, np.random.default_rng(seed + 1000))
    centroids = prior.copy()
    ca_counts = np.zeros((C, A))

    lc = 0
    all_confs, all_corrects = [], []

    for n in range(1, N_RUN + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, d), 0, 1).astype(np.float64)
        ta = true_action_d(gt, ci, fv)
        oa = noise_realistic_d(ta, ci, rng)
        action, conf, probs = score_d(fv, ci, centroids)
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
            scale = max(scale, 0.005)
            centroids[ci, ai] += scale * 0.05 * (fv - centroids[ci, ai])
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
    return {
        'acc': lc / N_RUN * 100,
        'ece': compute_ece(confs, corrs),
        'mean_conf': np.mean(confs),
    }


def main():
    print("=" * 80)
    print("EXP-P2: FACTOR DIMENSIONALITY SWEEP")
    print("=" * 80)

    # LANDSCAPE ANALYSIS per d
    print(f"\n{'=' * 80}")
    print("LANDSCAPE: gradient magnitude at different d")
    print(f"{'=' * 80}")
    print(f"  {'d':>4s}  {'BaseAcc':>7s}  {'Conf':>6s}  {'|Δacc|@0.05':>11s}  "
          f"{'|Δconf|@0.05':>12s}  {'Gradient':>8s}  {'10%→GT':>7s}  {'50%→GT':>7s}")
    print(f"  {'-' * 80}")

    for d in D_VALUES:
        base_accs, gradients, toward_10, toward_50 = [], [], [], []
        base_confs = []
        delta_accs, delta_confs = [], []

        for seed in SEEDS_SHORT:
            gt = build_gt_d(np.random.default_rng(seed), d)
            prior = build_prior_d(gt, np.random.default_rng(seed + 1000))

            acc_base, conf_base = measure_accuracy_d(prior, gt, seed + 50000, N_TEST, d)
            base_accs.append(acc_base)
            base_confs.append(conf_base)

            # Random perturbation at eps=0.05
            for di in range(5):
                rng_dir = np.random.default_rng(seed * 1000 + di)
                direction = rng_dir.normal(0, 1, prior.shape)
                direction = direction / np.linalg.norm(direction) * 0.05
                acc_pert, conf_pert = measure_accuracy_d(prior + direction, gt, seed + 50000, N_TEST, d)
                delta_accs.append(abs(acc_pert - acc_base))
                delta_confs.append(abs(conf_pert - conf_base))

            # Toward GT
            moved10 = prior + 0.10 * (gt - prior)
            a10, _ = measure_accuracy_d(moved10, gt, seed + 50000, N_TEST, d)
            toward_10.append(a10 - acc_base)

            moved50 = prior + 0.50 * (gt - prior)
            a50, _ = measure_accuracy_d(moved50, gt, seed + 50000, N_TEST, d)
            toward_50.append(a50 - acc_base)

        grad = np.mean(delta_accs) / 0.05
        print(f"  {d:>4d}  {np.mean(base_accs):>5.1f}%  {np.mean(base_confs):>6.4f}  "
              f"{np.mean(delta_accs):>9.2f}pp  {np.mean(delta_confs):>10.5f}  "
              f"{grad:>6.1f}  {np.mean(toward_10):>+5.1f}pp  {np.mean(toward_50):>+5.1f}pp")

    # CONTROLLER LEVERAGE per d
    print(f"\n{'=' * 80}")
    print("CONTROLLER LEVERAGE: does controller help more at higher d?")
    print(f"{'=' * 80}")
    print(f"  {'d':>4s}  {'Static':>7s}  {'Gated':>7s}  {'Decay':>7s}  "
          f"{'Gated-Static':>12s}  {'Decay-Static':>12s}")
    print(f"  {'-' * 55}")

    for d in D_VALUES:
        static_accs, gated_accs, decay_accs = [], [], []
        for seed in SEEDS_SHORT:
            r_s = run_learning_d(seed, d, "STATIC")
            r_g = run_learning_d(seed, d, "GATED")
            r_d = run_learning_d(seed, d, "SQRT_DECAY")
            static_accs.append(r_s['acc'])
            gated_accs.append(r_g['acc'])
            decay_accs.append(r_d['acc'])

        s, g, dd = np.mean(static_accs), np.mean(gated_accs), np.mean(decay_accs)
        print(f"  {d:>4d}  {s:>5.1f}%  {g:>5.1f}%  {dd:>5.1f}%  "
              f"{g-s:>+10.1f}pp  {dd-s:>+10.1f}pp")

    # COLD START per d
    print(f"\n{'=' * 80}")
    print("COLD START: how does d affect learning from scratch?")
    print(f"{'=' * 80}")
    print(f"  {'d':>4s}  {'Decay@200':>9s}  {'Decay@2000':>10s}")
    print(f"  {'-' * 28}")

    for d in D_VALUES:
        accs = []
        for seed in SEEDS_SHORT:
            rng = np.random.default_rng(seed)
            gt = build_gt_d(np.random.default_rng(seed), d)
            generic = np.full((C, A, d), 0.5)
            centroids = generic.copy()
            ca_counts = np.zeros((C, A))
            lc = 0
            cp = {}
            for n in range(1, N_RUN + 1):
                ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng.normal(0.5, 0.15, d), 0, 1).astype(np.float64)
                ta = true_action_d(gt, ci, fv)
                oa = noise_realistic_d(ta, ci, rng)
                action, conf, _ = score_d(fv, ci, centroids)
                correct = (action == oa)
                if correct: lc += 1
                ai = oa
                n_ca = ca_counts[ci, ai]
                scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
                centroids[ci, ai] += max(scale, 0.005) * 0.05 * (fv - centroids[ci, ai])
                ca_counts[ci, ai] += 1
                if n in [200, 2000]:
                    cp[n] = lc / n * 100
            accs.append(cp)
        a200 = np.mean([cp[200] for cp in accs])
        a2000 = np.mean([cp[2000] for cp in accs])
        print(f"  {d:>4d}  {a200:>7.1f}%  {a2000:>8.1f}%")

    print("\nDONE.")


if __name__ == "__main__":
    main()
