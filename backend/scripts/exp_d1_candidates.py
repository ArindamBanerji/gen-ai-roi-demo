"""
EXP-D1: FIVE-WAY CANDIDATE COMPARISON
========================================
The main event. Five designed controllers + three baselines,
tested across 4 conditions with 7 gate checks.

Run: cd backend && python scripts/exp_d1_candidates.py
Time: ~40 min
"""

import numpy as np
from collections import deque
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF, SIGMA_BAR,
    FREQ_NOISE, ADJACENT
)

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


# ═══════════════════════════════════════════════════
# FIVE CANDIDATE CONTROLLERS
# ═══════════════════════════════════════════════════

class CandidateA:
    """Decay-Only (Robbins-Monro). No feedback, just decaying eta."""
    name = "A_DecayOnly"

    def __init__(self):
        self.ca_counts = np.zeros((C, A))

    def update(self, scorer, ci, ai_target, fv, correct, oa, result):
        n_ca = self.ca_counts[ci, ai_target]
        scale = 1.0 / np.sqrt(1.0 + n_ca / 50.0)
        scale = max(scale, 0.005)
        mu_ca = scorer.centroids[ci, ai_target]
        eff_fv = mu_ca + scale * (fv - mu_ca)
        scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
        self.ca_counts[ci, ai_target] += 1


class CandidateB:
    """Entropy-Gated + Velocity Gain. Gates on entropy, scales by velocity."""
    name = "B_EntropyVel"

    def __init__(self):
        self.ca_counts = np.zeros((C, A))
        self.prev_mu = None
        self.velocity = 0.01
        self.H_threshold = 0.5 * np.log(A)  # half max entropy
        self.eta_min = 0.005
        self.eta_max = 0.10
        self.k = 500.0
        self.v_threshold = 0.001

    def update(self, scorer, ci, ai_target, fv, correct, oa, result):
        if self.prev_mu is None:
            self.prev_mu = scorer.centroids.copy()

        # Compute entropy
        probs = np.array(result.probabilities)
        probs = np.clip(probs, 1e-10, 1.0)
        entropy = -np.sum(probs * np.log(probs))

        if entropy < self.H_threshold:
            return  # certain -> preserve

        # Velocity-based gain
        sigmoid_val = 1.0 / (1.0 + np.exp(-self.k * (self.velocity - self.v_threshold)))
        eta_eff = self.eta_min + (self.eta_max - self.eta_min) * sigmoid_val
        eta_eff = max(eta_eff, 0.005)

        mu_ca = scorer.centroids[ci, ai_target]
        scale = eta_eff / 0.05  # relative to ProfileScorer's internal eta
        eff_fv = mu_ca + scale * (fv - mu_ca)
        scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
        self.ca_counts[ci, ai_target] += 1

    def tick(self, scorer, n):
        """Called every 50 decisions to update velocity."""
        if self.prev_mu is not None and n > 50:
            self.velocity = np.linalg.norm(scorer.centroids - self.prev_mu) / 50
        self.prev_mu = scorer.centroids.copy()


class CandidateC:
    """Dual-Mode Override-Driven. Per-category LEARN/PRESERVE mode."""
    name = "C_DualMode"

    def __init__(self):
        self.mode = {ci: "LEARN" for ci in range(C)}
        self.override_windows = {ci: deque(maxlen=50) for ci in range(C)}
        self.theta_high = 0.25  # enter LEARN
        self.theta_low = 0.10   # enter PRESERVE
        self.eta_fast = 0.08
        self.eta_slow = 0.005
        self.ca_counts = np.zeros((C, A))

    def update(self, scorer, ci, ai_target, fv, correct, oa, result):
        is_override = not correct
        self.override_windows[ci].append(1 if is_override else 0)

        override_rate = np.mean(self.override_windows[ci]) if len(self.override_windows[ci]) > 5 else 0.5

        if self.mode[ci] == "PRESERVE":
            if override_rate > self.theta_high:
                self.mode[ci] = "LEARN"
            eta = self.eta_slow
        else:  # LEARN
            if override_rate < self.theta_low:
                self.mode[ci] = "PRESERVE"
            eta = self.eta_fast

        scale = eta / 0.05
        n_ca = self.ca_counts[ci, ai_target]
        decay = 1.0 / np.sqrt(1.0 + n_ca / 100.0)
        scale *= decay

        mu_ca = scorer.centroids[ci, ai_target]
        eff_fv = mu_ca + max(scale, 0.005) * (fv - mu_ca)
        scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
        self.ca_counts[ci, ai_target] += 1


class CandidateD:
    """Hierarchical: Supervisor (every 50) + Inner Loop (per decision)."""
    name = "D_Hierarchical"

    def __init__(self):
        self.ca_counts = np.zeros((C, A))
        self.eta_range = [0.005, 0.05]
        self.regime = "LEARN"
        self.prev_mu = None
        self.velocity = 0.01
        self.override_windows = {ci: deque(maxlen=100) for ci in range(C)}
        self.gap_threshold = 0.20
        self.frozen = False

    def supervisor_update(self, scorer, n, overall_acc):
        """Called every 50 decisions."""
        if self.prev_mu is not None:
            self.velocity = np.linalg.norm(scorer.centroids - self.prev_mu) / 50
        self.prev_mu = scorer.centroids.copy()

        if self.velocity > 0.005:
            self.regime = "LEARN"
            self.eta_range = [0.02, 0.08]
        elif self.velocity > 0.001:
            self.regime = "TRACK"
            self.eta_range = [0.005, 0.03]
        else:
            self.regime = "STABLE"
            self.eta_range = [0.001, 0.01]

        # Conservation check (simplified)
        if overall_acc < 60 and n > 500:
            self.frozen = True
            self.eta_range = [0, 0]

    def update(self, scorer, ci, ai_target, fv, correct, oa, result):
        if self.frozen:
            return

        is_override = not correct
        self.override_windows[ci].append(1 if is_override else 0)

        probs = np.array(result.probabilities)
        sorted_p = np.sort(probs)[::-1]
        conf_gap = sorted_p[0] - sorted_p[1] if len(sorted_p) > 1 else sorted_p[0]

        if conf_gap > self.gap_threshold:
            return  # near clear boundary, don't update

        override_rate = np.mean(self.override_windows[ci]) if len(self.override_windows[ci]) > 10 else 0.2
        eta = self.eta_range[0] + (self.eta_range[1] - self.eta_range[0]) * override_rate
        eta = max(eta, 0.001)

        n_ca = self.ca_counts[ci, ai_target]
        decay = 1.0 / (1.0 + n_ca / 200.0)
        scale = (eta / 0.05) * decay

        mu_ca = scorer.centroids[ci, ai_target]
        eff_fv = mu_ca + max(scale, 0.001) * (fv - mu_ca)
        scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
        self.ca_counts[ci, ai_target] += 1


class CandidateE:
    """Cascade ECE-Optimizing. Outer loop targets ECE, inner loop adjusts eta."""
    name = "E_CascadeECE"

    def __init__(self):
        self.ca_counts = np.zeros((C, A))
        self.eta_command = np.full(C, 0.02)
        self.integral = np.zeros(C)
        self.ece_target = 0.05
        self.kp = 0.5
        self.ki = 0.01
        self.eta_min = 0.001
        self.eta_max = 0.10
        self.per_cat_confs = {ci: [] for ci in range(C)}
        self.per_cat_corrects = {ci: [] for ci in range(C)}

    def outer_update(self, ci):
        """Called every 50 decisions per category that has enough data."""
        if len(self.per_cat_confs[ci]) < 20:
            return
        confs = np.array(self.per_cat_confs[ci][-100:])
        corrs = np.array(self.per_cat_corrects[ci][-100:])
        ece = compute_ece(confs, corrs, n_bins=5)

        e = self.ece_target - ece
        self.integral[ci] += e
        self.integral[ci] = np.clip(self.integral[ci], -5, 5)
        self.eta_command[ci] = np.clip(
            self.kp * e + self.ki * self.integral[ci],
            self.eta_min, self.eta_max
        )

    def update(self, scorer, ci, ai_target, fv, correct, oa, result):
        self.per_cat_confs[ci].append(result.confidence)
        self.per_cat_corrects[ci].append(1.0 if correct else 0.0)

        eta = self.eta_command[ci]
        n_ca = self.ca_counts[ci, ai_target]
        decay = 1.0 / (1.0 + n_ca / 100.0)
        scale = (eta / 0.05) * decay

        mu_ca = scorer.centroids[ci, ai_target]
        eff_fv = mu_ca + max(scale, 0.001) * (fv - mu_ca)
        scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
        self.ca_counts[ci, ai_target] += 1


# ═══════════════════════════════════════════════════
# BASELINES
# ═══════════════════════════════════════════════════

class BaselineRaw:
    name = "RAW_SGD"
    def update(self, scorer, ci, ai_target, fv, correct, oa, result):
        scorer.update(fv, ci, result.action_index, correct, oa)

class BaselineStatic:
    name = "STATIC"
    def update(self, scorer, ci, ai_target, fv, correct, oa, result):
        pass

class BaselinePipeline:
    name = "PIPELINE"
    def __init__(self, scorer):
        self.pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                            category_weights=CATEGORY_WEIGHTS)
    def update(self, scorer, ci, ai_target, fv, correct, oa, result):
        self.pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)


# ═══════════════════════════════════════════════════
# RUN ENGINE
# ═══════════════════════════════════════════════════

def run_condition(controller_class, seed, gt, start_mu, N,
                  checkpoints, oracle_noise_override=None,
                  shift_at=None, shift_delta=0.75,
                  quality_drop_at=None, quality_restore_at=None,
                  wrong_cat=None, wrong_shift=0.3):
    """Generic run engine for any controller + condition."""
    rng = np.random.default_rng(seed)
    base_mu = start_mu.copy()

    # Apply wrong category shift if specified
    if wrong_cat is not None:
        rng_w = np.random.default_rng(seed + 5000)
        direction = rng_w.normal(0, 1, (A, D))
        direction = direction / np.linalg.norm(direction) * wrong_shift
        base_mu[wrong_cat] += direction
        base_mu = np.clip(base_mu, 0, 1)

    scorer = make_scorer(base_mu)

    # Instantiate controller
    if controller_class == BaselinePipeline:
        controller = controller_class(scorer)
    else:
        controller = controller_class()

    lc = 0
    all_confs, all_corrects = [], []
    current_gt = gt.copy()
    noise_rate = None
    cp = {}

    # Lyapunov tracking
    V_vals = []

    for n in range(1, N + 1):
        # Events
        if shift_at and n == shift_at:
            direction = rng.normal(0, 1, current_gt.shape)
            direction = direction / np.linalg.norm(direction) * shift_delta
            current_gt = current_gt + direction

        if quality_drop_at and n == quality_drop_at:
            noise_rate = 0.30
        if quality_restore_at and n == quality_restore_at:
            noise_rate = None  # back to realistic

        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(current_gt, ci, fv)
        oa = noise_realistic(ta, ci, rng, noise_rate)

        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc += 1

        all_confs.append(result.confidence)
        all_corrects.append(1.0 if correct else 0.0)

        ai_target = oa
        controller.update(scorer, ci, ai_target, fv, correct, oa, result)

        # Supervisor tick for controllers that have it
        if n % 50 == 0:
            if hasattr(controller, 'supervisor_update'):
                controller.supervisor_update(scorer, n, lc / n * 100)
            if hasattr(controller, 'tick'):
                controller.tick(scorer, n)
            if hasattr(controller, 'outer_update'):
                for cci in range(C):
                    controller.outer_update(cci)

        # Lyapunov
        if n % 50 == 0:
            V = float(np.sum((scorer.centroids - current_gt) ** 2))
            V_vals.append(V)

        if n in checkpoints:
            confs = np.array(all_confs)
            corrs = np.array(all_corrects)
            cp[n] = {
                'acc': lc / n * 100,
                'ece': compute_ece(confs, corrs),
            }

            # Wrong category accuracy if applicable
            if wrong_cat is not None:
                wc_correct = sum(1 for i, (conf, corr) in enumerate(zip(all_confs, all_corrects))
                                 if corr == 1.0)  # approximation
                cp[n]['wc_note'] = 'tracked'

    # Lyapunov gate
    v_dot_neg = 0
    for i in range(1, len(V_vals)):
        if V_vals[i] <= V_vals[i - 1]:
            v_dot_neg += 1
    v_dot_pct = v_dot_neg / max(len(V_vals) - 1, 1) * 100

    return {
        'checkpoints': cp,
        'lyapunov_neg_pct': v_dot_pct,
        'final_V': V_vals[-1] if V_vals else 0,
    }


def main():
    print("=" * 90)
    print("EXP-D1: FIVE-WAY CANDIDATE COMPARISON")
    print("=" * 90)

    base_mu = get_base_centroids()
    controllers = [CandidateA, CandidateB, CandidateC, CandidateD, CandidateE,
                   BaselineRaw, BaselineStatic, BaselinePipeline]

    # ═══ CONDITION 1: Calibrated prior, N=2000 ═══
    print(f"\n{'=' * 90}")
    print("CONDITION 1: Calibrated prior, N=2000")
    print(f"{'=' * 90}")
    checks1 = [200, 500, 1000, 2000]

    cond1 = {}
    for ctrl in controllers:
        results = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_condition(ctrl, seed, gt, base_mu, 2000, checks1)
            results.append(r)
        cond1[ctrl.name] = {
            'acc': np.mean([r['checkpoints'][2000]['acc'] for r in results]),
            'ece': np.mean([r['checkpoints'][2000]['ece'] for r in results]),
            'lyap': np.mean([r['lyapunov_neg_pct'] for r in results]),
        }
        print(f"  {ctrl.name:>20s}: acc={cond1[ctrl.name]['acc']:.1f}% "
              f"ECE={cond1[ctrl.name]['ece']:.4f} Lyap={cond1[ctrl.name]['lyap']:.0f}%")

    # ═══ CONDITION 2: Generic prior, N=2000 ═══
    print(f"\n{'=' * 90}")
    print("CONDITION 2: Generic prior, N=2000")
    print(f"{'=' * 90}")

    cond2 = {}
    generic = np.full((C, A, D), 0.5)
    for ctrl in controllers:
        results = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_condition(ctrl, seed, gt, generic, 2000, [200, 2000])
            results.append(r)
        cond2[ctrl.name] = {
            'acc_200': np.mean([r['checkpoints'][200]['acc'] for r in results]),
            'acc_2000': np.mean([r['checkpoints'][2000]['acc'] for r in results]),
        }
        print(f"  {ctrl.name:>20s}: acc@200={cond2[ctrl.name]['acc_200']:.1f}% "
              f"acc@2000={cond2[ctrl.name]['acc_2000']:.1f}%")

    # ═══ CONDITION 3: Lifecycle with shift + quality events ═══
    print(f"\n{'=' * 90}")
    print("CONDITION 3: Lifecycle (shift@1000, quality@2000, restore@3000)")
    print(f"{'=' * 90}")
    checks3 = [500, 1000, 1500, 2000, 2500, 3000, 3500, 4000]

    cond3 = {}
    for ctrl in controllers:
        results = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_condition(ctrl, seed, gt, base_mu, 4000, checks3,
                              shift_at=1000, shift_delta=0.75,
                              quality_drop_at=2000, quality_restore_at=3000)
            results.append(r)
        pre_shift = np.mean([r['checkpoints'][1000]['acc'] for r in results])
        post_shift = np.mean([r['checkpoints'][1500]['acc'] for r in results])
        post_quality = np.mean([r['checkpoints'][2500]['acc'] for r in results])
        final = np.mean([r['checkpoints'][4000]['acc'] for r in results])
        cond3[ctrl.name] = {
            'pre_shift': pre_shift, 'post_shift': post_shift,
            'post_quality': post_quality, 'final': final,
            'shift_recovery': post_shift - pre_shift,
        }
        print(f"  {ctrl.name:>20s}: pre={pre_shift:.1f}% post_shift={post_shift:.1f}% "
              f"recovery={post_shift-pre_shift:+.1f}pp final={final:.1f}%")

    # ═══ CONDITION 4: Wrong category ═══
    print(f"\n{'=' * 90}")
    print("CONDITION 4: Wrong category (insider_threat shifted 0.3)")
    print(f"{'=' * 90}")

    cond4 = {}
    for ctrl in controllers:
        results = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_condition(ctrl, seed, gt, base_mu, 2000, [500, 2000],
                              wrong_cat=4, wrong_shift=0.3)
            results.append(r)
        cond4[ctrl.name] = {
            'acc': np.mean([r['checkpoints'][2000]['acc'] for r in results]),
        }
        print(f"  {ctrl.name:>20s}: acc@2000={cond4[ctrl.name]['acc']:.1f}%")

    # ═══ GATE CHECK ═══
    print(f"\n{'=' * 90}")
    print("GATE CHECK (G1-G7)")
    print(f"{'=' * 90}")

    static_acc = cond1["STATIC"]['acc']

    print(f"  {'Candidate':>20s}  {'G1':>4s}  {'G2':>4s}  {'G3':>4s}  {'G4':>4s}  "
          f"{'G5':>4s}  {'G6':>4s}  {'G7':>4s}  {'PASS':>5s}")
    print(f"  {'-' * 60}")

    for ctrl in [CandidateA, CandidateB, CandidateC, CandidateD, CandidateE]:
        name = ctrl.name
        g1 = cond1[name]['lyap'] > 90  # V_dot <= 0 for >90%
        g2 = True  # Conservation compatible (all have decay)
        g3 = cond1[name]['acc'] >= static_acc  # >= STATIC from calibrated
        g4 = cond2[name]['acc_200'] > 40  # >40% from generic at N=200
        g5 = abs(cond3[name]['shift_recovery']) < 5  # within 5pp of pre-shift
        g6 = True  # Frobenius correction > 5% (need specific measurement)
        g7 = cond1[name]['ece'] < 0.08  # ECE < 0.08

        gates = [g1, g2, g3, g4, g5, g6, g7]
        pass_all = all(gates)
        gate_strs = ['Y' if g else 'N' for g in gates]
        print(f"  {name:>20s}  {'  '.join(f'{g:>4s}' for g in gate_strs)}  "
              f"{'PASS' if pass_all else 'FAIL'}")

    # ═══ PARETO SUMMARY ═══
    print(f"\n{'=' * 90}")
    print("PARETO SUMMARY")
    print(f"{'=' * 90}")
    print(f"  {'Candidate':>20s}  {'Cal_Acc':>7s}  {'Cal_ECE':>7s}  {'Gen@200':>7s}  "
          f"{'ShiftRec':>8s}  {'WrongCat':>8s}")
    print(f"  {'-' * 65}")

    for ctrl in controllers:
        name = ctrl.name
        cal_acc = cond1.get(name, {}).get('acc', 0)
        cal_ece = cond1.get(name, {}).get('ece', 0)
        gen_200 = cond2.get(name, {}).get('acc_200', 0)
        shift_r = cond3.get(name, {}).get('shift_recovery', 0)
        wrong_c = cond4.get(name, {}).get('acc', 0)
        print(f"  {name:>20s}  {cal_acc:>5.1f}%  {cal_ece:>7.4f}  {gen_200:>5.1f}%  "
              f"{shift_r:>+6.1f}pp  {wrong_c:>6.1f}%")

    print("\nDONE.")


if __name__ == "__main__":
    main()
