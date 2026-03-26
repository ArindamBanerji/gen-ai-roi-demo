"""
campaigns.py — Multi-Alert Campaign Correlation (F6).

Campaign schema, Cypher queries, and pure-Python helper functions.
No Neo4j calls in this module — all graph I/O lives in the service layer.

Confidence model:
  technique_sequence  0.85  (kill-chain pattern matched)
  shared_entity       0.70  (common asset/user/host across alerts)
  temporal            0.45  (time-proximity only)
  multi-rule boost   +0.10  capped at 0.95
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import uuid


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


# ── Cypher queries ───────────────────────────────────────────────────────────

SHARED_ENTITY_QUERY = """
MATCH (d1:Decision)-[:INVOLVES]->(e:Entity)<-[:INVOLVES]-(d2:Decision)
WHERE d1.alert_id <> d2.alert_id
  AND d1.created_at >= $window_start
  AND d2.created_at >= $window_start
WITH e, collect(DISTINCT d1) + collect(DISTINCT d2) AS decisions
WHERE size(decisions) >= 2
RETURN
    e.id                                       AS shared_entity,
    e.type                                     AS entity_type,
    [d IN decisions | d.alert_id]              AS alert_ids,
    [d IN decisions | d.id]                    AS decision_ids,
    [d IN decisions | d.category]              AS categories,
    [d IN decisions | d.severity]              AS severities,
    [d IN decisions | d.created_at]            AS timestamps
ORDER BY size(decisions) DESC
LIMIT $limit
"""

TECHNIQUE_SEQUENCE_QUERY = """
MATCH path = (d1:Decision)-[:TRIGGERED_EVOLUTION*1..5]->(d2:Decision)
WHERE d1.created_at >= $window_start
  AND d2.created_at >= $window_start
  AND d1.alert_id <> d2.alert_id
WITH
    [node IN nodes(path) WHERE node:Decision | node] AS chain_nodes
WHERE size(chain_nodes) >= 2
RETURN
    [n IN chain_nodes | n.alert_id]   AS alert_ids,
    [n IN chain_nodes | n.id]         AS decision_ids,
    [n IN chain_nodes | n.category]   AS categories,
    [n IN chain_nodes | n.severity]   AS severities,
    [n IN chain_nodes | n.created_at] AS timestamps
LIMIT $limit
"""

TEMPORAL_QUERY = """
MATCH (d:Decision)
WHERE d.created_at >= $window_start
  AND d.created_at <= $window_end
WITH d ORDER BY d.created_at ASC
WITH collect(d) AS decisions
UNWIND range(0, size(decisions) - 2) AS i
WITH decisions[i] AS d1, decisions[i+1] AS d2
WHERE duration.inSeconds(d1.created_at, d2.created_at).seconds <= $window_seconds
  AND d1.category = d2.category
RETURN
    d1.category                          AS category,
    [d1.alert_id, d2.alert_id]           AS alert_ids,
    [d1.id, d2.id]                       AS decision_ids,
    [d1.severity, d2.severity]           AS severities,
    [d1.created_at, d2.created_at]       AS timestamps
LIMIT $limit
"""

GET_CAMPAIGNS_QUERY = """
MATCH (c:Campaign)
OPTIONAL MATCH (c)-[:CONTAINS]->(d:Decision)
WITH c, collect(d.id) AS decision_ids
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
OPTIONAL MATCH (c)-[:CONTAINS]->(d:Decision)
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
    [d IN decisions | d.id]    AS member_decision_ids,
    c.correlation_window_hours AS correlation_window_hours,
    c.nl_summary               AS nl_summary,
    [d IN decisions | {
        id: d.id,
        alert_id: d.alert_id,
        category: d.category,
        action: d.action,
        confidence: d.confidence,
        created_at: d.created_at
    }] AS decision_details
"""


# ── Helper functions (pure Python, no Neo4j) ─────────────────────────────────

def make_campaign_id(alert_ids: List[str]) -> str:
    """Deterministic UUID5 from sorted alert IDs — order-independent."""
    return str(uuid.uuid5(uuid.NAMESPACE_OID, ",".join(sorted(alert_ids))))


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


def sliding_window_cluster(alerts: list, window_seconds: int) -> List[list]:
    """Group alerts into time-proximity clusters."""
    if not alerts:
        return []
    clusters = [[alerts[0]]]
    for alert in alerts[1:]:
        last_ts = clusters[-1][-1]["ts"]
        delta = (alert["ts"] - last_ts).total_seconds()
        if delta <= window_seconds:
            clusters[-1].append(alert)
        else:
            clusters.append([alert])
    return clusters


def build_nl_summary(events: list, shared_entities: List[str],
                     trigger_rule: str) -> str:
    """Deterministic NL summary. No LLM — template only."""
    n = len(events)
    cats = list(dict.fromkeys([e["category"] for e in events]))
    dur_hours = int(
        (max(e["ts"] for e in events) -
         min(e["ts"] for e in events)).total_seconds() / 3600
    )
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
