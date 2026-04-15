"""
support/setup/seed_zero_day.py — Load zero-day synthetic decisions into AGE.

Usage:
    python support/setup/seed_zero_day.py --dry-run
    python support/setup/seed_zero_day.py --live [--clean] [--file=path]

REQUIRES: GRAPH_BACKEND=age
"""
from __future__ import annotations
import asyncio, json, os, sys
from collections import Counter
from pathlib import Path

GRAPH_BACKEND = os.getenv("GRAPH_BACKEND", "neo4j")
if GRAPH_BACKEND != "age":
    print(f"[ERROR] GRAPH_BACKEND={GRAPH_BACKEND!r}. Set GRAPH_BACKEND=age.")
    sys.exit(1)

_args = set(sys.argv[1:])
DRY_RUN = "--dry-run" in _args
LIVE = "--live" in _args
CLEAN = "--clean" in _args
BACKFILL = "--backfill" in _args
BACKBONE = "--backbone" in _args
if not DRY_RUN and not LIVE and not BACKFILL and not BACKBONE:
    print("Usage: --dry-run or --live [--clean] [--file=path]")
    print("       --backfill  (SET correct/outcome on existing zero_day_synthetic nodes)")
    print("       --backbone  (seed Users, Assets, demo Alerts, Campaigns for Tab 1 queue)")
    sys.exit(1)

_file_arg = [a for a in sys.argv[1:] if a.startswith("--file=")]
_json_path = (
    Path(_file_arg[0].split("=", 1)[1]) if _file_arg
    else Path(__file__).parent / "zero_day_decisions.json"
)
if not _json_path.exists():
    print(f"[ERROR] Not found: {_json_path}")
    sys.exit(1)

with open(_json_path, "r", encoding="utf-8") as f:
    data = json.load(f)
alerts = data["alerts"]
decisions = data["decisions"]
metadata = data.get("metadata", {})
print(f"[INFO] {len(alerts)} alerts, {len(decisions)} decisions from {_json_path.name}")
if metadata:
    print(f"[INFO] Generator: {metadata.get('generator','?')}, days: {metadata.get('days_simulated','?')}")


def print_plan():
    cats = Counter(d["category"] for d in decisions)
    print(f"\n[DRY-RUN] Create {len(alerts)} Alerts + {len(decisions)} Decisions:")
    for cat, n in cats.most_common():
        c = sum(1 for d in decisions if d["category"] == cat and d["correct"])
        print(f"  {cat}: {n} ({c}/{n} = {c/n:.0%} correct)")

    errors = []
    aids = {a["alert_id"] for a in alerts}
    for i, d in enumerate(decisions):
        if not d.get("decision_id"):
            errors.append(f"[{i}]: no decision_id")
        if d.get("alert_id") not in aids:
            errors.append(f"[{i}]: orphan alert_id {d.get('alert_id')}")
        fv = d.get("factor_vector")
        if not isinstance(fv, list) or len(fv) != 6:
            errors.append(f"[{i}]: bad factor_vector (len={len(fv) if isinstance(fv,list) else type(fv).__name__})")
        if d.get("action") not in ("escalate", "investigate", "suppress", "monitor"):
            errors.append(f"[{i}]: bad action '{d.get('action')}'")
        if len(errors) >= 10:
            break

    if errors:
        print(f"\n  [ERRORS] {len(errors)} issues found:")
        for e in errors:
            print(f"    {e}")
    else:
        print(f"\n  [OK] All {len(decisions)} decisions passed validation.")
    print(f"\n  No changes made. Run with --live to load.")


async def run_live():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from ci_platform.graph.age_client import AGEClient
    client = AGEClient()
    S = AGEClient.serialize_for_age

    try:
        await client.ensure_graph()
        print("[OK] AGE connected.\n")
    except Exception as e:
        print(f"[ERROR] Cannot connect: {e}")
        sys.exit(1)

    if CLEAN:
        print("[CLEAN] Deleting existing zero_day_synthetic nodes...")
        await client.run_query(
            "MATCH (d:Decision {origin: 'zero_day_synthetic'}) DETACH DELETE d"
        )
        await client.run_query(
            "MATCH (a:Alert {origin: 'zero_day_synthetic'}) DETACH DELETE a"
        )
        print("[CLEAN] Done.\n")

    ex = await client.run_query(
        "MATCH (a:Alert) WHERE a.alert_id STARTS WITH 'SYN-' RETURN count(a) AS cnt"
    )
    if int(ex[0]["cnt"]) > 0 and not CLEAN:
        print(f"[WARN] {ex[0]['cnt']} synthetic alerts already exist. Use --clean or Ctrl+C.")
        import time
        time.sleep(3)

    print(f"[STEP 1] Creating {len(alerts)} alerts...")
    for i, a in enumerate(alerts):
        await client.run_query(
            f"CREATE (n:Alert {{"
            f"alert_id: {S(a['alert_id'])}, category: {S(a['category'])},"
            f"severity: {S(a.get('severity', 'medium'))},"
            f"alert_type: {S(a.get('alert_type', a['category']))},"
            f"timestamp_epoch: {S(a['timestamp_epoch'])},"
            f"origin: 'zero_day_synthetic',"
            f"source_location: {S(a.get('source_location', 'synthetic'))},"
            f"user_id: {S(a.get('user_id', ''))}, status: 'decided'"
            f"}})"
        )
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(alerts)} alerts...")

    print(f"[STEP 2] Creating {len(decisions)} decisions with DECIDED_ON edges...")
    ok, fail = 0, 0
    for d in decisions:
        try:
            await client.run_query(
                f"MATCH (a:Alert {{alert_id: {S(d['alert_id'])}}}) "
                f"CREATE (dd:Decision {{"
                f"decision_id: {S(d['decision_id'])}, category: {S(d['category'])},"
                f"action: {S(d['action'])}, factor_vector: {S(d['factor_vector'])},"
                f"confidence: {S(d['confidence'])}, correct: {S(d['correct'])},"
                f"outcome: {S(d['outcome'])}, timestamp_epoch: {S(d['timestamp_epoch'])},"
                f"origin: 'zero_day_synthetic',"
                f"source_id: {S(d.get('source_id', 'synthetic'))},"
                f"user_id: {S(d.get('user_id', ''))}"
                f"}}) CREATE (dd)-[:DECIDED_ON]->(a)"
            )
            ok += 1
        except Exception as e:
            fail += 1
            if fail <= 5:
                print(f"  [WARN] {d['decision_id']}: {e}")
        if (ok + fail) % 500 == 0:
            print(f"  {ok} ok, {fail} fail...")

    print(f"\n[STEP 3] Verification:")
    for lbl, q in [
        ("Syn alerts", "MATCH (a:Alert {origin: 'zero_day_synthetic'}) RETURN count(a) AS cnt"),
        ("Syn decisions", "MATCH (d:Decision {origin: 'zero_day_synthetic'}) RETURN count(d) AS cnt"),
        ("With DECIDED_ON", "MATCH (d:Decision {origin: 'zero_day_synthetic'})-[:DECIDED_ON]->() RETURN count(d) AS cnt"),
        ("Orphans (must=0)", "MATCH (d:Decision) WHERE NOT EXISTS((d)-[:DECIDED_ON]->()) RETURN count(d) AS cnt"),
        ("Total decisions", "MATCH (d:Decision) RETURN count(d) AS cnt"),
    ]:
        r = await client.run_query(q)
        print(f"  {lbl}: {r[0]['cnt']}")
    print("\n[OK] Done. Restart uvicorn.")


async def run_backfill():
    """
    SET correct and outcome on existing zero_day_synthetic Decision nodes that
    were created by an older version of this script before those properties were added.

    Reads the correct/outcome values from zero_day_decisions.json (the canonical source)
    and applies them in batches of 200 using inline decision_id literals.
    """
    from ci_platform.graph.age_client import AGEClient
    client = AGEClient()
    await client.ensure_graph()

    rows = await client.run_query(
        "MATCH (d:Decision {origin: 'zero_day_synthetic'}) "
        "WHERE d.correct IS NULL "
        "RETURN count(d) AS cnt"
    )
    need = int(rows[0]["cnt"]) if rows else 0
    print(f"[BACKFILL] {need} zero_day_synthetic nodes missing correct/outcome.")
    if need == 0:
        print("[BACKFILL] Nothing to do.")
        return

    correct_ids   = [d["decision_id"] for d in decisions if d["correct"]]
    incorrect_ids = [d["decision_id"] for d in decisions if not d["correct"]]
    print(f"[BACKFILL] From JSON: {len(correct_ids)} correct, {len(incorrect_ids)} incorrect.")

    BATCH = 200
    updated = 0

    for i in range(0, len(correct_ids), BATCH):
        batch = correct_ids[i : i + BATCH]
        id_lit = ", ".join(f"'{did}'" for did in batch)
        await client.run_query(
            f"MATCH (d:Decision) WHERE d.decision_id IN [{id_lit}] "
            f"SET d.correct = true, d.outcome = 'correct'"
        )
        updated += len(batch)
        if updated % 1000 < BATCH:
            print(f"  {updated} updated...")

    for i in range(0, len(incorrect_ids), BATCH):
        batch = incorrect_ids[i : i + BATCH]
        id_lit = ", ".join(f"'{did}'" for did in batch)
        await client.run_query(
            f"MATCH (d:Decision) WHERE d.decision_id IN [{id_lit}] "
            f"SET d.correct = false, d.outcome = 'incorrect'"
        )
        updated += len(batch)
        if updated % 1000 < BATCH:
            print(f"  {updated} updated...")

    print(f"[BACKFILL] SET complete: {updated} nodes processed.")

    # Verification
    r1 = await client.run_query(
        "MATCH (d:Decision) WHERE d.correct = true RETURN count(d) AS cnt"
    )
    r2 = await client.run_query(
        "MATCH (d:Decision {origin: 'zero_day_synthetic'}) WHERE d.correct = true RETURN count(d) AS cnt"
    )
    r3 = await client.run_query(
        "MATCH (d:Decision) WHERE d.outcome IS NOT NULL RETURN count(d) AS cnt"
    )
    print(f"[VERIFY] correct=true (all origins):    {r1[0]['cnt']}")
    print(f"[VERIFY] correct=true (zero_day only):  {r2[0]['cnt']}")
    print(f"[VERIFY] outcome IS NOT NULL:            {r3[0]['cnt']}")
    print("[OK] Backfill complete. Restart uvicorn.")


# ── Backbone demo data ────────────────────────────────────────────────────────
# 20 interactive demo alerts (origin='demo_backbone', status='pending').
# These populate Tab 1 queue. Users and Assets are MERGED idempotently.
# Campaigns group related alerts for Tab 6.

_BACKBONE_BASE_MS = 1744502400000  # 2026-04-12 12:00:00 UTC

DEMO_USERS = [
    {"user_id": "USR-001", "name": "Jane Smith",    "department": "Finance"},
    {"user_id": "USR-002", "name": "Alex Garcia",   "department": "IT"},
    {"user_id": "USR-003", "name": "Michael Lee",   "department": "HR"},
    {"user_id": "USR-004", "name": "Rachel Chen",   "department": "Security"},
    {"user_id": "USR-005", "name": "Dev Kumar",     "department": "Engineering"},
    {"user_id": "USR-006", "name": "Lisa Wilson",   "department": "Executive"},
]

DEMO_ASSETS = [
    {"asset_id": "AST-001", "hostname": "ws-finance-01.corp",    "asset_type": "workstation", "os": "Windows 11"},
    {"asset_id": "AST-002", "hostname": "srv-db-01.corp",        "asset_type": "server",      "os": "Ubuntu 22.04"},
    {"asset_id": "AST-003", "hostname": "srv-web-02.corp",       "asset_type": "server",      "os": "Ubuntu 22.04"},
    {"asset_id": "AST-004", "hostname": "ws-hr-03.corp",         "asset_type": "workstation", "os": "Windows 11"},
    {"asset_id": "AST-005", "hostname": "srv-vpn-01.corp",       "asset_type": "server",      "os": "CentOS 7"},
    {"asset_id": "AST-006", "hostname": "laptop-exec-01.corp",   "asset_type": "laptop",      "os": "macOS 14"},
    {"asset_id": "AST-007", "hostname": "srv-cloud-aws-01.corp", "asset_type": "cloud",       "os": "Amazon Linux 2"},
    {"asset_id": "AST-008", "hostname": "srv-email-01.corp",     "asset_type": "server",      "os": "Ubuntu 20.04"},
]

# (alert_id, category, severity, user_id, asset_id, ts_offset_ms)
_DEMO_ALERT_ROWS = [
    ("DEMO-CA-001", "credential_access",    "high",     "USR-001", "AST-001",         0),
    ("DEMO-LM-001", "lateral_movement",     "high",     "USR-001", "AST-002",   600_000),
    ("DEMO-DE-001", "data_exfiltration",    "critical", "USR-001", "AST-002", 1_200_000),
    ("DEMO-CA-002", "credential_access",    "medium",   "USR-002", "AST-005", 2_000_000),
    ("DEMO-ME-001", "malware_execution",    "critical", "USR-003", "AST-004", 2_600_000),
    ("DEMO-IT-001", "insider_threat",       "high",     "USR-004", "AST-008", 3_200_000),
    ("DEMO-CI-001", "cloud_infrastructure", "high",     "USR-005", "AST-007", 3_800_000),
    ("DEMO-LM-002", "lateral_movement",     "medium",   "USR-001", "AST-003", 4_400_000),
    ("DEMO-CA-003", "credential_access",    "low",      "USR-006", "AST-006", 5_000_000),
    ("DEMO-DE-002", "data_exfiltration",    "high",     "USR-005", "AST-007", 5_600_000),
    ("DEMO-ME-002", "malware_execution",    "high",     "USR-002", "AST-001", 6_200_000),
    ("DEMO-IT-002", "insider_threat",       "critical", "USR-004", "AST-002", 6_800_000),
    ("DEMO-CI-002", "cloud_infrastructure", "medium",   "USR-006", "AST-007", 7_400_000),
    ("DEMO-CA-004", "credential_access",    "high",     "USR-003", "AST-005", 8_000_000),
    ("DEMO-LM-003", "lateral_movement",     "critical", "USR-002", "AST-002", 8_600_000),
    ("DEMO-DE-003", "data_exfiltration",    "medium",   "USR-001", "AST-008", 9_200_000),
    ("DEMO-ME-003", "malware_execution",    "medium",   "USR-005", "AST-004", 9_800_000),
    ("DEMO-IT-003", "insider_threat",       "high",     "USR-004", "AST-006", 10_400_000),
    ("DEMO-CI-003", "cloud_infrastructure", "critical", "USR-003", "AST-007", 11_000_000),
    ("DEMO-CA-005", "credential_access",    "medium",   "USR-006", "AST-008", 11_600_000),
]

DEMO_ALERTS = [
    {
        "alert_id":        aid,
        "category":        cat,
        "severity":        sev,
        "alert_type":      cat,
        "user_id":         uid,
        "asset_id":        asid,
        "timestamp_epoch": _BACKBONE_BASE_MS + ts_off,
        "origin":          "demo_backbone",
        "source_location": "corp-network",
        "status":          "pending",
    }
    for aid, cat, sev, uid, asid, ts_off in _DEMO_ALERT_ROWS
]

DEMO_CAMPAIGNS = [
    {
        "campaign_id":             "CAMP-APT29-2026",
        "severity":                "HIGH",
        "confidence":              0.87,
        "trigger_rule":            "sequential_category",
        "category_sequence":       ["credential_access", "lateral_movement", "data_exfiltration"],
        "shared_entities":         [],
        "technique_sequence":      [],
        "nl_summary":              "Nation-state APT29 campaign: credential theft to lateral movement to data exfiltration chain.",
        "member_alert_ids":        ["DEMO-CA-001", "DEMO-LM-001", "DEMO-DE-001", "DEMO-LM-002", "DEMO-LM-003"],
        "correlation_window_hours": 24,
        "first_seen":              "2026-04-12T12:00:00",
        "last_seen":               "2026-04-12T14:13:20",
    },
    {
        "campaign_id":             "CAMP-INSIDER-Q1",
        "severity":                "HIGH",
        "confidence":              0.78,
        "trigger_rule":            "shared_user",
        "category_sequence":       ["insider_threat", "data_exfiltration"],
        "shared_entities":         ["USR-004"],
        "technique_sequence":      [],
        "nl_summary":              "Insider threat Q1: repeated policy violations by same user across email and database assets.",
        "member_alert_ids":        ["DEMO-IT-001", "DEMO-IT-002", "DEMO-IT-003", "DEMO-DE-003"],
        "correlation_window_hours": 168,
        "first_seen":              "2026-04-12T12:53:20",
        "last_seen":               "2026-04-12T14:33:20",
    },
    {
        "campaign_id":             "CAMP-CLOUD-BREACH",
        "severity":                "CRITICAL",
        "confidence":              0.91,
        "trigger_rule":            "shared_asset",
        "category_sequence":       ["cloud_infrastructure", "data_exfiltration"],
        "shared_entities":         ["AST-007"],
        "technique_sequence":      [],
        "nl_summary":              "Cloud infrastructure breach: repeated access to cloud asset followed by data exfiltration.",
        "member_alert_ids":        ["DEMO-CI-001", "DEMO-CI-002", "DEMO-CI-003", "DEMO-DE-002"],
        "correlation_window_hours": 72,
        "first_seen":              "2026-04-12T13:03:20",
        "last_seen":               "2026-04-12T15:03:20",
    },
]


async def seed_graph_backbone():
    """
    Seed the interactive demo graph backbone:
      - 6 User nodes (MERGE, idempotent)
      - 8 Asset nodes (MERGE, idempotent)
      - 20 Alert nodes (origin='demo_backbone', status='pending') (MERGE)
      - INVOLVES edges: Alert → User
      - DETECTED_ON edges: Alert → Asset
      - 3 Campaign nodes + MEMBER_OF edges: Alert → Campaign

    Use --clean to wipe existing backbone nodes before re-seeding.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from ci_platform.graph.age_client import AGEClient
    client = AGEClient()
    S = AGEClient.serialize_for_age

    try:
        await client.ensure_graph()
        print("[OK] AGE connected.\n")
    except Exception as e:
        print(f"[ERROR] Cannot connect: {e}")
        sys.exit(1)

    if CLEAN:
        print("[CLEAN] Removing existing backbone nodes...")
        await client.run_query("MATCH (a:Alert {origin: 'demo_backbone'}) DETACH DELETE a")
        await client.run_query(
            "MATCH (u:User) WHERE u.user_id STARTS WITH 'USR-' DETACH DELETE u"
        )
        await client.run_query(
            "MATCH (a:Asset) WHERE a.asset_id STARTS WITH 'AST-' DETACH DELETE a"
        )
        await client.run_query(
            "MATCH (c:Campaign) WHERE c.campaign_id STARTS WITH 'CAMP-' DETACH DELETE c"
        )
        print("[CLEAN] Done.\n")

    # Step 1: MERGE User nodes
    print(f"[STEP 1] Merging {len(DEMO_USERS)} User nodes...")
    for u in DEMO_USERS:
        await client.run_query(
            f"MERGE (u:User {{user_id: {S(u['user_id'])}}}) "
            f"SET u.name = {S(u['name'])}, u.department = {S(u['department'])}"
        )
    print("  Done.")

    # Step 2: MERGE Asset nodes
    print(f"[STEP 2] Merging {len(DEMO_ASSETS)} Asset nodes...")
    for a in DEMO_ASSETS:
        await client.run_query(
            f"MERGE (a:Asset {{asset_id: {S(a['asset_id'])}}}) "
            f"SET a.hostname = {S(a['hostname'])}, "
            f"a.asset_type = {S(a['asset_type'])}, a.os = {S(a['os'])}"
        )
    print("  Done.")

    # Step 3: MERGE demo Alert nodes
    print(f"[STEP 3] Merging {len(DEMO_ALERTS)} demo Alert nodes (origin='demo_backbone')...")
    for al in DEMO_ALERTS:
        await client.run_query(
            f"MERGE (alert:Alert {{alert_id: {S(al['alert_id'])}}}) "
            f"SET alert.category = {S(al['category'])}, "
            f"alert.severity = {S(al['severity'])}, "
            f"alert.alert_type = {S(al['alert_type'])}, "
            f"alert.status = 'pending', "
            f"alert.origin = 'demo_backbone', "
            f"alert.timestamp_epoch = {al['timestamp_epoch']}, "
            f"alert.source_location = {S(al['source_location'])}, "
            f"alert.user_id = {S(al['user_id'])}"
        )
    print("  Done.")

    # Step 4: MERGE INVOLVES edges (Alert → User)
    print(f"[STEP 4] Merging INVOLVES edges (Alert->User)...")
    for al in DEMO_ALERTS:
        await client.run_query(
            f"MATCH (alert:Alert {{alert_id: {S(al['alert_id'])}}}) "
            f"MATCH (u:User {{user_id: {S(al['user_id'])}}}) "
            f"MERGE (alert)-[:INVOLVES]->(u)"
        )
    print("  Done.")

    # Step 5: MERGE DETECTED_ON edges (Alert → Asset)
    print(f"[STEP 5] Merging DETECTED_ON edges (Alert->Asset)...")
    for al in DEMO_ALERTS:
        await client.run_query(
            f"MATCH (alert:Alert {{alert_id: {S(al['alert_id'])}}}) "
            f"MATCH (a:Asset {{asset_id: {S(al['asset_id'])}}}) "
            f"MERGE (alert)-[:DETECTED_ON]->(a)"
        )
    print("  Done.")

    # Step 6: MERGE Campaign nodes + MEMBER_OF edges (Alert → Campaign)
    print(f"[STEP 6] Merging {len(DEMO_CAMPAIGNS)} Campaign nodes + MEMBER_OF edges...")
    for c in DEMO_CAMPAIGNS:
        await client.run_query(
            f"MERGE (camp:Campaign {{campaign_id: {S(c['campaign_id'])}}}) "
            f"SET camp.id = {S(c['campaign_id'])}, "
            f"camp.severity = {S(c['severity'])}, "
            f"camp.confidence = {c['confidence']}, "
            f"camp.trigger_rule = {S(c['trigger_rule'])}, "
            f"camp.category_sequence = {S(json.dumps(c['category_sequence']))}, "
            f"camp.shared_entities = {S(json.dumps(c['shared_entities']))}, "
            f"camp.technique_sequence = {S(json.dumps(c['technique_sequence']))}, "
            f"camp.nl_summary = {S(c['nl_summary'])}, "
            f"camp.alert_count = {len(c['member_alert_ids'])}, "
            f"camp.member_alert_ids = {S(json.dumps(c['member_alert_ids']))}, "
            f"camp.correlation_window_hours = {c['correlation_window_hours']}, "
            f"camp.first_seen = {S(c['first_seen'])}, "
            f"camp.last_seen = {S(c['last_seen'])}"
        )
        for aid in c["member_alert_ids"]:
            await client.run_query(
                f"MATCH (alert:Alert {{alert_id: {S(aid)}}}) "
                f"MATCH (camp:Campaign {{campaign_id: {S(c['campaign_id'])}}}) "
                f"MERGE (alert)-[:MEMBER_OF]->(camp)"
            )
    print("  Done.")

    # Step 7: Verification
    print("\n[STEP 7] Verification:")
    checks = [
        ("Users (USR-*)",     "MATCH (u:User) WHERE u.user_id STARTS WITH 'USR-' RETURN count(u) AS cnt"),
        ("Assets (AST-*)",    "MATCH (a:Asset) WHERE a.asset_id STARTS WITH 'AST-' RETURN count(a) AS cnt"),
        ("Demo alerts",       "MATCH (a:Alert {origin: 'demo_backbone'}) RETURN count(a) AS cnt"),
        ("INVOLVES edges",    "MATCH (a:Alert {origin: 'demo_backbone'})-[:INVOLVES]->(:User) RETURN count(a) AS cnt"),
        ("DETECTED_ON edges", "MATCH (a:Alert {origin: 'demo_backbone'})-[:DETECTED_ON]->(:Asset) RETURN count(a) AS cnt"),
        ("Campaigns",         "MATCH (c:Campaign) WHERE c.campaign_id STARTS WITH 'CAMP-' RETURN count(c) AS cnt"),
        ("MEMBER_OF edges",   "MATCH (:Alert)-[:MEMBER_OF]->(:Campaign) RETURN count(*) AS cnt"),
    ]
    for lbl, q in checks:
        r = await client.run_query(q)
        print(f"  {lbl}: {r[0]['cnt']}")
    print("\n[OK] Backbone seeded. Restart uvicorn and test GET /api/alerts/queue.")


if __name__ == "__main__":
    if DRY_RUN:
        print_plan()
    elif LIVE:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run_live())
    elif BACKFILL:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run_backfill())
    elif BACKBONE:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(seed_graph_backbone())
