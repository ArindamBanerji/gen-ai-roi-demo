"""SOC VLD investigation loop tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.domains.soc.config import SOC_CATEGORIES, SOCDomainConfig
from app.services.investigation_loop import AggregationMethod, InvestigationLoop, RESIDUAL_THRESHOLD
from app.services.investigation_patterns import (
    PATTERN_REGISTRY,
    BaseInvestigationPattern,
    build_default_investigation_patterns,
)
from app.services.investigation_router import InvestigationRouter


class _GraphStore:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def get_security_context(self, alert_id: str) -> dict[str, Any]:
        return {
            "alert_id": alert_id,
            "user_id": "user-1",
            "asset_id": "asset-1",
            "pattern_id": "PAT-CRED-001",
            "nodes_consulted": 3,
            "origin": "zero_day_synthetic",
        }

    async def run_query(self, query: str) -> list[dict[str, Any]]:
        self.queries.append(query)
        return [{"alert_id": "ALT-VLD-001", "user_id": "user-1", "asset_id": "asset-1"}]


class _FactorProvider:
    def __init__(self, initial: np.ndarray) -> None:
        self.initial = np.asarray(initial, dtype=np.float64)
        self.calls: list[dict[str, Any]] = []

    async def compute(self, alert: dict[str, Any], context: Any) -> tuple[np.ndarray, dict[str, dict[str, Any]]]:
        self.calls.append({"alert": dict(alert), "context": context})
        surface = getattr(context, "vld_surface_vector", None)
        evidence_vectors = getattr(context, "vld_factor_vectors", None)
        if surface is not None and evidence_vectors:
            arrays = [np.asarray(surface, dtype=np.float64)] + [
                np.asarray(item, dtype=np.float64) for item in evidence_vectors
            ]
            return np.clip(sum(arrays) / float(len(arrays)), 0.0, 1.0), {"test": {"source": "evidence"}}
        return self.initial.copy(), {"test": {"source": "initial"}}


class _CountingScorer:
    def __init__(self, base: Any) -> None:
        self._base = base
        self.score_calls = 0

    @property
    def centroids(self) -> Any:
        return self._base.centroids

    @property
    def actions(self) -> Any:
        return self._base.actions

    @property
    def categories(self) -> Any:
        return self._base.categories

    @property
    def tau(self) -> float:
        return float(self._base.tau)

    def score(self, *args: Any, **kwargs: Any) -> Any:
        self.score_calls += 1
        return self._base.score(*args, **kwargs)


def _scorer() -> Any:
    return SOCDomainConfig().build_profile_scorer()


def _centroid(scorer: Any, category: str, action_index: int = 0) -> np.ndarray:
    value: np.ndarray = np.asarray(scorer.centroids[SOC_CATEGORIES.index(category), action_index, :], dtype=np.float64)
    return value


def _loop(
    scorer: Any,
    provider: _FactorProvider,
    *,
    L_max: int = 3,
    residual_threshold: float = RESIDUAL_THRESHOLD,
    max_flips: int = 2,
    aggregation_method: str = "reextract",
    patterns: dict[str, Any] | None = None,
) -> InvestigationLoop:
    router = InvestigationRouter(patterns or build_default_investigation_patterns(), L_max=L_max)
    return InvestigationLoop(
        scorer,
        router,
        provider,
        L_max=L_max,
        eps=0.5,
        residual_threshold=residual_threshold,
        max_flips=max_flips,
        aggregation_method=cast(AggregationMethod, aggregation_method),
    )


def _alert(category: str = "malware_execution") -> dict[str, Any]:
    return {
        "alert_id": "ALT-VLD-001",
        "alert_type": category,
        "category": category,
        "origin": "zero_day_synthetic",
    }


@pytest.mark.asyncio
async def test_step_zero_uses_centroid_routing_not_alert_label() -> None:
    scorer = _scorer()
    provider = _FactorProvider(_centroid(scorer, "credential_access"))

    result = await _loop(scorer, provider, L_max=1, residual_threshold=0.0).investigate(
        _alert("malware_execution"),
        _GraphStore(),
    )

    assert result.trace[0].pattern == "credential_access"
    assert result.trace[0].alert_category == "malware_execution"


@pytest.mark.asyncio
async def test_single_step_investigation_dispatches_pattern_and_logs_trace() -> None:
    scorer = _scorer()
    provider = _FactorProvider(_centroid(scorer, "credential_access"))

    result = await _loop(scorer, provider, L_max=1, residual_threshold=0.0).investigate(_alert(), _GraphStore())

    assert result.steps == 1
    assert result.trace[0].pattern == "credential_access"
    assert result.trace[0].selected_edge == "INVOLVES"
    assert "investigation_pattern" in result.trace[0].evidence_keys
    assert result.trace[0].cat_distances_before["credential_access"] >= 0.0


@pytest.mark.asyncio
async def test_multi_step_investigation_uses_updated_centroid_geometry() -> None:
    scorer = _scorer()
    provider = _FactorProvider(_centroid(scorer, "credential_access"))

    result = await _loop(scorer, provider, L_max=2, residual_threshold=0.0).investigate(_alert(), _GraphStore())

    assert result.steps == 2
    assert result.trace[0].pattern == "credential_access"
    assert result.trace[1].pattern != result.trace[0].pattern
    assert result.trace[1].pattern in SOC_CATEGORIES


@pytest.mark.asyncio
async def test_final_score_uses_no_category_locked_scorer_calls() -> None:
    scorer = _CountingScorer(_scorer())
    provider = _FactorProvider(_centroid(scorer, "credential_access"))

    result = await _loop(scorer, provider, L_max=2, residual_threshold=0.0).investigate(_alert(), _GraphStore())

    assert scorer.score_calls == 0
    assert result.category in SOC_CATEGORIES
    assert result.action in scorer.actions


@pytest.mark.asyncio
async def test_final_action_uses_best_across_all_categories() -> None:
    scorer = _scorer()
    surface = _centroid(scorer, "credential_access", 0)
    provider = _FactorProvider(surface)
    router = InvestigationRouter(PATTERN_REGISTRY)

    result = await InvestigationLoop(scorer, router, provider, L_max=1, residual_threshold=0.0).investigate(
        _alert("malware_execution"),
        _GraphStore(),
    )
    expected = router.score_best_from_centroids(np.asarray(result.v_final, dtype=np.float64), scorer)

    assert result.action == expected.action
    assert result.category == expected.category


@pytest.mark.asyncio
async def test_investigated_category_is_logged_separately_from_final_category() -> None:
    scorer = _scorer()
    provider = _FactorProvider(_centroid(scorer, "credential_access", 0))

    result = await _loop(scorer, provider, L_max=1, residual_threshold=0.0).investigate(
        _alert("malware_execution"),
        _GraphStore(),
    )

    assert result.investigated_category == result.trace[-1].pattern
    assert result.routing_agreed == (result.investigated_category == result.category)
    assert result.trace[-1].alert_category == "malware_execution"


@pytest.mark.asyncio
async def test_routing_decision_is_independent_of_final_score_contract() -> None:
    scorer = _scorer()
    provider = _FactorProvider(_centroid(scorer, "credential_access", 0))

    result = await _loop(scorer, provider, L_max=1, residual_threshold=0.0).investigate(
        _alert("malware_execution"),
        _GraphStore(),
    )

    assert result.trace[0].pattern == "credential_access"
    assert result.trace[0].pattern == result.investigated_category


@pytest.mark.asyncio
async def test_budget_exhaustion_halts_at_l_max() -> None:
    scorer = _scorer()
    provider = _FactorProvider(_centroid(scorer, "credential_access"))

    result = await _loop(scorer, provider, L_max=1, residual_threshold=0.0).investigate(_alert(), _GraphStore())

    assert result.steps == 1
    assert result.trace[-1].halt_reason == "budget_exhausted"
    assert result.halt_reason == "budget_exhausted"


@pytest.mark.asyncio
async def test_residual_halt_uses_pre_registered_threshold() -> None:
    scorer = _scorer()
    provider = _FactorProvider(_centroid(scorer, "credential_access"))

    result = await _loop(scorer, provider, L_max=3, residual_threshold=10.0).investigate(_alert(), _GraphStore())

    assert RESIDUAL_THRESHOLD == 0.05
    assert result.steps == 1
    assert result.trace[-1].residual < 10.0
    assert result.trace[-1].halt_reason == "residual_below_threshold"


@pytest.mark.asyncio
async def test_no_pattern_available_returns_single_pass_result() -> None:
    scorer = _scorer()
    provider = _FactorProvider(_centroid(scorer, "credential_access"))
    loop = InvestigationLoop(
        scorer,
        InvestigationRouter({}, L_max=3),
        provider,
        L_max=3,
        eps=1.0,
    )

    result = await loop.investigate(_alert(), _GraphStore())

    assert result.steps == 0
    assert result.trace == []
    assert result.action == result.single_pass_action
    assert result.halt_reason == "no_pattern_available"


@pytest.mark.asyncio
async def test_investigation_trace_has_required_shape_and_fields() -> None:
    scorer = _scorer()
    provider = _FactorProvider(_centroid(scorer, "credential_access"))

    result = await _loop(scorer, provider, L_max=1, residual_threshold=0.0).investigate(_alert(), _GraphStore())
    step = result.to_dict()["trace"][0]

    assert set(step) == {
        "step",
        "pattern",
        "alert_category",
        "v_before",
        "v_after",
        "cat_distances_before",
        "cat_distances_after",
        "evidence_keys",
        "candidate_reads",
        "selected_edge",
        "propensity",
        "cost",
        "timestamp",
        "policy_version",
        "residual",
        "halt_reason",
        "evidence_available",
        "evidence_admitted",
        "failure_reason",
    }
    assert len(step["v_before"]) == 6
    assert len(step["v_after"]) == 6
    assert set(step["cat_distances_before"]) == set(SOC_CATEGORIES)
    assert step["evidence_available"] is True
    assert step["evidence_admitted"] is True


@pytest.mark.asyncio
async def test_investigation_does_not_modify_scorer_centroids() -> None:
    scorer = _scorer()
    before = np.asarray(scorer.centroids).copy()
    provider = _FactorProvider(_centroid(scorer, "credential_access"))

    await _loop(scorer, provider, L_max=2, residual_threshold=0.0).investigate(_alert(), _GraphStore())

    np.testing.assert_allclose(np.asarray(scorer.centroids), before)


@pytest.mark.asyncio
async def test_single_pass_and_vld_results_are_returned_together() -> None:
    scorer = _scorer()
    provider = _FactorProvider(_centroid(scorer, "credential_access"))

    result = await _loop(scorer, provider, L_max=1, residual_threshold=0.0).investigate(_alert(), _GraphStore())
    payload = result.to_dict()

    assert payload["single_pass_action"]
    assert payload["single_pass_confidence"] >= 0.0
    assert payload["action"]
    assert payload["confidence"] >= 0.0
    assert "agreement" in payload


@pytest.mark.asyncio
async def test_campaign_bearing_seed_alert_runs_without_live_age() -> None:
    seed = json.loads(Path("support/setup/zero_day_decisions_v5.json").read_text(encoding="utf-8"))
    campaign_alert_id = seed["campaigns"][0]["member_alert_ids"][0]
    alert = next(item for item in seed["alerts"] if item["alert_id"] == campaign_alert_id)
    scorer = _scorer()
    category = alert.get("category") if alert.get("category") in SOC_CATEGORIES else "credential_access"
    provider = _FactorProvider(_centroid(scorer, category))

    result = await _loop(scorer, provider, L_max=1, residual_threshold=0.0).investigate(
        {**alert, "category": category},
        _GraphStore(),
    )

    assert result.steps == 1
    assert result.fixture_source == "planted"
    assert result.trace[0].cost >= 1.0


def test_default_patterns_return_different_evidence_keys() -> None:
    key_sets = {name: tuple(sorted(pattern.evidence_keys())) for name, pattern in PATTERN_REGISTRY.items()}

    assert set(key_sets) == set(SOC_CATEGORIES)
    assert len(set(key_sets.values())) == len(key_sets)


@pytest.mark.asyncio
async def test_evidence_enrichment_changes_vector_and_expected_dimensions() -> None:
    scorer = _scorer()
    surface = np.zeros(6, dtype=np.float64)
    provider = _FactorProvider(surface)

    result = await _loop(scorer, provider, L_max=1, residual_threshold=0.0).investigate(_alert(), _GraphStore())

    v1 = np.asarray(result.v_final, dtype=np.float64)
    assert not np.allclose(v1, surface)
    changed = set(np.flatnonzero(np.abs(v1 - surface) > 1.0e-8).tolist())
    pattern = PATTERN_REGISTRY[result.trace[0].pattern]
    assert isinstance(pattern, BaseInvestigationPattern)
    expected = {index for index, _value in pattern.vector_values}
    assert changed == expected


@pytest.mark.asyncio
async def test_reextraction_aggregation_averages_surface_and_all_evidence() -> None:
    scorer = _scorer()
    surface = np.zeros(6, dtype=np.float64)
    provider = _FactorProvider(surface)

    result = await _loop(scorer, provider, L_max=3, residual_threshold=0.0).investigate(_alert(), _GraphStore())

    expected = surface.copy()
    for step in result.trace:
        expected = expected + PATTERN_REGISTRY[step.pattern].evidence_vector({})
    expected = np.clip(expected / float(1 + len(result.trace)), 0.0, 1.0)
    np.testing.assert_allclose(np.asarray(result.v_final, dtype=np.float64), expected)


@pytest.mark.asyncio
async def test_damped_flag_keeps_comparison_path() -> None:
    scorer = _scorer()
    surface = np.zeros(6, dtype=np.float64)
    reextract_provider = _FactorProvider(surface)
    damped_provider = _FactorProvider(surface)

    reextract = await _loop(
        scorer,
        reextract_provider,
        L_max=2,
        residual_threshold=0.0,
        aggregation_method="reextract",
    ).investigate(_alert(), _GraphStore())
    damped = await _loop(
        scorer,
        damped_provider,
        L_max=2,
        residual_threshold=0.0,
        aggregation_method="damped",
    ).investigate(_alert(), _GraphStore())

    assert not np.allclose(np.asarray(reextract.v_final), np.asarray(damped.v_final))


def test_pattern_queries_are_schema_differentiated() -> None:
    signatures = {
        name: (pattern.selected_edge, pattern.graph_query, tuple(pattern.enriched_factors))
        for name, pattern in PATTERN_REGISTRY.items()
    }

    assert len(set(signatures.values())) == len(signatures)
    for name, (_edge, query, _factors) in signatures.items():
        assert "Alert" in query, name
        assert "ALT-FORMAT-PROBE" in query.format(alert_id="'ALT-FORMAT-PROBE'")
        assert not any(unavailable in query for unavailable in ["Process", "Session", "CloudResource"])


@pytest.mark.asyncio
async def test_flip_count_halts_at_exact_max_flips() -> None:
    scorer = _scorer()
    surface = _centroid(scorer, "credential_access", 0)
    pattern = BaseInvestigationPattern(
        category_name="credential_access",
        pattern_name="credential_flip_probe",
        traversal="Alert -> User",
        selected_edge="INVOLVES",
        enriched_factors=("privileged_identity_context",),
        candidate_read="credential_flip_probe",
        graph_query="MATCH (a:Alert {{alert_id: {alert_id}}})-[:INVOLVES]->(u:User) RETURN u.user_id AS user_id LIMIT 1",
        vector_values=tuple(enumerate(_centroid(scorer, "credential_access", 1).tolist())),
        specific_key_names=("credential_flip_signal",),
    )
    provider = _FactorProvider(surface)

    result = await _loop(
        scorer,
        provider,
        L_max=3,
        residual_threshold=0.0,
        max_flips=1,
        patterns={"credential_access": pattern},
    ).investigate(_alert(), _GraphStore())

    assert result.steps == 1
    assert result.trace[-1].halt_reason == "oscillation"


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["reextract", "damped"])
@pytest.mark.parametrize("failure", ["raise", "none", "malformed"])
@pytest.mark.parametrize("successful_reads", [0, 1])
async def test_unavailable_read_halts_at_last_valid_vector(mode, failure, successful_reads):
    scorer = _scorer()
    original_centroids = np.asarray(scorer.centroids).copy()
    surface = _centroid(scorer, "credential_access")
    provider = _FactorProvider(surface)
    graph = _GraphStore()
    last_read = RuntimeError("graph down") if failure == "raise" else None if failure == "none" else [None]
    reads = [[{"user_id": "user-1"}]] * successful_reads + [last_read]
    with patch.object(graph, "run_query", new=AsyncMock(side_effect=reads)) as query:
        result = await _loop(
            scorer, provider, L_max=3, residual_threshold=0.0,
            max_flips=10, aggregation_method=mode,
        ).investigate(_alert(), graph)
    failed = result.trace[-1]
    assert result.steps == len(result.trace) == successful_reads + 1
    assert query.await_count == successful_reads + 1
    assert len(provider.calls) == successful_reads + 1  # no extraction after failed read
    assert result.degraded is True and result.evidence_available is False
    assert result.failed_patterns == [PATTERN_REGISTRY[failed.pattern].pattern_name]
    assert result.halt_reason == failed.halt_reason == "evidence_unavailable"
    assert failed.evidence_available is False and failed.evidence_admitted is False
    assert failed.evidence_keys == [] and failed.failure_reason
    assert failed.v_before == failed.v_after == result.v_final
    assert failed.cat_distances_before == failed.cat_distances_after
    assert failed.residual == 0.0
    if successful_reads:
        assert result.v_final == result.trace[0].v_after
        assert result.v_final != surface.tolist()
    else:
        assert result.v_final == surface.tolist()
    expected = InvestigationRouter({}).score_best_from_centroids(np.asarray(result.v_final), scorer)
    assert (result.action, result.confidence) == (expected.action, expected.confidence)
    np.testing.assert_array_equal(scorer.centroids, original_centroids)


@pytest.mark.asyncio
async def test_successful_empty_read_remains_available():
    graph = _GraphStore()
    pattern = PATTERN_REGISTRY["credential_access"]
    with patch.object(graph, "run_query", new=AsyncMock(return_value=[])):
        evidence = await pattern.execute(_alert(), graph)
    assert evidence["evidence_available"] is True
    assert evidence["degraded"] is False
    assert len(evidence["vld_factor_vector"]) == 6


@pytest.mark.asyncio
@pytest.mark.parametrize("category", SOC_CATEGORIES)
async def test_investigation_pattern_query_executes_on_age(age_graph, category):
    alert_id = age_graph.alert(alert_type="anomalous_login")
    age_graph.query(
        "MATCH (a:Alert) "
        "CREATE (a)-[:INVOLVES]->(:User {user_id: 'u', risk_level: 'high', department: 'IT'}) "
        "CREATE (a)-[:DETECTED_ON]->(:Asset {asset_id: 'asset', criticality: 'high', asset_type: 'server'}) "
        "CREATE (a)-[:HAS_INDICATOR]->(:ThreatIndicator {indicator: 'test', severity: 'high'}) "
        "CREATE (a)-[:CLASSIFIED_AS]->(:AttackPattern {pattern_id: 'p', tactic: 'test'}) "
        "CREATE (a)-[:MEMBER_OF]->(:Campaign {campaign_id: 'c'}) RETURN a"
    )
    pattern = PATTERN_REGISTRY[category]
    # Exercise the exact production template against AGE, rather than a
    # permissive test reader that cannot detect invalid Cypher syntax.
    from app.graph_schema import _S
    rows = await age_graph.client.run_query(pattern.graph_query.format(alert_id=_S(alert_id)))
    assert len(rows) == 1
    assert any(value is not None for value in rows[0].values())


@pytest.mark.asyncio
async def test_adapter_rejects_failed_context_and_vector():
    from app.services.triage_providers import build_evidence_scoped_graph, _apply_vld_reextraction
    graph = _GraphStore()
    base = np.full(6, 0.3)
    adapter = build_evidence_scoped_graph(graph, [{
        "evidence_available": False, "vld_factor_vector": [0.9] * 6,
        "user_id": "fabricated", "invented_observation": True,
    }], np.full(6, 0.1))
    context = await adapter.get_security_context("ALT-VLD-001")
    assert context["user_id"] == "user-1"
    assert "invented_observation" not in context
    assert adapter.admitted_evidence == adapter.vld_factor_vectors == []
    np.testing.assert_array_equal(_apply_vld_reextraction(base, adapter), base)


@pytest.mark.asyncio
@pytest.mark.parametrize("policy_name", ["content", "majority", "random", "breadth"])
@pytest.mark.parametrize("failure", ["raise", "none"])
async def test_comparator_excludes_unavailable_read(policy_name, failure):
    from app.services.investigation_comparators import (
        ContentRulePolicy, MajorityBranchPolicy, RandomBranchPolicy, BreadthPolicy,
    )
    patterns = build_default_investigation_patterns()
    policies = {
        "content": ContentRulePolicy(patterns),
        "majority": MajorityBranchPolicy("credential_access", patterns),
        "random": RandomBranchPolicy(patterns, seed=3),
        "breadth": BreadthPolicy(patterns),
    }
    scorer = _scorer()
    surface = _centroid(scorer, "credential_access")
    provider = _FactorProvider(surface)
    graph = _GraphStore()
    query = AsyncMock(side_effect=RuntimeError("down")) if failure == "raise" else AsyncMock(return_value=None)
    with patch.object(graph, "run_query", new=query):
        result = await policies[policy_name].investigate(_alert(), scorer, provider, graph)
    assert result.degraded and not result.evidence_available
    assert result.failed_patterns
    assert result.steps == query.await_count == 1
    assert len(provider.calls) == 1
    assert result.v_final == surface.tolist()
    step = result.trace[0]
    assert step.v_before == step.v_after and step.residual == 0.0
    assert not step.evidence_admitted and not step.evidence_available
    assert step.cat_distances_before == step.cat_distances_after


@pytest.mark.asyncio
@pytest.mark.parametrize("initial", [None, [], [0.5] * 5])
async def test_invalid_initial_surface_fails_explicitly(initial):
    provider = MagicMock(compute=AsyncMock(return_value=(initial, {})))
    with pytest.raises(ValueError, match="factor_vector"):
        await _loop(_scorer(), provider).investigate(_alert(), _GraphStore())


def test_nonplanted_investigation_http_degraded_and_read_only():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.routers import triage
    from app.services.triage_providers import get_factor_vector_provider
    scorer = _scorer()
    centroids_before = np.asarray(scorer.centroids).copy()
    provider = _FactorProvider(_centroid(scorer, "credential_access"))
    graph = MagicMock(spec=["get_alert", "run_query"])
    graph.get_alert = AsyncMock(return_value=_alert())
    graph.run_query = AsyncMock(side_effect=RuntimeError("bounded read down"))
    previous = app.dependency_overrides.get(get_factor_vector_provider)
    app.dependency_overrides[get_factor_vector_provider] = lambda: provider
    try:
        with patch.object(triage, "graph_client", graph), \
             patch.object(triage, "_soc_get_security_context_for_analyze", new=AsyncMock(return_value=_alert())), \
             patch("app.services.gae_state.get_profile_scorer", return_value=scorer):
            response = TestClient(app).post("/api/soc/investigate", json={"alert_id": "ALT-VLD-001"})
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_factor_vector_provider, None)
        else:
            app.dependency_overrides[get_factor_vector_provider] = previous
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    for section in (body, body["vld"]):
        assert section["evidence_available"] is False and section["degraded"] is True
        assert section["failed_patterns"]
    assert body["investigation_trace"][0]["evidence_admitted"] is False
    assert body["vld"]["fixture_source"] == "planted"  # context origin only; not a planted algorithm
    assert body["vld"]["investigated_category"] == ""
    assert body["conservation_emit_gate"] == "not_evaluated_read_only"
    assert ": null" not in json.dumps(body)
    assert {call[0] for call in graph.method_calls} == {"get_alert", "run_query"}
    np.testing.assert_array_equal(scorer.centroids, centroids_before)
