"""
EXP-1: V-PRIOR-GAP
===================
Question: Is +0.4pp an artifact of starting near the answer?

Run: cd backend && python scripts/exp1_prior_gap.py
Time: ~15 min
"""

import numpy as np
from exp_shared import (
    C, A, D, CATEGORIES, SEEDS, get_base_centroids,
    build_gt, run_learning_loop, make_scorer
)

N = 2000
CHECKPOINTS = [50, 100, 200, 500, 1000, 2000]

def make_generic_prior():
    """All centroids at 0.5 — knows nothing."""
    return np.full((C, A, D), 0.5)

def make_wrong_prior(base_mu, rng, shift=0.3):
    """Expert prior shifted 0.3 Frobenius from GT in random direction."""
    wrong = base_mu.copy()
    direction = rng.normal(0, 1, wrong.shape)
    direction = direction / np.linalg.norm(direction) * shift
    wrong += direction
    return np.clip(wrong, 0, 1)

def main():
    print("=" * 75)
    print("EXP-1: V-PRIOR-GAP — Generic vs Calibrated vs Wrong Prior")
    print("=" * 75)

    base_mu = get_base_centroids()

    conditions = {
        "A_generic": lambda rng: make_generic_prior(),
        "B_calibrated": lambda rng: base_mu.copy(),
        "C_wrong": lambda rng: make_wrong_prior(base_mu, rng, shift=0.3),
    }

    strategies = ["LEARN_pipeline", "LEARN_raw", "STATIC"]

    results = {}  # (condition, strategy, seed) -> checkpoints

    for cond_name, prior_fn in conditions.items():
        for seed in SEEDS:
            rng = np.random.default_rng(seed + 10000)  # separate from learning rng
            gt = build_gt(np.random.default_rng(seed), base_mu)
            prior = prior_fn(rng)

            for strat in strategies:
                use_pipe = strat == "LEARN_pipeline"
                is_static = strat == "STATIC"

                if is_static:
                    # STATIC: score with prior, never update
                    r = run_learning_loop(gt, prior, N, CHECKPOINTS, seed,
                                          use_pipeline=False)
                    # Override: use static accuracy
                    key = (cond_name, strat, seed)
                    results[key] = {n: r['checkpoints'][n]['static'] for n in CHECKPOINTS}
                else:
                    r = run_learning_loop(gt, prior, N, CHECKPOINTS, seed,
                                          use_pipeline=use_pipe)
                    key = (cond_name, strat, seed)
                    results[key] = {n: r['checkpoints'][n]['learn'] for n in CHECKPOINTS}

                    # Also store frobenius
                    results[(cond_name, strat + "_frob", seed)] = {
                        n: r['checkpoints'][n]['frobenius'] for n in CHECKPOINTS
                    }

        print(f"  {cond_name} done ({len(SEEDS)} seeds × {len(strategies)} strategies)")

    # ═══ RESULTS TABLE ═══
    for cond_name in conditions:
        print(f"\n{'=' * 75}")
        print(f"CONDITION: {cond_name}")
        print(f"{'=' * 75}")
        print(f"  {'N':>6s}", end="")
        for s in strategies:
            print(f"  {s:>15s}", end="")
        print(f"  {'L_pipe-STATIC':>14s}  {'L_raw-STATIC':>13s}")
        print(f"  {'-' * 80}")

        for n in CHECKPOINTS:
            print(f"  {n:>6d}", end="")
            vals = {}
            for s in strategies:
                v = [results[(cond_name, s, seed)][n] for seed in SEEDS]
                m = np.mean(v)
                vals[s] = m
                print(f"  {m:13.1f}%", end="")
            gap_pipe = vals["LEARN_pipeline"] - vals["STATIC"]
            gap_raw = vals["LEARN_raw"] - vals["STATIC"]
            print(f"  {gap_pipe:+12.1f}pp  {gap_raw:+11.1f}pp")

    # ═══ FROBENIUS DISTANCE ═══
    print(f"\n{'=' * 75}")
    print("Frobenius ||μ(N) - μ(0)|| at N=2000 (mean across seeds)")
    print(f"{'=' * 75}")
    for cond_name in conditions:
        for strat in ["LEARN_pipeline", "LEARN_raw"]:
            vals = [results.get((cond_name, strat + "_frob", seed), {}).get(2000, 0)
                    for seed in SEEDS]
            print(f"  {cond_name:>15s} {strat:>15s}: {np.mean(vals):.4f}")

    # ═══ BINARY QUESTIONS ═══
    print(f"\n{'=' * 75}")
    print("BINARY QUESTIONS")
    print(f"{'=' * 75}")

    # Q1: LEARN-STATIC gap at N=2000: Condition A > Condition B?
    gap_A = np.mean([results[("A_generic", "LEARN_pipeline", s)][2000] -
                     results[("A_generic", "STATIC", s)][2000] for s in SEEDS])
    gap_B = np.mean([results[("B_calibrated", "LEARN_pipeline", s)][2000] -
                     results[("B_calibrated", "STATIC", s)][2000] for s in SEEDS])
    print(f"Q1: LEARN-STATIC gap A_generic={gap_A:+.1f}pp, B_calibrated={gap_B:+.1f}pp")
    print(f"    A > B? {'YES' if gap_A > gap_B else 'NO'}")

    # Q2: Condition C LEARN at N=2000 within 3pp of Condition B?
    c_learn = np.mean([results[("C_wrong", "LEARN_pipeline", s)][2000] for s in SEEDS])
    b_learn = np.mean([results[("B_calibrated", "LEARN_pipeline", s)][2000] for s in SEEDS])
    diff = abs(c_learn - b_learn)
    print(f"Q2: C_wrong LEARN={c_learn:.1f}%, B_calibrated LEARN={b_learn:.1f}%, diff={diff:.1f}pp")
    print(f"    Within 3pp? {'YES' if diff < 3.0 else 'NO'}")

    # Q3: Frobenius A > B?
    frob_A = np.mean([results.get(("A_generic", "LEARN_pipeline_frob", s), {}).get(2000, 0)
                      for s in SEEDS])
    frob_B = np.mean([results.get(("B_calibrated", "LEARN_pipeline_frob", s), {}).get(2000, 0)
                      for s in SEEDS])
    ratio = frob_A / frob_B if frob_B > 0 else float('inf')
    print(f"Q3: Frobenius A={frob_A:.4f}, B={frob_B:.4f}, ratio={ratio:.1f}x")
    print(f"    A > B? {'YES' if frob_A > frob_B else 'NO'}")

    # Q4: N at which A LEARN catches up to B STATIC
    b_static_2000 = np.mean([results[("B_calibrated", "STATIC", s)][2000] for s in SEEDS])
    catchup = "never"
    for n in CHECKPOINTS:
        a_learn = np.mean([results[("A_generic", "LEARN_pipeline", s)][n] for s in SEEDS])
        if a_learn >= b_static_2000:
            catchup = str(n)
            break
    print(f"Q4: A_generic LEARN catches B_calibrated STATIC ({b_static_2000:.1f}%) at N={catchup}")

    print("\nDONE.")


if __name__ == "__main__":
    main()
