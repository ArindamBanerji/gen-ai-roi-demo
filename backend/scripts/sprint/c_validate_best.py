from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
import os
from pathlib import Path

import numpy as np

from scripts.sprint.sprint_lib import evaluate_option, load_mu, run, scorer_from_mu, write_json

B_FILES = [
    "b1_dual_centroids",
    "b2_dimension_gating",
    "b3_joint_training",
    "b4_breadth_enrichment",
    "b5_ensemble",
    "b6_routing_feature",
    "b7_abstain_disagreement",
]


def collect_rows(*, use_bootstrapped: bool = False) -> list[dict]:
    rows: list[dict] = []
    for name in B_FILES:
        path = Path(f"data/sprint/{name}_bootstrapped.json") if use_bootstrapped else Path(f"data/sprint/{name}.json")
        if not path.exists():
            rows.append({"option": name, "skipped": True, "skip_reason": "output missing"})
            continue
        payload = json.load(open(path, encoding="utf-8"))
        if payload.get("skipped"):
            rows.append({"option": name, "skipped": True, "skip_reason": payload.get("skip_reason", "skipped"), "classification": payload.get("classification")})
            continue
        if "results" in payload:
            for row in payload["results"]:
                rows.append({"option": name, **row})
        elif "rows" in payload:
            best = payload.get("best") or payload.get("best_by_delta") or max(payload["rows"], key=lambda r: r.get("delta_vs_sp", r.get("accuracy", 0)))
            rows.append({"option": name, **best, "classification": payload.get("classification")})
        elif "result" in payload:
            rows.append({"option": name, **payload["result"]})
    return rows


def choose_best(rows: list[dict]) -> dict:
    candidates = [r for r in rows if not r.get("skipped") and r.get("accuracy") is not None]
    if not candidates:
        return {"option": "none", "classification": "EXP: no runnable candidates"}
    viable = [r for r in candidates if (r.get("rho") is None or r.get("rho", 0) > 0.5) and r.get("delta_vs_sp", 0) > 0]
    if viable:
        return max(viable, key=lambda r: (r.get("delta_vs_sp", 0), r.get("rho") or 0.0))
    positive = [r for r in candidates if r.get("delta_vs_sp", 0) > 0]
    if positive:
        return max(positive, key=lambda r: r.get("delta_vs_sp", 0))
    return max(candidates, key=lambda r: r.get("accuracy", 0))


def stability_for_trained(seed_count: int = 5, *, use_bootstrapped: bool = False) -> list[dict]:
    base = load_mu(use_bootstrapped=use_bootstrapped) if use_bootstrapped else load_mu(True)
    rows = []
    for seed in range(seed_count):
        rng = np.random.default_rng(seed)
        perturbed = base + rng.normal(0.0, 0.01, size=base.shape)
        scorer = scorer_from_mu(perturbed)
        row = run(evaluate_option(f"stability_seed_{seed}", scorer, scorer, "routed"))
        row["seed"] = seed
        rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase C validation")
    parser.add_argument("--bootstrapped", action="store_true", help="Use bootstrapped sprint outputs and stability centroids")
    args = parser.parse_args()
    rows = collect_rows(use_bootstrapped=args.bootstrapped)
    best = choose_best(rows)
    stability = stability_for_trained(5, use_bootstrapped=args.bootstrapped)
    deltas = [float(r["delta_vs_sp"]) for r in stability]
    sensitivity = {
        "stability_runs": len(stability),
        "delta_mean": float(np.mean(deltas)),
        "delta_std": float(np.std(deltas)),
        "all_finite": bool(np.all(np.isfinite(deltas))),
    }
    if best.get("option") == "b1_dual_centroids" and best.get("delta_vs_sp", 0) > 0 and (best.get("rho") or 0) > 0.5:
        verdict = "DUAL-CENTROID RESOLVES"
        recommendation = "Phase 2 should separate routing μ from action-scoring μ and keep investigation direction decoupled from terminal action scoring."
    elif best.get("option") == "b2_dimension_gating" and best.get("delta_vs_sp", 0) > 0:
        verdict = "DIMENSION GATING RESOLVES"
        recommendation = "Phase 2 should implement per-dimension evidence admission."
    elif best.get("option") == "b3_joint_training" and best.get("delta_vs_sp", 0) > 0 and (best.get("rho") or 0) > 0.5:
        verdict = "JOINT TRAINING RESOLVES"
        recommendation = "Phase 2 should use jointly-trained centroids at the selected alpha."
    elif best.get("option") == "b4_breadth_enrichment" and best.get("delta_vs_sp", 0) > 0:
        verdict = "BREADTH WINS"
        recommendation = "Phase 2 should test breadth+trained before adding adaptive routing complexity."
    elif best.get("option") == "b7_abstain_disagreement" and best.get("delta_vs_sp", 0) > 0:
        verdict = "ABSTENTION RESOLVES"
        recommendation = "Phase 2 should treat default/trained geometry disagreement as an abstain signal."
    else:
        verdict = "TENSION IS INHERENT"
        recommendation = "No tested option achieved rho>0.5 and delta>0 simultaneously; scope VLD to category identification unless production data changes this geometry."
    payload = {
        "experiment": "Phase C validation",
        "centroid_mode": "bootstrapped" if args.bootstrapped else "trained",
        "comparison_table": rows,
        "best_option": best,
        "stability": stability,
        "sensitivity": sensitivity,
        "verdict": verdict,
        "recommendation": recommendation,
        "production_data_needed": "Real verified SOC outcomes with production-trained routing and action centroids; validate whether fixture/synthetic centroid behavior persists out of sample.",
    }
    write_json("data/sprint/c_validate_best_bootstrapped.json" if args.bootstrapped else "data/sprint/c_validate_best.json", payload)
    print("Phase C validation")
    print(f"best={best.get('option')} {best.get('name', '')} rho={best.get('rho')} delta={best.get('delta_vs_sp')}")
    print(f"stability n={sensitivity['stability_runs']} mean_delta={sensitivity['delta_mean']:.4f} std={sensitivity['delta_std']:.4f}")
    print(verdict)


if __name__ == "__main__":
    main()
