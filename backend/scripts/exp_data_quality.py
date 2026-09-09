"""E-DATA: audit SOC VLD fixture data quality for value-chain interpretation."""

from __future__ import annotations

import argparse
from itertools import combinations
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from app.domains.soc.config import SOC_CATEGORIES
from app.services.investigation_patterns import PATTERN_REGISTRY
from scripts.value_chain_experiment_lib import (
    ExperimentContext,
    action_distribution,
    centroid_cell_counts,
    cosine_similarity,
    summarize_flags,
    write_json,
)

OUTPUT = Path("data/exp_data_quality.json")
TRAINED_OUTPUT = Path("data/exp_data_quality_trained.json")


def run_experiment(*, use_trained: bool = False) -> dict[str, Any]:
    ctx = ExperimentContext(use_trained=use_trained)
    category_counts = {category: 0 for category in SOC_CATEGORIES}
    for category in ctx.category_truth.values():
        category_counts[category] += 1
    total = sum(category_counts.values())
    flags: list[dict[str, str]] = []
    if total and max(category_counts.values()) / float(total) > 0.5:
        flags.append({"severity": "critical", "issue_category": "EXPERIMENT DESIGN ISSUE", "message": "category imbalance exceeds 50%"})

    actions = action_distribution(ctx)
    degenerate = [category for category, counts in actions.items() if sum(counts.values()) > 0 and len(counts) <= 1]
    if degenerate:
        flags.append({"severity": "warning", "issue_category": "EXPERIMENT DESIGN ISSUE", "message": f"degenerate action categories: {degenerate}"})

    matrix = np.asarray([ctx.v0(alert) for alert in ctx.eval_alerts], dtype=np.float64)
    factor_std = {str(i): float(np.std(matrix[:, i])) for i in range(matrix.shape[1])} if len(matrix) else {}
    near_constant = [dim for dim, value in factor_std.items() if value <= 1.0e-6]
    if near_constant:
        flags.append({"severity": "critical", "issue_category": "EXPERIMENT DESIGN ISSUE", "message": f"near-constant factor dimensions: {near_constant}"})

    evidence_overlap: dict[str, float] = {}
    max_overlap = 0.0
    for left, right in combinations(SOC_CATEGORIES, 2):
        sim = cosine_similarity(PATTERN_REGISTRY[left].evidence_vector({}), PATTERN_REGISTRY[right].evidence_vector({}))
        evidence_overlap[f"{left}__{right}"] = sim
        max_overlap = max(max_overlap, abs(sim))
    if max_overlap > 0.9:
        flags.append({"severity": "critical", "issue_category": "IMPLEMENTATION ISSUE", "message": f"evidence vector overlap exceeds 0.9: {max_overlap}"})

    cell_counts = centroid_cell_counts(ctx)
    zero_cells = [cell for cell, count in cell_counts.items() if count == 0]
    if zero_cells:
        flags.append({"severity": "critical", "issue_category": "EXPERIMENT DESIGN ISSUE", "message": f"zero centroid training cells: {zero_cells}"})

    report = {
        "experiment": "E-DATA",
        "centroid_mode": "trained" if use_trained else "default",
        "fixture": str(ctx.fixture_path),
        "provenance": "deterministic synthetic SOC seed fixture",
        "category_distribution": category_counts,
        "category_imbalance_fraction": max(category_counts.values()) / float(total) if total else None,
        "action_distribution_per_category": actions,
        "factor_std_per_dimension": factor_std,
        "evidence_cosine_similarity_by_pattern_pair": evidence_overlap,
        "max_abs_evidence_overlap": max_overlap,
        "centroid_cell_coverage": cell_counts,
        "zero_coverage_cells": zero_cells,
        "quality": summarize_flags(flags),
    }
    write_json(TRAINED_OUTPUT if use_trained else OUTPUT, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trained", action="store_true", help="Use data/trained_experiment_centroids.npy")
    args = parser.parse_args()
    report = run_experiment(use_trained=args.trained)
    print("=== E-DATA ===")
    print(f"Category distribution: {report['category_distribution']}")
    print(f"Max evidence overlap: {report['max_abs_evidence_overlap']}")
    print(f"Critical issues: {report['quality']['critical_count']}")
    print(f"Warnings: {report['quality']['warning_count']}")


if __name__ == "__main__":
    main()

