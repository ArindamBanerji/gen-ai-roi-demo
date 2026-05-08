"""Calibrate display-only expert bootstrap centroids for SOC Tab 3.

The artifact produced by this script is used only for Day-1 baseline
confidence display. It does not mutate the live ProfileScorer or learning
state.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

SEED = 42
TARGET_LOW = 0.50
TARGET_HIGH = 0.55
MAX_TRIALS = 50


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def configure_paths() -> None:
    root = repo_root()
    backend_path = root / "backend"
    gae_path = root.parent / "graph-attention-engine-v50"
    for path in (backend_path, gae_path):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)


configure_paths()

from app.domains.soc.config import (  # noqa: E402
    SCORER_ACTIONS,
    SOC_CATEGORIES,
    SOC_PROFILE_CENTROIDS,
)
from app.routers.evaluation import load_soc_scenarios  # noqa: E402
from gae.profile_scorer import KernelType, ProfileScorer  # noqa: E402


def artifact_path() -> Path:
    return repo_root() / "support" / "setup" / "bootstrap_centroids.json"


def load_converged_centroids() -> np.ndarray:
    """Return the current expert SOC centroid tensor."""
    return np.asarray(SOC_PROFILE_CENTROIDS, dtype=np.float64).copy()


def load_seed_alerts() -> list[dict[str, Any]]:
    """Load explicit SOC evaluation scenarios as the calibration seed pool."""
    seed_alerts: list[dict[str, Any]] = []
    n_actions = len(SCORER_ACTIONS)
    for scenario in load_soc_scenarios():
        if not 0 <= int(scenario.expected_action_index) < n_actions:
            continue
        seed_alerts.append(
            {
                "scenario_id": scenario.scenario_id,
                "category": scenario.category,
                "category_index": int(scenario.category_index),
                "factors": np.asarray(scenario.factors, dtype=np.float64),
                "correct_action": scenario.expected_action,
                "correct_action_index": int(scenario.expected_action_index),
            }
        )
    if not seed_alerts:
        raise RuntimeError("No seed alerts with scorer-action ground truth were available")
    return seed_alerts


def score_pool(bootstrap_centroids: np.ndarray, seed_alerts: list[dict[str, Any]]) -> float:
    """Return mean probability assigned to each scenario's correct action."""
    scorer = ProfileScorer(
        mu=np.asarray(bootstrap_centroids, dtype=np.float64),
        actions=list(SCORER_ACTIONS),
        categories=list(SOC_CATEGORIES),
        kernel=KernelType.L2,
    )
    confidences: list[float] = []
    for alert in seed_alerts:
        result = scorer.score(alert["factors"], alert["category_index"])
        confidences.append(float(result.probabilities[alert["correct_action_index"]]))
    return float(np.mean(confidences))


def _candidate_centroids(converged: np.ndarray, noise_scale: float) -> np.ndarray:
    """Move expert centroids toward Day-1 uncertainty and add deterministic noise."""
    uniform = np.full_like(converged, 0.5, dtype=np.float64)
    rng = np.random.default_rng(SEED)
    noise = rng.normal(0.0, noise_scale * 0.02, size=converged.shape)
    return np.clip(converged + noise_scale * (uniform - converged) + noise, 0.0, 1.0)


def calibrate(
    target_low: float = TARGET_LOW,
    target_high: float = TARGET_HIGH,
    max_trials: int = MAX_TRIALS,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Find a deterministic perturbation that yields the target confidence range."""
    converged = load_converged_centroids()
    seed_alerts = load_seed_alerts()

    lo = 0.0
    hi = 1.0
    best: tuple[float, float, np.ndarray, int] | None = None

    for trial in range(1, max_trials + 1):
        noise_scale = (lo + hi) / 2.0
        candidate = _candidate_centroids(converged, noise_scale)
        mean_confidence = score_pool(candidate, seed_alerts)

        if best is None or abs(mean_confidence - 0.525) < abs(best[0] - 0.525):
            best = (mean_confidence, noise_scale, candidate, trial)

        if target_low <= mean_confidence <= target_high:
            return candidate, {
                "mean_confidence": round(mean_confidence, 6),
                "noise_scale": round(noise_scale, 6),
                "seed": SEED,
                "trial": trial,
                "pool_size": len(seed_alerts),
            }

        # More perturbation pushes centroids toward uncertainty; less preserves expert confidence.
        if mean_confidence > target_high:
            lo = noise_scale
        else:
            hi = noise_scale

    assert best is not None
    raise RuntimeError(
        "Unable to calibrate bootstrap centroids after "
        f"{max_trials} trials; best_mean={best[0]:.6f}, noise_scale={best[1]:.6f}"
    )


def main() -> None:
    centroids, calibration = calibrate()
    output = {
        "shape": list(centroids.shape),
        "values": centroids.tolist(),
        "calibration": calibration,
    }
    path = artifact_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "Wrote "
        f"{path} mean_confidence={calibration['mean_confidence']} "
        f"noise_scale={calibration['noise_scale']} pool_size={calibration['pool_size']}"
    )


if __name__ == "__main__":
    main()
