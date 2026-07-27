"""FEATURE-07 Cross-Graph Discovery service.

Read-only SOC graph discovery over AGE-compatible Cypher. Discovery windows use
the production graph clock (max graph timestamp), not host wall-clock time.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional, cast

import numpy as np

from app.domains.soc.config import SOC_CATEGORIES, SOC_PROFILE_CENTROIDS
from app.graph_schema import _S


log = logging.getLogger(__name__)

DAY_MS = 86400 * 1000


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clamp_score(score: Any) -> float:
    try:
        value = float(score)
    except (TypeError, ValueError):
        return 0.0
    if not np.isfinite(value):
        return 0.0
    return float(max(0.0, min(1.0, value)))


def _severity_for_score(score: Any) -> str:
    score = _clamp_score(score)
    if score >= 0.7:
        return DiscoverySeverity.HIGH.value
    if score >= 0.4:
        return DiscoverySeverity.MEDIUM.value
    return DiscoverySeverity.LOW.value


def _parse_collected(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def _parse_factor_vector(value: Any) -> Optional[np.ndarray]:
    raw = value
    if isinstance(value, str):
        if not value.strip():
            return None
        try:
            raw = json.loads(value)
        except json.JSONDecodeError:
            return None
    if not isinstance(raw, (list, tuple, np.ndarray)):
        return None
    try:
        vector = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError):
        return None
    if vector.shape != (SOC_PROFILE_CENTROIDS.shape[2],):
        return None
    if not np.all(np.isfinite(vector)):
        return None
    return vector


class DiscoveryType(str, Enum):
    SHARED_ENTITY = "shared_entity"
    PATTERN_CONVERGENCE = "pattern_convergence"
    TEMPORAL_VELOCITY = "temporal_velocity"
    CROSS_FACTOR_MISROUTE = "cross_factor_misroute"
    CROSS_FACTOR_NOVEL = "cross_factor_novel"


class DiscoverySeverity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Discovery:
    discovery_id: str
    domain: str
    source_domains: list[str]
    type: str
    severity: str
    title: str
    description: str
    score: float
    discovered_at: str
    involved_entity_ids: list[str] = field(default_factory=list)
    involved_alert_ids: list[str] = field(default_factory=list)
    involved_decision_ids: list[str] = field(default_factory=list)
    threat_indicator_ids: list[str] = field(default_factory=list)
    entity_summary: str = ""
    category_summary: str = ""
    temporal_summary: str = ""
    factor_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        score = _clamp_score(self.score)
        return {
            "discovery_id": self.discovery_id,
            "domain": self.domain,
            "source_domains": list(self.source_domains),
            "type": self.type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "score": round(score, 4),
            "discovered_at": self.discovered_at,
            "involved_entity_ids": list(self.involved_entity_ids),
            "involved_alert_ids": list(self.involved_alert_ids),
            "involved_decision_ids": list(self.involved_decision_ids),
            "threat_indicator_ids": list(self.threat_indicator_ids),
            "entity_summary": self.entity_summary,
            "category_summary": self.category_summary,
            "temporal_summary": self.temporal_summary,
            "factor_summary": self.factor_summary,
        }


class DiscoveryService:
    DEFAULT_LOOKBACK_DAYS = 30
    DEFAULT_RECENT_DAYS = 7
    DEFAULT_DOMAIN = "soc"
    SUPPORTED_DOMAINS = {"soc"}
    CACHE_TTL_SECONDS = 60
    MIN_ALERTS_SHARED = 3
    MIN_CATEGORIES_SHARED = 2
    MIN_CONFIDENCE_CONVERGENCE = 0.70
    CONVERGENCE_LIMIT = 200
    MIN_VELOCITY_RATIO = 2.5
    MIN_RECENT_COUNT = 2
    ANOMALY_THRESHOLD = 0.65

    def __init__(
        self,
        ttl_seconds: int = CACHE_TTL_SECONDS,
        time_fn: Callable[[], float] = time.time,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.time_fn = time_fn
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_time: dict[str, float] = {}

    def validate_domain(self, domain: str) -> str:
        domain = domain or self.DEFAULT_DOMAIN
        if domain not in self.SUPPORTED_DOMAINS:
            raise ValueError(f"Unsupported discovery domain: {domain}")
        return domain

    async def _run_algorithm(
        self, coro: Any, name: str, timeout: float = 3.0
    ) -> tuple[Any, Optional[str]]:
        """Run an algorithm coroutine with timeout. Returns (result, error_msg)."""
        try:
            result = await asyncio.wait_for(coro, timeout=timeout)
            return result, None
        except asyncio.TimeoutError:
            log.warning("Discovery '%s' timed out after %.1fs", name, timeout)
            return [], f"{name} timed out"
        except Exception as e:
            log.warning("Discovery '%s' failed: %s", name, e)
            return [], f"{name}: {str(e)}"

    async def _get_as_of_epoch_ms(self, neo4j_client: Any) -> Optional[int]:
        queries = [
            (
                "max_alert_epoch",
                """
                MATCH (a:Alert)
                WHERE a.timestamp_epoch IS NOT NULL
                RETURN max(a.timestamp_epoch) AS max_alert_epoch
                """,
            ),
        ]
        values: list[int] = []
        for key, query in queries:
            try:
                rows = await neo4j_client.run_query(query)
            except Exception as exc:
                log.warning("Discovery graph clock query failed: %s", exc)
                continue
            if not rows:
                continue
            parsed = self._parse_epoch(rows[0].get(key))
            if parsed is not None:
                values.append(parsed)
        return max(values) if values else None

    @staticmethod
    def _parse_epoch(value: Any) -> Optional[int]:
        if isinstance(value, dict):
            for nested in value.values():
                parsed = DiscoveryService._parse_epoch(nested)
                if parsed is not None:
                    return parsed
            return None
        if isinstance(value, (list, tuple)):
            for nested in value:
                parsed = DiscoveryService._parse_epoch(nested)
                if parsed is not None:
                    return parsed
            return None
        try:
            parsed_float = float(value)
        except (TypeError, ValueError):
            return None
        if not np.isfinite(parsed_float):
            return None
        return int(parsed_float)

    def get_discoveries(self, domain: str = DEFAULT_DOMAIN) -> Optional[dict[str, Any]]:
        domain = self.validate_domain(domain)
        envelope = self._cache.get(domain)
        cache_time = self._cache_time.get(domain)
        if envelope is None or cache_time is None:
            return None
        if self.time_fn() - cache_time > self.ttl_seconds:
            return None
        cached = self._copy_envelope(envelope)
        cached["cache"] = {
            **cached.get("cache", {}),
            "hit": True,
            "stale": False,
            "ttl_seconds": self.ttl_seconds,
        }
        return cached

    async def refresh(self, domain: str, neo4j_client: Any) -> dict[str, Any]:
        domain = self.validate_domain(domain)
        generated_at = _now_iso()
        stale_cache = self._cache.get(domain)
        errors: list[str] = []
        as_of_epoch_ms: Optional[int] = None
        discoveries: list[Discovery] = []
        algorithm_failures = 0

        try:
            as_of_epoch_ms = await self._get_as_of_epoch_ms(neo4j_client)
        except Exception as exc:
            errors.append(f"graph_clock: {exc}")
            log.warning("Discovery graph clock failed: %s", exc)

        parsed_decisions: list[dict[str, Any]] = []
        if as_of_epoch_ms is None:
            errors.append("No graph timestamps available")
            if stale_cache is not None:
                return self._stale_envelope(stale_cache, errors)
        else:
            recent_cutoff = as_of_epoch_ms - self.DEFAULT_RECENT_DAYS * DAY_MS
            baseline_cutoff = as_of_epoch_ms - self.DEFAULT_LOOKBACK_DAYS * DAY_MS

            t0 = time.monotonic()

            t1 = time.monotonic()
            shared, err1 = await self._run_algorithm(
                self._shared_entity_discovery(neo4j_client, baseline_cutoff, as_of_epoch_ms),
                "shared_entity",
            )
            t_shared = time.monotonic() - t1
            if err1:
                algorithm_failures += 1
                errors.append(err1)
            else:
                discoveries.extend(shared)

            t2 = time.monotonic()
            conv_result, err2 = await self._run_algorithm(
                self._pattern_convergence_discovery(neo4j_client, baseline_cutoff),
                "pattern_convergence",
            )
            t_conv = time.monotonic() - t2
            if err2:
                algorithm_failures += 1
                errors.append(err2)
            else:
                new_conv_discoveries, parsed_decisions = conv_result
                discoveries.extend(new_conv_discoveries)

            t3 = time.monotonic()
            vel, err3 = await self._run_algorithm(
                self._temporal_velocity_discovery(neo4j_client, recent_cutoff, baseline_cutoff),
                "temporal_velocity",
            )
            t_vel = time.monotonic() - t3
            if err3:
                algorithm_failures += 1
                errors.append(err3)
            else:
                discoveries.extend(vel)

            t4 = time.monotonic()
            try:
                discoveries.extend(
                    self._cross_factor_anomaly_discovery(parsed_decisions)
                )
            except Exception as exc:
                algorithm_failures += 1
                errors.append(f"{DiscoveryType.CROSS_FACTOR_MISROUTE.value}: {exc}")
                log.warning("Cross-factor discovery failed: %s", exc)
            t_anom = time.monotonic() - t4

            total = time.monotonic() - t0
            log.info(
                "Discovery refresh: %.2fs (shared=%.2fs conv=%.2fs vel=%.2fs anom=%.2fs) %d discoveries",
                total, t_shared, t_conv, t_vel, t_anom, len(discoveries),
            )
            if total > 5.0:
                log.warning("Discovery refresh exceeded 5s target: %.2fs", total)

        if stale_cache is not None and as_of_epoch_ms is not None and algorithm_failures >= 4:
            return self._stale_envelope(stale_cache, errors)

        envelope = self._build_envelope(
            domain=domain,
            generated_at=generated_at,
            as_of_epoch_ms=as_of_epoch_ms,
            discoveries=discoveries,
            errors=errors,
            hit=False,
            stale=False,
        )
        self._cache[domain] = self._copy_envelope(envelope)
        self._cache_time[domain] = self.time_fn()
        return envelope

    async def get_summary(self, domain: str, neo4j_client: Any) -> dict[str, Any]:
        envelope = self.get_discoveries(domain)
        if envelope is None:
            envelope = await self.refresh(domain, neo4j_client)
        discoveries = envelope.get("discoveries", [])
        counts = {sev.value: 0 for sev in DiscoverySeverity}
        for discovery in discoveries:
            severity = discovery.get("severity")
            if severity in counts:
                counts[severity] += 1
        return {
            "domain": envelope["domain"],
            "source_domains": envelope["source_domains"],
            "total": len(discoveries),
            "high_count": counts[DiscoverySeverity.HIGH.value],
            "medium_count": counts[DiscoverySeverity.MEDIUM.value],
            "low_count": counts[DiscoverySeverity.LOW.value],
            "top_discoveries": discoveries[:5],
            "cache": envelope["cache"],
            "errors": envelope.get("errors", []),
        }

    def _build_envelope(
        self,
        domain: str,
        generated_at: str,
        as_of_epoch_ms: Optional[int],
        discoveries: list[Discovery],
        errors: list[str],
        hit: bool,
        stale: bool,
    ) -> dict[str, Any]:
        by_id: dict[str, Discovery] = {}
        for discovery in discoveries:
            discovery.score = _clamp_score(discovery.score)
            discovery.severity = _severity_for_score(discovery.score)
            by_id.setdefault(discovery.discovery_id, discovery)
        payload = [d.to_dict() for d in by_id.values()]
        payload.sort(key=lambda d: d["score"], reverse=True)
        return {
            "domain": domain,
            "source_domains": [domain],
            "generated_at": generated_at,
            "as_of_epoch_ms": as_of_epoch_ms,
            "cache": {
                "hit": hit,
                "stale": stale,
                "ttl_seconds": self.ttl_seconds,
            },
            "discoveries": payload,
            "total": len(payload),
            "errors": list(errors),
        }

    @staticmethod
    def _copy_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(json.dumps(envelope)))

    def _stale_envelope(
        self,
        stale_cache: dict[str, Any],
        errors: list[str],
    ) -> dict[str, Any]:
        stale = self._copy_envelope(stale_cache)
        stale["cache"] = {
            **stale.get("cache", {}),
            "hit": False,
            "stale": True,
            "ttl_seconds": self.ttl_seconds,
        }
        stale["errors"] = list(errors)
        return stale

    def _batch_parse_vectors(
        self, rows: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], np.ndarray]:
        """Parse factor vectors from rows into a (N, 6) numpy matrix.

        Returns (valid_rows, matrix). valid_rows contains only rows with
        parseable finite vectors; matrix[i] is the vector for valid_rows[i].
        """
        valid: list[dict[str, Any]] = []
        vecs: list[np.ndarray] = []
        for row in rows:
            v = _parse_factor_vector(row.get("factor_vector"))
            if v is not None and len(v) == 6 and np.all(np.isfinite(v)):
                valid.append(row)
                vecs.append(v)
        if not vecs:
            return [], np.empty((0, 6), dtype=np.float64)
        return valid, np.vstack(vecs)

    async def _shared_entity_discovery(
        self,
        neo4j_client: Any,
        baseline_cutoff: int,
        as_of_epoch_ms: int,
    ) -> list[Discovery]:
        """Algorithm 1: Shared Entity.

        Uses two aggregate queries + at most two batch threat-intel queries
        (one for users, one for assets). Total graph queries <= 4.
        """
        user_agg_query = f"""
        MATCH (a:Alert)-[:INVOLVES]->(u:User)
        WHERE a.timestamp_epoch >= {baseline_cutoff}
          AND a.timestamp_epoch <= {as_of_epoch_ms}
        RETURN u.user_id AS entity_id,
               u.name AS entity_name,
               collect(a.alert_id) AS alert_ids_json,
               collect(a.category) AS categories_json,
               collect(a.timestamp_epoch) AS timestamps_json,
               count(a) AS cnt
        ORDER BY cnt DESC
        LIMIT 50
        """
        asset_agg_query = f"""
        MATCH (a:Alert)-[:DETECTED_ON]->(asset:Asset)
        WHERE a.timestamp_epoch >= {baseline_cutoff}
          AND a.timestamp_epoch <= {as_of_epoch_ms}
        RETURN asset.asset_id AS entity_id,
               asset.hostname AS entity_name,
               collect(a.alert_id) AS alert_ids_json,
               collect(a.category) AS categories_json,
               collect(a.timestamp_epoch) AS timestamps_json,
               count(a) AS cnt
        ORDER BY cnt DESC
        LIMIT 50
        """
        user_ti_batch_query = f"""
        MATCH (a:Alert)-[:INVOLVES]->(u:User)
        MATCH (a)-[:HAS_INDICATOR]->(ti:ThreatIndicator)
        WHERE a.timestamp_epoch >= {baseline_cutoff}
          AND a.timestamp_epoch <= {as_of_epoch_ms}
        RETURN u.user_id AS entity_id,
               ti.indicator AS indicator,
               ti.severity AS indicator_severity,
               a.alert_id AS alert_id
        LIMIT 500
        """
        asset_ti_batch_query = f"""
        MATCH (a:Alert)-[:DETECTED_ON]->(asset:Asset)
        MATCH (a)-[:HAS_INDICATOR]->(ti:ThreatIndicator)
        WHERE a.timestamp_epoch >= {baseline_cutoff}
          AND a.timestamp_epoch <= {as_of_epoch_ms}
        RETURN asset.asset_id AS entity_id,
               ti.indicator AS indicator,
               ti.severity AS indicator_severity,
               a.alert_id AS alert_id
        LIMIT 500
        """

        # Phase 1: aggregate queries
        user_rows = await neo4j_client.run_query(user_agg_query)
        asset_rows = await neo4j_client.run_query(asset_agg_query)

        # Pre-filter to qualifying entities before fetching TI
        def _qualify(rows: list[dict[str, Any]]) -> list[tuple]:
            result: list[tuple[Any, ...]] = []
            for row in rows or []:
                filtered = self._aligned_alert_rows(row, baseline_cutoff, as_of_epoch_ms)
                alert_ids = [item["alert_id"] for item in filtered]
                categories = sorted({item["category"] for item in filtered if item["category"]})
                if (
                    len(alert_ids) < self.MIN_ALERTS_SHARED
                    or len(categories) < self.MIN_CATEGORIES_SHARED
                ):
                    continue
                entity_id = str(row.get("entity_id") or "")
                if not entity_id:
                    continue
                result.append((row, filtered, alert_ids, categories, entity_id))
            return result

        qualifying_users = _qualify(user_rows)
        qualifying_assets = _qualify(asset_rows)

        # Phase 2: batch threat-intel (one query per entity type, only if needed)
        ti_by_user: dict[str, list[dict[str, Any]]] = {}
        if qualifying_users:
            ti_user_rows = await neo4j_client.run_query(user_ti_batch_query)
            for r in ti_user_rows or []:
                eid = str(r.get("entity_id") or "")
                if eid:
                    ti_by_user.setdefault(eid, []).append(r)

        ti_by_asset: dict[str, list[dict[str, Any]]] = {}
        if qualifying_assets:
            ti_asset_rows = await neo4j_client.run_query(asset_ti_batch_query)
            for r in ti_asset_rows or []:
                eid = str(r.get("entity_id") or "")
                if eid:
                    ti_by_asset.setdefault(eid, []).append(r)

        # Phase 3: build discoveries using TI lookup
        discoveries: list[Discovery] = []
        for (entity_type, qualifying, ti_lookup) in [
            ("User", qualifying_users, ti_by_user),
            ("Asset", qualifying_assets, ti_by_asset),
        ]:
            for row, filtered, alert_ids, categories, entity_id in qualifying:
                entity_ti = ti_lookup.get(entity_id, [])
                indicators = sorted({
                    str(r.get("indicator"))
                    for r in entity_ti
                    if r.get("indicator")
                })
                score = self._shared_entity_score(
                    len(alert_ids), len(categories), filtered, bool(indicators)
                )
                entity_name = str(row.get("entity_name") or entity_id)
                discoveries.append(
                    Discovery(
                        discovery_id=self._stable_id(
                            DiscoveryType.SHARED_ENTITY.value, entity_type, entity_id
                        ),
                        domain=self.DEFAULT_DOMAIN,
                        source_domains=[self.DEFAULT_DOMAIN],
                        type=DiscoveryType.SHARED_ENTITY.value,
                        severity=_severity_for_score(score),
                        title=f"Shared {entity_type.lower()} spans SOC categories",
                        description=(
                            f"{entity_name} appears in {len(alert_ids)} alerts "
                            f"across {len(categories)} categories."
                        ),
                        score=score,
                        discovered_at=_now_iso(),
                        involved_entity_ids=[entity_id],
                        involved_alert_ids=alert_ids,
                        threat_indicator_ids=indicators,
                        entity_summary=f"{entity_type} {entity_name}",
                        category_summary=", ".join(categories),
                        temporal_summary=(
                            f"{len(alert_ids)} alerts in the current 30-day graph window"
                        ),
                    )
                )
        return discoveries

    @staticmethod
    def _aligned_alert_rows(
        row: dict[str, Any],
        baseline_cutoff: int,
        as_of_epoch_ms: int,
    ) -> list[dict[str, Any]]:
        alert_ids = _parse_collected(row.get("alert_ids_json"))
        categories = _parse_collected(row.get("categories_json"))
        timestamps = _parse_collected(row.get("timestamps_json"))
        filtered: list[dict[str, Any]] = []
        for alert_id, category, timestamp in zip(alert_ids, categories, timestamps):
            epoch = DiscoveryService._parse_epoch(timestamp)
            if epoch is None:
                continue
            if baseline_cutoff <= epoch <= as_of_epoch_ms:
                filtered.append({
                    "alert_id": str(alert_id),
                    "category": str(category or ""),
                    "timestamp_epoch": epoch,
                })
        return filtered

    def _shared_entity_score(
        self,
        alert_count: int,
        category_count: int,
        filtered: list[dict[str, Any]],
        threat_intel_present: bool,
    ) -> float:
        timestamps = [item["timestamp_epoch"] for item in filtered]
        window_days = max((max(timestamps) - min(timestamps)) / DAY_MS, 1.0) if timestamps else 1.0
        temporal_density = min(alert_count / window_days / 3.0, 1.0)
        return _clamp_score(
            0.20 * min(alert_count / 20.0, 1.0)
            + 0.30 * min(category_count / 6.0, 1.0)
            + 0.20 * temporal_density
            + 0.30 * (1.0 if threat_intel_present else 0.0)
        )

    async def _pattern_convergence_discovery(
        self,
        neo4j_client: Any,
        baseline_cutoff: int,
    ) -> tuple[list[Discovery], list[dict[str, Any]]]:
        """Algorithm 2: Pattern Convergence.

        Uses numpy broadcasting for pairwise L2 distances -- O(G^2) numpy ops
        rather than O(G^2) Python loops. CONVERGENCE_LIMIT=200 caps worst-case
        pairs at 200*199/2 = 19,900.
        """
        query = f"""
        MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
        WHERE d.domain = 'soc'
          AND d.timestamp_epoch >= {baseline_cutoff}
          AND d.confidence > {self.MIN_CONFIDENCE_CONVERGENCE}
        RETURN d.decision_id AS decision_id,
               a.alert_id AS alert_id,
               d.category AS category,
               d.action AS action,
               d.confidence AS confidence,
               d.factor_vector AS factor_vector,
               d.timestamp_epoch AS timestamp_epoch
        ORDER BY d.timestamp_epoch DESC
        LIMIT {self.CONVERGENCE_LIMIT}
        """
        rows = await neo4j_client.run_query(query)

        # Parse rows, attach "vector" key for Algorithm 4 reuse
        parsed: list[dict[str, Any]] = []
        for row in rows or []:
            vector = _parse_factor_vector(row.get("factor_vector"))
            if vector is None:
                continue
            category = str(row.get("category") or "")
            action = str(row.get("action") or "")
            if not category or not action:
                continue
            parsed.append({**row, "vector": vector, "category": category, "action": action})

        discoveries: list[Discovery] = []
        by_action: dict[str, list[dict[str, Any]]] = {}
        for row in parsed:
            by_action.setdefault(row["action"], []).append(row)

        for action, action_rows in by_action.items():
            if len(action_rows) < 2:
                continue
            group_cats = [r["category"] for r in action_rows]
            if len(set(group_cats)) < 2:
                continue

            # Vectorized pairwise distances: one numpy call for the entire matrix
            vecs = np.vstack([r["vector"] for r in action_rows])  # (G, 6)
            diff = vecs[:, np.newaxis, :] - vecs[np.newaxis, :, :]  # (G, G, 6)
            distances = np.sqrt((diff ** 2).sum(axis=2))  # (G, G)

            best: Optional[tuple[float, dict[str, Any], dict[str, Any]]] = None
            for i in range(len(action_rows)):
                for j in range(i + 1, len(action_rows)):
                    if group_cats[i] == group_cats[j]:
                        continue
                    dist = float(distances[i, j])
                    confidence = (
                        float(action_rows[i].get("confidence") or 0.0)
                        + float(action_rows[j].get("confidence") or 0.0)
                    ) / 2.0
                    score = _clamp_score(min(dist, 1.0) * confidence)
                    if best is None or score > best[0]:
                        best = (score, action_rows[i], action_rows[j])

            if best is None:
                continue
            score, left, right = best
            categories = sorted({left["category"], right["category"]})
            discoveries.append(
                Discovery(
                    discovery_id=self._stable_id(
                        DiscoveryType.PATTERN_CONVERGENCE.value, action, *categories
                    ),
                    domain=self.DEFAULT_DOMAIN,
                    source_domains=[self.DEFAULT_DOMAIN],
                    type=DiscoveryType.PATTERN_CONVERGENCE.value,
                    severity=_severity_for_score(score),
                    title=f"Cross-category action divergence: {action}",
                    description=(
                        f"Decisions from {categories[0]} and {categories[1]} "
                        f"share action {action} despite divergent factor geometry."
                    ),
                    score=score,
                    discovered_at=_now_iso(),
                    involved_alert_ids=[
                        str(left.get("alert_id") or ""),
                        str(right.get("alert_id") or ""),
                    ],
                    involved_decision_ids=[
                        str(left.get("decision_id") or ""),
                        str(right.get("decision_id") or ""),
                    ],
                    category_summary=", ".join(categories),
                    factor_summary=f"pairwise_l2={np.linalg.norm(left['vector'] - right['vector']):.4f}",
                )
            )
        return discoveries, parsed

    async def _temporal_velocity_discovery(
        self,
        neo4j_client: Any,
        recent_cutoff: int,
        baseline_cutoff: int,
    ) -> list[Discovery]:
        specs = [
            (
                "User",
                f"""
                MATCH (a:Alert)-[:INVOLVES]->(u:User)
                WHERE a.timestamp_epoch >= {recent_cutoff}
                RETURN u.user_id AS entity_id,
                       u.name AS entity_name,
                       collect(a.alert_id) AS alert_ids_json,
                       count(a) AS cnt
                ORDER BY cnt DESC
                LIMIT 100
                """,
                f"""
                MATCH (a:Alert)-[:INVOLVES]->(u:User)
                WHERE a.timestamp_epoch >= {baseline_cutoff}
                  AND a.timestamp_epoch < {recent_cutoff}
                RETURN u.user_id AS entity_id,
                       u.name AS entity_name,
                       count(a) AS cnt
                ORDER BY cnt DESC
                LIMIT 100
                """,
            ),
            (
                "Asset",
                f"""
                MATCH (a:Alert)-[:DETECTED_ON]->(asset:Asset)
                WHERE a.timestamp_epoch >= {recent_cutoff}
                RETURN asset.asset_id AS entity_id,
                       asset.hostname AS entity_name,
                       collect(a.alert_id) AS alert_ids_json,
                       count(a) AS cnt
                ORDER BY cnt DESC
                LIMIT 100
                """,
                f"""
                MATCH (a:Alert)-[:DETECTED_ON]->(asset:Asset)
                WHERE a.timestamp_epoch >= {baseline_cutoff}
                  AND a.timestamp_epoch < {recent_cutoff}
                RETURN asset.asset_id AS entity_id,
                       asset.hostname AS entity_name,
                       count(a) AS cnt
                ORDER BY cnt DESC
                LIMIT 100
                """,
            ),
        ]
        discoveries: list[Discovery] = []
        for entity_type, recent_query, baseline_query in specs:
            recent_rows = await neo4j_client.run_query(recent_query)
            baseline_rows = await neo4j_client.run_query(baseline_query)
            baseline_by_id = {
                str(r.get("entity_id")): int(r.get("cnt") or 0)
                for r in baseline_rows or []
                if r.get("entity_id")
            }
            for row in recent_rows or []:
                entity_id = str(row.get("entity_id") or "")
                recent_cnt = int(row.get("cnt") or 0)
                baseline_cnt = baseline_by_id.get(entity_id, 0)
                if recent_cnt < self.MIN_RECENT_COUNT or baseline_cnt <= 0:
                    continue
                baseline_normalized = baseline_cnt * self.DEFAULT_RECENT_DAYS / self.DEFAULT_LOOKBACK_DAYS
                if baseline_normalized <= 0:
                    continue
                ratio = recent_cnt / baseline_normalized
                if ratio < self.MIN_VELOCITY_RATIO:
                    continue
                score = _clamp_score(ratio / 20.0)
                discoveries.append(
                    Discovery(
                        discovery_id=self._stable_id(
                            DiscoveryType.TEMPORAL_VELOCITY.value, entity_type, entity_id
                        ),
                        domain=self.DEFAULT_DOMAIN,
                        source_domains=[self.DEFAULT_DOMAIN],
                        type=DiscoveryType.TEMPORAL_VELOCITY.value,
                        severity=_severity_for_score(score),
                        title=f"{entity_type} alert velocity increased",
                        description=(
                            f"{entity_id} has {recent_cnt} recent alerts, "
                            f"{ratio:.2f}x normalized baseline."
                        ),
                        score=score,
                        discovered_at=_now_iso(),
                        involved_entity_ids=[entity_id],
                        involved_alert_ids=[
                            str(item)
                            for item in _parse_collected(row.get("alert_ids_json"))
                        ],
                        entity_summary=f"{entity_type} {row.get('entity_name') or entity_id}",
                        temporal_summary=f"recent={recent_cnt}, baseline={baseline_cnt}, ratio={ratio:.2f}",
                    )
                )
        return discoveries

    def _cross_factor_anomaly_discovery(
        self,
        decisions_with_vectors: list[dict[str, Any]],
        timeout: float = 3.0,
    ) -> list[Discovery]:
        discoveries: list[Discovery] = []
        category_means = np.asarray(SOC_PROFILE_CENTROIDS, dtype=np.float64).mean(axis=1)
        start = time.monotonic()
        for i, row in enumerate(decisions_with_vectors or []):
            if time.monotonic() - start > timeout:
                log.warning(
                    "Cross-factor anomaly timed out at row %d/%d",
                    i, len(decisions_with_vectors),
                )
                break
            category = str(row.get("category") or "")
            if category not in SOC_CATEGORIES:
                continue
            vector = row.get("vector")
            if vector is None:
                vector = _parse_factor_vector(row.get("factor_vector"))
            if vector is None:
                continue
            assigned_index = SOC_CATEGORIES.index(category)
            distances = np.linalg.norm(category_means - vector, axis=1)
            nearest_index = int(np.argmin(distances))
            nearest_category = SOC_CATEGORIES[nearest_index]
            assigned_distance = float(distances[assigned_index])
            nearest_distance = float(distances[nearest_index])
            distance_gap = assigned_distance - nearest_distance
            emitted_misroute = False
            if nearest_category != category and distance_gap > 0.0:
                score = _clamp_score(distance_gap)
                discoveries.append(
                    Discovery(
                        discovery_id=self._stable_id(
                            DiscoveryType.CROSS_FACTOR_MISROUTE.value,
                            str(row.get("decision_id") or ""),
                        ),
                        domain=self.DEFAULT_DOMAIN,
                        source_domains=[self.DEFAULT_DOMAIN],
                        type=DiscoveryType.CROSS_FACTOR_MISROUTE.value,
                        severity=_severity_for_score(score),
                        title="Decision is closer to another SOC category",
                        description=(
                            f"{row.get('decision_id')} is assigned {category} "
                            f"but nearest to {nearest_category}."
                        ),
                        score=score,
                        discovered_at=_now_iso(),
                        involved_alert_ids=[str(row.get("alert_id") or "")],
                        involved_decision_ids=[str(row.get("decision_id") or "")],
                        category_summary=f"assigned={category}, nearest={nearest_category}",
                        factor_summary=f"distance_gap={distance_gap:.4f}",
                    )
                )
                emitted_misroute = True
            if nearest_distance > self.ANOMALY_THRESHOLD and not emitted_misroute:
                score = _clamp_score(nearest_distance - self.ANOMALY_THRESHOLD)
                discoveries.append(
                    Discovery(
                        discovery_id=self._stable_id(
                            DiscoveryType.CROSS_FACTOR_NOVEL.value,
                            str(row.get("decision_id") or ""),
                        ),
                        domain=self.DEFAULT_DOMAIN,
                        source_domains=[self.DEFAULT_DOMAIN],
                        type=DiscoveryType.CROSS_FACTOR_NOVEL.value,
                        severity=_severity_for_score(score),
                        title="Decision is far from known SOC centroids",
                        description=(
                            f"{row.get('decision_id')} is far from every "
                            "category centroid."
                        ),
                        score=score,
                        discovered_at=_now_iso(),
                        involved_alert_ids=[str(row.get("alert_id") or "")],
                        involved_decision_ids=[str(row.get("decision_id") or "")],
                        category_summary=f"assigned={category}",
                        factor_summary=f"min_distance={nearest_distance:.4f}",
                    )
                )
        return discoveries

    @staticmethod
    def _stable_id(*parts: Any) -> str:
        raw = "|".join(str(part) for part in parts)
        return "disc-" + uuid.uuid5(uuid.NAMESPACE_URL, raw).hex[:16]


discovery_service = DiscoveryService()
