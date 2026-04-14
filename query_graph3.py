"""Query 3: Deep-dive on the three findings from query_graph2.py.
Finding 1: metrics.py calls seed_neo4j directly (bypass)
Finding 2: Two state_manager.py files
Finding 3: seed_neo4j.py unguarded
"""
import sqlite3
import os

db_path = os.path.join(".code-review-graph", "graph.db")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
SEP = os.sep

def short(path):
    if not path:
        return ""
    parts = path.replace("\\", "/").split("/")
    # Return last 3 path segments for context
    return "/".join(parts[-3:]) if len(parts) >= 3 else path

def short_qual(qn):
    if not qn:
        return ""
    return qn.split("::")[-1]

print("=" * 70)
print("BACKLOG-069 DEEP DIVE — Three Critical Findings")
print("=" * 70)

# ================================================================
# FINDING 1: metrics.py — what functions call seed_neo4j?
# ================================================================
print("\n" + "=" * 70)
print("FINDING 1: metrics.py seed_neo4j calls")
print("=" * 70)

# All functions in metrics.py
print("\n  All functions in metrics.py:")
metrics_fns = conn.execute(
    "SELECT name, kind, line_start, line_end, parent_name FROM nodes "
    "WHERE file_path LIKE '%routers%metrics.py' AND kind = 'Function' "
    "ORDER BY line_start"
).fetchall()
for f in metrics_fns:
    parent = " (" + f["parent_name"] + ")" if f["parent_name"] else ""
    print("    L" + str(f["line_start"]) + "-" + str(f["line_end"]) +
          ": " + f["name"] + parent)

# Edges FROM metrics.py TO seed_neo4j
print("\n  metrics.py -> seed_neo4j edges:")
m2s = conn.execute(
    "SELECT source_qualified, target_qualified, kind, line FROM edges "
    "WHERE file_path LIKE '%routers%metrics.py' "
    "AND target_qualified LIKE '%seed_neo4j%' "
    "ORDER BY line"
).fetchall()
for e in m2s:
    print("    L" + str(e["line"]) + " [" + e["kind"] + "] " +
          short_qual(e["source_qualified"]) + " -> " +
          short_qual(e["target_qualified"]))

# Which function in metrics.py contains the seed_neo4j call?
print("\n  Functions near seed_neo4j call sites:")
for e in m2s:
    if e["kind"] == "CALLS":
        line = e["line"]
        containing_fn = conn.execute(
            "SELECT name, line_start, line_end FROM nodes "
            "WHERE file_path LIKE '%routers%metrics.py' "
            "AND kind = 'Function' "
            "AND line_start <= ? AND line_end >= ? "
            "ORDER BY line_start DESC LIMIT 1", (line, line)
        ).fetchone()
        if containing_fn:
            print("    seed_neo4j called at L" + str(line) +
                  " inside: " + containing_fn["name"] +
                  " (L" + str(containing_fn["line_start"]) + "-" +
                  str(containing_fn["line_end"]) + ")")

# What calls those metrics.py functions?
print("\n  HTTP endpoints that reach seed_neo4j via metrics.py:")
for e in m2s:
    if e["kind"] == "CALLS":
        src_fn = e["source_qualified"]
        callers = conn.execute(
            "SELECT source_qualified, file_path, line, kind FROM edges "
            "WHERE target_qualified = ? AND kind = 'CALLS'", (src_fn,)
        ).fetchall()
        for c in callers:
            print("    " + short_qual(c["source_qualified"]) +
                  " (" + short(c["file_path"]) + ":L" + str(c["line"]) + ")")
        if not callers:
            print("    (no callers — likely a direct route handler)")

# ================================================================
# FINDING 2: Two state_manager.py files — is core/ safe?
# ================================================================
print("\n" + "=" * 70)
print("FINDING 2: app/core/state_manager.py (DemoStateManager)")
print("=" * 70)

# All functions in core/state_manager.py
print("\n  Functions in core/state_manager.py:")
core_fns = conn.execute(
    "SELECT name, kind, line_start, line_end, parent_name FROM nodes "
    "WHERE file_path LIKE '%core%state_manager%' AND kind = 'Function' "
    "ORDER BY line_start"
).fetchall()
for f in core_fns:
    parent = " (" + f["parent_name"] + ")" if f["parent_name"] else ""
    print("    L" + str(f["line_start"]) + "-" + str(f["line_end"]) +
          ": " + f["name"] + parent)

# What does DemoStateManager call?
print("\n  DemoStateManager outgoing calls:")
demo_calls = conn.execute(
    "SELECT source_qualified, target_qualified, kind, line FROM edges "
    "WHERE file_path LIKE '%core%state_manager%' AND kind = 'CALLS' "
    "ORDER BY line"
).fetchall()
for c in demo_calls:
    print("    L" + str(c["line"]) + ": " + short_qual(c["source_qualified"]) +
          " -> " + short_qual(c["target_qualified"]))
if not demo_calls:
    print("    (no outgoing calls — likely just orchestrates registered handlers)")

# Who calls DemoStateManager methods?
print("\n  Callers of DemoStateManager methods:")
demo_methods = conn.execute(
    "SELECT qualified_name, name FROM nodes "
    "WHERE file_path LIKE '%core%state_manager%' AND kind = 'Function'"
).fetchall()
for dm in demo_methods:
    callers = conn.execute(
        "SELECT source_qualified, file_path, line FROM edges "
        "WHERE target_qualified = ? AND kind = 'CALLS'", (dm["qualified_name"],)
    ).fetchall()
    for c in callers:
        print("    " + dm["name"] + " <- " +
              short_qual(c["source_qualified"]) +
              " (" + short(c["file_path"]) + ":L" + str(c["line"]) + ")")

# ================================================================
# FINDING 3: ALL files that could destroy Decision data
# ================================================================
print("\n" + "=" * 70)
print("FINDING 3: All files with edges to Decision-related functions")
print("=" * 70)

# Find any node named something with "Decision" + "delete" or "remove"
print("\n  Nodes with 'delete' or 'remove' + 'decision' in name:")
danger_nodes = conn.execute(
    "SELECT name, file_path, kind, line_start FROM nodes "
    "WHERE (LOWER(name) LIKE '%delete%decision%' "
    "   OR LOWER(name) LIKE '%remove%decision%' "
    "   OR LOWER(name) LIKE '%clear%decision%' "
    "   OR LOWER(name) LIKE '%wipe%decision%' "
    "   OR LOWER(name) LIKE '%decision%delete%' "
    "   OR LOWER(name) LIKE '%decision%clear%') "
    "ORDER BY file_path"
).fetchall()
for n in danger_nodes:
    print("    " + short(n["file_path"]) + ":L" + str(n["line_start"]) +
          " " + n["name"] + " [" + n["kind"] + "]")
if not danger_nodes:
    print("    (none found by name — destructive ops may be inline Cypher)")

# ================================================================
# BONUS: Full call chain from admin.py to StateManager
# ================================================================
print("\n" + "=" * 70)
print("BONUS: admin.py -> StateManager call chain")
print("=" * 70)

admin_fns = conn.execute(
    "SELECT qualified_name, name, line_start FROM nodes "
    "WHERE file_path LIKE '%routers%admin.py' AND kind = 'Function' "
    "ORDER BY line_start"
).fetchall()
for af in admin_fns:
    print("\n  " + af["name"] + " (L" + str(af["line_start"]) + "):")
    # What does this admin function call?
    admin_calls = conn.execute(
        "SELECT target_qualified, line FROM edges "
        "WHERE source_qualified = ? AND kind = 'CALLS' "
        "ORDER BY line", (af["qualified_name"],)
    ).fetchall()
    for ac in admin_calls:
        tgt = short_qual(ac["target_qualified"])
        print("    L" + str(ac["line"]) + " -> " + tgt)
        # One more level: what does THAT function call?
        deeper = conn.execute(
            "SELECT target_qualified, line FROM edges "
            "WHERE source_qualified = ? AND kind = 'CALLS' "
            "ORDER BY line", (ac["target_qualified"],)
        ).fetchall()
        for d in deeper:
            print("      L" + str(d["line"]) + " -> " + short_qual(d["target_qualified"]))

# ================================================================
# BONUS: simulation.py -> StateManager call chain
# ================================================================
print("\n" + "=" * 70)
print("BONUS: simulation.py -> StateManager call chain")
print("=" * 70)

sim_to_sm = conn.execute(
    "SELECT source_qualified, target_qualified, line FROM edges "
    "WHERE file_path LIKE '%routers%simulation.py' "
    "AND target_qualified LIKE '%state_manager%' "
    "AND kind = 'CALLS' ORDER BY line"
).fetchall()
for s in sim_to_sm:
    print("  L" + str(s["line"]) + ": " +
          short_qual(s["source_qualified"]) + " -> " +
          short_qual(s["target_qualified"]))
if not sim_to_sm:
    # Broader: what does simulation.py call?
    print("  No direct state_manager calls. All simulation.py calls:")
    sim_calls = conn.execute(
        "SELECT source_qualified, target_qualified, line FROM edges "
        "WHERE file_path LIKE '%routers%simulation.py' AND kind = 'CALLS' "
        "ORDER BY line"
    ).fetchall()
    for s in sim_calls:
        tgt = short_qual(s["target_qualified"])
        if "reset" in tgt.lower() or "state" in tgt.lower() or "manager" in tgt.lower():
            print("  * L" + str(s["line"]) + ": " +
                  short_qual(s["source_qualified"]) + " -> " + tgt)

conn.close()
print("\n" + "=" * 70)
print("DONE — paste output to Claude chat for analysis")
print("=" * 70)
