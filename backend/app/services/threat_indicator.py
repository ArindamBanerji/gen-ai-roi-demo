"""
ThreatIndicatorService — persistent ThreatIndicator nodes with 24h TTL cache.

Distinct from the legacy :ThreatIntel nodes (written by connectors/pulsedive.py).
:ThreatIndicator nodes are managed exclusively by this service and support:
  - MERGE (idempotent upsert) with last_seen refresh
  - TTL cleanup (24h default)
  - Alert linkage via [:ASSOCIATED_WITH]
  - Grouped summary (by_type, by_severity)

CISO Q5 answer: "Why not Security Copilot?" → firm-specific threat graph + IOC count.

Reference: docs/project_status_and_plan_v3_part2.md Phase 7
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

log = logging.getLogger(__name__)


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
        ioc_type: str,
        ioc_value: str,
        source: str,
        severity: str,
        name: str,
        neo4j_service: Any,
    ) -> str:
        """MERGE a ThreatIndicator node. Idempotent — updates timestamp on re-insert.

        Returns the node ID (UUID).  Returns "" if the write fails.
        """
        if not ioc_value:
            log.warning(
                "[THREAT-INDICATOR] upsert skipped: ioc_value is empty or None "
                "(source=%r, type=%r)",
                source, ioc_type,
            )
            return ""
        try:
            params = {
                "ioc_value":  ioc_value,
                "ioc_type":   ioc_type,
                "source":     source,
                "severity":   severity,
                "name":       name,
                "now_epoch":  int(datetime.utcnow().timestamp() * 1000),
            }
            # Step A — try MATCH (update existing node)
            result = await neo4j_service.run_query(
                """
                MATCH (ti:ThreatIndicator {ioc_value: $ioc_value, ioc_type: $ioc_type})
                SET ti.last_seen_epoch = $now_epoch,
                    ti.source          = $source,
                    ti.severity        = $severity
                RETURN ti.id AS id
                """,
                params,
            )
            if result:
                return result[0]["id"]
            # Step B — CREATE (node does not exist yet)
            result = await neo4j_service.run_query(
                """
                CREATE (ti:ThreatIndicator {
                    id: randomUUID(),
                    ioc_value: $ioc_value,
                    ioc_type: $ioc_type,
                    name: $name,
                    source: $source,
                    severity: $severity,
                    created_at_epoch: $now_epoch,
                    last_seen_epoch: $now_epoch
                })
                RETURN ti.id AS id
                """,
                params,
            )
            return result[0]["id"] if result else ""
        except Exception as exc:
            log.warning(
                "[THREAT-INDICATOR] upsert failed ioc_value=%r: %s", ioc_value, exc
            )
            return ""

    @staticmethod
    async def link_to_alert(
        ioc_value: str,
        ioc_type: str,
        alert_id: str,
        neo4j_service: Any,
    ) -> None:
        """Create [:ASSOCIATED_WITH] edge between ThreatIndicator and Alert."""
        try:
            await neo4j_service.run_query(
                """
                MATCH (ti:ThreatIndicator {ioc_value: $ioc_value, ioc_type: $ioc_type})
                MATCH (a:Alert {alert_id: $alert_id})
                MERGE (ti)-[:ASSOCIATED_WITH]->(a)
                """,
                {"ioc_value": ioc_value, "ioc_type": ioc_type, "alert_id": alert_id},
            )
        except Exception as exc:
            log.warning(
                "[THREAT-INDICATOR] link_to_alert failed ioc_value=%r alert=%r: %s",
                ioc_value, alert_id, exc,
            )

    @staticmethod
    async def get_indicators_for_alert(alert_id: str, neo4j_service: Any) -> list:
        """Get all ThreatIndicators linked to an alert via [:ASSOCIATED_WITH]."""
        try:
            result = await neo4j_service.run_query(
                """
                MATCH (ti:ThreatIndicator)-[:ASSOCIATED_WITH]->(a:Alert {alert_id: $id})
                RETURN ti.id        AS id,
                       ti.name      AS name,
                       ti.ioc_type  AS ioc_type,
                       ti.ioc_value AS ioc_value,
                       ti.source    AS source,
                       ti.severity  AS severity,
                       ti.last_seen AS last_seen
                """,
                {"id": alert_id},
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
                RETURN ti.id         AS id,
                       ti.name       AS name,
                       ti.ioc_type   AS ioc_type,
                       ti.ioc_value  AS ioc_value,
                       ti.source     AS source,
                       ti.severity   AS severity,
                       ti.last_seen  AS last_seen,
                       ti.created_at AS created_at
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
            "by_type":     _group_by(indicators, "ioc_type"),
            "by_severity": _group_by(indicators, "severity"),
        }

    @staticmethod
    async def cleanup_expired(neo4j_service: Any) -> int:
        """Remove ThreatIndicator nodes older than TTL_HOURS. Returns count removed."""
        try:
            result = await neo4j_service.run_query(
                """
                MATCH (ti:ThreatIndicator)
                WHERE ti.last_seen_epoch < $cutoff_epoch
                WITH ti
                DETACH DELETE ti
                RETURN count(ti) AS removed
                """,
                {"cutoff_epoch": int((datetime.utcnow().timestamp() - ThreatIndicatorService.TTL_HOURS * 3600) * 1000)},
            )
            return int(result[0]["removed"]) if result else 0
        except Exception as exc:
            log.warning("[THREAT-INDICATOR] cleanup_expired failed: %s", exc)
            return 0
