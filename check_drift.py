"""
check_drift.py — Mechanical drift detection for SOC Copilot.

Catches the class of bugs that text instructions in CLAUDE.md cannot:
- Code patterns that violate AGE constraints
- Data format mismatches between producers and consumers
- Stale references to retired code
- Contract violations

Run after every significant change:
    python check_drift.py

Exit code 0 = clean, 1 = drift detected.
"""

import json
import os
import re
import sys

DRIFT = []
WARN = []


def drift(msg):
    DRIFT.append(msg)
    print("  [DRIFT] " + msg)


def warn(msg):
    WARN.append(msg)
    print("  [WARN]  " + msg)


def ok(msg):
    print("  [OK]    " + msg)


def scan_py(root, pattern, exclude_files=None):
    """Yield (filepath, line_no, line_text) for all .py matches."""
    exclude = set(exclude_files or [])
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in
                   ("node_modules", ".git", "__pycache__",
                    ".code-review-graph", "test-results")]
        for f in files:
            if not f.endswith(".py"):
                continue
            fp = os.path.join(dirpath, f)
            short = fp.replace("\\", "/")
            if any(ex in short for ex in exclude):
                continue
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        if pattern.search(line):
                            yield short, i, line.strip()
            except Exception:
                pass


print("=" * 60)
print("DRIFT DETECTION")
print("=" * 60)

backend = os.path.join("backend")
frontend = os.path.join("frontend")

# ================================================================
# 1. MERGE in production code (AGE incompatible)
# ================================================================
print("\n[1] MERGE in production Cypher (AGE cannot use MERGE)")
# Match MERGE followed by ( — catches Cypher MERGE, skips English "merge"
merge_re = re.compile(r'\bMERGE\s*\(', re.IGNORECASE)
found = False
for fp, ln, line in scan_py(
    os.path.join(backend, "app"), merge_re,
    exclude_files=["age_experiments"]
):
    # Skip lines that are pure comments
    code_part = line.split("#")[0].strip()
    if not code_part:
        continue
    # Skip BLOCKED_KEYWORDS lists
    if "BLOCKED_KEYWORDS" in line:
        continue
    drift("MERGE in " + fp + ":L" + str(ln) + " — " + line[:80])
    found = True
if not found:
    ok("No MERGE in production Cypher")

# ================================================================
# 2. SET n = {} (wipes all properties)
# ================================================================
print("\n[2] SET n = {} in production code (forbidden)")
set_wipe_re = re.compile(r'SET\s+\w+\s*=\s*\{', re.IGNORECASE)
found = False
for fp, ln, line in scan_py(
    os.path.join(backend, "app"), set_wipe_re,
    exclude_files=["age_experiments", "test_"]
):
    drift("SET {} in " + fp + ":L" + str(ln) + " — " + line[:80])
    found = True
if not found:
    ok("No SET n = {} in production code")

# ================================================================
# 3. asyncio.get_event_loop() (broken on Win 3.11)
# ================================================================
print("\n[3] asyncio.get_event_loop() (broken on Windows Python 3.11+)")
loop_re = re.compile(r'get_event_loop\(\)')
found = False
for fp, ln, line in scan_py(backend, loop_re):
    drift("get_event_loop in " + fp + ":L" + str(ln))
    found = True
if not found:
    ok("No get_event_loop usage")

# ================================================================
# 4. Demo alert IDs match E2E regex
# ================================================================
print("\n[4] Demo alert IDs match E2E test expectations")
v5_path = os.path.join(backend, "support", "setup",
                       "zero_day_decisions_v5.json")
if os.path.exists(v5_path):
    with open(v5_path) as f:
        v5 = json.load(f)

    # E2E expects: /^(SIM-|ALERT-)/ (checklist.spec.ts:16)
    #              /ALERT-|SIM-/i   (deep_flows.spec.ts:27)
    #              /SIM-/           (decision_flow.spec.ts:28)
    e2e_pattern = re.compile(r'^(SIM-|ALERT-)', re.IGNORECASE)

    bad_ids = []
    for a in v5.get("demo_alerts", []):
        if not e2e_pattern.match(a["alert_id"]):
            bad_ids.append(a["alert_id"])
    if bad_ids:
        drift("Demo alert IDs won't match E2E regex: " +
              str(bad_ids[:5]) +
              " (expected SIM- or ALERT- prefix)")
    else:
        ok("All " + str(len(v5.get("demo_alerts", []))) +
           " demo alert IDs match E2E regex")

    # Also check training alerts don't accidentally match
    # (they shouldn't appear in the queue)
else:
    warn("v5 JSON not found: " + v5_path)

# ================================================================
# 5. Campaign alert_ids reference real alerts
# ================================================================
print("\n[5] Campaign alert_ids reference real alerts")
if os.path.exists(v5_path):
    alert_ids = {a["alert_id"] for a in v5.get("alerts", [])}
    campaign_ok = True
    for c in v5.get("campaigns", []):
        camp_aids = c.get("alert_ids", [])
        if not camp_aids:
            warn("Campaign " + c["campaign_id"] + " has empty alert_ids")
        else:
            missing = [a for a in camp_aids if a not in alert_ids]
            if missing:
                drift("Campaign " + c["campaign_id"] +
                      " references missing alerts: " + str(missing[:3]))
                campaign_ok = False
    if campaign_ok:
        ok("All campaign alert_ids reference real alerts")

# ================================================================
# 6. seed_neo4j.py has RuntimeError guards
# ================================================================
print("\n[6] seed_neo4j.py has RuntimeError guards on AGE")
for seed_path in [
    os.path.join(backend, "seed_neo4j.py"),
    os.path.join(backend, "app", "services", "seed_neo4j.py"),
]:
    if os.path.exists(seed_path):
        with open(seed_path) as f:
            content = f.read()
        if "RuntimeError" in content:
            ok("Guard present: " + seed_path)
        else:
            drift("No RuntimeError guard: " + seed_path)

# ================================================================
# 7. graph_schema.py in ALLOWED_FILES
# ================================================================
print("\n[7] graph_schema.py in static analysis ALLOWED_FILES")
sa_path = os.path.join(backend, "tests",
                       "test_no_destructive_decision_queries.py")
if os.path.exists(sa_path):
    with open(sa_path) as f:
        content = f.read()
    if "graph_schema.py" in content:
        ok("graph_schema.py in ALLOWED_FILES")
    else:
        drift("graph_schema.py NOT in ALLOWED_FILES")
else:
    warn("Static analysis test not found")

# ================================================================
# 8. No live seed_neo4j imports in metrics.py
# ================================================================
print("\n[8] No live seed_neo4j imports in metrics.py")
metrics_path = os.path.join(backend, "app", "routers", "metrics.py")
if os.path.exists(metrics_path):
    with open(metrics_path) as f:
        content = f.read()
    live_imports = re.findall(
        r'^(?!#).*import.*seed_neo4j', content, re.MULTILINE
    )
    if live_imports:
        drift("Live seed_neo4j import in metrics.py")
    else:
        ok("No live seed_neo4j imports in metrics.py")

# ================================================================
# 9. ShadowDecision source data exists
# ================================================================
print("\n[9] ShadowDecision source data")
shadow_source = os.path.join(
    os.path.dirname(backend), "..", "cross-graph-experiments",
    "experiments", "v_shadow_synthetic_v3",
    "v_shadow_synthetic_results.json"
)
# Normalize for display
shadow_source_norm = os.path.normpath(shadow_source)
if os.path.exists(shadow_source):
    ok("ShadowDecision source exists: " + shadow_source_norm)
else:
    warn("ShadowDecision source not found: " + shadow_source_norm +
         " (analyst-benchmarking needs seed_shadow_decisions.py)")

# ================================================================
# 10. JSON referential integrity (decisions -> alerts)
# ================================================================
print("\n[10] JSON referential integrity")
if os.path.exists(v5_path):
    all_alert_ids = {a["alert_id"] for a in v5.get("alerts", [])}
    orphans = [d["decision_id"] for d in v5.get("decisions", [])
               if d.get("alert_id") not in all_alert_ids]
    if orphans:
        drift(str(len(orphans)) + " decisions reference missing alerts")
    else:
        ok("All " + str(len(v5.get("decisions", []))) +
           " decisions reference valid alerts")

# ================================================================
# 11. Origin string consistency
# ================================================================
print("\n[11] Origin string consistency")
gs_path = os.path.join(backend, "app", "graph_schema.py")
sm_path = os.path.join(backend, "app", "services", "state_manager.py")
triage_path_check = os.path.join(backend, "app", "routers", "triage.py")

# SYNTHETIC_ORIGIN must match between graph_schema and state_manager
synthetic_values = set()
for path in [gs_path, sm_path]:
    if os.path.exists(path):
        with open(path) as f:
            content = f.read()
        matches = re.findall(
            r"(?:SYNTHETIC_ORIGIN|PERSISTENT_ORIGIN)\s*=\s*['\"]([^'\"]+)['\"]",
            content
        )
        synthetic_values.update(matches)
if len(synthetic_values) > 1:
    drift("Multiple synthetic origin values: " + str(synthetic_values))
elif synthetic_values:
    ok("Consistent synthetic origin: " + str(synthetic_values.pop()))

# DEMO_ORIGIN must match between graph_schema and triage.py reset
if os.path.exists(gs_path):
    with open(gs_path) as f:
        gs_content = f.read()
    demo_match = re.search(r"DEMO_ORIGIN\s*=\s*['\"]([^'\"]+)['\"]", gs_content)
    if demo_match:
        demo_val = demo_match.group(1)
        if os.path.exists(triage_path_check):
            with open(triage_path_check) as f:
                triage_content = f.read()
            if demo_val in triage_content:
                ok("DEMO_ORIGIN '" + demo_val + "' consistent in triage.py")
            else:
                drift("DEMO_ORIGIN '" + demo_val + "' not found in triage.py reset")

# Demo alerts in v5 JSON must use DEMO_ORIGIN
if os.path.exists(v5_path):
    demo_origins = set(a.get("origin", "") for a in v5.get("demo_alerts", []))
    training_origins = set(a.get("origin", "") for a in v5.get("alerts", []))
    if demo_origins and demo_origins != {"zero_day_demo"}:
        drift("Demo alerts have wrong origin: " + str(demo_origins))
    elif demo_origins:
        ok("Demo alerts origin: zero_day_demo")
    if training_origins and training_origins != {"zero_day_synthetic"}:
        drift("Training alerts have wrong origin: " + str(training_origins))
    elif training_origins:
        ok("Training alerts origin: zero_day_synthetic")

# ================================================================
# SUMMARY
# ================================================================
print("\n" + "=" * 60)
if DRIFT:
    print("DRIFT DETECTED: " + str(len(DRIFT)) + " issues")
    for d in DRIFT:
        print("  - " + d)
    sys.exit(1)
elif WARN:
    print("CLEAN (with " + str(len(WARN)) + " warnings)")
    sys.exit(0)
else:
    print("CLEAN — no drift detected")
    sys.exit(0)
