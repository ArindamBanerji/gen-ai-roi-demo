from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sprint.sprint_lib import write_json


def main() -> None:
    payload = {
        "experiment": "B6 routing confidence as feature",
        "skipped": True,
        "skip_reason": "Requires augmented centroid dimensionality and retraining; B1-B5/B7 are cheaper and directly answer the one-tensor tension first.",
        "classification": "EXP: intentionally deferred contingent architecture",
    }
    write_json("data/sprint/b6_routing_feature.json", payload)
    print(payload["skip_reason"])


if __name__ == "__main__":
    main()
