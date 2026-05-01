"""
EXP-R6: V-UNMEASURED-VALUE
=============================
Does the centroid provide operational value that accuracy
and ECE don't capture?

Run: cd backend && python scripts/exp_r6_unmeasured.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF
)

N_RUN = 2000
SEEDS_SHORT = [42, 123, 777]
N_PROBES = 20


def main():
    print("=" * 80)
    print("EXP-R6: V-UNMEASURED-VALUE")
    print("=" * 80)

    base_mu = get_base_centroids()

    for seed in SEEDS_SHORT:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)

        # Create three scorers: STATIC, PIPELINE, RAW_SGD
        scorer_static = make_scorer(base_mu.copy())
        scorer_pipe = make_scorer(base_mu.copy())
        scorer_raw = make_scorer(base_mu.copy())
        pipeline = ThreeStagePipeline(scorer_pipe, K=K_BATCH, theta_conf=THETA_CONF,
                                       category_weights=CATEGORY_WEIGHTS)

        # Generate probe factor vectors (fixed test points)
        rng_probe = np.random.default_rng(seed + 99000)
        probes = []
        for _ in range(N_PROBES):
            ci = int(rng_probe.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_probe.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            probes.append((ci, fv))

        # Track probe recommendations at checkpoints
        probe_history = {'PIPELINE': {}, 'RAW_SGD': {}, 'STATIC': {}}
        checkpoints = [200, 500, 1000, 2000]

        # Referral tracking
        referral_stats = {s: {'referred': 0, 'ref_correct': 0, 'ref_difficult': 0,
                              'total': 0, 'difficult': 0}
                          for s in ['PIPELINE', 'RAW_SGD', 'STATIC']}

        # Run simulation
        for n in range(1, N_RUN + 1):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)

            # All three score
            r_s = scorer_static.score(fv, ci)
            r_p = scorer_pipe.score(fv, ci)
            r_r = scorer_raw.score(fv, ci)

            # Update pipeline and raw
            pipeline.process(fv, ci, r_p.action_index, r_p.action_index == oa, oa, r_p.confidence)
            scorer_raw.update(fv, ci, r_r.action_index, r_r.action_index == oa, oa)

            # Referral tracking (conf < 0.50 = refer)
            majority_action = 1  # investigate (most common)
            is_difficult = (ta != majority_action)

            for name, result in [('PIPELINE', r_p), ('RAW_SGD', r_r), ('STATIC', r_s)]:
                referral_stats[name]['total'] += 1
                if is_difficult:
                    referral_stats[name]['difficult'] += 1
                if result.confidence < 0.50:
                    referral_stats[name]['referred'] += 1
                    if is_difficult:
                        referral_stats[name]['ref_difficult'] += 1

            # Probe at checkpoints
            if n in checkpoints:
                for name, scorer in [('PIPELINE', scorer_pipe), ('RAW_SGD', scorer_raw),
                                      ('STATIC', scorer_static)]:
                    if n not in probe_history[name]:
                        probe_history[name][n] = []
                    for p_ci, p_fv in probes:
                        r = scorer.score(p_fv, p_ci)
                        probe_history[name][n].append(r.action_index)

        print(f"\n  Seed {seed}:")

        # METRIC 1: Referral quality
        print(f"\n  METRIC 1: Referral Quality (conf < 0.50)")
        print(f"  {'Strategy':>10s}  {'Referred':>8s}  {'Ref_Difficult':>13s}  {'Precision':>9s}")
        print(f"  {'-' * 45}")
        for name in ['PIPELINE', 'RAW_SGD', 'STATIC']:
            s = referral_stats[name]
            precision = s['ref_difficult'] / max(s['referred'], 1) * 100
            ref_rate = s['referred'] / s['total'] * 100
            print(f"  {name:>10s}  {ref_rate:>6.1f}%  "
                  f"{s['ref_difficult']:>13d}  {precision:>7.1f}%")

        # METRIC 2: Boundary sharpness
        print(f"\n  METRIC 2: Boundary Sharpness")
        rng_sharp = np.random.default_rng(seed + 88000)
        for name, scorer in [('PIPELINE', scorer_pipe), ('RAW_SGD', scorer_raw),
                              ('STATIC', scorer_static)]:
            gaps = []
            for _ in range(1000):
                ci = int(rng_sharp.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng_sharp.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                r = scorer.score(fv, ci)
                probs = np.array(r.probabilities)
                sp = np.sort(probs)[::-1]
                gaps.append(sp[0] - sp[1])
            gaps = np.array(gaps)
            sharp = (gaps > 0.30).mean() * 100
            print(f"    {name:>10s}: %gap>0.30 = {sharp:.1f}%, mean_gap = {np.mean(gaps):.4f}")

        # METRIC 3: Temporal stability of probes
        print(f"\n  METRIC 3: Temporal Stability (probe consistency)")
        for name in ['PIPELINE', 'RAW_SGD', 'STATIC']:
            if len(checkpoints) < 2:
                continue
            stable_count = 0
            for p_idx in range(N_PROBES):
                actions_over_time = [probe_history[name][cp][p_idx] for cp in checkpoints]
                if len(set(actions_over_time)) == 1:
                    stable_count += 1
            stability = stable_count / N_PROBES * 100
            print(f"    {name:>10s}: {stability:.0f}% of probes stable across all checkpoints")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)
    print(f"Q1: PIPELINE referral precision > STATIC by >5pp? (see above)")
    print(f"Q3: PIPELINE achieves sharper boundaries? (see gap>0.30 above)")
    print(f"Q4: PIPELINE probe stability > 95%? (see above)")
    print(f"Q5: RAW SGD probe stability < 80%? (see above)")

    print("\nDONE.")


if __name__ == "__main__":
    main()
