import logging
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
    "/health", "/saml/", "/docs", "/openapi.json",
)

ADMIN_PREFIXES = (
    "/api/admin", "/api/framework", "/api/audit",
)


async def require_auth(request: Request) -> Optional[dict]:
    from app.auth.jwt_utils import verify_jwt
    config = get_auth_config()

    if not config.saml_enabled:
        return None

    # Normalize path to prevent traversal bypass
    from urllib.parse import unquote
    path = request.url.path
    path = unquote(path)
    # Collapse double slashes and resolve dot segments
    while "//" in path:
        path = path.replace("//", "/")
    if "/.." in path or "/../" in path:
        path = "/" + path.split("/")[-1]
    if any(path.startswith(p) for p in EXEMPT_PREFIXES):
        return None

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

    return claims
