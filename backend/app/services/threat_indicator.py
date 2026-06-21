"""
ThreatIndicatorService — persistent ThreatIndicator nodes with 24h TTL cache.

Distinct from the legacy :ThreatIntel nodes (written by connectors/pulsedive.py).
:ThreatIndicator nodes are managed exclusively by this service and support:
  - MERGE (idempotent upsert) with last_seen refresh
  - TTL cleanup (24h default)
  - Alert linkage via [:HAS_INDICATOR]
  - Grouped summary (by_type, by_severity)

CISO Q5 answer: "Why not Security Copilot?" → firm-specific threat graph + IOC count.

Reference: docs/project_status_and_plan_v3_part2.md Phase 7
"""

from __future__ import annotations

import logging
import uuid as _uuid
from datetime import datetime
from typing import Any, cast

log = logging.getLogger(__name__)


def _S(val) -> str:
    """Serialize a Python value to an AGE-safe inline Cypher literal."""
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    return "'" + str(val).replace("\\", "\\\\").replace("'", "\\'") + "'"


def _group_by(items: list, key: str) -> dict:
    """Count items grouped by a field value."""
    groups: dict = {}
    for item in items:
        k = item.get(key) or "unknown"
        groups[k] = groups.get(k, 0) + 1
    return groups


class ThreatIndicatorService:
    """Manages persistent ThreatIndicator nodes with TTL cache."""

    TTL_HOURS = 24

    @staticmethod
    async def upsert_indicator(
        indicator_type: str,
        indicator_value: str,
        source: str,
        severity: str,
        name: str,
        neo4j_service: Any,
    ) -> str:
        """MERGE a ThreatIndicator node. Idempotent — updates timestamp on re-insert.

        Returns the node ID (UUID).  Returns "" if the write fails.
        """
        if not indicator_value:
            log.warning(
                "[THREAT-INDICATOR] upsert skipped: indicator_value is empty or None "
                "(source=%r, type=%r)",
                source, indicator_type,
            )
            return ""
        try:
            now_s  = _S(int(datetime.utcnow().timestamp() * 1000))
            val_s  = _S(indicator_value)
            type_s = _S(indicator_type)
            src_s  = _S(source)
            sev_s  = _S(severity)
            name_s = _S(name)
            # Step A — try MATCH (update existing node)
            result = await neo4j_service.run_query(
                f"MATCH (ti:ThreatIndicator {{indicator: {val_s}, indicator_type: {type_s}}})"
                f" SET ti.last_seen = {now_s},"
                f"     ti.source = {src_s},"
                f"     ti.severity = {sev_s}"
                f" RETURN ti.id AS id"
            )
            if result:
                return cast(str, result[0]["id"])
            # Step B — CREATE (node does not exist yet)
            node_id = str(_uuid.uuid4())
            result = await neo4j_service.run_query(
                f"CREATE (ti:ThreatIndicator {{"
                f" id: {_S(node_id)},"
                f" indicator: {val_s},"
                f" indicator_type: {type_s},"
                f" name: {name_s},"
                f" source: {src_s},"
                f" severity: {sev_s},"
                f" created_at: {now_s},"
                f" last_seen: {now_s}"
                f"}}) RETURN ti.id AS id"
            )
            return cast(str, result[0]["id"]) if result else node_id
        except Exception as exc:
            log.warning(
                "[THREAT-INDICATOR] upsert failed indicator_value=%r: %s",
                indicator_value, exc,
            )
            return ""

    @staticmethod
    async def link_to_alert(
        indicator_value: str,
        indicator_type: str,
        alert_id: str,
        neo4j_service: Any,
    ) -> None:
        """Create [:HAS_INDICATOR] edge between Alert and ThreatIndicator."""
        try:
            val_s  = _S(indicator_value)
            type_s = _S(indicator_type)
            aid_s  = _S(alert_id)
            edge_check = await neo4j_service.run_query(
                f"MATCH (a:Alert {{alert_id: {aid_s}}})"
                f"-[:HAS_INDICATOR]->(ti:ThreatIndicator {{indicator: {val_s}, indicator_type: {type_s}}}) RETURN ti"
            )
            if not edge_check:
                await neo4j_service.run_query(
                    f"MATCH (a:Alert {{alert_id: {aid_s}}})"
                    f" MATCH (ti:ThreatIndicator {{indicator: {val_s}, indicator_type: {type_s}}})"
                    f" CREATE (a)-[:HAS_INDICATOR]->(ti)"
                )
        except Exception as exc:
            log.warning(
                "[THREAT-INDICATOR] link_to_alert failed indicator_value=%r alert=%r: %s",
                indicator_value, alert_id, exc,
            )

    @staticmethod
    async def get_indicators_for_alert(alert_id: str, neo4j_service: Any) -> list:
        """Get all ThreatIndicators linked to an alert via [:HAS_INDICATOR]."""
        try:
            result = await neo4j_service.run_query(
                f"MATCH (a:Alert {{alert_id: {_S(alert_id)}}})"
                f"-[:HAS_INDICATOR]->(ti:ThreatIndicator)"
                f" RETURN ti.id AS id, ti.name AS name,"
                f"        ti.indicator_type AS indicator_type,"
                f"        ti.indicator AS indicator, ti.source AS source,"
                f"        ti.severity AS severity, ti.last_seen AS last_seen"
            )
            return [dict(r) for r in result]
        except Exception as exc:
            log.warning(
                "[THREAT-INDICATOR] get_indicators_for_alert failed alert=%r: %s",
                alert_id, exc,
            )
            return []

    @staticmethod
    async def get_all_indicators(neo4j_service: Any) -> dict:
        """Get all ThreatIndicator nodes with TTL status and grouped counts.

        Returns
        -------
        {
            "total":       int,
            "indicators":  list[dict],
            "by_type":     {"ip": N, "domain": M, ...},
            "by_severity": {"critical": A, "high": B, ...},
        }
        """
        try:
            result = await neo4j_service.run_query(
                """
                MATCH (ti:ThreatIndicator)
                RETURN ti.id             AS id,
                       ti.name           AS name,
                       ti.indicator_type AS indicator_type,
                       ti.indicator      AS indicator,
                       ti.source         AS source,
                       ti.severity       AS severity,
                       ti.last_seen      AS last_seen,
                       ti.created_at     AS created_at
                ORDER BY ti.last_seen DESC
                """,
            )
            indicators = [dict(r) for r in result]
        except Exception as exc:
            log.warning("[THREAT-INDICATOR] get_all_indicators failed: %s", exc)
            indicators = []

        return {
            "total":       len(indicators),
            "indicators":  indicators,
            "by_type":     _group_by(indicators, "indicator_type"),
            "by_severity": _group_by(indicators, "severity"),
        }

    @staticmethod
    async def cleanup_expired(neo4j_service: Any) -> int:
        """Remove ThreatIndicator nodes older than TTL_HOURS. Returns count removed."""
        try:
            cutoff = int((datetime.utcnow().timestamp() - ThreatIndicatorService.TTL_HOURS * 3600) * 1000)
            result = await neo4j_service.run_query(
                f"MATCH (ti:ThreatIndicator)"
                f" WHERE ti.last_seen < {_S(cutoff)}"
                f" WITH ti DETACH DELETE ti"
                f" RETURN count(ti) AS removed"
            )
            return int(result[0]["removed"]) if result else 0
        except Exception as exc:
            log.warning("[THREAT-INDICATOR] cleanup_expired failed: %s", exc)
            return 0
