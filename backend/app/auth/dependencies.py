import logging
import os
from typing import Optional
from fastapi import Request, HTTPException

log = logging.getLogger(__name__)

_auth_config = None


def get_auth_config():
    global _auth_config
    if _auth_config is None:
        from app.auth.config import load_auth_config
        _auth_config = load_auth_config()
    return _auth_config


EXEMPT_PREFIXES = (
    "/health", "/saml/", "/docs", "/openapi.json", "/redoc",
)

ADMIN_PREFIXES = (
    "/api/admin", "/api/framework", "/api/audit",
)

MUTATION_PATHS = (
    "/api/soc/checkpoint/rollback",
    "/api/soc/scorer/freeze",
    "/api/soc/scorer/unfreeze",
    "/api/soc/interventions/rollback",
    "/api/soc/interventions/threshold",
    "/api/soc/reset",
    "/api/admin/reset",
)


async def require_auth(request: Request) -> Optional[dict]:
    from app.auth.jwt_utils import verify_jwt
    config = get_auth_config()

    # Infrastructure and API-discovery endpoints must remain reachable for
    # load balancers, demo.py health waits, and monitoring even when auth is
    # fail-closed for application routes.
    path = request.url.path if request is not None else ""
    if any(path.startswith(prefix) for prefix in EXEMPT_PREFIXES):
        return None

    if not config.saml_enabled:
        if os.environ.get("SOC_DEMO_MODE", "false").lower() == "true":
            return None
        raise HTTPException(
            status_code=403,
            detail=(
                "Authentication required. Set SOC_DEMO_MODE=true "
                "only for an explicit local demo."
            ),
        )

    # Normalize path to prevent traversal bypass for authenticated routes.
    from urllib.parse import unquote
    path = unquote(path)
    # Collapse double slashes and resolve dot segments
    while "//" in path:
        path = path.replace("//", "/")
    if "/.." in path or "/../" in path:
        path = "/" + path.split("/")[-1]
    token = request.cookies.get("soc_auth_token")
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required")

    claims = verify_jwt(token, config)
    if claims is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token")

    if any(path == p or path.startswith(p + "/") for p in ADMIN_PREFIXES):
        if claims.get("role") != "admin":
            raise HTTPException(
                status_code=403,
                detail="Admin access required")

    if any(path == p or path.startswith(p + "/") for p in MUTATION_PATHS):
        if claims.get("role") != "admin":
            raise HTTPException(
                status_code=403,
                detail="Admin access required for mutation")

    return claims
