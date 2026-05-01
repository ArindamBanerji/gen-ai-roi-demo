"""
EXP-31: V-FREQUENCY-RESPONSE
==============================
Bode plot equivalent: what frequency of change does the system track vs reject?

Run: cd backend && python scripts/exp31_frequency.py
Time: ~20 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, CATEGORY_WEIGHTS,
    get_base_centroids, build_gt, true_action, noise_realistic,
    make_scorer, ThreeStagePipeline, K_BATCH, THETA_CONF,
    FREQ_NOISE, ADJACENT
)

PERIODS = [20, 50, 100, 200, 500, 1000, 2000]
N = 4000
SEEDS_SHORT = [42, 123, 777]


def noise_periodic(gt_a, ci, rng, n, period):
    """Oracle noise rate oscillates sinusoidally."""
    base_rate = FREQ_NOISE.get(ci, 0.15)
    rate = base_rate + 0.10 * np.sin(2 * np.pi * n / period)
    rate = np.clip(rate, 0.01, 0.40)
    if rng.random() < rate:
        nbrs = ADJACENT.get(gt_a, [])
        if nbrs:
            return int(rng.choice(nbrs))
        wrong = [a for a in range(A) if a != gt_a]
        return int(rng.choice(wrong))
    return gt_a


def run_frequency(seed, period, strategy):
    rng = np.random.default_rng(seed)
    base_mu = get_base_centroids()
    gt = build_gt(rng, base_mu)

    scorer = make_scorer()
    pipeline = None
    if strategy == "PIPELINE":
        pipeline = ThreeStagePipeline(scorer, K=K_BATCH, theta_conf=THETA_CONF,
                                       category_weights=CATEGORY_WEIGHTS)

    # Track accuracy in windows of period/4 to measure output amplitude
    window = max(period // 4, 10)
    window_correct = 0
    window_total = 0
    acc_trace = []

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=CATEGORY_WEIGHTS))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_periodic(ta, ci, rng, n, period)

        result = scorer.score(fv, ci)
        correct = (result.action_index == oa)
        window_correct += int(correct)
        window_total += 1

        if strategy == "PIPELINE":
            pipeline.process(fv, ci, result.action_index, correct, oa, result.confidence)
        elif strategy == "RAW_SGD":
            scorer.update(fv, ci, result.action_index, correct, oa)

        if window_total >= window:
            acc_trace.append(window_correct / window_total * 100)
            window_correct = 0
            window_total = 0

    # Compute output amplitude (std of accuracy trace in steady state)
    if len(acc_trace) > 10:
        steady = acc_trace[len(acc_trace) // 2:]  # second half
        output_amplitude = np.std(steady)
    else:
        output_amplitude = 0

    return {'amplitude': output_amplitude, 'mean_acc': np.mean(acc_trace) if acc_trace else 0}


def main():
    print("=" * 80)
    print("EXP-31: V-FREQUENCY-RESPONSE")
    print("Periodic oracle noise amplitude=0.10, periods 20-2000")
    print("=" * 80)

    strategies = ["PIPELINE", "RAW_SGD", "STATIC"]
    results = {s: {} for s in strategies}

    for s in strategies:
        for T in PERIODS:
            amps = []
            accs = []
            for seed in SEEDS_SHORT:
                r = run_frequency(seed, T, s)
                amps.append(r['amplitude'])
                accs.append(r['mean_acc'])
            results[s][T] = {'amp': np.mean(amps), 'acc': np.mean(accs)}
        print(f"  {s} done")

    # Frequency response table
    print(f"\n{'=' * 80}")
    print("FREQUENCY RESPONSE TABLE")
    print("Input: noise rate oscillation amplitude = 0.10 (10pp)")
    print(f"{'=' * 80}")
    print(f"  {'Period':>7s}  {'Freq':>8s}", end="")
    for s in strategies:
        print(f"  {s[:8] + '_amp':>12s}  {s[:8] + '_acc':>12s}", end="")
    print()
    print(f"  {'-' * 85}")

    for T in PERIODS:
        freq = 1.0 / T
        print(f"  {T:>7d}  {freq:>8.4f}", end="")
        for s in strategies:
            r = results[s][T]
            print(f"  {r['amp']:>10.2f}pp  {r['acc']:>10.1f}%", end="")
        print()

    # Gain computation (output amplitude / input amplitude)
    # Input amplitude in accuracy terms: 10pp noise → ~5pp accuracy effect
    input_amp = 5.0  # approximate
    print(f"\n  GAIN (output_amplitude / {input_amp:.0f}pp input):")
    for s in strategies:
        print(f"    {s}:")
        for T in PERIODS:
            gain = results[s][T]['amp'] / input_amp if input_amp > 0 else 0
            print(f"      T={T:>4d}: gain={gain:.3f}", end="")
            if gain < 0.1:
                print("  (ATTENUATED)", end="")
            elif gain > 0.5:
                print("  (TRACKS)", end="")
            print()

    # Binary questions
    print(f"\n{'=' * 80}")
    print("BINARY QUESTIONS")
    print("=" * 80)

    # Q1: High-freq attenuation
    p_amp_20 = results["PIPELINE"][20]['amp']
    print(f"Q1: High-freq attenuation (T=20)? amp={p_amp_20:.2f}pp "
          f"gain={p_amp_20/input_amp:.3f} {'YES' if p_amp_20/input_amp < 0.1 else 'NO'}")

    # Q2: Low-freq tracking
    p_amp_2000 = results["PIPELINE"][2000]['amp']
    print(f"Q2: Low-freq tracking (T=2000)? amp={p_amp_2000:.2f}pp "
          f"gain={p_amp_2000/input_amp:.3f} {'YES' if p_amp_2000/input_amp > 0.5 else 'NO'}")

    # Q3: Crossover frequency
    crossover = "none"
    for T in PERIODS:
        gain = results["PIPELINE"][T]['amp'] / input_amp
        if gain >= 0.5:
            crossover = str(T)
            break
    print(f"Q3: Crossover period (gain=0.5): T={crossover}")

    # Q4: Pipeline vs raw bandwidth
    for T in PERIODS:
        p_gain = results["PIPELINE"][T]['amp'] / input_amp
        r_gain = results["RAW_SGD"][T]['amp'] / input_amp
        if abs(p_gain - r_gain) > 0.1:
            print(f"Q4: Bandwidth differs at T={T}: pipe={p_gain:.3f} raw={r_gain:.3f}")
            break
    else:
        print(f"Q4: Bandwidths similar across all periods")

    print("\nDONE.")


if __name__ == "__main__":
    main()
