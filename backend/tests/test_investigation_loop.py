"""SOC VLD investigation loop tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

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
    }
    assert len(step["v_before"]) == 6
    assert len(step["v_after"]) == 6
    assert set(step["cat_distances_before"]) == set(SOC_CATEGORIES)


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
        graph_query="MATCH (a:Alert {alert_id: {alert_id}})-[:INVOLVES]->(u:User) RETURN u.user_id AS user_id LIMIT 1",
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
