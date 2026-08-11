import os
from unittest.mock import patch

from fastapi.testclient import TestClient


def _health_client():
    # Reset the module-level config cache so each test exercises the current
    # environment, while the health exemption itself remains unconditional.
    import app.auth.dependencies as dependencies

    dependencies._auth_config = None
    from app.main import app

    return TestClient(app)


def test_health_always_open_without_demo_mode():
    """Health must return 200 even when SOC_DEMO_MODE is disabled."""
    with patch.dict(os.environ, {"SOC_DEMO_MODE": "false"}, clear=False):
        response = _health_client().get("/health")
    assert response.status_code == 200


def test_health_always_open_with_demo_mode():
    with patch.dict(os.environ, {"SOC_DEMO_MODE": "true"}, clear=False):
        response = _health_client().get("/health")
    assert response.status_code == 200
