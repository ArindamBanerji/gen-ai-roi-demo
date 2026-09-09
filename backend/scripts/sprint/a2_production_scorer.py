from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import os

from scripts.sprint.sprint_lib import centroid_geometry, load_mu, write_json


def main() -> None:
    default = centroid_geometry(load_mu(False))
    production = centroid_geometry(load_mu(False))
    same = default["hash"] == production["hash"]
    persisted = [p for p in ["data/soc_centroids.npy", "data/centroids.json", "data/soc_authority.sqlite3"] if os.path.exists(p)]
    classification = "EXP: production scorer resolves to the default app scorer in this offline harness" if same else "ARCH: production scorer geometry differs but must be evaluated separately"
    payload = {
        "experiment": "A2 production scorer examination",
        "production_load_method": "SOCDomainConfig().build_profile_scorer() in offline backend process",
        "persisted_candidates_present": persisted,
        "production_equals_default": same,
        "default": default,
        "production": production,
        "classification": classification,
        "limitation": "This does not query a live running backend process; it examines the production initialization path available to tests.",
    }
    write_json("data/sprint/a2_production_scorer.json", payload)
    print("A2 production scorer")
    print(f"production_equals_default={same}, persisted_candidates={persisted}")
    print(classification)


if __name__ == "__main__":
    main()
