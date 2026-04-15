"""Query 5: Trace the alert queue pipeline.

Why does GET /api/alerts/queue return 0 alerts when 540 pending alerts exist?
The check_alerts.py showed: 540 pending, but 0 without DECIDED_ON edges.
The queue query likely filters out alerts that already have decisions.

This script traces:
1. What function handles GET /api/alerts/queue?
2. What does that function call?
3. What Cypher query does it run?
4. What other functions create/delete Alert nodes?
5. What creates the DECIDED_ON edges?
6. Does alerts/reset clear DECIDED_ON edges or just set status=pending?
"""
import sqlite3
import os

db_path = os.path.join(".code-review-graph", "graph.db")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

def short(path):
    if not path:
        return ""
    parts = path.replace("\\", "/").split("/")
    return "/".join(parts[-3:]) if len(parts) >= 3 else path

def short_qual(qn):
    if not qn:
        return ""
    return qn.split("::")[-1]

print("=" * 70)
print("QUERY 5: Alert Queue Pipeline Investigation")
print("=" * 70)

# ================================================================
# 1. Functions in triage.py (handles alert endpoints)
# ================================================================
print("\n1. All functions in triage.py:")
print("-" * 50)
triage_fns = conn.execute(
    "SELECT name, kind, line_start, line_end, parent_name FROM nodes "
    "WHERE file_path LIKE '%routers%triage.py' AND kind = 'Function' "
    "ORDER BY line_start"
).fetchall()
for f in triage_fns:
    parent = " (" + f["parent_name"] + ")" if f["parent_name"] else ""
    # Highlight alert-related functions
    marker = " ***" if "alert" in f["name"].lower() or "queue" in f["name"].lower() or "reset" in f["name"].lower() else ""
    print("  L" + str(f["line_start"]) + "-" + str(f["line_end"]) +
          ": " + f["name"] + parent + marker)

# ================================================================
# 2. What does the queue handler call?
# ================================================================
print("\n2. Queue handler outgoing calls:")
print("-" * 50)
# Find functions with 'queue' or 'alert' in name
queue_fns = conn.execute(
    "SELECT qualified_name, name, line_start FROM nodes "
    "WHERE file_path LIKE '%routers%triage.py' AND kind = 'Function' "
    "AND (LOWER(name) LIKE '%queue%' OR LOWER(name) LIKE '%get_alert%')"
).fetchall()
for qf in queue_fns:
    print("\n  " + qf["name"] + " (L" + str(qf["line_start"]) + "):")
    calls = conn.execute(
        "SELECT target_qualified, line FROM edges "
        "WHERE source_qualified = ? AND kind = 'CALLS' ORDER BY line",
        (qf["qualified_name"],)
    ).fetchall()
    for c in calls:
        print("    L" + str(c["line"]) + " -> " + short_qual(c["target_qualified"]))

# ================================================================
# 3. What does the reset handler call?
# ================================================================
print("\n3. Reset handler outgoing calls:")
print("-" * 50)
reset_fns = conn.execute(
    "SELECT qualified_name, name, line_start FROM nodes "
    "WHERE file_path LIKE '%routers%triage.py' AND kind = 'Function' "
    "AND LOWER(name) LIKE '%reset%'"
).fetchall()
for rf in reset_fns:
    print("\n  " + rf["name"] + " (L" + str(rf["line_start"]) + "):")
    calls = conn.execute(
        "SELECT target_qualified, line FROM edges "
        "WHERE source_qualified = ? AND kind = 'CALLS' ORDER BY line",
        (rf["qualified_name"],)
    ).fetchall()
    for c in calls:
        print("    L" + str(c["line"]) + " -> " + short_qual(c["target_qualified"]))

# ================================================================
# 4. Functions that create or manage DECIDED_ON edges
# ================================================================
print("\n4. Functions with 'decided' or 'decision' in name (any file):")
print("-" * 50)
decided_fns = conn.execute(
    "SELECT name, file_path, kind, line_start FROM nodes "
    "WHERE (LOWER(name) LIKE '%decided%' OR LOWER(name) LIKE '%decide%') "
    "AND kind = 'Function' ORDER BY file_path"
).fetchall()
for d in decided_fns:
    print("  " + short(d["file_path"]) + ":L" + str(d["line_start"]) +
          " " + d["name"])

# ================================================================
# 5. What functions does seed_zero_day.py have?
# ================================================================
print("\n5. seed_zero_day.py functions:")
print("-" * 50)
seed_fns = conn.execute(
    "SELECT name, kind, line_start, line_end FROM nodes "
    "WHERE file_path LIKE '%seed_zero_day%' AND kind = 'Function' "
    "ORDER BY line_start"
).fetchall()
for f in seed_fns:
    print("  L" + str(f["line_start"]) + "-" + str(f["line_end"]) +
          ": " + f["name"])

# ================================================================
# 6. What does execute_action call? (creates DECIDED_ON edges)
# ================================================================
print("\n6. execute_action outgoing calls:")
print("-" * 50)
exec_fns = conn.execute(
    "SELECT qualified_name, name, line_start FROM nodes "
    "WHERE kind = 'Function' AND LOWER(name) LIKE '%execute%action%'"
).fetchall()
for ef in exec_fns:
    print("\n  " + ef["name"] + " (L" + str(ef["line_start"]) + ") in " +
          short(conn.execute(
              "SELECT file_path FROM nodes WHERE qualified_name = ?",
              (ef["qualified_name"],)
          ).fetchone()["file_path"]))
    calls = conn.execute(
        "SELECT target_qualified, line FROM edges "
        "WHERE source_qualified = ? AND kind = 'CALLS' ORDER BY line",
        (ef["qualified_name"],)
    ).fetchall()
    for c in calls:
        print("    L" + str(c["line"]) + " -> " + short_qual(c["target_qualified"]))

# ================================================================
# 7. What does analyze_alert call?
# ================================================================
print("\n7. analyze_alert outgoing calls:")
print("-" * 50)
analyze_fns = conn.execute(
    "SELECT qualified_name, name, line_start FROM nodes "
    "WHERE kind = 'Function' AND LOWER(name) LIKE '%analyze%alert%'"
).fetchall()
for af in analyze_fns:
    print("\n  " + af["name"] + " (L" + str(af["line_start"]) + "):")
    calls = conn.execute(
        "SELECT target_qualified, line FROM edges "
        "WHERE source_qualified = ? AND kind = 'CALLS' ORDER BY line",
        (af["qualified_name"],)
    ).fetchall()
    for c in calls:
        print("    L" + str(c["line"]) + " -> " + short_qual(c["target_qualified"]))

# ================================================================
# 8. All functions that reference Alert nodes (cross-file)
# ================================================================
print("\n8. Functions containing 'Alert' in any file (potential Alert mutators):")
print("-" * 50)
alert_fns = conn.execute(
    "SELECT name, file_path, line_start FROM nodes "
    "WHERE kind = 'Function' "
    "AND (LOWER(name) LIKE '%alert%' OR LOWER(name) LIKE '%seed_alert%') "
    "AND file_path NOT LIKE '%test_%' "
    "ORDER BY file_path, line_start"
).fetchall()
for a in alert_fns:
    print("  " + short(a["file_path"]) + ":L" + str(a["line_start"]) +
          " " + a["name"])

# ================================================================
# 9. What creates Alert nodes? (seed scripts)
# ================================================================
print("\n9. Files that could create Alert nodes:")
print("-" * 50)
# Look for files with 'seed' or 'bootstrap' in the name
seed_files = conn.execute(
    "SELECT DISTINCT file_path FROM nodes "
    "WHERE (file_path LIKE '%seed%' OR file_path LIKE '%bootstrap%') "
    "AND kind = 'File' ORDER BY file_path"
).fetchall()
for s in seed_files:
    print("  " + short(s["file_path"]))

# ================================================================
# 10. Impact: what depends on triage.py queue function?
# ================================================================
print("\n10. Files depending on triage.py:")
print("-" * 50)
triage_deps = conn.execute(
    "SELECT DISTINCT file_path FROM edges "
    "WHERE target_qualified LIKE '%triage%' "
    "AND file_path NOT LIKE '%triage%' "
    "ORDER BY file_path"
).fetchall()
for d in triage_deps:
    print("  " + short(d["file_path"]))

conn.close()
print("\n" + "=" * 70)
print("DONE — paste output for analysis")
print("=" * 70)
