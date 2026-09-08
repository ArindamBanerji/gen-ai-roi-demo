"""SOC VLD investigation loop tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from app.domains.soc.config import SOC_CATEGORIES, SOCDomainConfig
from app.services.investigation_loop import InvestigationLoop
from app.services.investigation_patterns import build_default_investigation_patterns
from app.services.investigation_router import InvestigationRouter


class _GraphStore:
    async def get_security_context(self, alert_id: str) -> dict[str, Any]:
        return {
            "alert_id": alert_id,
            "user_id": "user-1",
            "asset_id": "asset-1",
            "pattern_id": "PAT-CRED-001",
            "nodes_consulted": 3,
            "origin": "zero_day_synthetic",
        }


class _FactorProvider:
    def __init__(self, initial: np.ndarray, after: dict[str, np.ndarray] | None = None) -> None:
        self.initial = np.asarray(initial, dtype=np.float64)
        self.after = {key: np.asarray(value, dtype=np.float64) for key, value in (after or {}).items()}
        self.calls: list[dict[str, Any]] = []

    async def compute(self, alert: dict[str, Any], context: Any) -> tuple[np.ndarray, dict[str, dict[str, Any]]]:
        self.calls.append({"alert": dict(alert), "context": context})
        if isinstance(context, dict):
            category = str(context.get("investigation_category") or "")
            if category in self.after:
                return self.after[category].copy(), {"test": {"source": category}}
        return self.initial.copy(), {"test": {"source": "initial"}}


def _scorer():
    return SOCDomainConfig().build_profile_scorer()


def _centroid(scorer: Any, category: str, action_index: int = 0) -> np.ndarray:
    value: np.ndarray = np.asarray(scorer.centroids[SOC_CATEGORIES.index(category), action_index, :], dtype=np.float64)
    return value


def _loop(
    scorer: Any,
    provider: _FactorProvider,
    *,
    L_max: int = 3,
    residual_threshold: float = 1.0e-3,
) -> InvestigationLoop:
    router = InvestigationRouter(build_default_investigation_patterns(), L_max=L_max)
    return InvestigationLoop(
        scorer,
        router,
        provider,
        L_max=L_max,
        eps=1.0,
        residual_threshold=residual_threshold,
    )


def _alert(category: str = "credential_access") -> dict[str, Any]:
    return {
        "alert_id": "ALT-VLD-001",
        "alert_type": category,
        "category": category,
        "origin": "zero_day_synthetic",
    }


@pytest.mark.asyncio
async def test_single_step_investigation_dispatches_pattern_and_logs_trace() -> None:
    scorer = _scorer()
    provider = _FactorProvider(_centroid(scorer, "credential_access"))

    result = await _loop(scorer, provider, L_max=1).investigate(_alert(), _GraphStore())

    assert result.steps == 1
    assert result.trace[0].pattern == "credential_access"
    assert result.trace[0].selected_edge == "INVOLVES"
    assert "investigation_pattern" in result.trace[0].evidence_keys
    assert result.trace[0].cat_distances_before["credential_access"] >= 0.0


@pytest.mark.asyncio
async def test_multi_step_investigation_pivots_when_centroid_geometry_changes() -> None:
    scorer = _scorer()
    provider = _FactorProvider(
        _centroid(scorer, "credential_access"),
        after={
            "credential_access": _centroid(scorer, "malware_execution"),
            "malware_execution": _centroid(scorer, "malware_execution"),
        },
    )

    result = await _loop(scorer, provider, L_max=2).investigate(_alert(), _GraphStore())

    assert [step.pattern for step in result.trace] == ["credential_access", "malware_execution"]
    assert result.category == "malware_execution"


@pytest.mark.asyncio
async def test_budget_exhaustion_halts_at_l_max() -> None:
    scorer = _scorer()
    provider = _FactorProvider(
        _centroid(scorer, "credential_access"),
        after={"credential_access": _centroid(scorer, "malware_execution")},
    )

    result = await _loop(scorer, provider, L_max=1).investigate(_alert(), _GraphStore())

    assert result.steps == 1
    assert result.trace[-1].halt_reason == "budget_exhausted"


@pytest.mark.asyncio
async def test_residual_halt_stops_when_vector_is_stable() -> None:
    scorer = _scorer()
    stable = _centroid(scorer, "credential_access")
    provider = _FactorProvider(stable, after={"credential_access": stable})

    result = await _loop(scorer, provider, L_max=3).investigate(_alert(), _GraphStore())

    assert result.steps == 1
    assert result.trace[-1].residual == 0.0
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


@pytest.mark.asyncio
async def test_investigation_trace_has_required_shape_and_fields() -> None:
    scorer = _scorer()
    provider = _FactorProvider(_centroid(scorer, "credential_access"))

    result = await _loop(scorer, provider, L_max=1).investigate(_alert(), _GraphStore())
    step = result.to_dict()["trace"][0]

    assert set(step) == {
        "step",
        "pattern",
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
    provider = _FactorProvider(
        _centroid(scorer, "credential_access"),
        after={"credential_access": _centroid(scorer, "malware_execution")},
    )

    await _loop(scorer, provider, L_max=2).investigate(_alert(), _GraphStore())

    np.testing.assert_allclose(np.asarray(scorer.centroids), before)


@pytest.mark.asyncio
async def test_single_pass_and_vld_results_are_returned_together() -> None:
    scorer = _scorer()
    provider = _FactorProvider(_centroid(scorer, "credential_access"))

    result = await _loop(scorer, provider, L_max=1).investigate(_alert(), _GraphStore())
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

    result = await _loop(scorer, provider, L_max=1).investigate(
        {**alert, "category": category},
        _GraphStore(),
    )

    assert result.steps == 1
    assert result.fixture_source == "planted"
    assert result.trace[0].cost >= 1.0
