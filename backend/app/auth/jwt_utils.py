"""Compatibility exports for the SDK authentication contract."""
from copilot_sdk.auth.jwt_utils import create_jwt, derive_role, verify_jwt
__all__ = ["create_jwt", "derive_role", "verify_jwt"]
