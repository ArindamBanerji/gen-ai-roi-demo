import os
import time
import pytest
from fastapi.testclient import TestClient


# ── GROUP 1: JWT roundtrip ──

def test_jwt_create_and_verify_roundtrip():
    from app.auth.config import AuthConfig
    from app.auth.jwt_utils import create_jwt, verify_jwt
    cfg = AuthConfig(
        jwt_secret="x" * 32, jwt_algorithm="HS256",
        jwt_lifetime_hours=8)
    token = create_jwt(
        "analyst@firm.com", "analyst", ["soc-analysts"], cfg)
    claims = verify_jwt(token, cfg)
    assert claims is not None
    assert claims["sub"] == "analyst@firm.com"
    assert claims["role"] == "analyst"
    assert claims["groups"] == ["soc-analysts"]

def test_jwt_expired_rejected():
    from app.auth.config import AuthConfig
    from app.auth.jwt_utils import create_jwt, verify_jwt
    cfg = AuthConfig(
        jwt_secret="x" * 32, jwt_algorithm="HS256",
        jwt_lifetime_hours=0)
    token = create_jwt("test@test.com", "analyst", [], cfg)
    time.sleep(1)
    assert verify_jwt(token, cfg) is None

def test_jwt_wrong_secret_rejected():
    from app.auth.config import AuthConfig
    from app.auth.jwt_utils import create_jwt, verify_jwt
    cfg1 = AuthConfig(jwt_secret="a" * 32, jwt_algorithm="HS256")
    cfg2 = AuthConfig(jwt_secret="b" * 32, jwt_algorithm="HS256")
    token = create_jwt("test@test.com", "analyst", [], cfg1)
    assert verify_jwt(token, cfg2) is None


# ── GROUP 2: Role derivation ──

def test_derive_role_default_analyst():
    from app.auth.jwt_utils import derive_role
    assert derive_role([], ["admins"]) == "analyst"
    assert derive_role(["users"], ["admins"]) == "analyst"

def test_derive_role_admin_match():
    from app.auth.jwt_utils import derive_role
    assert derive_role(
        ["soc-admins"], ["soc-admins"]) == "admin"

def test_derive_role_case_insensitive():
    from app.auth.jwt_utils import derive_role
    assert derive_role(
        ["SOC-Admins"], ["soc-admins"]) == "admin"


# ── GROUP 3: Config validation ──

def test_config_valid_when_disabled():
    from app.auth.config import AuthConfig
    cfg = AuthConfig(saml_enabled=False)
    assert cfg.validate() == []

def test_config_invalid_missing_secret():
    from app.auth.config import AuthConfig
    cfg = AuthConfig(saml_enabled=True, jwt_secret="")
    errors = cfg.validate()
    assert any("SAML_JWT_SECRET" in e for e in errors)

def test_config_invalid_short_secret():
    from app.auth.config import AuthConfig
    cfg = AuthConfig(saml_enabled=True, jwt_secret="short")
    errors = cfg.validate()
    assert any("32" in e for e in errors)

def test_config_invalid_missing_idp():
    from app.auth.config import AuthConfig
    cfg = AuthConfig(
        saml_enabled=True, jwt_secret="x" * 32,
        idp_entity_id="", idp_sso_url="",
        idp_x509_cert="")
    errors = cfg.validate()
    assert len(errors) >= 3


# ── GROUP 4: Integration (TestClient) ──

@pytest.fixture
def app_client():
    """TestClient with SAML disabled (default)."""
    os.environ.pop("SAML_ENABLED", None)
    import app.auth.dependencies as dep
    dep._auth_config = None
    from app.main import app
    return TestClient(app)

def test_disabled_health_open(app_client):
    r = app_client.get("/health")
    assert r.status_code == 200

def test_disabled_api_open(app_client):
    r = app_client.get("/api/soc/learning-state")
    assert r.status_code == 200

def test_saml_status_endpoint(app_client):
    r = app_client.get("/saml/status")
    assert r.status_code == 200
    data = r.json()
    assert "saml_enabled" in data
    assert data["saml_enabled"] is False

def test_saml_metadata_returns_xml(app_client):
    r = app_client.get("/saml/metadata")
    assert r.status_code == 200
    assert "EntityDescriptor" in r.text

def test_saml_logout_redirects(app_client):
    r = app_client.get("/saml/logout",
                        follow_redirects=False)
    assert r.status_code == 302

def test_saml_status_no_secrets(app_client):
    """Status endpoint must NOT expose secrets."""
    r = app_client.get("/saml/status")
    data = r.json()
    assert "jwt_secret" not in str(data).lower()
    assert "x509" not in str(data).lower()
    assert "cert" not in str(data).lower()
