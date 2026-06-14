"""SOC adapter for the SDK Situation Analyzer foundation."""

from __future__ import annotations

import asyncio
import inspect
from typing import Any

from copilot_sdk.situation import (
    SituationContext,
    TraversalEdge,
    TraversalNode,
    TypedIntent,
)


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
        return asyncio.run(value)
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
