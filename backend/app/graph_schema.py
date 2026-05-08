"""
graph_schema.py — Single source of truth for the SOC graph structure.

Three public symbols:
    GRAPH_CONTRACT  — expected node labels, edge types, counts, invariants
    verify_graph()  — async check of current graph against the contract
    seed_graph()    — async create/recreate complete graph from v5 JSON

Usage:
    python -m app.graph_schema verify
    python -m app.graph_schema seed --clean
    python -m app.graph_schema seed --clean --file=path/to/v5.json

verify_graph() is used ONLY by:
    - This CLI
    - conftest.py (post-session health report)
    - seed_graph() (post-seed verification)

verify_graph() is NOT used by:
    - StateManager (pre-check is _verify_deletion_safety, not this)
    - API endpoints or runtime request paths

IMPORTANT: This file must be listed in ALLOWED_FILES in
test_no_destructive_decision_queries.py because the clean phase
runs DETACH DELETE on Decision/Alert nodes (scoped to origin='zero_day_synthetic'
and origin='zero_day_demo').
"""

import json as _json
import logging
import math
import os
import sys

log = logging.getLogger(__name__)

# Origin values for seeded data
SYNTHETIC_ORIGIN = "zero_day_synthetic"  # Training data (protected by StateManager)
DEMO_ORIGIN = "zero_day_demo"            # Demo alerts (ephemeral, reset by /api/alerts/reset)


# ---------------------------------------------------------------------------
# Serializer — safe inline values for AGE Cypher
# ---------------------------------------------------------------------------

def _S(val):
    """Serialize a Python value for inline use in AGE Cypher.

    Handles: None, bool, int, float, str, list, tuple, numpy arrays.
    Lists are stored as JSON strings (AGE has no array property type).
    Strings are single-quoted with escaping.
    Booleans are lowercase true/false.

    Raises ValueError on NaN/Inf (AGE cannot store these).
    """
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            raise ValueError("AGE cannot store NaN/Inf: " + repr(val))
        return str(val)
    if isinstance(val, (list, tuple)):
        return "'" + _json.dumps(val).replace("'", "\\'") + "'"
    if hasattr(val, "tolist"):  # numpy array
        return "'" + _json.dumps(val.tolist()).replace("'", "\\'") + "'"
    s = str(val).replace("\\", "\\\\").replace("'", "\\'")
    return "'" + s + "'"


# ---------------------------------------------------------------------------
# GRAPH_CONTRACT — what a healthy graph looks like
# ---------------------------------------------------------------------------

GRAPH_CONTRACT = {
    "nodes": {
        "Alert": {
            "min_count": 570,
            "required_fields": ["alert_id", "category", "severity",
                                "status", "origin", "timestamp_epoch",
                                "user_id", "asset_id", "alert_type",
                                "source_location", "attack_pattern_id"],
        },
        "Decision": {
            "min_count": 4860,
            "required_fields": ["decision_id", "category", "action",
                                "factor_vector", "confidence",
                                "outcome", "timestamp_epoch"],
            "optional_fields": [
                "correct", "origin",
                "source_id", "user_id", "reasoning", "alert_id",
                "nodes_consulted", "patterns_matched", "user_snapshot",
                "asset_snapshot", "campaign_id", "auto_approved",
                "verified_at_epoch", "override_comment",
                "centroid_delta_norm", "pattern_id", "playbook_id",
                "shadow_mode", "analyst_action", "agreement",
                "triage_entropy", "triage_confidence_gap", "entry_hash",
                "decision_chain_index", "outcome_chain_index", "outcome_entry_hash",
                "verified_by",
            ],
        },
        "User": {
            "min_count": 20,
            "required_fields": ["user_id", "name", "origin",
                                "department", "risk_level"],
        },
        "Asset": {
            "min_count": 15,
            "required_fields": ["asset_id", "hostname", "criticality",
                                "origin", "asset_type"],
            "optional_fields": ["type", "business_unit", "os", "owner_id"],
        },
        "Campaign": {
            "min_count": 3,
            "required_fields": ["campaign_id", "category_sequence",
                                "name", "origin", "severity",
                                "last_seen", "first_seen", "alert_count"],
            "optional_fields": [
                "shared_entities", "technique_sequence", "confidence",
                "trigger_rule", "correlation_window_hours", "nl_summary",
                "updated_at_epoch",
            ],
        },
        "ThreatIndicator": {
            "min_count": 5,
            "required_fields": ["indicator", "indicator_type", "severity",
                                "origin", "source"],
            "optional_fields": [
                "id",
                "name",
                "created_at_epoch",
                "last_seen_epoch",
                "risk_factors",
            ],
        },
        "AttackPattern": {
            "min_count": 6,
            "required_fields": ["pattern_id", "name", "mitre_id",
                                "origin", "tactic", "category"],
        },
    },
    "edges": {
        "DECIDED_ON":         {"min_count": 4860, "from": "Decision",  "to": "Alert"},
        "INVOLVES":           {"min_count": 540,  "from": "Alert",     "to": "User"},
        "DETECTED_ON":        {"min_count": 540,  "from": "Alert",     "to": "Asset"},
        "MEMBER_OF":          {"min_count": 12,   "from": "Alert",     "to": "Campaign"},
        "CLASSIFIED_AS":      {"min_count": 540,  "from": "Alert",     "to": "AttackPattern"},
        "HAS_INDICATOR":      {"min_count": 10,   "from": "Alert",     "to": "ThreatIndicator"},
        "TRIGGERED_EVOLUTION":{"min_count": 0,    "from": "Decision",  "to": "EvolutionEvent"},
    },
    "invariants": [
        {
            "name": "no_orphan_decisions",
            "query": "MATCH (d:Decision) WHERE NOT EXISTS((d)-[:DECIDED_ON]->()) "
                     "RETURN count(d) AS n",
            "expected": 0,
        },
        {
            "name": "no_missing_outcomes",
            "query": "MATCH (d:Decision {origin: '" + SYNTHETIC_ORIGIN + "'}) "
                     "WHERE d.correct IS NULL RETURN count(d) AS n",
            "expected": 0,
        },
        {
            "name": "demo_alerts_exist",
            "query": "MATCH (a:Alert {status: 'pending'}) RETURN count(a) AS n",
            "expected_min": 25,
        },
        {
            "name": "no_null_categories",
            "query": "MATCH (d:Decision) WHERE d.category IS NULL "
                     "RETURN count(d) AS n",
            "expected": 0,
        },
        {
            "name": "alerts_have_users",
            "query": "MATCH (a:Alert) "
                     "WHERE (a.origin = '" + SYNTHETIC_ORIGIN + "' "
                     "OR a.origin = '" + DEMO_ORIGIN + "') "
                     "AND NOT EXISTS((a)-[:INVOLVES]->()) "
                     "RETURN count(a) AS n",
            "expected": 0,
        },
        {
            "name": "alerts_have_assets",
            "query": "MATCH (a:Alert) "
                     "WHERE (a.origin = '" + SYNTHETIC_ORIGIN + "' "
                     "OR a.origin = '" + DEMO_ORIGIN + "') "
                     "AND NOT EXISTS((a)-[:DETECTED_ON]->()) "
                     "RETURN count(a) AS n",
            "expected": 0,
        },
    ],
}

# Clean phase: backbone labels delete ALL nodes (we fully own these).
# Data labels delete both origins: zero_day_synthetic + zero_day_demo.
# Session decisions (origin=NULL) survive a clean.
_BACKBONE_LABELS = ["User", "Asset", "Campaign",
                    "ThreatIndicator", "AttackPattern"]
_DATA_LABELS = ["Decision", "Alert"]
_DATA_ORIGINS = [SYNTHETIC_ORIGIN, DEMO_ORIGIN]


# ---------------------------------------------------------------------------
# verify_graph()
# ---------------------------------------------------------------------------

async def verify_graph(client=None):
    """Check current graph against GRAPH_CONTRACT.

    Returns {"healthy": bool, "issues": [...], "warnings": [...], "counts": {...}}
    counts is ALWAYS populated, even when healthy.
    """
    if client is None:
        os.environ.setdefault("GRAPH_BACKEND", "age")
        from ci_platform.graph import get_graph_client
        client = get_graph_client()

    report = {"healthy": True, "issues": [], "warnings": [], "counts": {}}

    # -- Node counts + sample field check --
    for label, spec in GRAPH_CONTRACT["nodes"].items():
        try:
            r = await client.run_query(
                "MATCH (n:" + label + ") RETURN count(n) AS cnt"
            )
            count = int(r[0]["cnt"]) if r else 0
        except Exception as exc:
            count = -1
            report["healthy"] = False
            report["issues"].append(label + ": count query failed - " + str(exc))

        report["counts"][label] = count

        if count >= 0 and count < spec["min_count"]:
            report["healthy"] = False
            report["issues"].append(
                label + ": " + str(count) + " (need >= " +
                str(spec["min_count"]) + ")"
            )

        # Sample a seeded node for field presence. Filter by SYNTHETIC_ORIGIN
        # (training data) since it's always present and has the same fields as
        # DEMO_ORIGIN alerts. Unfiltered sampling risks hitting orphan nodes.
        if count > 0:
            try:
                sample = await client.run_query(
                    "MATCH (n:" + label + " {origin: " +
                    _S(SYNTHETIC_ORIGIN) + "}) RETURN n LIMIT 1"
                )
                if sample:
                    node = sample[0].get("n", sample[0])
                    if isinstance(node, dict):
                        for field in spec["required_fields"]:
                            if field not in node or node[field] is None:
                                report["healthy"] = False
                                report["issues"].append(
                                    label + ": missing '" + field +
                                    "' on sample"
                                )
                        known = (set(spec["required_fields"]) |
                                 set(spec.get("optional_fields", [])))
                        for field in node:
                            if field.startswith("_age_"):
                                continue  # AGE internal field — always skip
                            if field not in known:
                                report["warnings"].append(
                                    label + ": unexpected field '" +
                                    field + "' on sample node"
                                )
                else:
                    # Nodes exist but none have our origin — hard failure
                    report["healthy"] = False
                    report["issues"].append(
                        label + ": " + str(count) +
                        " nodes but none with origin='" +
                        SYNTHETIC_ORIGIN + "'"
                    )
            except Exception as exc:
                report["healthy"] = False
                report["issues"].append(
                    label + ": sample check failed - " + str(exc)
                )

    # -- Edge counts --
    for rel_type, spec in GRAPH_CONTRACT["edges"].items():
        try:
            r = await client.run_query(
                "MATCH ()-[r:" + rel_type + "]->() RETURN count(r) AS cnt"
            )
            count = int(r[0]["cnt"]) if r else 0
        except Exception as exc:
            count = -1
            report["healthy"] = False
            report["issues"].append(
                rel_type + ": edge query failed - " + str(exc)
            )

        report["counts"][rel_type] = count

        if count >= 0 and count < spec["min_count"]:
            report["healthy"] = False
            report["issues"].append(
                rel_type + ": " + str(count) + " edges (need >= " +
                str(spec["min_count"]) + ")"
            )

        # Verify from/to endpoint labels when declared and edges exist
        if count > 0 and "from" in spec and "to" in spec:
            from_label = spec["from"]
            to_label = spec["to"]
            try:
                lr = await client.run_query(
                    "MATCH (src:" + from_label + ")-[r:" + rel_type +
                    "]->(dst:" + to_label + ") RETURN count(r) AS cnt LIMIT 1"
                )
                matched = int(lr[0]["cnt"]) if lr else 0
                if matched == 0:
                    report["healthy"] = False
                    report["issues"].append(
                        rel_type + ": expected " + from_label +
                        "->" + to_label + ", found wrong labels"
                    )
            except Exception as exc:
                report["warnings"].append(
                    rel_type + ": label check failed - " + str(exc)
                )

    # -- Invariants --
    for inv in GRAPH_CONTRACT["invariants"]:
        try:
            r = await client.run_query(inv["query"])
            value = int(r[0]["n"]) if r else -1
        except Exception as exc:
            report["healthy"] = False
            report["issues"].append(
                "Invariant '" + inv["name"] + "' failed: " + str(exc)
            )
            continue

        if "expected" in inv and value != inv["expected"]:
            report["healthy"] = False
            report["issues"].append(
                "Invariant '" + inv["name"] + "': " + str(value) +
                " (expected " + str(inv["expected"]) + ")"
            )
        elif "expected_min" in inv and value < inv["expected_min"]:
            report["healthy"] = False
            report["issues"].append(
                "Invariant '" + inv["name"] + "': " + str(value) +
                " (need >= " + str(inv["expected_min"]) + ")"
            )

    return report


# ---------------------------------------------------------------------------
# JSON validation
# ---------------------------------------------------------------------------

def _validate_json(data):
    """Validate v5 JSON structure before seeding. Raises ValueError on errors."""
    errors = []

    required_keys = ["alerts", "demo_alerts", "decisions", "users", "assets",
                     "attack_patterns", "threat_indicators", "campaigns"]
    for key in required_keys:
        if key not in data:
            errors.append("Missing top-level key: " + key)

    if errors:
        raise ValueError("JSON validation failed:\n  " + "\n  ".join(errors))

    # Check required fields on first 3 items in each section
    for section, fields in [
        ("alerts", ["alert_id", "category", "severity", "timestamp_epoch"]),
        ("demo_alerts", ["alert_id", "category", "severity", "timestamp_epoch"]),
        ("decisions", ["decision_id", "alert_id", "category", "action",
                       "factor_vector", "confidence", "correct", "outcome",
                       "timestamp_epoch"]),
        ("users", ["user_id", "name"]),
        ("assets", ["asset_id", "hostname", "criticality"]),
        ("attack_patterns", ["pattern_id", "name", "mitre_id"]),
        ("threat_indicators", ["indicator", "indicator_type", "severity"]),
        ("campaigns", ["campaign_id"]),
    ]:
        items = data.get(section, [])
        for i, item in enumerate(items[:3]):
            for field in fields:
                if field not in item:
                    errors.append(
                        section + "[" + str(i) + "]: missing '" + field + "'"
                    )

    # Check referential integrity
    alert_ids = {a["alert_id"] for a in data.get("alerts", [])}
    orphan_decisions = [d["decision_id"] for d in data.get("decisions", [])
                        if d.get("alert_id") not in alert_ids]
    if orphan_decisions:
        errors.append(str(len(orphan_decisions)) +
                      " decisions reference missing alerts (e.g. " +
                      str(orphan_decisions[:3]) + ")")

    for c in data.get("campaigns", []):
        for aid in c.get("alert_ids", []):
            if aid not in alert_ids:
                errors.append("Campaign " + c.get("campaign_id", "?") +
                              " references missing alert: " + aid)

    if errors:
        raise ValueError("JSON validation failed:\n  " + "\n  ".join(errors))


# ---------------------------------------------------------------------------
# seed_graph()
# ---------------------------------------------------------------------------

async def seed_graph(json_path, clean=False, client=None):
    """Create complete graph from zero_day_decisions_v5.json.

    clean=True:  delete backbone nodes (ALL) + seeded Decision/Alert nodes
                 (both zero_day_synthetic and zero_day_demo origins),
                 then CREATE everything fresh. Session decisions survive.
    clean=False: CREATE without deleting. Will duplicate if run twice.
                 Use --clean unless you know the graph is empty.

    Returns verify_graph() result.
    """
    if client is None:
        os.environ.setdefault("GRAPH_BACKEND", "age")
        from ci_platform.graph import get_graph_client
        client = get_graph_client()

    print("[SEED] Loading " + json_path + "...")
    with open(json_path, encoding="utf-8") as fh:
        data = _json.load(fh)

    # Validate JSON before touching the graph
    print("[SEED] Validating JSON structure...")
    _validate_json(data)
    print("[SEED] JSON valid.")

    users       = data.get("users", [])
    assets      = data.get("assets", [])
    patterns    = data.get("attack_patterns", [])
    indicators  = data.get("threat_indicators", [])
    campaigns   = data.get("campaigns", [])
    alerts      = data.get("alerts", [])
    demo_alerts = data.get("demo_alerts", [])
    decisions   = data.get("decisions", [])

    print("  " + str(len(users)) + " users, " +
          str(len(assets)) + " assets, " +
          str(len(patterns)) + " attack_patterns, " +
          str(len(indicators)) + " threat_indicators")
    print("  " + str(len(campaigns)) + " campaigns, " +
          str(len(alerts)) + " training alerts, " +
          str(len(demo_alerts)) + " demo alerts, " +
          str(len(decisions)) + " decisions")

    # Ensure the AGE graph exists
    await client.ensure_graph()

    # ── Phase 1: CLEAN ────────────────────────────────────────────────
    # Backbone labels (User, Asset, Campaign, etc.): delete ALL nodes.
    # We fully control these and recreate from JSON. Old nodes without
    # origin fields (from seed_neo4j.py or campaign correlation engine)
    # must not survive.
    # Decision + Alert: delete both zero_day_synthetic and zero_day_demo.
    # Session decisions (origin=NULL) survive a clean.
    if clean:
        print("[1/9] Cleaning graph for re-seed...")
        for label in _BACKBONE_LABELS:
            before = await client.run_query(
                "MATCH (n:" + label + ") RETURN count(n) AS cnt"
            )
            await client.run_query(
                "MATCH (n:" + label + ") "
                "WHERE n.origin IS NULL "
                "OR n.origin = " + _S(SYNTHETIC_ORIGIN) + " "
                "OR n.origin = " + _S(DEMO_ORIGIN) + " "
                "DETACH DELETE n"
            )
            deleted = int(before[0]["cnt"]) if before else 0
            print("  " + label + ": deleted " + str(deleted))
        for label in _DATA_LABELS:
            for origin in _DATA_ORIGINS:
                before = await client.run_query(
                    "MATCH (n:" + label + " {origin: " +
                    _S(origin) + "}) RETURN count(n) AS cnt"
                )
                await client.run_query(
                    "MATCH (n:" + label + " {origin: " +
                    _S(origin) + "}) DETACH DELETE n"
                )
                deleted = int(before[0]["cnt"]) if before else 0
                if deleted > 0:
                    print("  " + label + " (" + origin + "): deleted " +
                          str(deleted))

        # Verify backbone is empty
        for label in _BACKBONE_LABELS:
            remaining = await client.run_query(
                "MATCH (n:" + label + ") RETURN count(n) AS cnt"
            )
            cnt = int(remaining[0]["cnt"]) if remaining else 0
            if cnt > 0:
                print("  [WARN] " + label + ": " + str(cnt) +
                      " nodes survived clean (no origin field?)")
        print("  Done.")
    else:
        print("[1/9] Skipped (no --clean).")

    # ── Phase 2: Users ────────────────────────────────────────────────
    print("[2/9] Creating " + str(len(users)) + " Users...")
    for u in users:
        await client.run_query(
            "CREATE (n:User {"
            "user_id: " + _S(u["user_id"]) + ", "
            "name: " + _S(u["name"]) + ", "
            "department: " + _S(u.get("department", "")) + ", "
            "risk_level: " + _S(u.get("risk_level", "standard")) + ", "
            "origin: " + _S(SYNTHETIC_ORIGIN) +
            "})"
        )

    # ── Phase 3: Assets, AttackPatterns, ThreatIndicators ─────────────
    print("[3/9] Creating " + str(len(assets)) + " Assets, " +
          str(len(patterns)) + " AttackPatterns, " +
          str(len(indicators)) + " ThreatIndicators...")

    for a in assets:
        await client.run_query(
            "CREATE (n:Asset {"
            "asset_id: " + _S(a["asset_id"]) + ", "
            "hostname: " + _S(a["hostname"]) + ", "
            "criticality: " + _S(a["criticality"]) + ", "
            "asset_type: " + _S(a.get("asset_type", "")) + ", "
            "origin: " + _S(SYNTHETIC_ORIGIN) +
            "})"
        )

    for p in patterns:
        await client.run_query(
            "CREATE (n:AttackPattern {"
            "pattern_id: " + _S(p["pattern_id"]) + ", "
            "name: " + _S(p["name"]) + ", "
            "mitre_id: " + _S(p["mitre_id"]) + ", "
            "tactic: " + _S(p.get("tactic", "")) + ", "
            "category: " + _S(p.get("category", "")) + ", "
            "origin: " + _S(SYNTHETIC_ORIGIN) +
            "})"
        )

    for t in indicators:
        await client.run_query(
            "CREATE (n:ThreatIndicator {"
            "indicator: " + _S(t["indicator"]) + ", "
            "indicator_type: " + _S(t["indicator_type"]) + ", "
            "severity: " + _S(t["severity"]) + ", "
            "source: " + _S(t["source"]) + ", "
            "origin: " + _S(SYNTHETIC_ORIGIN) +
            "})"
        )

    # ── Phase 4: Campaigns ────────────────────────────────────────────
    print("[4/9] Creating " + str(len(campaigns)) + " Campaigns...")
    for c in campaigns:
        await client.run_query(
            "CREATE (n:Campaign {"
            "campaign_id: " + _S(c["campaign_id"]) + ", "
            "name: " + _S(c.get("name", "")) + ", "
            "category_sequence: " + _S(c.get("category_sequence", [])) + ", "
            "first_seen: " + _S(c.get("first_seen", 0)) + ", "
            "last_seen: " + _S(c.get("last_seen", 0)) + ", "
            "severity: " + _S(c.get("severity", "medium")) + ", "
            "alert_count: " + _S(len(c.get("alert_ids", []))) + ", "
            "origin: " + _S(SYNTHETIC_ORIGIN) +
            "})"
        )

    # ── Phase 5: Training Alerts (540) ────────────────────────────────
    print("[5/9] Creating " + str(len(alerts)) + " training Alerts...")
    for i, a in enumerate(alerts):
        await client.run_query(
            "CREATE (n:Alert {"
            "alert_id: " + _S(a["alert_id"]) + ", "
            "category: " + _S(a["category"]) + ", "
            "severity: " + _S(a["severity"]) + ", "
            "alert_type: " + _S(a.get("alert_type", a["category"])) + ", "
            "status: " + _S(a.get("status", "decided")) + ", "
            "origin: " + _S(a.get("origin", SYNTHETIC_ORIGIN)) + ", "
            "timestamp_epoch: " + _S(a["timestamp_epoch"]) + ", "
            "source_location: " + _S(a.get("source_location", "synthetic")) + ", "
            "user_id: " + _S(a.get("user_id", "")) + ", "
            "asset_id: " + _S(a.get("asset_id", "")) + ", "
            "attack_pattern_id: " + _S(a.get("attack_pattern_id", "")) +
            "})"
        )
        if (i + 1) % 100 == 0:
            print("  " + str(i + 1) + "/" + str(len(alerts)) + " alerts...")

    # ── Phase 6: Demo Alerts (30) ─────────────────────────────────────
    print("[6/9] Creating " + str(len(demo_alerts)) + " demo Alerts...")
    for a in demo_alerts:
        await client.run_query(
            "CREATE (n:Alert {"
            "alert_id: " + _S(a["alert_id"]) + ", "
            "category: " + _S(a["category"]) + ", "
            "severity: " + _S(a["severity"]) + ", "
            "alert_type: " + _S(a.get("alert_type", a["category"])) + ", "
            "status: 'pending', "
            "origin: " + _S(a.get("origin", DEMO_ORIGIN)) + ", "
            "timestamp_epoch: " + _S(a["timestamp_epoch"]) + ", "
            "source_location: " + _S(a.get("source_location", "corp-network")) + ", "
            "user_id: " + _S(a.get("user_id", "")) + ", "
            "asset_id: " + _S(a.get("asset_id", "")) + ", "
            "attack_pattern_id: " + _S(a.get("attack_pattern_id", "")) +
            "})"
        )

    # ── Phase 7: All edges ────────────────────────────────────────────
    all_alerts = alerts + demo_alerts
    print("[7/9] Creating edges for " + str(len(all_alerts)) + " alerts...")

    involves_ok, involves_fail = 0, 0
    detected_ok, detected_fail = 0, 0
    classified_ok, classified_fail = 0, 0
    indicator_ok, indicator_fail = 0, 0

    for a in all_alerts:
        aid = a["alert_id"]
        uid = a.get("user_id") or ""
        asid = a.get("asset_id") or ""
        apid = a.get("attack_pattern_id") or ""

        # INVOLVES (Alert -> User)
        if uid:
            try:
                await client.run_query(
                    "MATCH (alert:Alert {alert_id: " + _S(aid) + "}), "
                    "(u:User {user_id: " + _S(uid) + "}) "
                    "CREATE (alert)-[:INVOLVES]->(u)"
                )
                involves_ok += 1
            except Exception as exc:
                involves_fail += 1
                if involves_fail <= 3:
                    log.warning("[7/9] INVOLVES failed for %s: %s", aid, exc)

        # DETECTED_ON (Alert -> Asset)
        if asid:
            try:
                await client.run_query(
                    "MATCH (alert:Alert {alert_id: " + _S(aid) + "}), "
                    "(ast:Asset {asset_id: " + _S(asid) + "}) "
                    "CREATE (alert)-[:DETECTED_ON]->(ast)"
                )
                detected_ok += 1
            except Exception as exc:
                detected_fail += 1
                if detected_fail <= 3:
                    log.warning("[7/9] DETECTED_ON failed for %s: %s", aid, exc)

        # CLASSIFIED_AS (Alert -> AttackPattern)
        if apid:
            try:
                await client.run_query(
                    "MATCH (alert:Alert {alert_id: " + _S(aid) + "}), "
                    "(ap:AttackPattern {pattern_id: " + _S(apid) + "}) "
                    "CREATE (alert)-[:CLASSIFIED_AS]->(ap)"
                )
                classified_ok += 1
            except Exception as exc:
                classified_fail += 1
                if classified_fail <= 3:
                    log.warning("[7/9] CLASSIFIED_AS failed for %s: %s",
                                aid, exc)

        # HAS_INDICATOR (Alert -> ThreatIndicator)
        for ind_val in a.get("indicator_ids", []):
            try:
                await client.run_query(
                    "MATCH (alert:Alert {alert_id: " + _S(aid) + "}), "
                    "(ti:ThreatIndicator {indicator: " + _S(ind_val) + "}) "
                    "CREATE (alert)-[:HAS_INDICATOR]->(ti)"
                )
                indicator_ok += 1
            except Exception as exc:
                indicator_fail += 1
                if indicator_fail <= 3:
                    log.warning("[7/9] HAS_INDICATOR failed for %s: %s",
                                aid, exc)

    # MEMBER_OF (Alert -> Campaign)
    member_ok, member_fail = 0, 0
    for c in campaigns:
        cid = c["campaign_id"]
        for aid in c.get("alert_ids", []):
            try:
                await client.run_query(
                    "MATCH (alert:Alert {alert_id: " + _S(aid) + "}), "
                    "(camp:Campaign {campaign_id: " + _S(cid) + "}) "
                    "CREATE (alert)-[:MEMBER_OF]->(camp)"
                )
                member_ok += 1
            except Exception as exc:
                member_fail += 1
                if member_fail <= 3:
                    log.warning("[7/9] MEMBER_OF failed %s->%s: %s",
                                aid, cid, exc)

    print("  INVOLVES: " + str(involves_ok) + " ok, " +
          str(involves_fail) + " fail")
    print("  DETECTED_ON: " + str(detected_ok) + " ok, " +
          str(detected_fail) + " fail")
    print("  CLASSIFIED_AS: " + str(classified_ok) + " ok, " +
          str(classified_fail) + " fail")
    print("  HAS_INDICATOR: " + str(indicator_ok) + " ok, " +
          str(indicator_fail) + " fail")
    print("  MEMBER_OF: " + str(member_ok) + " ok, " +
          str(member_fail) + " fail")

    total_fail = (involves_fail + detected_fail + classified_fail +
                  indicator_fail + member_fail)
    if total_fail > 0:
        print("  [WARN] " + str(total_fail) + " total edge failures")

    # ── Phase 8: Decisions + DECIDED_ON (atomic) ──────────────────────
    print("[8/9] Creating " + str(len(decisions)) +
          " Decisions + DECIDED_ON edges...")
    ok, fail = 0, 0
    for d in decisions:
        try:
            await client.run_query(
                "MATCH (a:Alert {alert_id: " + _S(d["alert_id"]) + "}) "
                "CREATE (dd:Decision {"
                "decision_id: " + _S(d["decision_id"]) + ", "
                "category: " + _S(d["category"]) + ", "
                "action: " + _S(d["action"]) + ", "
                "factor_vector: " + _S(d["factor_vector"]) + ", "
                "confidence: " + _S(d["confidence"]) + ", "
                "correct: " + _S(d["correct"]) + ", "
                "outcome: " + _S(d["outcome"]) + ", "
                "timestamp_epoch: " + _S(d["timestamp_epoch"]) + ", "
                "origin: " + _S(SYNTHETIC_ORIGIN) + ", "
                "source_id: " + _S(d.get("source_id", "synthetic")) + ", "
                "user_id: " + _S(d.get("user_id", "")) +
                "})-[:DECIDED_ON]->(a)"
            )
            ok += 1
        except Exception as exc:
            fail += 1
            if fail <= 5:
                log.warning("[8/9] Decision %s failed: %s",
                            d.get("decision_id", "?"), exc)
        if (ok + fail) % 1000 == 0:
            print("  " + str(ok) + " ok, " + str(fail) + " fail...")
    print("  Done: " + str(ok) + " ok, " + str(fail) + " fail.")

    if fail > 0:
        print("  [ERROR] " + str(fail) + " decisions failed to create")

    # ── Phase 9: Verify ───────────────────────────────────────────────
    print("[9/9] Verifying graph contract...")
    report = await verify_graph(client)
    if report["healthy"]:
        print("[OK] Graph healthy.")
        for label, count in sorted(report["counts"].items()):
            print("  " + label + ": " + str(count))
    else:
        print("[WARN] " + str(len(report["issues"])) + " issues:")
        for issue in report["issues"]:
            print("  - " + issue)
    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    os.environ.setdefault("GRAPH_BACKEND", "age")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    if len(sys.argv) < 2 or sys.argv[1] not in ("verify", "seed"):
        print("Usage:")
        print("  python -m app.graph_schema verify")
        print("  python -m app.graph_schema seed [--clean] [--file=path]")
        sys.exit(1)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    if sys.argv[1] == "verify":
        report = asyncio.run(verify_graph())
        if report["healthy"]:
            print("[OK] Graph healthy.")
            for label, count in sorted(report["counts"].items()):
                print("  " + label + ": " + str(count))
        else:
            print("[FAIL] " + str(len(report["issues"])) + " issues:")
            for i in report["issues"]:
                print("  " + i)
            sys.exit(1)

    elif sys.argv[1] == "seed":
        do_clean = "--clean" in sys.argv
        json_path = os.path.join("support", "setup",
                                 "zero_day_decisions_v5.json")
        file_args = [a for a in sys.argv if a.startswith("--file=")]
        if file_args:
            json_path = file_args[0].split("=", 1)[1]
        if not os.path.exists(json_path):
            print("[ERROR] Not found: " + json_path)
            sys.exit(1)
        report = asyncio.run(seed_graph(json_path, clean=do_clean))
        if not report["healthy"]:
            sys.exit(1)
