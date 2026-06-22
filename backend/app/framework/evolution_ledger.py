"""
Shim -- evolution ledger has moved to gae.evolution.

All symbols are re-exported from the canonical location so that any
remaining call-sites that haven't been updated yet continue to work.
New code should import from gae.evolution directly.
"""

from gae.evolution import (  # noqa: F401
    VARIANT_CREATED,
    SHADOW_STARTED,
    SHADOW_RESULT,
    PROMOTION_APPROVED,
    PROMOTION_REJECTED,
    ROLLBACK,
    VALID_EVENT_TYPES,
    ARTIFACT_ROUTING_RULE,
    ARTIFACT_CONTEXT_POLICY,
    ARTIFACT_EVIDENCE_ORDER,
    ARTIFACT_SCORING_THRESHOLD,
    ARTIFACT_PROMPT_MODULE,
    VALID_ARTIFACT_TYPES,
    record_evolution_event,
    rebuild_shadow_index,
    get_shadow_summary,
    get_variant_history,
    get_recent_events,
    get_evolution_summary,
    reset_evolution_ledger,
)
