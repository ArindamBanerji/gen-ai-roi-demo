from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sprint.sprint_lib import centroid_hash, evaluate_option, load_mu, load_scorer, run, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="B1 dual-centroid experiment")
    parser.add_argument("--bootstrapped", action="store_true", help="Use data/bootstrapped_centroids.npy for action scoring")
    args = parser.parse_args()
    scoring_label = "bootstrapped" if args.bootstrapped else "trained"
    output = "data/sprint/b1_dual_centroids_bootstrapped.json" if args.bootstrapped else "data/sprint/b1_dual_centroids.json"
    default_scorer = load_scorer(False)
    scoring_scorer = load_scorer(use_bootstrapped=args.bootstrapped) if args.bootstrapped else load_scorer(True)
    primary = run(evaluate_option(f"B1 dual-centroid: default route, {scoring_label} score", default_scorer, scoring_scorer, "routed"))
    surface = run(evaluate_option(f"B1a default route, {scoring_label} score, no evidence", default_scorer, scoring_scorer, "none"))
    payload = {
        "experiment": "B1 dual centroids",
        "centroid_mode": scoring_label,
        "design_justification": "Use the centroid set that routed well for investigation selection and the centroid set that scored actions better for terminal decisions.",
        "routing_centroid_hash": centroid_hash(load_mu(False)),
        "scoring_centroid_hash": centroid_hash(load_mu(use_bootstrapped=args.bootstrapped) if args.bootstrapped else load_mu(True)),
        "results": [primary, surface],
        "classification": primary["classification"],
    }
    write_json(output, payload)
    print("B1 dual centroids")
    print(primary)


if __name__ == "__main__":
    main()
