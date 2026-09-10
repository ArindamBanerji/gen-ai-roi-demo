"""SOC category-specific investigation patterns for VLD Phase 1a.

The SOC graph contract supports Alert, User, Asset, Campaign,
ThreatIndicator and AttackPattern nodes, with Alert-originating INVOLVES,
DETECTED_ON, MEMBER_OF, CLASSIFIED_AS and HAS_INDICATOR edges.  Each pattern
below performs a distinct bounded read when ``run_query`` is available and
falls back to the existing bulk context adapter only as a read-failure-safe
source for fixture/offline execution.
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from typing import Any, Protocol, cast, runtime_checkable

import numpy as np

from app.domains.soc.config import N_FACTORS
from app.graph_schema import _S

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

    @property
    def graph_query(self) -> str:
        ...

    def supports(self, alert_context: dict[str, Any]) -> bool:
        ...

    async def execute(self, alert_context: dict[str, Any], graph_store: Any) -> dict[str, Any]:
        ...

    def evidence_vector(self, evidence: dict[str, Any]) -> np.ndarray:
        ...

    def evidence_keys(self) -> tuple[str, ...]:
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
    vector_values: tuple[tuple[int, float], ...]
    specific_key_names: tuple[str, ...]

    def supports(self, alert_context: dict[str, Any]) -> bool:
        return bool(str(alert_context.get("alert_id") or alert_context.get("id") or "").strip())

    async def execute(self, alert_context: dict[str, Any], graph_store: Any) -> dict[str, Any]:
        alert_id = str(alert_context.get("alert_id") or alert_context.get("id") or "").strip()
        rows = await self._bounded_read(alert_id, graph_store)
        context = await self._fallback_context(alert_id, graph_store)
        evidence = self._specific_evidence(alert_context, context, rows)
        vector = self.evidence_vector(evidence)
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
                "vld_factor_vector": [float(x) for x in vector.tolist()],
                "read_cost": float(len(rows) if rows else context.get("nodes_consulted", 1.0) or 1.0),
            }
        )
        evidence["evidence_keys"] = sorted(str(key) for key in self.evidence_keys())
        logger.info(
            "SOC VLD pattern retrieved evidence",
            extra={"pattern": self.pattern_name, "alert_id": alert_id, "keys": evidence["evidence_keys"]},
        )
        return evidence

    async def _bounded_read(self, alert_id: str, graph_store: Any) -> list[dict[str, Any]]:
        run_query = getattr(graph_store, "run_query", None)
        if not callable(run_query) or not alert_id:
            return []
        try:
            rows = await _maybe_await(run_query(self.graph_query.format(alert_id=_S(alert_id))))
        except Exception as exc:
            logger.warning("SOC VLD pattern %s bounded read failed: %s", self.pattern_name, exc)
            return []
        if isinstance(rows, list):
            return [dict(row) for row in rows if isinstance(row, dict)]
        return []

    async def _fallback_context(self, alert_id: str, graph_store: Any) -> dict[str, Any]:
        get_context = getattr(graph_store, "get_security_context", None)
        if not callable(get_context) or not alert_id:
            return {}
        try:
            raw = await _maybe_await(get_context(alert_id))
        except Exception as exc:
            logger.warning("SOC VLD pattern %s context fallback failed: %s", self.pattern_name, exc)
            return {"read_error": type(exc).__name__}
        return dict(raw) if isinstance(raw, dict) else {}

    def _specific_evidence(
        self,
        alert_context: dict[str, Any],
        context: dict[str, Any],
        rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        merged = {**alert_context, **context}
        return {name: merged.get(name, len(rows) if rows else 1) for name in self.specific_key_names}

    def evidence_vector(self, evidence: dict[str, Any]) -> np.ndarray:
        vector = np.zeros(N_FACTORS, dtype=np.float64)
        for index, value in self.vector_values:
            vector[index] = float(value)
        return cast(np.ndarray, vector)

    def evidence_keys(self) -> tuple[str, ...]:
        return self.specific_key_names + (
            "investigation_category",
            "investigation_pattern",
            "selected_edge",
            "vld_factor_vector",
        )


class CredentialInvestigationPattern(BaseInvestigationPattern):
    def __init__(self) -> None:
        super().__init__(
            category_name="credential_access",
            pattern_name="credential_investigation",
            traversal="Alert -> User -> identity-risk context",
            selected_edge="INVOLVES",
            enriched_factors=("privileged_identity_context", "pattern_history"),
            candidate_read="user_identity_context",
            graph_query=(
                "MATCH (a:Alert {{alert_id: {alert_id}}}-[:INVOLVES]->(u:User) "
                "RETURN a.alert_id AS alert_id, u.user_id AS user_id, u.risk_level AS user_risk LIMIT 5"
            ),
            vector_values=((0, 0.88), (3, 0.72)),
            specific_key_names=("credential_user_id", "credential_user_risk", "credential_identity_signal"),
        )

    def _specific_evidence(self, alert_context: dict[str, Any], context: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
        first = rows[0] if rows else {}
        return {
            "credential_user_id": first.get("user_id") or context.get("user_id") or alert_context.get("user_id"),
            "credential_user_risk": first.get("user_risk") or context.get("user_risk_score") or context.get("risk_level"),
            "credential_identity_signal": bool(first or context.get("user_id") or alert_context.get("user_id")),
        }


class MalwareInvestigationPattern(BaseInvestigationPattern):
    def __init__(self) -> None:
        super().__init__(
            category_name="malware_execution",
            pattern_name="malware_investigation",
            traversal="Alert -> ThreatIndicator -> AttackPattern",
            selected_edge="HAS_INDICATOR",
            enriched_factors=("threat_intel_enrichment", "time_anomaly"),
            candidate_read="threat_indicator_context",
            graph_query=(
                "MATCH (a:Alert {{alert_id: {alert_id}}}-[:HAS_INDICATOR]->(ti:ThreatIndicator) "
                "OPTIONAL MATCH (a)-[:CLASSIFIED_AS]->(ap:AttackPattern) "
                "RETURN ti.indicator AS indicator, ti.severity AS indicator_severity, ap.pattern_id AS pattern_id LIMIT 5"
            ),
            vector_values=((2, 0.90), (4, 0.70)),
            specific_key_names=("malware_indicator", "malware_indicator_severity", "malware_attack_pattern"),
        )


class LateralMovementPattern(BaseInvestigationPattern):
    def __init__(self) -> None:
        super().__init__(
            category_name="lateral_movement",
            pattern_name="lateral_movement_investigation",
            traversal="Alert -> Asset -> Campaign",
            selected_edge="DETECTED_ON",
            enriched_factors=("device_trust", "privileged_identity_context"),
            candidate_read="asset_campaign_context",
            graph_query=(
                "MATCH (a:Alert {{alert_id: {alert_id}}}-[:DETECTED_ON]->(asset:Asset) "
                "OPTIONAL MATCH (a)-[:MEMBER_OF]->(campaign:Campaign) "
                "RETURN asset.asset_id AS asset_id, asset.criticality AS asset_criticality, campaign.campaign_id AS campaign_id LIMIT 5"
            ),
            vector_values=((5, 0.20), (0, 0.75)),
            specific_key_names=("lateral_asset_id", "lateral_asset_criticality", "lateral_campaign_id"),
        )


class ExfiltrationPattern(BaseInvestigationPattern):
    def __init__(self) -> None:
        super().__init__(
            category_name="data_exfiltration",
            pattern_name="exfiltration_investigation",
            traversal="Alert -> Asset -> ThreatIndicator / Campaign",
            selected_edge="DETECTED_ON",
            enriched_factors=("asset_criticality", "pattern_history"),
            candidate_read="asset_data_movement_context",
            graph_query=(
                "MATCH (a:Alert {{alert_id: {alert_id}}}-[:DETECTED_ON]->(asset:Asset) "
                "OPTIONAL MATCH (a)-[:HAS_INDICATOR]->(ti:ThreatIndicator) "
                "OPTIONAL MATCH (a)-[:MEMBER_OF]->(campaign:Campaign) "
                "RETURN asset.asset_id AS asset_id, asset.criticality AS asset_criticality, ti.indicator AS indicator, campaign.campaign_id AS campaign_id LIMIT 5"
            ),
            vector_values=((1, 0.92), (3, 0.78)),
            specific_key_names=("exfil_asset_id", "exfil_asset_criticality", "exfil_indicator", "exfil_campaign_id"),
        )


class InsiderPattern(BaseInvestigationPattern):
    def __init__(self) -> None:
        super().__init__(
            category_name="insider_threat",
            pattern_name="insider_investigation",
            traversal="Alert -> User -> Campaign behavioral baseline",
            selected_edge="INVOLVES",
            enriched_factors=("time_anomaly", "pattern_history"),
            candidate_read="user_behavior_context",
            graph_query=(
                "MATCH (a:Alert {{alert_id: {alert_id}}}-[:INVOLVES]->(u:User) "
                "OPTIONAL MATCH (a)-[:MEMBER_OF]->(campaign:Campaign) "
                "RETURN u.user_id AS user_id, u.department AS department, campaign.campaign_id AS campaign_id LIMIT 5"
            ),
            vector_values=((4, 0.88), (3, 0.82)),
            specific_key_names=("insider_user_id", "insider_department", "insider_campaign_id"),
        )


class CloudInfraPattern(BaseInvestigationPattern):
    def __init__(self) -> None:
        super().__init__(
            category_name="cloud_infrastructure",
            pattern_name="cloud_infrastructure_investigation",
            traversal="Alert -> Asset -> AttackPattern cloud metadata",
            selected_edge="CLASSIFIED_AS",
            enriched_factors=("asset_criticality", "device_trust"),
            candidate_read="cloud_asset_context",
            graph_query=(
                "MATCH (a:Alert {{alert_id: {alert_id}}}-[:CLASSIFIED_AS]->(ap:AttackPattern) "
                "OPTIONAL MATCH (a)-[:DETECTED_ON]->(asset:Asset) "
                "RETURN ap.pattern_id AS pattern_id, ap.tactic AS tactic, asset.asset_id AS asset_id, asset.asset_type AS asset_type LIMIT 5"
            ),
            vector_values=((1, 0.82), (5, 0.30)),
            specific_key_names=("cloud_pattern_id", "cloud_tactic", "cloud_asset_id", "cloud_asset_type"),
        )


PATTERN_REGISTRY: dict[str, InvestigationPattern] = {
    pattern.category_name: pattern
    for pattern in [
        CredentialInvestigationPattern(),
        MalwareInvestigationPattern(),
        LateralMovementPattern(),
        ExfiltrationPattern(),
        InsiderPattern(),
        CloudInfraPattern(),
    ]
}


def build_default_investigation_patterns() -> dict[str, InvestigationPattern]:
    return dict(PATTERN_REGISTRY)



@dataclass(frozen=True)
class Stage1ConditionalPattern:
    """Template-specific planted multi-hop pattern for Stage 1 demo traces."""

    category_name: str
    pattern_name: str
    scenario_type: str
    selected_edge: str
    enriched_factors: tuple[str, ...]
    candidate_read: str
    graph_query: str = "ScenarioGraphStore decision_tree.hops"

    def supports(self, alert_context: dict[str, Any]) -> bool:
        if alert_context.get("scenario_type") == self.scenario_type:
            return True
        return bool(str(alert_context.get("alert_id") or alert_context.get("id") or "").strip())

    async def execute(self, alert_context: dict[str, Any], graph_store: Any) -> dict[str, Any]:
        scenario = getattr(graph_store, "scenario", None)
        if isinstance(scenario, dict):
            branches = scenario.get("correct_branches", {})
            first_step = min((int(k) for k in branches), default=1)
            branch_names = list(branches.get(str(first_step), []))
            branch_name = branch_names[0] if branch_names else self.candidate_read
            get_evidence = getattr(graph_store, "get_evidence", None)
            if callable(get_evidence):
                evidence = await _maybe_await(get_evidence(branch_name, first_step))
                if isinstance(evidence, dict):
                    out = dict(evidence)
                    out.setdefault("investigation_category", self.category_name)
                    out.setdefault("investigation_pattern", self.pattern_name)
                    out.setdefault("selected_edge", self.selected_edge)
                    out.setdefault("candidate_read", self.candidate_read)
                    out.setdefault("candidate_reads", [self.candidate_read])
                    out.setdefault("enriched_factors", list(self.enriched_factors))
                    out.setdefault("scenario_type", self.scenario_type)
                    return out
        return {
            "investigation_category": self.category_name,
            "investigation_pattern": self.pattern_name,
            "scenario_type": self.scenario_type,
            "selected_edge": self.selected_edge,
            "candidate_read": self.candidate_read,
            "candidate_reads": [self.candidate_read],
            "enriched_factors": list(self.enriched_factors),
            "factor_enriched": self.enriched_factors[0] if self.enriched_factors else "pattern_history",
            "factor_new_value": 0.5,
            "evidence_found": "No planted scenario evidence available.",
            "evidence_keys": (self.candidate_read, "factor_enriched", "factor_new_value"),
            "read_cost": 1.0,
        }

    def evidence_vector(self, evidence: dict[str, Any]) -> np.ndarray:
        vector = np.zeros(N_FACTORS, dtype=np.float64)
        factor = evidence.get("factor_enriched")
        factor_names = [
            "privileged_identity_context",
            "asset_criticality",
            "threat_intel_enrichment",
            "time_anomaly",
            "pattern_history",
            "device_trust",
        ]
        if factor in factor_names:
            vector[factor_names.index(str(factor))] = float(evidence.get("factor_new_value", 0.5))
        return cast(np.ndarray, vector)

    def evidence_keys(self) -> tuple[str, ...]:
        return (self.candidate_read, "factor_enriched", "factor_new_value", "evidence_found")


class CredentialLateralPattern(Stage1ConditionalPattern):
    def __init__(self) -> None:
        super().__init__("credential_access", "credential_lateral_multihop", "credential_lateral_compound", "HAS_AUTH_TRAIL", ("privileged_identity_context", "asset_criticality"), "auth_trail_path")


class InsiderCompromisedPattern(Stage1ConditionalPattern):
    def __init__(self) -> None:
        super().__init__("insider_threat", "insider_compromised_multihop", "insider_vs_compromised", "HAS_EMPLOYMENT_CONTEXT", ("pattern_history", "device_trust"), "hr_context_path")


class CloudMisconfigPattern(Stage1ConditionalPattern):
    def __init__(self) -> None:
        super().__init__("cloud_infrastructure", "cloud_misconfig_multihop", "cloud_misconfig_vs_attack", "COVERED_BY_CHANGE", ("asset_criticality", "device_trust"), "config_history_path")


class ServiceAccountPattern(Stage1ConditionalPattern):
    def __init__(self) -> None:
        super().__init__("credential_access", "service_account_multihop", "service_account_automated_vs_hijacked", "RUNS_JOB", ("privileged_identity_context", "pattern_history"), "job_schedule_path")


class MaintenanceWindowPattern(Stage1ConditionalPattern):
    def __init__(self) -> None:
        super().__init__("cloud_infrastructure", "maintenance_window_multihop", "maintenance_window_false_positive", "COVERED_BY_CHANGE", ("time_anomaly", "asset_criticality"), "maintenance_window_path")


class VulnerabilityPatchPattern(Stage1ConditionalPattern):
    def __init__(self) -> None:
        super().__init__("malware_execution", "vulnerability_patch_multihop", "cve_match_patch_status", "MATCHES_CVE", ("threat_intel_enrichment", "asset_criticality"), "cve_patch_path")


class PrivilegeChainPattern(Stage1ConditionalPattern):
    def __init__(self) -> None:
        super().__init__("lateral_movement", "privilege_chain_multihop", "privilege_escalation_chain", "NESTED_IN", ("privileged_identity_context", "asset_criticality"), "group_chain_path")


class CampaignCorrelationPattern(Stage1ConditionalPattern):
    def __init__(self) -> None:
        super().__init__("malware_execution", "campaign_correlation_multihop", "campaign_correlation", "MEMBER_OF", ("threat_intel_enrichment", "time_anomaly"), "campaign_path")


MULTIHOP_PATTERN_REGISTRY: dict[str, InvestigationPattern] = {
    pattern.pattern_name: pattern
    for pattern in [
        CredentialLateralPattern(),
        InsiderCompromisedPattern(),
        CloudMisconfigPattern(),
        ServiceAccountPattern(),
        MaintenanceWindowPattern(),
        VulnerabilityPatchPattern(),
        PrivilegeChainPattern(),
        CampaignCorrelationPattern(),
    ]
}


def build_multihop_investigation_patterns() -> dict[str, InvestigationPattern]:
    return dict(MULTIHOP_PATTERN_REGISTRY)
