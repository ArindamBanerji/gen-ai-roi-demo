import jwt
import time
import logging
from typing import Optional, List

log = logging.getLogger(__name__)


def create_jwt(user_email: str, role: str,
               groups: List[str], config) -> str:
    payload = {
        "sub": user_email,
        "role": role,
        "groups": groups,
        "iat": int(time.time()),
        "exp": int(time.time()) +
               config.jwt_lifetime_hours * 3600,
    }
    return jwt.encode(
        payload, config.jwt_secret,
        algorithm=config.jwt_algorithm)


def verify_jwt(token: str, config) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token, config.jwt_secret,
            algorithms=[config.jwt_algorithm])
        if not payload.get("sub"):
            log.debug("JWT missing 'sub' claim")
            return None
        if "role" not in payload:
            log.debug("JWT missing 'role' claim")
            return None
        return payload
    except jwt.ExpiredSignatureError:
        log.debug("JWT expired")
        return None
    except jwt.InvalidTokenError as e:
        log.debug("JWT invalid: %s", e)
        return None


def derive_role(groups: List[str],
                admin_groups: List[str]) -> str:
    if not groups:
        return "analyst"
    for g in groups:
        if not isinstance(g, str):
            continue
        if g.lower() in [ag.lower() for ag in admin_groups if isinstance(ag, str)]:
            return "admin"
    return "analyst"
