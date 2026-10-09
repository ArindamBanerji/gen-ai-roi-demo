"""
tests/test_write_roundtrips.py -- Response-model and write-path roundtrip tests.

15 tests covering:
  - All 9 response_model endpoints return 200 (model mismatch -> 500)
  - ProfileScorer shape (6, 4, 6)
  - SCORER_ACTIONS has 4 items, no refer_to_analyst
  - Alert queue items use 'id' field
  - Campaign category_sequence is a list
  - Decision factors endpoint returns exactly 6 factors

Run from backend/:
    pytest tests/test_write_roundtrips.py -v
"""

import sys
import os
import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from psycopg import OperationalError

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.services.triage import FactorReadUnavailable

client = TestClient(app)


# =============================================================================
# Response-model tests — each endpoint must return 200.
# A Pydantic validation failure causes FastAPI to return 500;
# these tests catch model/response mismatches early.
# =============================================================================

def test_response_model_alert_queue():
    r = client.get("/api/alerts/queue")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert "alerts" in body
    assert isinstance(body["alerts"], list)


def test_response_model_analytics():
    r = client.get("/api/soc/analytics")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
    body = r.json()
    for key in ("total_alerts", "open_alerts", "total_decisions", "correct_decisions",
                "accuracy_pct", "category_breakdown", "source", "estimated_metrics"):
        assert key in body, f"Missing key: {key}"


def test_response_model_learning_state():
    r = client.get("/api/soc/learning-state")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert "frozen" in body
    assert "iks_v2" in body
    assert "iks_components" in body


def test_response_model_profile():
    r = client.get("/api/soc/profile")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
    body = r.json()
    for key in ("categories", "actions", "centroids", "counts", "decision_count", "iks"):
        assert key in body, f"Missing key: {key}"


def test_response_model_detection_engineering():
    r = client.get("/api/soc/detection-engineering")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert "category_scores" in body
    assert "noise_map" in body
    assert isinstance(body["category_scores"], list)
    assert isinstance(body["noise_map"], list)


def test_response_model_campaigns():
    r = client.get("/api/soc/campaigns")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert "campaigns" in body
    assert "total" in body
    assert "active_campaigns" in body


def test_response_model_executive_narrative():
    r = client.get("/api/soc/executive-narrative")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
    body = r.json()
    for key in ("headline", "what_changed", "what_discovered", "what_knows",
                "metrics", "generated_at", "pdf_available"):
        assert key in body, f"Missing key: {key}"


def test_response_model_decision_factors(age_graph):
    age_graph.alert(alert_id="SIM-CA-001", alert_type="anomalous_login")
    with (
        patch("app.routers.triage.graph_client", age_graph.client),
        patch("app.services.triage.graph_client", age_graph.client),
    ):
        r = client.get("/api/triage/decision-factors/SIM-CA-001")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert "alert_id" in body
    assert "factors" in body
    assert "recommended_action" in body
    assert "confidence" in body


def test_response_model_centroid_support():
    r = client.get("/api/soc/centroid-support")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
    body = r.json()
    for key in ("support_summary", "overall_health", "warning_count",
                "threshold_sigma", "interpretation", "status", "reason",
                "support_available", "degraded"):
        assert key in body, f"Missing key: {key}"
    assert isinstance(body["warning_count"], int)
    assert isinstance(body["support_available"], bool)
    assert isinstance(body["degraded"], bool)


# =============================================================================
# Shape and invariant tests
# =============================================================================

def test_profile_scorer_shape_6_4_6():
    """ProfileScorer centroids must have shape (6, 4, 6) -- 6 categories, 4 actions, 6 factors."""
    r = client.get("/api/soc/profile")
    assert r.status_code == 200
    centroids = r.json()["centroids"]
    assert len(centroids) == 6, f"Expected 6 categories, got {len(centroids)}"
    for i, cat_row in enumerate(centroids):
        assert len(cat_row) == 4, f"Category {i}: expected 4 actions, got {len(cat_row)}"
        for j, action_row in enumerate(cat_row):
            assert len(action_row) == 6, (
                f"Category {i}, action {j}: expected 6 factors, got {len(action_row)}"
            )


def test_scorer_actions_has_4_items():
    """SCORER_ACTIONS must have exactly 4 items (escalate, investigate, suppress, monitor)."""
    from app.domains.soc.config import SCORER_ACTIONS
    assert len(SCORER_ACTIONS) == 4, (
        f"Expected 4 SCORER_ACTIONS, got {len(SCORER_ACTIONS)}: {SCORER_ACTIONS}"
    )


def test_scorer_actions_no_refer_to_analyst():
    """refer_to_analyst is a routing decision, not a ProfileScorer action."""
    from app.domains.soc.config import SCORER_ACTIONS
    assert "refer_to_analyst" not in SCORER_ACTIONS, (
        f"refer_to_analyst must not be in SCORER_ACTIONS: {SCORER_ACTIONS}"
    )


def test_alert_queue_items_use_id_field():
    """Alert queue items must have 'id' key (AGE uses alert_id; frontend expects 'id')."""
    r = client.get("/api/alerts/queue")
    assert r.status_code == 200
    alerts = r.json().get("alerts", [])
    if alerts:
        first = alerts[0]
        assert "id" in first, (
            f"Alert queue item missing 'id' field. Keys: {list(first.keys())}"
        )


def test_campaigns_category_sequence_is_list():
    """Campaign category_sequence must be a list, not a string or None."""
    r = client.get("/api/soc/campaigns")
    assert r.status_code == 200
    campaigns = r.json().get("campaigns", [])
    if campaigns:
        seq = campaigns[0].get("category_sequence")
        assert isinstance(seq, list), (
            f"category_sequence must be list, got {type(seq).__name__}: {seq!r}"
        )


def test_decision_factors_returns_6_factors(age_graph):
    """GET /triage/decision-factors must return exactly 6 factors."""
    age_graph.alert(alert_id="SIM-CA-001", alert_type="anomalous_login")
    with (
        patch("app.routers.triage.graph_client", age_graph.client),
        patch("app.services.triage.graph_client", age_graph.client),
    ):
        r = client.get("/api/triage/decision-factors/SIM-CA-001")
    assert r.status_code == 200
    factors = r.json().get("factors", [])
    assert len(factors) == 6, (
        f"Expected 6 decision factors, got {len(factors)}: "
        f"{[f['name'] for f in factors]}"
    )


@pytest.mark.parametrize("failure", [
    "none", "raises", "empty", "short", "missing_value", "nan", "inf", "malformed",
])
def test_execute_unavailable_factors_has_no_side_effects(age_graph, failure):
    from app.routers import triage

    alert_id = age_graph.alert(alert_type="anomalous_login")
    payload = {"factors": [{"name": f"factor_{i}", "value": 0.5} for i in range(6)]}
    if failure == "empty":
        payload["factors"] = []
    elif failure == "short":
        payload["factors"].pop()
    elif failure == "missing_value":
        del payload["factors"][0]["value"]
    elif failure in ("nan", "inf"):
        payload["factors"][0]["value"] = float(failure)
    provider = AsyncMock(return_value=None if failure == "none" else {} if failure == "malformed" else payload)
    if failure == "raises":
        provider.side_effect = FactorReadUnavailable("graph disconnected")
    with (
        patch.object(triage.graph_client, "get_security_context", AsyncMock(return_value={"alert_type": "anomalous_login"})),
        patch.object(triage.graph_client, "run_query", wraps=age_graph.client.run_query) as writes,
        patch.object(triage, "get_decision_factors", provider),
        patch.object(triage, "record_decision", AsyncMock()) as audit,
        patch.object(triage.event_bus, "emit", AsyncMock()) as events,
        patch.object(triage.agent, "decide") as decide,
        patch.object(triage.narrator, "generate_reasoning", AsyncMock()) as reason,
        patch.object(triage.uuid, "uuid4") as receipt,
    ):
        response = client.post("/api/action/execute", json={"alert_id": alert_id})
    assert response.status_code == 503, response.text
    assert response.json() == {"detail": "Decision factors unavailable; action was not executed."}
    provider.assert_awaited_once_with(alert_id)
    writes.assert_not_called()
    audit.assert_not_awaited()
    events.assert_not_awaited()
    decide.assert_not_called()
    reason.assert_not_awaited()
    receipt.assert_not_called()
    assert age_graph.query("MATCH (d:Decision) RETURN count(d) AS total")[0]["total"] == 0
    assert age_graph.query("MATCH (a:Alert) RETURN a.status AS status")[0]["status"] == "new"


@pytest.mark.parametrize("values", [[0.1, 0.2, 0.3, 0.4, 0.5, 0.6], [0.5] * 6])
def test_execute_preserves_measured_factors_in_age(age_graph, values):
    from app.routers import triage

    alert_id = age_graph.alert(alert_type="anomalous_login")
    payload = {"factors": [{"name": f"factor_{i}", "value": value} for i, value in enumerate(values)]}
    with (
        patch.object(triage.graph_client, "get_security_context", AsyncMock(return_value={"alert_type": "anomalous_login"})),
        patch.object(triage.graph_client, "run_query", wraps=age_graph.client.run_query),
        patch.object(triage, "get_decision_factors", AsyncMock(return_value=payload)) as provider,
        patch.object(triage, "record_decision", AsyncMock(return_value={})) as audit,
        patch.object(triage.event_bus, "emit", AsyncMock()) as events,
        patch.object(triage.narrator, "generate_reasoning", AsyncMock(return_value="Measured factors")),
    ):
        response = client.post("/api/action/execute", json={"alert_id": alert_id})
    assert response.status_code == 200, response.text
    provider.assert_awaited_once_with(alert_id)
    audit.assert_awaited_once()
    assert events.await_count == 3
    row = age_graph.query("MATCH (d:Decision) RETURN d.factor_vector AS vector, d.decision_id AS id")[0]
    assert row["vector"] == values
    assert row["id"] == response.json()["evidence"]["decision_id"]
    assert age_graph.query("MATCH (a:Alert) RETURN a.status AS status")[0]["status"] == "resolved"


@pytest.mark.parametrize("failure", ["none", "raises"])
def test_factor_get_unavailable_is_503(failure):
    from app.routers import triage

    provider = AsyncMock(return_value=None)
    if failure == "raises":
        provider.side_effect = FactorReadUnavailable("graph unavailable")
    with (
        patch.object(triage.graph_client, "get_alert", AsyncMock(return_value={"alert_id": "test"})),
        patch.object(triage, "get_decision_factors", provider),
    ):
        response = client.get("/api/triage/decision-factors/test")
    assert response.status_code == 503, response.text
    provider.assert_awaited_once()
    assert isinstance(response.json()["detail"], str)


def test_factor_get_missing_alert_still_404():
    from app.routers import triage

    with (
        patch.object(triage.graph_client, "get_alert", AsyncMock(return_value=None)),
        patch.object(triage, "get_decision_factors", AsyncMock()) as provider,
    ):
        response = client.get("/api/triage/decision-factors/absent")
    assert response.status_code == 404
    provider.assert_not_awaited()


@pytest.mark.parametrize("failure", ["none", "connection", "operational", "programming"])
def test_factor_service_classifies_graph_failure(failure):
    from app.services import triage

    query = AsyncMock(return_value=None)
    if failure == "connection":
        query.side_effect = ConnectionError("AGE disconnected")
    elif failure == "operational":
        query.side_effect = OperationalError("AGE disconnected")
    elif failure == "programming":
        query.side_effect = TypeError("query programming bug")
    with patch.object(triage.graph_client, "run_query", query):
        with pytest.raises(TypeError if failure == "programming" else FactorReadUnavailable):
            asyncio.run(triage.get_decision_factors("test"))
    assert query.await_count == 2


def test_factor_service_successful_empty_indicator_read_is_measured():
    from app.services import triage

    with patch.object(triage.graph_client, "run_query", AsyncMock(return_value=[])) as query:
        result = asyncio.run(triage.get_decision_factors("test"))
    assert query.await_count == 2
    assert len(result["factors"]) == 6
    assert result["factors"][2]["value"] == 0.0


def test_factor_get_programming_failure_stays_500():
    from app.routers import triage

    with (
        patch.object(triage.graph_client, "get_alert", AsyncMock(return_value={"alert_id": "test"})),
        patch.object(triage, "get_decision_factors", AsyncMock(side_effect=TypeError("bad code"))) as provider,
    ):
        response = client.get("/api/triage/decision-factors/test")
    assert response.status_code == 500
    provider.assert_awaited_once()


@pytest.mark.parametrize("helper", ["_build_threat_intel_factor", "_get_alert_type"])
@pytest.mark.parametrize("value", [None, {}])
def test_factor_service_rejects_unavailable_helper(helper, value):
    from app.services import triage

    # The unrelated query succeeds with no indicators; only the chosen helper fails.
    with (
        patch.object(triage.graph_client, "run_query", AsyncMock(return_value=[])),
        patch.object(triage, helper, AsyncMock(return_value=value)) as read,
    ):
        with pytest.raises(FactorReadUnavailable):
            asyncio.run(triage.get_decision_factors("test"))
    read.assert_awaited_once_with("test")


def test_execute_missing_alert_stays_404():
    from app.routers import triage

    with (
        patch.object(triage.graph_client, "get_security_context", AsyncMock(return_value=None)),
        patch.object(triage, "get_decision_factors", AsyncMock()) as factors,
        patch.object(triage.graph_client, "run_query", AsyncMock()) as writes,
    ):
        response = client.post("/api/action/execute", json={"alert_id": "absent"})
    assert response.status_code == 404
    factors.assert_not_awaited()
    writes.assert_not_awaited()
