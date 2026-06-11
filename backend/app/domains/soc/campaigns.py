"""
campaigns.py — Multi-Alert Campaign Correlation (F6).

Campaign schema, Cypher queries, and pure-Python helper functions.
No Neo4j calls in this module — all graph I/O lives in the service layer.

Confidence model:
  technique_sequence  0.85  (kill-chain pattern matched)
  shared_entity       0.70  (common asset/user/host across alerts)
  temporal            0.45  (time-proximity only)
  multi-rule boost   +0.10  capped at 0.95

# Innovation mapping (MAP v4.6):
# F6 Attack Chain Correlation maps to:
#   Innovation 7 (CGA/W2 — graph compounds across decisions)
#   Innovation 4 (pluggable kernels — campaign confidence uses
#                 DiagonalKernel weighting via ThreatIntelEnrichmentFactor)
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional
import hashlib
import json as _json
import logging
import os
import time
import uuid

log = logging.getLogger(__name__)

_TRACE_FALSE_VALUES = {"", "0", "false", "no", "off"}
_TRACE_MAX_QUERY_EVENTS = 50


def _campaign_trace_enabled() -> bool:
    return os.getenv("SOC_PERF_TRACE_ENABLED", "false").strip().lower() not in _TRACE_FALSE_VALUES


def _campaign_trace_output_path() -> Path:
    raw = os.getenv("SOC_PERF_TRACE_OUTPUT", "scratch/temp/soc_perf_trace.jsonl")
    path = Path(raw)
    repo_root = Path(__file__).resolve().parents[4]
    return path if path.is_absolute() else repo_root / path


def _campaign_trace_emit(event: dict[str, Any]) -> None:
    if not _campaign_trace_enabled():
        return
    try:
        output_path = _campaign_trace_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("a", encoding="utf-8") as fh:
            fh.write(_json.dumps(event, sort_keys=True) + "\n")
    except Exception:
        pass


class CampaignTraceCollector:
    """Best-effort campaign-local perf counters. Disabled unless SOC_PERF_TRACE_ENABLED is true."""

    def __init__(self, alert_id: str):
        self.enabled = _campaign_trace_enabled()
        self.alert_id = alert_id
        self.started = time.perf_counter()
        self.query_count = 0
        self.read_query_count = 0
        self.write_query_count = 0
        self.query_total_ms = 0.0
        self.query_max_ms = 0.0
        self.queries: list[dict[str, Any]] = []
        self.recent_event_count: int | None = None
        self.member_alert_count: int | None = None
        self.member_edge_existing_count: int | None = None
        self.member_edge_missing_count: int | None = None
        self.member_alert_missing_count: int | None = None
        self.member_edge_create_chunk_count: int | None = None
        self.member_edges_created_count: int | None = None
        self.candidate_campaign_count: int | None = None
        self.path = "unknown"

    def record_query(
        self,
        label: str,
        kind: str,
        duration_ms: float,
        row_count: int | None,
        status: str,
        exception_type: str | None = None,
    ) -> None:
        if not self.enabled:
            return
        self.query_count += 1
        if kind == "write":
            self.write_query_count += 1
        else:
            self.read_query_count += 1
        self.query_total_ms += duration_ms
        self.query_max_ms = max(self.query_max_ms, duration_ms)
        query_event = {
            "label": label,
            "kind": kind,
            "duration_ms": round(duration_ms, 3),
            "row_count": row_count,
            "status": status,
            "exception_type": exception_type,
        }
        if len(self.queries) < _TRACE_MAX_QUERY_EVENTS:
            self.queries.append(query_event)
        _campaign_trace_emit(
            {
                "event_type": "phase_timing",
                "phase": f"campaign_query_{label}",
                "route": "/api/alert/analyze",
                "duration_ms": round(duration_ms, 3),
                "status": status,
                "exception_type": exception_type,
                "graph_name": os.getenv("AGE_GRAPH_NAME"),
                "alert_id": self.alert_id,
                "decision_id": None,
                "category": None,
                "action": None,
                "metadata": {
                    "query_label": label,
                    "query_kind": kind,
                    "row_count": row_count,
                },
                "timestamp_epoch_ms": int(time.time() * 1000),
            }
        )

    def emit_summary(self, campaign_id: str | None = None) -> None:
        if not self.enabled:
            return
        duration_ms = (time.perf_counter() - self.started) * 1000.0
        _campaign_trace_emit(
            {
                "event_type": "phase_timing",
                "phase": "campaign_correlation_summary",
                "route": "/api/alert/analyze",
                "duration_ms": round(duration_ms, 3),
                "status": "ok",
                "exception_type": None,
                "graph_name": os.getenv("AGE_GRAPH_NAME"),
                "alert_id": self.alert_id,
                "decision_id": None,
                "category": None,
                "action": None,
                "metadata": {
                    "campaign_id_present": bool(campaign_id),
                    "campaign_query_count": self.query_count,
                    "campaign_query_total_ms": round(self.query_total_ms, 3),
                    "campaign_query_max_ms": round(self.query_max_ms, 3),
                    "read_query_count": self.read_query_count,
                    "write_query_count": self.write_query_count,
                    "recent_event_count": self.recent_event_count,
                    "member_alert_count": self.member_alert_count,
                    "member_edge_existing_count": self.member_edge_existing_count,
                    "member_edge_missing_count": self.member_edge_missing_count,
                    "member_alert_missing_count": self.member_alert_missing_count,
                    "member_edge_create_chunk_count": self.member_edge_create_chunk_count,
                    "member_edges_created_count": self.member_edges_created_count,
                    "candidate_campaign_count": self.candidate_campaign_count,
                    "path": self.path,
                    "queries": self.queries,
                },
                "timestamp_epoch_ms": int(time.time() * 1000),
            }
        )


async def _campaign_trace_query(
    collector: CampaignTraceCollector | None,
    label: str,
    kind: str,
    awaitable,
):
    if collector is None or not collector.enabled:
        return await awaitable
    started = time.perf_counter()
    status = "ok"
    exception_type = None
    row_count = None
    try:
        result = await awaitable
        if isinstance(result, list):
            row_count = len(result)
        return result
    except Exception as exc:
        status = "error"
        exception_type = type(exc).__name__
        raise
    finally:
        collector.record_query(
            label,
            kind,
            (time.perf_counter() - started) * 1000.0,
            row_count,
            status,
            exception_type,
        )


def _S(val) -> str:
    """Serialize a Python value to an AGE-safe inline Cypher literal."""
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, (list, tuple)):
        return "'" + _json.dumps(val).replace("'", "\\'") + "'"
    return "'" + str(val).replace("\\", "\\\\").replace("'", "\\'") + "'"


def _dedupe_preserve_order(values: List[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _alert_id_or_predicate(alias: str, alert_ids: List[str]) -> str:
    return " OR ".join(f"{alias}.alert_id = {_S(alert_id)}" for alert_id in alert_ids)


def _chunks(values: List[str], size: int) -> List[List[str]]:
    return [values[i:i + size] for i in range(0, len(values), size)]


def _to_python_dt(value):
    """Convert neo4j DateTime / epoch int to Python datetime; pass through if already datetime."""
    if isinstance(value, datetime):
        return value
    if hasattr(value, "to_native"):
        return value.to_native()
    # AGE stores timestamps as epoch-millisecond integers
    if isinstance(value, (int, float)) and value > 1e9:
        divisor = 1000 if value > 1e12 else 1  # ms vs s
        return datetime.utcfromtimestamp(value / divisor)
    return value


# ── Kill-chain templates ─────────────────────────────────────────────────────

KILL_CHAINS = {
    "credential_then_lateral": [
        ("credential_access", "lateral_movement"),
    ],
    "credential_then_lateral_then_exfil": [
        ("credential_access", "lateral_movement", "data_exfiltration"),
    ],
    "cloud_recon_to_exfil": [
        ("cloud_infrastructure", "data_exfiltration"),
    ],
    "insider_to_exfil": [
        ("insider_threat", "data_exfiltration"),
    ],
}

# ── Confidence constants ─────────────────────────────────────────────────────

CONFIDENCE_TECHNIQUE_SEQUENCE = 0.85
CONFIDENCE_SHARED_ENTITY = 0.70
CONFIDENCE_TEMPORAL = 0.45
CONFIDENCE_MULTI_RULE_BOOST = 0.10
CONFIDENCE_MAX = 0.95


# ── Campaign dataclass ───────────────────────────────────────────────────────

@dataclass
class Campaign:
    campaign_id: str
    first_seen: datetime
    last_seen: datetime
    alert_count: int
    category_sequence: List[str]
    shared_entities: List[str]
    technique_sequence: List[str]
    confidence: float
    trigger_rule: str        # "shared_entity" | "technique_sequence" | "temporal"
    severity: str            # "HIGH" | "MEDIUM" | "LOW"
    member_decision_ids: List[str]
    member_alert_ids: List[str]
    correlation_window_hours: int
    nl_summary: str
    rule_type: str = ""
    derived_entity_key: str = ""
    category: str = ""
    time_bucket: int = 0


# ── Cypher queries ───────────────────────────────────────────────────────────

SHARED_ENTITY_QUERY = """
MATCH (d1:Decision)-[:INVOLVES]->(e:Entity)<-[:INVOLVES]-(d2:Decision)
WHERE d1.alert_id <> d2.alert_id
  AND d1.timestamp_epoch >= $window_start
  AND d2.timestamp_epoch >= $window_start
WITH e, collect(DISTINCT d1) + collect(DISTINCT d2) AS decisions
WHERE size(decisions) >= 2
RETURN
    e.id                                            AS shared_entity,
    e.type                                          AS entity_type,
    [d IN decisions | d.alert_id]                   AS alert_ids,
    [d IN decisions | d.decision_id]                AS decision_ids,
    [d IN decisions | d.category]                   AS categories,
    [d IN decisions | d.severity]                   AS severities,
    [d IN decisions | d.timestamp_epoch]            AS timestamps
ORDER BY size(decisions) DESC
LIMIT $limit
"""

TECHNIQUE_SEQUENCE_QUERY = """
MATCH path = (d1:Decision)-[:TRIGGERED_EVOLUTION*1..5]->(d2:Decision)
WHERE d1.timestamp_epoch >= $window_start
  AND d2.timestamp_epoch >= $window_start
  AND d1.alert_id <> d2.alert_id
WITH
    [node IN nodes(path) WHERE node:Decision | node] AS chain_nodes
WHERE size(chain_nodes) >= 2
RETURN
    [n IN chain_nodes | n.alert_id]         AS alert_ids,
    [n IN chain_nodes | n.decision_id]      AS decision_ids,
    [n IN chain_nodes | n.category]         AS categories,
    [n IN chain_nodes | n.severity]         AS severities,
    [n IN chain_nodes | n.timestamp_epoch]  AS timestamps
LIMIT $limit
"""

TEMPORAL_QUERY = """
MATCH (d:Decision)
WHERE d.timestamp_epoch >= $window_start
  AND d.timestamp_epoch <= $window_end
WITH d ORDER BY d.timestamp_epoch ASC
WITH collect(d) AS decisions
UNWIND range(0, size(decisions) - 2) AS i
WITH decisions[i] AS d1, decisions[i+1] AS d2
WHERE (d2.timestamp_epoch - d1.timestamp_epoch) / 1000 <= $window_seconds
  AND d1.category = d2.category
RETURN
    d1.category                                       AS category,
    [d1.alert_id, d2.alert_id]                        AS alert_ids,
    [d1.decision_id, d2.decision_id]                  AS decision_ids,
    [d1.severity, d2.severity]                        AS severities,
    [d1.timestamp_epoch, d2.timestamp_epoch]          AS timestamps
LIMIT $limit
"""

GET_CAMPAIGNS_QUERY = """
MATCH (c:Campaign)
OPTIONAL MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)-[:MEMBER_OF]->(c)
WITH c, collect(d.decision_id) AS decision_ids
RETURN
    c.campaign_id              AS campaign_id,
    c.first_seen               AS first_seen,
    c.last_seen                AS last_seen,
    c.alert_count              AS alert_count,
    c.category_sequence        AS category_sequence,
    c.shared_entities          AS shared_entities,
    c.technique_sequence       AS technique_sequence,
    c.confidence               AS confidence,
    c.trigger_rule             AS trigger_rule,
    c.severity                 AS severity,
    c.member_alert_ids         AS member_alert_ids,
    decision_ids               AS member_decision_ids,
    c.correlation_window_hours AS correlation_window_hours,
    c.nl_summary               AS nl_summary
ORDER BY c.last_seen DESC
LIMIT $limit
"""

GET_CAMPAIGN_DETAIL_QUERY = """
MATCH (c:Campaign {campaign_id: $campaign_id})
OPTIONAL MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)-[:MEMBER_OF]->(c)
WITH c, collect(d) AS decisions
RETURN
    c.campaign_id              AS campaign_id,
    c.first_seen               AS first_seen,
    c.last_seen                AS last_seen,
    c.alert_count              AS alert_count,
    c.category_sequence        AS category_sequence,
    c.shared_entities          AS shared_entities,
    c.technique_sequence       AS technique_sequence,
    c.confidence               AS confidence,
    c.trigger_rule             AS trigger_rule,
    c.severity                 AS severity,
    c.member_alert_ids         AS member_alert_ids,
    [d IN decisions | d.decision_id]  AS member_decision_ids,
    c.correlation_window_hours        AS correlation_window_hours,
    c.nl_summary                      AS nl_summary,
    [d IN decisions | {
        id: d.decision_id,
        alert_id: d.alert_id,
        category: d.category,
        action: d.action,
        confidence: d.confidence,
        created_at: d.timestamp_epoch
    }] AS decision_details
"""


# ── Helper functions (pure Python, no Neo4j) ─────────────────────────────────

def make_campaign_id(alert_ids: List[str]) -> str:
    """Deterministic UUID5 from sorted alert IDs — order-independent."""
    return str(uuid.uuid5(uuid.NAMESPACE_OID, ",".join(sorted(alert_ids))))


def _present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def derived_entity_key(event: dict) -> str | None:
    """Phase 1 L1 campaign entity key with type prefixes to avoid collisions."""
    for field_name, prefix in (
        ("source_entity_id", "entity"),
        ("user_id", "user"),
        ("asset_id", "asset"),
        ("source_location", "loc"),
    ):
        value = event.get(field_name)
        if _present(value):
            return f"{prefix}:{str(value).strip()}"
    return None


def campaign_time_bucket(ts, window_seconds: int) -> int | None:
    """Epoch-aligned time bucket for Phase 1 campaign identity."""
    if not window_seconds or window_seconds <= 0 or ts is None:
        return None
    if hasattr(ts, "to_native"):
        ts = ts.to_native()
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            seconds = ts.replace(tzinfo=timezone.utc).timestamp()
        else:
            seconds = ts.timestamp()
    else:
        seconds = _ts_to_seconds(ts)
    return int(seconds // window_seconds)


def make_campaign_identity_key(
    rule_type: str,
    derived_entity_key: str,
    category: str,
    time_bucket: int,
) -> str:
    """Stable Phase 1 L1 campaign ID from rule, entity, category, and bucket."""
    material = (
        "L1:"
        + str(rule_type)
        + "\x00"
        + str(derived_entity_key)
        + "\x00"
        + str(category)
        + "\x00"
        + str(int(time_bucket))
    )
    return "L1-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def is_subsequence(needle: tuple, haystack: List[str]) -> bool:
    """Check if needle categories appear in order in haystack."""
    it = iter(haystack)
    return all(c in it for c in needle)


def derive_severity(severities: List[str]) -> str:
    """HIGH if any HIGH/CRITICAL, MEDIUM if any MEDIUM, else LOW."""
    if any(s in ("HIGH", "CRITICAL") for s in severities):
        return "HIGH"
    if "MEDIUM" in severities:
        return "MEDIUM"
    return "LOW"


def _ts_to_seconds(ts) -> float:
    """Convert ts to a comparable float (seconds since epoch).

    ts may be a Python datetime, a neo4j DateTime (has .to_native()), or an
    epoch integer in milliseconds (as written by the migrated epoch fields).
    """
    if isinstance(ts, (int, float)):
        return ts / 1000.0  # epoch millis → seconds
    if hasattr(ts, "to_native"):
        ts = ts.to_native()
    if isinstance(ts, datetime):
        return ts.timestamp()
    return float(ts)


def sliding_window_cluster(alerts: list, window_seconds: int) -> List[list]:
    """Group alerts into time-proximity clusters."""
    if not alerts:
        return []
    clusters = [[alerts[0]]]
    for alert in alerts[1:]:
        last_ts = _ts_to_seconds(clusters[-1][-1]["ts"])
        delta = _ts_to_seconds(alert["ts"]) - last_ts
        if delta <= window_seconds:
            clusters[-1].append(alert)
        else:
            clusters.append([alert])
    return clusters


def build_nl_summary(events: list, shared_entities: List[str],
                     trigger_rule: str) -> str:
    """Deterministic NL summary. No LLM — template only."""
    n = len(events)
    cats = list(dict.fromkeys([e["category"] or "unknown" for e in events]))
    ts_values = [_ts_to_seconds(e["ts"]) for e in events]
    dur_hours = int((max(ts_values) - min(ts_values)) / 3600)
    cat_str = " → ".join(cats)
    if trigger_rule == "technique_sequence":
        return (f"{n} alerts: {cat_str} over {dur_hours}h. "
                f"Kill chain pattern detected.")
    elif trigger_rule == "shared_entity":
        ent_count = len(shared_entities)
        return (f"{n} alerts from {ent_count} shared "
                f"{'entity' if ent_count == 1 else 'entities'}. "
                f"{cat_str} over {dur_hours}h.")
    else:
        return (f"{n} alerts in {cats[0] if cats else 'unknown'} "
                f"cluster over {dur_hours}h. Temporal proximity pattern.")


def compute_confidence(trigger_rule: str,
                       additional_rules: List[str] = None) -> float:
    """
    Confidence model per F6 spec.
    Multi-rule boost: +0.10 capped at 0.95.
    """
    base = {
        "technique_sequence": CONFIDENCE_TECHNIQUE_SEQUENCE,
        "shared_entity":      CONFIDENCE_SHARED_ENTITY,
        "temporal":           CONFIDENCE_TEMPORAL,
    }.get(trigger_rule, CONFIDENCE_TEMPORAL)

    if additional_rules:
        base = min(base + CONFIDENCE_MULTI_RULE_BOOST, CONFIDENCE_MAX)
    return base


# ── CampaignCorrelationEngine ─────────────────────────────────────────────────
# TODO(CopilotFramework): CampaignCorrelationEngine is framework-level.
# Move to ci-platform CopilotFramework during Phase 3 Priority 2
# extraction. KILL_CHAINS and get_campaign_config() stay SOC domain.

class CampaignCorrelationEngine:
    """
    Finds campaigns from alert event data.
    Rule priority: technique_sequence > shared_entity > temporal.
    Campaign IDs are stable per Phase 1 L1 identity tuple:
    rule_type + derived entity + category + epoch-aligned bucket.
    All methods accept plain dicts — no Neo4j dependency in this class.
    Neo4j queries live in CampaignRepository (Step 5).
    """

    def __init__(self, config: dict):
        self.window_seconds = config["correlation_window_hours"] * 3600
        self.temporal_window = config["temporal_window_minutes"] * 60
        self.min_alerts = config["min_alerts_for_campaign"]

    def correlate(self, events: List[dict]) -> List[Campaign]:
        """
        Run all 3 rules against a list of alert events.
        Each event dict must have:
          alert_id, category, entity fields (nullable),
          ts (datetime), technique_id (nullable), severity

        Returns list of Campaign objects. Each alert appears in
        at most ONE campaign (highest-priority rule wins).
        """
        claimed: set = set()   # alert_ids already assigned to a campaign
        campaigns: List[Campaign] = []

        # Pass 1 — technique_sequence (highest confidence, first priority)
        new_campaigns, claimed = self._apply_technique_sequence(events, claimed)
        campaigns += new_campaigns

        # Pass 2 — shared_entity on unclaimed alerts
        unclaimed = [e for e in events if e["alert_id"] not in claimed]
        new_campaigns, claimed = self._apply_shared_entity(unclaimed, claimed)
        campaigns += new_campaigns

        # Pass 3 — temporal on remaining unclaimed alerts
        unclaimed = [e for e in events if e["alert_id"] not in claimed]
        new_campaigns, claimed = self._apply_temporal(unclaimed, claimed)
        campaigns += new_campaigns

        return campaigns

    def _apply_technique_sequence(
        self, events: List[dict], claimed: set
    ) -> tuple:
        """
        Rule 2: Phase 1 only permits same-category/entity/bucket L1 campaigns.
        Cross-category attack-chain semantics are deferred to Level 2.
        """
        identity_groups = self._identity_groups(events, claimed)

        # Flatten all chains, sorted longest first so greedy match is correct
        all_chains: List[tuple] = []
        for chain_list in KILL_CHAINS.values():
            all_chains.extend(chain_list)
        all_chains.sort(key=lambda c: len(c), reverse=True)

        new_campaigns: List[Campaign] = []
        for (entity_key, _category, _bucket), group in identity_groups.items():
            group_sorted = sorted(group, key=lambda e: e["ts"])
            categories = [e["category"] for e in group_sorted]

            for chain in all_chains:
                if len(set(chain)) != 1:
                    continue
                if is_subsequence(chain, categories):
                    matching = self._extract_chain_events(group_sorted, chain)
                    if len(matching) >= self.min_alerts:
                        alert_ids = [e["alert_id"] for e in matching]
                        # Skip only if every member already claimed
                        if all(aid in claimed for aid in alert_ids):
                            continue
                        campaign = self._build_campaign(
                            matching,
                            trigger_rule="technique_sequence",
                            confidence=CONFIDENCE_TECHNIQUE_SEQUENCE,
                            shared_entities=[entity_key],
                        )
                        if campaign is not None:
                            new_campaigns.append(campaign)
                            claimed.update(alert_ids)
                        break  # one chain match per entity — exit chain loop

        return new_campaigns, claimed

    def _apply_shared_entity(
        self, events: List[dict], claimed: set
    ) -> tuple:
        """
        Rule 1: Group unclaimed events by Phase 1 entity/category/bucket.
        """
        identity_groups = self._identity_groups(events, claimed)

        new_campaigns: List[Campaign] = []
        for (entity_key, _category, _bucket), group in identity_groups.items():
            group_sorted = sorted(group, key=lambda e: e["ts"])
            windowed = self._filter_to_window(group_sorted, self.window_seconds)
            if len(windowed) >= self.min_alerts:
                alert_ids = [e["alert_id"] for e in windowed]
                campaign = self._build_campaign(
                    windowed,
                    trigger_rule="shared_entity",
                    confidence=CONFIDENCE_SHARED_ENTITY,
                    shared_entities=[entity_key],
                )
                if campaign is not None:
                    new_campaigns.append(campaign)
                    claimed.update(alert_ids)

        return new_campaigns, claimed

    def _apply_temporal(
        self, events: List[dict], claimed: set
    ) -> tuple:
        """
        Rule 3: Group unclaimed events by Phase 1 entity/category/bucket,
        then cluster by temporal proximity.
        """
        identity_groups = self._identity_groups(events, claimed)

        new_campaigns: List[Campaign] = []
        for (_entity_key, _category, _bucket), group in identity_groups.items():
            group_sorted = sorted(group, key=lambda e: e["ts"])
            clusters = sliding_window_cluster(group_sorted, self.temporal_window)
            for cluster in clusters:
                if len(cluster) >= self.min_alerts:
                    alert_ids = [e["alert_id"] for e in cluster]
                    if all(aid in claimed for aid in alert_ids):
                        continue
                    campaign = self._build_campaign(
                        cluster,
                        trigger_rule="temporal",
                        confidence=CONFIDENCE_TEMPORAL,
                        shared_entities=[],
                    )
                    if campaign is not None:
                        new_campaigns.append(campaign)
                        claimed.update(alert_ids)

        return new_campaigns, claimed

    def _build_campaign(
        self, events: List[dict], trigger_rule: str,
        confidence: float, shared_entities: List[str],
    ) -> Optional[Campaign]:
        if not events:
            return None
        entity_key = derived_entity_key(events[0])
        category = events[0].get("category")
        bucket = campaign_time_bucket(events[0].get("ts"), self.window_seconds)
        if not entity_key or not category or bucket is None:
            return None
        for event in events:
            if (
                derived_entity_key(event) != entity_key
                or event.get("category") != category
                or campaign_time_bucket(event.get("ts"), self.window_seconds) != bucket
            ):
                return None

        alert_ids = [e["alert_id"] for e in events]
        cats = [e["category"] for e in events]
        techniques = [e["technique_id"] for e in events if e.get("technique_id")]
        severities = [e.get("severity", "LOW") for e in events]

        return Campaign(
            campaign_id=make_campaign_identity_key(trigger_rule, entity_key, category, bucket),
            first_seen=min(e["ts"] for e in events),
            last_seen=max(e["ts"] for e in events),
            alert_count=len(alert_ids),
            category_sequence=cats,
            shared_entities=shared_entities,
            technique_sequence=techniques,
            confidence=confidence,
            trigger_rule=trigger_rule,
            severity=derive_severity(severities),
            member_decision_ids=[],
            member_alert_ids=alert_ids,
            correlation_window_hours=self.window_seconds // 3600,
            nl_summary=build_nl_summary(events, shared_entities, trigger_rule),
            rule_type=trigger_rule,
            derived_entity_key=entity_key,
            category=category,
            time_bucket=bucket,
        )

    def _identity_groups(self, events: List[dict], claimed: set) -> dict:
        groups: dict = defaultdict(list)
        for event in events:
            if event["alert_id"] in claimed:
                continue
            entity_key = derived_entity_key(event)
            category = event.get("category")
            bucket = campaign_time_bucket(event.get("ts"), self.window_seconds)
            if not entity_key or not category or bucket is None:
                continue
            groups[(entity_key, category, bucket)].append(event)
        return groups

    def _extract_chain_events(
        self, events: List[dict], chain: tuple
    ) -> List[dict]:
        """
        Extract events that match the chain in order.
        Returns the first matching event per chain category.
        """
        result = []
        chain_list = list(chain)
        chain_idx = 0
        for e in events:
            if chain_idx < len(chain_list) and e["category"] == chain_list[chain_idx]:
                result.append(e)
                chain_idx += 1
        return result

    @staticmethod
    def _filter_to_window(
        events: List[dict], window_seconds: int
    ) -> List[dict]:
        """Keep events within window_seconds of the first event."""
        if not events:
            return []
        start_ts = events[0]["ts"]
        return [
            e for e in events
            if (e["ts"] - start_ts).total_seconds() <= window_seconds
        ]


# ── CampaignRepository ────────────────────────────────────────────────────────

class CampaignRepository:
    """
    All Neo4j I/O for campaigns.
    Reads alert events from Decision/Alert nodes.
    Writes Campaign nodes and :MEMBER_OF edges.
    """

    def __init__(self, neo4j):
        self.neo4j = neo4j

    async def fetch_all_events(self) -> List[dict]:
        """
        Fetch triage alert events for retroactive correlation.
        Only includes decisions made by the live triage path:
          - source_id IS NOT NULL  (excludes simulation artifacts)
          - source_id <> 'synthetic'  (excludes seed/zero-day artifacts with SYN-DEC-* ids)
        Both populations lack campaign semantics and cause temporal clusters of
        thousands of events that overwhelm write_campaign.
        Returns list of event dicts compatible with CampaignCorrelationEngine.
        """
        try:
            results = await self.neo4j.run_query("""
                MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
                WHERE d.source_id IS NOT NULL AND d.source_id <> 'synthetic'
                RETURN a.alert_id AS alert_id,
                       COALESCE(a.category, d.category) AS category,
                       COALESCE(a.source_entity_id, d.source_id) AS source_entity_id,
                       a.user_id AS user_id,
                       a.asset_id AS asset_id,
                       COALESCE(a.source_location, d.source_id) AS source_location,
                       a.technique_id AS technique_id,
                       d.timestamp_epoch AS ts,
                       COALESCE(a.severity, 'MEDIUM') AS severity,
                       d.decision_id AS decision_id
                ORDER BY ts
            """, {})
            return [{**dict(r), "ts": _to_python_dt(r["ts"])} for r in results] if results else []
        except Exception as e:
            log.warning(f"fetch_all_events failed: {e}")
            return []

    async def fetch_recent_events(
        self, window_hours: int = 24,
        trace: CampaignTraceCollector | None = None,
    ) -> List[dict]:
        """
        Fetch recent unclaimed events for real-time matching.
        """
        try:
            results = await _campaign_trace_query(
                trace,
                "fetch_recent_events",
                "read",
                self.neo4j.run_query("""
                    MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
                    WHERE d.timestamp_epoch > $cutoff_epoch
                    RETURN a.alert_id AS alert_id,
                           COALESCE(a.category, d.category) AS category,
                           COALESCE(a.source_entity_id, d.source_id) AS source_entity_id,
                           a.user_id AS user_id,
                           a.asset_id AS asset_id,
                           COALESCE(a.source_location, d.source_id) AS source_location,
                           a.technique_id AS technique_id,
                           d.timestamp_epoch AS ts,
                           COALESCE(a.severity, 'MEDIUM') AS severity,
                           d.decision_id AS decision_id
                    ORDER BY ts
                """, {"cutoff_epoch": int((datetime.utcnow().timestamp() - window_hours * 3600) * 1000)}),
            )
            events = [{**dict(r), "ts": _to_python_dt(r["ts"])} for r in results] if results else []
            if trace is not None and trace.enabled:
                trace.recent_event_count = len(events)
            return events
        except Exception as e:
            log.warning(f"fetch_recent_events failed: {e}")
            return []

    async def fetch_single_alert_event(
        self,
        alert_id: str,
        trace: CampaignTraceCollector | None = None,
    ) -> Optional[dict]:
        """Fetch one alert event by ID."""
        try:
            results = await _campaign_trace_query(
                trace,
                "fetch_single_alert_event",
                "read",
                self.neo4j.run_query("""
                    MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert {alert_id: $alert_id})
                    RETURN a.alert_id AS alert_id,
                           COALESCE(a.category, d.category) AS category,
                           COALESCE(a.source_entity_id, d.source_id) AS source_entity_id,
                           a.user_id AS user_id,
                           a.asset_id AS asset_id,
                           COALESCE(a.source_location, d.source_id) AS source_location,
                           a.technique_id AS technique_id,
                           d.timestamp_epoch AS ts,
                           COALESCE(a.severity, 'MEDIUM') AS severity,
                           d.decision_id AS decision_id
                    LIMIT 1
                """, {"alert_id": alert_id}),
            )
            if results:
                r = dict(results[0])
                r["ts"] = _to_python_dt(r["ts"])
                return r
            return None
        except Exception as e:
            log.warning(f"fetch_single_alert_event failed: {e}")
            return None

    async def write_campaign(
        self,
        campaign: Campaign,
        trace: CampaignTraceCollector | None = None,
    ) -> bool:
        """
        Write Campaign node and :MEMBER_OF edges to Neo4j.
        Idempotent — MATCH-then-CREATE (AGE has no MERGE).
        Returns True on success.
        """
        try:
            if trace is not None and trace.enabled:
                trace.member_alert_count = len(campaign.member_alert_ids)
            cid = _S(campaign.campaign_id)
            ts = _S(int(datetime.utcnow().timestamp() * 1000))
            existing = await _campaign_trace_query(
                trace,
                "check_campaign_exists",
                "read",
                self.neo4j.run_query(
                    f"MATCH (c:Campaign {{campaign_id: {cid}}}) RETURN c"
                ),
            )
            if existing:
                await _campaign_trace_query(
                    trace,
                    "update_campaign",
                    "write",
                    self.neo4j.run_query(
                        f"MATCH (c:Campaign {{campaign_id: {cid}}})"
                        f" SET c.first_seen = {_S(campaign.first_seen.isoformat())},"
                        f"     c.last_seen = {_S(campaign.last_seen.isoformat())},"
                        f"     c.alert_count = {_S(campaign.alert_count)},"
                        f"     c.category_sequence = {_S(campaign.category_sequence)},"
                        f"     c.shared_entities = {_S(campaign.shared_entities)},"
                        f"     c.technique_sequence = {_S(campaign.technique_sequence)},"
                        f"     c.confidence = {_S(campaign.confidence)},"
                        f"     c.trigger_rule = {_S(campaign.trigger_rule)},"
                        f"     c.rule_type = {_S(campaign.rule_type or campaign.trigger_rule)},"
                        f"     c.derived_entity_key = {_S(campaign.derived_entity_key)},"
                        f"     c.category = {_S(campaign.category)},"
                        f"     c.time_bucket = {_S(campaign.time_bucket)},"
                        f"     c.severity = {_S(campaign.severity)},"
                        f"     c.correlation_window_hours = {_S(campaign.correlation_window_hours)},"
                        f"     c.nl_summary = {_S(campaign.nl_summary)},"
                        f"     c.updated_at_epoch = {ts}"
                    ),
                )
            else:
                await _campaign_trace_query(
                    trace,
                    "create_campaign",
                    "write",
                    self.neo4j.run_query(
                        f"CREATE (c:Campaign {{"
                        f" campaign_id: {cid},"
                        f" first_seen: {_S(campaign.first_seen.isoformat())},"
                        f" last_seen: {_S(campaign.last_seen.isoformat())},"
                        f" alert_count: {_S(campaign.alert_count)},"
                        f" category_sequence: {_S(campaign.category_sequence)},"
                        f" shared_entities: {_S(campaign.shared_entities)},"
                        f" technique_sequence: {_S(campaign.technique_sequence)},"
                        f" confidence: {_S(campaign.confidence)},"
                        f" trigger_rule: {_S(campaign.trigger_rule)},"
                        f" rule_type: {_S(campaign.rule_type or campaign.trigger_rule)},"
                        f" derived_entity_key: {_S(campaign.derived_entity_key)},"
                        f" category: {_S(campaign.category)},"
                        f" time_bucket: {_S(campaign.time_bucket)},"
                        f" severity: {_S(campaign.severity)},"
                        f" correlation_window_hours: {_S(campaign.correlation_window_hours)},"
                        f" nl_summary: {_S(campaign.nl_summary)},"
                        f" updated_at_epoch: {ts}"
                        f"}})"
                    ),
                )

            # Write :MEMBER_OF edges. AGE has no MERGE in this path, so keep the
            # existing check-then-create semantics but batch graph round trips.
            member_alert_ids = _dedupe_preserve_order(campaign.member_alert_ids)
            if trace is not None and trace.enabled:
                trace.member_alert_count = len(member_alert_ids)
            if member_alert_ids:
                existing_edges = await _campaign_trace_query(
                    trace,
                    "member_edges_existing_read",
                    "read",
                    self.neo4j.run_query(
                        f"MATCH (a:Alert)-[:MEMBER_OF]->(c:Campaign {{campaign_id: {cid}}})"
                        f" WHERE {_alert_id_or_predicate('a', member_alert_ids)}"
                        f" RETURN a.alert_id AS alert_id"
                    ),
                )
                existing_edge_ids = {
                    row.get("alert_id")
                    for row in (existing_edges or [])
                    if row.get("alert_id") is not None
                }
                missing_edge_ids = [
                    alert_id for alert_id in member_alert_ids
                    if alert_id not in existing_edge_ids
                ]

                if trace is not None and trace.enabled:
                    trace.member_edge_existing_count = len(existing_edge_ids)
                    trace.member_edge_missing_count = len(missing_edge_ids)

                existing_alert_ids: set[str] = set()
                if missing_edge_ids:
                    existing_alerts = await _campaign_trace_query(
                        trace,
                        "member_alert_nodes_read",
                        "read",
                        self.neo4j.run_query(
                            f"MATCH (a:Alert)"
                            f" WHERE {_alert_id_or_predicate('a', missing_edge_ids)}"
                            f" RETURN a.alert_id AS alert_id"
                        ),
                    )
                    existing_alert_ids = {
                        row.get("alert_id")
                        for row in (existing_alerts or [])
                        if row.get("alert_id") is not None
                    }

                creatable_ids = [
                    alert_id for alert_id in missing_edge_ids
                    if alert_id in existing_alert_ids
                ]

                if trace is not None and trace.enabled:
                    trace.member_alert_missing_count = len(missing_edge_ids) - len(creatable_ids)
                    trace.member_edge_create_chunk_count = len(_chunks(creatable_ids, 25))
                    trace.member_edges_created_count = 0

                for chunk in _chunks(creatable_ids, 25):
                    clauses = [f"MATCH (c:Campaign {{campaign_id: {cid}}})"]
                    create_patterns = []
                    for idx, alert_id in enumerate(chunk):
                        alias = f"a{idx}"
                        clauses.append(f"MATCH ({alias}:Alert {{alert_id: {_S(alert_id)}}})")
                        create_patterns.append(f"({alias})-[:MEMBER_OF]->(c)")
                    create_query = (
                        " ".join(clauses)
                        + " CREATE "
                        + ", ".join(create_patterns)
                        + f" RETURN {_S(len(chunk))} AS created_count"
                    )
                    created_rows = await _campaign_trace_query(
                        trace,
                        "member_edges_batch_create",
                        "write",
                        self.neo4j.run_query(create_query),
                    )
                    if trace is not None and trace.enabled:
                        trace.member_edges_created_count = (
                            (trace.member_edges_created_count or 0)
                            + sum(int(row.get("created_count") or 0) for row in (created_rows or []))
                        )
            return True
        except Exception as e:
            log.error(f"write_campaign failed for {campaign.campaign_id}: {e}")
            return False

    async def get_campaigns(
        self, limit: int = 50,
        min_confidence: float = 0.0,
        trigger_rule: Optional[str] = None,
    ) -> List[dict]:
        """Fetch campaign list for GET /api/soc/campaigns."""
        try:
            where_clause = "WHERE c.confidence >= $min_confidence"
            if trigger_rule:
                where_clause += " AND c.trigger_rule = $trigger_rule"
            results = await self.neo4j.run_query(f"""
                MATCH (c:Campaign)
                {where_clause}
                OPTIONAL MATCH (a:Alert)-[:MEMBER_OF]->(c)
                RETURN c, collect(a.alert_id) AS alert_ids
                ORDER BY c.last_seen DESC
                LIMIT $limit
            """, {"min_confidence": min_confidence, "trigger_rule": trigger_rule, "limit": limit})
            return [dict(r) for r in results] if results else []
        except Exception as e:
            log.warning(f"get_campaigns failed: {e}")
            return []

    async def get_campaign_detail(self, campaign_id: str) -> Optional[dict]:
        """Fetch full campaign detail for GET /api/soc/campaigns/{id}."""
        try:
            results = await self.neo4j.run_query("""
                MATCH (c:Campaign {campaign_id: $campaign_id})
                MATCH (a:Alert)-[:MEMBER_OF]->(c)
                OPTIONAL MATCH (d:Decision)-[:DECIDED_ON]->(a)
                RETURN c,
                       collect({
                           alert_id: a.alert_id,
                           alert_type: a.alert_type,
                           technique_id: a.technique_id,
                           category: d.category,
                           action: d.action,
                           confidence: d.confidence,
                           timestamp: d.timestamp_epoch
                       }) AS decisions
            """, {"campaign_id": campaign_id})
            return dict(results[0]) if results else None
        except Exception as e:
            log.warning(f"get_campaign_detail failed: {e}")
            return None

    async def campaigns_exist(self) -> bool:
        """Check if any Campaign nodes exist (for startup recorrelation)."""
        try:
            results = await self.neo4j.run_query(
                "MATCH (c:Campaign) RETURN count(c) AS n LIMIT 1", {}
            )
            return results[0]["n"] > 0 if results else False
        except Exception:
            return False


# ── CampaignMatcher ───────────────────────────────────────────────────────────

class CampaignMatcher:
    """
    Real-time: called after write_decision_to_graph() on each new alert.
    Checks if new alert joins existing campaign or starts a new one.
    Never blocks alert processing — all failures are logged and swallowed.
    """

    def __init__(self, neo4j, config: dict,
                 engine: CampaignCorrelationEngine,
                 repo: CampaignRepository):
        self.neo4j = neo4j
        self.config = config
        self.engine = engine
        self.repo = repo

    async def check_alert(self, alert_id: str) -> Optional[str]:
        """
        Returns campaign_id if alert joined/created a campaign, else None.
        Non-blocking — Exception → log warning → return None.
        """
        trace = CampaignTraceCollector(alert_id)
        campaign_id = None
        try:
            # 1. Fetch recent events + this new alert. Phase 1 campaign reuse is
            # driven by stable identity-keyed candidates and write_campaign's
            # existing check/update path after the rule_type is known.
            recent = await self.repo.fetch_recent_events(
                self.config["correlation_window_hours"],
                trace=trace,
            )
            # Ensure the new alert is included
            if not any(e["alert_id"] == alert_id for e in recent):
                new_event = await self.repo.fetch_single_alert_event(alert_id, trace=trace)
                if new_event:
                    recent.append(new_event)
                    if trace.enabled:
                        trace.recent_event_count = len(recent)

            # 2. Run correlation on recent window
            if len(recent) >= self.config["min_alerts_for_campaign"]:
                campaigns = self.engine.correlate(recent)
                if trace.enabled:
                    trace.candidate_campaign_count = len(campaigns)
                for c in campaigns:
                    if alert_id in c.member_alert_ids:
                        trace.path = "new_campaign"
                        await self.repo.write_campaign(c, trace=trace)
                        campaign_id = c.campaign_id
                        return campaign_id

            trace.path = "no_campaign"
            return None

        except Exception as e:
            log.warning(f"CampaignMatcher.check_alert({alert_id}) failed: {e}")
            trace.path = "unknown"
            return None
        finally:
            trace.emit_summary(campaign_id)

    async def _find_matching_campaign(
        self,
        alert_id: str,
        trace: CampaignTraceCollector | None = None,
    ) -> Optional[str]:
        """Find existing open campaign this alert should join."""
        try:
            results = await _campaign_trace_query(
                trace,
                "find_matching_campaign",
                "read",
                self.neo4j.run_query("""
                    MATCH (a_new:Alert {alert_id: $alert_id})
                    MATCH (a_existing:Alert)-[:MEMBER_OF]->(c:Campaign)
                    WHERE a_existing.source_entity_id IS NOT NULL
                      AND a_existing.source_entity_id = a_new.source_entity_id
                      AND c.last_seen > $cutoff_epoch
                    RETURN c.campaign_id AS campaign_id
                    ORDER BY c.last_seen DESC LIMIT 1
                """, {"alert_id": alert_id,
                      "cutoff_epoch": int((datetime.utcnow().timestamp() - self.config["correlation_window_hours"] * 3600) * 1000)}),
            )
            if trace is not None and trace.enabled:
                trace.candidate_campaign_count = len(results or [])
            return results[0]["campaign_id"] if results else None
        except Exception as e:
            log.warning(f"_find_matching_campaign failed: {e}")
            return None

    async def _add_alert_to_campaign(
        self,
        alert_id: str,
        campaign_id: str,
        trace: CampaignTraceCollector | None = None,
    ) -> None:
        """Add alert to existing campaign, update last_seen + alert_count."""
        try:
            epoch = _S(int(datetime.utcnow().timestamp() * 1000))
            cid = _S(campaign_id)
            aid = _S(alert_id)
            await _campaign_trace_query(
                trace,
                "existing_campaign_update",
                "write",
                self.neo4j.run_query(
                    f"MATCH (c:Campaign {{campaign_id: {cid}}})"
                    f" SET c.last_seen = {epoch}, c.alert_count = c.alert_count + 1"
                ),
            )
            edge_exists = await _campaign_trace_query(
                trace,
                "existing_campaign_edge_check",
                "read",
                self.neo4j.run_query(
                    f"MATCH (a:Alert {{alert_id: {aid}}})"
                    f"-[:MEMBER_OF]->(c:Campaign {{campaign_id: {cid}}}) RETURN a"
                ),
            )
            if not edge_exists:
                await _campaign_trace_query(
                    trace,
                    "existing_campaign_edge_create",
                    "write",
                    self.neo4j.run_query(
                        f"MATCH (a:Alert {{alert_id: {aid}}})"
                        f" MATCH (c:Campaign {{campaign_id: {cid}}})"
                        f" CREATE (a)-[:MEMBER_OF]->(c)"
                    ),
                )
        except Exception as e:
            log.warning(f"_add_alert_to_campaign failed: {e}")
