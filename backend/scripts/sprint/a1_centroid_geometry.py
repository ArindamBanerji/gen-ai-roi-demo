from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sprint.sprint_lib import centroid_geometry, load_mu, write_json


def classify(default: dict, trained: dict) -> str:
    d_route = set(default["routing_dimensions"])
    d_action = set(default["action_dimensions"])
    t_route = set(trained["routing_dimensions"])
    t_action = set(trained["action_dimensions"])
    overlap = len((d_route | t_route) & (d_action | t_action)) / max(len((d_route | t_route) | (d_action | t_action)), 1)
    if overlap < 0.3:
        return "HYPO: category and action signals are separable enough for dual-centroid or gating designs"
    if overlap > 0.8:
        return "ARCH: category and action signals use the same factor dimensions, so one tensor is structurally conflicted"
    return "HYPO: partial overlap; tension is real but may be reduced by separate tensors or gated dimensions"


def main() -> None:
    default = centroid_geometry(load_mu(False))
    trained = centroid_geometry(load_mu(True))
    payload = {"experiment": "A1 centroid geometry", "default": default, "trained": trained, "classification": classify(default, trained)}
    write_json("data/sprint/a1_centroid_geometry.json", payload)
    print("A1 centroid geometry")
    print(f"default ratio={default['inter_category_to_action_ratio']:.4f}, trained ratio={trained['inter_category_to_action_ratio']:.4f}")
    print(payload["classification"])


if __name__ == "__main__":
    main()
