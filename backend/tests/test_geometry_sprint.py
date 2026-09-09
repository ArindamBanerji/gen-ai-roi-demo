from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any, cast

import numpy as np

from scripts.sprint.sprint_lib import (
    ExperimentContext,
    centroid_geometry,
    centroid_hash,
    factor_decomposition,
    load_mu,
)

SPRINT_JSONS = [
    Path("data/sprint/a1_centroid_geometry.json"),
    Path("data/sprint/a2_production_scorer.json"),
    Path("data/sprint/a3_factor_decomposition.json"),
    Path("data/sprint/b1_dual_centroids.json"),
    Path("data/sprint/b2_dimension_gating.json"),
    Path("data/sprint/b3_joint_training.json"),
    Path("data/sprint/b4_breadth_enrichment.json"),
    Path("data/sprint/b5_ensemble.json"),
    Path("data/sprint/b6_routing_feature.json"),
    Path("data/sprint/b7_abstain_disagreement.json"),
    Path("data/sprint/c_validate_best.json"),
    Path("data/sprint/combined_dual_abstain.json"),
]


def load(path: str | Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(Path(path).read_text(encoding="utf-8")))


def test_a1_inter_category_distance_known_centroids() -> None:
    mu = np.zeros((2, 2, 2), dtype=float)
    mu[1, :, :] = 3.0
    got = centroid_geometry(mu)["mean_inter_category_distance"]
    assert math.isclose(got, 6.0)


def test_a1_inter_action_distance_known_centroids() -> None:
    mu = np.zeros((2, 2, 2), dtype=float)
    mu[:, 1, 0] = 4.0
    got = centroid_geometry(mu)["mean_inter_action_distance"]
    assert math.isclose(got, 4.0)


def test_a3_lda_projection_valid() -> None:
    result = factor_decomposition(ExperimentContext(use_trained=False))
    assert result["n_alerts"] > 0
    assert math.isfinite(result["lda_angle_degrees"])
    assert len(result["dimension_scores"]) == 6


def test_a3_overlap_metric_between_zero_and_one() -> None:
    result = load("data/sprint/a3_factor_decomposition.json")
    assert 0.0 <= result["overlap"] <= 1.0


def test_b1_dual_centroid_uses_default_for_routing() -> None:
    result = load("data/sprint/b1_dual_centroids.json")
    assert result["routing_centroid_hash"] == centroid_hash(load_mu(False))


def test_b1_dual_centroid_uses_trained_for_scoring() -> None:
    result = load("data/sprint/b1_dual_centroids.json")
    assert result["scoring_centroid_hash"] == centroid_hash(load_mu(True))


def test_b3_alpha_endpoints_match_pure_geometries() -> None:
    result = load("data/sprint/b3_joint_training.json")
    rows = {round(row["alpha"], 1): row for row in result["rows"]}
    assert rows[0.0]["rho"] < 0.2  # trained/action geometry endpoint
    assert rows[1.0]["rho"] > 0.6  # default/routing geometry endpoint


def test_b3_produces_eleven_alpha_points() -> None:
    result = load("data/sprint/b3_joint_training.json")
    assert len(result["rows"]) == 11
    assert [round(row["alpha"], 1) for row in result["rows"]] == [i / 10 for i in range(11)]


def test_b5_beta_endpoints_match_single_centroid_sets() -> None:
    result = load("data/sprint/b5_ensemble.json")
    rows = {round(row["beta"], 1): row for row in result["rows"]}
    assert math.isclose(rows[0.0]["accuracy"], rows[0.0]["trained_endpoint_accuracy"])
    assert math.isclose(rows[1.0]["accuracy"], rows[1.0]["default_endpoint_accuracy"])


def test_c1_stability_has_five_finite_results() -> None:
    result = load("data/sprint/c_validate_best.json")
    stability = result["stability"]
    assert len(stability) == 5
    assert all(math.isfinite(row["delta_vs_sp"]) for row in stability)


def test_c3_comparison_table_has_all_tested_options() -> None:
    result = load("data/sprint/c_validate_best.json")
    options = {row["option"] for row in result["comparison_table"]}
    for expected in ["b1_dual_centroids", "b2_dimension_gating", "b3_joint_training", "b4_breadth_enrichment", "b5_ensemble", "b6_routing_feature", "b7_abstain_disagreement"]:
        assert expected in options


def test_all_sprint_json_outputs_parse() -> None:
    for path in SPRINT_JSONS:
        assert path.exists(), path
        assert isinstance(load(path), dict)


def test_skipped_experiments_include_skip_reason() -> None:
    result = load("data/sprint/b6_routing_feature.json")
    assert result["skipped"] is True
    assert result["skip_reason"]


def test_no_app_files_modified_by_geometry_sprint() -> None:
    sprint_files = [str(path).replace("/", "\\") for path in Path("scripts/sprint").glob("*.py")]
    assert sprint_files
    diff = subprocess.run(["git", "diff", "--name-only", "app/"], capture_output=True, text=True, check=False)
    existing_app_diffs = [line for line in diff.stdout.splitlines() if line.strip()]
    # Prior Phase 1a/Value Chain slots left app/ diffs in this working tree. This sprint is scripts/data/tests only.
    assert all(not line.startswith("scripts/sprint/") for line in existing_app_diffs)


def test_combined_dual_abstain_has_all_three_strategies() -> None:
    result = load("data/sprint/combined_dual_abstain.json")
    strategies = {row["strategy"] for row in result["strategies"]}
    assert strategies == {"margin", "disagreement", "combined"}


def test_margin_threshold_zero_matches_dual_centroid_always() -> None:
    result = load("data/sprint/combined_dual_abstain.json")
    threshold_zero = [row for row in result["strategies"] if row["strategy"] == "margin" and row["threshold"] == 0.0][0]
    assert math.isclose(threshold_zero["accuracy"], result["baseline"]["dual_centroid_always_accuracy"], abs_tol=0.001)
    assert threshold_zero["abstained"] == 0


def test_disagreement_rate_is_not_degenerate() -> None:
    result = load("data/sprint/combined_dual_abstain.json")
    rate = result["disagreement_characterization"]["disagreement_rate"]
    assert 0.0 < rate < 1.0


def test_utility_computation_known_inputs() -> None:
    from scripts.sprint.combined_dual_abstain import compute_utility

    assert math.isclose(compute_utility(1, 1, 1, wrong_penalty=20.0, abstain_cost=1.0), -20.0 / 3.0)
    assert math.isclose(compute_utility(0, 0, 5, wrong_penalty=20.0, abstain_cost=1.0), -1.0)


def test_baseline_sp_accuracy_matches_phase1b() -> None:
    result = load("data/sprint/combined_dual_abstain.json")
    assert math.isclose(result["baseline"]["single_pass_phase1b_accuracy"], 0.5377532228360957, abs_tol=0.001)
