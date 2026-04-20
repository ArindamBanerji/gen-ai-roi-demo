"""
GraphExplorerService — safe graph exploration for the CISO demo (Phase 8).

Provides:
  - Read-only Cypher query validation + execution
  - Top-N nodes by connection count
  - Node neighbour traversal
  - Graph-wide node/relationship summary
  - Pre-built curated queries (Tab 1 Panel B)

CISO Q5: "Why not Security Copilot?" → firm-specific threat graph + IOC count.

Reference: docs/project_status_and_plan_v3_part2.md Phase 8
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pre-built queries — shown in the graph explorer panel
# ---------------------------------------------------------------------------

PREBUILT_QUERIES = {
    "top_risk_users": {
        "name":        "Top Risk Users",
        "description": "Users with highest risk scores",
        "cypher": (
            "MATCH (u:User) "
            "RETURN u.name AS name, u.department AS dept, u.risk_level AS risk "
            "ORDER BY risk DESC LIMIT 10"
        ),
    },
    "critical_assets": {
        "name":        "Critical Assets",
        "description": "Assets marked as critical or high criticality",
        "cypher": (
            "MATCH (a:Asset) "
            "WHERE a.criticality IN ['critical', 'high'] "
            "RETURN a.hostname AS hostname, a.asset_type AS type, "
            "a.criticality AS criticality, a.business_unit AS unit"
        ),
    },
    "threat_intel_matches": {
        "name":        "Threat Intel Matches",
        "description": "Alerts with linked threat intelligence indicators",
        "cypher": (
            "MATCH (a:Alert)-[:HAS_INDICATOR]->(ti:ThreatIndicator) "
            "RETURN a.alert_id AS alert_id, ti.indicator AS indicator, "
            "ti.severity AS severity, ti.indicator_type AS type "
            "ORDER BY ti.severity"
        ),
    },
    "recent_decisions": {
        "name":        "Recent Decisions",
        "description": "Latest triage decisions with outcomes",
        "cypher": (
            "MATCH (d:Decision) "
            "RETURN d.decision_id AS id, d.category AS category, d.action AS action, "
            "d.confidence AS confidence, d.auto_approved AS auto_approved "
            "ORDER BY d.timestamp_epoch DESC LIMIT 20"
        ),
    },
    "attack_patterns": {
        "name":        "Attack Pattern Library",
        "description": "Known attack patterns with false positive rates",
        "cypher": (
            "MATCH (p:AttackPattern) "
            "RETURN p.name AS pattern, p.fp_rate AS fp_rate, "
            "p.occurrence_count AS occurrences, p.confidence AS confidence "
            "ORDER BY p.occurrence_count DESC"
        ),
    },
}


# ---------------------------------------------------------------------------
# GraphExplorerService
# ---------------------------------------------------------------------------

class GraphExplorerService:
    """Safe graph exploration for the CISO demo."""

    # Whitelist of safe read-only Cypher prefixes
    SAFE_PREFIXES = ["MATCH", "RETURN", "WITH", "OPTIONAL MATCH", "CALL", "UNWIND"]

    # Mutation keywords that are never allowed
    BLOCKED_KEYWORDS = ["DELETE", "CREATE", "SET", "REMOVE", "MERGE", "DROP", "DETACH"]

    @staticmethod
    def validate_query(cypher: str) -> bool:
        """Only allow read-only queries.

        Returns True if the query starts with a safe prefix AND contains no
        blocked mutation keywords.
        """
        upper = cypher.strip().upper()

        if not any(upper.startswith(p) for p in GraphExplorerService.SAFE_PREFIXES):
            return False

        for kw in GraphExplorerService.BLOCKED_KEYWORDS:
            # Word-boundary match: "SET" matches " SET " but not "ASSET" or "RESET"
            if re.search(r'\b' + kw + r'\b', upper):
                return False

        return True

    @staticmethod
    async def run_safe_query(
        cypher: str,
        neo4j_service: Any,
        limit: int = 50,
    ) -> dict:
        """Run a validated read-only Cypher query.

        Returns
        -------
        {"rows": [...], "count": N, "query": str}
        or
        {"error": str, "query": str}
        """
        if not GraphExplorerService.validate_query(cypher):
            return {
                "error": "Query contains blocked keywords. Read-only queries only.",
                "query": cypher,
            }

        # Add LIMIT if not already present
        if "LIMIT" not in cypher.upper():
            cypher = cypher.rstrip().rstrip(";") + f" LIMIT {limit}"

        try:
            result = await neo4j_service.run_query(cypher)
            rows = [dict(r) for r in result]
            return {"rows": rows, "count": len(rows), "query": cypher}
        except Exception as exc:
            log.warning("[GRAPH-EXPLORER] run_safe_query failed: %s", exc)
            return {"error": str(exc), "query": cypher}

    @staticmethod
    async def get_top_nodes(
        neo4j_service: Any,
        node_type: Optional[str] = None,
        limit: int = 10,
    ) -> list:
        """Get top N nodes by connection count.

        Excludes :Decision and :Checkpoint nodes (internal bookkeeping).
        """
        try:
            if node_type:
                query = (
                    f"MATCH (n:{node_type})-[r]-() "
                    "RETURN n.id AS id, head(labels(n)) AS type,"
                    "coalesce(n.name, n.hostname, n.id) AS display_name, "
                    "count(r) AS connections "
                    "ORDER BY connections DESC LIMIT $limit"
                )
            else:
                query = (
                    "MATCH (n)-[r]-() "
                    "WHERE NOT n:Decision AND NOT n:Checkpoint "
                    "RETURN n.id AS id, head(labels(n)) AS type,"
                    "coalesce(n.name, n.hostname, n.id) AS display_name, "
                    "count(r) AS connections "
                    "ORDER BY connections DESC LIMIT $limit"
                )
            result = await neo4j_service.run_query(query, {"limit": limit})
            return [dict(r) for r in result]
        except Exception as exc:
            log.warning("[GRAPH-EXPLORER] get_top_nodes failed: %s", exc)
            return []

    @staticmethod
    async def get_node_neighbors(node_id: str, neo4j_service: Any) -> dict:
        """Get all neighbors of a specific node.

        Returns
        -------
        {"node_id": str, "neighbors": [...], "total": int}
        """
        try:
            result = await neo4j_service.run_query(
                """
                MATCH (n {id: $id})-[r]-(m)
                RETURN type(r)                                  AS relationship,
                       labels(m)[0]                             AS neighbor_type,
                       coalesce(m.name, m.hostname, m.id)       AS neighbor_name,
                       m.id                                     AS neighbor_id
                LIMIT 50
                """,
                {"id": node_id},
            )
            neighbors = [dict(r) for r in result]
        except Exception as exc:
            log.warning(
                "[GRAPH-EXPLORER] get_node_neighbors failed node_id=%r: %s", node_id, exc
            )
            neighbors = []

        return {
            "node_id":   node_id,
            "neighbors": neighbors,
            "total":     len(neighbors),
        }

    @staticmethod
    async def get_graph_summary(neo4j_service: Any) -> dict:
        """High-level graph statistics for the explorer header.

        Returns
        -------
        {
            "total_nodes":          int,
            "total_relationships":  int,
            "node_types":           {"Alert": N, "User": M, ...},
            "relationship_types":   {"DECIDED_ON": N, ...},
        }
        """
        try:
            counts = await neo4j_service.run_query(
                """
                MATCH (n)
                RETURN head(labels(n)) AS label, count(n) AS cnt
                ORDER BY cnt DESC
                """
            )
        except Exception as exc:
            log.warning("[GRAPH-EXPLORER] get_graph_summary node count failed: %s", exc)
            counts = []

        try:
            rel_counts = await neo4j_service.run_query(
                """
                MATCH ()-[r]->()
                RETURN type(r) AS type, count(r) AS cnt
                ORDER BY cnt DESC
                """
            )
        except Exception as exc:
            log.warning("[GRAPH-EXPLORER] get_graph_summary rel count failed: %s", exc)
            rel_counts = []

        total_nodes = sum(int(r.get("cnt") or 0) for r in counts)
        total_rels  = sum(int(r.get("cnt") or 0) for r in rel_counts)

        return {
            "total_nodes":         total_nodes,
            "total_relationships": total_rels,
            "node_types":          {r["label"]: r["cnt"] for r in counts if r.get("label")},
            "relationship_types":  {r["type"]:  r["cnt"] for r in rel_counts if r.get("type")},
        }

    @staticmethod
    def list_prebuilt_queries() -> list:
        """Return metadata for all pre-built queries (name + description only)."""
        return [
            {"key": key, "name": meta["name"], "description": meta["description"]}
            for key, meta in PREBUILT_QUERIES.items()
        ]

    @staticmethod
    async def run_prebuilt_query(query_name: str, neo4j_service: Any) -> dict:
        """Run a pre-built query by key name.

        Returns
        -------
        {"rows": [...], "count": N, "query": str}
        or
        {"error": "Unknown query name: ..."}
        """
        meta = PREBUILT_QUERIES.get(query_name)
        if meta is None:
            known = list(PREBUILT_QUERIES.keys())
            return {"error": f"Unknown query name: {query_name!r}. Known: {known}"}

        cypher = meta["cypher"]
        try:
            result = await neo4j_service.run_query(cypher)
            rows = [dict(r) for r in result]
            return {"rows": rows, "count": len(rows), "query": cypher}
        except Exception as exc:
            log.warning(
                "[GRAPH-EXPLORER] prebuilt query %r failed: %s", query_name, exc
            )
            return {"error": str(exc), "query": cypher}
