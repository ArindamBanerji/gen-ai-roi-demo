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
from datetime import datetime
from typing import List, Optional
import logging
import uuid

log = logging.getLogger(__name__)


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
    Campaign IDs are deterministic — same alert set = same campaign_id.
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
          alert_id, category, source_entity_id (nullable),
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
        Rule 2: Group events by source_entity_id. For each group,
        check if the category sequence contains a known kill chain.
        Longest matching chain wins (checked first via length sort).
        One chain match per entity — both loops exit on first match.
        """
        entity_groups: dict = defaultdict(list)
        for e in events:
            if e.get("source_entity_id") and e["alert_id"] not in claimed:
                entity_groups[e["source_entity_id"]].append(e)

        # Flatten all chains, sorted longest first so greedy match is correct
        all_chains: List[tuple] = []
        for chain_list in KILL_CHAINS.values():
            all_chains.extend(chain_list)
        all_chains.sort(key=lambda c: len(c), reverse=True)

        new_campaigns: List[Campaign] = []
        for entity_id, group in entity_groups.items():
            group_sorted = sorted(group, key=lambda e: e["ts"])
            categories = [e["category"] for e in group_sorted]

            for chain in all_chains:
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
                            shared_entities=[entity_id],
                        )
                        new_campaigns.append(campaign)
                        claimed.update(alert_ids)
                        break  # one chain match per entity — exit chain loop

        return new_campaigns, claimed

    def _apply_shared_entity(
        self, events: List[dict], claimed: set
    ) -> tuple:
        """
        Rule 1: Group unclaimed events by source_entity_id within window.
        """
        entity_groups: dict = defaultdict(list)
        for e in events:
            if e.get("source_entity_id") and e["alert_id"] not in claimed:
                entity_groups[e["source_entity_id"]].append(e)

        new_campaigns: List[Campaign] = []
        for entity_id, group in entity_groups.items():
            group_sorted = sorted(group, key=lambda e: e["ts"])
            windowed = self._filter_to_window(group_sorted, self.window_seconds)
            if len(windowed) >= self.min_alerts:
                alert_ids = [e["alert_id"] for e in windowed]
                campaign = self._build_campaign(
                    windowed,
                    trigger_rule="shared_entity",
                    confidence=CONFIDENCE_SHARED_ENTITY,
                    shared_entities=[entity_id],
                )
                new_campaigns.append(campaign)
                claimed.update(alert_ids)

        return new_campaigns, claimed

    def _apply_temporal(
        self, events: List[dict], claimed: set
    ) -> tuple:
        """
        Rule 3: Group unclaimed events by category, then cluster
        by temporal proximity. No shared entity required.
        """
        category_groups: dict = defaultdict(list)
        for e in events:
            if e["alert_id"] not in claimed:
                category_groups[e["category"]].append(e)

        new_campaigns: List[Campaign] = []
        for category, group in category_groups.items():
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
                    new_campaigns.append(campaign)
                    claimed.update(alert_ids)

        return new_campaigns, claimed

    def _build_campaign(
        self, events: List[dict], trigger_rule: str,
        confidence: float, shared_entities: List[str],
    ) -> Campaign:
        alert_ids = [e["alert_id"] for e in events]
        cats = [e["category"] for e in events]
        techniques = [e["technique_id"] for e in events if e.get("technique_id")]
        severities = [e.get("severity", "LOW") for e in events]

        return Campaign(
            campaign_id=make_campaign_id(alert_ids),
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
        )

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
        Fetch all alert events for retroactive correlation.
        Returns list of event dicts compatible with CampaignCorrelationEngine.
        """
        try:
            results = await self.neo4j.run_query("""
                MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
                RETURN COALESCE(a.alert_id, a.id) AS alert_id,
                       d.category AS category,
                       a.source_entity_id AS source_entity_id,
                       a.technique_id AS technique_id,
                       d.timestamp_epoch AS ts,
                       COALESCE(a.severity, 'MEDIUM') AS severity,
                       COALESCE(d.decision_id, d.id) AS decision_id
                ORDER BY ts
            """, {})
            return [{**dict(r), "ts": _to_python_dt(r["ts"])} for r in results] if results else []
        except Exception as e:
            log.warning(f"fetch_all_events failed: {e}")
            return []

    async def fetch_recent_events(
        self, window_hours: int = 24
    ) -> List[dict]:
        """
        Fetch recent unclaimed events for real-time matching.
        """
        try:
            results = await self.neo4j.run_query("""
                MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
                WHERE d.timestamp_epoch > $cutoff_epoch
                RETURN COALESCE(a.alert_id, a.id) AS alert_id,
                       d.category AS category,
                       a.source_entity_id AS source_entity_id,
                       a.technique_id AS technique_id,
                       d.timestamp_epoch AS ts,
                       COALESCE(a.severity, 'MEDIUM') AS severity,
                       COALESCE(d.decision_id, d.id) AS decision_id
                ORDER BY ts
            """, {"cutoff_epoch": int((datetime.utcnow().timestamp() - window_hours * 3600) * 1000)})
            return [{**dict(r), "ts": _to_python_dt(r["ts"])} for r in results] if results else []
        except Exception as e:
            log.warning(f"fetch_recent_events failed: {e}")
            return []

    async def fetch_single_alert_event(self, alert_id: str) -> Optional[dict]:
        """Fetch one alert event by ID."""
        try:
            results = await self.neo4j.run_query("""
                MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert {alert_id: $alert_id})
                RETURN a.id AS alert_id,
                       d.category AS category,
                       a.source_entity_id AS source_entity_id,
                       a.technique_id AS technique_id,
                       d.timestamp_epoch AS ts,
                       COALESCE(a.severity, 'MEDIUM') AS severity,
                       d.id AS decision_id
                LIMIT 1
            """, {"alert_id": alert_id})
            if results:
                r = dict(results[0])
                r["ts"] = _to_python_dt(r["ts"])
                return r
            return None
        except Exception as e:
            log.warning(f"fetch_single_alert_event failed: {e}")
            return None

    async def write_campaign(self, campaign: Campaign) -> bool:
        """
        Write Campaign node and :MEMBER_OF edges to Neo4j.
        Idempotent — MERGE on campaign_id.
        Returns True on success.
        """
        try:
            await self.neo4j.run_query("""
                MERGE (c:Campaign {id: $campaign_id})
                SET c.first_seen = $first_seen,
                    c.last_seen = $last_seen,
                    c.alert_count = $alert_count,
                    c.category_sequence = $category_sequence,
                    c.shared_entities = $shared_entities,
                    c.technique_sequence = $technique_sequence,
                    c.confidence = $confidence,
                    c.trigger_rule = $trigger_rule,
                    c.severity = $severity,
                    c.correlation_window_hours = $correlation_window_hours,
                    c.nl_summary = $nl_summary,
                    c.updated_at_epoch = $updated_at_epoch
            """, {
                "campaign_id": campaign.campaign_id,
                "first_seen": campaign.first_seen.isoformat(),
                "last_seen": campaign.last_seen.isoformat(),
                "alert_count": campaign.alert_count,
                "category_sequence": campaign.category_sequence,
                "shared_entities": campaign.shared_entities,
                "technique_sequence": campaign.technique_sequence,
                "confidence": campaign.confidence,
                "trigger_rule": campaign.trigger_rule,
                "severity": campaign.severity,
                "correlation_window_hours": campaign.correlation_window_hours,
                "nl_summary": campaign.nl_summary,
                "updated_at_epoch": int(datetime.utcnow().timestamp() * 1000),
            })

            # Write :MEMBER_OF edges
            for alert_id in campaign.member_alert_ids:
                await self.neo4j.run_query("""
                    MATCH (a:Alert {alert_id: $alert_id})
                    MATCH (c:Campaign {id: $campaign_id})
                    MERGE (a)-[:MEMBER_OF]->(c)
                """, {"alert_id": alert_id, "campaign_id": campaign.campaign_id})
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
                RETURN c, collect(COALESCE(a.alert_id, a.id)) AS alert_ids
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
                MATCH (c:Campaign {id: $campaign_id})
                MATCH (a:Alert)-[:MEMBER_OF]->(c)
                OPTIONAL MATCH (d:Decision)-[:DECIDED_ON]->(a)
                RETURN c,
                       collect({
                           alert_id: COALESCE(a.alert_id, a.id),
                           alert_type: a.alert_type,
                           technique_id: a.technique_id,
                           category: d.category,
                           action: d.action,
                           confidence: d.confidence,
                           timestamp: d.timestamp
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
        try:
            # 1. Check if alert matches an existing campaign via shared entity
            existing_campaign_id = await self._find_matching_campaign(alert_id)
            if existing_campaign_id:
                await self._add_alert_to_campaign(alert_id, existing_campaign_id)
                return existing_campaign_id

            # 2. Fetch recent unclaimed events + this new alert
            recent = await self.repo.fetch_recent_events(
                self.config["correlation_window_hours"]
            )
            # Ensure the new alert is included
            if not any(e["alert_id"] == alert_id for e in recent):
                new_event = await self.repo.fetch_single_alert_event(alert_id)
                if new_event:
                    recent.append(new_event)

            # 3. Run correlation on recent window
            if len(recent) >= self.config["min_alerts_for_campaign"]:
                campaigns = self.engine.correlate(recent)
                for c in campaigns:
                    if alert_id in c.member_alert_ids:
                        await self.repo.write_campaign(c)
                        return c.campaign_id

            return None

        except Exception as e:
            log.warning(f"CampaignMatcher.check_alert({alert_id}) failed: {e}")
            return None

    async def _find_matching_campaign(
        self, alert_id: str
    ) -> Optional[str]:
        """Find existing open campaign this alert should join."""
        try:
            results = await self.neo4j.run_query("""
                MATCH (a_new:Alert {alert_id: $alert_id})
                MATCH (a_existing:Alert)-[:MEMBER_OF]->(c:Campaign)
                WHERE a_existing.source_entity_id IS NOT NULL
                  AND a_existing.source_entity_id = a_new.source_entity_id
                  AND c.last_seen_epoch > $cutoff_epoch
                RETURN c.id AS campaign_id
                ORDER BY c.last_seen_epoch DESC LIMIT 1
            """, {"alert_id": alert_id,
                  "cutoff_epoch": int((datetime.utcnow().timestamp() - self.config["correlation_window_hours"] * 3600) * 1000)})
            return results[0]["campaign_id"] if results else None
        except Exception as e:
            log.warning(f"_find_matching_campaign failed: {e}")
            return None

    async def _add_alert_to_campaign(
        self, alert_id: str, campaign_id: str
    ) -> None:
        """Add alert to existing campaign, update last_seen + alert_count."""
        try:
            await self.neo4j.run_query("""
                MATCH (a:Alert {alert_id: $alert_id})
                MATCH (c:Campaign {id: $campaign_id})
                MERGE (a)-[:MEMBER_OF]->(c)
                SET c.last_seen_epoch = $last_seen_epoch,
                    c.alert_count = c.alert_count + 1
            """, {"alert_id": alert_id, "campaign_id": campaign_id,
                  "last_seen_epoch": int(datetime.utcnow().timestamp() * 1000)})
        except Exception as e:
            log.warning(f"_add_alert_to_campaign failed: {e}")
