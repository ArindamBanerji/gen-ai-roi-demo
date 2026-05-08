"""
EXP-G1 v3: Re-Convergence Factorial — Real GAE ProfileScorer

Uses the actual ProfileScorer from graph-attention-engine, not a
simplified simulation. Scoring dynamics (softmax over DK-weighted
L2 distances, η-weighted centroid updates) match production exactly.

Factorial design (2×2):
  COLD:          μ₀ = 0.5 uniform,  kernel = L2 (default, no DK)
  WARM_DK:       μ₀ = 0.5 uniform,  kernel = DiagonalKernel(sigma)
  WARM_CENTROID: μ  = converged,     kernel = L2 (default, no DK)
  WARM_BOTH:     μ  = converged,     kernel = DiagonalKernel(sigma)

Each seed:
  Phase 1 — Converge from cold with DK kernel → get converged centroids
  Phase 2 — Disrupt ALL 6 categories (±0.30 per cell)
  Phase 3 — Run all 4 conditions against same disrupted target

Metrics:
  γ_DK       = N_half_cold / N_half_warm_DK        (DK effect alone)
  γ_centroid = N_half_cold / N_half_warm_centroid   (geometry effect alone)
  γ_both     = N_half_cold / N_half_warm_both       (combined)

Output: G:\\My Drive\\public-files\\gen-ai-roi\\experiments\\reconvergence_exp_g1_v3.json
Runtime: ~30-90 seconds.

Usage:
  cd gen-ai-roi-demo-v4-v50\\backend
  python scripts/exp_g1_reconvergence.py
"""

import json
import os
import sys
import time
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# GAE import — add to sys.path from env var or relative path
# ---------------------------------------------------------------------------
GAE_PATH = os.environ.get("CLAUDE_GAE")
if not GAE_PATH:
    _here = Path(__file__).resolve().parent
    GAE_PATH = str(_here.parent.parent.parent / "graph-attention-engine-v50")

if GAE_PATH not in sys.path:
    sys.path.insert(0, GAE_PATH)

try:
    from gae.profile_scorer import ProfileScorer
    from gae.kernels import DiagonalKernel
    print(f"[EXP-G1] GAE imported from {GAE_PATH}")
except ImportError as e:
    print(f"[EXP-G1] ERROR: Cannot import GAE from {GAE_PATH}")
    print(f"  {e}")
    print(f"  Set CLAUDE_GAE env var or run from SOC backend/scripts/")
    sys.exit(1)

# ===========================================================================
# Constants (from math_synopsis v15)
# ===========================================================================

C, A, F = 6, 4, 6
ACTIONS = ["escalate", "investigate", "suppress", "monitor"]
EPSILON_FIRM = 0.125

N_SEEDS = 50
MAX_DECISIONS = 5000
BATCH_SIZE = 25

# Disruption magnitude per cell: U(-0.30, +0.30).
# RMS of this shift ≈ sqrt(0.30²/3) ≈ 0.173 — comfortably above ε_firm.
# This ensures warm_centroid does NOT start already "converged."
# v1 used 0.15 (sparse) → artifact. v2 used 0.20 (full) → didn't converge.
# 0.30 is calibrated to start all conditions above ε_firm while remaining
# within range where convergence is achievable in MAX_DECISIONS.
DISRUPTION_MAGNITUDE = 0.30

OUTPUT_PATH = Path(
    r"G:\My Drive\public-files\gen-ai-roi\experiments\reconvergence_exp_g1_v3.json"
)

# ===========================================================================
# Ground truth generation
# ===========================================================================

def generate_ground_truth(rng: np.random.Generator) -> np.ndarray:
    """Realistic target centroids: each category has primary + secondary action."""
    mu = rng.uniform(0.3, 0.7, size=(C, A, F))
    for c in range(C):
        primary = rng.integers(0, A)
        mu[c, primary, :] += rng.uniform(0.05, 0.15, size=F)
        secondary = (primary + 1) % A
        mu[c, secondary, :] += rng.uniform(0.02, 0.08, size=F)
    return np.clip(mu, 0.0, 1.0)


def generate_sigma(rng: np.random.Generator) -> np.ndarray:
    """Per-factor noise levels matching live SOC distribution."""
    base = np.array([0.10, 0.12, 0.07, 0.15, 0.20, 0.28])
    return np.clip(base + rng.uniform(-0.02, 0.02, size=F), 0.05, 0.35)


# ===========================================================================
# Scorer factory
# ===========================================================================

def make_scorer(centroids: np.ndarray,
                dk_kernel=None) -> ProfileScorer:
    """Create ProfileScorer. Copies centroids — caller's array not mutated."""
    return ProfileScorer(
        mu=centroids.copy(),
        actions=ACTIONS,
        scoring_kernel=dk_kernel,
    )


# ===========================================================================
# Convergence measurement
# ===========================================================================

def compute_epsilon(scorer: ProfileScorer, target: np.ndarray) -> float:
    """ε_firm: RMS distance between current centroids and target."""
    return float(np.sqrt(np.mean((scorer.centroids - target) ** 2)))


def run_convergence(scorer: ProfileScorer, target: np.ndarray,
                    sigma: np.ndarray, rng: np.random.Generator,
                    max_decisions: int = MAX_DECISIONS) -> tuple:
    """Run simulated decisions until ε < EPSILON_FIRM or max reached.

    Each decision:
      1. Random category
      2. Random source action (ensures all 24 cells get updates)
      3. Factor vector = target[cat, source_action] + Gaussian noise(σ)
      4. Ground truth action = closest target centroid for this fv
      5. scorer.update(fv, cat, gt_action, correct=True)

    Returns (n_half, converged, epsilon_final, final_centroids).
    """
    for d in range(1, max_decisions + 1):
        cat = rng.integers(0, C)
        source_action = rng.integers(0, A)

        fv = target[cat, source_action, :] + rng.normal(0, sigma)
        fv = np.clip(fv, 0.0, 1.0)

        gt_distances = np.sum((target[cat] - fv[np.newaxis, :]) ** 2, axis=1)
        gt_action = int(np.argmin(gt_distances))

        scorer.update(fv, cat, gt_action, correct=True)

        if d % BATCH_SIZE == 0:
            eps = compute_epsilon(scorer, target)
            if eps < EPSILON_FIRM:
                return d, True, eps, scorer.centroids.copy()

    eps_final = compute_epsilon(scorer, target)
    return max_decisions, False, eps_final, scorer.centroids.copy()


# ===========================================================================
# Disruption: shift ALL categories
# ===========================================================================

def disrupt_all_categories(target: np.ndarray,
                           rng: np.random.Generator) -> np.ndarray:
    """Shift ALL 6 categories. RMS ≈ 0.173 for magnitude=0.30."""
    new_target = target.copy()
    for c in range(C):
        shift = rng.uniform(-DISRUPTION_MAGNITUDE, DISRUPTION_MAGNITUDE,
                            size=(A, F))
        new_target[c] += shift
    return np.clip(new_target, 0.0, 1.0)


# ===========================================================================
# Single seed
# ===========================================================================

def run_seed(seed: int) -> dict:
    rng = np.random.default_rng(seed)

    target_v1 = generate_ground_truth(rng)
    sigma = generate_sigma(rng)
    dk_kernel = DiagonalKernel(sigma=sigma)
    cold_centroids = np.full((C, A, F), 0.5)

    # --- Phase 1: Initial convergence with DK kernel ---
    phase1_rng = np.random.default_rng(seed * 10000 + 1)
    phase1_scorer = make_scorer(cold_centroids, dk_kernel=dk_kernel)
    init_n, init_conv, init_eps, converged_centroids = run_convergence(
        phase1_scorer, target_v1, sigma, phase1_rng
    )

    # --- Phase 2: Disrupt ALL categories ---
    disruption_rng = np.random.default_rng(seed * 10000 + 2)
    target_v2 = disrupt_all_categories(target_v1, disruption_rng)

    # --- Phase 3: 4 conditions against target_v2 ---
    condition_names = ["cold", "warm_dk", "warm_centroid", "warm_both"]
    condition_configs = [
        (cold_centroids,      None),       # cold
        (cold_centroids,      dk_kernel),  # warm_dk
        (converged_centroids, None),       # warm_centroid
        (converged_centroids, dk_kernel),  # warm_both
    ]

    results = {}
    for i, (name, (centroids, kernel)) in enumerate(
        zip(condition_names, condition_configs)
    ):
        cond_rng = np.random.default_rng(seed * 10000 + 3 + i)
        scorer = make_scorer(centroids, dk_kernel=kernel)
        eps_start = compute_epsilon(scorer, target_v2)

        n_half, converged, eps_final, _ = run_convergence(
            scorer, target_v2, sigma, cond_rng
        )

        results[name] = {
            "n_half": n_half,
            "converged": converged,
            "epsilon_start": round(eps_start, 6),
            "epsilon_final": round(eps_final, 6),
        }

    # --- Compute gammas (ratio to cold start) ---
    cold_n = results["cold"]["n_half"]

    def gamma(cond_name):
        cond_n = results[cond_name]["n_half"]
        if cond_n <= 0:
            return 0.0
        return round(cold_n / cond_n, 4)

    return {
        "seed": seed,
        "sigma": sigma.round(4).tolist(),
        "initial_n_half": init_n,
        "initial_converged": init_conv,
        "initial_epsilon_final": round(init_eps, 6),
        "conditions": results,
        "gamma_dk": gamma("warm_dk"),
        "gamma_centroid": gamma("warm_centroid"),
        "gamma_both": gamma("warm_both"),
    }


# ===========================================================================
# Aggregation helpers
# ===========================================================================

def gamma_stats(values: list) -> dict:
    v = [x for x in values if x > 0 and not np.isinf(x)]
    if not v:
        return {"mean": 0, "median": 0, "std": 0,
                "ci_lower": 0, "ci_upper": 0, "gt_1_pct": 0, "n": 0}
    return {
        "mean": round(float(np.mean(v)), 4),
        "median": round(float(np.median(v)), 4),
        "std": round(float(np.std(v)), 4),
        "ci_lower": round(float(np.percentile(v, 2.5)), 4),
        "ci_upper": round(float(np.percentile(v, 97.5)), 4),
        "gt_1_pct": round(sum(1 for x in v if x > 1.0) / len(v) * 100, 1),
        "n": len(v),
    }


def nhalf_stats(all_seeds: list, condition: str) -> dict:
    vals = [s["conditions"][condition]["n_half"] for s in all_seeds]
    conv = [s["conditions"][condition]["converged"] for s in all_seeds]
    return {
        "mean": round(float(np.mean(vals)), 1),
        "median": round(float(np.median(vals)), 1),
        "std": round(float(np.std(vals)), 1),
        "converged_pct": round(sum(conv) / len(conv) * 100, 1),
    }


# ===========================================================================
# Main
# ===========================================================================

def main():
    print("EXP-G1 v3: Re-Convergence Factorial — Real GAE ProfileScorer")
    print(f"  Seeds: {N_SEEDS}, Tensor: ({C},{A},{F}), "
          f"Disruption: ALL {C} cats ±{DISRUPTION_MAGNITUDE}")
    print(f"  ε_firm★: {EPSILON_FIRM}, Max decisions: {MAX_DECISIONS}")
    print()

    start = time.time()
    all_seeds = []
    gammas = {"dk": [], "centroid": [], "both": []}

    for seed in range(N_SEEDS):
        result = run_seed(seed)
        all_seeds.append(result)
        gammas["dk"].append(result["gamma_dk"])
        gammas["centroid"].append(result["gamma_centroid"])
        gammas["both"].append(result["gamma_both"])

        if (seed + 1) % 10 == 0:
            elapsed = time.time() - start
            c = result["conditions"]
            mark = lambda v: "✓" if v else "✗"
            print(
                f"  Seed {seed+1}/{N_SEEDS} ({elapsed:.1f}s)  "
                f"init={result['initial_n_half']}{mark(result['initial_converged'])}  "
                f"cold={c['cold']['n_half']}{mark(c['cold']['converged'])}  "
                f"dk={c['warm_dk']['n_half']}{mark(c['warm_dk']['converged'])}  "
                f"cent={c['warm_centroid']['n_half']}{mark(c['warm_centroid']['converged'])}  "
                f"both={c['warm_both']['n_half']}{mark(c['warm_both']['converged'])}"
            )

    elapsed = time.time() - start

    dk_s = gamma_stats(gammas["dk"])
    cent_s = gamma_stats(gammas["centroid"])
    both_s = gamma_stats(gammas["both"])

    summary = {
        "experiment": "EXP-G1_v3",
        "description": (
            "Factorial isolation of re-convergence mechanisms using real GAE "
            "ProfileScorer. γ_DK: DK weight knowledge alone. γ_centroid: "
            "centroid geometry alone. γ_both: combined effect."
        ),
        "source": "EXP-G1_simulation_factorial_gae",
        "gae_path": GAE_PATH,
        "parameters": {
            "tensor_shape": f"({C}, {A}, {F})",
            "n_seeds": N_SEEDS,
            "disruption": f"all_{C}_categories",
            "disruption_magnitude": DISRUPTION_MAGNITUDE,
            "epsilon_firm": EPSILON_FIRM,
            "max_decisions": MAX_DECISIONS,
            "batch_size": BATCH_SIZE,
            "scorer": "gae.profile_scorer.ProfileScorer",
            "dk_kernel": "gae.kernels.DiagonalKernel(sigma)",
            "non_dk_kernel": "L2 (ProfileScorer default)",
        },
        "results": {
            "gamma_dk": dk_s,
            "gamma_centroid": cent_s,
            "gamma_both": both_s,
        },
        "per_condition_n_half": {
            cond: nhalf_stats(all_seeds, cond)
            for cond in ["cold", "warm_dk", "warm_centroid", "warm_both"]
        },
        "initial_convergence": {
            "mean_n_half": round(float(np.mean(
                [s["initial_n_half"] for s in all_seeds])), 1),
            "converged_pct": round(
                sum(s["initial_converged"] for s in all_seeds)
                / N_SEEDS * 100, 1),
        },
        "runtime_seconds": round(elapsed, 1),
        "gate": "Tier 2 (conditional). Production validation pending pilot data.",
        "seeds": all_seeds,
    }

    # --- Interpretation ---
    lines = []
    for label, s in [("γ_DK", dk_s), ("γ_centroid", cent_s), ("γ_both", both_s)]:
        pct = s["gt_1_pct"]
        m = s["mean"]
        if pct >= 60:
            lines.append(f"{label}: STRONG ({m:.2f}, {pct}% > 1)")
        elif pct >= 40:
            lines.append(f"{label}: MODERATE ({m:.2f}, {pct}% > 1)")
        elif m > 1.0:
            lines.append(f"{label}: WEAK ({m:.2f}, {pct}% > 1)")
        else:
            lines.append(f"{label}: NOT DEMONSTRATED ({m:.2f}, {pct}% > 1)")

    # Identify dominant mechanism
    if dk_s["mean"] > cent_s["mean"] * 1.1:
        lines.append("Dominant: DK weights (knowing WHICH dimensions)")
    elif cent_s["mean"] > dk_s["mean"] * 1.1:
        lines.append("Dominant: centroid geometry (starting NEAR target)")
    else:
        lines.append("Both mechanisms contribute comparably")

    summary["interpretation"] = " | ".join(lines)

    # --- Save ---
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(summary, f, indent=2)

    # --- Print ---
    print()
    print("=" * 65)
    print("EXP-G1 v3 — Real GAE ProfileScorer")
    print("=" * 65)
    init = summary["initial_convergence"]
    print(f"\n  Phase 1: N_half={init['mean_n_half']:.0f} "
          f"({init['converged_pct']}% converged)")
    print("\n  Recovery N_half (lower = faster):")
    for cond in ["cold", "warm_dk", "warm_centroid", "warm_both"]:
        s = summary["per_condition_n_half"][cond]
        print(f"    {cond:18s}: {s['mean']:6.0f} ± {s['std']:5.0f}  "
              f"(converged {s['converged_pct']}%)")
    print("\n  Acceleration (γ > 1 = faster than cold):")
    for label, s in [("γ_DK", dk_s), ("γ_centroid", cent_s), ("γ_both", both_s)]:
        print(f"    {label:12s}: mean={s['mean']:.3f}  median={s['median']:.3f}  "
              f"95%CI=[{s['ci_lower']:.2f}, {s['ci_upper']:.2f}]  "
              f">{'>'}1: {s['gt_1_pct']}%")
    print()
    for line in lines:
        print(f"  {line}")
    print(f"\n  Runtime: {elapsed:.1f}s")
    print(f"  Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
