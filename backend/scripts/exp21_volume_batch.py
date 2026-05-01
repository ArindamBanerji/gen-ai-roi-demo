"""
EXP-21: V-VOLUME-AWARE-BATCH
===============================
Does volume-aware K fix the lockout problem?

Run: cd backend && python scripts/exp21_volume_batch.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF, SIGMA_BAR
)
from collections import Counter

N = 2000
CHECKPOINTS = [50, 200, 500, 1000, 2000]
WRONG_CAT = 4
WRONG_SHIFT = 0.3
MEAN_WEIGHT = 1/C


def make_wrong_prior(base_mu, rng):
    prior = base_mu.copy()
    direction = rng.normal(0, 1, (A, D))
    direction = direction / np.linalg.norm(direction) * WRONG_SHIFT
    prior[WRONG_CAT] += direction
    return np.clip(prior, 0, 1)


class VolumeAwarePipeline:
    """Pipeline with K_eff = max(3, round(V_c/V_mean * K))."""

    def __init__(self, scorer, K_base=10, theta_conf=0.60, cat_weights=None):
        self.scorer = scorer
        self.K_base = K_base
        self.theta_conf = theta_conf
        self.cat_weights = cat_weights or [1/C]*C
        self.mean_weight = MEAN_WEIGHT
        self.buffers = {}
        self.counts = np.zeros((C, A))
        self.stats = {'updates': 0, 'gate_blocked': 0, 'gate_passed': 0}

    def get_K(self, ci):
        ratio = self.cat_weights[ci] / self.mean_weight
        return max(3, round(ratio * self.K_base))

    def process(self, fv, ci, scorer_action, correct, gt_action, confidence):
        if confidence > self.theta_conf:
            self.stats['gate_blocked'] += 1
            return
        self.stats['gate_passed'] += 1

        ai_target = gt_action
        key = (ci, ai_target)
        if key not in self.buffers:
            self.buffers[key] = []
        self.buffers[key].append({'fv': fv.copy(), 'correct': correct, 'gt_action': gt_action})

        K_eff = self.get_K(ci)
        if len(self.buffers[key]) >= K_eff:
            self._flush(key, K_eff)

    def _flush(self, key, K_eff):
        ci, ai = key
        buf = self.buffers[key]
        confirmed = [b for b in buf if b['correct']]
        K_total = len(buf)
        self.buffers[key] = []
        self.counts[ci, ai] += K_total

        if len(confirmed) == 0:
            return

        K_conf = len(confirmed)
        mu_cur = self.scorer.centroids[ci, ai]
        d_bar = np.mean([b['fv'] - mu_cur for b in confirmed], axis=0)
        magnitude = np.linalg.norm(d_bar)
        tau = SIGMA_BAR / np.sqrt(K_conf)

        if magnitude <= tau:
            return

        mean_fv = np.mean([b['fv'] for b in confirmed], axis=0)
        N_ca = self.counts[ci, ai]
        precision = K_total / (N_ca + K_total)
        vol_scale = np.sqrt(self.mean_weight / self.cat_weights[ci])
        vol_scale = np.clip(vol_scale, 0.1, 3.0)
        combined = np.clip(precision * vol_scale, 0.01, 1.0)
        effective_fv = mu_cur + combined * (mean_fv - mu_cur)

        gt_actions = [b['gt_action'] for b in confirmed]
        batch_gt = Counter(gt_actions).most_common(1)[0][0]
        r = self.scorer.score(effective_fv.astype(np.float64), ci)
        self.scorer.update(effective_fv.astype(np.float64), ci,
                           r.action_index, r.action_index == batch_gt, batch_gt)
        self.stats['updates'] += 1


def run_volume_test(seed, mode):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)
    wrong_prior = make_wrong_prior(base_mu, np.random.default_rng(seed + 5000))
    scorer = make_scorer(wrong_prior)

    if mode == "K10":
        pipeline = ThreeStagePipeline(scorer, K=10, theta_conf=THETA_CONF,
                                       category_weights=CATEGORY_WEIGHTS)
    elif mode == "VOLUME_AWARE":
        pipeline = VolumeAwarePipeline(scorer, K_base=10, theta_conf=THETA_CONF,
                                        cat_weights=CATEGORY_WEIGHTS)
    elif mode == "K3_ALL":
        pipeline = ThreeStagePipeline(scorer, K=3, theta_conf=THETA_CONF,
                                       category_weights=CATEGORY_WEIGHTS)

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

        if ci == WRONG_CAT:
            wc_total += 1
            if correct: wc_correct += 1
        else:
            other_total += 1
            if correct: other_correct += 1

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
    print("EXP-21: V-VOLUME-AWARE-BATCH")
    print(f"Wrong category: {CATEGORIES[WRONG_CAT]} (5% volume)")

    # Show K_eff per category
    for ci, cat in enumerate(CATEGORIES):
        ratio = CATEGORY_WEIGHTS[ci] / MEAN_WEIGHT
        K_eff = max(3, round(ratio * 10))
        print(f"  {cat}: vol={CATEGORY_WEIGHTS[ci]*100:.0f}%, K_eff={K_eff}")
    print("=" * 80)

    modes = ["K10", "VOLUME_AWARE", "K3_ALL"]

    for mode in modes:
        all_r = [run_volume_test(s, mode) for s in SEEDS]
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

    k10_wc = np.mean([run_volume_test(s, "K10")[N]['wc_acc'] for s in SEEDS])
    va_wc = np.mean([run_volume_test(s, "VOLUME_AWARE")[N]['wc_acc'] for s in SEEDS])
    k3_wc = np.mean([run_volume_test(s, "K3_ALL")[N]['wc_acc'] for s in SEEDS])

    print(f"Q1: Volume-aware corrects faster? K10={k10_wc:.1f}% VA={va_wc:.1f}% "
          f"{'YES' if va_wc > k10_wc + 1 else 'NO'}")

    k10_oc = np.mean([run_volume_test(s, "K10")[N]['other_acc'] for s in SEEDS])
    va_oc = np.mean([run_volume_test(s, "VOLUME_AWARE")[N]['other_acc'] for s in SEEDS])
    print(f"Q2: Volume-aware maintains others? K10={k10_oc:.1f}% VA={va_oc:.1f}% "
          f"{'YES' if va_oc >= k10_oc - 1 else 'NO'}")

    print(f"Q3: K3_ALL sufficient? K3={k3_wc:.1f}% vs VA={va_wc:.1f}% "
          f"{'YES' if abs(k3_wc - va_wc) < 1.0 else 'NO'}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
