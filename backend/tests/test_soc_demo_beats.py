"""Contract coverage for SOC demo-beat presentation endpoints."""

# FLAKY-FIX EVALUATION (Sep 2026)
# Approach A: session-scoped health polling waits before live_backend tests;
#   test-side only and portable to SDK copilots. This is the primary defense.
# Approach B: lifespan-driven middleware returns 503 + Retry-After during
#   hydration, protecting all clients. Ready requests use a boolean fast path.
# Both are active. Health polling is primary; middleware is defense-in-depth.

from __future__ import annotations

import time

import pytest
import httpx
from conftest import _backend_is_ready, _backend_url

from app.main import app


class _Retry503Transport(httpx.HTTPTransport):
    """Retry transient live-stack unavailability without hiding persistent errors."""

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        deadline = time.monotonic() + 30.0
        while True:
            response = super().handle_request(request)
            if response.status_code != 503 or time.monotonic() >= deadline:
                return response
            response.close()
            time.sleep(min(0.5, max(0.0, deadline - time.monotonic())))


@pytest.fixture(scope="module")
def live_client():
    """Use the separately started SOC process for live graph contracts."""
    with httpx.Client(
        base_url=_backend_url(),
        timeout=30.0,
        transport=_Retry503Transport(),
    ) as client:
        yield client


@pytest.mark.live_backend
def test_backend_ready_check_returns_bool() -> None:
    assert _backend_is_ready() is True


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
def test_demo_beat_returns_contract(
    path: str, required_keys: set[str], live_client: httpx.Client
) -> None:
    response = live_client.get(path)
    assert response.status_code == 200, response.text
    assert required_keys <= response.json().keys()


@pytest.mark.live_backend
def test_what_if_contract_for_live_alert(live_client: httpx.Client) -> None:
    candidates = live_client.get("/api/context/no-precedent").json()["alerts"]
    if not candidates:
        pytest.skip("No unclassified live SOC alert is available")
    response = live_client.get(f"/api/context/what-if/{candidates[0]['alert_id']}")
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
def test_sc_demo_surface_contract(
    path: str, field: str, live_client: httpx.Client
) -> None:
    response = live_client.get(path)
    assert response.status_code == 200, response.text
    assert field in response.json()
