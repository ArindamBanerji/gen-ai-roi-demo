"""
EXP-26: V-COUPLING-ISOLATION
==============================
Break the feedback loop to measure coupling strength.
Does decoupling the gate from confidence fix cold start?

Run: cd backend && python scripts/exp26_coupling.py
Time: ~20 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF, SIGMA_BAR
)


N = 2000
CHECKPOINTS = [50, 100, 200, 500, 1000, 2000]


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


def run_coupled(seed, config):
    """
    FULL: normal pipeline (gate uses live confidence)
    DECOUPLED_GATE: gate uses INITIAL confidence distribution (frozen at N=0)
    DECOUPLED_BATCH: batch uses fixed sigma, doesn't adapt
    """
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)

    scorer = make_scorer()
    initial_scorer = make_scorer()  # frozen copy for decoupled gate

    pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                   category_weights=CATEGORY_WEIGHTS)

    lc = 0
    all_confs = []
    all_corrects = []
    cp = {}

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

        if config == "FULL":
            pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)

        elif config == "DECOUPLED_GATE":
            # Gate decision based on INITIAL scorer's confidence (frozen)
            initial_result = initial_scorer.score(fv, ci)
            initial_conf = initial_result.confidence
            # Use initial confidence for gating, but actual scorer for everything else
            pipeline.process(fv, ci, result.action_index, correct, oa, initial_conf)

        elif config == "DECOUPLED_BATCH":
            # Gate uses live confidence (normal)
            # But we override the sigma in significance test to be fixed
            # (This is approximate — we process normally but the pipeline
            # internally uses SIGMA_BAR which is already fixed)
            pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)

        if n in CHECKPOINTS:
            confs = np.array(all_confs)
            corrs = np.array(all_corrects)
            cp[n] = {
                'acc': lc / n * 100,
                'ece': compute_ece(confs, corrs),
                'gate_rej': pipeline.stats['gate_blocked'] / (pipeline.stats['gate_blocked'] + pipeline.stats['gate_passed'])
                            if (pipeline.stats['gate_blocked'] + pipeline.stats['gate_passed']) > 0 else 0,
                'updates': pipeline.stats['updates'],
            }

    return cp


def main():
    print("=" * 80)
    print("EXP-26: V-COUPLING-ISOLATION")
    print("=" * 80)

    configs = ["FULL", "DECOUPLED_GATE"]  # DECOUPLED_BATCH is same as FULL (sigma already fixed)

    # Run from CALIBRATED prior
    print("\n  From CALIBRATED prior:")
    for config in configs:
        all_r = [run_coupled(s, config) for s in SEEDS]
        print(f"\n  {config}:")
        print(f"  {'N':>6s}  {'acc':>6s}  {'ECE':>8s}  {'gate_rej':>8s}  {'updates':>7s}")
        print(f"  {'-' * 40}")
        for n in CHECKPOINTS:
            accs = [r[n]['acc'] for r in all_r]
            eces = [r[n]['ece'] for r in all_r]
            grs = [r[n]['gate_rej'] * 100 for r in all_r]
            ups = [r[n]['updates'] for r in all_r]
            print(f"  {n:>6d}  {np.mean(accs):5.1f}%  {np.mean(eces):8.4f}  "
                  f"{np.mean(grs):6.1f}%  {np.mean(ups):>5.0f}")

    # Run from GENERIC prior (cold start test)
    print("\n\n  From GENERIC prior (cold start):")
    for config in configs:
        all_r_generic = []
        for seed in SEEDS:
            rng = np.random.default_rng(seed)
            base_mu = get_base_centroids()
            gt = build_gt(rng, base_mu)

            generic = np.full((C, A, D), 0.5)
            scorer = make_scorer(generic)
            initial_scorer = make_scorer(generic)

            pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                           category_weights=CATEGORY_WEIGHTS)

            lc = 0
            cp = {}
            for n in range(1, N + 1):
                ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                ta = true_action(gt, ci, fv)
                oa = noise_realistic(ta, ci, rng)

                result = scorer.score(fv, ci)
                correct = (result.action_index == oa)
                if correct: lc += 1

                if config == "FULL":
                    pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)
                elif config == "DECOUPLED_GATE":
                    initial_result = initial_scorer.score(fv, ci)
                    pipeline.process(fv, ci, result.action_index, correct, oa, initial_result.confidence)

                if n in CHECKPOINTS:
                    cp[n] = {
                        'acc': lc / n * 100,
                        'updates': pipeline.stats['updates'],
                    }
            all_r_generic.append(cp)

        print(f"\n  {config} (GENERIC):")
        print(f"  {'N':>6s}  {'acc':>6s}  {'updates':>7s}")
        print(f"  {'-' * 25}")
        for n in CHECKPOINTS:
            accs = [r[n]['acc'] for r in all_r_generic]
            ups = [r[n]['updates'] for r in all_r_generic]
            print(f"  {n:>6d}  {np.mean(accs):5.1f}%  {np.mean(ups):>5.0f}")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    # Q4: Does decoupled gate show faster cold-start learning?
    full_generic = [run_coupled(s, "FULL") for s in SEEDS]  # rerun isn't ideal but works
    # Use the generic results from above
    print(f"Q4: Does DECOUPLED_GATE improve cold-start learning?")
    print(f"    (Compare GENERIC accuracy trajectories above)")

    print("\nDONE.")


if __name__ == "__main__":
    main()
