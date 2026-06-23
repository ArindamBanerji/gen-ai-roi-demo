"""
EXP-P1: SOFTMAX TEMPERATURE SWEEP
====================================
The softmax temperature tau controls how "peaked" the confidence
distribution is. High tau -> flat confidences -> informative gradient.
Low tau -> peaked confidences -> blind gradient (what we have now).

C7 showed the landscape is flat and confidence is blind.
Is this because tau is wrong?

Run: cd backend && python scripts/exp_p1_temperature.py
Time: ~20 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_TEST = 2000
N_RUN = 2000
SEEDS_SHORT = [42, 123, 777]
EPSILON_VALUES = [0.01, 0.05, 0.10]


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


class TempScorer:
    """ProfileScorer-like but with adjustable softmax temperature."""

    def __init__(self, centroids, temperature=1.0):
        self.centroids = centroids.copy()
        self.temperature = temperature
        self.C, self.A, self.D = centroids.shape

    def score(self, fv, ci):
        dists = np.array([np.linalg.norm(fv - self.centroids[ci, ai])
                          for ai in range(self.A)])
        # Softmax with temperature: lower temp → more peaked
        logits = -dists ** 2 / self.temperature
        logits -= np.max(logits)  # numerical stability
        probs = np.exp(logits)
        probs /= probs.sum()

        action = int(np.argmax(probs))
        confidence = float(probs[action])

        class Result:
            pass
        r = Result()
        r.action_index = action
        r.confidence = confidence
        r.probabilities = probs.tolist()
        return r

    def update(self, fv, ci, scorer_action, correct, gt_action):
        # Standard SGD update (eta=0.05)
        eta = 0.05
        ai = gt_action
        self.centroids[ci, ai] += eta * (fv - self.centroids[ci, ai])


def measure_landscape(scorer, gt, seed, N):
    """Measure accuracy and mean confidence."""
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
    return correct / N * 100, np.mean(confs), np.std(confs)


def run_with_temp(seed, temperature, gt, base_mu, strategy="STATIC"):
    """Run a full N_RUN simulation with given temperature."""
    rng = np.random.default_rng(seed)
    scorer = TempScorer(base_mu.copy(), temperature)
    lc = 0
    all_confs, all_corrects = [], []
    ca_counts = np.zeros((C, A))

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

        if strategy == "SQRT_DECAY":
            ai = oa
            n_ca = ca_counts[ci, ai]
            scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
            mu_ca = scorer.centroids[ci, ai]
            eff_fv = mu_ca + max(scale, 0.005) * (fv - mu_ca)
            scorer.update(eff_fv, ci, result.action_index, correct, oa)
            ca_counts[ci, ai] += 1
        elif strategy == "GATED":
            if result.confidence <= 0.60:
                ai = oa
                n_ca = ca_counts[ci, ai]
                scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
                mu_ca = scorer.centroids[ci, ai]
                eff_fv = mu_ca + max(scale, 0.005) * (fv - mu_ca)
                scorer.update(eff_fv, ci, result.action_index, correct, oa)
                ca_counts[ci, ai] += 1

    confs = np.array(all_confs)
    corrs = np.array(all_corrects)
    return {
        'acc': lc / N_RUN * 100,
        'ece': compute_ece(confs, corrs),
        'mean_conf': np.mean(confs),
        'pct_above_80': np.mean(confs > 0.80) * 100,
    }


def main():
    print("=" * 80)
    print("EXP-P1: SOFTMAX TEMPERATURE SWEEP")
    print("=" * 80)

    base_mu = get_base_centroids()
    # Note: current ProfileScorer uses τ ≈ 1.0 implicitly
    temperatures = [0.01, 0.05, 0.10, 0.25, 0.50, 1.00, 2.00, 5.00, 10.0]

    # LANDSCAPE ANALYSIS per temperature
    print(f"\n{'=' * 80}")
    print("LANDSCAPE ANALYSIS (C7 repeated at each temperature)")
    print(f"{'=' * 80}")
    print(f"  {'Temp':>6s}  {'BaseAcc':>7s}  {'MeanConf':>8s}  {'%>0.80':>6s}  ", end="")
    for eps in EPSILON_VALUES:
        print(f"{'|Deltaacc|@'+str(eps):>12s}  {'|Deltaconf|@'+str(eps):>13s}  ", end="")
    print(f"{'Gradient':>8s}")
    print(f"  {'-' * 120}")

    for temp in temperatures:
        # Baseline
        accs, confs_mean, confs_std = [], [], []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            scorer = TempScorer(base_mu.copy(), temp)
            a, c, s = measure_landscape(scorer, gt, seed + 50000, N_TEST)
            accs.append(a)
            confs_mean.append(c)
        base_acc = np.mean(accs)
        base_conf = np.mean(confs_mean)
        pct_above_80 = 0

        # Quick pct>0.80 check
        for seed in SEEDS_SHORT[:1]:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            scorer = TempScorer(base_mu.copy(), temp)
            rng = np.random.default_rng(seed + 60000)
            above = 0
            for _ in range(500):
                ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                r = scorer.score(fv, ci)
                if r.confidence > 0.80:
                    above += 1
            pct_above_80 = above / 500 * 100

        print(f"  {temp:>6.2f}  {base_acc:>5.1f}%  {base_conf:>8.4f}  {pct_above_80:>5.0f}%  ", end="")

        # Perturbation sensitivity at each epsilon
        for eps in EPSILON_VALUES:
            delta_accs = []
            delta_confs = []
            for seed in SEEDS_SHORT:
                gt = build_gt(np.random.default_rng(seed), base_mu)
                scorer_base = TempScorer(base_mu.copy(), temp)
                acc_base, conf_base, _ = measure_landscape(scorer_base, gt, seed + 50000, N_TEST)

                for d in range(5):
                    rng_dir = np.random.default_rng(seed * 1000 + d)
                    direction = rng_dir.normal(0, 1, base_mu.shape)
                    direction = direction / np.linalg.norm(direction) * eps
                    scorer_pert = TempScorer(base_mu.copy() + direction, temp)
                    acc_pert, conf_pert, _ = measure_landscape(scorer_pert, gt, seed + 50000, N_TEST)
                    delta_accs.append(abs(acc_pert - acc_base))
                    delta_confs.append(abs(conf_pert - conf_base))

            mean_da = np.mean(delta_accs)
            mean_dc = np.mean(delta_confs)
            print(f"{mean_da:>10.2f}pp  {mean_dc:>11.5f}  ", end="")

        gradient = np.mean(delta_accs) / EPSILON_VALUES[-1] if EPSILON_VALUES[-1] > 0 else 0
        print(f"{gradient:>6.1f}")

    # CONTROLLER PERFORMANCE at different temperatures
    print(f"\n{'=' * 80}")
    print("CONTROLLER PERFORMANCE AT DIFFERENT TEMPERATURES")
    print(f"{'=' * 80}")
    print(f"  {'Temp':>6s}  {'Static':>7s}  {'Gated':>7s}  {'Decay':>7s}  "
          f"{'Gated-Static':>12s}  {'Decay-Static':>12s}")
    print(f"  {'-' * 60}")

    for temp in temperatures:
        static_accs, gated_accs, decay_accs = [], [], []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r_s = run_with_temp(seed, temp, gt, base_mu, "STATIC")
            r_g = run_with_temp(seed, temp, gt, base_mu, "GATED")
            r_d = run_with_temp(seed, temp, gt, base_mu, "SQRT_DECAY")
            static_accs.append(r_s['acc'])
            gated_accs.append(r_g['acc'])
            decay_accs.append(r_d['acc'])

        s = np.mean(static_accs)
        g = np.mean(gated_accs)
        d = np.mean(decay_accs)
        print(f"  {temp:>6.2f}  {s:>5.1f}%  {g:>5.1f}%  {d:>5.1f}%  "
              f"{g-s:>+10.1f}pp  {d-s:>+10.1f}pp")

    # TOWARD-GT perturbation at different temperatures
    print(f"\n{'=' * 80}")
    print("TOWARD-GT PERTURBATION (10% and 50% of distance)")
    print(f"{'=' * 80}")
    print(f"  {'Temp':>6s}  {'Baseline':>8s}  {'10%->GT':>8s}  {'Delta@10%':>7s}  {'50%->GT':>8s}  {'Delta@50%':>7s}")
    print(f"  {'-' * 50}")

    for temp in temperatures:
        baselines, at10, at50 = [], [], []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            scorer = TempScorer(base_mu.copy(), temp)
            b, _, _ = measure_landscape(scorer, gt, seed + 50000, N_TEST)
            baselines.append(b)

            moved10 = base_mu + 0.10 * (gt - base_mu)
            scorer10 = TempScorer(moved10, temp)
            a10, _, _ = measure_landscape(scorer10, gt, seed + 50000, N_TEST)
            at10.append(a10)

            moved50 = base_mu + 0.50 * (gt - base_mu)
            scorer50 = TempScorer(moved50, temp)
            a50, _, _ = measure_landscape(scorer50, gt, seed + 50000, N_TEST)
            at50.append(a50)

        bl = np.mean(baselines)
        t10 = np.mean(at10)
        t50 = np.mean(at50)
        print(f"  {temp:>6.2f}  {bl:>6.1f}%  {t10:>6.1f}%  {t10-bl:>+5.1f}pp  "
              f"{t50:>6.1f}%  {t50-bl:>+5.1f}pp")

    print("\nDONE.")


if __name__ == "__main__":
    main()
