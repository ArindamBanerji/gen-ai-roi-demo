"""SOC adapter for the SDK Situation Analyzer foundation."""

from __future__ import annotations

import asyncio
import inspect
from typing import Any, Coroutine, cast
from datetime import datetime, timezone

from app.domains.soc.campaign_holdout import banner_suppressed
from copilot_sdk.situation import (
    SituationContext,
    TraversalEdge,
    TraversalNode,
    TypedIntent,
)

CAMPAIGN_ADVISORY_VERSION = "phase4_temporal_v1"


def build_campaign_context_payload(
    *,
    campaign_id: str | None,
    async_state: Any,
    alert_id: str,
    holdout_pct: int = 15,
) -> tuple[dict[str, Any] | None, dict[str, bool | str | None]]:
    """Build v6.0 campaign context from process-local cache only."""
    flags: dict[str, bool | str | None] = {
        "is_campaign_alert": bool(campaign_id),
        "campaign_context_shown": False,
    }
    if not campaign_id:
        return None, flags

    flags["campaign_advisory_version"] = CAMPAIGN_ADVISORY_VERSION
    if banner_suppressed(alert_id, holdout_pct=holdout_pct):
        return None, flags

    flags["campaign_context_shown"] = True
    context = None
    get_context = getattr(async_state, "get_campaign_context", None)
    if callable(get_context):
        context = get_context(campaign_id)
    temporal_context = None
    get_temporal_context = getattr(async_state, "get_temporal_context", None)
    if callable(get_temporal_context):
        temporal_context = get_temporal_context(campaign_id)

    payload: dict[str, Any] = {
        "campaign_id": str(campaign_id),
        "source": "graph_store_cached",
        "advisory_version": CAMPAIGN_ADVISORY_VERSION,
        "status": "materialized" if context is not None else "cold_cache",
    }

    member_count = getattr(context, "member_count", None) if context is not None else None
    first_seen = getattr(context, "first_seen", None) if context is not None else None
    if context is not None:
        payload["category"] = getattr(context, "category", None)
        payload["first_seen"] = first_seen
        payload["member_count"] = member_count
        payload["age_days"] = _campaign_context_age_days(first_seen)

    temporal = _temporal_context_payload(temporal_context)
    if temporal:
        payload["temporal_context"] = temporal
        payload["chain_day"] = temporal["chain_day"]
        payload["total_alerts_across_chain"] = temporal["total_alerts_across_chain"]

    if member_count is not None and int(member_count or 0) >= 3:
        payload["label"] = "Active Campaign"
        age_text = _campaign_context_age_text(payload.get("age_days"))
        payload["advisory"] = (
            f"Active {int(member_count)}-member campaign. {age_text} "
            "Consider escalating the campaign, not just this alert."
        )
    else:
        payload["label"] = "Emerging Campaign Pattern"
        payload["advisory"] = (
            "Emerging campaign pattern. Continue monitoring related alerts before "
            "campaign-level escalation."
        )
    if temporal:
        payload["advisory"] += (
            f" Ongoing incident context: day {temporal['chain_day']} of a cached "
            f"temporal chain with {temporal['total_alerts_across_chain']} total "
            "alerts across related campaign buckets. Use this temporal intelligence "
            "as advisory context; scoring remains campaign-unaware."
        )

    return payload, flags


def _temporal_context_payload(temporal_context: Any) -> dict[str, Any] | None:
    if temporal_context is None:
        return None
    try:
        chain_day = int(getattr(temporal_context, "chain_length_buckets", 1) or 1)
        total_alerts = int(getattr(temporal_context, "total_alert_count", 0) or 0)
    except (TypeError, ValueError):
        return None

    member_counts = getattr(temporal_context, "member_count_by_campaign", {}) or {}
    chain_campaign_ids = [str(cid) for cid in member_counts.keys() if cid]
    previous_campaign_id = getattr(temporal_context, "previous_campaign_id", None)
    chain_start_campaign_id = getattr(temporal_context, "chain_start_campaign_id", None)
    current_campaign_id = getattr(temporal_context, "campaign_id", None)
    for cid in (chain_start_campaign_id, previous_campaign_id, current_campaign_id):
        if cid and str(cid) not in chain_campaign_ids:
            chain_campaign_ids.append(str(cid))
    if not _has_actual_temporal_continuity(
        chain_day=chain_day,
        previous_campaign_id=previous_campaign_id,
        chain_campaign_ids=chain_campaign_ids,
    ):
        return None

    payload: dict[str, Any] = {
        "source": "graph_store_cached",
        "chain_day": chain_day,
        "total_alerts_across_chain": total_alerts,
        "chain_campaign_ids": chain_campaign_ids,
    }
    chain_start_bucket = getattr(temporal_context, "chain_start_bucket", None)
    if chain_start_bucket is not None:
        payload["active_since_bucket"] = chain_start_bucket
    if previous_campaign_id:
        payload["previous_campaign_id"] = str(previous_campaign_id)
        payload["previous_campaign_ids"] = [str(previous_campaign_id)]
    return payload


def _has_actual_temporal_continuity(
    *,
    chain_day: int,
    previous_campaign_id: Any,
    chain_campaign_ids: list[str],
) -> bool:
    return (
        chain_day > 1
        or bool(str(previous_campaign_id).strip() if previous_campaign_id is not None else "")
        or len(chain_campaign_ids) > 1
    )


def _campaign_context_age_days(first_seen: Any) -> int | None:
    if not first_seen:
        return None
    try:
        dt = datetime.fromisoformat(str(first_seen).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, int((datetime.now(timezone.utc) - dt).total_seconds() // 86400))
    except Exception:
        return None


def _campaign_context_age_text(age_days: int | None) -> str:
    if age_days is None:
        return "Campaign age is unavailable."
    if age_days < 1:
        return "Started today."
    if age_days == 1:
        return "Active for 1 day."
    return f"Active for {age_days} days."


class SocAlertTraversalPattern:
    """Map existing SOC alert context into a domain-agnostic situation context."""

    domain = "soc"
    name = "soc_alert_context"
    default_max_depth = 3

    def __init__(self, graph_client: Any | None = None) -> None:
        self.graph_client = graph_client

    def supports(self, intent: TypedIntent) -> bool:
        if intent.domain != self.domain:
            return False
        return bool(_alert_id(intent))

    def traverse(
        self,
        intent: TypedIntent,
        *,
        graph_store: Any = None,
        max_depth: int = 3,
    ) -> SituationContext:
        client = graph_store or self.graph_client
        get_context = getattr(client, "get_security_context", None)
        if callable(get_context) and inspect.iscoroutinefunction(get_context):
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                raw_context = asyncio.run(get_context(_alert_id(intent)))
                return self._context_from_raw(intent, raw_context, max_depth=max_depth)
            return _warning_context(
                intent,
                max_depth,
                "async get_security_context requires traverse_async inside a running event loop",
            )
        return self._traverse_sync(intent, graph_store=graph_store, max_depth=max_depth)

    async def traverse_async(
        self,
        intent: TypedIntent,
        *,
        graph_store: Any = None,
        max_depth: int = 3,
    ) -> SituationContext:
        alert_id = _alert_id(intent)
        if not alert_id:
            return _warning_context(intent, max_depth, "SOC alert intent is missing alert_id")

        client = graph_store or self.graph_client
        get_context = getattr(client, "get_security_context", None)
        if not callable(get_context):
            context = _base_context(intent, alert_id, max_depth=max_depth)
            context.warnings.append("graph client does not provide get_security_context")
            return context

        try:
            value = get_context(alert_id)
            raw_context = await value if inspect.isawaitable(value) else value
        except Exception as exc:
            context = _base_context(intent, alert_id, max_depth=max_depth)
            context.warnings.append(f"get_security_context failed: {exc}")
            return context
        return self._context_from_raw(intent, raw_context, max_depth=max_depth)

    def _traverse_sync(
        self,
        intent: TypedIntent,
        *,
        graph_store: Any = None,
        max_depth: int = 3,
    ) -> SituationContext:
        alert_id = _alert_id(intent)
        if not alert_id:
            return _warning_context(intent, max_depth, "SOC alert intent is missing alert_id")

        client = graph_store or self.graph_client
        get_context = getattr(client, "get_security_context", None)
        if not callable(get_context):
            context = _base_context(intent, alert_id, max_depth=max_depth)
            context.warnings.append("graph client does not provide get_security_context")
            return context

        try:
            raw_context = _resolve_call(get_context(alert_id))
        except Exception as exc:
            context = _base_context(intent, alert_id, max_depth=max_depth)
            context.warnings.append(f"get_security_context failed: {exc}")
            return context
        return self._context_from_raw(intent, raw_context, max_depth=max_depth)

    def _context_from_raw(
        self,
        intent: TypedIntent,
        raw_context: Any,
        *,
        max_depth: int,
    ) -> SituationContext:
        alert_id = _alert_id(intent)
        if not isinstance(raw_context, dict) or not raw_context:
            context = _base_context(intent, alert_id, max_depth=max_depth)
            context.warnings.append("no SOC security context found")
            return context

        return _map_security_context(intent, raw_context, max_depth=max_depth)


def _alert_id(intent: TypedIntent) -> str:
    value = (
        intent.scope.get("alert_id")
        or intent.source_event_id
        or intent.scope.get("source_event_id")
        or intent.metadata.get("alert_id")
    )
    return str(value or "").strip()


def _resolve_call(value: Any) -> Any:
    if not inspect.isawaitable(value):
        return value
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(cast(Coroutine[Any, Any, Any], value))
    raise RuntimeError("async get_security_context requires calling from a synchronous test/helper")


def _warning_context(intent: TypedIntent, max_depth: int, warning: str) -> SituationContext:
    return SituationContext(
        domain="soc",
        decision_id=intent.decision_id,
        intent=intent,
        pattern_name=SocAlertTraversalPattern.name,
        max_depth=max_depth,
        warnings=[warning],
    )


def _base_context(intent: TypedIntent, alert_id: str, *, max_depth: int) -> SituationContext:
    return SituationContext(
        domain="soc",
        decision_id=intent.decision_id,
        intent=intent,
        pattern_name=SocAlertTraversalPattern.name,
        nodes=[
            TraversalNode(
                id=alert_id,
                type="Alert",
                label="Alert",
                properties={"alert_id": alert_id},
                depth=0,
                source="soc",
            )
        ],
        evidence_chain=[{"node_id": alert_id, "type": "Alert", "depth": 0}],
        max_depth=max_depth,
    )


def _map_security_context(
    intent: TypedIntent,
    raw_context: dict[str, Any],
    *,
    max_depth: int,
) -> SituationContext:
    alert_id = str(raw_context.get("alert_id") or _alert_id(intent))
    context = _base_context(intent, alert_id, max_depth=max_depth)
    alert_node = context.nodes[0]
    context.nodes[0] = TraversalNode(
        id=alert_node.id,
        type=alert_node.type,
        label=str(raw_context.get("alert_type") or "Alert"),
        properties={
            key: raw_context.get(key)
            for key in (
                "alert_id",
                "alert_type",
                "mfa_completed",
                "device_fingerprint_match",
                "known_campaign_signature",
                "nodes_consulted",
            )
            if key in raw_context
        },
        depth=0,
        source="soc",
    )

    if max_depth <= 0:
        return SituationContext(
            domain=context.domain,
            decision_id=context.decision_id,
            intent=context.intent,
            pattern_name=context.pattern_name,
            nodes=context.nodes,
            edges=[],
            evidence_chain=context.evidence_chain,
            max_depth=max_depth,
            truncated=True,
            warnings=["max_depth=0 limited SOC context to alert node"],
            metadata={"nodes_consulted": raw_context.get("nodes_consulted")},
        )

    nodes = list(context.nodes)
    edges: list[TraversalEdge] = []
    evidence_chain = list(context.evidence_chain)

    _add_context_node(
        nodes,
        edges,
        evidence_chain,
        alert_id,
        node_id=str(raw_context.get("user_id") or ""),
        node_type="User",
        edge_type="INVOLVES",
        label=str(raw_context.get("user_name") or raw_context.get("user_id") or ""),
        properties={
            "user_id": raw_context.get("user_id"),
            "user_name": raw_context.get("user_name"),
            "user_title": raw_context.get("user_title"),
            "user_risk_score": raw_context.get("user_risk_score"),
        },
    )
    _add_context_node(
        nodes,
        edges,
        evidence_chain,
        alert_id,
        node_id=str(raw_context.get("asset_id") or ""),
        node_type="Asset",
        edge_type="DETECTED_ON",
        label=str(raw_context.get("asset_hostname") or raw_context.get("asset_id") or ""),
        properties={
            "asset_id": raw_context.get("asset_id"),
            "asset_hostname": raw_context.get("asset_hostname"),
            "asset_criticality": raw_context.get("asset_criticality"),
        },
    )
    if raw_context.get("user_traveling"):
        destination = str(raw_context.get("travel_destination") or "travel")
        _add_context_node(
            nodes,
            edges,
            evidence_chain,
            alert_id,
            node_id=f"travel:{destination}",
            node_type="TravelContext",
            edge_type="HAS_TRAVEL",
            label=destination,
            properties={
                "travel_destination": raw_context.get("travel_destination"),
                "vpn_matches_location": raw_context.get("vpn_matches_location"),
                "vpn_provider": raw_context.get("vpn_provider"),
            },
        )
    _add_context_node(
        nodes,
        edges,
        evidence_chain,
        alert_id,
        node_id=str(raw_context.get("playbook_id") or ""),
        node_type="Playbook",
        edge_type="HANDLED_BY",
        label=str(raw_context.get("playbook_id") or ""),
        properties={"playbook_id": raw_context.get("playbook_id")},
    )
    _add_context_node(
        nodes,
        edges,
        evidence_chain,
        alert_id,
        node_id=str(raw_context.get("pattern_id") or ""),
        node_type="AttackPattern",
        edge_type="MATCHES",
        label=str(raw_context.get("pattern_id") or ""),
        properties={
            "pattern_id": raw_context.get("pattern_id"),
            "pattern_count": raw_context.get("pattern_count"),
            "fp_rate": raw_context.get("fp_rate"),
        },
    )
    _add_context_node(
        nodes,
        edges,
        evidence_chain,
        alert_id,
        node_id=str(raw_context.get("campaign_id") or raw_context.get("campaign") or ""),
        node_type="Campaign",
        edge_type="MEMBER_OF",
        label=str(raw_context.get("campaign_id") or raw_context.get("campaign") or ""),
        properties={
            "campaign_id": raw_context.get("campaign_id") or raw_context.get("campaign"),
        },
    )

    return SituationContext(
        domain="soc",
        decision_id=intent.decision_id,
        intent=intent,
        pattern_name=SocAlertTraversalPattern.name,
        nodes=nodes,
        edges=edges,
        evidence_chain=evidence_chain,
        max_depth=max_depth,
        metadata={"nodes_consulted": raw_context.get("nodes_consulted")},
    )


def _add_context_node(
    nodes: list[TraversalNode],
    edges: list[TraversalEdge],
    evidence_chain: list[dict[str, Any]],
    alert_id: str,
    *,
    node_id: str,
    node_type: str,
    edge_type: str,
    label: str,
    properties: dict[str, Any],
) -> None:
    clean_id = str(node_id or "").strip()
    if not clean_id:
        return
    clean_properties = {key: value for key, value in properties.items() if value is not None}
    nodes.append(
        TraversalNode(
            id=clean_id,
            type=node_type,
            label=label,
            properties=clean_properties,
            depth=1,
            source="soc",
        )
    )
    edges.append(
        TraversalEdge(
            source_id=alert_id,
            target_id=clean_id,
            type=edge_type,
            depth=1,
        )
    )
    evidence_chain.append({"node_id": clean_id, "type": node_type, "depth": 1})
