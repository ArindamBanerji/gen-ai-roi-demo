"""
EXP-D4: SWITCHING LOGIC COMPARISON
=====================================
Fix architecture (dual-mode), vary switching logic.

Run: cd backend && python scripts/exp_d4_switching.py
Time: ~20 min
"""

import numpy as np
from collections import deque
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, FREQ_NOISE, ADJACENT
)

N_LIFECYCLE = 4000
SEEDS_SHORT = [42, 123, 777]
WRONG_CAT = 4
WRONG_SHIFT = 0.3


def run_switching_test(seed, logic_name, gt, start_mu, N,
                       shift_at=None, quality_at=None, restore_at=None):
    rng = np.random.default_rng(seed)
    scorer = make_scorer(start_mu.copy())
    ca_counts = np.zeros((C, A))
    override_windows = {ci: deque(maxlen=50) for ci in range(C)}
    prev_mu = scorer.centroids.copy()
    velocity = 0.01

    # Per-category mode
    mode = {ci: "LEARN" for ci in range(C)}
    eta_fast = 0.08
    eta_slow = 0.005

    # FSM states
    fsm_state = "COLD"
    fsm_timer = 0

    lc = 0
    current_gt = gt.copy()
    noise_rate = None
    chattering = 0
    prev_modes = {ci: "LEARN" for ci in range(C)}
    cp = {}

    for n in range(1, N + 1):
        if shift_at and n == shift_at:
            direction = rng.normal(0, 1, current_gt.shape)
            direction = direction / np.linalg.norm(direction) * 0.75
            current_gt = current_gt + direction
        if quality_at and n == quality_at:
            noise_rate = 0.30
        if restore_at and n == restore_at:
            noise_rate = None

        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(current_gt, ci, fv)
        oa = noise_realistic(ta, ci, rng, noise_rate)
        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if correct: lc += 1
        override_windows[ci].append(0 if correct else 1)

        if n % 50 == 0:
            velocity = np.linalg.norm(scorer.centroids - prev_mu) / 50
            prev_mu = scorer.centroids.copy()

        override_rate = np.mean(override_windows[ci]) if len(override_windows[ci]) > 5 else 0.5

        # Determine mode based on switching logic
        if logic_name == "fixed_200":
            mode[ci] = "LEARN" if n <= 200 else "PRESERVE"
        elif logic_name == "velocity_threshold":
            mode[ci] = "LEARN" if velocity > 0.001 else "PRESERVE"
        elif logic_name == "override_threshold":
            mode[ci] = "LEARN" if override_rate > 0.15 else "PRESERVE"
        elif logic_name == "hysteresis":
            if mode[ci] == "PRESERVE" and override_rate > 0.25:
                mode[ci] = "LEARN"
            elif mode[ci] == "LEARN" and override_rate < 0.10:
                mode[ci] = "PRESERVE"
        elif logic_name == "fsm":
            if n % 50 == 0:
                if fsm_state == "COLD":
                    if velocity < 0.005 and n > 100:
                        fsm_state = "TRACK"
                elif fsm_state == "TRACK":
                    if velocity < 0.001:
                        fsm_state = "STABLE"
                    elif velocity > 0.01:
                        fsm_state = "COLD"
                elif fsm_state == "STABLE":
                    if velocity > 0.005:
                        fsm_state = "SHIFT"
                elif fsm_state == "SHIFT":
                    if velocity < 0.002:
                        fsm_state = "TRACK"
                    fsm_timer += 1
                    if fsm_timer > 10:
                        fsm_state = "TRACK"
                        fsm_timer = 0

            if fsm_state in ["COLD", "SHIFT"]:
                mode[ci] = "LEARN"
            elif fsm_state == "TRACK":
                mode[ci] = "LEARN" if override_rate > 0.15 else "PRESERVE"
            else:
                mode[ci] = "PRESERVE"

        # Track chattering
        if mode[ci] != prev_modes.get(ci, "LEARN"):
            chattering += 1
        prev_modes[ci] = mode[ci]

        # Apply update based on mode
        if mode[ci] == "LEARN":
            eta = eta_fast
        else:
            eta = eta_slow

        n_ca = ca_counts[ci, oa]
        decay = 1.0 / np.sqrt(1.0 + n_ca / 100.0)
        scale = (eta / 0.05) * decay
        mu_ca = scorer.centroids[ci, oa]
        eff_fv = mu_ca + max(scale, 0.005) * (fv - mu_ca)
        scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
        ca_counts[ci, oa] += 1

        if n in [500, 1000, 1500, 2000, 3000, 4000]:
            if n <= N:
                cp[n] = {'acc': lc / n * 100, 'chattering': chattering}

    return cp


def main():
    print("=" * 80)
    print("EXP-D4: SWITCHING LOGIC COMPARISON")
    print("=" * 80)

    base_mu = get_base_centroids()
    logics = ["fixed_200", "velocity_threshold", "override_threshold",
              "hysteresis", "fsm"]

    # Lifecycle
    print(f"\n  LIFECYCLE (shift@1000, quality@2000, restore@3000):")
    print(f"  {'Logic':>18s}  {'Pre@1000':>8s}  {'Post@1500':>9s}  {'Final@4000':>10s}  {'Chatter':>7s}")
    print(f"  {'-' * 60}")

    for logic in logics:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_switching_test(seed, logic, gt, base_mu, N_LIFECYCLE,
                                   shift_at=1000, quality_at=2000, restore_at=3000)
            runs.append(r)
        pre = np.mean([r[1000]['acc'] for r in runs])
        post = np.mean([r[1500]['acc'] for r in runs])
        final = np.mean([r[4000]['acc'] for r in runs])
        chatter = np.mean([r[4000]['chattering'] for r in runs])
        print(f"  {logic:>18s}  {pre:>6.1f}%  {post:>7.1f}%  {final:>8.1f}%  {chatter:>5.0f}")

    # Wrong category
    print(f"\n  WRONG CATEGORY (insider_threat shifted 0.3):")
    print(f"  {'Logic':>18s}  {'Acc@500':>7s}  {'Acc@2000':>8s}")
    print(f"  {'-' * 38}")

    for logic in logics:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            wrong_mu = base_mu.copy()
            rng_w = np.random.default_rng(seed + 5000)
            direction = rng_w.normal(0, 1, (A, D))
            direction = direction / np.linalg.norm(direction) * WRONG_SHIFT
            wrong_mu[WRONG_CAT] += direction
            wrong_mu = np.clip(wrong_mu, 0, 1)
            r = run_switching_test(seed, logic, gt, wrong_mu, 2000)
            runs.append(r)
        acc_500 = np.mean([r.get(500, {}).get('acc', 0) for r in runs])
        acc_2000 = np.mean([r.get(2000, {}).get('acc', 0) for r in runs])
        print(f"  {logic:>18s}  {acc_500:>5.1f}%  {acc_2000:>6.1f}%")

    print("\nDONE.")


if __name__ == "__main__":
    main()
