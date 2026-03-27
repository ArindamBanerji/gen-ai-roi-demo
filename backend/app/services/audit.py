"""
Re-export stub — implementation moved to app.framework.audit.
Preserved for backwards compatibility. Do not add logic here.
When copilot-sdk is extracted, update callers to import from
copilot_sdk.audit directly.
"""
from app.framework.audit import *  # noqa: F401, F403
# Private module-level objects accessed by tests via `import app.services.audit as m`
from app.framework.audit import _LEDGER, _SITUATION_TYPES  # noqa: F401
