"""Contract coverage for SOC demo-beat presentation endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


EXPECTED_ROUTES = {
    "/api/learning/control-room",
    "/api/learning/autonomy-ladder",
    "/api/learning/frozen-twin",
    "/api/context/no-precedent",
    "/api/context/what-if/{alert_id}",
    "/api/diagnostics/day-zero",
    "/api/diagnostics/frontier",
    "/api/diagnostics/centroid-timeline",
    "/api/diagnostics/accuracy-alerts",
    "/api/evolution/rule-genealogy",
    "/api/diagnostics/decision-explorer",
    "/api/evolution/rule-lifecycle",
    "/api/diagnostics/audit-trail",
}


def test_soc_demo_beat_routes_are_mounted() -> None:
    routes = {getattr(route, "path", None) for route in app.routes}
    assert EXPECTED_ROUTES <= routes


@pytest.mark.parametrize(
    "path,required_keys",
    [
        ("/api/learning/control-room", {"categories", "learning_rate", "source"}),
        ("/api/learning/autonomy-ladder", {"stages", "categories", "time_in_stage"}),
        ("/api/learning/frozen-twin", {"current_vs_frozen", "source"}),
        ("/api/context/no-precedent", {"alerts", "count", "source"}),
        ("/api/diagnostics/day-zero", {"categories", "coverage_gaps", "checklist"}),
        ("/api/diagnostics/frontier", {"safety_bar", "above", "below", "frontier"}),
    ],
)
@pytest.mark.live_backend
def test_demo_beat_returns_contract(path: str, required_keys: set[str]) -> None:
    response = TestClient(app).get(path)
    assert response.status_code == 200, response.text
    assert required_keys <= response.json().keys()


@pytest.mark.live_backend
def test_what_if_contract_for_live_alert() -> None:
    client = TestClient(app)
    candidates = client.get("/api/context/no-precedent").json()["alerts"]
    if not candidates:
        pytest.skip("No unclassified live SOC alert is available")
    response = client.get(f"/api/context/what-if/{candidates[0]['alert_id']}")
    assert response.status_code == 200, response.text
    assert {"category", "current_action", "per_factor"} <= response.json().keys()


@pytest.mark.live_backend
@pytest.mark.parametrize(
    "path,field",
    [
        ("/api/diagnostics/centroid-timeline", "timeline"),
        ("/api/diagnostics/accuracy-alerts", "trajectory"),
        ("/api/evolution/rule-genealogy", "events"),
        ("/api/diagnostics/decision-explorer", "decisions"),
        ("/api/evolution/rule-lifecycle", "lifecycle"),
        ("/api/diagnostics/audit-trail", "audit"),
    ],
)
def test_sc_demo_surface_contract(path: str, field: str) -> None:
    response = TestClient(app).get(path)
    assert response.status_code == 200, response.text
    assert field in response.json()
