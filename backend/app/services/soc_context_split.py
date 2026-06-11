"""SOC context split helpers for EntityCache route readiness.

The current AGE security-context read returns a flat dictionary. This module
classifies that flat shape so future route wiring can cache only stable entity
context and keep alert subjects, counters, proof authority, and mutable runtime
state out of EntityCache.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


FRESH_ALERT_FIELDS = frozenset(
    {
        "alert_id",
        "id",
        "alert_type",
        "severity",
        "status",
        "source_location",
        "source_ip",
        "destination_ip",
        "timestamp",
        "created_at",
        "created_at_epoch",
        "received_at",
        "category",
    }
)

STABLE_ENTITY_FIELDS = frozenset(
    {
        "entity_id",
        "user_id",
        "user_name",
        "name",
        "department",
        "risk_level",
        "user_risk_score",
        "user_traveling",
        "travel_destination",
        "vpn_matches_location",
        "mfa_completed",
        "device_fingerprint_match",
        "asset_id",
        "asset_hostname",
        "hostname",
        "asset_criticality",
        "criticality",
        "asset_type",
        "business_unit",
        "os",
        "owner_id",
        "location_id",
        "location",
        "country",
        "region",
    }
)

NON_CACHEABLE_FIELDS = frozenset(
    {
        "sequence_count",
        "cross_category_count",
        "decision_id",
        "decision",
        "outcome",
        "proof",
        "dk",
        "l5",
        "conservation",
        "factor_vector",
        "campaign_id",
        "campaign_name",
        "known_campaign_signature",
        "indicator",
        "indicator_type",
        "threat_indicator",
        "threat_intel",
        "nodes_consulted",
    }
)


@dataclass(frozen=True)
class SOCContextCacheKey:
    domain: str
    kind: str
    identifier: str


@dataclass(frozen=True)
class SOCContextSplit:
    fresh_alert: dict[str, Any]
    stable_entity: dict[str, Any]
    non_cacheable: dict[str, Any]
    ambiguous: dict[str, Any]
    cache_key: Optional[SOCContextCacheKey]

    def recompose_for_current_route(self) -> dict[str, Any]:
        """Recreate the current flat route context without cache authority changes."""

        return {
            **self.fresh_alert,
            **self.stable_entity,
            **self.non_cacheable,
            **self.ambiguous,
        }


def split_soc_security_context(flat_context: Mapping[str, Any]) -> SOCContextSplit:
    fresh_alert: dict[str, Any] = {}
    stable_entity: dict[str, Any] = {}
    non_cacheable: dict[str, Any] = {}
    ambiguous: dict[str, Any] = {}

    for key, value in dict(flat_context or {}).items():
        key_text = str(key)
        key_l = key_text.lower()
        if key_l in FRESH_ALERT_FIELDS:
            fresh_alert[key_text] = value
        elif key_l in STABLE_ENTITY_FIELDS:
            stable_entity[key_text] = value
        elif key_l in NON_CACHEABLE_FIELDS or _has_non_cacheable_prefix(key_l):
            non_cacheable[key_text] = value
        else:
            ambiguous[key_text] = value

    return SOCContextSplit(
        fresh_alert=fresh_alert,
        stable_entity=stable_entity,
        non_cacheable=non_cacheable,
        ambiguous=ambiguous,
        cache_key=_derive_cache_key(stable_entity),
    )


def _derive_cache_key(stable_entity: Mapping[str, Any]) -> Optional[SOCContextCacheKey]:
    for kind, field_name in (
        ("user", "user_id"),
        ("entity", "entity_id"),
        ("asset", "asset_id"),
    ):
        value = stable_entity.get(field_name)
        if value:
            return SOCContextCacheKey(domain="soc", kind=kind, identifier=str(value))
    return None


def _has_non_cacheable_prefix(key_l: str) -> bool:
    return key_l.startswith(
        (
            "counter_",
            "proof_",
            "dk_",
            "l5_",
            "conservation_",
            "decision_",
            "outcome_",
            "campaign_",
            "indicator_",
            "threat_intel_",
        )
    )
