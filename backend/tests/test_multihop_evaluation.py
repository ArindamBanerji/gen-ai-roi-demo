from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.evaluate_multihop_stage1 import (
    DATA_PATH,
    RESULTS_PATH,
    ScenarioGraphStore,
    action_for_branches,
    build_scorer,
    evaluate_all,
    evaluate_arm,
    load_scenarios,
    select_correct_budgeted,
    select_random_budgeted,
    select_vld_branches,
    surface_vector_from_alert,
)


@pytest.fixture(scope="module")
def scenarios():
    return load_scenarios(DATA_PATH)


def test_scenario_graph_store_returns_correct_evidence(scenarios):
    scenario = next(s for s in scenarios if s["correct_branches"])
    branch = scenario["correct_branches"]["1"][0]
    evidence = ScenarioGraphStore(scenario).get_evidence(branch, 1)
    assert evidence["branch_name"] == branch
    assert evidence["correct_branch"] is True
    assert evidence["factor_enriched"] in scenario["alert"]["surface_factors"]


def test_scenario_graph_store_returns_misleading_evidence(scenarios):
    scenario = next(s for s in scenarios if s["misleading_branches"])
    branch = scenario["misleading_branches"][0]
    evidence = ScenarioGraphStore(scenario).get_evidence(branch)
    assert evidence["branch_name"] == branch
    assert evidence["misleading_branch"] is True
    assert 0.0 <= evidence["factor_new_value"] <= 1.0


def test_single_pass_arm_uses_only_surface_factors(scenarios):
    scorer = build_scorer()
    scenario = scenarios[0]
    row = evaluate_arm(scenario, "single_pass", scorer)
    assert row.read_branches == []
    assert row.cost_used == 0
    assert surface_vector_from_alert(scenario["alert"]).shape == (6,)


def test_breadth_arm_reads_budgeted_branches(scenarios):
    scenario = next(s for s in scenarios if s["available_branches"])
    branches = select_random_budgeted(scenario, seed="test")
    assert sum(scenario["read_costs"][b] for b in branches) <= scenario["budget"]
    assert set(branches).issubset({b for bs in scenario["available_branches"].values() for b in bs})


def test_content_rule_arm_uses_correct_branches(scenarios):
    scenario = next(s for s in scenarios if s["correct_branches"])
    branches = select_correct_budgeted(scenario)
    assert branches
    correct = {b for bs in scenario["correct_branches"].values() for b in bs}
    assert set(branches).issubset(correct)


def test_vld_arm_uses_scenario_routing_store(scenarios):
    scorer = build_scorer()
    scenario = next(s for s in scenarios if s["branching_kind"] == "score_keyed" and s["rho_planted"] == 1.0)
    branches = select_vld_branches(scenario, scorer)
    row = evaluate_arm(scenario, "vld", scorer)
    assert row.read_branches == branches
    assert row.arm == "vld"
    assert row.budget >= row.cost_used


def test_flat_control_vld_does_not_beat_single_pass(scenarios):
    payload = evaluate_all(scenarios)
    flat = payload["controls"]["flat"]
    assert flat["vld"] <= flat["single_pass"]


def test_rho_0_50_control_vld_near_chance(scenarios):
    payload = evaluate_all(scenarios)
    vld = payload["controls"]["rho_0_50"]["vld"]
    assert 0.10 <= vld <= 0.40


def test_report_json_has_required_sections(scenarios):
    payload = evaluate_all(scenarios)
    for key in ["per_kind_accuracy", "per_rho_accuracy", "controls", "acceptance_test", "headline_vld_minus_content_rule_score_keyed"]:
        assert key in payload
    assert payload["acceptance_test"]["verdict"] in {"PASS", "FAIL"}


def test_all_50_instances_evaluated_no_skips(scenarios):
    payload = evaluate_all(scenarios)
    assert payload["n_scenarios"] == 50
    assert len(payload["results"]) == 50 * 4
    assert {row["arm"] for row in payload["results"]} == {"single_pass", "breadth", "content_rule", "vld"}


def test_action_for_correct_branch_returns_ground_truth(scenarios):
    scorer = build_scorer()
    scenario = next(s for s in scenarios if s["correct_branches"])
    branch = scenario["correct_branches"]["1"][0]
    assert action_for_branches(scenario, [branch], scorer) == scenario["decision_tree"]["ground_truth_action"]
