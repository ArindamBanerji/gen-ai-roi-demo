"""Compatibility exports for the SDK authentication contract."""
from copilot_sdk.auth.dependencies import ADMIN_PREFIXES, EXEMPT_PREFIXES, MUTATION_PATHS, get_auth_config, require_auth
_auth_config = None
__all__ = ["ADMIN_PREFIXES", "EXEMPT_PREFIXES", "MUTATION_PATHS", "get_auth_config", "require_auth"]
