"""
SEED-2 — Realistic seed data for SOC Copilot.

200 users with power-law alert distribution, planted suspicious patterns,
and department diversity for more varied factor computation.

All generation is fully deterministic (no random — modulo arithmetic only).
Every run produces identical output.

Usage:
    python seed_neo4j.py --realistic
"""

from datetime import date, timedelta
from typing import Any, Dict, List

from app.domains.soc.config import SOC_CATEGORIES


# ─── Module-level constants (tested directly) ─────────────────────────────────

DEPARTMENT_DISTRIBUTION: Dict[str, int] = {
    "Engineering": 80,
    "Finance": 30,
    "Executive": 10,
    "Sales": 40,
    "IT": 20,
    "Legal": 10,
    "HR": 10,
}
assert sum(DEPARTMENT_DISTRIBUTION.values()) == 200, \
    "DEPARTMENT_DISTRIBUTION must total exactly 200"

ALERT_CATEGORY_DISTRIBUTION: Dict[str, int] = {
    "credential_access": 17,
    "threat_intel_match": 17,
    "lateral_movement": 17,
    "data_exfiltration": 17,
    "insider_threat": 16,
    "cloud_infrastructure": 16,
}
assert sum(ALERT_CATEGORY_DISTRIBUTION.values()) == 100, \
    "ALERT_CATEGORY_DISTRIBUTION must total exactly 100"

# Short codes used in alert IDs — "REAL-CA-001", etc.
CATEGORY_CODES: Dict[str, str] = {
    "credential_access": "CA",
    "threat_intel_match": "TI",
    "lateral_movement": "LM",
    "data_exfiltration": "DE",
    "insider_threat": "IT",
    "cloud_infrastructure": "CI",
}

# ─── Internal lookup tables ───────────────────────────────────────────────────

_SEVERITIES = ["critical", "high", "medium", "low"]

_TRAVEL_DESTINATIONS = [
    "Singapore", "London", "Tokyo", "Dubai",
    "New York", "Berlin", "Sydney",
]

_TI_SOURCES = ["CISA", "GreyNoise", "internal"]

_DC_SENSITIVITIES = ["PII", "RESTRICTED", "CONFIDENTIAL", "PUBLIC"]

_BASE_DATE = date(2026, 2, 7)
_DATES: List[str] = [
    (_BASE_DATE + timedelta(days=i)).isoformat() for i in range(30)
]

# Flat ordered list: index → department (len == 200)
_DEPT_ORDER: List[str] = []
for _dept, _count in DEPARTMENT_DISTRIBUTION.items():
    _DEPT_ORDER.extend([_dept] * _count)
assert len(_DEPT_ORDER) == 200


# ─── Public helper functions (tested directly) ────────────────────────────────

def build_user_properties(user_id: str) -> Dict[str, Any]:
    """
    Return a dict of deterministic properties for a single User node.

    Planted suspicious users (REAL-USR-0001 through REAL-USR-0005) always
    receive access_level="privileged" and travel_frequency="frequent".

    ~15% of users omit device_type (those where n % 7 == 0).

    Args:
        user_id: "REAL-USR-NNNN" where N is a 4-digit index.
    """
    n = int(user_id.split("-")[-1])

    # ── Planted suspicious patterns for first 5 users ─────────────────────
    if 1 <= n <= 5:
        access_level = "privileged"
        travel_frequency = "frequent"
    else:
        # Access level: 70% standard / 20% elevated / 10% privileged
        al_rem = (n - 6) % 10
        if al_rem < 7:
            access_level = "standard"
        elif al_rem < 9:
            access_level = "elevated"
        else:
            access_level = "privileged"

        # Travel frequency: 20% frequent / 50% occasional / 30% rare
        tf_rem = (n - 6) % 10
        if tf_rem < 2:
            travel_frequency = "frequent"
        elif tf_rem < 7:
            travel_frequency = "occasional"
        else:
            travel_frequency = "rare"

    # Device type: 60% corporate_laptop / 25% mobile / 15% desktop
    dt_rem = n % 20
    device_type = (
        "corporate_laptop" if dt_rem < 12
        else "mobile" if dt_rem < 17
        else "desktop"
    )

    # Risk score: access_level base + travel bonus + small index variance
    risk_base = {"standard": 0.20, "elevated": 0.50, "privileged": 0.70}[access_level]
    travel_bonus = {"frequent": 0.15, "occasional": 0.05, "rare": 0.00}[travel_frequency]
    risk_score = min(0.90, round(risk_base + travel_bonus + (n % 5) * 0.02, 2))

    # Department from the pre-built ordered list (1-indexed users → 0-indexed list)
    department = _DEPT_ORDER[(n - 1) % 200]

    props: Dict[str, Any] = {
        "user_id": user_id,
        "name": f"User {n}",
        "department": department,
        "travel_frequency": travel_frequency,
        "access_level": access_level,
        "risk_score": risk_score,
    }

    # Missing device_type for ~15% of users (n % 7 == 0 → 28/200 = 14%)
    if n % 7 != 0:
        props["device_type"] = device_type

    return props


def build_alert_id(category: str, n: int) -> str:
    """
    Return "REAL-{CODE}-{n:03d}" for a given SOC category and alert number.

    Example:
        build_alert_id("credential_access", 1) → "REAL-CA-001"
    """
    code = CATEGORY_CODES.get(category, "XX")
    return f"REAL-{code}-{n:03d}"


# ─── Internal record builders ─────────────────────────────────────────────────

def _build_alert_records() -> List[Dict[str, Any]]:
    """
    Build 100 alert records (pure Python, no Neo4j).

    Power-law distribution:
      global_n  0–59  (60 alerts): top 20 users — 3 alerts each
      global_n 60–99  (40 alerts): next 40 users — 1 alert each

    Category assignment: SOC_CATEGORIES[global_n % 6] → even spread.

    Returns list of dicts with keys:
        props     — properties to SET on the Alert node
        alert_id  — REAL-{CODE}-{n:03d}
        user_id   — REAL-USR-{n:04d}
        category  — SOC category string
        global_n  — 0-based alert index
    """
    records = []
    cat_counters: Dict[str, int] = {cat: 0 for cat in SOC_CATEGORIES}

    for global_n in range(100):
        category = SOC_CATEGORIES[global_n % 6]
        cat_counters[category] += 1
        alert_id = build_alert_id(category, cat_counters[category])

        # User assignment: top 20 get 3 alerts each (indices 0–19),
        # next 40 get 1 alert each (indices 20–59).
        if global_n < 60:
            user_index = global_n // 3        # 0..19
        else:
            user_index = 20 + (global_n - 60) # 20..59

        user_id = f"REAL-USR-{(user_index + 1):04d}"
        timestamp = f"{_DATES[global_n % 30]}T{(global_n % 24):02d}:00:00Z"
        severity = _SEVERITIES[global_n % 4]

        props: Dict[str, Any] = {
            "alert_id": alert_id,
            "category": category,
            "severity": severity,
            "status": "pending",
            "created_at": timestamp,
            "user_id": user_id,
            "source": "SEED-2",
        }
        records.append({
            "props": props,
            "alert_id": alert_id,
            "user_id": user_id,
            "category": category,
            "global_n": global_n,
        })

    return records


def _build_ti_nodes() -> List[Dict[str, Any]]:
    """Build 20 ThreatIntel node property dicts. Sources cycle: CISA / GreyNoise / internal."""
    nodes = []
    for n in range(1, 21):
        source = _TI_SOURCES[n % 3]
        nodes.append({
            "ti_id": f"REAL-TI-{n:03d}",
            "source": source,
            "indicator_type": "domain" if n % 2 == 0 else "ip",
            "confidence": round(0.5 + (n % 5) * 0.1, 1),
        })
    return nodes


def _build_dataclass_nodes() -> List[Dict[str, Any]]:
    """Build 10 DataClass node property dicts."""
    nodes = []
    for n in range(1, 11):
        sensitivity = _DC_SENSITIVITIES[(n - 1) % 4]
        nodes.append({
            "dc_id": f"REAL-DC-{n:03d}",
            "sensitivity": sensitivity,
            "name": f"{sensitivity} Data {n}",
        })
    return nodes


# ─── Main async entry point ───────────────────────────────────────────────────

async def seed_realistic(neo4j_client: Any) -> None:
    """
    Seed Neo4j with SEED-2 realistic data.

    MUST be called after seed_data() — existing demo data must already exist.
    Does NOT delete any existing nodes; only adds REAL-prefixed nodes.
    """

    # ── 1. Users ─────────────────────────────────────────────────────────────
    print("[SEED-2] Creating 200 users (REAL-USR-0001..0200)...")
    users = [build_user_properties(f"REAL-USR-{n:04d}") for n in range(1, 201)]

    await neo4j_client.run_query(
        "UNWIND $users AS u "
        "MERGE (node:User {user_id: u.user_id}) "
        "SET node += u",
        {"users": users},
    )
    print(f"  [OK] {len(users)} user nodes created/merged")

    # ── 2. Alert nodes ────────────────────────────────────────────────────────
    print("[SEED-2] Creating 100 alerts (power-law distribution)...")
    alert_records = _build_alert_records()

    await neo4j_client.run_query(
        "UNWIND $alerts AS a "
        "CREATE (node:Alert) "
        "SET node += a",
        {"alerts": [r["props"] for r in alert_records]},
    )

    # ── 3. INVOLVES relationships (alert → user) ──────────────────────────────
    involves_pairs = [
        {"alert_id": r["alert_id"], "user_id": r["user_id"]}
        for r in alert_records
    ]
    await neo4j_client.run_query(
        "UNWIND $pairs AS pair "
        "MATCH (a:Alert {alert_id: pair.alert_id}) "
        "MATCH (u:User {user_id: pair.user_id}) "
        "CREATE (a)-[:INVOLVES]->(u)",
        {"pairs": involves_pairs},
    )
    print(f"  [OK] {len(alert_records)} alerts created with [:INVOLVES] edges")

    # ── 4. ThreatIntel nodes ──────────────────────────────────────────────────
    print("[SEED-2] Creating 20 ThreatIntel nodes (CISA / GreyNoise / internal)...")
    ti_nodes = _build_ti_nodes()
    await neo4j_client.run_query(
        "UNWIND $nodes AS t "
        "CREATE (node:ThreatIntel) "
        "SET node += t",
        {"nodes": ti_nodes},
    )

    # Link threat_intel_match alerts AND planted-user alerts to ThreatIntel
    planted_ids = {f"REAL-USR-{n:04d}" for n in range(1, 6)}
    ti_pairs: List[Dict[str, str]] = []
    seen: set = set()
    for r in alert_records:
        if r["category"] == "threat_intel_match" or r["user_id"] in planted_ids:
            ti_id = f"REAL-TI-{(r['global_n'] % 20) + 1:03d}"
            key = (r["alert_id"], ti_id)
            if key not in seen:
                ti_pairs.append({"alert_id": r["alert_id"], "ti_id": ti_id})
                seen.add(key)

    if ti_pairs:
        await neo4j_client.run_query(
            "UNWIND $pairs AS pair "
            "MATCH (a:Alert {alert_id: pair.alert_id}) "
            "MATCH (t:ThreatIntel {ti_id: pair.ti_id}) "
            "CREATE (a)-[:ASSOCIATED_WITH]->(t)",
            {"pairs": ti_pairs},
        )
    print(
        f"  [OK] {len(ti_nodes)} ThreatIntel nodes, "
        f"{len(ti_pairs)} [:ASSOCIATED_WITH] edges"
    )

    # ── 5. Travel records ─────────────────────────────────────────────────────
    print("[SEED-2] Creating travel records for frequent travelers...")
    travel_batch: List[Dict[str, Any]] = []
    for props in users:
        if props.get("travel_frequency") == "frequent":
            n = int(props["user_id"].split("-")[-1])
            dest = _TRAVEL_DESTINATIONS[n % len(_TRAVEL_DESTINATIONS)]
            travel_batch.append({
                "user_id": props["user_id"],
                "travel_id": f"REAL-TRAVEL-{n:04d}",
                "destination": dest,
                "start_date": _DATES[n % 30],
                "end_date": _DATES[(n + 3) % 30],
            })

    await neo4j_client.run_query(
        "UNWIND $travels AS t "
        "MATCH (u:User {user_id: t.user_id}) "
        "CREATE (travel:TravelContext {"
        "  travel_id: t.travel_id, "
        "  user_id: t.user_id, "
        "  destination: t.destination, "
        "  start_date: t.start_date, "
        "  end_date: t.end_date "
        "}) "
        "CREATE (u)-[:HAS_TRAVEL]->(travel)",
        {"travels": travel_batch},
    )
    print(f"  [OK] {len(travel_batch)} travel records created")

    # ── 6. DataClass nodes ────────────────────────────────────────────────────
    print("[SEED-2] Creating 10 DataClass nodes (PII / RESTRICTED / CONFIDENTIAL / PUBLIC)...")
    dc_nodes = _build_dataclass_nodes()
    await neo4j_client.run_query(
        "UNWIND $nodes AS dc "
        "CREATE (node:DataClass) "
        "SET node += dc",
        {"nodes": dc_nodes},
    )
    print(f"  [OK] {len(dc_nodes)} DataClass nodes created")

    print("[SEED-2] Realistic seed complete.")
    print(
        f"  Summary — Users: {len(users)} | Alerts: {len(alert_records)} | "
        f"ThreatIntel: {len(ti_nodes)} | Travel: {len(travel_batch)} | "
        f"DataClass: {len(dc_nodes)}"
    )
