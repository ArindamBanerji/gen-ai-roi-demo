from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sprint.sprint_lib import ExperimentContext, factor_decomposition, write_json


def classify(payload: dict) -> str:
    overlap = float(payload["overlap"])
    max_sep = max(float(payload["max_category_eta_squared"]), float(payload["max_action_eta_squared"]))
    if max_sep < 0.2:
        return "EXP: fixture labels are weakly separable in the six-factor space"
    if overlap > 0.8:
        return "ARCH: routing and action use the same factor subspace"
    if overlap < 0.3:
        return "HYPO: routing/action subspaces are mostly separable; dual-centroid or dimension gating is viable"
    return "HYPO: partial subspace overlap; test dual-centroid and gating rather than one tensor"


def main() -> None:
    payload = factor_decomposition(ExperimentContext(use_trained=False))
    payload = {"experiment": "A3 factor decomposition", **payload, "classification": classify(payload)}
    write_json("data/sprint/a3_factor_decomposition.json", payload)
    print("A3 factor decomposition")
    print(f"overlap={payload['overlap']:.4f}, angle={payload['lda_angle_degrees']:.2f}")
    print(payload["classification"])


if __name__ == "__main__":
    main()
