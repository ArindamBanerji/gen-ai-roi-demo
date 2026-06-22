"""
Re-export stub -- implementation moved to app.framework.event_bus.
Preserved for backwards compatibility. Do not add logic here.
When copilot-sdk is extracted, update callers to import from
copilot_sdk.event_bus directly.
"""
from app.framework.event_bus import *  # noqa: F401, F403
