"""SOC category-specific investigation patterns for VLD Phase 1a.

These patterns are read-only adapters over the existing SOC graph schema.  The
schema currently provides Alert, User, Asset, Campaign, ThreatIndicator, and
AttackPattern nodes with INVOLVES, DETECTED_ON, MEMBER_OF, CLASSIFIED_AS, and
HAS_INDICATOR edges.  Requested investigation concepts such as Process,
Session, and CloudResource are represented with the closest available SOC
schema and alert/context metadata until first-class graph nodes exist.
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class InvestigationPattern(Protocol):
    @property
    def category_name(self) -> str:
        ...

    @property
    def pattern_name(self) -> str:
        ...

    @property
    def selected_edge(self) -> str:
        ...

    @property
    def enriched_factors(self) -> tuple[str, ...]:
        ...

    @property
    def candidate_read(self) -> str:
        ...

    def supports(self, alert_context: dict[str, Any]) -> bool:
        ...

    async def execute(self, alert_context: dict[str, Any], graph_store: Any) -> dict[str, Any]:
        ...


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


@dataclass(frozen=True)
class BaseInvestigationPattern:
    category_name: str
    pattern_name: str
    traversal: str
    selected_edge: str
    enriched_factors: tuple[str, ...]
    candidate_read: str
    graph_query: str

    def supports(self, alert_context: dict[str, Any]) -> bool:
        return bool(str(alert_context.get("alert_id") or alert_context.get("id") or "").strip())

    async def execute(self, alert_context: dict[str, Any], graph_store: Any) -> dict[str, Any]:
        alert_id = str(alert_context.get("alert_id") or alert_context.get("id") or "").strip()
        context: dict[str, Any] = {}
        get_context = getattr(graph_store, "get_security_context", None)
        if callable(get_context) and alert_id:
            try:
                raw = await _maybe_await(get_context(alert_id))
                if isinstance(raw, dict):
                    context = raw
            except Exception as exc:  # read-only diagnostic: report failed read as evidence metadata
                logger.warning("SOC VLD investigation pattern %s failed context read: %s", self.pattern_name, exc)
                context = {"read_error": type(exc).__name__}

        evidence = self._evidence_from_context(alert_context, context)
        evidence.update(
            {
                "investigation_category": self.category_name,
                "investigation_pattern": self.pattern_name,
                "traversal": self.traversal,
                "selected_edge": self.selected_edge,
                "candidate_read": self.candidate_read,
                "candidate_reads": [self.candidate_read],
                "enriched_factors": list(self.enriched_factors),
                "graph_query": self.graph_query,
                "schema_source": "SOC_GRAPH_CONTRACT",
                "read_cost": float(evidence.get("nodes_consulted", context.get("nodes_consulted", 1.0)) or 1.0),
            }
        )
        evidence["evidence_keys"] = sorted(str(key) for key in evidence.keys())
        logger.info(
            "SOC VLD pattern retrieved evidence",
            extra={"pattern": self.pattern_name, "alert_id": alert_id, "keys": evidence["evidence_keys"]},
        )
        return evidence

    def _evidence_from_context(self, alert_context: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        merged = {**alert_context, **context}
        return {key: value for key, value in merged.items() if value is not None}


class CredentialInvestigationPattern(BaseInvestigationPattern):
    def __init__(self) -> None:
        super().__init__(
            category_name="credential_access",
            pattern_name="credential_investigation",
            traversal="Alert -> User -> IAM-equivalent identity context -> privilege changes",
            selected_edge="INVOLVES",
            enriched_factors=("privileged_identity_context", "pattern_history"),
            candidate_read="user_identity_context",
            graph_query=(
                "MATCH (a:Alert)-[:INVOLVES]->(u:User) "
                "OPTIONAL MATCH (a)-[:CLASSIFIED_AS]->(ap:AttackPattern) "
                "OPTIONAL MATCH (a)-[:HAS_INDICATOR]->(ti:ThreatIndicator)"
            ),
        )


class MalwareInvestigationPattern(BaseInvestigationPattern):
    def __init__(self) -> None:
        super().__init__(
            category_name="malware_execution",
            pattern_name="malware_investigation",
            traversal="Alert -> ThreatIndicator / AttackPattern -> alert process metadata fallback",
            selected_edge="HAS_INDICATOR",
            enriched_factors=("threat_intel_enrichment", "time_anomaly"),
            candidate_read="threat_indicator_context",
            graph_query=(
                "MATCH (a:Alert)-[:HAS_INDICATOR]->(ti:ThreatIndicator) "
                "OPTIONAL MATCH (a)-[:CLASSIFIED_AS]->(ap:AttackPattern)"
            ),
        )


class LateralMovementPattern(BaseInvestigationPattern):
    def __init__(self) -> None:
        super().__init__(
            category_name="lateral_movement",
            pattern_name="lateral_movement_investigation",
            traversal="Alert -> Asset -> Campaign / peer alert context",
            selected_edge="DETECTED_ON",
            enriched_factors=("device_trust", "privileged_identity_context"),
            candidate_read="asset_campaign_context",
            graph_query=(
                "MATCH (a:Alert)-[:DETECTED_ON]->(asset:Asset) "
                "OPTIONAL MATCH (a)-[:MEMBER_OF]->(campaign:Campaign)"
            ),
        )


class ExfiltrationPattern(BaseInvestigationPattern):
    def __init__(self) -> None:
        super().__init__(
            category_name="data_exfiltration",
            pattern_name="exfiltration_investigation",
            traversal="Alert -> Asset -> Campaign / threat indicators for data movement",
            selected_edge="DETECTED_ON",
            enriched_factors=("asset_criticality", "pattern_history"),
            candidate_read="asset_data_movement_context",
            graph_query=(
                "MATCH (a:Alert)-[:DETECTED_ON]->(asset:Asset) "
                "OPTIONAL MATCH (a)-[:HAS_INDICATOR]->(ti:ThreatIndicator) "
                "OPTIONAL MATCH (a)-[:MEMBER_OF]->(campaign:Campaign)"
            ),
        )


class InsiderPattern(BaseInvestigationPattern):
    def __init__(self) -> None:
        super().__init__(
            category_name="insider_threat",
            pattern_name="insider_investigation",
            traversal="Alert -> User -> Campaign / peer baseline metadata",
            selected_edge="INVOLVES",
            enriched_factors=("time_anomaly", "pattern_history"),
            candidate_read="user_behavior_context",
            graph_query=(
                "MATCH (a:Alert)-[:INVOLVES]->(u:User) "
                "OPTIONAL MATCH (a)-[:MEMBER_OF]->(campaign:Campaign)"
            ),
        )


class CloudInfraPattern(BaseInvestigationPattern):
    def __init__(self) -> None:
        super().__init__(
            category_name="cloud_infrastructure",
            pattern_name="cloud_infrastructure_investigation",
            traversal="Alert -> Asset -> AttackPattern / IAM-like cloud metadata fallback",
            selected_edge="DETECTED_ON",
            enriched_factors=("asset_criticality", "device_trust"),
            candidate_read="cloud_asset_context",
            graph_query=(
                "MATCH (a:Alert)-[:DETECTED_ON]->(asset:Asset) "
                "OPTIONAL MATCH (a)-[:CLASSIFIED_AS]->(ap:AttackPattern)"
            ),
        )


def build_default_investigation_patterns() -> dict[str, InvestigationPattern]:
    patterns: list[InvestigationPattern] = [
        CredentialInvestigationPattern(),
        MalwareInvestigationPattern(),
        LateralMovementPattern(),
        ExfiltrationPattern(),
        InsiderPattern(),
        CloudInfraPattern(),
    ]
    return {pattern.category_name: pattern for pattern in patterns}
