"""
EXP-D6: COMPONENT COMBINATION
=================================
After D2-D5 identify best signal, gain, switching, scope,
test whether they compose or interfere.

Run: cd backend && python scripts/exp_d6_combination.py
Time: ~25 min
"""

import numpy as np
from collections import deque
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF
)

N = 2000
SEEDS_SHORT = [42, 123, 777]


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


class ComposedController:
    """Controller built from mix-and-match components."""

    def __init__(self, signal, gain, switching, scope):
        self.signal_name = signal
        self.gain_name = gain
        self.switching_name = switching
        self.scope_name = scope

        self.ca_counts = np.zeros((C, A))
        self.override_windows = {ci: deque(maxlen=50) for ci in range(C)}
        self.prev_mu = None
        self.velocity = 0.01
        self.mode = {ci: "LEARN" for ci in range(C)}
        self.name = f"{signal[:3]}_{gain[:3]}_{switching[:3]}_{scope[:3]}"

    def compute_signal(self, scorer, ci, fv, result, correct):
        self.override_windows[ci].append(0 if correct else 1)
        if self.signal_name == "confidence":
            return result.confidence, result.confidence > 0.60
        elif self.signal_name == "entropy":
            probs = np.clip(np.array(result.probabilities), 1e-10, 1.0)
            H = -np.sum(probs * np.log(probs))
            return H, H < 0.5 * np.log(A)
        elif self.signal_name == "override_rate":
            or_val = np.mean(self.override_windows[ci]) if len(self.override_windows[ci]) > 5 else 0.5
            return or_val, or_val < 0.15
        elif self.signal_name == "conf_gap":
            probs = np.array(result.probabilities)
            sp = np.sort(probs)[::-1]
            gap = sp[0] - sp[1] if len(sp) > 1 else sp[0]
            return gap, gap > 0.30

    def compute_gain(self, ci, ai, n_ca):
        base_decay = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
        if self.gain_name == "inv_sqrt":
            return base_decay
        elif self.gain_name == "velocity":
            sigmoid = 1.0 / (1.0 + np.exp(-500 * (self.velocity - 0.001)))
            return (0.1 + 1.9 * sigmoid) * base_decay
        elif self.gain_name == "override":
            or_val = np.mean(self.override_windows[ci]) if len(self.override_windows[ci]) > 5 else 0.2
            return (0.1 + 1.9 * or_val) * base_decay
        elif self.gain_name == "dual_rate":
            if self.mode[ci] == "LEARN":
                return 1.6 * base_decay
            else:
                return 0.1 * base_decay

    def compute_switching(self, ci):
        or_val = np.mean(self.override_windows[ci]) if len(self.override_windows[ci]) > 5 else 0.5
        if self.switching_name == "none":
            return  # always LEARN
        elif self.switching_name == "hysteresis":
            if self.mode[ci] == "PRESERVE" and or_val > 0.25:
                self.mode[ci] = "LEARN"
            elif self.mode[ci] == "LEARN" and or_val < 0.10:
                self.mode[ci] = "PRESERVE"
        elif self.switching_name == "velocity_thresh":
            self.mode[ci] = "LEARN" if self.velocity > 0.001 else "PRESERVE"
        elif self.switching_name == "override_thresh":
            self.mode[ci] = "LEARN" if or_val > 0.15 else "PRESERVE"

    def get_scope_params(self, ci):
        """Return (theta_mult, eta_mult) based on scope."""
        if self.scope_name == "global":
            return 1.0, 1.0
        elif self.scope_name == "per_category":
            or_val = np.mean(self.override_windows[ci]) if len(self.override_windows[ci]) > 10 else 0.2
            theta_mult = 1.0 - or_val  # lower threshold for high-error categories
            eta_mult = 0.5 + or_val * 2.0  # higher eta for high-error categories
            return max(theta_mult, 0.5), min(eta_mult, 2.0)
        elif self.scope_name == "clustered":
            vol = CATEGORY_WEIGHTS[ci]
            if vol > 0.3:
                return 1.2, 0.6  # tight gate, low eta for dominant
            elif vol > 0.07:
                return 1.0, 1.0  # default for medium
            else:
                return 0.7, 1.5  # loose gate, high eta for rare

    def tick(self, scorer, n):
        if n % 50 == 0:
            if self.prev_mu is not None:
                self.velocity = np.linalg.norm(scorer.centroids - self.prev_mu) / 50
            self.prev_mu = scorer.centroids.copy()
            for ci in range(C):
                self.compute_switching(ci)


def run_composed(seed, controller, gt, start_mu, wrong_cat=None, wrong_shift=0.3):
    rng = np.random.default_rng(seed)
    mu = start_mu.copy()
    if wrong_cat is not None:
        rng_w = np.random.default_rng(seed + 5000)
        direction = rng_w.normal(0, 1, (A, D))
        direction = direction / np.linalg.norm(direction) * wrong_shift
        mu[wrong_cat] += direction
        mu = np.clip(mu, 0, 1)

    scorer = make_scorer(mu)
    lc = 0
    all_confs, all_corrects = [], []
    wc_correct, wc_total = 0, 0

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc += 1
        all_confs.append(result.confidence)
        all_corrects.append(1.0 if correct else 0.0)
        if wrong_cat is not None and ci == wrong_cat:
            wc_total += 1
            if correct: wc_correct += 1

        controller.tick(scorer, n)
        signal_val, should_block = controller.compute_signal(scorer, ci, fv, result, correct)

        theta_mult, eta_mult = controller.get_scope_params(ci)
        if should_block and theta_mult >= 0.8:
            continue

        ai_target = oa
        n_ca = controller.ca_counts[ci, ai_target]
        gain = controller.compute_gain(ci, ai_target, n_ca)
        gain *= eta_mult
        gain = max(gain, 0.005)

        mu_ca = scorer.centroids[ci, ai_target]
        eff_fv = mu_ca + gain * (fv - mu_ca)
        scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
        controller.ca_counts[ci, ai_target] += 1

    confs = np.array(all_confs)
    corrs = np.array(all_corrects)
    wc_acc = wc_correct / wc_total * 100 if wc_total > 0 else 0
    return {
        'acc': lc / N * 100,
        'ece': compute_ece(confs, corrs),
        'wc_acc': wc_acc,
    }


def main():
    print("=" * 90)
    print("EXP-D6: COMPONENT COMBINATION")
    print("Mix-and-match best components from D2-D5")
    print("=" * 90)

    base_mu = get_base_centroids()

    # Test grid: 2 signals × 2 gains × 2 switching × 2 scopes = 16 combos
    # (Using plausible "best" candidates — adjust after D2-D5 results)
    signals = ["confidence", "override_rate"]
    gains = ["inv_sqrt", "dual_rate"]
    switchings = ["none", "hysteresis"]
    scopes = ["global", "per_category"]

    configs = []
    for sig in signals:
        for gain in gains:
            for sw in switchings:
                for sc in scopes:
                    configs.append((sig, gain, sw, sc))

    # Add baselines
    # (STATIC and PIPELINE handled separately)

    # CALIBRATED PRIOR
    print(f"\n{'=' * 90}")
    print("CALIBRATED PRIOR")
    print(f"{'=' * 90}")
    print(f"  {'Signal':>8s} {'Gain':>8s} {'Switch':>8s} {'Scope':>8s}  {'Acc':>6s}  {'ECE':>8s}")
    print(f"  {'-' * 55}")

    cal_results = {}
    for sig, gain, sw, sc in configs:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            ctrl = ComposedController(sig, gain, sw, sc)
            r = run_composed(seed, ctrl, gt, base_mu)
            runs.append(r)
        key = f"{sig[:3]}_{gain[:3]}_{sw[:3]}_{sc[:3]}"
        acc = np.mean([r['acc'] for r in runs])
        ece = np.mean([r['ece'] for r in runs])
        cal_results[key] = {'acc': acc, 'ece': ece}
        print(f"  {sig:>8s} {gain:>8s} {sw:>8s} {sc:>8s}  {acc:5.1f}%  {ece:8.4f}")

    # Baselines
    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
    static_runs = []
    pipe_runs = []
    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        s_scorer = make_scorer(base_mu.copy())
        p_scorer = make_scorer(base_mu.copy())
        pipe = ThreeStagePipeline(p_scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                   category_weights=CATEGORY_WEIGHTS)
        rng = np.random.default_rng(seed)
        lc_s, lc_p = 0, 0
        confs_s, corrs_s, confs_p, corrs_p = [], [], [], []
        for n in range(1, N + 1):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            rs = s_scorer.score(fv, ci)
            rp = p_scorer.score(fv, ci)
            cs = rs.action_index == oa
            cp_ = rp.action_index == oa
            if cs: lc_s += 1
            if cp_: lc_p += 1
            confs_s.append(rs.confidence); corrs_s.append(1.0 if cs else 0.0)
            confs_p.append(rp.confidence); corrs_p.append(1.0 if cp_ else 0.0)
            pipe.process(fv, ci, rp.action_index, cp_, oa, rp.confidence)
        static_runs.append({'acc': lc_s/N*100, 'ece': compute_ece(np.array(confs_s), np.array(corrs_s))})
        pipe_runs.append({'acc': lc_p/N*100, 'ece': compute_ece(np.array(confs_p), np.array(corrs_p))})

    s_acc = np.mean([r['acc'] for r in static_runs])
    s_ece = np.mean([r['ece'] for r in static_runs])
    p_acc = np.mean([r['acc'] for r in pipe_runs])
    p_ece = np.mean([r['ece'] for r in pipe_runs])
    print(f"  {'STATIC':>35s}  {s_acc:5.1f}%  {s_ece:8.4f}")
    print(f"  {'PIPELINE':>35s}  {p_acc:5.1f}%  {p_ece:8.4f}")

    # WRONG CATEGORY
    print(f"\n{'=' * 90}")
    print("WRONG CATEGORY (insider_threat shifted 0.3)")
    print(f"{'=' * 90}")
    print(f"  {'Signal':>8s} {'Gain':>8s} {'Switch':>8s} {'Scope':>8s}  {'Overall':>7s}  {'WrongCat':>8s}")
    print(f"  {'-' * 55}")

    for sig, gain, sw, sc in configs:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            ctrl = ComposedController(sig, gain, sw, sc)
            r = run_composed(seed, ctrl, gt, base_mu, wrong_cat=4)
            runs.append(r)
        acc = np.mean([r['acc'] for r in runs])
        wc = np.mean([r['wc_acc'] for r in runs])
        print(f"  {sig:>8s} {gain:>8s} {sw:>8s} {sc:>8s}  {acc:5.1f}%  {wc:6.1f}%")

    # INTERACTION ANALYSIS
    print(f"\n{'=' * 90}")
    print("INTERACTION ANALYSIS (do components compose?)")
    print(f"{'=' * 90}")

    # Main effects
    for dim_name, dim_vals, dim_idx in [
        ("signal", signals, 0), ("gain", gains, 1),
        ("switching", switchings, 2), ("scope", scopes, 3)
    ]:
        for val in dim_vals:
            matching = [k for k, v in cal_results.items()
                        if k.split('_')[dim_idx] == val[:3]]
            if matching:
                mean_acc = np.mean([cal_results[k]['acc'] for k in matching])
                mean_ece = np.mean([cal_results[k]['ece'] for k in matching])
                print(f"  {dim_name}={val:>12s}: mean_acc={mean_acc:.1f}%  mean_ece={mean_ece:.4f}")

    # Best combo
    best_acc_key = max(cal_results, key=lambda k: cal_results[k]['acc'])
    best_ece_key = min(cal_results, key=lambda k: cal_results[k]['ece'])
    best_comp_key = max(cal_results, key=lambda k: cal_results[k]['acc'] * (1 - cal_results[k]['ece']))
    print(f"\n  Best accuracy: {best_acc_key} ({cal_results[best_acc_key]['acc']:.1f}%)")
    print(f"  Best ECE: {best_ece_key} ({cal_results[best_ece_key]['ece']:.4f})")
    print(f"  Best composite: {best_comp_key}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
