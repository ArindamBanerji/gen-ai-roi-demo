"""
EXP-P5: PLANT-CONTROLLER INTERACTION
=======================================
The key experiment: combine plant variations (temperature,
dimensionality, metric) WITH the winning controller to find
which plant configuration gives the most controller leverage.

If changing the plant makes the controller 10× more effective,
the plant was the bottleneck all along.

Run: cd backend && python scripts/exp_p5_interaction.py
Time: ~30 min
"""

import numpy as np
from collections import deque
from exp_shared import (
    C, A, D, CATEGORIES, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
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


class PlantConfig:
    """Configurable plant with different scoring properties."""

    def __init__(self, temperature=1.0, metric="euclidean",
                 d_override=None, noise_scale=1.0):
        self.temperature = temperature
        self.metric = metric
        self.d_override = d_override  # None = use standard D
        self.noise_scale = noise_scale
        self.d_eff = d_override if d_override else D

    def score(self, fv, ci, centroids):
        """Score with this plant configuration."""
        if self.metric == "euclidean":
            sims = [-np.linalg.norm(fv - centroids[ci, ai]) ** 2
                     for ai in range(A)]
        elif self.metric == "cosine":
            sims = []
            for ai in range(A):
                mu = centroids[ci, ai]
                n1, n2 = np.linalg.norm(fv), np.linalg.norm(mu)
                sims.append(np.dot(fv, mu) / (n1 * n2) if n1 > 0 and n2 > 0 else 0)
        elif self.metric == "rbf_narrow":
            sims = [-10.0 * np.linalg.norm(fv - centroids[ci, ai]) ** 2
                     for ai in range(A)]

        sims = np.array(sims, dtype=np.float64) / self.temperature
        sims -= np.max(sims)
        probs = np.exp(sims)
        probs /= probs.sum()
        action = int(np.argmax(probs))
        confidence = float(probs[action])
        return action, confidence, probs


def run_plant_controller(seed, plant, strategy, gt=None, prior=None):
    """Run with given plant config and controller strategy."""
    rng = np.random.default_rng(seed)
    d = plant.d_eff
    base_mu = get_base_centroids()

    if gt is None:
        gt = build_gt(np.random.default_rng(seed), base_mu)
    if prior is None:
        prior = base_mu.copy()

    # Truncate/extend to match d if needed
    if d != D:
        gt_d = np.random.default_rng(seed + 8000).uniform(0.2, 0.8, (C, A, d))
        # Add structure
        for ci in range(C):
            for ai in range(A):
                gt_d[ci, ai] += np.random.default_rng(seed + ci * A + ai).normal(0, 0.1, d)
        gt_d = np.clip(gt_d, 0, 1)
        prior_d = gt_d + np.random.default_rng(seed + 9000).normal(0, 0.05, gt_d.shape)
        prior_d = np.clip(prior_d, 0, 1)
        gt = gt_d
        prior = prior_d

    centroids = prior.copy()
    ca_counts = np.zeros((C, A))
    override_windows = {ci: deque(maxlen=50) for ci in range(C)}
    mode = {ci: "LEARN" for ci in range(C)}

    lc = 0
    all_confs, all_corrects = [], []

    for n in range(1, N_RUN + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, d), 0, 1).astype(np.float64)

        # True action using plant's metric
        dists = [np.linalg.norm(fv - gt[ci, ai]) for ai in range(A)]
        ta = int(np.argmin(dists))

        # Oracle noise
        noise_rate = {0: 0.08, 1: 0.12, 2: 0.15, 3: 0.18, 4: 0.22, 5: 0.20}.get(ci, 0.15)
        noise_rate *= plant.noise_scale
        adj = {0: [1], 1: [0, 2], 2: [1, 3], 3: [2]}
        if rng.random() < noise_rate:
            nbrs = adj.get(ta, [])
            oa = int(rng.choice(nbrs)) if nbrs else int(rng.choice([a for a in range(A) if a != ta]))
        else:
            oa = ta

        action, conf, probs = plant.score(fv, ci, centroids)
        correct = (action == oa)
        if correct: lc += 1
        all_confs.append(conf)
        all_corrects.append(1.0 if correct else 0.0)
        override_windows[ci].append(0 if correct else 1)

        ai = oa

        if strategy == "STATIC":
            pass
        elif strategy == "SQRT_DECAY":
            n_ca = ca_counts[ci, ai]
            scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
            centroids[ci, ai] += max(scale, 0.005) * 0.05 * (fv - centroids[ci, ai])
            ca_counts[ci, ai] += 1
        elif strategy == "BEST_COMPOSED":
            # confidence + dual_rate + hysteresis + global (D6 winner)
            or_val = np.mean(override_windows[ci]) if len(override_windows[ci]) > 5 else 0.5
            if mode[ci] == "PRESERVE" and or_val > 0.25:
                mode[ci] = "LEARN"
            elif mode[ci] == "LEARN" and or_val < 0.10:
                mode[ci] = "PRESERVE"

            if conf <= 0.60:  # confidence gate
                n_ca = ca_counts[ci, ai]
                if mode[ci] == "LEARN":
                    base_rate = 1.6
                else:
                    base_rate = 0.1
                decay = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
                scale = base_rate * decay
                centroids[ci, ai] += max(scale, 0.005) * 0.05 * (fv - centroids[ci, ai])
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
    print("=" * 90)
    print("EXP-P5: PLANT-CONTROLLER INTERACTION")
    print("Which plant configuration gives the controller the most leverage?")
    print("=" * 90)

    strategies = ["STATIC", "SQRT_DECAY", "BEST_COMPOSED"]

    # TEMPERATURE × CONTROLLER
    print(f"\n{'=' * 90}")
    print("TEMPERATURE × CONTROLLER")
    print(f"{'=' * 90}")
    print(f"  {'Temp':>6s}  {'%>0.80':>6s}  {'Static':>7s}  {'Decay':>7s}  {'Best':>7s}  "
          f"{'Decay-Stat':>10s}  {'Best-Stat':>9s}")
    print(f"  {'-' * 65}")

    for temp in [0.05, 0.10, 0.25, 0.50, 1.00, 2.00, 5.00]:
        plant = PlantConfig(temperature=temp)
        results = {}
        pct80 = 0
        for strategy in strategies:
            accs = []
            for seed in SEEDS_SHORT:
                r = run_plant_controller(seed, plant, strategy)
                accs.append(r['acc'])
                if strategy == "STATIC":
                    pct80 = r['pct_above_80']
            results[strategy] = np.mean(accs)

        s, d, b = results["STATIC"], results["SQRT_DECAY"], results["BEST_COMPOSED"]
        print(f"  {temp:>6.2f}  {pct80:>5.0f}%  {s:>5.1f}%  {d:>5.1f}%  {b:>5.1f}%  "
              f"{d-s:>+8.1f}pp  {b-s:>+7.1f}pp")

    # METRIC × CONTROLLER
    print(f"\n{'=' * 90}")
    print("METRIC × CONTROLLER")
    print(f"{'=' * 90}")
    print(f"  {'Metric':>12s}  {'Static':>7s}  {'Decay':>7s}  {'Best':>7s}  "
          f"{'Decay-Stat':>10s}  {'Best-Stat':>9s}")
    print(f"  {'-' * 55}")

    for metric in ["euclidean", "cosine", "rbf_narrow"]:
        plant = PlantConfig(metric=metric)
        results = {}
        for strategy in strategies:
            accs = []
            for seed in SEEDS_SHORT:
                r = run_plant_controller(seed, plant, strategy)
                accs.append(r['acc'])
            results[strategy] = np.mean(accs)

        s, d, b = results["STATIC"], results["SQRT_DECAY"], results["BEST_COMPOSED"]
        print(f"  {metric:>12s}  {s:>5.1f}%  {d:>5.1f}%  {b:>5.1f}%  "
              f"{d-s:>+8.1f}pp  {b-s:>+7.1f}pp")

    # DIMENSIONALITY × CONTROLLER
    print(f"\n{'=' * 90}")
    print("DIMENSIONALITY × CONTROLLER")
    print(f"{'=' * 90}")
    print(f"  {'d':>4s}  {'Static':>7s}  {'Decay':>7s}  {'Best':>7s}  "
          f"{'Decay-Stat':>10s}  {'Best-Stat':>9s}")
    print(f"  {'-' * 48}")

    for d_val in [2, 4, 6, 12, 24]:
        plant = PlantConfig(d_override=d_val)
        results = {}
        for strategy in strategies:
            accs = []
            for seed in SEEDS_SHORT:
                r = run_plant_controller(seed, plant, strategy)
                accs.append(r['acc'])
            results[strategy] = np.mean(accs)

        s, d_a, b = results["STATIC"], results["SQRT_DECAY"], results["BEST_COMPOSED"]
        print(f"  {d_val:>4d}  {s:>5.1f}%  {d_a:>5.1f}%  {b:>5.1f}%  "
              f"{d_a-s:>+8.1f}pp  {b-s:>+7.1f}pp")

    # NOISE SCALE × CONTROLLER
    print(f"\n{'=' * 90}")
    print("NOISE SCALE × CONTROLLER")
    print(f"{'=' * 90}")
    print(f"  {'Noise':>6s}  {'Static':>7s}  {'Decay':>7s}  {'Best':>7s}  "
          f"{'Decay-Stat':>10s}  {'Best-Stat':>9s}")
    print(f"  {'-' * 50}")

    for ns in [0.0, 0.25, 0.50, 1.00, 1.50, 2.00]:
        plant = PlantConfig(noise_scale=ns)
        results = {}
        for strategy in strategies:
            accs = []
            for seed in SEEDS_SHORT:
                r = run_plant_controller(seed, plant, strategy)
                accs.append(r['acc'])
            results[strategy] = np.mean(accs)

        s, d, b = results["STATIC"], results["SQRT_DECAY"], results["BEST_COMPOSED"]
        print(f"  {ns:>6.2f}  {s:>5.1f}%  {d:>5.1f}%  {b:>5.1f}%  "
              f"{d-s:>+8.1f}pp  {b-s:>+7.1f}pp")

    # COMBINED: temperature × metric × controller
    print(f"\n{'=' * 90}")
    print("BEST PLANT: temperature=2.0 + metric=cosine (hypothesis)")
    print(f"{'=' * 90}")

    for temp, metric in [(1.0, "euclidean"), (2.0, "euclidean"),
                         (1.0, "cosine"), (2.0, "cosine"),
                         (0.5, "rbf_narrow"), (5.0, "euclidean")]:
        plant = PlantConfig(temperature=temp, metric=metric)
        results = {}
        for strategy in strategies:
            accs = []
            for seed in SEEDS_SHORT:
                r = run_plant_controller(seed, plant, strategy)
                accs.append(r['acc'])
            results[strategy] = np.mean(accs)
        s, d, b = results["STATIC"], results["SQRT_DECAY"], results["BEST_COMPOSED"]
        print(f"  τ={temp:.1f} {metric:>12s}: Static={s:.1f}% Decay={d:.1f}% Best={b:.1f}%  "
              f"leverage={b-s:+.1f}pp")

    print("\nDONE.")


if __name__ == "__main__":
    main()
