"""
EXP-ORDER-3: DK TRANSFER, COMPOSITION, AND SATURATION
=========================================================
Three questions that determine the compounding framework:

Q1: Does Firm A's DK weights help Firm B?
    (If YES: DK provides cross-deployment compounding)
    
Q2: Does bounded MLP on top of DK beat DK alone?
    (If YES: the three-layer architecture is justified)
    
Q3: Where does the DK learning curve plateau?
    (Determines the saturation point for variance learning)

Run: cd backend && python scripts/exp_order3_gaps.py
Time: ~25 min
"""

import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score
from exp_shared import (
    C, A, D, CATEGORIES, ACTIONS, SEEDS, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer
)

N_TEST = 500
FREEZE_AT = 500


def score_dk(fv, ci, centroids, weights):
    sims = []
    for ai in range(A):
        diff = fv - centroids[ci, ai]
        sims.append(-np.sum(weights[ci, ai] * diff ** 2))
    return int(np.argmax(sims))


def estimate_dk_from_decisions(decisions, centroids, n_rounds=5):
    weights = np.ones((C, A, D))
    for _ in range(n_rounds):
        for ci in range(C):
            for ai in range(A):
                for di in range(D):
                    cat_decs = [(fv, oa) for fv, cat, oa in decisions if cat == ci]
                    if len(cat_decs) < 10:
                        continue
                    best_w = weights[ci, ai, di]
                    best_acc = sum(1 for fv, oa in cat_decs
                                  if score_dk(fv, ci, centroids, weights) == oa) / len(cat_decs)
                    for w_trial in [0.1, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0]:
                        trial_w = weights.copy()
                        trial_w[ci, ai, di] = w_trial
                        trial_acc = sum(1 for fv, oa in cat_decs
                                        if score_dk(fv, ci, centroids, trial_w) == oa) / len(cat_decs)
                        if trial_acc > best_acc:
                            best_acc = trial_acc
                            best_w = w_trial
                    weights[ci, ai, di] = best_w
    return weights


def collect_decisions(gt, seed, N, freeze_scorer=None):
    """Collect N decisions. If freeze_scorer provided, use its frozen centroids."""
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    scorer = make_scorer(base_mu.copy())
    decisions = []

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)
        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        if n <= FREEZE_AT:
            scorer.update(fv, ci, result.action_index, correct, oa)
        decisions.append((fv, ci, oa))

    return decisions, scorer.centroids.copy()


def evaluate_on_test(scorer_func, test_data):
    correct = sum(1 for fv, ci, oa in test_data if scorer_func(fv, ci) == oa)
    return correct / len(test_data) * 100


def main():
    base_mu = get_base_centroids()

    # ═══════════════════════════════════════════════════════════════
    # Q1: DK TRANSFER
    # Does Firm A's DK weights help Firm B?
    # ═══════════════════════════════════════════════════════════════
    print("=" * 90)
    print("Q1: DK TRANSFER")
    print("Does Firm A's DK weights help Firm B?")
    print("=" * 90)

    print(f"\n  {'Config':>30s}  {'Acc':>6s}  {'Delta vs centroid':>13s}")
    print(f"  {'-' * 55}")

    transfer_results = {}
    seed_pairs = [(42, 123), (123, 777), (777, 42)]

    for config in ["Centroid only", "DK from Firm A", "DK from Firm B",
                    "DK from A+B", "MLP from Firm A (G3)"]:
        accs = []
        for seed_a, seed_b in seed_pairs:
            gt_a = build_gt(np.random.default_rng(seed_a), base_mu)
            gt_b = build_gt(np.random.default_rng(seed_b), base_mu)

            # Firm A data + frozen centroids
            decs_a, mu_a = collect_decisions(gt_a, seed_a, 2000)
            # Firm B data + frozen centroids
            decs_b, mu_b = collect_decisions(gt_b, seed_b, 2000)

            # Test on Firm B
            rng_test = np.random.default_rng(seed_b + 50000)
            test_data = []
            for _ in range(N_TEST):
                ci = int(rng_test.choice(C, p=CATEGORY_WEIGHTS))
                fv = np.clip(rng_test.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
                ta = true_action(gt_b, ci, fv)
                oa = noise_realistic(ta, ci, rng_test)
                test_data.append((fv, ci, oa))

            if config == "Centroid only":
                scorer = make_scorer(base_mu.copy())
                acc = evaluate_on_test(lambda fv, ci: scorer.score(fv, ci).action_index, test_data)

            elif config == "DK from Firm A":
                w_a = estimate_dk_from_decisions(decs_a, base_mu, n_rounds=5)
                acc = evaluate_on_test(lambda fv, ci: score_dk(fv, ci, base_mu, w_a), test_data)

            elif config == "DK from Firm B":
                w_b = estimate_dk_from_decisions(decs_b, base_mu, n_rounds=5)
                acc = evaluate_on_test(lambda fv, ci: score_dk(fv, ci, base_mu, w_b), test_data)

            elif config == "DK from A+B":
                decs_ab = decs_a + decs_b
                w_ab = estimate_dk_from_decisions(decs_ab, base_mu, n_rounds=5)
                acc = evaluate_on_test(lambda fv, ci: score_dk(fv, ci, base_mu, w_ab), test_data)

            elif config == "MLP from Firm A (G3)":
                # From G3: MLP trained on A hurts B by -2.2pp
                acc = -999  # placeholder, use G3 result
                accs.append(77.3)  # G3 mean
                continue

            accs.append(acc)

        mean_acc = np.mean(accs)
        transfer_results[config] = mean_acc
        cent_base = transfer_results.get("Centroid only", mean_acc)
        print(f"  {config:>30s}  {mean_acc:>4.1f}%  {mean_acc - cent_base:>+11.1f}pp")

    # DK weight similarity across firms
    print(f"\n  DK WEIGHT SIMILARITY ACROSS FIRMS:")
    for seed_a, seed_b in seed_pairs[:2]:
        gt_a = build_gt(np.random.default_rng(seed_a), base_mu)
        gt_b = build_gt(np.random.default_rng(seed_b), base_mu)
        decs_a, _ = collect_decisions(gt_a, seed_a, 2000)
        decs_b, _ = collect_decisions(gt_b, seed_b, 2000)
        w_a = estimate_dk_from_decisions(decs_a, base_mu, n_rounds=5)
        w_b = estimate_dk_from_decisions(decs_b, base_mu, n_rounds=5)
        corr = np.corrcoef(w_a.flatten(), w_b.flatten())[0, 1]
        cos = np.dot(w_a.flatten(), w_b.flatten()) / (
            np.linalg.norm(w_a.flatten()) * np.linalg.norm(w_b.flatten()))
        print(f"    Firm {seed_a} vs Firm {seed_b}: corr={corr:+.3f} cos={cos:.3f}")

    # ═══════════════════════════════════════════════════════════════
    # Q2: DK + MLP COMPOSITION
    # Does bounded MLP on top of DK beat DK alone?
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("Q2: DK + MLP COMPOSITION")
    print("Does bounded MLP on DK residuals beat DK alone?")
    print("=" * 90)

    for seed in SEEDS[:3]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        decs, frozen_mu = collect_decisions(gt, seed, 2000)

        # Test data
        rng_test = np.random.default_rng(seed + 50000)
        test_data = []
        for _ in range(N_TEST):
            ci = int(rng_test.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_test.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng_test)
            test_data.append((fv, ci, oa))

        # Layer 1: Centroid only
        scorer = make_scorer(frozen_mu)
        cent_acc = evaluate_on_test(lambda fv, ci: scorer.score(fv, ci).action_index, test_data)

        # Layer 1.5: DK on frozen centroids
        dk_weights = estimate_dk_from_decisions(decs, frozen_mu, n_rounds=5)
        dk_acc = evaluate_on_test(lambda fv, ci: score_dk(fv, ci, frozen_mu, dk_weights), test_data)

        # Layer 2a: Bounded MLP on centroid residuals (standard approach)
        X_train = np.array([np.concatenate([fv, np.eye(C)[ci]]) for fv, ci, oa in decs])
        y_train = np.array([oa for fv, ci, oa in decs])

        cent_preds_train = np.array([scorer.score(fv, ci).action_index for fv, ci, oa in decs])
        feat_train_c = np.column_stack([X_train, np.eye(A)[cent_preds_train]])

        X_test = np.array([np.concatenate([fv, np.eye(C)[ci]]) for fv, ci, oa in test_data])
        y_test = np.array([oa for fv, ci, oa in test_data])
        cent_preds_test = np.array([scorer.score(fv, ci).action_index for fv, ci, oa in test_data])
        feat_test_c = np.column_stack([X_test, np.eye(A)[cent_preds_test]])

        # Centroid gaps for bounding
        cent_gaps = []
        for fv, ci, oa in test_data:
            result = scorer.score(fv, ci)
            probs = np.array(result.probabilities)
            sp = np.sort(probs)[::-1]
            cent_gaps.append(sp[0] - sp[1])
        cent_gaps = np.array(cent_gaps)

        mlp_on_cent = MLPClassifier(hidden_layer_sizes=(32,), max_iter=1000, random_state=seed)
        mlp_on_cent.fit(feat_train_c, y_train)
        mlp_cent_preds = mlp_on_cent.predict(feat_test_c)

        bounded_cent = cent_preds_test.copy()
        for i in range(N_TEST):
            if mlp_cent_preds[i] != cent_preds_test[i] and cent_gaps[i] <= 0.30:
                bounded_cent[i] = mlp_cent_preds[i]
        mlp_on_cent_acc = accuracy_score(y_test, bounded_cent) * 100

        # Layer 2b: Bounded MLP on DK residuals (composed)
        dk_preds_train = np.array([score_dk(fv, ci, frozen_mu, dk_weights) for fv, ci, oa in decs])
        feat_train_dk = np.column_stack([X_train, np.eye(A)[dk_preds_train]])

        dk_preds_test = np.array([score_dk(fv, ci, frozen_mu, dk_weights) for fv, ci, oa in test_data])
        feat_test_dk = np.column_stack([X_test, np.eye(A)[dk_preds_test]])

        # DK gaps for bounding (approximate from DK scores)
        dk_gaps = []
        for fv, ci, oa in test_data:
            sims = []
            for ai in range(A):
                diff = fv - frozen_mu[ci, ai]
                sims.append(-np.sum(dk_weights[ci, ai] * diff ** 2))
            sims = np.array(sims)
            sims_sorted = np.sort(sims)[::-1]
            dk_gaps.append(sims_sorted[0] - sims_sorted[1])
        dk_gaps = np.array(dk_gaps)
        # Normalize gaps to [0, 1] range for bounding
        if dk_gaps.max() > 0:
            dk_gaps_norm = dk_gaps / dk_gaps.max()
        else:
            dk_gaps_norm = dk_gaps

        mlp_on_dk = MLPClassifier(hidden_layer_sizes=(32,), max_iter=1000, random_state=seed)
        mlp_on_dk.fit(feat_train_dk, y_train)
        mlp_dk_preds = mlp_on_dk.predict(feat_test_dk)

        bounded_dk = dk_preds_test.copy()
        for i in range(N_TEST):
            if mlp_dk_preds[i] != dk_preds_test[i] and dk_gaps_norm[i] <= 0.30:
                bounded_dk[i] = mlp_dk_preds[i]
        mlp_on_dk_acc = accuracy_score(y_test, bounded_dk) * 100

        # Unbounded MLP on DK
        unbounded_dk_acc = accuracy_score(y_test, mlp_dk_preds) * 100

        # Unbounded MLP standalone
        mlp_standalone = MLPClassifier(hidden_layer_sizes=(32,), max_iter=1000, random_state=seed)
        mlp_standalone.fit(X_train, y_train)
        standalone_preds = mlp_standalone.predict(X_test)
        standalone_acc = accuracy_score(y_test, standalone_preds) * 100

        print(f"\n  Seed {seed}:")
        print(f"  {'Config':>30s}  {'Acc':>6s}  {'Delta vs cent':>9s}  {'Layers':>10s}")
        print(f"  {'-' * 60}")
        print(f"  {'Centroid only':>30s}  {cent_acc:>4.1f}%  {'--':>9s}  {'L1':>10s}")
        print(f"  {'DK on frozen':>30s}  {dk_acc:>4.1f}%  {dk_acc-cent_acc:>+7.1f}pp  {'L1+L1.5':>10s}")
        print(f"  {'Bounded MLP on centroid':>30s}  {mlp_on_cent_acc:>4.1f}%  {mlp_on_cent_acc-cent_acc:>+7.1f}pp  {'L1+L2':>10s}")
        print(f"  {'Bounded MLP on DK':>30s}  {mlp_on_dk_acc:>4.1f}%  {mlp_on_dk_acc-cent_acc:>+7.1f}pp  {'L1+L1.5+L2':>10s}")
        print(f"  {'Unbounded MLP on DK':>30s}  {unbounded_dk_acc:>4.1f}%  {unbounded_dk_acc-cent_acc:>+7.1f}pp  {'L1+L1.5+L2*':>10s}")
        print(f"  {'MLP standalone':>30s}  {standalone_acc:>4.1f}%  {standalone_acc-cent_acc:>+7.1f}pp  {'L2 only':>10s}")

    # ═══════════════════════════════════════════════════════════════
    # Q3: DK SATURATION
    # Extended learning curve to N=8000
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("Q3: DK SATURATION")
    print("Extended learning curve: where does DK plateau?")
    print("=" * 90)

    N_EXTENDED = 8000
    checkpoints = [200, 500, 1000, 1500, 2000, 3000, 4000, 5000, 6000, 7000, 8000]

    for seed in SEEDS[:3]:
        gt = build_gt(np.random.default_rng(seed), base_mu)
        rng = np.random.default_rng(seed)

        # Collect extended decisions
        scorer = make_scorer(base_mu.copy())
        all_decisions = []
        for n in range(1, N_EXTENDED + 1):
            ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng)
            result = scorer.score(fv, ci)
            if n <= FREEZE_AT:
                scorer.update(fv, ci, result.action_index,
                              result.action_index == oa, oa)
            all_decisions.append((fv, ci, oa))

        frozen_mu = scorer.centroids.copy()

        # Test data
        rng_test = np.random.default_rng(seed + 50000)
        test_data = []
        for _ in range(N_TEST):
            ci = int(rng_test.choice(C, p=CATEGORY_WEIGHTS))
            fv = np.clip(rng_test.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
            ta = true_action(gt, ci, fv)
            oa = noise_realistic(ta, ci, rng_test)
            test_data.append((fv, ci, oa))

        cent_acc = evaluate_on_test(
            lambda fv, ci: make_scorer(frozen_mu).score(fv, ci).action_index, test_data)

        print(f"\n  Seed {seed} (centroid baseline: {cent_acc:.1f}%):")
        print(f"  {'N':>6s}  {'DK_acc':>7s}  {'DK-Cent':>7s}  {'Delta from prev':>11s}  {'Marginal/1000':>13s}")
        print(f"  {'-' * 55}")

        prev_acc = cent_acc
        prev_n = 0
        for cp in checkpoints:
            if cp > N_EXTENDED:
                break
            decs = all_decisions[:cp]
            w = estimate_dk_from_decisions(decs, frozen_mu, n_rounds=5)
            dk_acc = evaluate_on_test(
                lambda fv, ci, w=w: score_dk(fv, ci, frozen_mu, w), test_data)

            delta = dk_acc - prev_acc
            marginal = delta / max((cp - prev_n) / 1000, 0.001) if cp > prev_n else 0

            print(f"  {cp:>6d}  {dk_acc:>5.1f}%  {dk_acc-cent_acc:>+5.1f}pp  "
                  f"{delta:>+9.1f}pp  {marginal:>+11.1f}pp")

            prev_acc = dk_acc
            prev_n = cp

    # ═══════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'=' * 90}")
    print("BINARY ANSWERS")
    print("=" * 90)
    print("Q1: Does Firm A's DK help Firm B? (compare to G3 MLP transfer at -2.2pp)")
    print("Q2: Does L1+L1.5+L2 > max(L1+L1.5, L1+L2)?")
    print("Q3: At what N does DK marginal gain drop below +0.1pp/1000?")

    print("\nDONE.")


if __name__ == "__main__":
    main()
