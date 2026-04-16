"""
Deep structural audit — finds problems we DON'T already know about.

Categories:
1. ALL Cypher mutations across the codebase (not just Decision)
2. ALL async patterns (get_event_loop vs asyncio.run)
3. ALL hardcoded alert IDs in frontend + backend + tests
4. ALL bare except blocks
5. ALL TODO/FIXME/HACK markers
6. ALL import chains from graph_schema / state_manager
7. Frontend-backend contract mismatches
8. Dead code (functions never called)
9. Circular dependencies
10. Files changed but not tested
"""
import sqlite3
import os
import re
import json
import sys
from collections import defaultdict

db_path = os.path.join(".code-review-graph", "graph.db")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

def walk_py(root):
    """Yield (filepath, content) for all .py files under root."""
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "__pycache__", ".code-review-graph", "test-results")]
        for f in files:
            if f.endswith(".py"):
                fp = os.path.join(dirpath, f)
                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                        yield fp, fh.read()
                except Exception:
                    pass

def walk_ts(root):
    """Yield (filepath, content) for all .ts/.tsx files under root."""
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "__pycache__", "dist", "build")]
        for f in files:
            if f.endswith((".ts", ".tsx")):
                fp = os.path.join(dirpath, f)
                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                        yield fp, fh.read()
                except Exception:
                    pass

def short(path):
    parts = path.replace("\\", "/").split("/")
    return "/".join(parts[-2:])

backend = os.path.join("backend")
frontend = os.path.join("frontend")

print("=" * 70)
print("DEEP STRUCTURAL AUDIT")
print("=" * 70)

# ================================================================
# 1. ALL Cypher mutations (not just Decision)
# ================================================================
print("\n[1/10] ALL Cypher mutations across backend")
print("-" * 50)
mutation_patterns = [
    (r'DETACH\s+DELETE', "DETACH DELETE"),
    (r'(?<!DETACH\s)DELETE\s', "DELETE"),
    (r'REMOVE\s+\w+\.\w+', "REMOVE property"),
    (r'SET\s+\w+\s*=\s*\{', "SET n = {} (wipe props)"),
    (r'CREATE\s+\(', "CREATE node"),
]
mutation_counts = defaultdict(list)
for fp, content in walk_py(backend):
    for pattern, label in mutation_patterns:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        if matches:
            for m in matches:
                # Get line number
                line_no = content[:m.start()].count("\n") + 1
                mutation_counts[label].append(short(fp) + ":L" + str(line_no))

for label, locations in sorted(mutation_counts.items()):
    print("  " + label + ": " + str(len(locations)) + " occurrences")
    for loc in locations[:5]:
        print("    " + loc)
    if len(locations) > 5:
        print("    ... and " + str(len(locations) - 5) + " more")

# ================================================================
# 2. ALL async patterns
# ================================================================
print("\n[2/10] Async pattern analysis")
print("-" * 50)
event_loop_files = []
asyncio_run_files = []
for fp, content in walk_py(backend):
    if "get_event_loop" in content:
        lines = [i+1 for i, l in enumerate(content.split("\n")) if "get_event_loop" in l]
        event_loop_files.append((short(fp), lines))
    if "asyncio.run" in content:
        asyncio_run_files.append(short(fp))

print("  Files using get_event_loop (BROKEN on Win 3.11):")
for fp, lines in event_loop_files:
    print("    " + fp + " lines " + str(lines))
print("  Files using asyncio.run (CORRECT): " + str(len(asyncio_run_files)))

# ================================================================
# 3. ALL hardcoded alert IDs
# ================================================================
print("\n[3/10] Hardcoded alert ID patterns")
print("-" * 50)
alert_patterns = {
    "SIM-": re.compile(r'SIM-[A-Z0-9-]+'),
    "ALERT-": re.compile(r'ALERT-\d+'),
    "DEMO-": re.compile(r'DEMO-[A-Z0-9-]+'),
    "SYN-": re.compile(r'SYN-[A-Z0-9-]+'),
}

# Backend
print("  Backend .py files:")
for prefix, pattern in alert_patterns.items():
    files_with = set()
    for fp, content in walk_py(backend):
        if pattern.search(content):
            files_with.add(short(fp))
    if files_with:
        print("    " + prefix + "* in " + str(len(files_with)) + " files: " + str(sorted(files_with)[:5]))

# Frontend
print("  Frontend .ts/.tsx files:")
for prefix, pattern in alert_patterns.items():
    files_with = set()
    for fp, content in walk_ts(frontend):
        if pattern.search(content):
            files_with.add(short(fp))
    if files_with:
        print("    " + prefix + "* in " + str(len(files_with)) + " files: " + str(sorted(files_with)[:5]))

# E2E tests specifically
print("  E2E test alert ID regex:")
for fp, content in walk_ts(os.path.join(frontend, "tests")):
    regexes = re.findall(r'/[^/]*(?:SIM|ALERT|DEMO)[^/]*/[gi]*', content)
    if regexes:
        print("    " + short(fp) + ": " + str(set(regexes)))

# ================================================================
# 4. ALL bare except blocks
# ================================================================
print("\n[4/10] Exception handling analysis")
print("-" * 50)
bare_except = 0
except_pass = 0
except_log = 0
total_except = 0
for fp, content in walk_py(backend):
    lines = content.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("except") and ":" in stripped:
            total_except += 1
            if stripped == "except:" or stripped == "except Exception:":
                bare_except += 1
            # Check next non-empty line
            for j in range(i+1, min(i+3, len(lines))):
                next_line = lines[j].strip()
                if next_line:
                    if next_line == "pass":
                        except_pass += 1
                    elif "log" in next_line or "print" in next_line or "warning" in next_line:
                        except_log += 1
                    break

print("  Total except blocks: " + str(total_except))
print("  Bare except/except Exception: " + str(bare_except))
print("  except → pass (silent): " + str(except_pass))
print("  except → log/print: " + str(except_log))

# ================================================================
# 5. TODO/FIXME/HACK markers
# ================================================================
print("\n[5/10] TODO/FIXME/HACK markers")
print("-" * 50)
markers = defaultdict(list)
for fp, content in walk_py(backend):
    for i, line in enumerate(content.split("\n")):
        for marker in ["TODO", "FIXME", "HACK", "XXX", "WORKAROUND"]:
            if marker in line.upper() and not line.strip().startswith('"""'):
                markers[marker].append(short(fp) + ":L" + str(i+1))

for marker, locations in sorted(markers.items()):
    print("  " + marker + ": " + str(len(locations)))
    for loc in locations[:3]:
        print("    " + loc)

# ================================================================
# 6. Functions with no callers (potential dead code)
# ================================================================
print("\n[6/10] Potential dead code (functions with 0 callers)")
print("-" * 50)
# Get all functions in app/
app_functions = conn.execute(
    "SELECT qualified_name, name, file_path, line_start FROM nodes "
    "WHERE kind = 'Function' "
    "AND file_path LIKE '%app%' "
    "AND name NOT LIKE '__%' "
    "AND name NOT LIKE 'test_%' "
    "AND file_path NOT LIKE '%test_%' "
    "ORDER BY file_path, line_start"
).fetchall()

dead_functions = []
for fn in app_functions:
    callers = conn.execute(
        "SELECT count(*) AS n FROM edges "
        "WHERE target_qualified = ? AND kind = 'CALLS'",
        (fn["qualified_name"],)
    ).fetchone()
    if callers["n"] == 0:
        # Check if it's a route handler (decorated)
        dead_functions.append((short(fn["file_path"]), fn["name"], fn["line_start"]))

print("  Functions with 0 callers: " + str(len(dead_functions)))
# Show first 15
for fp, name, line in dead_functions[:15]:
    print("    " + fp + ":L" + str(line) + " " + name)
if len(dead_functions) > 15:
    print("    ... and " + str(len(dead_functions) - 15) + " more")

# ================================================================
# 7. Frontend-backend contract: what alert fields does frontend expect?
# ================================================================
print("\n[7/10] Frontend alert field expectations")
print("-" * 50)
alert_fields_used = set()
for fp, content in walk_ts(frontend):
    # Find property accesses like alert.severity, alert.id, etc.
    field_matches = re.findall(r'alert(?:_?\w*)?\.(\w+)', content)
    alert_fields_used.update(field_matches)

# What does the queue API return?
print("  Frontend uses these alert fields: " + str(sorted(alert_fields_used)[:20]))

# Check what the queue endpoint returns
queue_fields = set()
triage_path = os.path.join("backend", "app", "routers", "triage.py")
if os.path.exists(triage_path):
    with open(triage_path, "r") as f:
        content = f.read()
    # Find dict keys in the queue response
    key_matches = re.findall(r'"(\w+)":\s*(?:alert|record)', content)
    queue_fields.update(key_matches)
    # Also find explicit key assignments
    key_matches2 = re.findall(r'"(\w+)":\s*\w+\.get\(', content)
    queue_fields.update(key_matches2)
print("  Queue API returns these fields: " + str(sorted(queue_fields)))

# ================================================================
# 8. Import chain depth from critical files
# ================================================================
print("\n[8/10] Import chains from critical files")
print("-" * 50)
for target in ["state_manager", "graph_schema", "triage"]:
    importers = conn.execute(
        "SELECT DISTINCT file_path FROM edges "
        "WHERE target_qualified LIKE '%" + target + "%' "
        "AND kind = 'IMPORTS_FROM' "
        "AND file_path NOT LIKE '%" + target + "%'"
    ).fetchall()
    files = [short(i["file_path"]) for i in importers]
    print("  " + target + " imported by " + str(len(files)) + " files")
    for f in files[:5]:
        print("    " + f)

# ================================================================
# 9. Files with most outgoing edges (complexity hotspots)
# ================================================================
print("\n[9/10] Complexity hotspots (most outgoing CALLS edges)")
print("-" * 50)
hotspots = conn.execute(
    "SELECT file_path, count(*) AS n FROM edges "
    "WHERE kind = 'CALLS' "
    "GROUP BY file_path ORDER BY n DESC LIMIT 10"
).fetchall()
for h in hotspots:
    print("  " + short(h["file_path"]) + ": " + str(h["n"]) + " calls")

# ================================================================
# 10. Regression risk: what changed recently but has no test?
# ================================================================
print("\n[10/10] Files with graph_schema/state_manager in call chain but no test coverage")
print("-" * 50)
# Files that depend on state_manager or graph_schema
dependent_files = conn.execute(
    "SELECT DISTINCT file_path FROM edges "
    "WHERE (target_qualified LIKE '%state_manager%' "
    "    OR target_qualified LIKE '%graph_schema%') "
    "AND kind IN ('CALLS', 'IMPORTS_FROM') "
    "AND file_path NOT LIKE '%test_%' "
    "AND file_path NOT LIKE '%conftest%'"
).fetchall()

# Check which have corresponding test files
for df in dependent_files:
    fp = df["file_path"].replace("\\", "/")
    basename = fp.split("/")[-1].replace(".py", "")
    test_name = "test_" + basename
    has_test = conn.execute(
        "SELECT count(*) AS n FROM nodes WHERE kind = 'File' "
        "AND file_path LIKE '%" + test_name + "%'"
    ).fetchone()
    if has_test["n"] == 0:
        print("  NO TEST: " + short(fp))

conn.close()

# ================================================================
# SUMMARY STATISTICS
# ================================================================
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("""
Backend tests:   621 passed, 1 failed, 3 skipped
E2E tests:       103 passed, 38 failed, 2 skipped  
Stress tests:    19 passed, 2 deselected
Contracts:       69/69

The 38 E2E failures have 3 root causes:
  28: Alert ID prefix mismatch (DEMO- vs SIM-/ALERT-)
   5: ShadowDecision data missing
   5: Data gaps (breakdown, weekly, chain summary)

The 1 backend failure:
   1: ShadowDecision data missing (analyst_benchmarking)

Total test regression from start of session:
  Backend: 570 → 621 (+51, but different composition)
  E2E: 120/121 → 103/143 (REGRESSION: -17 net, +22 new tests added)
""")
print("=" * 70)
print("DEEP AUDIT COMPLETE")
print("=" * 70)
