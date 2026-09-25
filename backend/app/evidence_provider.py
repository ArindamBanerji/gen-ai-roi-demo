"""SOC-specific VLD evidence provider.

The core VLD investigator is intentionally domain-neutral.  This module maps
SOC factor dimensions to evidence reads from the SOC graph and to the seeded
showcase evidence used by the demo beats.
"""
from __future__ import annotations

import asyncio
import inspect
from typing import Any, Optional


SOC_VLD_FACTOR_NAMES = [
    "privileged_identity_context",
    "asset_criticality",
    "threat_intel_enrichment",
    "pattern_history",
    "time_anomaly",
    "device_trust",
]

LEGACY_FACTOR_ALIASES = {
    "severity": "asset_criticality",
    "identity_confidence": "privileged_identity_context",
    "intel_corroboration": "threat_intel_enrichment",
    "timing_pattern": "time_anomaly",
    "historical_frequency": "pattern_history",
    "device_reputation": "device_trust",
}

_FACTOR_TO_DIMENSION = {name: idx for idx, name in enumerate(SOC_VLD_FACTOR_NAMES)}
_FACTOR_TO_DIMENSION.update(
    {alias: _FACTOR_TO_DIMENSION[target] for alias, target in LEGACY_FACTOR_ALIASES.items()}
)

_SHOWCASE_EVIDENCE: dict[str, dict[int, dict[str, Any]]] = {}


def normalize_factor_name(factor_name: str | None, dimension: int) -> str:
    """Return the live SOC factor name for a VLD dimension."""
    if factor_name in LEGACY_FACTOR_ALIASES:
        return LEGACY_FACTOR_ALIASES[factor_name]
    if factor_name in _FACTOR_TO_DIMENSION:
        return str(factor_name)
    if 0 <= int(dimension) < len(SOC_VLD_FACTOR_NAMES):
        return SOC_VLD_FACTOR_NAMES[int(dimension)]
    return str(factor_name or f"factor_{dimension}")


def register_showcase_evidence(alert_id: str, evidence_by_dimension: dict[int, dict[str, Any]]) -> None:
    """Register deterministic evidence for a showcase alert.

    The registry is process-local and idempotent.  Startup also attempts to
    write the same facts to AGE; the registry gives the synchronous VLD core a
    reliable protocol-compatible read path in tests and demos.
    """
    _SHOWCASE_EVIDENCE[str(alert_id)] = {
        int(dim): dict(payload) for dim, payload in evidence_by_dimension.items()
    }


def get_showcase_evidence(alert_id: str) -> dict[int, dict[str, Any]]:
    """Return registered showcase evidence for inspection/tests."""
    return {dim: dict(payload) for dim, payload in _SHOWCASE_EVIDENCE.get(str(alert_id), {}).items()}


class SOCEvidenceProvider:
    """EvidenceProvider implementation for SOC VLD investigations."""

    def __init__(self, graph_client: Any, alert_id: str):
        self.graph_client = graph_client
        self.alert_id = str(alert_id)

    def read_evidence(
        self, decision_id: str, dimension: int, factor_name: str
    ) -> Optional[dict[str, Any]]:
        dim = int(dimension)
        canonical = normalize_factor_name(factor_name, dim)

        seeded = _SHOWCASE_EVIDENCE.get(self.alert_id, {}).get(dim)
        if seeded is not None:
            return self._normalize_payload(seeded, canonical)

        graph_payload = self._read_from_graph_client(decision_id, dim, canonical)
        if graph_payload is not None:
            return graph_payload
        return None

    def _read_from_graph_client(
        self, decision_id: str, dimension: int, factor_name: str
    ) -> Optional[dict[str, Any]]:
        if self.graph_client is None:
            return None

        if hasattr(self.graph_client, "get_vld_evidence"):
            payload = self.graph_client.get_vld_evidence(self.alert_id, dimension, factor_name)
            if inspect.isawaitable(payload):
                return None
            return self._normalize_payload(payload, factor_name)

        evidence_map = getattr(self.graph_client, "vld_evidence", None)
        if isinstance(evidence_map, dict):
            payload = evidence_map.get((self.alert_id, dimension))
            if payload is None:
                payload = evidence_map.get(self.alert_id, {}).get(dimension) if isinstance(evidence_map.get(self.alert_id), dict) else None
            if payload is not None:
                return self._normalize_payload(payload, factor_name)

        if hasattr(self.graph_client, "run_query"):
            query = self._query_for_factor(factor_name)
            try:
                rows = self.graph_client.run_query(query)
                if inspect.iscoroutine(rows):
                    try:
                        asyncio.get_running_loop()
                        return None
                    except RuntimeError:
                        rows = asyncio.run(rows)
                elif inspect.isawaitable(rows):
                    return None
                if rows:
                    return self._row_to_evidence(rows[0], factor_name)
            except Exception:
                return None
        return None

    def _query_for_factor(self, factor_name: str) -> str:
        alert = self._cypher_string(self.alert_id)
        if factor_name == "privileged_identity_context":
            return (
                f"MATCH (a:Alert {{alert_id: {alert}}})-[:INVOLVES|AFFECTS]->(u:User) "
                "OPTIONAL MATCH (a)-[:MEMBER_OF]->(c:Campaign) "
                "RETURN coalesce(c.confidence, 0.35) AS value, 0.92 AS confidence, 'identity_graph' AS source"
            )
        if factor_name == "asset_criticality":
            return (
                f"MATCH (a:Alert {{alert_id: {alert}}})-[:DETECTED_ON|TARGETS]->(asset:Asset) "
                "RETURN coalesce(asset.criticality_score, asset.criticality, 0.6) AS value, 0.80 AS confidence, 'asset_inventory' AS source"
            )
        if factor_name == "threat_intel_enrichment":
            return (
                f"MATCH (a:Alert {{alert_id: {alert}}})-[:HAS_INDICATOR|MATCHES]->(ti:ThreatIndicator) "
                "RETURN coalesce(ti.match_strength, ti.severity, 0.75) AS value, 0.88 AS confidence, 'threat_intel' AS source"
            )
        if factor_name == "pattern_history":
            return (
                f"MATCH (a:Alert {{alert_id: {alert}}}) "
                "RETURN coalesce(a.similar_alerts_30d, a.history_score, 0.0) AS value, 0.85 AS confidence, 'historical_db' AS source"
            )
        if factor_name == "time_anomaly":
            return (
                f"MATCH (a:Alert {{alert_id: {alert}}}) "
                "RETURN coalesce(a.time_anomaly, a.timing_score, 0.5) AS value, 0.75 AS confidence, 'timing_analysis' AS source"
            )
        if factor_name == "device_trust":
            return (
                f"MATCH (a:Alert {{alert_id: {alert}}})-[:DETECTED_ON|TARGETS]->(asset:Asset) "
                "RETURN coalesce(asset.reputation_score, asset.device_trust, 0.5) AS value, 0.80 AS confidence, 'asset_inventory' AS source"
            )
        return f"MATCH (a:Alert {{alert_id: {alert}}}) RETURN null AS value"

    def _row_to_evidence(self, row: Any, factor_name: str) -> Optional[dict[str, Any]]:
        if not isinstance(row, dict):
            return None
        value = row.get("value")
        if value is None:
            return None
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return None
        return {
            "value": max(0.0, min(1.0, numeric_value)),
            "confidence": max(0.0, min(1.0, float(row.get("confidence", 0.8)))),
            "source": str(row.get("source") or self._default_source(factor_name)),
        }

    def _normalize_payload(self, payload: Any, factor_name: str) -> Optional[dict[str, Any]]:
        if not isinstance(payload, dict):
            return None
        value = payload.get("value")
        if value is None:
            return None
        try:
            numeric_value = float(value)
            confidence = float(payload.get("confidence", 0.8))
        except (TypeError, ValueError):
            return None
        return {
            "value": max(0.0, min(1.0, numeric_value)),
            "confidence": max(0.0, min(1.0, confidence)),
            "source": str(payload.get("source") or self._default_source(factor_name)),
        }

    def _default_source(self, factor_name: str) -> str:
        return {
            "privileged_identity_context": "identity_graph",
            "asset_criticality": "asset_inventory",
            "threat_intel_enrichment": "threat_intel",
            "pattern_history": "historical_db",
            "time_anomaly": "timing_analysis",
            "device_trust": "asset_inventory",
        }.get(factor_name, "soc_graph")

    def _cypher_string(self, value: str) -> str:
        return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"
