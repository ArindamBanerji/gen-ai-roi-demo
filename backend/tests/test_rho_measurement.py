"""Tests for SOC VLD Phase 1b rho measurement infrastructure."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, cast

import numpy as np
import pytest

from app.domains.soc.config import SOC_CATEGORIES, SOCDomainConfig
from app.models.investigation import InvestigationResult
from app.services.investigation_comparators import (
    BreadthPolicy,
    ContentRulePolicy,
    MajorityBranchPolicy,
    RandomBranchPolicy,
    SinglePassPolicy,
)
from app.services.investigation_loop import InvestigationLoop
from app.services.investigation_patterns import PATTERN_REGISTRY
from app.services.investigation_router import InvestigationRouter
from scripts.generate_score_keyed_alerts import generate_score_keyed_alerts
from scripts.measure_rho import (
    FixtureFactorProvider,
    FixtureGraphStore,
    compute_rho,
    margin_from_distances,
    run_measurement,
    vector_skew,
    vectors_by_alert,
)
from scripts.diagnose_value_chain import run_diagnostic


class _Policy(Protocol):
    async def investigate(self, alert_context: dict[str, Any], scorer: Any, factor_provider: Any, graph_store: Any) -> InvestigationResult:
        ...


class _Graph(FixtureGraphStore):
    pass


def _fixture_vector(category: str = "credential_access") -> np.ndarray:
    scorer = SOCDomainConfig().build_profile_scorer()
    return cast(np.ndarray, np.asarray(scorer.centroids[SOC_CATEGORIES.index(category), 0, :], dtype=np.float64).copy())


def _provider(vector: np.ndarray | None = None) -> FixtureFactorProvider:
    return FixtureFactorProvider({"A1": [float(x) for x in (vector if vector is not None else _fixture_vector())]})


def _alert(category: str = "credential_access") -> dict[str, Any]:
    return {"alert_id": "A1", "category": category, "alert_type": category, "origin": "test"}


def _scorer() -> Any:
    return SOCDomainConfig().build_profile_scorer()


@pytest.mark.asyncio
async def test_single_pass_policy_returns_zero_step_result() -> None:
    result = await SinglePassPolicy().investigate(_alert(), _scorer(), _provider(), _Graph())
    assert isinstance(result, InvestigationResult)
    assert result.steps == 0
    assert result.policy == "single_pass"


@pytest.mark.asyncio
async def test_content_rule_policy_uses_alert_category_label() -> None:
    result = await ContentRulePolicy(PATTERN_REGISTRY).investigate(_alert("malware_execution"), _scorer(), _provider(), _Graph())
    assert result.steps == 1
    assert result.trace[0].pattern == "malware_execution"
    assert result.policy == "content_rule"


@pytest.mark.asyncio
async def test_content_rule_policy_falls_back_without_label() -> None:
    alert = {"alert_id": "A1", "origin": "test"}
    result = await ContentRulePolicy(PATTERN_REGISTRY).investigate(alert, _scorer(), _provider(), _Graph())
    assert result.steps == 0
    assert result.policy == "single_pass"


@pytest.mark.asyncio
async def test_majority_branch_policy_uses_configured_majority_category() -> None:
    result = await MajorityBranchPolicy("cloud_infrastructure", PATTERN_REGISTRY).investigate(_alert(), _scorer(), _provider(), _Graph())
    assert result.steps == 1
    assert result.trace[0].pattern == "cloud_infrastructure"
    assert result.policy == "majority_branch"


@pytest.mark.asyncio
async def test_random_branch_policy_returns_valid_result() -> None:
    result = await RandomBranchPolicy(PATTERN_REGISTRY, seed=3).investigate(_alert(), _scorer(), _provider(), _Graph())
    assert isinstance(result, InvestigationResult)
    assert result.steps == 1
    assert result.trace[0].pattern in SOC_CATEGORIES
    assert result.policy == "random_branch"


@pytest.mark.asyncio
async def test_breadth_policy_reads_all_patterns() -> None:
    result = await BreadthPolicy(PATTERN_REGISTRY).investigate(_alert(), _scorer(), _provider(), _Graph())
    assert result.steps == len(PATTERN_REGISTRY)
    assert {step.pattern for step in result.trace} == set(PATTERN_REGISTRY)
    assert result.policy == "breadth_all"


@pytest.mark.asyncio
async def test_all_comparators_return_required_fields() -> None:
    policies: list[_Policy] = [
        SinglePassPolicy(),
        ContentRulePolicy(PATTERN_REGISTRY),
        MajorityBranchPolicy("credential_access", PATTERN_REGISTRY),
        RandomBranchPolicy(PATTERN_REGISTRY),
        BreadthPolicy(PATTERN_REGISTRY),
    ]
    for policy in policies:
        result = await policy.investigate(_alert(), _scorer(), _provider(), _Graph())
        payload = result.to_dict()
        assert payload["policy"]
        assert payload["action"]
        assert payload["category"] in SOC_CATEGORIES
        assert isinstance(payload["v_final"], list)


def test_stripped_alerts_have_no_category_fields(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture.json"
    out = tmp_path / "score_keyed.json"
    truth = tmp_path / "truth.json"
    fixture.write_text(json.dumps({"alerts": [_alert("credential_access")]}), encoding="utf-8")
    generate_score_keyed_alerts(fixture, out, truth)
    alerts = json.loads(out.read_text(encoding="utf-8"))
    assert all("category" not in alert and "alert_type" not in alert and "category_index" not in alert for alert in alerts)


def test_ground_truth_mapping_preserves_original_categories(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture.json"
    out = tmp_path / "score_keyed.json"
    truth = tmp_path / "truth.json"
    fixture.write_text(json.dumps({"alerts": [_alert("lateral_movement")]}), encoding="utf-8")
    generate_score_keyed_alerts(fixture, out, truth)
    assert json.loads(truth.read_text(encoding="utf-8")) == {"A1": "lateral_movement"}


@pytest.mark.asyncio
async def test_fixture_provider_produces_valid_vector_from_stripped_alert() -> None:
    vector = _fixture_vector("credential_access")
    provider = _provider(vector)
    stripped = {"alert_id": "A1", "origin": "test"}
    v, _ = await provider.compute(stripped, _Graph())
    assert v.shape == (6,)
    np.testing.assert_allclose(v, vector)


def test_rho_computation_three_of_six() -> None:
    assert compute_rho(["a", "b", "c", "a", "b", "c"], ["a", "x", "c", "y", "b", "z"]) == 0.5


def test_margin_computation_uses_second_minus_first() -> None:
    assert margin_from_distances({"a": 0.2, "b": 0.7, "c": 0.4}) == pytest.approx(0.2)


def test_mu_skew_uses_l2_norm() -> None:
    assert vector_skew(np.array([0.0, 0.0]), np.array([3.0, 4.0])) == pytest.approx(5.0)


@pytest.mark.asyncio
async def test_json_report_output_contains_required_keys(tmp_path: Path) -> None:
    report = await run_measurement()
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    for key in ["rho_vld", "rho_vld_scorekey", "rho_majority", "gate_verdict", "margin_distribution", "mu_skew"]:
        assert key in loaded


@pytest.mark.asyncio
async def test_value_chain_diagnostic_report_contains_h2_gate_fields(tmp_path: Path) -> None:
    report = await run_diagnostic()
    path = tmp_path / "value_chain.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    h2 = loaded["hypotheses"]["H2_scoring_locked_to_routed_category"]
    assert "score_best_accuracy" in h2
    assert "score_in_last_investigated_accuracy" in h2
    assert "current_vld_matches_score_best" in h2
    assert "conclusion" in loaded


@pytest.mark.asyncio
async def test_vld_investigation_changes_v_on_fixture_alert() -> None:
    scorer = _scorer()
    vector = _fixture_vector("credential_access")
    provider = _provider(vector)
    result = await InvestigationLoop(scorer, InvestigationRouter(PATTERN_REGISTRY), provider, L_max=1, residual_threshold=0.0).investigate(_alert(), _Graph())
    assert not np.allclose(np.asarray(result.v_final), vector)


@pytest.mark.asyncio
async def test_reextraction_budget_one_equals_surface_plus_evidence_average() -> None:
    scorer = _scorer()
    vector = np.zeros(6, dtype=np.float64)
    provider = _provider(vector)
    result = await InvestigationLoop(scorer, InvestigationRouter(PATTERN_REGISTRY), provider, L_max=1, residual_threshold=0.0).investigate(_alert(), _Graph())
    expected = (vector + PATTERN_REGISTRY[result.trace[0].pattern].evidence_vector({})) / 2.0
    np.testing.assert_allclose(np.asarray(result.v_final), expected)


@pytest.mark.asyncio
async def test_vld_routes_differently_than_content_rule_on_mismatched_label() -> None:
    scorer = _scorer()
    provider = _provider(_fixture_vector("credential_access"))
    alert = _alert("malware_execution")
    vld = await InvestigationLoop(scorer, InvestigationRouter(PATTERN_REGISTRY), provider, L_max=1, residual_threshold=0.0).investigate(alert, _Graph())
    content = await ContentRulePolicy(PATTERN_REGISTRY).investigate(alert, scorer, provider, _Graph())
    assert vld.trace[0].pattern == "credential_access"
    assert content.trace[0].pattern == "malware_execution"
