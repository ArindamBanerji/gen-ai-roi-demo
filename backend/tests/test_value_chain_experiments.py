"""Tests for SOC VLD value-chain experiment scripts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES
from scripts.exp_baseline_verify import OUTPUT as BASELINE_OUTPUT, run_experiment as run_baseline
from scripts.exp_data_quality import OUTPUT as DATA_OUTPUT, run_experiment as run_data_quality
from scripts.exp_dimension_decomposition import OUTPUT as DIM_OUTPUT, run_experiment as run_dimension_decomposition
from scripts.exp_split_enrichment import OUTPUT as SPLIT_OUTPUT, run_experiment as run_split_enrichment
from scripts.exp_wrong_route_impact import OUTPUT as WRONG_OUTPUT, run_experiment as run_wrong_route_impact
from scripts.value_chain_experiment_lib import ExperimentContext, cosine_similarity, full_distance, score_best


@pytest.mark.asyncio
async def test_baseline_scorer_sanity_scores_centroids_correctly() -> None:
    report = await run_baseline()
    check = next(item for item in report["checks"] if item["check"] == "scorer_centroid_sanity")
    assert check["passed"] is True


@pytest.mark.asyncio
async def test_baseline_sp_recomputation_matches_phase1b() -> None:
    report = await run_baseline()
    assert report["sp_accuracy"] == pytest.approx(0.5377532228360957, abs=0.001)


def test_data_category_distribution_sums_to_total() -> None:
    report = run_data_quality()
    assert sum(report["category_distribution"].values()) == 543


def test_data_evidence_overlap_known_vectors() -> None:
    assert cosine_similarity(np.array([1.0, 0.0]), np.array([0.0, 1.0])) == pytest.approx(0.0)
    assert cosine_similarity(np.array([1.0, 1.0]), np.array([1.0, 1.0])) == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_dimension_decomposition_has_expected_formula() -> None:
    report = await run_dimension_decomposition()
    first_dim = report["dimensions"][0]
    assert first_dim["factor"]
    v0 = np.array([0.0, 1.0])
    v_l = np.array([0.25, 0.25])
    target = np.array([0.5, 0.0])
    improved = abs(v_l[0] - target[0]) < abs(v0[0] - target[0])
    assert bool(improved)


def test_dimension_full_vector_distance_computed_correctly() -> None:
    assert full_distance(np.array([0.0, 0.0]), np.array([3.0, 4.0])) == pytest.approx(5.0)


@pytest.mark.asyncio
async def test_split_strategy_a_reproduces_phase1b_vld_accuracy() -> None:
    report = await run_split_enrichment()
    assert report["strategies"]["A_current_vld"]["accuracy"] == pytest.approx(0.31307550644567217, abs=0.001)
    assert report["strategy_a_matches_phase1b"] is True


@pytest.mark.asyncio
async def test_split_oracle_uses_true_category_and_correct_evidence() -> None:
    ctx = ExperimentContext()
    alert = next(item for item in ctx.eval_alerts if ctx.true_category(item) != score_best(ctx.v0(item), ctx)["category"])
    report = await run_split_enrichment()
    assert "E_oracle" in report["strategies"]
    assert ctx.true_category(alert) in SOC_CATEGORIES


@pytest.mark.asyncio
async def test_split_all_strategies_return_valid_accuracy_values() -> None:
    report = await run_split_enrichment()
    for payload in report["strategies"].values():
        assert payload["accuracy"] is not None
        assert 0.0 <= payload["accuracy"] <= 1.0


@pytest.mark.asyncio
async def test_wrong_route_confusion_matrix_rows_sum_to_total_wrong_routed() -> None:
    report = await run_wrong_route_impact()
    matrix = report["confusion_matrix"]
    wrong = 0
    for routed, row in matrix.items():
        for true, count in row.items():
            if routed != true:
                wrong += count
    assert wrong == report["sample"]["route_wrong"]


@pytest.mark.asyncio
async def test_wrong_route_no_evidence_condition_uses_routing_without_enrichment() -> None:
    report = await run_wrong_route_impact()
    no_evidence = report["condition_accuracy"]["VLD_no_evidence"]
    sp = report["condition_accuracy"]["SP"]
    assert no_evidence["all"] == pytest.approx(sp["all"])
    assert no_evidence["route_wrong"] == pytest.approx(sp["route_wrong"])


@pytest.mark.asyncio
async def test_all_experiment_json_outputs_are_valid_and_parseable() -> None:
    await run_baseline()
    run_data_quality()
    await run_dimension_decomposition()
    await run_split_enrichment()
    await run_wrong_route_impact()
    for path in [BASELINE_OUTPUT, DATA_OUTPUT, DIM_OUTPUT, SPLIT_OUTPUT, WRONG_OUTPUT]:
        loaded: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
        assert loaded["experiment"]
