"""
support/setup/enrich_zero_day_v5.py -- Enrich v4 zero_day_decisions.json to v5.

Adds to the existing 540 alerts + 4860 decisions:
  - 20 User records (zero_day_synthetic)
  - 15 Asset records (zero_day_synthetic)
  - 6 AttackPattern records (MITRE ATT&CK)
  - 5 ThreatIndicator records
  - user_id, asset_id, attack_pattern_id, indicator_ids on each v4 alert
  - 4 Campaign groups (CAMP-001..004)
  - 30 demo_alerts (status='pending', no decisions)

Reads:  zero_day_decisions.json  (v4, unchanged)
Writes: zero_day_decisions_v5.json

Usage:
    python support/setup/enrich_zero_day_v5.py
"""
from __future__ import annotations
import json
import sys
import datetime
from collections import defaultdict
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
HERE    = Path(__file__).parent
V4_PATH = HERE / "zero_day_decisions.json"
V5_PATH = HERE / "zero_day_decisions_v5.json"

# ── Load v4 ───────────────────────────────────────────────────────────────────
print(f"[LOAD] Reading {V4_PATH.name}...")
with open(V4_PATH, encoding="utf-8") as f:
    v4 = json.load(f)

v4_alerts    = v4["alerts"]
v4_decisions = v4["decisions"]
v4_metadata  = v4.get("metadata", {})

print(f"  {len(v4_alerts)} alerts, {len(v4_decisions)} decisions")
print(f"  Alert keys:    {list(v4_alerts[0].keys())}")
print(f"  Decision keys: {list(v4_decisions[0].keys())}")

from collections import Counter
cat_dist = Counter(a["category"] for a in v4_alerts)
print("  Category distribution:")
for cat, cnt in sorted(cat_dist.items()):
    print(f"    {cat}: {cnt}")

unique_user_ids = set(a.get("user_id", "") for a in v4_alerts)
print(f"  Unique user_id values in v4: {sorted(unique_user_ids)} (count={len(unique_user_ids)})")

MIN_TS = min(a["timestamp_epoch"] for a in v4_alerts)
MAX_TS = max(a["timestamp_epoch"] for a in v4_alerts)
DAY_MS = 86_400_000
print(f"  Min ts: {MIN_TS} = {datetime.datetime.utcfromtimestamp(MIN_TS/1000).date()}")
print(f"  Max ts: {MAX_TS} = {datetime.datetime.utcfromtimestamp(MAX_TS/1000).date()}")
print(f"  Day range: {(MAX_TS - MIN_TS) // DAY_MS} days")

# ── Hardcoded backbone data ────────────────────────────────────────────────────

USERS = [
    {"user_id": "USR-001", "name": "Sarah K.",       "department": "engineering", "risk_level": "standard"},
    {"user_id": "USR-002", "name": "James R.",        "department": "finance",     "risk_level": "standard"},
    {"user_id": "USR-003", "name": "Maria L.",        "department": "security",    "risk_level": "elevated"},
    {"user_id": "USR-004", "name": "David W.",        "department": "executive",   "risk_level": "high"},
    {"user_id": "USR-005", "name": "Chen H.",         "department": "engineering", "risk_level": "standard"},
    {"user_id": "USR-006", "name": "Priya M.",        "department": "IT",          "risk_level": "standard"},
    {"user_id": "USR-007", "name": "Robert J.",       "department": "finance",     "risk_level": "standard"},
    {"user_id": "USR-008", "name": "Ana G.",          "department": "engineering", "risk_level": "standard"},
    {"user_id": "USR-009", "name": "Tom J.",          "department": "security",    "risk_level": "elevated"},
    {"user_id": "USR-010", "name": "Lisa C.",         "department": "IT",          "risk_level": "standard"},
    {"user_id": "USR-011", "name": "Mike C.",         "department": "engineering", "risk_level": "standard"},
    {"user_id": "USR-012", "name": "Alice L.",        "department": "finance",     "risk_level": "standard"},
    {"user_id": "USR-013", "name": "Mary C.",         "department": "executive",   "risk_level": "high"},
    {"user_id": "USR-014", "name": "Mike W.",         "department": "IT",          "risk_level": "elevated"},
    {"user_id": "USR-015", "name": "Kavita P.",       "department": "engineering", "risk_level": "standard"},
    {"user_id": "USR-016", "name": "Richard W.",      "department": "security",    "risk_level": "elevated"},
    {"user_id": "USR-017", "name": "John S.",         "department": "engineering", "risk_level": "standard"},
    {"user_id": "USR-018", "name": "svc-backup",      "department": "IT",          "risk_level": "service"},
    {"user_id": "USR-019", "name": "system",          "department": "IT",          "risk_level": "service"},
    {"user_id": "USR-020", "name": "devops-pipeline", "department": "engineering", "risk_level": "service"},
]
for u in USERS:
    u["origin"] = "zero_day_synthetic"

ASSETS = [
    {"asset_id": "AST-001", "hostname": "dc-prod-01.corp.local",  "criticality": "critical", "asset_type": "domain_controller"},
    {"asset_id": "AST-002", "hostname": "dc-prod-02.corp.local",  "criticality": "critical", "asset_type": "domain_controller"},
    {"asset_id": "AST-003", "hostname": "srv-db-prod-01",         "criticality": "high",     "asset_type": "server"},
    {"asset_id": "AST-004", "hostname": "srv-web-03",             "criticality": "high",     "asset_type": "server"},
    {"asset_id": "AST-005", "hostname": "srv-backup-01",          "criticality": "high",     "asset_type": "server"},
    {"asset_id": "AST-006", "hostname": "srv-app-prod-01",        "criticality": "high",     "asset_type": "server"},
    {"asset_id": "AST-007", "hostname": "srv-mail-01",            "criticality": "high",     "asset_type": "server"},
    {"asset_id": "AST-008", "hostname": "ws-eng-042",             "criticality": "medium",   "asset_type": "workstation"},
    {"asset_id": "AST-009", "hostname": "ws-fin-019",             "criticality": "medium",   "asset_type": "workstation"},
    {"asset_id": "AST-010", "hostname": "ws-sec-007",             "criticality": "medium",   "asset_type": "workstation"},
    {"asset_id": "AST-011", "hostname": "ws-exec-003",            "criticality": "medium",   "asset_type": "workstation"},
    {"asset_id": "AST-012", "hostname": "ws-it-015",              "criticality": "medium",   "asset_type": "workstation"},
    {"asset_id": "AST-013", "hostname": "ws-eng-088",             "criticality": "medium",   "asset_type": "workstation"},
    {"asset_id": "AST-014", "hostname": "vpn-gateway-01",         "criticality": "high",     "asset_type": "network_device"},
    {"asset_id": "AST-015", "hostname": "aws-prod-account",       "criticality": "high",     "asset_type": "cloud_resource"},
]
for a in ASSETS:
    a["origin"] = "zero_day_synthetic"

ATTACK_PATTERNS = [
    {"pattern_id": "T1078",     "name": "Valid Accounts",                          "mitre_id": "T1078",     "tactic": "initial_access",       "category": "credential_access"},
    {"pattern_id": "T1021",     "name": "Remote Services",                         "mitre_id": "T1021",     "tactic": "lateral_movement",     "category": "lateral_movement"},
    {"pattern_id": "T1048",     "name": "Exfiltration Over Alternative Protocol",  "mitre_id": "T1048",     "tactic": "exfiltration",         "category": "data_exfiltration"},
    {"pattern_id": "T1588",     "name": "Obtain Capabilities",                     "mitre_id": "T1588",     "tactic": "resource_development", "category": "malware_execution"},
    {"pattern_id": "T1078.004", "name": "Valid Accounts: Cloud Accounts",          "mitre_id": "T1078.004", "tactic": "persistence",          "category": "insider_threat"},
    {"pattern_id": "T1078.003", "name": "Valid Accounts: Local Accounts",          "mitre_id": "T1078.003", "tactic": "defense_evasion",      "category": "cloud_infrastructure"},
]
for p in ATTACK_PATTERNS:
    p["origin"] = "zero_day_synthetic"

THREAT_INDICATORS = [
    {"indicator": "103.15.42.17",                "indicator_type": "ip",     "severity": "high",     "source": "Pulsedive"},
    {"indicator": "185.220.101.34",              "indicator_type": "ip",     "severity": "critical", "source": "Pulsedive"},
    {"indicator": "cobaltstrike.github.io",      "indicator_type": "domain", "severity": "critical", "source": "Pulsedive"},
    {"indicator": "45.33.32.156",                "indicator_type": "ip",     "severity": "medium",   "source": "Pulsedive"},
    {"indicator": "malware-traffic-analysis.net","indicator_type": "domain", "severity": "high",     "source": "Pulsedive"},
]
for t in THREAT_INDICATORS:
    t["origin"] = "zero_day_synthetic"

# ── Category → user / asset / pattern pools ───────────────────────────────────

CATEGORY_USER_MAP = {
    "credential_access":    ["USR-004", "USR-013", "USR-017", "USR-012", "USR-001"],
    "lateral_movement":     ["USR-014", "USR-006", "USR-010", "USR-018", "USR-011"],
    "data_exfiltration":    ["USR-002", "USR-007", "USR-012", "USR-017", "USR-008"],
    "malware_execution":    ["USR-001", "USR-005", "USR-008", "USR-011", "USR-015"],
    "insider_threat":       ["USR-003", "USR-009", "USR-016", "USR-014", "USR-006"],
    "cloud_infrastructure": ["USR-019", "USR-020", "USR-006", "USR-010", "USR-014"],
}

CATEGORY_ASSET_MAP = {
    "credential_access":    ["AST-001", "AST-002", "AST-011", "AST-008", "AST-009"],
    "lateral_movement":     ["AST-003", "AST-004", "AST-005", "AST-006", "AST-007"],
    "data_exfiltration":    ["AST-008", "AST-009", "AST-014", "AST-011", "AST-013"],
    "malware_execution":    ["AST-008", "AST-013", "AST-003", "AST-004", "AST-012"],
    "insider_threat":       ["AST-003", "AST-005", "AST-010", "AST-006", "AST-007"],
    "cloud_infrastructure": ["AST-015", "AST-014", "AST-012", "AST-006", "AST-004"],
}

CATEGORY_PATTERN_MAP = {
    "credential_access":    "T1078",
    "lateral_movement":     "T1021",
    "data_exfiltration":    "T1048",
    "malware_execution":    "T1588",
    "insider_threat":       "T1078.004",
    "cloud_infrastructure": "T1078.003",
}

# ── Campaign definitions ───────────────────────────────────────────────────────

CAMPAIGN_DEFS = [
    {
        "campaign_id": "CAMP-001",
        "name": "Credential Harvesting Wave",
        "categories": ["credential_access"],
        "day_range": (5, 15),
        "pick": 6,
        "severity": "high",
        "confidence": 0.82,
        "trigger_rule": "sequential_category",
        "correlation_window_hours": 240,
        "nl_summary": "Coordinated credential harvesting against domain controllers and executive workstations across a 10-day window.",
    },
    {
        "campaign_id": "CAMP-002",
        "name": "Lateral Movement Campaign",
        "categories": ["lateral_movement"],
        "day_range": (20, 35),
        "pick": 5,
        "severity": "critical",
        "confidence": 0.88,
        "trigger_rule": "sequential_category",
        "correlation_window_hours": 360,
        "nl_summary": "Systematic lateral movement from compromised servers toward database and backup infrastructure.",
    },
    {
        "campaign_id": "CAMP-003",
        "name": "Data Exfiltration Attempt",
        "categories": ["data_exfiltration"],
        "day_range": (40, 55),
        "pick": 4,
        "severity": "critical",
        "confidence": 0.85,
        "trigger_rule": "shared_asset",
        "correlation_window_hours": 360,
        "nl_summary": "Staged data exfiltration via VPN gateway and cloud resources, targeting finance and engineering data.",
    },
    {
        "campaign_id": "CAMP-004",
        "name": "APT Multi-Phase Intrusion",
        "categories": ["credential_access", "lateral_movement", "data_exfiltration"],
        "day_range": (60, 80),
        "pick": 8,
        "severity": "critical",
        "confidence": 0.91,
        "trigger_rule": "multi_category",
        "correlation_window_hours": 480,
        "nl_summary": "Nation-state APT multi-phase intrusion: credential access, lateral movement, and data exfiltration across a 20-day campaign.",
    },
]

# ── Demo alert config ──────────────────────────────────────────────────────────

CATEGORIES = [
    "credential_access", "lateral_movement", "data_exfiltration",
    "malware_execution", "insider_threat", "cloud_infrastructure",
]

CAT_PREFIX = {
    "credential_access":    "CA",
    "lateral_movement":     "LM",
    "data_exfiltration":    "DE",
    "malware_execution":    "ME",
    "insider_threat":       "IT",
    "cloud_infrastructure": "CI",
}

DEMO_ALERT_TYPE_MAP = {
    "credential_access":    "anomalous_login",
    "lateral_movement":     "privilege_escalation",
    "data_exfiltration":    "data_exfil",
    "malware_execution":    "malware_detection",
    "insider_threat":       "insider_threat",
    "cloud_infrastructure": "cloud_config",
}

# 5 per category: 1 critical, 2 high, 1 medium, 1 low
DEMO_SEVERITIES = ["critical", "high", "high", "medium", "low"]

DEMO_SOURCE_LOCATIONS = [
    "10.0.1.54",
    "vpn-gw.corp.local",
    "aws-prod-eu-west-1",
    "192.168.100.23",
    "citrix-gateway.corp",
    "10.10.5.128",
    "srv-proxy-01.corp.local",
    "edge-fw-02.corp",
    "172.16.8.201",
    "remote.vpn.corp.local",
]

# ── Lookup dicts ───────────────────────────────────────────────────────────────
user_by_id  = {u["user_id"]: u for u in USERS}
asset_by_id = {a["asset_id"]: a for a in ASSETS}


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Enrich v4 alerts with user_id, asset_id, attack_pattern_id, indicator_ids
# ─────────────────────────────────────────────────────────────────────────────
print("\n[STEP 1] Assigning user_id, asset_id, attack_pattern_id, indicator_ids to v4 alerts...")

alerts   = [dict(a) for a in v4_alerts]   # shallow copy -- we'll mutate
cat_idx  = defaultdict(int)
ind_cycle = 0

for i, alert in enumerate(alerts):
    cat  = alert["category"]
    cidx = cat_idx[cat]
    cat_idx[cat] += 1

    alert["user_id"]           = CATEGORY_USER_MAP[cat][cidx % len(CATEGORY_USER_MAP[cat])]
    alert["asset_id"]          = CATEGORY_ASSET_MAP[cat][cidx % len(CATEGORY_ASSET_MAP[cat])]
    alert["attack_pattern_id"] = CATEGORY_PATTERN_MAP[cat]

    if i % 20 == 0:
        alert["indicator_ids"] = [
            THREAT_INDICATORS[ind_cycle       % len(THREAT_INDICATORS)]["indicator"],
            THREAT_INDICATORS[(ind_cycle + 1) % len(THREAT_INDICATORS)]["indicator"],
        ]
        ind_cycle += 2
    elif i % 10 == 0:
        alert["indicator_ids"] = [
            THREAT_INDICATORS[ind_cycle % len(THREAT_INDICATORS)]["indicator"],
        ]
        ind_cycle += 1
    else:
        alert["indicator_ids"] = []

n_with_indicators = sum(1 for a in alerts if a["indicator_ids"])
print(f"  {len(alerts)} alerts enriched.")
print(f"  indicator_ids assigned to {n_with_indicators} alerts (~{n_with_indicators/len(alerts):.0%}).")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Build campaigns
# ─────────────────────────────────────────────────────────────────────────────
print("\n[STEP 2] Building campaigns...")


def ts_to_iso(ts_ms: int) -> str:
    return datetime.datetime.utcfromtimestamp(ts_ms / 1000).isoformat()


campaigns = []
for cdef in CAMPAIGN_DEFS:
    day_start_ts = MIN_TS + (cdef["day_range"][0] - 1) * DAY_MS
    day_end_ts   = MIN_TS + (cdef["day_range"][1] - 1) * DAY_MS

    cats = set(cdef["categories"])
    candidates = sorted(
        [
            a for a in alerts
            if a["category"] in cats
            and day_start_ts <= a["timestamp_epoch"] <= day_end_ts
        ],
        key=lambda a: a["timestamp_epoch"],
    )
    members = candidates[: cdef["pick"]]

    if not members:
        print(f"  [WARN] {cdef['campaign_id']}: no matching alerts for {cats} in days {cdef['day_range']}")

    member_ids   = [a["alert_id"] for a in members]
    cat_sequence = [a["category"] for a in members]
    first_seen   = ts_to_iso(members[0]["timestamp_epoch"])  if members else ts_to_iso(MIN_TS)
    last_seen    = ts_to_iso(members[-1]["timestamp_epoch"]) if members else ts_to_iso(MIN_TS)

    campaigns.append({
        "campaign_id":             cdef["campaign_id"],
        "name":                    cdef["name"],
        "severity":                cdef["severity"],
        "confidence":              cdef["confidence"],
        "trigger_rule":            cdef["trigger_rule"],
        "category_sequence":       cat_sequence,
        "shared_entities":         [],
        "technique_sequence":      [],
        "nl_summary":              cdef["nl_summary"],
        "member_alert_ids":        member_ids,
        "alert_count":             len(member_ids),
        "correlation_window_hours": cdef["correlation_window_hours"],
        "first_seen":              first_seen,
        "last_seen":               last_seen,
        "origin":                  "zero_day_synthetic",
    })
    print(f"  {cdef['campaign_id']}: {len(member_ids)} alerts matched "
          f"(days {cdef['day_range']}, cats={sorted(cats)})")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Generate 30 demo alerts (5 per category, status='pending')
# ─────────────────────────────────────────────────────────────────────────────
print("\n[STEP 3] Generating 30 demo alerts (5 per category, status='pending')...")

demo_alerts = []
src_cycle   = 0

for cat in CATEGORIES:
    prefix     = CAT_PREFIX[cat]
    user_pool  = CATEGORY_USER_MAP[cat]
    asset_pool = CATEGORY_ASSET_MAP[cat]

    for i, sev in enumerate(DEMO_SEVERITIES):
        alert_id = f"DEMO-{prefix}-{i + 1:03d}"
        user_id  = user_pool[i % len(user_pool)]
        asset_id = asset_pool[i % len(asset_pool)]
        # Spread across last 7 days; add hour offset for intra-day variety
        ts_epoch = MAX_TS - (6 - i) * DAY_MS + i * 3_600_000

        demo_alerts.append({
            "alert_id":          alert_id,
            "category":          cat,
            "severity":          sev,
            "alert_type":        DEMO_ALERT_TYPE_MAP[cat],
            "timestamp_epoch":   ts_epoch,
            "origin":            "zero_day_synthetic",
            "source_location":   DEMO_SOURCE_LOCATIONS[src_cycle % len(DEMO_SOURCE_LOCATIONS)],
            "user_id":           user_id,
            "asset_id":          asset_id,
            "user_name":         user_by_id[user_id]["name"],
            "asset_hostname":    asset_by_id[asset_id]["hostname"],
            "attack_pattern_id": CATEGORY_PATTERN_MAP[cat],
            "indicator_ids":     [],
            "status":            "pending",
        })
        src_cycle += 1

print(f"  {len(demo_alerts)} demo alerts generated.")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: Assemble v5
# ─────────────────────────────────────────────────────────────────────────────
print("\n[STEP 4] Assembling v5 JSON...")

# Carry forward select v4 metadata fields
_carry = ["days_simulated", "category_order", "action_order",
          "p_correct_by_cat", "rng_seed", "overall_correct_rate"]

v5 = {
    "metadata": {
        "generator":                "enrich_zero_day_v5",
        "version":                  "5.0",
        "based_on":                 "zero_day_decisions.json (v4)",
        "total_alerts":             len(alerts),
        "total_demo_alerts":        len(demo_alerts),
        "total_decisions":          len(v4_decisions),
        "total_users":              len(USERS),
        "total_assets":             len(ASSETS),
        "total_attack_patterns":    len(ATTACK_PATTERNS),
        "total_threat_indicators":  len(THREAT_INDICATORS),
        "total_campaigns":          len(campaigns),
        **{k: v4_metadata[k] for k in _carry if k in v4_metadata},
    },
    "users":             USERS,
    "assets":            ASSETS,
    "attack_patterns":   ATTACK_PATTERNS,
    "threat_indicators": THREAT_INDICATORS,
    "campaigns":         campaigns,
    "alerts":            alerts,
    "demo_alerts":       demo_alerts,
    "decisions":         [dict(d) for d in v4_decisions],  # copy -- we mutate user_id below
}

# Propagate user_id from enriched alerts to decisions (v4 decisions all had user_id='')
_alert_user_map = {a["alert_id"]: a["user_id"] for a in v5["alerts"]}
_fixed = 0
for d in v5["decisions"]:
    if not d.get("user_id"):
        d["user_id"] = _alert_user_map.get(d["alert_id"], "")
        _fixed += 1
print(f"  Propagated user_id to {_fixed} decisions.")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: Validation — 18 gates
# ─────────────────────────────────────────────────────────────────────────────
print("\n[STEP 5] Validating (18 gates)...")

VALID_ACTIONS = {"escalate", "investigate", "suppress", "monitor"}
VALID_CATS    = set(CATEGORIES)

failures: list[str] = []

def gate(n: int, desc: str, ok: bool, detail: str = "") -> None:
    label = "[OK  ]" if ok else "[FAIL]"
    line  = f"  {label} Gate {n:02d}: {desc}"
    if not ok and detail:
        line += f" -- {detail}"
    print(line)
    if not ok:
        failures.append(line)


dec    = v5["decisions"]
al     = v5["alerts"]
da     = v5["demo_alerts"]
al_ids = {a["alert_id"] for a in al}
usr_ids = {u["user_id"] for u in v5["users"]}
ast_ids = {a["asset_id"] for a in v5["assets"]}

gate(1,  "len(decisions) == 4860",
     len(dec) == 4860, f"got {len(dec)}")

_req_dec = {"decision_id", "category", "action", "factor_vector", "confidence", "correct", "outcome"}
gate(2,  "All decisions have required fields",
     all(_req_dec.issubset(d.keys()) for d in dec))

gate(3,  "All factor_vectors have length 6",
     all(isinstance(d["factor_vector"], list) and len(d["factor_vector"]) == 6 for d in dec))

_bad_actions = [d["action"] for d in dec if d["action"] not in VALID_ACTIONS]
gate(4,  "All decision actions valid",
     len(_bad_actions) == 0, f"invalid: {_bad_actions[:5]}")

_bad_cats = [d["category"] for d in dec if d["category"] not in VALID_CATS]
gate(5,  "All decision categories valid",
     len(_bad_cats) == 0, f"invalid: {_bad_cats[:5]}")

_orphan_dec = [d["alert_id"] for d in dec if d["alert_id"] not in al_ids]
gate(6,  "Every decision.alert_id exists in alerts",
     len(_orphan_dec) == 0, f"orphan sample: {_orphan_dec[:3]}")

correct_rate = sum(1 for d in dec if d["correct"]) / len(dec)
gate(7,  f"Correct rate 70-90% (actual={correct_rate:.1%})",
     0.70 <= correct_rate <= 0.90)

cat_correct: dict[str, list[bool]] = defaultdict(list)
for d in dec:
    cat_correct[d["category"]].append(bool(d["correct"]))
cat_rates = {cat: sum(vals) / len(vals) for cat, vals in cat_correct.items()}
variance  = sum((r - correct_rate) ** 2 for r in cat_rates.values()) / len(cat_rates)
gate(8,  f"Per-category correct rate variance > 0 (var={variance:.6f})",
     variance > 0)

gate(9,  "len(alerts) == 540",
     len(al) == 540, f"got {len(al)}")

gate(10, "len(users) >= 20 with user_id, name, department",
     len(v5["users"]) >= 20
     and all("user_id" in u and "name" in u and "department" in u for u in v5["users"]))

gate(11, "len(assets) >= 15 with asset_id, hostname, criticality",
     len(v5["assets"]) >= 15
     and all("asset_id" in a and "hostname" in a and "criticality" in a for a in v5["assets"]))

_bad_usr = [a["alert_id"] for a in al if a.get("user_id") not in usr_ids]
gate(12, "Every alert has user_id matching a user",
     len(_bad_usr) == 0, f"sample: {_bad_usr[:3]}")

_bad_ast = [a["alert_id"] for a in al if a.get("asset_id") not in ast_ids]
gate(13, "Every alert has asset_id matching an asset",
     len(_bad_ast) == 0, f"sample: {_bad_ast[:3]}")

_non_pending = [a["alert_id"] for a in da if a["status"] != "pending"]
gate(14, f"len(demo_alerts) >= 25, all status='pending' (got {len(da)})",
     len(da) >= 25 and len(_non_pending) == 0,
     f"non-pending: {_non_pending[:3]}")

_camp_issues = [
    f"{c['campaign_id']}:{len(c['member_alert_ids'])} members"
    for c in v5["campaigns"]
    if len(c["member_alert_ids"]) < 3
    or any(aid not in al_ids for aid in c["member_alert_ids"])
]
gate(15, "len(campaigns) == 4, each >= 3 member_alert_ids in alerts",
     len(v5["campaigns"]) == 4 and len(_camp_issues) == 0,
     f"issues: {_camp_issues}")

gate(16, "len(threat_indicators) >= 5",
     len(v5["threat_indicators"]) >= 5)

gate(17, "len(attack_patterns) == 6",
     len(v5["attack_patterns"]) == 6)

_bad_demo = [
    a["alert_id"] for a in da
    if a.get("user_id") not in usr_ids or a.get("asset_id") not in ast_ids
]
gate(18, "Every demo_alert has user_id and asset_id from pools",
     len(_bad_demo) == 0, f"bad: {_bad_demo[:3]}")

print()
if failures:
    print(f"[FAIL] {len(failures)} gate(s) failed. Fix before saving.")
    for f in failures:
        print(f"  {f}")
    sys.exit(1)

print("[OK] All 18 validation gates passed.")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6: Save
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[SAVE] Writing {V5_PATH}...")
with open(V5_PATH, "w", encoding="utf-8") as f:
    json.dump(v5, f, indent=2)

size_mb = V5_PATH.stat().st_size / (1024 * 1024)
print(f"  Size: {size_mb:.2f} MB")
print(f"\n[DONE] zero_day_decisions_v5.json written.")
