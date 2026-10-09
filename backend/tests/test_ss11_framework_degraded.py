from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.routers import cohort_status_router, framework_router, soc
from app.routers.framework_router import intervention_history, intervention_state


class BrokenGraph:
    async def run_query(self, *args, **kwargs):
        raise RuntimeError("AGE unavailable")


@pytest.mark.asyncio
async def test_checkpoint_list_graph_failure() -> None:
    with patch.object(framework_router, "graph_client", BrokenGraph()):
        payload = await framework_router.checkpoint_list()

    assert payload["checkpoints"] == []
    assert payload["checkpoints_available"] is False


@pytest.mark.asyncio
async def test_intervention_state_graph_failure() -> None:
    gate = SimpleNamespace(
        AUTO_APPROVE_DISABLED=False,
        CATEGORY_CONFIDENCE_THRESHOLDS={},
        FROZEN_CATEGORIES=set(),
        FORCE_REVIEW_CATEGORIES=set(),
    )
    ctrl = SimpleNamespace(
        db=BrokenGraph(),
        scorer=SimpleNamespace(frozen=False),
        gate=gate,
        get_current_state=None,
    )
    from app.framework.intervention_controls import InterventionControls

    real_ctrl = InterventionControls(ctrl.db, ctrl.scorer, None, gate)
    with patch.object(framework_router, "_get_intervention_controls", return_value=real_ctrl):
        payload = await intervention_state()

    assert payload["last_intervention"] is None
    assert payload["state_available"] is False
    assert isinstance(payload["thresholds"], dict)


@pytest.mark.asyncio
async def test_intervention_history_graph_failure() -> None:
    gate = SimpleNamespace(
        AUTO_APPROVE_DISABLED=False,
        CATEGORY_CONFIDENCE_THRESHOLDS={},
        FROZEN_CATEGORIES=set(),
        FORCE_REVIEW_CATEGORIES=set(),
    )
    from app.framework.intervention_controls import InterventionControls

    ctrl = InterventionControls(BrokenGraph(), SimpleNamespace(frozen=False), None, gate)
    with patch.object(framework_router, "_get_intervention_controls", return_value=ctrl):
        payload = await intervention_history()

    assert payload["interventions"] == []
    assert payload["count"] == 0
    assert payload["history_available"] is False


@pytest.mark.asyncio
async def test_provenance_graph_failure() -> None:
    with patch.object(soc, "graph_client", BrokenGraph()):
        payload = await soc.get_decision_provenance("DEC-SS11")

    assert payload["decision_id"] == "DEC-SS11"
    assert payload["factors"] == []
    assert payload["total_nodes_consulted"] == 0
    assert payload["provenance_available"] is False


@pytest.mark.asyncio
async def test_shadow_report_graph_failure() -> None:
    with patch.object(framework_router, "graph_client", BrokenGraph()):
        payload = await framework_router.shadow_report()

    assert payload["total_shadow_decisions"] == 0
    assert payload["by_category"] == {}
    assert payload["report_available"] is False


@pytest.mark.asyncio
async def test_similar_cases_graph_failure() -> None:
    async def run_query(query, params=None):
        if "MATCH (d:Decision {decision_id:" in query:
            return [{
                "factor_vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
                "category": "credential_access",
                "action": "investigate",
                "confidence": 0.8,
                "timestamp": 1,
                "source_location": "",
                "source_ip": "",
                "destination_ip": "",
                "alert_description": "",
                "alert_type": "credential_access",
                "severity": "medium",
                "user_name": "user",
                "user_title": "analyst",
                "user_department": "security",
                "asset_hostname": "host",
                "asset_criticality_str": "medium",
                "asset_business_unit": "security",
            }]
        if "RETURN count(d) AS cnt" in query:
            return []
        raise RuntimeError("AGE unavailable")

    with patch.object(soc, "graph_client", SimpleNamespace(run_query=run_query)):
        payload = await soc.explain_decision("DEC-SS11")

    assert payload["similar_cases"] == []
    assert payload["similar_cases_available"] is False
    assert payload["degraded"] is True


@pytest.mark.asyncio
async def test_cohort_decisions_graph_failure() -> None:
    with patch.object(cohort_status_router, "graph_client", BrokenGraph()):
        payload = await cohort_status_router.get_campaign_cohort_status()

    assert payload["decisions_available"] is False
    assert payload["degraded"] is True
    assert payload["real"]["treatment_n"] == 0
    assert payload["real"]["control_n"] == 0
