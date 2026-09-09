from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
import os

from scripts.sprint.sprint_lib import evaluate_option, load_scorer, run, write_json


def main() -> None:
    a3_path = "data/sprint/a3_factor_decomposition.json"
    if not os.path.exists(a3_path):
        payload = {"experiment": "B2 dimension gating", "skipped": True, "skip_reason": "A3 factor decomposition output missing", "classification": "EXP: dependency missing"}
        write_json("data/sprint/b2_dimension_gating.json", payload)
        print(payload["skip_reason"])
        return
    a3 = json.load(open(a3_path, encoding="utf-8"))
    if float(a3.get("overlap", 1.0)) > 0.8:
        payload = {"experiment": "B2 dimension gating", "skipped": True, "skip_reason": "A3 found >80% routing/action subspace overlap", "classification": "ARCH: dimension gating ruled out by Phase A"}
        write_json("data/sprint/b2_dimension_gating.json", payload)
        print(payload["skip_reason"])
        return
    dims = [int(x) for x in a3["action_dimension_indices"]]
    default_scorer = load_scorer(False)
    trained_scorer = load_scorer(True)
    default_result = run(evaluate_option("B2 default centroid dimension gating", default_scorer, default_scorer, "routed", selected_dims=dims))
    trained_result = run(evaluate_option("B2a trained centroid dimension gating", default_scorer, trained_scorer, "routed", selected_dims=dims))
    result_rows = [default_result, trained_result]
    payload = {
        "experiment": "B2 dimension gating",
        "skipped": False,
        "design_justification": "Use evidence only on action-correlated dimensions from A3 while preserving routing dimensions from surface factors.",
        "selected_dimension_indices": dims,
        "selected_dimensions": a3["action_dimensions"],
        "results": result_rows,
        "classification": max(result_rows, key=lambda r: r["delta_vs_sp"])["classification"],
    }
    write_json("data/sprint/b2_dimension_gating.json", payload)
    print("B2 dimension gating")
    for row in result_rows:
        print(row)


if __name__ == "__main__":
    main()
