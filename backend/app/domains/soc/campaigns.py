"""
campaigns.py -- Multi-Alert Campaign Correlation (F6).

Campaign schema, Cypher queries, and pure-Python helper functions.
No AGE calls in this module -- all graph I/O lives in the service layer.

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
from typing import Any, Callable, List, Optional, cast
import asyncio
import warnings
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
    """Convert graph DateTime / epoch int to Python datetime; pass through if already datetime."""
    if isinstance(value, datetime):
        return value
    if hasattr(value, "to_native"):
        return value.to_native()
    # AGE stores timestamps as epoch-millisecond integers
    if isinstance(value, (int, float)) and value > 1e9:
        divisor = 1000 if value > 1e12 else 1  # ms vs s
        return datetime.utcfromtimestamp(value / divisor)
    return value


def _coerce_alert_ids(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                parsed = _json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed if item is not None]
            except Exception:
                return []
        return [stripped] if stripped else []
    return [str(value)]


def _event_epoch_ms(event: dict) -> int:
    ts = event.get("ts")
    if ts is None:
        return int(time.time() * 1000)
    if isinstance(ts, (int, float)):
        return int(ts if ts > 1e12 else ts * 1000)
    if hasattr(ts, "to_native"):
        ts = ts.to_native()
    if isinstance(ts, datetime):
        return int(ts.timestamp() * 1000)
    return int(_ts_to_seconds(ts) * 1000)


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
DEFAULT_CAMPAIGN_SEED_TTL_SECONDS = 7 * 24 * 3600


def campaign_advisory_lock_key(seed_or_campaign_id: str) -> int:
    """Deterministic signed int64 key for PostgreSQL advisory locks."""
    digest = hashlib.sha256(str(seed_or_campaign_id).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


def _acquire_campaign_advisory_xact_lock(tx, identity: str) -> int:
    """Acquire a transaction-scoped PostgreSQL advisory lock on the tx connection."""
    lock_key = campaign_advisory_lock_key(identity)
    tx.execute_sql("SELECT pg_advisory_xact_lock(%s)", (lock_key,))
    return lock_key


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


@dataclass
class CampaignContext:
    """Cache-backed v6.0 display context; not live graph truth."""

    campaign_id: str
    category: str
    first_seen: str
    member_count: int = 0


@dataclass
class CampaignTemporalContext:
    """Process-local Phase 4 temporal context; cache-backed, not live graph truth."""

    campaign_id: str
    previous_campaign_id: str | None = None
    chain_start_campaign_id: str | None = None
    chain_start_bucket: int | None = None
    chain_length_buckets: int = 1
    total_alert_count: int = 0
    member_count_by_campaign: dict[str, int] = field(default_factory=dict)


# ── Cypher queries ───────────────────────────────────────────────────────────

SHARED_ENTITY_QUERY = """
MATCH (d1:Decision)-[:INVOLVES]->(e:Entity)<-[:INVOLVES]-(d2:Decision)
WHERE d1.domain = 'soc'
  AND d2.domain = 'soc'
  AND d1.alert_id <> d2.alert_id
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
WHERE d1.domain = 'soc'
  AND d2.domain = 'soc'
  AND d1.timestamp_epoch >= $window_start
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
WHERE d.domain = 'soc'
  AND d.timestamp_epoch >= $window_start
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
WITH c, [d IN collect(d) WHERE d.domain = 'soc' | d.decision_id] AS decision_ids
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
WITH c, [d IN collect(d) WHERE d.domain = 'soc' | d] AS decisions
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


# ── Helper functions (pure Python, no AGE) ─────────────────────────────────

def make_campaign_id(alert_ids: List[str]) -> str:
    """Legacy alert-set identity; production paths must use the Phase 1 key.

    This compatibility helper is intentionally retained for callers that still
    consume the pre-Phase-2 API.  It is not a campaign-creation identity and
    must not be used for new production paths; use
    :func:`make_campaign_identity_key` instead.
    """
    warnings.warn(
        "make_campaign_id() is legacy-only; use make_campaign_identity_key()",
        DeprecationWarning,
        stacklevel=2,
    )
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


def make_campaign_seed_key(
    rule_type: str,
    derived_entity_key: str,
    category: str,
    time_bucket: int,
) -> str:
    """Distinct Phase 2 seed key from the same Phase 1 identity dimensions."""
    material = (
        "S1:"
        + str(rule_type)
        + "\x00"
        + str(derived_entity_key)
        + "\x00"
        + str(category)
        + "\x00"
        + str(int(time_bucket))
    )
    return "S1-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def campaign_seed_candidate(
    event: dict,
    window_seconds: int,
    rule_type: str = "shared_entity",
) -> dict[str, Any] | None:
    """Build the unmaterialized seed identity for a single Phase 1 event."""
    entity_key = derived_entity_key(event)
    category = event.get("category")
    bucket = campaign_time_bucket(event.get("ts"), window_seconds)
    if not entity_key or not category or bucket is None:
        return None
    campaign_id = make_campaign_identity_key(rule_type, entity_key, category, bucket)
    seed_key = make_campaign_seed_key(rule_type, entity_key, category, bucket)
    return {
        "seed_key": seed_key,
        "campaign_id": campaign_id,
        "rule_type": rule_type,
        "derived_entity_key": entity_key,
        "category": category,
        "time_bucket": bucket,
    }


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

    ts may be a Python datetime, a graph DateTime (has .to_native()), or an
    epoch integer in milliseconds (as written by the migrated epoch fields).
    """
    if isinstance(ts, (int, float)):
        return ts / 1000.0  # epoch millis -> seconds
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
    """Deterministic NL summary. No LLM -- template only."""
    n = len(events)
    cats = list(dict.fromkeys([e["category"] or "unknown" for e in events]))
    ts_values = [_ts_to_seconds(e["ts"]) for e in events]
    dur_hours = int((max(ts_values) - min(ts_values)) / 3600)
    cat_str = " -> ".join(cats)
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
                       additional_rules: List[str] | None = None) -> float:
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
    All methods accept plain dicts -- no AGE dependency in this class.
    AGE queries live in CampaignRepository (Step 5).
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
        all_chains: List[tuple[Any, ...]] = []
        for chain_list in KILL_CHAINS.values():
            all_chains.extend(cast(List[tuple[Any, ...]], chain_list))
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
                        break  # one chain match per entity -- exit chain loop

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
    All AGE I/O for campaigns.
    Reads alert events from Decision/Alert nodes.
    Writes Campaign nodes and :MEMBER_OF edges.
    """

    def __init__(self, graph):
        self.graph = graph
        self.temporal_contexts: dict[str, CampaignTemporalContext] = {}

    def _has_transactional_graph_client(self) -> bool:
        """True for real AGE clients/fakes with class-defined transactions."""
        return callable(getattr(type(self.graph), "run_transaction", None))

    async def _run_campaign_locked_transaction(
        self,
        identity: str,
        operation: Callable[[Callable[[str], list[dict[str, Any]]]], Any],
    ) -> Any:
        """Run campaign AGE writes under a PostgreSQL transaction advisory lock."""
        if not self._has_transactional_graph_client():
            raise RuntimeError(
                "Campaign Phase 2 requires a transaction-capable AGE client "
                "for PostgreSQL advisory-lock race safety."
            )
        run_transaction = self.graph.run_transaction

        def _operation(tx):
            _acquire_campaign_advisory_xact_lock(tx, identity)
            return operation(tx.run_cypher)

        return await run_transaction(_operation)

    def _persist_campaign_seed_locked(
        self,
        run_cypher: Callable[[str], list[dict[str, Any]]],
        seed: dict[str, Any],
        event: dict,
        alert_id: str,
        now_epoch: int,
    ) -> dict[str, Any]:
        seed_key_lit = _S(seed["seed_key"])
        alert_ids = _dedupe_preserve_order([str(alert_id)])

        existing = run_cypher(
            f"MATCH (s:CampaignSeed {{seed_key: {seed_key_lit}}}) RETURN s"
        )
        if existing:
            row = existing[0] or {}
            seed_node = row.get("s", row)
            existing_alert_ids = _coerce_alert_ids(seed_node.get("alert_ids"))
            alert_ids = _dedupe_preserve_order(existing_alert_ids + alert_ids)
            run_cypher(
                f"MATCH (s:CampaignSeed {{seed_key: {seed_key_lit}}})"
                f" SET s.alert_ids = {_S(alert_ids)},"
                f"     s.last_alert_id = {_S(alert_id)},"
                f"     s.last_seen_epoch = {_S(_event_epoch_ms(event))},"
                f"     s.updated_at_epoch = {_S(now_epoch)},"
                f"     s.status = {_S(seed_node.get('status') or 'open')}"
            )
        else:
            run_cypher(
                f"CREATE (s:CampaignSeed {{"
                f" seed_key: {seed_key_lit},"
                f" campaign_id: {_S(seed['campaign_id'])},"
                f" rule_type: {_S(seed['rule_type'])},"
                f" derived_entity_key: {_S(seed['derived_entity_key'])},"
                f" category: {_S(seed['category'])},"
                f" time_bucket: {_S(seed['time_bucket'])},"
                f" status: {_S('open')},"
                f" alert_ids: {_S(alert_ids)},"
                f" first_alert_id: {_S(alert_id)},"
                f" last_alert_id: {_S(alert_id)},"
                f" first_seen_epoch: {_S(_event_epoch_ms(event))},"
                f" last_seen_epoch: {_S(_event_epoch_ms(event))},"
                f" created_at_epoch: {_S(now_epoch)},"
                f" updated_at_epoch: {_S(now_epoch)}"
                f"}})"
            )
        return {**seed, "alert_ids": alert_ids, "status": "open"}

    def _mark_campaign_seed_promoted_locked(
        self,
        run_cypher: Callable[[str], list[dict[str, Any]]],
        campaign: Campaign,
    ) -> None:
        seed_key = make_campaign_seed_key(
            campaign.rule_type or campaign.trigger_rule,
            campaign.derived_entity_key,
            campaign.category,
            campaign.time_bucket,
        )
        now_epoch = int(time.time() * 1000)
        run_cypher(
            f"MATCH (s:CampaignSeed {{seed_key: {_S(seed_key)}}})"
            f" SET s.status = {_S('promoted')},"
            f"     s.campaign_id = {_S(campaign.campaign_id)},"
            f"     s.materialized_at_epoch = {_S(now_epoch)},"
            f"     s.updated_at_epoch = {_S(now_epoch)}"
        )

    def _write_campaign_locked(
        self,
        run_cypher: Callable[[str], list[dict[str, Any]]],
        campaign: Campaign,
    ) -> bool:
        cid = _S(campaign.campaign_id)
        ts = _S(int(datetime.utcnow().timestamp() * 1000))
        existing = run_cypher(
            f"MATCH (c:Campaign {{campaign_id: {cid}}}) RETURN c"
        )
        if existing:
            run_cypher(
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
            )
        else:
            run_cypher(
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
            )

        member_alert_ids = _dedupe_preserve_order(campaign.member_alert_ids)
        if member_alert_ids:
            existing_edges = run_cypher(
                f"MATCH (a:Alert)-[:MEMBER_OF]->(c:Campaign {{campaign_id: {cid}}})"
                f" WHERE {_alert_id_or_predicate('a', member_alert_ids)}"
                f" RETURN a.alert_id AS alert_id"
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

            existing_alert_ids: set[str] = set()
            if missing_edge_ids:
                existing_alerts = run_cypher(
                    f"MATCH (a:Alert)"
                    f" WHERE {_alert_id_or_predicate('a', missing_edge_ids)}"
                    f" RETURN a.alert_id AS alert_id"
                )
                existing_alert_ids = {
                    str(row.get("alert_id"))
                    for row in (existing_alerts or [])
                    if row.get("alert_id") is not None
                }

            creatable_ids = [
                alert_id for alert_id in missing_edge_ids
                if alert_id in existing_alert_ids
            ]
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
                run_cypher(create_query)
        self._write_continues_locked(run_cypher, campaign)
        return True

    @staticmethod
    def _effective_rule_value(rule_type: Any, trigger_rule: Any) -> str:
        rule = str(rule_type).strip() if rule_type is not None else ""
        if rule:
            return rule
        return str(trigger_rule).strip() if trigger_rule is not None else ""

    def _campaign_effective_rule(self, campaign: Campaign) -> str:
        return self._effective_rule_value(campaign.rule_type, campaign.trigger_rule)

    def _write_continues_locked(
        self,
        run_cypher: Callable[[str], list[dict[str, Any]]],
        campaign: Campaign,
    ) -> CampaignTemporalContext | None:
        """Create one strict adjacent-bucket CONTINUES edge under the campaign lock."""
        rule_type = self._campaign_effective_rule(campaign)
        if (
            not campaign.campaign_id
            or not campaign.derived_entity_key
            or not campaign.category
            or not rule_type
            or campaign.time_bucket is None
        ):
            return None

        try:
            current_bucket = int(campaign.time_bucket)
        except (TypeError, ValueError):
            return None
        older_bucket = current_bucket - 1
        now_epoch = int(time.time() * 1000)
        current_count = int(campaign.alert_count or len(campaign.member_alert_ids) or 0)
        context = CampaignTemporalContext(
            campaign_id=str(campaign.campaign_id),
            chain_start_campaign_id=str(campaign.campaign_id),
            chain_start_bucket=current_bucket,
            chain_length_buckets=1,
            total_alert_count=current_count,
            member_count_by_campaign={str(campaign.campaign_id): current_count},
        )

        candidate_rows = run_cypher(
            f"MATCH (older:Campaign)"
            f" WHERE older.derived_entity_key = {_S(campaign.derived_entity_key)}"
            f"   AND older.category = {_S(campaign.category)}"
            f"   AND older.time_bucket = {_S(older_bucket)}"
            f" RETURN older.campaign_id AS campaign_id,"
            f"        older.time_bucket AS time_bucket,"
            f"        older.rule_type AS rule_type,"
            f"        older.trigger_rule AS trigger_rule,"
            f"        older.alert_count AS alert_count"
            f" ORDER BY older.updated_at_epoch DESC"
        )
        older_rows = [
            row for row in (candidate_rows or [])
            if self._effective_rule_value(row.get("rule_type"), row.get("trigger_rule")) == rule_type
        ]
        if not older_rows:
            self.temporal_contexts[str(campaign.campaign_id)] = context
            return context

        older_row = older_rows[0] or {}
        older_campaign_id = older_row.get("campaign_id")
        if not older_campaign_id or str(older_campaign_id) == str(campaign.campaign_id):
            self.temporal_contexts[str(campaign.campaign_id)] = context
            return context

        older_count = int(older_row.get("alert_count") or 0)
        exists = run_cypher(
            f"MATCH (older:Campaign {{campaign_id: {_S(older_campaign_id)}}})"
            f"-[:CONTINUES]->"
            f"(newer:Campaign {{campaign_id: {_S(campaign.campaign_id)}}})"
            f" RETURN older.campaign_id AS campaign_id"
        )
        if not exists:
            run_cypher(
                f"MATCH (older:Campaign {{campaign_id: {_S(older_campaign_id)}}})"
                f" MATCH (newer:Campaign {{campaign_id: {_S(campaign.campaign_id)}}})"
                f" CREATE (older)-[:CONTINUES {{"
                f" created_at_epoch: {_S(now_epoch)},"
                f" gap_buckets: {_S(1)},"
                f" rule_type: {_S(rule_type)}"
                f"}}]->(newer)"
            )

        older_context = self.temporal_contexts.get(str(older_campaign_id))
        chain_start_id = (
            older_context.chain_start_campaign_id
            if older_context and older_context.chain_start_campaign_id
            else str(older_campaign_id)
        )
        chain_start_bucket = (
            older_context.chain_start_bucket
            if older_context and older_context.chain_start_bucket is not None
            else older_bucket
        )
        chain_length = (
            older_context.chain_length_buckets + 1
            if older_context
            else 2
        )
        total_alert_count = (
            older_context.total_alert_count + current_count
            if older_context
            else older_count + current_count
        )
        member_counts = (
            dict(older_context.member_count_by_campaign)
            if older_context
            else {str(older_campaign_id): older_count}
        )
        member_counts[str(campaign.campaign_id)] = current_count
        context = CampaignTemporalContext(
            campaign_id=str(campaign.campaign_id),
            previous_campaign_id=str(older_campaign_id),
            chain_start_campaign_id=chain_start_id,
            chain_start_bucket=chain_start_bucket,
            chain_length_buckets=chain_length,
            total_alert_count=total_alert_count,
            member_count_by_campaign=member_counts,
        )
        self.temporal_contexts[str(campaign.campaign_id)] = context
        return context

    def get_temporal_context(self, campaign_id: str | None) -> CampaignTemporalContext | None:
        if not campaign_id:
            return None
        return self.temporal_contexts.get(str(campaign_id))

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
            results = await self.graph.run_query("""
                MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
                WHERE d.domain = 'soc'
                  AND d.source_id IS NOT NULL AND d.source_id <> 'synthetic'
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
                self.graph.run_query("""
                    MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
                    WHERE d.domain = 'soc'
                      AND d.timestamp_epoch > $cutoff_epoch
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
                self.graph.run_query("""
                    MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert {alert_id: $alert_id})
                    WHERE d.domain = 'soc'
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

    async def persist_campaign_seed(
        self,
        event: dict,
        *,
        rule_type: str = "shared_entity",
        window_seconds: int = 24 * 3600,
        trace: CampaignTraceCollector | None = None,
    ) -> dict[str, Any] | None:
        """
        Persist the unmaterialized Phase 2 CampaignSeed for one alert.

        AGE writes intentionally avoid MERGE, $params, Cypher datetime(), and
        destructive deletes. Duplicate prevention is MATCH-then-CREATE by
        seed_key, with alert_ids updated idempotently for display/cleanup only.
        """
        seed = cast(
            dict[str, Any] | None,
            campaign_seed_candidate(event, window_seconds, rule_type=rule_type),
        )
        if seed is None:
            return None

        alert_id = event.get("alert_id")
        if not alert_id:
            return None

        now_epoch = int(time.time() * 1000)
        try:
            if not self._has_transactional_graph_client():
                log.debug("CampaignSeed persistence skipped: graph client has no transaction support")
                return {**seed, "alert_ids": [str(alert_id)], "status": "unpersisted"}
            seed_for_persist = cast(dict[str, Any], seed)
            return cast(dict[str, Any], await self._run_campaign_locked_transaction(
                seed_for_persist["seed_key"],
                lambda run_cypher: self._persist_campaign_seed_locked(
                    run_cypher,
                    seed_for_persist,
                    event,
                    str(alert_id),
                    now_epoch,
                ),
            ))
        except Exception as e:
            log.warning(f"persist_campaign_seed failed for {seed_for_persist['seed_key']}: {e}")
            return None

    async def mark_campaign_seed_promoted(
        self,
        campaign: Campaign,
        trace: CampaignTraceCollector | None = None,
    ) -> bool:
        seed_key = make_campaign_seed_key(
            campaign.rule_type or campaign.trigger_rule,
            campaign.derived_entity_key,
            campaign.category,
            campaign.time_bucket,
        )
        try:
            await _campaign_trace_query(
                trace,
                "campaign_seed_promote",
                "write",
                self.graph.run_query(
                    f"MATCH (s:CampaignSeed {{seed_key: {_S(seed_key)}}})"
                    f" SET s.status = {_S('promoted')},"
                    f"     s.campaign_id = {_S(campaign.campaign_id)},"
                    f"     s.materialized_at_epoch = {_S(int(time.time() * 1000))},"
                    f"     s.updated_at_epoch = {_S(int(time.time() * 1000))}"
                ),
            )
            return True
        except Exception as e:
            log.warning(f"mark_campaign_seed_promoted failed for {seed_key}: {e}")
            return False

    async def materialize_seed_campaign(
        self,
        campaign: Campaign,
        trace: CampaignTraceCollector | None = None,
    ) -> bool:
        """
        Race-safe seed promotion into a materialized Campaign.

        The transaction-scoped PostgreSQL advisory lock serializes same-identity
        writers across backend workers before the AGE MATCH-then-CREATE writes.
        """
        try:
            if not self._has_transactional_graph_client():
                return await self.write_campaign(campaign, trace=trace)
            return cast(bool, await self._run_campaign_locked_transaction(
                campaign.campaign_id,
                lambda run_cypher: self._materialize_seed_campaign_locked(
                    run_cypher,
                    campaign,
                ),
            ))
        except Exception as e:
            log.warning(f"materialize_seed_campaign failed for {campaign.campaign_id}: {e}")
            return False

    def _materialize_seed_campaign_locked(
        self,
        run_cypher: Callable[[str], list[dict[str, Any]]],
        campaign: Campaign,
    ) -> bool:
        written = self._write_campaign_locked(run_cypher, campaign)
        if written:
            self._mark_campaign_seed_promoted_locked(run_cypher, campaign)
        return written

    async def cleanup_orphan_campaign_seeds(
        self,
        ttl_seconds: int = DEFAULT_CAMPAIGN_SEED_TTL_SECONDS,
        trace: CampaignTraceCollector | None = None,
    ) -> int:
        """
        Expire old unmaterialized CampaignSeed nodes without deleting graph data.

        AGE deletion semantics are intentionally avoided here. Expired seeds are
        marked status='expired'; Campaign nodes and MEMBER_OF edges are untouched.
        """
        cutoff_epoch = int((time.time() - ttl_seconds) * 1000)
        try:
            rows = await _campaign_trace_query(
                trace,
                "campaign_seed_expire_orphans",
                "write",
                self.graph.run_query(
                    f"MATCH (s:CampaignSeed)"
                    f" WHERE s.status = {_S('open')} AND s.updated_at_epoch < {_S(cutoff_epoch)}"
                    f" SET s.status = {_S('expired')},"
                    f"     s.expired_at_epoch = {_S(int(time.time() * 1000))}"
                    f" RETURN count(s) AS expired_count"
                ),
            )
            if not rows:
                return 0
            return int((rows[0] or {}).get("expired_count") or 0)
        except Exception as e:
            log.warning(f"cleanup_orphan_campaign_seeds failed: {e}")
            return 0

    async def write_campaign(
        self,
        campaign: Campaign,
        trace: CampaignTraceCollector | None = None,
    ) -> bool:
        """
        Write Campaign node and :MEMBER_OF edges to AGE.
        Idempotent -- MATCH-then-CREATE (AGE has no MERGE).
        Returns True on success.
        """
        if self._has_transactional_graph_client():
            try:
                if trace is not None and trace.enabled:
                    trace.member_alert_count = len(campaign.member_alert_ids)
                return cast(bool, await self._run_campaign_locked_transaction(
                    campaign.campaign_id,
                    lambda run_cypher: self._write_campaign_locked(run_cypher, campaign),
                ))
            except Exception as e:
                log.error(f"write_campaign locked transaction failed for {campaign.campaign_id}: {e}")
                return False

        # Phase 4 CONTINUES requires transaction/advisory-lock semantics.
        # Legacy non-transaction fallback intentionally writes only Campaign and
        # MEMBER_OF data; it must not add an unlocked CONTINUES fallback.
        try:
            if trace is not None and trace.enabled:
                trace.member_alert_count = len(campaign.member_alert_ids)
            cid = _S(campaign.campaign_id)
            ts = _S(int(datetime.utcnow().timestamp() * 1000))
            existing = await _campaign_trace_query(
                trace,
                "check_campaign_exists",
                "read",
                self.graph.run_query(
                    f"MATCH (c:Campaign {{campaign_id: {cid}}}) RETURN c"
                ),
            )
            if existing:
                await _campaign_trace_query(
                    trace,
                    "update_campaign",
                    "write",
                    self.graph.run_query(
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
                    self.graph.run_query(
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
                    self.graph.run_query(
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
                        self.graph.run_query(
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
                        self.graph.run_query(create_query),
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
            results = await self.graph.run_query(f"""
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
            results = await self.graph.run_query("""
                MATCH (c:Campaign {campaign_id: $campaign_id})
                OPTIONAL MATCH (a:Alert)-[:MEMBER_OF]->(c)
                OPTIONAL MATCH (d:Decision)-[:DECIDED_ON]->(a)
                WHERE d.domain = 'soc'
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
            results = await self.graph.run_query(
                "MATCH (c:Campaign) RETURN count(c) AS n LIMIT 1", {}
            )
            return bool(results[0]["n"] > 0) if results else False
        except Exception:
            return False


# ── CampaignMatcher ───────────────────────────────────────────────────────────

@dataclass
class CampaignAsyncState:
    """Process-local Phase 3 async state shared by request-created matchers."""

    bg_tasks: set[asyncio.Task] = field(default_factory=set)
    pending_seeds: set[str] = field(default_factory=set)
    pending_seed_campaigns: dict[str, str] = field(default_factory=dict)
    materialized_campaigns: dict[str, str] = field(default_factory=dict)
    campaign_contexts: dict[str, CampaignContext] = field(default_factory=dict)
    temporal_contexts: dict[str, CampaignTemporalContext] = field(default_factory=dict)

    def mark_pending(self, seed_key: str, campaign_id: str) -> bool:
        """Return True when this caller owns scheduling for the seed."""
        if seed_key in self.pending_seeds:
            return False
        self.pending_seeds.add(seed_key)
        self.pending_seed_campaigns[seed_key] = campaign_id
        return True

    def pending_campaign_id(self, seed_key: str) -> str | None:
        if seed_key not in self.pending_seeds:
            return None
        return self.pending_seed_campaigns.get(seed_key)

    def mark_materialized(self, campaign_id: str | None) -> None:
        """Positive-only process-local cache for materialized campaign identities."""
        if campaign_id:
            self.materialized_campaigns[str(campaign_id)] = str(campaign_id)

    def mark_materialized_with_context(
        self,
        campaign_id: str,
        category: str,
        first_seen: str,
        member_count: int = 0,
    ) -> None:
        """Cache campaign display context alongside the materialized id cache."""
        self.mark_materialized(campaign_id)
        if campaign_id:
            self.campaign_contexts[str(campaign_id)] = CampaignContext(
                campaign_id=str(campaign_id),
                category=str(category or ""),
                first_seen=str(first_seen or ""),
                member_count=int(member_count or 0),
            )

    def materialized_campaign_id(self, campaign_id: str | None) -> str | None:
        if not campaign_id:
            return None
        return self.materialized_campaigns.get(str(campaign_id))

    def get_campaign_context(self, campaign_id: str | None) -> CampaignContext | None:
        if not campaign_id:
            return None
        return self.campaign_contexts.get(str(campaign_id))

    def increment_member_count(self, campaign_id: str) -> None:
        context = self.get_campaign_context(campaign_id)
        if context is not None:
            context.member_count += 1

    def mark_temporal_context(self, context: CampaignTemporalContext | None) -> None:
        if context is not None and context.campaign_id:
            self.temporal_contexts[str(context.campaign_id)] = context

    def get_temporal_context(self, campaign_id: str | None) -> CampaignTemporalContext | None:
        if not campaign_id:
            return None
        return self.temporal_contexts.get(str(campaign_id))

    def retain_task(self, task: asyncio.Task) -> None:
        self.bg_tasks.add(task)
        task.add_done_callback(self.bg_tasks.discard)

    def clear_pending(self, seed_key: str) -> None:
        self.pending_seeds.discard(seed_key)
        self.pending_seed_campaigns.pop(seed_key, None)

    def reset_for_tests(self) -> None:
        self.bg_tasks.clear()
        self.pending_seeds.clear()
        self.pending_seed_campaigns.clear()
        self.materialized_campaigns.clear()
        self.campaign_contexts.clear()
        self.temporal_contexts.clear()


_DEFAULT_CAMPAIGN_ASYNC_STATE = CampaignAsyncState()


class CampaignMatcher:
    """
    Real-time: called after write_decision_to_graph() on each new alert.
    Checks if new alert joins existing campaign or starts a new one.
    Never blocks alert processing -- all failures are logged and swallowed.
    """

    def __init__(
        self,
        graph,
        config: dict,
        engine: CampaignCorrelationEngine,
        repo: CampaignRepository,
        background: bool = True,
        async_state: CampaignAsyncState | None = None,
    ):
        self.graph = graph
        self.config = config
        self.engine = engine
        self.repo = repo
        self.background = background
        self.async_state = async_state or (
            _DEFAULT_CAMPAIGN_ASYNC_STATE if background else CampaignAsyncState()
        )

    @property
    def _bg_tasks(self) -> set[asyncio.Task]:
        return self.async_state.bg_tasks

    @property
    def _pending_seeds(self) -> set[str]:
        return self.async_state.pending_seeds

    @property
    def _pending_seed_campaigns(self) -> dict[str, str]:
        return self.async_state.pending_seed_campaigns

    @property
    def _materialized_campaigns(self) -> dict[str, str]:
        return self.async_state.materialized_campaigns

    async def check_alert(self, alert_id: str) -> Optional[str]:
        """
        Returns campaign_id if alert joined/created a campaign, else None.
        Non-blocking -- Exception -> log warning -> return None.
        """
        return await self._check_alert_impl(alert_id)

    async def check_alert_timed(self, alert_id: str) -> dict[str, Any]:
        """Unit-testable timing wrapper for the campaign hot path."""
        started = time.perf_counter()
        campaign_id = await self._check_alert_impl(alert_id)
        return {
            "campaign_id": campaign_id,
            "elapsed_ms": (time.perf_counter() - started) * 1000.0,
            "measurement_mode": "mock/unit",
        }

    async def _check_alert_impl(self, alert_id: str) -> Optional[str]:
        trace = CampaignTraceCollector(alert_id)
        campaign_id = None
        try:
            new_event = await self.repo.fetch_single_alert_event(alert_id, trace=trace)
            if not new_event:
                trace.path = "no_alert_event"
                return None

            campaign_id = self._check_materialized_campaign_cache(new_event)
            if campaign_id:
                trace.path = "materialized_campaign_cache"
                return campaign_id

            campaign_id = self._check_pending_seed(new_event)
            if campaign_id:
                trace.path = "pending_seed"
                return campaign_id

            campaign_id = await self._check_materialized_campaign(new_event, trace=trace)
            if campaign_id:
                trace.path = "materialized_campaign"
                return campaign_id

            if self.background:
                await self._schedule_materialization(alert_id, new_event)
                trace.path = "scheduled_background"
                return None

            trace.path = "inline_materialization"
            campaign_id = await self._materialize_alert(alert_id, new_event)
            return campaign_id

        except Exception as e:
            log.warning(f"CampaignMatcher.check_alert({alert_id}) failed: {e}")
            trace.path = "unknown"
            return None
        finally:
            trace.emit_summary(campaign_id)

    def _shared_entity_seed(self, event: dict) -> dict | None:
        # Phase 3B keeps the existing supported hot-path identity rule; broader
        # rule-type lookup remains a documented P3 until Roadmap scopes it.
        return campaign_seed_candidate(
            event,
            self.engine.window_seconds,
            rule_type="shared_entity",
        )

    def _check_materialized_campaign_cache(self, event: dict) -> Optional[str]:
        """Fast positive lookup before falling back to the AGE read path."""
        seed = self._shared_entity_seed(event)
        if not seed:
            return None
        return self.async_state.materialized_campaign_id(seed["campaign_id"])

    async def _check_materialized_campaign(
        self,
        event: dict,
        trace: CampaignTraceCollector | None = None,
    ) -> Optional[str]:
        """Read-only keyed lookup by Phase 1 stable campaign identity."""
        seed = self._shared_entity_seed(event)
        if not seed:
            return None
        if self.graph is None or not hasattr(self.graph, "run_query"):
            return None
        try:
            rows = await _campaign_trace_query(
                trace,
                "check_materialized_campaign_by_identity",
                "read",
                self.graph.run_query(
                    f"MATCH (c:Campaign {{campaign_id: {_S(seed['campaign_id'])}}}) "
                    f"RETURN c.campaign_id AS campaign_id LIMIT 1"
                ),
            )
            if rows:
                campaign_id = str(rows[0].get("campaign_id") or seed["campaign_id"])
                self.async_state.mark_materialized(campaign_id)
                return campaign_id
            return None
        except Exception as e:
            log.warning(f"_check_materialized_campaign failed: {e}")
            return None

    def _check_pending_seed(self, event: dict) -> Optional[str]:
        """In-memory provisional match for seeds already scheduled in this process."""
        seed = self._shared_entity_seed(event)
        if not seed:
            return None
        return self.async_state.pending_campaign_id(seed["seed_key"]) or (
            seed["campaign_id"] if seed["seed_key"] in self._pending_seeds else None
        )

    async def _schedule_materialization(self, alert_id: str, event: dict) -> Optional[str]:
        seed = self._shared_entity_seed(event)
        if not seed:
            return None
        seed_key = seed["seed_key"]
        if not self.async_state.mark_pending(seed_key, seed["campaign_id"]):
            return cast(str, seed["campaign_id"])
        if not self.background:
            return await self._materialize_in_background(alert_id, seed_key, event)

        task = asyncio.create_task(
            self._materialize_in_background(alert_id, seed_key, event)
        )
        self.async_state.retain_task(task)
        return cast(str, seed["campaign_id"])

    async def _materialize_in_background(
        self,
        alert_id: str,
        seed_key: str,
        event: dict | None = None,
    ) -> Optional[str]:
        try:
            campaign_id = await self._materialize_alert(alert_id, event)
            self.async_state.mark_materialized(campaign_id)
            return campaign_id
        except Exception as e:
            log.warning(
                "Background campaign materialization failed for alert=%s seed=%s: %s",
                alert_id,
                seed_key,
                e,
            )
            return None
        finally:
            self.async_state.clear_pending(seed_key)

    async def _materialize_alert(
        self,
        alert_id: str,
        event: dict | None = None,
        trace: CampaignTraceCollector | None = None,
    ) -> Optional[str]:
        recent = await self.repo.fetch_recent_events(
            self.config["correlation_window_hours"],
            trace=trace,
        )
        if event and not any(e["alert_id"] == alert_id for e in recent):
            recent.append(event)
        elif not event:
            event = next((e for e in recent if e["alert_id"] == alert_id), None)
            if event is None:
                event = await self.repo.fetch_single_alert_event(alert_id, trace=trace)
                if event:
                    recent.append(event)

        if not event:
            return None

        if hasattr(self.repo, "persist_campaign_seed"):
            await self.repo.persist_campaign_seed(
                event,
                rule_type="shared_entity",
                window_seconds=self.engine.window_seconds,
                trace=trace,
            )

        if len(recent) < self.config["min_alerts_for_campaign"]:
            return None

        campaigns = self.engine.correlate(recent)
        for campaign in campaigns:
            if alert_id not in campaign.member_alert_ids:
                continue
            if hasattr(self.repo, "materialize_seed_campaign"):
                written = await self.repo.materialize_seed_campaign(campaign, trace=trace)
            else:
                written = await self.repo.write_campaign(campaign, trace=trace)
            if written:
                self.async_state.mark_materialized_with_context(
                    campaign.campaign_id,
                    campaign.category,
                    campaign.first_seen.isoformat(),
                    campaign.alert_count or len(campaign.member_alert_ids),
                )
                get_temporal_context = getattr(self.repo, "get_temporal_context", None)
                if callable(get_temporal_context):
                    self.async_state.mark_temporal_context(
                        get_temporal_context(campaign.campaign_id)
                    )
            return campaign.campaign_id if written else None
        return None

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
                self.graph.run_query("""
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
                self.graph.run_query(
                    f"MATCH (c:Campaign {{campaign_id: {cid}}})"
                    f" SET c.last_seen = {epoch}, c.alert_count = c.alert_count + 1"
                ),
            )
            edge_exists = await _campaign_trace_query(
                trace,
                "existing_campaign_edge_check",
                "read",
                self.graph.run_query(
                    f"MATCH (a:Alert {{alert_id: {aid}}})"
                    f"-[:MEMBER_OF]->(c:Campaign {{campaign_id: {cid}}}) RETURN a"
                ),
            )
            if not edge_exists:
                await _campaign_trace_query(
                    trace,
                    "existing_campaign_edge_create",
                    "write",
                    self.graph.run_query(
                        f"MATCH (a:Alert {{alert_id: {aid}}})"
                        f" MATCH (c:Campaign {{campaign_id: {cid}}})"
                        f" CREATE (a)-[:MEMBER_OF]->(c)"
                    ),
                )
        except Exception as e:
            log.warning(f"_add_alert_to_campaign failed: {e}")
