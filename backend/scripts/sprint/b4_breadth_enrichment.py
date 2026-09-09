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
    rows = [
        run(evaluate_option("B4 breadth all patterns, default score", None, default_scorer, "all")),
        run(evaluate_option("B4a breadth all patterns, trained score", None, trained_scorer, "all")),
    ]
    best = max(rows, key=lambda r: r["delta_vs_sp"])
    classification = "HYPO: breadth beats adaptive selection" if best["delta_vs_sp"] > 0 else "ARCH: breadth evidence does not recover action value"
    payload = {"experiment": "B4 breadth enrichment", "design_justification": "Test whether selective routing is the failure mode by reading every pattern before terminal scoring.", "results": rows, "best": best, "classification": classification}
    write_json("data/sprint/b4_breadth_enrichment.json", payload)
    print("B4 breadth enrichment")
    for row in rows:
        print(row)
    print(classification)


if __name__ == "__main__":
    main()
