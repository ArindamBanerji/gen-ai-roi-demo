"""
SAML auth extended tests -- P1 batch.

Groups:
  1 -- JWT edge cases (7 tests)
  2 -- derive_role edge cases (4 tests)
  3 -- Auth dependency with SAML enabled (7 tests)
  4 -- SAML router tests (4 tests)

Total: 22 tests.
"""
import os
import time
import jwt
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(secret="x" * 32, lifetime_hours=8):
    from app.auth.config import AuthConfig
    return AuthConfig(
        jwt_secret=secret,
        jwt_algorithm="HS256",
        jwt_lifetime_hours=lifetime_hours,
    )


def _make_jwt(role="analyst", email="test@test.com",
              secret="x" * 32, lifetime_hours=8):
    from app.auth.jwt_utils import create_jwt
    cfg = _make_config(secret=secret, lifetime_hours=lifetime_hours)
    groups = ["soc-admins"] if role == "admin" else ["soc-analysts"]
    return create_jwt(email, role, groups, cfg)


# ---------------------------------------------------------------------------
# GROUP 1 — JWT edge cases
# ---------------------------------------------------------------------------

def test_jwt_none_email_verify_returns_none():
    """Token with None sub: verify_jwt returns None (not payload.get('sub') is True)."""
    from app.auth.jwt_utils import create_jwt, verify_jwt
    cfg = _make_config()
    token = create_jwt(None, "analyst", [], cfg)
    assert verify_jwt(token, cfg) is None


def test_jwt_empty_email_verify_returns_none():
    """Token with empty-string sub: verify_jwt returns None."""
    from app.auth.jwt_utils import create_jwt, verify_jwt
    cfg = _make_config()
    token = create_jwt("", "analyst", [], cfg)
    assert verify_jwt(token, cfg) is None


def test_jwt_negative_lifetime_is_expired():
    """Negative lifetime produces an immediately-expired token."""
    from app.auth.jwt_utils import create_jwt, verify_jwt
    cfg = _make_config(lifetime_hours=-1)
    token = create_jwt("user@test.com", "analyst", [], cfg)
    assert verify_jwt(token, cfg) is None


def test_jwt_empty_string_token_returns_none():
    """Empty string is not a valid JWT."""
    from app.auth.jwt_utils import verify_jwt
    cfg = _make_config()
    assert verify_jwt("", cfg) is None


def test_jwt_malformed_token_returns_none():
    """Garbage string token returns None."""
    from app.auth.jwt_utils import verify_jwt
    cfg = _make_config()
    assert verify_jwt("not.a.valid.jwt.token", cfg) is None


def test_jwt_missing_sub_claim_returns_none():
    """Token with role but no sub field returns None."""
    from app.auth.jwt_utils import verify_jwt
    cfg = _make_config()
    payload = {
        "role": "analyst",
        "groups": [],
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    token = jwt.encode(payload, "x" * 32, algorithm="HS256")
    assert verify_jwt(token, cfg) is None


def test_jwt_missing_role_claim_returns_none():
    """Token with sub but no role field returns None."""
    from app.auth.jwt_utils import verify_jwt
    cfg = _make_config()
    payload = {
        "sub": "user@test.com",
        "groups": [],
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    token = jwt.encode(payload, "x" * 32, algorithm="HS256")
    assert verify_jwt(token, cfg) is None


# ---------------------------------------------------------------------------
# GROUP 2 — derive_role edge cases
# ---------------------------------------------------------------------------

def test_derive_role_none_groups_is_analyst():
    """None groups is falsy -> default analyst."""
    from app.auth.jwt_utils import derive_role
    assert derive_role(None, ["soc-admins"]) == "analyst"


def test_derive_role_empty_admin_groups_is_analyst():
    """Empty admin_groups list -> no match possible -> analyst."""
    from app.auth.jwt_utils import derive_role
    assert derive_role(["soc-admins"], []) == "analyst"


def test_derive_role_non_string_values_skipped():
    """Non-string items in groups are skipped; no valid match -> analyst."""
    from app.auth.jwt_utils import derive_role
    assert derive_role([1, None, 42, True], ["soc-admins"]) == "analyst"


def test_derive_role_whitespace_group_not_matched():
    """Whitespace-padded group name does not match exact admin group -> analyst."""
    from app.auth.jwt_utils import derive_role
    # "  soc-admins  ".lower() != "soc-admins" — no strip applied
    assert derive_role(["  soc-admins  "], ["soc-admins"]) == "analyst"


# ---------------------------------------------------------------------------
# GROUP 3 — Auth dependency with SAML enabled
# ---------------------------------------------------------------------------

@pytest.fixture
def saml_enabled_client():
    """TestClient with SAML enabled and a valid JWT secret."""
    os.environ["SAML_ENABLED"] = "true"
    os.environ["SAML_JWT_SECRET"] = "x" * 32
    import app.auth.dependencies as dep
    dep._auth_config = None
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    os.environ.pop("SAML_ENABLED", None)
    os.environ.pop("SAML_JWT_SECRET", None)
    dep._auth_config = None


def test_saml_enabled_no_cookie_returns_401(saml_enabled_client):
    """Non-exempt path with no cookie -> 401."""
    r = saml_enabled_client.get("/api/soc/epistemic-state")
    assert r.status_code == 401


def test_saml_enabled_bad_cookie_returns_401(saml_enabled_client):
    """Malformed JWT cookie -> 401."""
    r = saml_enabled_client.get(
        "/api/soc/epistemic-state",
        cookies={"soc_auth_token": "garbage.token.value"},
    )
    assert r.status_code == 401


def test_saml_enabled_valid_analyst_passes_auth(saml_enabled_client):
    """Valid analyst JWT in cookie -- auth passes (not 401 or 403)."""
    token = _make_jwt("analyst")
    r = saml_enabled_client.get(
        "/api/soc/epistemic-state",
        cookies={"soc_auth_token": token},
    )
    assert r.status_code not in (401, 403)


def test_saml_enabled_health_is_exempt(saml_enabled_client):
    """/health is in EXEMPT_PREFIXES -- no cookie required."""
    r = saml_enabled_client.get("/health")
    assert r.status_code == 200


def test_saml_enabled_saml_prefix_is_exempt(saml_enabled_client):
    """/saml/* is exempt -- status endpoint accessible without cookie."""
    r = saml_enabled_client.get("/saml/status")
    assert r.status_code == 200


def test_saml_enabled_admin_path_denies_analyst(saml_enabled_client):
    """Analyst JWT on /api/audit/* (ADMIN_PREFIXES) -> 403."""
    token = _make_jwt("analyst")
    r = saml_enabled_client.get(
        "/api/audit/chain",
        cookies={"soc_auth_token": token},
    )
    assert r.status_code == 403


def test_saml_enabled_admin_path_allows_admin_jwt(saml_enabled_client):
    """Admin JWT on /api/audit/* -- middleware allows through (status != 403)."""
    token = _make_jwt("admin")
    r = saml_enabled_client.get(
        "/api/audit/chain",
        cookies={"soc_auth_token": token},
    )
    assert r.status_code != 403


# ---------------------------------------------------------------------------
# GROUP 4 — SAML router tests
# ---------------------------------------------------------------------------

@pytest.fixture
def app_client():
    """TestClient with SAML disabled (default env)."""
    os.environ.pop("SAML_ENABLED", None)
    import app.auth.dependencies as dep
    dep._auth_config = None
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


def test_saml_login_503_when_idp_not_configured(app_client):
    """GET /saml/login -> 503 when IdP credentials are absent."""
    r = app_client.get("/saml/login", follow_redirects=False)
    assert r.status_code == 503


def test_saml_acs_400_when_saml_response_missing(app_client):
    """POST /saml/acs with no SAMLResponse form field -> 400."""
    r = app_client.post("/saml/acs", data={})
    assert r.status_code == 400


def test_saml_logout_deletes_auth_cookie(app_client):
    """GET /saml/logout -> 302 redirect and deletes soc_auth_token cookie."""
    r = app_client.get("/saml/logout", follow_redirects=False)
    assert r.status_code == 302
    set_cookie = r.headers.get("set-cookie", "")
    assert "soc_auth_token" in set_cookie


def test_saml_status_has_required_keys(app_client):
    """GET /saml/status -> JSON with all required schema keys, no secrets."""
    r = app_client.get("/saml/status")
    assert r.status_code == 200
    data = r.json()
    for key in ("saml_enabled", "idp_configured", "sp_entity_id", "sp_acs_url"):
        assert key in data
    # Must not expose any secrets
    serialized = str(data).lower()
    assert "jwt_secret" not in serialized
    assert "x509" not in serialized
    assert "cert" not in serialized
