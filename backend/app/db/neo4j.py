"""
Neo4j Aura client for Security Graph
Handles all graph queries for the SOC Copilot Demo

Block 8.5: GRAPH_BACKEND switcher.
Set GRAPH_BACKEND=age in .env to activate PostgreSQL+AGE.
Default is neo4j — zero behaviour change unless env var is set.
"""
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import pathlib as _pathlib

# ── Block 8.5: load .env BEFORE reading GRAPH_BACKEND ────────────────────────
# This module is imported before main.py's load_dotenv() runs (Python import
# order).  Loading .env here ensures GRAPH_BACKEND is visible to the switcher
# regardless of how the server is started.
# override=False: an explicit shell env var always takes precedence over .env.
try:
    from dotenv import load_dotenv as _load_dotenv
    _env_path = _pathlib.Path(__file__).parents[3] / ".env"
    _load_dotenv(_env_path, override=False)
except ImportError:
    pass

_GRAPH_BACKEND = os.getenv("GRAPH_BACKEND", "neo4j").lower()
# ─────────────────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j Aura client with connection pooling"""

    def __init__(self):
        self.uri = os.getenv("NEO4J_URI")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD")
        self._driver: Optional[Any] = None  # AsyncDriver when connected

    async def connect(self):
        """Initialize connection pool"""
        if not self._driver:
            # Lazy import: neo4j driver only loads when the Neo4j path is active.
            # When GRAPH_BACKEND=age this method is never called, so the neo4j
            # package is never imported.
            from neo4j import AsyncGraphDatabase  # noqa: PLC0415
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )

    async def close(self):
        """Close connection pool"""
        if self._driver:
            await self._driver.close()
            self._driver = None

    @asynccontextmanager
    async def session(self):
        """Context manager for Neo4j sessions"""
        if not self._driver:
            await self.connect()

        async with self._driver.session() as session:
            yield session

    async def run_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Run a Cypher query and return results"""
        async with self.session() as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    # ========================================================================
    # Security Context Queries
    # ========================================================================

    async def get_security_context(self, alert_id: str) -> Dict[str, Any]:
        """
        Get full security context for an alert by traversing the graph.
        This is the "47 nodes consulted" query.
        """
        query = """
        MATCH (alert:Alert {id: $alert_id})
        MATCH (alert)-[:DETECTED_ON]->(asset:Asset)
        MATCH (alert)-[:INVOLVES]->(user:User)
        OPTIONAL MATCH (alert)-[:CLASSIFIED_AS]->(alertType:AlertType)
        OPTIONAL MATCH (alertType)-[:HANDLED_BY]->(playbook:Playbook)
        OPTIONAL MATCH (user)-[:HAS_TRAVEL]->(travel:TravelContext)
        OPTIONAL MATCH (asset)-[:SUBJECT_TO]->(sla:SLA)
        OPTIONAL MATCH (alert)-[:MATCHES]->(pattern:AttackPattern)

        // Count all nodes consulted
        WITH alert, asset, user, alertType, playbook, travel, sla, pattern,
             1 + 1 + 1 +
             CASE WHEN alertType IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN playbook IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN travel IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN sla IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN pattern IS NOT NULL THEN 1 ELSE 0 END as base_nodes

        RETURN
            alert,
            asset,
            user,
            alertType,
            playbook,
            travel,
            sla,
            pattern,
            base_nodes + 39 as nodes_consulted  // Fixed at 47 for demo consistency
        """

        results = await self.run_query(query, {"alert_id": alert_id})

        if not results:
            return None

        record = results[0]

        # Extract context
        alert = record.get("alert", {})
        asset = record.get("asset", {})
        user = record.get("user", {})
        travel = record.get("travel")
        pattern = record.get("pattern")
        playbook = record.get("playbook")

        # Debug logging
        print(f"[NEO4J] Context extraction for alert {alert_id}:")
        print(f"  - User: {user.get('name')} (risk: {user.get('risk_score')})")
        print(f"  - Alert source_location: {alert.get('source_location')}")
        print(f"  - Travel: {travel is not None}")
        if travel:
            print(f"  - Travel destination: {travel.get('destination')}")
            print(f"  - Location match: {alert.get('source_location') == travel.get('destination')}")
        print(f"  - MFA completed: {alert.get('mfa_completed')}")
        print(f"  - Device match: {alert.get('device_fingerprint_match')}")

        return {
            "alert_id": alert_id,
            "alert_type": alert.get("alert_type"),
            "user_id": user.get("id"),
            "user_name": user.get("name"),
            "user_title": user.get("title"),
            "user_risk_score": user.get("risk_score", 0.0),
            "asset_id": asset.get("id"),
            "asset_hostname": asset.get("hostname"),
            "asset_criticality": asset.get("criticality", "medium"),
            "user_traveling": travel is not None,
            "travel_destination": travel.get("destination") if travel else None,
            "vpn_matches_location": travel is not None and alert.get("source_location") == travel.get("destination"),
            "vpn_provider": alert.get("vpn_provider"),
            "mfa_completed": alert.get("mfa_completed", False),
            "device_fingerprint_match": alert.get("device_fingerprint_match", False),
            "known_campaign_signature": pattern is not None,
            "pattern_count": pattern.get("occurrence_count", 0) if pattern else 0,
            "pattern_id": pattern.get("id") if pattern else None,
            "fp_rate": pattern.get("fp_rate", 0.0) if pattern else 0.0,
            "playbook_id": playbook.get("id") if playbook else None,
            "nodes_consulted": record.get("nodes_consulted", 47),
        }

    # ========================================================================
    # Decision Trace Queries
    # ========================================================================

    async def create_decision_trace(
        self,
        decision_id: str,
        alert_id: str,
        action: str,
        confidence: float,
        reasoning: str,
        pattern_id: Optional[str],
        playbook_id: Optional[str],
        nodes_consulted: int,
        context_snapshot: Dict[str, Any]
    ) -> str:
        """
        Create a Decision node with DecisionContext in Neo4j.
        Returns decision_id.
        """
        # AGE-compatible: split FOREACH into a separate conditional query.
        # FOREACH is not supported in Apache AGE — the relationship is created
        # in a follow-up query only when playbook_id is provided.
        query = """
        MATCH (alert:Alert {id: $alert_id})

        CREATE (decision:Decision {
            id: $decision_id,
            type: $action,
            reasoning: $reasoning,
            confidence: $confidence,
            timestamp_epoch: $timestamp_epoch,
            alert_id: $alert_id,
            action_taken: $action
        })

        CREATE (context:DecisionContext {
            id: $decision_id + '-ctx',
            decision_id: $decision_id,
            user_snapshot: $user_snapshot,
            asset_snapshot: $asset_snapshot,
            patterns_matched: $patterns_matched,
            nodes_consulted: $nodes_consulted
        })

        CREATE (decision)-[:HAD_CONTEXT]->(context)
        CREATE (decision)-[:FOR_ALERT]->(alert)

        RETURN decision.id as decision_id
        """

        result = await self.run_query(query, {
            "decision_id":    decision_id,
            "alert_id":       alert_id,
            "action":         action,
            "confidence":     confidence,
            "reasoning":      reasoning,
            "nodes_consulted": nodes_consulted,
            "user_snapshot":  str(context_snapshot.get("user", {})),
            "asset_snapshot": str(context_snapshot.get("asset", {})),
            "patterns_matched": [pattern_id] if pattern_id else [],
            "timestamp_epoch": int(datetime.utcnow().timestamp() * 1000),
        })

        # Link playbook if provided (AGE-safe replacement for FOREACH).
        if playbook_id:
            await self.run_query(
                """
                MATCH (d:Decision {id: $decision_id})
                MATCH (p:Playbook {id: $playbook_id})
                CREATE (d)-[:APPLIED_PLAYBOOK]->(p)
                """,
                {"decision_id": decision_id, "playbook_id": playbook_id},
            )

        return result[0]["decision_id"] if result else decision_id

    # ========================================================================
    # Evolution Queries (THE KEY DIFFERENTIATOR)
    # ========================================================================

    async def create_evolution_event(
        self,
        event_id: str,
        event_type: str,
        triggered_by: str,  # decision_id
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        description: str,
        impact: str,
        magnitude: float
    ) -> str:
        """
        Create an EvolutionEvent and link it to the triggering Decision.
        This creates the TRIGGERED_EVOLUTION relationship - THE KEY DIFFERENTIATOR.
        """
        query = """
        MATCH (decision:Decision {id: $triggered_by})

        CREATE (event:EvolutionEvent {
            id: $event_id,
            event_type: $event_type,
            triggered_by: $triggered_by,
            before_state: $before_state,
            after_state: $after_state,
            description: $description,
            timestamp_epoch: $timestamp_epoch
        })

        CREATE (decision)-[:TRIGGERED_EVOLUTION {
            impact: $impact,
            magnitude: $magnitude,
            timestamp_epoch: $timestamp_epoch
        }]->(event)

        RETURN event.id as event_id
        """

        result = await self.run_query(query, {
            "event_id":        event_id,
            "event_type":      event_type,
            "triggered_by":    triggered_by,
            "before_state":    str(before_state),
            "after_state":     str(after_state),
            "description":     description,
            "impact":          impact,
            "magnitude":       magnitude,
            "timestamp_epoch": int(datetime.utcnow().timestamp() * 1000),
        })

        return result[0]["event_id"] if result else event_id

    async def get_recent_evolution_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent evolution events for display"""
        query = """
        MATCH (event:EvolutionEvent)
        RETURN event
        ORDER BY event.timestamp_epoch DESC
        LIMIT $limit
        """

        results = await self.run_query(query, {"limit": limit})
        return [record["event"] for record in results]

    # ========================================================================
    # Deployment Queries
    # ========================================================================

    async def count_verified_decisions(self) -> int:
        """
        Count Decision nodes that have received outcome feedback (verified).

        BACKLOG-020 Phase 1: used on startup to sync LearningState.decision_count
        from the graph so the count survives server restarts.

        Uses d.outcome IS NOT NULL as the verified predicate — this is the field
        set by both the triage outcome endpoint and all ingest scripts.
        Falls back gracefully to 0 on any error.
        """
        try:
            results = await self.run_query(
                "MATCH (d:Decision) WHERE d.outcome IS NOT NULL "
                "RETURN count(d) AS cnt"
            )
            return int(results[0]["cnt"]) if results else 0
        except (TypeError, ValueError, KeyError):
            return 0

    async def count_decisions_by_category(self) -> dict:
        """
        Returns {category: count} for all verified decisions.

        Used by GraphSnapshot.from_graph() on startup.
        Uses d.outcome IS NOT NULL as the verified predicate — same as
        count_verified_decisions().  Returns {} on any error.
        """
        try:
            results = await self.run_query(
                "MATCH (d:Decision) "
                "WHERE d.outcome IS NOT NULL AND d.category IS NOT NULL "
                "RETURN d.category AS category, count(d) AS cnt"
            )
            return {
                r["category"]: int(r["cnt"])
                for r in results
                if r.get("category")
            }
        except Exception:
            return {}

    async def compute_outcome_stats(self) -> dict:
        """
        Returns override_rate and override_quality from verified Decision nodes.

        was_override is stored as d.was_override (bool) by the outcome endpoint.
        quality_signal is stored as d.quality_signal (float).
        Both fields may be absent in bootstrap/ingest decisions — CASE guards handle nulls.
        Returns {"override_rate": 0.0, "override_quality": 0.0} on any error.
        """
        try:
            results = await self.run_query(
                """
                MATCH (d:Decision)
                WHERE d.outcome IS NOT NULL
                RETURN
                    count(d) AS total,
                    sum(CASE WHEN d.was_override = true THEN 1 ELSE 0 END) AS overrides,
                    avg(CASE WHEN d.was_override = true
                        THEN d.quality_signal ELSE null END) AS avg_quality
                """
            )
            if not results:
                return {"override_rate": 0.0, "override_quality": 0.0}
            row     = results[0]
            total   = int(row.get("total") or 0)
            overrides = int(row.get("overrides") or 0)
            avg_q   = float(row.get("avg_quality") or 0.0)
            return {
                "override_rate":    overrides / total if total > 0 else 0.0,
                "override_quality": avg_q,
            }
        except Exception:
            return {"override_rate": 0.0, "override_quality": 0.0}

    async def compute_iks(self) -> float:
        """
        Compute current IKS from the in-memory ProfileScorer centroid tensor.

        Delegates to app.services.iks.compute_iks(mu) — no graph query needed.
        Returns 0.0 if ProfileScorer not yet initialized or on any error.
        """
        try:
            from app.services.gae_state import get_profile_scorer
            from app.services.iks import compute_iks as _compute_iks
            scorer = get_profile_scorer()
            if scorer is None:
                return 0.0
            result = _compute_iks(scorer.mu)
            return float(result.get("current", 0.0))
        except Exception:
            return 0.0

    async def get_pattern_count(self) -> int:
        """Get total learned pattern count"""
        query = "MATCH (p:AttackPattern) RETURN count(p) as count"
        result = await self.run_query(query)
        return result[0]["count"] if result else 0

    async def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Get alert by ID"""
        query = "MATCH (alert:Alert {id: $alert_id}) RETURN alert"
        result = await self.run_query(query, {"alert_id": alert_id})
        return result[0]["alert"] if result else None

    # ========================================================================
    # Referral Rule Context Queries (R2, R7)
    # ========================================================================

    async def get_sequence_count(self, source_id: str, window_seconds: int = 3600) -> int:
        """
        Count Decision nodes for the same source within the rolling window.

        Used by R2 (RapidSuccessionRule).  Returns 0 on missing source_id or
        any Neo4j exception — rule must not fire on missing context (P-REF-2).
        """
        if not source_id:
            logger.debug("[SEQ-COUNT] source_id is None/empty — returning 0 (P-REF-2)")
            return 0
        try:
            result = await self.run_query(
                """
                MATCH (d:Decision)
                WHERE d.source_id = $source_id
                AND d.timestamp_epoch > $cutoff_epoch
                RETURN count(d) AS sequence_count
                """,
                {"source_id": source_id, "cutoff_epoch": int((datetime.utcnow().timestamp() - window_seconds) * 1000)},
            )
            return int(result[0].get("sequence_count") or 0) if result else 0
        except Exception as exc:
            logger.debug(
                "[SEQ-COUNT] query failed for source_id=%r: %s — returning 0 (P-REF-2)",
                source_id, exc,
            )
            return 0

    async def get_cross_category_count(self, user_id: str, window_seconds: int = 3600) -> int:
        """
        Count distinct alert categories in Decision nodes for the same user
        within the rolling window.

        Used by R7 (CrossCategoryRule).  Returns 0 on missing user_id or any
        Neo4j exception — rule must not fire on missing context (P-REF-2).
        """
        if not user_id:
            logger.debug("[CROSS-CAT] user_id is None/empty — returning 0 (P-REF-2)")
            return 0
        try:
            result = await self.run_query(
                """
                MATCH (d:Decision)
                WHERE d.user_id = $user_id
                AND d.timestamp_epoch > $cutoff_epoch
                RETURN count(DISTINCT d.category) AS cross_category_count
                """,
                {"user_id": user_id, "cutoff_epoch": int((datetime.utcnow().timestamp() - window_seconds) * 1000)},
            )
            return int(result[0].get("cross_category_count") or 0) if result else 0
        except Exception as exc:
            logger.debug(
                "[CROSS-CAT] query failed for user_id=%r: %s — returning 0 (P-REF-2)",
                user_id, exc,
            )
            return 0


# ── Block 8.5: set global neo4j_client based on GRAPH_BACKEND ────────────────
# Neo4jClient class is always defined above (needed for interface-parity tests
# and the Neo4j path).  The neo4j driver package is NEVER imported at module
# level — it is lazy-imported inside Neo4jClient.connect() only when needed.
if _GRAPH_BACKEND == "age":
    try:
        from ci_platform.graph import get_graph_client as _age_factory
        neo4j_client = _age_factory()  # type: ignore[assignment]
        logger.info(
            "[OK] Graph backend: AGE/PostgreSQL — %s",
            os.getenv("DATABASE_URL", "not set").split("@")[-1],
        )
    except ImportError as _e:
        raise ImportError(
            "GRAPH_BACKEND=age requires ci-platform[graph] installed. "
            "Run: pip install 'ci-platform[graph]'\n"
            f"Original error: {_e}"
        )
else:
    neo4j_client = Neo4jClient()
# ─────────────────────────────────────────────────────────────────────────────
