"""
support/setup/rebuild_age_graph.py -- Seed the Apache AGE / PostgreSQL graph.

Usage:
    python support/setup/rebuild_age_graph.py --dry-run   # print plan, no DB writes
    python support/setup/rebuild_age_graph.py --live      # run against live AGE graph

REQUIRES:
    GRAPH_BACKEND=age in environment (or export it before running)
    DATABASE_URL=postgresql://user:pass@host:5432/dbname

    Quick-start (set credentials, then run):
        export GRAPH_BACKEND=age
        export DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/soc_copilot
        python support/setup/rebuild_age_graph.py --dry-run
        python support/setup/rebuild_age_graph.py --live

Guard: script refuses to run when GRAPH_BACKEND != age.
Idempotency: all writes use MERGE -- safe to run multiple times.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone

# ── pre-flight: GRAPH_BACKEND guard ──────────────────────────────────────────

GRAPH_BACKEND = os.getenv("GRAPH_BACKEND", "neo4j")
if GRAPH_BACKEND != "age":
    print(
        f"[ERROR] GRAPH_BACKEND={GRAPH_BACKEND!r}. This script only runs against AGE.\n"
        "        Set GRAPH_BACKEND=age and DATABASE_URL=postgresql://... then retry."
    )
    sys.exit(1)

# ── mode flag ─────────────────────────────────────────────────────────────────

_args = set(sys.argv[1:])
DRY_RUN = "--dry-run" in _args
LIVE = "--live" in _args

if not DRY_RUN and not LIVE:
    print(
        "Usage:\n"
        "  python support/setup/rebuild_age_graph.py --dry-run\n"
        "  python support/setup/rebuild_age_graph.py --live\n"
    )
    sys.exit(1)

# ── seed plan ─────────────────────────────────────────────────────────────────

# Deterministic seed data — all strings, no runtime randomness
_NOW_EPOCH = int(datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc).timestamp())
_NOW_ISO = "2026-01-15T12:00:00+00:00"

ALERTS = [
    {
        "alert_id": "ALERT-7823",
        "alert_type": "anomalous_login",
        "category": "credential_access",
        "severity": "high",
        "timestamp": _NOW_ISO,
        "timestamp_epoch": _NOW_EPOCH,
        "source_ip": "203.0.113.45",
        "description": "Anomalous login from unusual location",
    },
    {
        "alert_id": "ALERT-7824",
        "alert_type": "data_exfiltration",
        "category": "exfiltration",
        "severity": "critical",
        "timestamp": _NOW_ISO,
        "timestamp_epoch": _NOW_EPOCH,
        "source_ip": "10.0.0.55",
        "description": "Large outbound data transfer detected",
    },
    {
        "alert_id": "ALERT-7825",
        "alert_type": "lateral_movement",
        "category": "lateral_movement",
        "severity": "medium",
        "timestamp": _NOW_ISO,
        "timestamp_epoch": _NOW_EPOCH,
        "source_ip": "10.0.0.12",
        "description": "Pass-the-hash lateral movement attempt",
    },
    {
        "alert_id": "ALERT-7826",
        "alert_type": "privilege_escalation",
        "category": "privilege_escalation",
        "severity": "high",
        "timestamp": _NOW_ISO,
        "timestamp_epoch": _NOW_EPOCH,
        "source_ip": "10.0.1.33",
        "description": "Privilege escalation via sudo abuse",
    },
    {
        "alert_id": "ALERT-7827",
        "alert_type": "malware_detected",
        "category": "malware",
        "severity": "critical",
        "timestamp": _NOW_ISO,
        "timestamp_epoch": _NOW_EPOCH,
        "source_ip": "10.0.2.77",
        "description": "Ransomware binary detected in-memory",
    },
]

ENTITIES = [
    {"entity_id": "USER-jsmith", "entity_type": "user", "name": "John Smith"},
    {"entity_id": "USER-mbrown", "entity_type": "user", "name": "Mary Brown"},
    {"entity_id": "HOST-dc01", "entity_type": "host", "name": "DC01"},
    {"entity_id": "HOST-ws100", "entity_type": "host", "name": "WS100"},
    {"entity_id": "SVC-api01", "entity_type": "service", "name": "api-service-01"},
]

ASSETS = [
    {
        "asset_id": "LAPTOP-JSMITH",
        "hostname": "LAPTOP-JSMITH",
        "asset_type": "endpoint",
        "criticality": "medium",
        "business_unit": "Finance",
        "os": "Windows 11",
        "owner_id": "jsmith@company.com",
    },
    {
        "asset_id": "SERVER-DC01",
        "hostname": "DC01",
        "asset_type": "server",
        "criticality": "critical",
        "business_unit": "IT",
        "os": "Windows Server 2022",
        "owner_id": "it-ops@company.com",
    },
]

USERS = [
    {
        "user_id": "jsmith@company.com",
        "name": "John Smith",
        "department": "Finance",
        "title": "VP Finance",
        "risk_score": 0.25,
        "is_privileged": True,
    },
    {
        "user_id": "mbrown@company.com",
        "name": "Mary Brown",
        "department": "Engineering",
        "title": "Senior Engineer",
        "risk_score": 0.10,
        "is_privileged": False,
    },
]

LOCATIONS = [
    {"location_id": "LOC-SG", "city": "Singapore", "country": "SG", "is_vpn": True},
    {"location_id": "LOC-US-NY", "city": "New York", "country": "US", "is_vpn": False},
]

ATTACK_PATTERNS = [
    {
        "pattern_id": "ATT-T1078",
        "mitre_id": "T1078",
        "name": "Valid Accounts",
        "tactic": "Initial Access",
    },
    {
        "pattern_id": "ATT-T1003",
        "mitre_id": "T1003",
        "name": "OS Credential Dumping",
        "tactic": "Credential Access",
    },
]

CAMPAIGNS = [
    {
        "campaign_id": "CAMP-APT29-2026",
        "name": "APT29 Q1-2026",
        "actor": "APT29",
        "confidence": 0.72,
    }
]

THREAT_INDICATORS = [
    {
        "indicator_id": "IOC-ip-203.0.113.45",
        "indicator_type": "ip",
        "value": "203.0.113.45",
        "threat_score": 0.85,
        "source": "greynoise",
    },
    {
        "indicator_id": "IOC-hash-abc123",
        "indicator_type": "file_hash",
        "value": "abc123def456",
        "threat_score": 0.95,
        "source": "pulsedive",
    },
]

BEHAVIOR_HISTORIES = [
    {
        "history_id": "BH-jsmith-001",
        "user_id": "jsmith@company.com",
        "avg_login_hour": 9,
        "usual_location": "New York",
        "travel_history": "frequent",
    }
]

# alert_id → entity_id pairs for INVOLVES relationships
INVOLVES_EDGES = [
    ("ALERT-7823", "USER-jsmith"),
    ("ALERT-7824", "USER-mbrown"),
    ("ALERT-7824", "HOST-ws100"),
    ("ALERT-7825", "HOST-dc01"),
    ("ALERT-7826", "SVC-api01"),
    ("ALERT-7827", "HOST-ws100"),
]

# Decisions: (decision_id, alert_id, action, confidence, category)
DECISIONS = [
    ("DEC-7823-01", "ALERT-7823", "escalate", 0.91, "credential_access"),
    ("DEC-7824-01", "ALERT-7824", "contain",  0.87, "exfiltration"),
    ("DEC-7825-01", "ALERT-7825", "escalate", 0.79, "lateral_movement"),
    ("DEC-7826-01", "ALERT-7826", "contain",  0.93, "privilege_escalation"),
    ("DEC-7827-01", "ALERT-7827", "contain",  0.98, "malware"),
]

# Evolution events: (alert_id, entity_id, action, verified_correct, impact, magnitude)
EVOLUTION_EVENTS = [
    ("ALERT-7823", "USER-jsmith", "escalate", True,  0.12, 0.88),
    ("ALERT-7824", "USER-mbrown", "contain",  True,  0.35, 0.75),
    ("ALERT-7825", "HOST-dc01",   "escalate", False, 0.05, 0.40),
    ("ALERT-7826", "SVC-api01",   "contain",  True,  0.28, 0.91),
    ("ALERT-7827", "HOST-ws100",  "contain",  True,  0.50, 0.96),
]

# Distance logs: (decision_id, centroid_dist, pattern_history_val, category_dist)
DISTANCE_LOGS = [
    ("DEC-7823-01", 0.14, 0.82, {"credential_access": 3}),
    ("DEC-7824-01", 0.27, 0.71, {"exfiltration": 2}),
    ("DEC-7825-01", 0.41, 0.59, {"lateral_movement": 1}),
    ("DEC-7826-01", 0.09, 0.88, {"privilege_escalation": 4}),
    ("DEC-7827-01", 0.03, 0.97, {"malware": 5}),
]

# alert_id → asset_id for INVOLVES (asset variant)
ASSET_INVOLVES = [
    ("ALERT-7823", "LAPTOP-JSMITH"),
    ("ALERT-7824", "SERVER-DC01"),
]

# alert_id → user_id for INVOLVES (user variant)
USER_INVOLVES = [
    ("ALERT-7823", "jsmith@company.com"),
    ("ALERT-7824", "mbrown@company.com"),
]

# alert_id → location_id for ORIGINATES_FROM
LOCATION_EDGES = [
    ("ALERT-7823", "LOC-SG"),
    ("ALERT-7824", "LOC-US-NY"),
]

# alert_id → pattern_id for MATCHES
PATTERN_EDGES = [
    ("ALERT-7823", "ATT-T1078"),
    ("ALERT-7825", "ATT-T1003"),
]

# alert_id → campaign_id for PART_OF
CAMPAIGN_EDGES = [
    ("ALERT-7823", "CAMP-APT29-2026"),
    ("ALERT-7824", "CAMP-APT29-2026"),
]

# alert_id → indicator_id for HAS_INDICATOR
INDICATOR_EDGES = [
    ("ALERT-7823", "IOC-ip-203.0.113.45"),
    ("ALERT-7827", "IOC-hash-abc123"),
]

# user_id → history_id for HAS_HISTORY
HISTORY_EDGES = [
    ("jsmith@company.com", "BH-jsmith-001"),
]


# ── dry-run output ────────────────────────────────────────────────────────────

def print_plan() -> None:
    print("\n[DRY-RUN] rebuild_age_graph.py -- seed plan")
    print("=" * 60)
    print(f"  Alerts            : {len(ALERTS)}")
    print(f"  Entities          : {len(ENTITIES)}")
    print(f"  Assets            : {len(ASSETS)}")
    print(f"  Users             : {len(USERS)}")
    print(f"  Locations         : {len(LOCATIONS)}")
    print(f"  AttackPatterns    : {len(ATTACK_PATTERNS)}")
    print(f"  Campaigns         : {len(CAMPAIGNS)}")
    print(f"  ThreatIndicators  : {len(THREAT_INDICATORS)}")
    print(f"  BehaviorHistories : {len(BEHAVIOR_HISTORIES)}")
    print(f"  Decisions         : {len(DECISIONS)}")
    print(f"  EvolutionEvents   : {len(EVOLUTION_EVENTS)}")
    print(f"  DistanceLogs      : {len(DISTANCE_LOGS)}")
    print()
    print("  Relationships:")
    print(f"    INVOLVES (entity)   : {len(INVOLVES_EDGES)}")
    print(f"    INVOLVES (asset)    : {len(ASSET_INVOLVES)}")
    print(f"    INVOLVES (user)     : {len(USER_INVOLVES)}")
    print(f"    ORIGINATES_FROM     : {len(LOCATION_EDGES)}")
    print(f"    MATCHES             : {len(PATTERN_EDGES)}")
    print(f"    PART_OF             : {len(CAMPAIGN_EDGES)}")
    print(f"    HAS_INDICATOR       : {len(INDICATOR_EDGES)}")
    print(f"    HAS_HISTORY         : {len(HISTORY_EDGES)}")
    print()
    print("  DATABASE_URL:", os.getenv("DATABASE_URL", "(default) postgresql://localhost:5432/soc_copilot"))
    print("  AGE_GRAPH_NAME:", os.getenv("AGE_GRAPH_NAME", "soc_graph"))
    print()
    print("[DRY-RUN] No database writes. Re-run with --live to execute.")


# ── live seed ─────────────────────────────────────────────────────────────────

async def run_live() -> None:
    from ci_platform.graph import AGEClient

    client = AGEClient()
    graph = os.getenv("AGE_GRAPH_NAME", "soc_graph")

    # Step 0 — connectivity test
    print(f"\n[STEP 0] Connecting to AGE graph '{graph}'...")
    print(f"         DSN: {os.getenv('DATABASE_URL', 'postgresql://localhost:5432/soc_copilot')}")
    try:
        await client.ensure_graph()
        print(f"[STEP 0] Graph '{graph}' ready.\n")
    except Exception as e:
        print(
            f"\n[ERROR] Cannot connect to PostgreSQL+AGE: {e}\n\n"
            "  Fix: set DATABASE_URL with valid credentials, e.g.:\n"
            "    export DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/soc_copilot\n"
            "    python support/setup/rebuild_age_graph.py --live\n"
        )
        sys.exit(1)

    # Step 1 — Alert nodes
    print(f"[STEP 1] Seeding {len(ALERTS)} Alert nodes...")
    for a in ALERTS:
        await client.run_query(
            """
            MERGE (n:Alert {alert_id: $alert_id})
            SET n.alert_type       = $alert_type,
                n.category         = $category,
                n.severity         = $severity,
                n.timestamp        = $created_at,
                n.timestamp_epoch  = $ts_epoch,
                n.source_ip        = $source_ip,
                n.description      = $description
            """,
            {
                "alert_id":    a["alert_id"],
                "alert_type":  a["alert_type"],
                "category":    a["category"],
                "severity":    a["severity"],
                "created_at":  a["timestamp"],
                "ts_epoch":    a["timestamp_epoch"],
                "source_ip":   a["source_ip"],
                "description": a["description"],
            },
        )
        print(f"  MERGE Alert {a['alert_id']}")

    # Step 2 — Entity nodes
    print(f"\n[STEP 2] Seeding {len(ENTITIES)} Entity nodes...")
    for e in ENTITIES:
        await client.run_query(
            """
            MERGE (n:Entity {entity_id: $eid})
            SET n.entity_type = $etype,
                n.name        = $name
            """,
            {"eid": e["entity_id"], "etype": e["entity_type"], "name": e["name"]},
        )
        print(f"  MERGE Entity {e['entity_id']}")

    # Step 3 — Asset nodes
    print(f"\n[STEP 3] Seeding {len(ASSETS)} Asset nodes...")
    for a in ASSETS:
        await client.run_query(
            """
            MERGE (n:Asset {asset_id: $asset_id})
            SET n.hostname       = $hostname,
                n.asset_type     = $asset_type,
                n.criticality    = $criticality,
                n.business_unit  = $business_unit,
                n.os             = $os,
                n.owner_id       = $owner_id
            """,
            {
                "asset_id":     a["asset_id"],
                "hostname":     a["hostname"],
                "asset_type":   a["asset_type"],
                "criticality":  a["criticality"],
                "business_unit": a["business_unit"],
                "os":           a["os"],
                "owner_id":     a["owner_id"],
            },
        )
        print(f"  MERGE Asset {a['asset_id']}")

    # Step 4 — User nodes
    print(f"\n[STEP 4] Seeding {len(USERS)} User nodes...")
    for u in USERS:
        await client.run_query(
            """
            MERGE (n:User {user_id: $uid})
            SET n.name          = $name,
                n.department    = $dept,
                n.title         = $title,
                n.risk_score    = $risk,
                n.is_privileged = $priv
            """,
            {
                "uid":  u["user_id"],
                "name": u["name"],
                "dept": u["department"],
                "title": u["title"],
                "risk": u["risk_score"],
                "priv": u["is_privileged"],
            },
        )
        print(f"  MERGE User {u['user_id']}")

    # Step 5 — Location nodes
    print(f"\n[STEP 5] Seeding {len(LOCATIONS)} Location nodes...")
    for loc in LOCATIONS:
        await client.run_query(
            """
            MERGE (n:Location {location_id: $lid})
            SET n.city    = $city,
                n.country = $country,
                n.is_vpn  = $vpn
            """,
            {"lid": loc["location_id"], "city": loc["city"],
             "country": loc["country"], "vpn": loc["is_vpn"]},
        )
        print(f"  MERGE Location {loc['location_id']}")

    # Step 6 — AttackPattern nodes
    print(f"\n[STEP 6] Seeding {len(ATTACK_PATTERNS)} AttackPattern nodes...")
    for p in ATTACK_PATTERNS:
        await client.run_query(
            """
            MERGE (n:AttackPattern {pattern_id: $pid})
            SET n.mitre_id = $mitre,
                n.name     = $name,
                n.tactic   = $tactic
            """,
            {"pid": p["pattern_id"], "mitre": p["mitre_id"],
             "name": p["name"], "tactic": p["tactic"]},
        )
        print(f"  MERGE AttackPattern {p['pattern_id']}")

    # Step 7 — Campaign nodes
    print(f"\n[STEP 7] Seeding {len(CAMPAIGNS)} Campaign nodes...")
    for c in CAMPAIGNS:
        await client.run_query(
            """
            MERGE (n:Campaign {campaign_id: $cid})
            SET n.name       = $name,
                n.actor      = $actor,
                n.confidence = $conf
            """,
            {"cid": c["campaign_id"], "name": c["name"],
             "actor": c["actor"], "conf": c["confidence"]},
        )
        print(f"  MERGE Campaign {c['campaign_id']}")

    # Step 8 — ThreatIndicator nodes
    print(f"\n[STEP 8] Seeding {len(THREAT_INDICATORS)} ThreatIndicator nodes...")
    for ti in THREAT_INDICATORS:
        await client.run_query(
            """
            MERGE (n:ThreatIndicator {indicator_id: $iid})
            SET n.indicator_type = $itype,
                n.value          = $val,
                n.threat_score   = $score,
                n.source         = $source
            """,
            {"iid": ti["indicator_id"], "itype": ti["indicator_type"],
             "val": ti["value"], "score": ti["threat_score"], "source": ti["source"]},
        )
        print(f"  MERGE ThreatIndicator {ti['indicator_id']}")

    # Step 9 — BehaviorHistory nodes
    print(f"\n[STEP 9] Seeding {len(BEHAVIOR_HISTORIES)} BehaviorHistory nodes...")
    for bh in BEHAVIOR_HISTORIES:
        await client.run_query(
            """
            MERGE (n:BehaviorHistory {history_id: $hid})
            SET n.user_id         = $uid,
                n.avg_login_hour  = $hour,
                n.usual_location  = $loc,
                n.travel_history  = $travel
            """,
            {"hid": bh["history_id"], "uid": bh["user_id"],
             "hour": bh["avg_login_hour"], "loc": bh["usual_location"],
             "travel": bh["travel_history"]},
        )
        print(f"  MERGE BehaviorHistory {bh['history_id']}")

    # Step 10 — INVOLVES (entity)
    print(f"\n[STEP 10] Seeding {len(INVOLVES_EDGES)} INVOLVES (entity) edges...")
    for alert_id, entity_id in INVOLVES_EDGES:
        await client.run_query(
            """
            MATCH (a:Alert  {alert_id:  $aid})
            MATCH (e:Entity {entity_id: $eid})
            MERGE (a)-[:INVOLVES]->(e)
            """,
            {"aid": alert_id, "eid": entity_id},
        )
        print(f"  MERGE ({alert_id})-[:INVOLVES]->({entity_id})")

    # Step 11 — INVOLVES (asset)
    print(f"\n[STEP 11] Seeding {len(ASSET_INVOLVES)} INVOLVES (asset) edges...")
    for alert_id, asset_id in ASSET_INVOLVES:
        await client.run_query(
            """
            MATCH (a:Alert {alert_id:  $aid})
            MATCH (s:Asset {asset_id: $sid})
            MERGE (a)-[:INVOLVES]->(s)
            """,
            {"aid": alert_id, "sid": asset_id},
        )
        print(f"  MERGE ({alert_id})-[:INVOLVES]->({asset_id})")

    # Step 12 — INVOLVES (user)
    print(f"\n[STEP 12] Seeding {len(USER_INVOLVES)} INVOLVES (user) edges...")
    for alert_id, user_id in USER_INVOLVES:
        await client.run_query(
            """
            MATCH (a:Alert {alert_id: $aid})
            MATCH (u:User  {user_id:  $uid})
            MERGE (a)-[:INVOLVES]->(u)
            """,
            {"aid": alert_id, "uid": user_id},
        )
        print(f"  MERGE ({alert_id})-[:INVOLVES]->({user_id})")

    # Step 13 — ORIGINATES_FROM
    print(f"\n[STEP 13] Seeding {len(LOCATION_EDGES)} ORIGINATES_FROM edges...")
    for alert_id, location_id in LOCATION_EDGES:
        await client.run_query(
            """
            MATCH (a:Alert    {alert_id:    $aid})
            MATCH (l:Location {location_id: $lid})
            MERGE (a)-[:ORIGINATES_FROM]->(l)
            """,
            {"aid": alert_id, "lid": location_id},
        )
        print(f"  MERGE ({alert_id})-[:ORIGINATES_FROM]->({location_id})")

    # Step 14 — MATCHES
    print(f"\n[STEP 14] Seeding {len(PATTERN_EDGES)} MATCHES edges...")
    for alert_id, pattern_id in PATTERN_EDGES:
        await client.run_query(
            """
            MATCH (a:Alert         {alert_id:   $aid})
            MATCH (p:AttackPattern {pattern_id: $pid})
            MERGE (a)-[:MATCHES]->(p)
            """,
            {"aid": alert_id, "pid": pattern_id},
        )
        print(f"  MERGE ({alert_id})-[:MATCHES]->({pattern_id})")

    # Step 15 — PART_OF
    print(f"\n[STEP 15] Seeding {len(CAMPAIGN_EDGES)} PART_OF edges...")
    for alert_id, campaign_id in CAMPAIGN_EDGES:
        await client.run_query(
            """
            MATCH (a:Alert    {alert_id:    $aid})
            MATCH (c:Campaign {campaign_id: $cid})
            MERGE (a)-[:PART_OF]->(c)
            """,
            {"aid": alert_id, "cid": campaign_id},
        )
        print(f"  MERGE ({alert_id})-[:PART_OF]->({campaign_id})")

    # Step 16 — HAS_INDICATOR
    print(f"\n[STEP 16] Seeding {len(INDICATOR_EDGES)} HAS_INDICATOR edges...")
    for alert_id, indicator_id in INDICATOR_EDGES:
        await client.run_query(
            """
            MATCH (a:Alert           {alert_id:     $aid})
            MATCH (t:ThreatIndicator {indicator_id: $tid})
            MERGE (a)-[:HAS_INDICATOR]->(t)
            """,
            {"aid": alert_id, "tid": indicator_id},
        )
        print(f"  MERGE ({alert_id})-[:HAS_INDICATOR]->({indicator_id})")

    # Step 17 — HAS_HISTORY
    print(f"\n[STEP 17] Seeding {len(HISTORY_EDGES)} HAS_HISTORY edges...")
    for user_id, history_id in HISTORY_EDGES:
        await client.run_query(
            """
            MATCH (u:User            {user_id:    $uid})
            MATCH (h:BehaviorHistory {history_id: $hid})
            MERGE (u)-[:HAS_HISTORY]->(h)
            """,
            {"uid": user_id, "hid": history_id},
        )
        print(f"  MERGE ({user_id})-[:HAS_HISTORY]->({history_id})")

    # Step 18 — Decision nodes + TRIGGERED_EVOLUTION
    print(f"\n[STEP 18] Seeding {len(DECISIONS)} Decision nodes via create_decision_trace()...")
    for dec_id, alert_id, action, confidence, category in DECISIONS:
        await client.create_decision_trace(
            decision_id=dec_id,
            alert_id=alert_id,
            action=action,
            confidence=confidence,
            category=category,
            patterns_matched=["pattern_A", "pattern_B"],
        )
        print(f"  MERGE Decision {dec_id}")

    print(f"\n[STEP 19] Seeding {len(EVOLUTION_EVENTS)} TRIGGERED_EVOLUTION edges...")
    for alert_id, entity_id, action, verified, impact, magnitude in EVOLUTION_EVENTS:
        await client.create_evolution_event(
            alert_id=alert_id,
            entity_id=entity_id,
            action=action,
            verified_correct=verified,
            impact=impact,
            magnitude=magnitude,
        )
        print(f"  MERGE ({alert_id})-[:TRIGGERED_EVOLUTION]->({entity_id})")

    # Step 20 — DecisionDistanceLog
    print(f"\n[STEP 20] Seeding {len(DISTANCE_LOGS)} DecisionDistanceLog nodes...")
    for dec_id, dist, phv, cat_dist in DISTANCE_LOGS:
        await client.log_decision_distance(
            decision_id=dec_id,
            centroid_distance_to_canonical=dist,
            pattern_history_value=phv,
            alert_category_distribution=cat_dist,
        )
        print(f"  MERGE DecisionDistanceLog {dec_id}")

    # Step 21 — node count verification
    print("\n[STEP 21] Node count verification...")
    label_counts: dict[str, int] = {}
    for label in [
        "Alert", "Entity", "Asset", "User", "Location",
        "AttackPattern", "Campaign", "ThreatIndicator",
        "BehaviorHistory", "Decision", "DecisionContext",
        "DecisionDistanceLog",
    ]:
        try:
            rows = await client.run_query(
                f"MATCH (n:{label}) RETURN count(n) AS cnt"
            )
            label_counts[label] = int((rows[0].get("cnt") or 0) if rows else 0)
        except Exception as exc:
            label_counts[label] = -1
            print(f"  [WARN] count({label}) failed: {exc}")

    total = sum(v for v in label_counts.values() if v >= 0)
    print()
    for label, cnt in label_counts.items():
        status = "OK" if cnt > 0 else ("WARN" if cnt == 0 else "ERR")
        print(f"  [{status}] {label:<25} {cnt:>4}")
    print(f"\n  Total nodes: {total}")

    if total == 0:
        print("\n[ERROR] Graph is empty after seed -- check AGE query syntax.")
        sys.exit(1)

    print("\n[OK] Graph ready. Run collect_tab_content.py to verify.")


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if DRY_RUN:
        print_plan()
    else:
        # Windows requires SelectorEventLoop for psycopg async
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run_live())
