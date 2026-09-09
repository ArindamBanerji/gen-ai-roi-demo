from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sprint.sprint_lib import evaluate_option, load_scorer, run, write_json


def main() -> None:
    default_scorer = load_scorer(False)
    trained_scorer = load_scorer(True)
    result = run(evaluate_option("B7 abstain on default/trained route disagreement", default_scorer, trained_scorer, "routed", require_route_agreement=True))
    payload = {"experiment": "B7 abstain on geometry disagreement", "design_justification": "Treat centroid-set disagreement as uncertainty and measure committed accuracy plus abstention rate.", "result": result, "classification": result["classification"]}
    write_json("data/sprint/b7_abstain_disagreement.json", payload)
    print("B7 abstain disagreement")
    print(result)


if __name__ == "__main__":
    main()
