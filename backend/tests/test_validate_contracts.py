"""Self-tests for dynamic contract fixture resolution."""

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parents[2]))

from scripts import validate_contracts  # noqa: E402


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


class _ReadTimeoutStream(httpx.SyncByteStream):
    """Yield an optional partial body before simulating a body-read timeout."""

    def __init__(self, partial: bytes = b"") -> None:
        self.partial = partial

    def __iter__(self):  # type: ignore[no-untyped-def]
        if self.partial:
            yield self.partial
        raise httpx.ReadTimeout("simulated body-read timeout")


def test_resolved_path_uses_alert_id_from_queue() -> None:
    validate_contracts._cached_alert_ids.clear()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/alerts/queue"
        return httpx.Response(200, json={"alerts": [{"id": "ALERT-LIVE-42"}]})

    with _client(handler) as client:
        path, body, query = validate_contracts._resolve_contract_placeholders(
            "http://test",
            "/api/triage/decision-factors/__FROM_QUEUE__",
            {"alert_id": "__FROM_QUEUE__"},
            {"alert_id": "__FROM_QUEUE__"},
            client,
        )

    assert path.endswith("/ALERT-LIVE-42")
    assert body == {"alert_id": "ALERT-LIVE-42"}
    assert query == {"alert_id": "ALERT-LIVE-42"}


def test_placeholder_in_path_is_resolved_before_request() -> None:
    validate_contracts._cached_alert_ids.clear()
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.url.path == "/api/alerts/queue":
            return httpx.Response(200, json={"alerts": [{"alert_id": "ALERT-REAL-7"}]})
        assert request.url.path == "/api/triage/decision-factors/ALERT-REAL-7"
        return httpx.Response(200, json={"alert_id": "ALERT-REAL-7", "factors": []})

    endpoint = {
        "path": "/api/triage/decision-factors/__FROM_QUEUE__",
        "method": "GET",
        "required_fields": ["alert_id", "factors"],
    }
    with _client(handler) as client:
        result = validate_contracts.validate_endpoint(
            "http://test", endpoint, verbose=False, client=client
        )

    assert result["pass"] is True
    assert result["resolved_path"].endswith("/ALERT-REAL-7")
    assert requested_paths == [
        "/api/alerts/queue",
        "/api/triage/decision-factors/ALERT-REAL-7",
    ]


def test_missing_queue_data_reports_error_without_fallback() -> None:
    validate_contracts._cached_alert_ids.clear()
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(200, json={"alerts": []})

    endpoint = {
        "path": "/api/triage/decision-factors/__FROM_QUEUE__",
        "method": "GET",
        "required_fields": ["alert_id", "factors"],
    }
    with _client(handler) as client:
        result = validate_contracts.validate_endpoint(
            "http://test", endpoint, verbose=False, client=client
        )

    assert result["pass"] is False
    assert result["error"] == "fixture resolution failed: queue contains no alerts"
    assert requested_paths == ["/api/alerts/queue"]


def test_connect_timeout_produces_diagnostic_without_retry() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectTimeout("simulated connect timeout", request=request)

    endpoint = {
        "name": "connect-timeout",
        "method": "GET",
        "path": "/api/connect-timeout",
        "required_fields": [],
    }
    with _client(handler) as client:
        result = validate_contracts.validate_endpoint(
            "http://test", endpoint, verbose=False, client=client
        )

    assert result["pass"] is False
    assert result["path"] == "/api/connect-timeout"
    assert "Connect timeout" in result["error"]
    assert result["attempts"][0]["phase"] == "connect"
    assert calls == 1


def test_read_timeout_produces_diagnostic() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("simulated header timeout", request=request)

    endpoint = {
        "name": "read-timeout",
        "method": "GET",
        "path": "/api/read-timeout",
        "required_fields": [],
    }
    with _client(handler) as client:
        result = validate_contracts.validate_endpoint(
            "http://test", endpoint, verbose=False, client=client
        )

    assert result["pass"] is False
    assert result["path"] == "/api/read-timeout"
    assert "Header timeout" in result["error"]
    assert result["attempts"][0]["phase"] == "header"
    assert calls == 1


def test_get_body_read_retry_succeeds() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                200,
                headers={"content-length": "24"},
                stream=_ReadTimeoutStream(b'{"ok":'),
                request=request,
            )
        return httpx.Response(200, json={"ok": True}, request=request)

    endpoint = {
        "name": "get-body-retry",
        "method": "GET",
        "path": "/api/get-body-retry",
        "required_fields": ["ok"],
    }
    with _client(handler) as client:
        result = validate_contracts.validate_endpoint(
            "http://test", endpoint, verbose=False, client=client
        )

    assert result["pass"] is True
    assert calls == 2
    assert len(result["attempts"]) == 2
    assert result["attempts"][0]["phase"] == "body-read"
    assert result["attempts"][0]["bytes_received"] == len(b'{"ok":')
    assert result["attempts"][1]["phase"] == "complete"


def test_post_no_retry_on_body_read_failure() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            headers={"content-length": "30"},
            stream=_ReadTimeoutStream(b"partial"),
            request=request,
        )

    endpoint = {
        "name": "post-no-retry",
        "method": "POST",
        "path": "/api/post-no-retry",
        "body": {"value": 1},
        "required_fields": [],
    }
    with _client(handler) as client:
        result = validate_contracts.validate_endpoint(
            "http://test", endpoint, verbose=False, client=client
        )

    assert result["pass"] is False
    assert result["attempts"][0]["phase"] == "body-read"
    assert len(result["attempts"]) == 1
    assert calls == 1


def test_contract_timeout_override_is_passed_to_httpx() -> None:
    observed_read_timeouts: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        timeout = request.extensions["timeout"]
        observed_read_timeouts.append(float(timeout["read"]))
        return httpx.Response(200, json={"ok": True}, request=request)

    endpoint = {
        "name": "custom-timeout",
        "method": "GET",
        "path": "/api/custom-timeout",
        "timeout_seconds": 42,
        "required_fields": ["ok"],
    }
    with _client(handler) as client:
        result = validate_contracts.validate_endpoint(
            "http://test", endpoint, verbose=False, client=client
        )

    assert result["pass"] is True
    assert observed_read_timeouts == [42.0]
