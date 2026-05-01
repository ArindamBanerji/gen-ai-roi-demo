"""
EXP-D7: BOOTSTRAP-THEN-HANDOFF
=================================
Tests H4: cold start needs aggressive raw SGD, then handoff
to designed controller.

Run: cd backend && python scripts/exp_d7_bootstrap.py
Time: ~15 min
"""

import numpy as np
from collections import deque
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF
)

N = 2000
CHECKPOINTS = [50, 100, 200, 500, 1000, 2000]
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


def run_bootstrap(seed, bootstrap_n, bootstrap_eta, post_strategy, gt):
    """Run raw SGD for bootstrap_n decisions, then switch to post_strategy."""
    rng = np.random.default_rng(seed)
    generic = np.full((C, A, D), 0.5)
    scorer = make_scorer(generic)
    ca_counts = np.zeros((C, A))

    pipeline = None
    if post_strategy == "PIPELINE":
        pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                       category_weights=CATEGORY_WEIGHTS)

    lc = 0
    all_confs, all_corrects = [], []
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

        if n <= bootstrap_n:
            # BOOTSTRAP: aggressive raw SGD
            eta_scale = bootstrap_eta / 0.05
            mu_ca = scorer.centroids[ci, oa]
            eff_fv = mu_ca + eta_scale * (fv - mu_ca)
            scorer.update(eff_fv.astype(np.float64), ci, result.action_index, correct, oa)
        else:
            # POST-BOOTSTRAP: designed controller
            if post_strategy == "STATIC":
                pass
            elif post_strategy == "PIPELINE":
                pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)
            elif post_strategy == "GATE_DECAY":
                if result.confidence <= THETA_CONF:
                    n_ca = ca_counts[ci, oa]
                    scale = 1.0 / np.sqrt(1.0 + n_ca / 10.0)
                    mu_ca = scorer.centroids[ci, oa]
                    eff_fv = mu_ca + max(scale, 0.01) * (fv - mu_ca)
                    scorer.update(eff_fv.astype(np.float64), ci,
                                  result.action_index, correct, oa)
                    ca_counts[ci, oa] += 1
            elif post_strategy == "RAW_CONTINUED":
                # Continue raw SGD at SAME bootstrap eta
                eta_scale = bootstrap_eta / 0.05
                mu_ca = scorer.centroids[ci, oa]
                eff_fv = mu_ca + eta_scale * (fv - mu_ca)
                scorer.update(eff_fv.astype(np.float64), ci,
                              result.action_index, correct, oa)

        if n in CHECKPOINTS:
            confs = np.array(all_confs)
            corrs = np.array(all_corrects)
            cp[n] = {
                'acc': lc / n * 100,
                'ece': compute_ece(confs, corrs),
            }

    return cp


def main():
    print("=" * 80)
    print("EXP-D7: BOOTSTRAP-THEN-HANDOFF (from GENERIC prior)")
    print("=" * 80)

    base_mu = get_base_centroids()

    # Grid: bootstrap_n × bootstrap_eta × post_strategy
    bootstrap_ns = [0, 50, 100, 200, 500]
    bootstrap_etas = [0.10, 0.15, 0.20]
    post_strategies = ["STATIC", "PIPELINE", "GATE_DECAY", "RAW_CONTINUED"]

    # First: find best bootstrap_n and eta (with STATIC post-bootstrap)
    print(f"\n  BOOTSTRAP PHASE OPTIMIZATION (post=STATIC):")
    print(f"  {'boot_n':>6s}  {'boot_eta':>8s}  {'Acc@200':>7s}  {'Acc@2000':>8s}  {'ECE@2000':>8s}")
    print(f"  {'-' * 45}")

    best_2000 = 0
    best_config = None

    for bn in bootstrap_ns:
        for be in bootstrap_etas:
            if bn == 0:
                if be != bootstrap_etas[0]:
                    continue  # skip redundant zero-bootstrap runs
            runs = []
            for seed in SEEDS_SHORT:
                gt = build_gt(np.random.default_rng(seed), base_mu)
                r = run_bootstrap(seed, bn, be, "STATIC", gt)
                runs.append(r)
            acc_200 = np.mean([r[200]['acc'] for r in runs])
            acc_2000 = np.mean([r[N]['acc'] for r in runs])
            ece_2000 = np.mean([r[N]['ece'] for r in runs])
            if acc_2000 > best_2000:
                best_2000 = acc_2000
                best_config = (bn, be)
            print(f"  {bn:>6d}  {be:>8.2f}  {acc_200:>5.1f}%  {acc_2000:>6.1f}%  {ece_2000:>8.4f}")

    print(f"\n  Best bootstrap config: N={best_config[0]}, eta={best_config[1]}")

    # Then: test post-bootstrap strategies with best bootstrap
    bn_best, be_best = best_config
    print(f"\n  POST-BOOTSTRAP COMPARISON (bootstrap N={bn_best}, eta={be_best}):")
    print(f"  {'Post Strategy':>15s}  {'Acc@500':>7s}  {'Acc@2000':>8s}  {'ECE@2000':>8s}")
    print(f"  {'-' * 42}")

    for ps in post_strategies:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_bootstrap(seed, bn_best, be_best, ps, gt)
            runs.append(r)
        acc_500 = np.mean([r[500]['acc'] for r in runs])
        acc_2000 = np.mean([r[N]['acc'] for r in runs])
        ece_2000 = np.mean([r[N]['ece'] for r in runs])
        print(f"  {ps:>15s}  {acc_500:>5.1f}%  {acc_2000:>6.1f}%  {ece_2000:>8.4f}")

    # Compare to pure strategies (no bootstrap)
    print(f"\n  COMPARISON: Bootstrap+handoff vs pure strategies:")
    print(f"  {'Strategy':>25s}  {'Acc@2000':>8s}")
    print(f"  {'-' * 37}")

    # Pure RAW
    for be in [0.05, 0.10, 0.20]:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_bootstrap(seed, N, be, "RAW_CONTINUED", gt)  # all bootstrap, no handoff
            runs.append(r)
        acc = np.mean([r[N]['acc'] for r in runs])
        print(f"  {'Pure RAW eta=' + str(be):>25s}  {acc:>6.1f}%")

    # Bootstrap + best post
    for ps in post_strategies:
        runs = []
        for seed in SEEDS_SHORT:
            gt = build_gt(np.random.default_rng(seed), base_mu)
            r = run_bootstrap(seed, bn_best, be_best, ps, gt)
            runs.append(r)
        acc = np.mean([r[N]['acc'] for r in runs])
        print(f"  {'Boot' + str(bn_best) + '+' + ps:>25s}  {acc:>6.1f}%")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    print(f"Q1: Does bootstrap+handoff beat pure RAW at N=2000?")
    print(f"Q2: Does bootstrap+handoff beat pure PIPELINE from generic?")
    print(f"Q3: Best post-bootstrap strategy?")
    print(f"Q4: Optimal bootstrap length? N={best_config[0]}")
    print(f"Q5: H4 confirmed? (Cold start needs aggressive eta, not smart controller)")

    print("\nDONE.")


if __name__ == "__main__":
    main()
