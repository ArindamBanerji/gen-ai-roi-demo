from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.services.investigation_patterns import (
    MULTIHOP_PATTERN_REGISTRY,
    PATTERN_REGISTRY,
    CredentialLateralPattern,
    InsiderCompromisedPattern,
    MaintenanceWindowPattern,
    PrivilegeChainPattern,
)
from app.services.multihop_scenarios import (
    ScenarioGraphStore,
    load_stage1_scenarios,
    run_stage1_investigation,
    scenario_by_id,
)
from scripts.evaluate_multihop_stage1 import evaluate_all
from scripts.seed_multihop_graph import build_seed_payload, write_seed_artifact


def _scenario(scenario_id: str) -> dict:
    scenario = scenario_by_id(scenario_id)
    assert scenario is not None
    return dict(scenario)


def test_seed_multihop_graph_builds_idempotent_payload(tmp_path: Path) -> None:
    first = build_seed_payload()
    second = build_seed_payload()
    assert first == second
    assert first["scenario_count"] == 50
    assert len(first["nodes"]) >= 100
    assert len(first["edges"]) >= 40
    assert "EmploymentContext" in first["node_types"]
    assert "HAS_EMPLOYMENT_CONTEXT" in first["edge_types"]
    out = tmp_path / "seed.json"
    written = write_seed_artifact(out)
    assert json.loads(out.read_text(encoding="utf-8")) == written


def test_multihop_patterns_registered_and_existing_preserved() -> None:
    assert len(PATTERN_REGISTRY) == 6
    assert len(MULTIHOP_PATTERN_REGISTRY) == 8
    assert {p.pattern_name for p in MULTIHOP_PATTERN_REGISTRY.values()} == set(MULTIHOP_PATTERN_REGISTRY)


def test_each_new_pattern_instantiates_and_has_category() -> None:
    for pattern in MULTIHOP_PATTERN_REGISTRY.values():
        assert pattern.category_name
        assert pattern.pattern_name
        assert pattern.selected_edge
        assert pattern.evidence_keys()


def test_credential_insider_pattern_branches_on_departing_employee() -> None:
    scenario = _scenario("SOC-MH-002-v1")
    store = ScenarioGraphStore(scenario)
    pattern = InsiderCompromisedPattern()
    evidence = asyncio.run(pattern.execute(scenario["alert"], store))
    assert evidence["scenario_type"] == "insider_vs_compromised"
    assert evidence["correct_branch"] is True
    assert evidence["factor_enriched"] == "pattern_history"


def test_credential_insider_pattern_branches_on_active_employee_variant() -> None:
    scenario = _scenario("SOC-MH-002-v3")
    store = ScenarioGraphStore(scenario)
    pattern = InsiderCompromisedPattern()
    evidence = asyncio.run(pattern.execute(scenario["alert"], store))
    assert evidence["scenario_type"] == "insider_vs_compromised"
    assert evidence["factor_enriched"] in {"pattern_history", "device_trust", "privileged_identity_context"}
    assert "evidence_found" in evidence


def test_maintenance_window_pattern_suppresses_active_window() -> None:
    scenario = _scenario("SOC-MH-004-v1")
    result = asyncio.run(run_stage1_investigation(scenario))
    assert result.action == "suppress"
    assert result.steps == 1
    assert result.trace[0].evidence_keys
    pattern = MaintenanceWindowPattern()
    evidence = asyncio.run(pattern.execute(scenario["alert"], ScenarioGraphStore(scenario)))
    assert evidence["scenario_type"] == "maintenance_window_false_positive"


def test_privilege_chain_pattern_follows_three_hops_to_escalate() -> None:
    scenario = _scenario("SOC-MH-005-v1")
    result = asyncio.run(run_stage1_investigation(scenario))
    assert result.action == "escalate"
    assert result.steps == 3
    assert [step.selected_edge for step in result.trace]
    pattern = PrivilegeChainPattern()
    evidence = asyncio.run(pattern.execute(scenario["alert"], ScenarioGraphStore(scenario)))
    assert evidence["scenario_type"] == "privilege_escalation_chain"


def test_investigation_loop_showcase_one_has_multihop_trace() -> None:
    result = asyncio.run(run_stage1_investigation(_scenario("SOC-MH-002-v1")))
    assert result.steps >= 2
    assert result.fixture_source == "planted"
    assert result.trace[0].candidate_reads


def test_investigation_loop_showcase_two_has_single_hop_trace() -> None:
    result = asyncio.run(run_stage1_investigation(_scenario("SOC-MH-004-v1")))
    assert result.steps == 1
    assert result.action == "suppress"


def test_flat_alert_still_produces_valid_investigation_result() -> None:
    scenario = next(s for s in load_stage1_scenarios() if s["scenario_type"] == "flat_control")
    result = asyncio.run(run_stage1_investigation(scenario))
    assert result.steps == 0
    assert result.trace == []
    assert result.action in {"escalate", "investigate", "monitor", "suppress"}


def test_investigate_endpoint_stage1_payload_shape() -> None:
    from app.routers.triage import ProcessAlertRequest, investigate_alert

    response = asyncio.run(investigate_alert(ProcessAlertRequest(alert_id="ALERT-MH-003-v1"), None))
    payload = response["vld"]
    assert response["status"] == "ok"
    assert response["mode"] == "vld_multihop_stage1_shadow"
    assert payload["fixture_source"] == "planted"
    assert payload["trace"]
    assert payload["conservation_emit_gate"] == "not_evaluated_read_only"


def test_all_50_stage1_instances_produce_investigation_result() -> None:
    scenarios = load_stage1_scenarios()
    results = [asyncio.run(run_stage1_investigation(s)) for s in scenarios]
    assert len(results) == 50
    assert all(r.action in {"escalate", "investigate", "monitor", "suppress"} for r in results)


def test_stage1_high_rho_vld_reproduction() -> None:
    summary = evaluate_all()
    rows = summary["results"]
    high = [
        r for r in rows
        if r["arm"] == "vld" and r["branching_kind"] == "score_keyed" and float(r["rho_planted"]) >= 0.7
    ]
    assert len(high) == 16
    assert sum(1 for r in high if r["correct"]) / len(high) == 1.0
