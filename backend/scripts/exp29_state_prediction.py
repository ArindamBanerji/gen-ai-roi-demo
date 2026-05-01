"""
EXP-29: V-STATE-PREDICTION
============================
Can we PREDICT w(t+delta) from the current state s(t)?
Direct test of whether F is identifiable from data.

Run: cd backend && python scripts/exp29_state_prediction.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF
)

N = 4000
WINDOW = 50
ALL_SEEDS = [42, 123, 777, 2024, 9999, 31415, 27182, 11235, 81321, 14142]
TRAIN_SEEDS = ALL_SEEDS[:8]
VAL_SEEDS = ALL_SEEDS[8:]


def run_trajectory(seed):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)

    scorer_pipe = make_scorer()
    scorer_raw = make_scorer()
    scorer_static = make_scorer()

    pipeline = ThreeStagePipeline(scorer_pipe, K=K_BATCH, theta_conf=THETA_CONF,
                                   category_weights=CATEGORY_WEIGHTS)

    lc_p, lc_r, lc_s = 0, 0, 0
    prev_mu = scorer_pipe.centroids.copy()
    window_confs = []
    window_gated = 0
    window_total = 0
    prev_updates = 0
    timeline = []

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng)

        r_p = scorer_pipe.score(fv, ci)
        if r_p.action_index == oa: lc_p += 1
        pipeline.process(fv, ci, r_p.action_index, r_p.action_index == oa, oa, r_p.confidence)

        r_r = scorer_raw.score(fv, ci)
        if r_r.action_index == oa: lc_r += 1
        scorer_raw.update(fv, ci, r_r.action_index, r_r.action_index == oa, oa)

        r_s = scorer_static.score(fv, ci)
        if r_s.action_index == oa: lc_s += 1

        window_confs.append(r_p.confidence)
        window_total += 1
        if r_p.confidence > THETA_CONF:
            window_gated += 1

        if n % WINDOW == 0:
            acc_p = lc_p / n * 100
            acc_r = lc_r / n * 100
            acc_s = lc_s / n * 100

            velocity = np.linalg.norm(scorer_pipe.centroids - prev_mu) / WINDOW
            confs = np.array(window_confs)
            gate_rej = window_gated / window_total if window_total > 0 else 0
            new_updates = pipeline.stats['updates'] - prev_updates
            sig_rate = pipeline.stats['batch_sig'] / max(pipeline.stats['batch_total'], 1)

            # Pipeline contribution (target variable)
            pipe_contrib = acc_p - acc_r

            # State features
            timeline.append({
                'n': n,
                # Target
                'w_pipeline': pipe_contrib,
                # State features
                'accuracy': acc_p,
                'velocity': velocity,
                'mean_conf': np.mean(confs),
                'pct_conf_above_60': np.mean(confs > 0.60) * 100,
                'pct_conf_above_80': np.mean(confs > 0.80) * 100,
                'gate_rejection': gate_rej * 100,
                'sig_rate': sig_rate * 100,
                'update_rate': new_updates / WINDOW * 100,
                'frobenius_from_init': float(np.linalg.norm(scorer_pipe.centroids - base_mu)),
            })

            prev_mu = scorer_pipe.centroids.copy()
            prev_updates = pipeline.stats['updates']
            window_confs = []
            window_gated = 0
            window_total = 0

    return timeline


def fit_linear_model(X, y):
    """OLS fit. Returns coefficients and predictions."""
    X_bias = np.column_stack([np.ones(len(X)), X])
    try:
        beta = np.linalg.lstsq(X_bias, y, rcond=None)[0]
        y_pred = X_bias @ beta
        return beta, y_pred
    except np.linalg.LinAlgError:
        return None, np.zeros_like(y)


def main():
    print("=" * 80)
    print("EXP-29: V-STATE-PREDICTION")
    print(f"10 seeds: 8 train, 2 validation")
    print("=" * 80)

    # Collect all trajectories
    train_tls = [run_trajectory(s) for s in TRAIN_SEEDS]
    val_tls = [run_trajectory(s) for s in VAL_SEEDS]
    print(f"  {len(TRAIN_SEEDS)} train + {len(VAL_SEEDS)} val seeds done")

    # Flatten to arrays
    feature_names = ['accuracy', 'velocity', 'mean_conf', 'pct_conf_above_60',
                     'pct_conf_above_80', 'gate_rejection', 'sig_rate',
                     'update_rate', 'frobenius_from_init']

    def extract_arrays(tls):
        N_arr = []
        X = {f: [] for f in feature_names}
        y = []
        for tl in tls:
            for pt in tl:
                N_arr.append(pt['n'])
                for f in feature_names:
                    X[f].append(pt[f])
                y.append(pt['w_pipeline'])
        return np.array(N_arr), {f: np.array(v) for f, v in X.items()}, np.array(y)

    N_train, X_train, y_train = extract_arrays(train_tls)
    N_val, X_val, y_val = extract_arrays(val_tls)

    # MODEL A: w_pipeline = b0 + b1*N (pure time)
    beta_A, pred_A_train = fit_linear_model(N_train.reshape(-1, 1), y_train)
    _, pred_A_val = fit_linear_model(N_val.reshape(-1, 1), y_val) if beta_A is not None else (None, np.zeros_like(y_val))
    if beta_A is not None:
        X_val_bias = np.column_stack([np.ones(len(N_val)), N_val])
        pred_A_val = X_val_bias @ beta_A

    rmse_A_train = np.sqrt(np.mean((y_train - pred_A_train) ** 2))
    rmse_A_val = np.sqrt(np.mean((y_val - pred_A_val) ** 2))

    # MODEL B: w_pipeline = b0 + b1*acc + b2*velocity + b3*mean_conf (state only, no time)
    state_features_B = ['accuracy', 'velocity', 'mean_conf']
    X_B_train = np.column_stack([X_train[f] for f in state_features_B])
    X_B_val = np.column_stack([X_val[f] for f in state_features_B])
    beta_B, pred_B_train = fit_linear_model(X_B_train, y_train)
    if beta_B is not None:
        X_B_val_bias = np.column_stack([np.ones(len(X_B_val)), X_B_val])
        pred_B_val = X_B_val_bias @ beta_B
    else:
        pred_B_val = np.zeros_like(y_val)

    rmse_B_train = np.sqrt(np.mean((y_train - pred_B_train) ** 2))
    rmse_B_val = np.sqrt(np.mean((y_val - pred_B_val) ** 2))

    # MODEL C: w_pipeline = b0 + b1*N + b2*acc + b3*velocity + b4*gate_rejection (mixed)
    mixed_features = ['accuracy', 'velocity', 'gate_rejection']
    X_C_train = np.column_stack([N_train] + [X_train[f] for f in mixed_features])
    X_C_val = np.column_stack([N_val] + [X_val[f] for f in mixed_features])
    beta_C, pred_C_train = fit_linear_model(X_C_train, y_train)
    if beta_C is not None:
        X_C_val_bias = np.column_stack([np.ones(len(X_C_val)), X_C_val])
        pred_C_val = X_C_val_bias @ beta_C
    else:
        pred_C_val = np.zeros_like(y_val)

    rmse_C_train = np.sqrt(np.mean((y_train - pred_C_train) ** 2))
    rmse_C_val = np.sqrt(np.mean((y_val - pred_C_val) ** 2))

    # Results
    print(f"\n{'=' * 80}")
    print("MODEL COMPARISON")
    print(f"{'=' * 80}")
    print(f"  {'Model':>25s}  {'Train RMSE':>10s}  {'Val RMSE':>10s}  {'Val < 0.05?':>11s}")
    print(f"  {'-' * 60}")
    print(f"  {'A: w = f(N)':>25s}  {rmse_A_train:>10.4f}  {rmse_A_val:>10.4f}  "
          f"{'YES' if rmse_A_val < 0.05 else 'NO'}")
    print(f"  {'B: w = f(acc,vel,conf)':>25s}  {rmse_B_train:>10.4f}  {rmse_B_val:>10.4f}  "
          f"{'YES' if rmse_B_val < 0.05 else 'NO'}")
    print(f"  {'C: w = f(N,acc,vel,gate)':>25s}  {rmse_C_train:>10.4f}  {rmse_C_val:>10.4f}  "
          f"{'YES' if rmse_C_val < 0.05 else 'NO'}")

    # Coefficients
    if beta_B is not None:
        print(f"\n  MODEL B coefficients:")
        print(f"    intercept: {beta_B[0]:+.4f}")
        for i, f in enumerate(state_features_B):
            print(f"    {f}: {beta_B[i+1]:+.6f}")

    if beta_C is not None:
        print(f"\n  MODEL C coefficients:")
        print(f"    intercept: {beta_C[0]:+.4f}")
        print(f"    N: {beta_C[1]:+.8f}")
        for i, f in enumerate(mixed_features):
            print(f"    {f}: {beta_C[i+2]:+.6f}")

    # Feature importance (absolute beta * std)
    if beta_B is not None:
        print(f"\n  Feature importance (|beta * std|) for Model B:")
        importances = []
        for i, f in enumerate(state_features_B):
            imp = abs(beta_B[i+1]) * np.std(X_train[f])
            importances.append((f, imp))
        importances.sort(key=lambda x: -x[1])
        for f, imp in importances:
            print(f"    {f}: {imp:.4f}")

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    print(f"Q1: Model B (state) outperforms Model A (time)? "
          f"B_val={rmse_B_val:.4f} A_val={rmse_A_val:.4f} "
          f"{'YES' if rmse_B_val < rmse_A_val else 'NO'}")

    print(f"Q2: Model C improves over Model B? "
          f"C_val={rmse_C_val:.4f} B_val={rmse_B_val:.4f} "
          f"{'YES' if rmse_C_val < rmse_B_val - 0.005 else 'NO'}")

    print(f"Q3: Validation RMSE < 0.05 for any model? "
          f"{'YES' if min(rmse_A_val, rmse_B_val, rmse_C_val) < 0.05 else 'NO'}")

    if beta_B is not None:
        importances.sort(key=lambda x: -x[1])
        print(f"Q4: Top 3 state drivers: {', '.join(f'{f}({imp:.4f})' for f, imp in importances[:3])}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
