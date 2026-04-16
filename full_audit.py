"""
Comprehensive codebase audit for session summary.
Queries the code-review-graph + live AGE to build a complete picture.
"""
import sqlite3
import os
import json
import subprocess
import sys

# ================================================================
# PART 1: Code-review-graph analysis
# ================================================================

db_path = os.path.join(".code-review-graph", "graph.db")
if not os.path.exists(db_path):
    print("[ERROR] Run 'code-review-graph build' first")
    sys.exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

print("=" * 70)
print("COMPREHENSIVE CODEBASE AUDIT")
print("=" * 70)

# --- File counts ---
files = conn.execute("SELECT count(*) AS n FROM nodes WHERE kind = 'File'").fetchone()
nodes = conn.execute("SELECT count(*) AS n FROM nodes").fetchone()
edges = conn.execute("SELECT count(*) AS n FROM edges").fetchone()
print("\nCodebase size:")
print("  Files: " + str(files["n"]))
print("  Nodes: " + str(nodes["n"]))
print("  Edges: " + str(edges["n"]))

# --- Seed scripts (active vs retired vs guarded) ---
print("\n" + "=" * 70)
print("SEED SCRIPTS STATUS")
print("-" * 50)
seed_files = conn.execute(
    "SELECT file_path FROM nodes WHERE kind = 'File' "
    "AND (file_path LIKE '%seed%' OR file_path LIKE '%bootstrap%') "
    "ORDER BY file_path"
).fetchall()
for f in seed_files:
    path = f["file_path"].replace("\\", "/").split("/")
    short = "/".join(path[-3:])
    print("  " + short)

# --- Who calls what in the reset/seed chain ---
print("\n" + "=" * 70)
print("DESTRUCTIVE PATH ANALYSIS")
print("-" * 50)

# All callers of soft_reset/hard_reset
for method in ["soft_reset", "hard_reset"]:
    callers = conn.execute(
        "SELECT DISTINCT file_path, line FROM edges "
        "WHERE target_qualified LIKE '%" + method + "%' "
        "AND kind = 'CALLS' "
        "ORDER BY file_path"
    ).fetchall()
    print("\n  " + method + " callers:")
    for c in callers:
        parts = c["file_path"].replace("\\", "/").split("/")
        print("    " + "/".join(parts[-2:]) + ":L" + str(c["line"]))

# --- E2E test patterns (what alert IDs do they expect?) ---
print("\n" + "=" * 70)
print("E2E TEST EXPECTATIONS")
print("-" * 50)

e2e_files = conn.execute(
    "SELECT file_path FROM nodes WHERE kind = 'File' "
    "AND file_path LIKE '%e2e%' AND file_path LIKE '%.spec.ts%'"
).fetchall()
print("  E2E test files: " + str(len(e2e_files)))
for f in e2e_files:
    parts = f["file_path"].replace("\\", "/").split("/")
    print("    " + parts[-1])

# --- Frontend alert card regex ---
print("\n  Alert card regex patterns in E2E tests:")
for f in e2e_files:
    try:
        with open(f["file_path"], "r", encoding="utf-8") as fh:
            content = fh.read()
            # Find regex patterns for alert matching
            import re
            patterns = re.findall(r'/\^?\(?(SIM-|ALERT-|DEMO-)[^/]*/[gi]?', content)
            if patterns:
                parts = f["file_path"].replace("\\", "/").split("/")
                print("    " + parts[-1] + ": " + str(set(patterns)))
    except Exception:
        pass

# --- What alert_id prefixes exist in v5 JSON? ---
print("\n" + "=" * 70)
print("V5 JSON DATA ANALYSIS")
print("-" * 50)
v5_path = os.path.join("backend", "support", "setup", "zero_day_decisions_v5.json")
if os.path.exists(v5_path):
    with open(v5_path, "r") as f:
        v5 = json.load(f)

    # Alert ID prefixes
    training_prefixes = set()
    for a in v5.get("alerts", []):
        prefix = a["alert_id"].split("-")[0] + "-" + a["alert_id"].split("-")[1]
        training_prefixes.add(prefix)

    demo_prefixes = set()
    for a in v5.get("demo_alerts", []):
        prefix = a["alert_id"].split("-")[0] + "-" + a["alert_id"].split("-")[1]
        demo_prefixes.add(prefix)

    print("  Training alert prefixes: " + str(sorted(training_prefixes)))
    print("  Demo alert prefixes: " + str(sorted(demo_prefixes)))
    print("  Training alerts: " + str(len(v5.get("alerts", []))))
    print("  Demo alerts: " + str(len(v5.get("demo_alerts", []))))
    print("  Decisions: " + str(len(v5.get("decisions", []))))
    print("  Users: " + str(len(v5.get("users", []))))
    print("  Assets: " + str(len(v5.get("assets", []))))
    print("  Campaigns: " + str(len(v5.get("campaigns", []))))

    # Campaign alert_ids
    print("\n  Campaign data:")
    for c in v5.get("campaigns", []):
        aids = c.get("alert_ids", [])
        print("    " + c["campaign_id"] + ": " + str(len(aids)) + " members")

    # What fields do alerts have?
    if v5.get("alerts"):
        print("\n  Alert fields: " + str(sorted(v5["alerts"][0].keys())))
    if v5.get("demo_alerts"):
        print("  Demo alert fields: " + str(sorted(v5["demo_alerts"][0].keys())))

    # ShadowDecision data?
    print("  ShadowDecisions in JSON: " + str(len(v5.get("shadow_decisions", []))))
else:
    print("  [MISSING] " + v5_path)

# --- What does the queue query expect? ---
print("\n" + "=" * 70)
print("QUEUE QUERY ANALYSIS")
print("-" * 50)
triage_path = os.path.join("backend", "app", "routers", "triage.py")
if os.path.exists(triage_path):
    with open(triage_path, "r", encoding="utf-8") as f:
        content = f.read()
    # Find the queue query
    import re
    queue_matches = re.findall(r'MATCH.*Alert.*status.*pending.*RETURN', content, re.DOTALL)
    if queue_matches:
        # Clean up whitespace
        q = queue_matches[0][:200].replace("\n", " ").replace("  ", " ")
        print("  Queue query: " + q + "...")
    # Find alert card regex in frontend
    print("\n  Frontend alert ID expectations:")
    # Check what the frontend API returns as 'id' field
    id_matches = re.findall(r'def _node_id.*?return.*', content)
    for m in id_matches:
        print("    " + m.strip())

# --- conftest.py issues ---
print("\n" + "=" * 70)
print("CONFTEST.PY ANALYSIS")
print("-" * 50)
conftest_path = os.path.join("backend", "conftest.py")
if os.path.exists(conftest_path):
    with open(conftest_path, "r", encoding="utf-8") as f:
        content = f.read()
    if "get_event_loop" in content:
        print("  [BUG] Uses asyncio.get_event_loop() — breaks on Win Python 3.11")
    if "asyncio.run" in content:
        print("  [OK] Uses asyncio.run()")
    if "verify_persistent_data" in content:
        print("  [OK] Has verify_persistent_data fixture")
    if "report_graph_contract" in content:
        print("  [OK] Has report_graph_contract fixture")
    if "pytest.exit" in content:
        print("  [OK] Has blocking pre-test check (pytest.exit)")
    if "pytest.fail" in content:
        print("  [OK] Has post-test check (pytest.fail)")

# --- State manager analysis ---
print("\n" + "=" * 70)
print("STATE MANAGER ANALYSIS")
print("-" * 50)
sm_path = os.path.join("backend", "app", "services", "state_manager.py")
if os.path.exists(sm_path):
    with open(sm_path, "r", encoding="utf-8") as f:
        content = f.read()
    if "PERSISTENT_ORIGIN" in content:
        print("  [OK] Has PERSISTENT_ORIGIN constant")
    if "_verify_deletion_safety" in content:
        print("  [OK] Has _verify_deletion_safety method")
    if "DataProtectionError" in content:
        print("  [OK] Has DataProtectionError exception")
    if "seed_neo4j" in content:
        print("  [BUG] Still references seed_neo4j")
    else:
        print("  [OK] No seed_neo4j references")
    if "hard_reset_all" in content:
        print("  [INFO] Has hard_reset_all method")
    else:
        print("  [INFO] No hard_reset_all (uses hard_reset)")

    # Count methods
    import re
    methods = re.findall(r'async def (\w+)', content)
    print("  Methods: " + str(methods))

# --- graph_schema.py analysis ---
print("\n" + "=" * 70)
print("GRAPH_SCHEMA.PY ANALYSIS")
print("-" * 50)
gs_path = os.path.join("backend", "app", "graph_schema.py")
if os.path.exists(gs_path):
    with open(gs_path, "r", encoding="utf-8") as f:
        content = f.read()
    if '__main__' in content:
        print("  [OK] Has __main__ CLI entry point")
    else:
        print("  [BUG] Missing __main__ CLI entry point")
    if 'MERGE' in content:
        print("  [BUG] Uses MERGE (AGE incompatible)")
    else:
        print("  [OK] No MERGE (uses CREATE)")
    if 'asyncio.run' in content:
        print("  [OK] Uses asyncio.run() in CLI")
    if 'get_event_loop' in content:
        print("  [BUG] Uses get_event_loop")
    if 'GRAPH_CONTRACT' in content:
        print("  [OK] Has GRAPH_CONTRACT")
    if 'verify_graph' in content:
        print("  [OK] Has verify_graph()")
    if 'seed_graph' in content:
        print("  [OK] Has seed_graph()")
    if 'ensure_graph' in content:
        print("  [OK] Calls ensure_graph()")

    line_count = content.count("\n")
    print("  Lines: " + str(line_count))

# --- Metrics.py seed_neo4j status ---
print("\n" + "=" * 70)
print("METRICS.PY SEED STATUS")
print("-" * 50)
metrics_path = os.path.join("backend", "app", "routers", "metrics.py")
if os.path.exists(metrics_path):
    with open(metrics_path, "r", encoding="utf-8") as f:
        content = f.read()
    import re
    live_imports = re.findall(r'^(?!#).*import.*seed_neo4j', content, re.MULTILINE)
    live_calls = re.findall(r'^(?!#).*seed_neo4j\.\w+\(', content, re.MULTILINE)
    print("  Live seed_neo4j imports: " + str(len(live_imports)))
    print("  Live seed_neo4j calls: " + str(len(live_calls)))
    if not live_imports and not live_calls:
        print("  [OK] All seed_neo4j references are blocked/comments")

# --- Test file inventory ---
print("\n" + "=" * 70)
print("TEST INVENTORY")
print("-" * 50)
test_nodes = conn.execute(
    "SELECT file_path FROM nodes WHERE kind = 'File' "
    "AND file_path LIKE '%test_%' "
    "ORDER BY file_path"
).fetchall()
backend_tests = [t for t in test_nodes if "backend" in t["file_path"].replace("\\", "/") and "e2e" not in t["file_path"]]
e2e_tests = [t for t in test_nodes if "e2e" in t["file_path"].replace("\\", "/")]
other_tests = [t for t in test_nodes if t not in backend_tests and t not in e2e_tests]
print("  Backend tests: " + str(len(backend_tests)))
print("  E2E tests: " + str(len(e2e_tests)))
print("  Other tests: " + str(len(other_tests)))

# --- Known broken tests categorization ---
print("\n" + "=" * 70)
print("KNOWN ISSUES SUMMARY")
print("-" * 50)
print("""
CATEGORY 1: Alert ID prefix mismatch (28 E2E failures)
  E2E tests match: /^(SIM-|ALERT-)/ 
  Demo alerts use: DEMO-CA-001, DEMO-LM-001, etc.
  Impact: Every test that clicks an alert times out (30s each)

CATEGORY 2: ShadowDecision data missing (5 failures, backend + E2E)
  analyst-benchmarking returns status='accumulating'
  Needs ShadowDecision nodes or different test expectations

CATEGORY 3: Data gaps (5 E2E failures)
  attack-tactic-breakdown: empty breakdown array
  compounding weekly: zero pattern_count
  chain summary: text pattern /\\d+ alerts in \\w+ cluster/ not matched

CATEGORY 4: conftest.py asyncio bug (non-blocking)
  report_graph_contract uses get_event_loop() 
  Crashes on Windows Python 3.11 at teardown

CATEGORY 5: Stress test method name (2 deselected)
  Tests hard_reset_all() which doesn't exist
  Actual method is hard_reset()
""")

conn.close()
print("=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)
