import os
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

import app.middleware.pii_redaction as pii_redaction
import app.services.pii_redaction as pii_service
from app.middleware.pii_redaction import (
    PIIRedactionMiddleware,
    _is_enabled,
    _should_skip,
)
from app.services.pii_redaction import redact_payload
from ci_platform.redaction.pii_redactor import PIIRedactor


def _client() -> TestClient:
    app = FastAPI()
    app.add_middleware(PIIRedactionMiddleware)

    @app.get("/api/test/json")
    async def json_response():
        return redact_payload({
            "alert_id": "ALERT-001",
            "message": "Contact john.doe@customer.com from 10.0.1.54",
            "nested": {"email": "analyst@firm.com"},
        }, "/api/test/json")

    @app.get("/api/test/plain")
    async def plain_response():
        return PlainTextResponse("Email john.doe@customer.com")

    @app.get("/health")
    async def health_response():
        return {"email": "health@firm.com", "status": "healthy"}

    @app.get("/api/admin/test")
    async def admin_response():
        return {"email": "admin@firm.com", "status": "ok"}

    return TestClient(app, raise_server_exceptions=False)


def setup_function():
    pii_service._redactor = None


def teardown_function():
    pii_service._redactor = None
    os.environ.pop("PII_REDACTION_ENABLED", None)


def test_is_enabled_default_false():
    os.environ.pop("PII_REDACTION_ENABLED", None)

    assert _is_enabled() is False


def test_is_enabled_true_values():
    for value in ("true", "1", "yes", " TRUE "):
        with patch.dict(os.environ, {"PII_REDACTION_ENABLED": value}, clear=False):
            assert _is_enabled() is True


def test_should_skip_exempt_paths():
    assert _should_skip("/health")
    assert _should_skip("/docs")
    assert _should_skip("/openapi.json")
    assert _should_skip("/redoc")
    assert _should_skip("/api/admin")
    assert _should_skip("/api/admin/users")
    assert not _should_skip("/api/test/json")


def test_redact_dict_integration_alert_like_data():
    data = {
        "alert_id": "ALERT-001",
        "category": "credential_access",
        "user_email": "john.doe@customer.com",
        "source_ip": "10.0.1.54",
        "narrative": "Email john.doe@customer.com from 10.0.1.54",
    }

    redacted, report = PIIRedactor().redact_dict(data)

    assert redacted["alert_id"] == "ALERT-001"
    assert redacted["category"] == "credential_access"
    redacted_text = str(redacted)
    assert "john.doe@customer.com" not in redacted_text
    assert "10.0.1.54" not in redacted_text
    assert report.total_redactions >= 4


def test_redact_preserves_nested_structure():
    data = {
        "alerts": [
            {"email": "a@firm.com", "phones": ["415-555-1212"]},
            {"email": "b@firm.com", "ip": "10.0.1.54"},
        ],
        "metadata": {"owner": "owner@firm.com"},
    }

    redacted, report = PIIRedactor().redact_dict(data)

    assert list(redacted.keys()) == ["alerts", "metadata"]
    assert len(redacted["alerts"]) == 2
    assert "phones" in redacted["alerts"][0]
    redacted_text = str(redacted)
    assert "a@firm.com" not in redacted_text
    assert "b@firm.com" not in redacted_text
    assert "owner@firm.com" not in redacted_text
    assert "10.0.1.54" not in redacted_text
    assert report.total_redactions >= 4


def test_middleware_enabled_redacts_json_response():
    with patch.dict(os.environ, {"PII_REDACTION_ENABLED": "true"}, clear=False):
        response = _client().get("/api/test/json")

    assert response.status_code == 200
    assert "john.doe@customer.com" not in response.text
    assert "10.0.1.54" not in response.text
    assert response.json()["alert_id"] == "ALERT-001"
    if "content-length" in response.headers:
        assert int(response.headers["content-length"]) == len(response.content)


def test_middleware_disabled_leaves_json_unredacted():
    with patch.dict(os.environ, {"PII_REDACTION_ENABLED": "false"}, clear=False):
        response = _client().get("/api/test/json")

    assert response.status_code == 200
    assert "john.doe@customer.com" in response.text
    assert "10.0.1.54" in response.text


def test_middleware_fail_open_returns_original_response():
    class BrokenRedactor:
        def redact_dict(self, data):
            raise RuntimeError("boom")

    with patch.dict(os.environ, {"PII_REDACTION_ENABLED": "true"}, clear=False):
        with patch("app.services.pii_redaction._get_redactor", return_value=BrokenRedactor()):
            response = _client().get("/api/test/json")

    assert response.status_code == 200
    assert "john.doe@customer.com" in response.text
    assert "10.0.1.54" in response.text
    if "content-length" in response.headers:
        assert int(response.headers["content-length"]) == len(response.content)


def test_exempt_path_skips_redaction():
    with patch.dict(os.environ, {"PII_REDACTION_ENABLED": "true"}, clear=False):
        health = _client().get("/health")
        admin = _client().get("/api/admin/test")

    assert health.status_code == 200
    assert "health@firm.com" in health.text
    assert admin.status_code == 200
    assert "admin@firm.com" in admin.text


def test_non_json_response_skipped():
    with patch.dict(os.environ, {"PII_REDACTION_ENABLED": "true"}, clear=False):
        response = _client().get("/api/test/plain")

    assert response.status_code == 200
    assert "john.doe@customer.com" in response.text
    assert "application/json" not in response.headers.get("content-type", "")


def test_main_health_and_openapi_still_work_with_redaction_enabled():
    with patch.dict(os.environ, {"PII_REDACTION_ENABLED": "true"}, clear=False):
        from app.main import app

        client = TestClient(app, raise_server_exceptions=False)
        health = client.get("/health")
        openapi = client.get("/openapi.json")

    assert health.status_code == 200
    assert openapi.status_code == 200
