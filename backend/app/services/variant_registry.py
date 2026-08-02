"""AE-01 in-memory registry for AgentEvolver variants.

The registry is a read-optimized projection rebuilt from AE-04
EvolutionEvent nodes. It tracks dynamic operational variants created from
graph context while leaving scoring and learning state outside this module.
"""

from __future__ import annotations

import ast
import json
import logging
import time
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Optional, cast

from gae.evolution import (
    ARTIFACT_CONTEXT_POLICY,
    ARTIFACT_EVIDENCE_ORDER,
    ARTIFACT_PROMPT_MODULE,
    ARTIFACT_ROUTING_RULE,
    ARTIFACT_SCORING_THRESHOLD,
    PROMOTION_APPROVED,
    PROMOTION_REJECTED,
    ROLLBACK,
    VALID_ARTIFACT_TYPES,
    VARIANT_CREATED,
)
from app.graph_schema import _S

log = logging.getLogger(__name__)

CANDIDATE = "candidate"
SHADOW = "shadow"
ACTIVE = "active"
REJECTED = "rejected"
ROLLED_BACK = "rolled_back"

VALID_STATUSES = {
    CANDIDATE,
    SHADOW,
    ACTIVE,
    REJECTED,
    ROLLED_BACK,
}

_VALID_TRANSITIONS: dict[str, set[str]] = {
    CANDIDATE: {SHADOW, REJECTED},
    SHADOW: {ACTIVE, REJECTED},
    ACTIVE: {ROLLED_BACK},
    REJECTED: set(),
    ROLLED_BACK: set(),
}

_DEDUP_STATUSES: set[str] = {CANDIDATE, SHADOW, ACTIVE}
_REGISTRY: dict[str, "VariantRecord"] = {}


@dataclass
class VariantRecord:
    variant_id: str
    artifact_type: str
    category: Optional[str]
    config: dict[str, Any]
    status: str
    trigger_key: str
    graph_trigger: dict[str, Any]
    created_at: float
    promoted_at: Optional[float] = None


def _copy_record(record: VariantRecord) -> VariantRecord:
    return deepcopy(record)


def _parse_json_state(value: Any) -> Any:
    if value is None or value == "":
        return {}
    if isinstance(value, (dict, list, str, int, float, bool)):
        if not isinstance(value, str):
            return deepcopy(value)
    else:
        return {}
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return {}
        if isinstance(parsed, (dict, list, str, int, float, bool)):
            return parsed
    return {}


def _row_value(row: dict[str, Any], key: str, default: Any = None) -> Any:
    if key in row:
        return row.get(key)
    event = row.get("e")
    if isinstance(event, dict) and key in event:
        return event.get(key)
    return default


def _timestamp_seconds(value: Any, *, epoch_ms: bool = False) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return time.time()
    if epoch_ms or numeric > 10_000_000_000:
        return numeric / 1000.0
    return numeric


def _validate_record(record: VariantRecord) -> None:
    if not record.variant_id or not str(record.variant_id).strip():
        raise ValueError("variant_id is required")
    if record.artifact_type not in VALID_ARTIFACT_TYPES:
        raise ValueError(f"invalid artifact_type: {record.artifact_type}")
    if record.status not in VALID_STATUSES:
        raise ValueError(f"invalid variant status: {record.status}")
    if not record.trigger_key or not str(record.trigger_key).strip():
        raise ValueError("trigger_key is required")


def _first_string(*values: Any) -> Optional[str]:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _config_from_event(
    after_state: dict[str, Any],
    metadata: dict[str, Any],
    graph_context: dict[str, Any],
) -> dict[str, Any]:
    for source in (after_state, metadata, graph_context):
        config = source.get("config") if isinstance(source, dict) else None
        if isinstance(config, dict):
            return deepcopy(config)
    return deepcopy(after_state) if isinstance(after_state, dict) else {}


def _record_from_created(row: dict[str, Any]) -> VariantRecord | None:
    variant_id = _first_string(_row_value(row, "variant_id"))
    artifact_type = _first_string(_row_value(row, "artifact_type"))
    if not variant_id or artifact_type not in VALID_ARTIFACT_TYPES:
        return None
    artifact_type = cast(str, artifact_type)

    after_state = _parse_json_state(_row_value(row, "after_state"))
    metadata = _parse_json_state(_row_value(row, "metadata"))
    graph_context = _parse_json_state(_row_value(row, "graph_context"))
    if not isinstance(after_state, dict):
        after_state = {}
    if not isinstance(metadata, dict):
        metadata = {}
    if not isinstance(graph_context, dict):
        graph_context = {}

    category = _first_string(
        after_state.get("category"),
        metadata.get("category"),
        graph_context.get("category"),
    )
    trigger_key = _first_string(
        metadata.get("trigger_key"),
        graph_context.get("trigger_key"),
        after_state.get("trigger_key"),
        f"{artifact_type}:{category or 'global'}:{variant_id}",
    )
    status = _first_string(after_state.get("status"), metadata.get("status"), CANDIDATE)
    timestamp_epoch = _row_value(row, "timestamp_epoch")
    created_at = _timestamp_seconds(
        timestamp_epoch if timestamp_epoch is not None else _row_value(row, "timestamp", None),
        epoch_ms=timestamp_epoch is not None,
    )

    try:
        record = VariantRecord(
            variant_id=variant_id,
            artifact_type=artifact_type,
            category=category,
            config=_config_from_event(after_state, metadata, graph_context),
            status=status or CANDIDATE,
            trigger_key=trigger_key or variant_id,
            graph_trigger=graph_context,
            created_at=created_at,
        )
        _validate_record(record)
    except ValueError:
        return None
    return record


def register_variant(record: VariantRecord) -> VariantRecord:
    """Register or replace an in-memory variant record."""
    _validate_record(record)
    _REGISTRY[record.variant_id] = _copy_record(record)
    return _copy_record(record)


def get_variant(variant_id: str) -> VariantRecord | None:
    record = _REGISTRY.get(variant_id)
    return _copy_record(record) if record is not None else None


def get_active_variant_for_category(
    category: str | None,
    artifact_type: str,
) -> VariantRecord | None:
    if artifact_type not in VALID_ARTIFACT_TYPES:
        raise ValueError(f"invalid artifact_type: {artifact_type}")
    matches = [
        record
        for record in _REGISTRY.values()
        if record.status == ACTIVE
        and record.artifact_type == artifact_type
        and (record.category == category or record.category is None)
    ]
    if not matches:
        return None
    matches.sort(key=lambda record: (record.promoted_at or 0.0, record.created_at), reverse=True)
    return _copy_record(matches[0])


def has_active_or_shadow(trigger_key: str) -> bool:
    return any(
        record.trigger_key == trigger_key and record.status in _DEDUP_STATUSES
        for record in _REGISTRY.values()
    )


def transition_status(variant_id: str, new_status: str) -> VariantRecord:
    if new_status not in VALID_STATUSES:
        raise ValueError(f"invalid variant status: {new_status}")
    record = _REGISTRY.get(variant_id)
    if record is None:
        raise KeyError(variant_id)
    allowed = _VALID_TRANSITIONS.get(record.status, set())
    if new_status not in allowed:
        raise ValueError(f"invalid transition: {record.status} -> {new_status}")
    updated = _copy_record(record)
    updated.status = new_status
    if new_status == ACTIVE:
        updated.promoted_at = time.time()
    _REGISTRY[variant_id] = _copy_record(updated)
    return _copy_record(updated)


def get_all_variants(status_filter: str | None = None) -> list[VariantRecord]:
    if status_filter is not None and status_filter not in VALID_STATUSES:
        raise ValueError(f"invalid variant status: {status_filter}")
    records = [
        record
        for record in _REGISTRY.values()
        if status_filter is None or record.status == status_filter
    ]
    records.sort(key=lambda record: (record.created_at, record.variant_id))
    return [_copy_record(record) for record in records]


async def _query_events(graph_client: Any, event_type: str) -> tuple[list[dict[str, Any]], str | None]:
    try:
        rows = await graph_client.run_query(
            "MATCH (e:EvolutionEvent) "
            f"WHERE e.event_type = {_S(event_type)} "
            "RETURN e.id AS id, e.event_type AS event_type, "
            "e.variant_id AS variant_id, e.artifact_type AS artifact_type, "
            "e.after_state AS after_state, e.graph_context AS graph_context, "
            "e.metadata AS metadata, e.timestamp AS timestamp, "
            "e.timestamp_epoch AS timestamp_epoch "
            "ORDER BY e.timestamp_epoch ASC"
        )
    except Exception as exc:
        log.warning("Variant registry rebuild query failed for %s: %s", event_type, exc)
        return [], str(exc)
    return list(rows or []), None


async def rebuild_registry(graph_client: Any) -> dict[str, Any]:
    """Rebuild the in-memory registry from durable AE-04 EvolutionEvent nodes."""
    _REGISTRY.clear()
    errors: list[dict[str, str]] = []

    created_rows, error = await _query_events(graph_client, VARIANT_CREATED)
    if error:
        errors.append({"event_type": VARIANT_CREATED, "error": error})
    for row in created_rows:
        record = _record_from_created(row)
        if record is not None:
            _REGISTRY[record.variant_id] = record

    promotion_rows, error = await _query_events(graph_client, PROMOTION_APPROVED)
    if error:
        errors.append({"event_type": PROMOTION_APPROVED, "error": error})
    for row in promotion_rows:
        variant_id = _first_string(_row_value(row, "variant_id"))
        record = _REGISTRY.get(variant_id or "")
        if record is None:
            continue
        record.status = ACTIVE
        timestamp_epoch = _row_value(row, "timestamp_epoch")
        record.promoted_at = _timestamp_seconds(
            timestamp_epoch if timestamp_epoch is not None else _row_value(row, "timestamp", None),
            epoch_ms=timestamp_epoch is not None,
        )

    rollback_rows, error = await _query_events(graph_client, ROLLBACK)
    if error:
        errors.append({"event_type": ROLLBACK, "error": error})
    for row in rollback_rows:
        variant_id = _first_string(_row_value(row, "variant_id"))
        record = _REGISTRY.get(variant_id or "")
        if record is None:
            continue
        record.status = ROLLED_BACK

    rejection_rows, error = await _query_events(graph_client, PROMOTION_REJECTED)
    if error:
        errors.append({"event_type": PROMOTION_REJECTED, "error": error})
    for row in rejection_rows:
        variant_id = _first_string(_row_value(row, "variant_id"))
        record = _REGISTRY.get(variant_id or "")
        if record is None:
            continue
        record.status = REJECTED

    return {
        "rebuilt": len(_REGISTRY),
        "active": len([r for r in _REGISTRY.values() if r.status == ACTIVE]),
        "rolled_back": len([r for r in _REGISTRY.values() if r.status == ROLLED_BACK]),
        "rejected": len([r for r in _REGISTRY.values() if r.status == REJECTED]),
        "errors": errors,
        "variants": [variant_to_dict(record) for record in get_all_variants()],
    }


def reset_variant_registry() -> None:
    """Clear the in-memory registry without touching graph storage."""
    _REGISTRY.clear()


def variant_to_dict(record: VariantRecord) -> dict[str, Any]:
    return {
        "variant_id": record.variant_id,
        "artifact_type": record.artifact_type,
        "category": record.category,
        "config": deepcopy(record.config),
        "status": record.status,
        "trigger_key": record.trigger_key,
        "graph_trigger": deepcopy(record.graph_trigger),
        "created_at": record.created_at,
        "promoted_at": record.promoted_at,
    }


__all__ = [
    "ACTIVE",
    "ARTIFACT_CONTEXT_POLICY",
    "ARTIFACT_EVIDENCE_ORDER",
    "ARTIFACT_PROMPT_MODULE",
    "ARTIFACT_ROUTING_RULE",
    "ARTIFACT_SCORING_THRESHOLD",
    "CANDIDATE",
    "PROMOTION_REJECTED",
    "REJECTED",
    "ROLLED_BACK",
    "SHADOW",
    "VALID_STATUSES",
    "VariantRecord",
    "get_active_variant_for_category",
    "get_all_variants",
    "get_variant",
    "has_active_or_shadow",
    "rebuild_registry",
    "register_variant",
    "reset_variant_registry",
    "transition_status",
    "variant_to_dict",
]
