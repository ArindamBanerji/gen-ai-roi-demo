"""Query code-review-graph SQLite -- fixed for actual schema."""
import sqlite3
import os

db_path = os.path.join(".code-review-graph", "graph.db")
if not os.path.exists(db_path):
    print("ERROR: " + db_path + " not found")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
SEP = os.sep

def short(path):
    if not path:
        return ""
    return path.split(SEP)[-1]

def short_qual(qn):
    if not qn:
        return ""
    return qn.split("::")[-1]

print("=" * 70)
print("BACKLOG-069 CODE REVIEW")
print("=" * 70)

# STEP 1: StateManager methods and their callers
print("\nSTEP 1: StateManager method callers")
print("-" * 50)
methods = [
    "soft_reset", "hard_reset", "clear_session_decisions",
    "delete_session_decisions", "_verify_deletion_safety"
]
for method in methods:
    nodes = conn.execute(
        "SELECT qualified_name, file_path, line_start FROM nodes "
        "WHERE name = ? AND file_path LIKE '%state_manager%'", (method,)
    ).fetchall()
    if not nodes:
        print("  " + method + ": NOT FOUND in state_manager.py")
        continue
    for n in nodes:
        qn = n["qualified_name"]
        print("\n  " + method + " (L" + str(n["line_start"]) + ")")
        # Try all edge kinds pointing to this method
        callers = conn.execute(
            "SELECT source_qualified, file_path, line, kind FROM edges "
            "WHERE target_qualified = ?", (qn,)
        ).fetchall()
        if callers:
            for c in callers:
                print("    <- [" + c["kind"] + "] " +
                      short_qual(c["source_qualified"]) +
                      " (" + short(c["file_path"]) + ":L" + str(c["line"]) + ")")
        else:
            print("    (no incoming edges found)")

# STEP 2: seed_neo4j references
print("\n" + "=" * 70)
print("STEP 2: seed_neo4j references")
print("-" * 50)
refs = conn.execute(
    "SELECT name, file_path, kind, line_start FROM nodes "
    "WHERE file_path LIKE '%seed_neo4j%' ORDER BY file_path"
).fetchall()
for r in refs:
    print("  " + short(r["file_path"]) + ":L" + str(r["line_start"]) +
          " " + r["name"] + " (" + r["kind"] + ")")

print("\n  Edges pointing TO seed_neo4j:")
imports = conn.execute(
    "SELECT DISTINCT source_qualified, file_path, kind, line FROM edges "
    "WHERE target_qualified LIKE '%seed_neo4j%' ORDER BY file_path"
).fetchall()
if imports:
    for i in imports:
        print("    " + short(i["file_path"]) + ":L" + str(i["line"]) +
              " [" + i["kind"] + "] " + short_qual(i["source_qualified"]))
else:
    print("    (none found)")

# STEP 3: Functions in state_manager.py
print("\n" + "=" * 70)
print("STEP 3: Functions in state_manager.py")
print("-" * 50)
sm = conn.execute(
    "SELECT name, kind, line_start, line_end, parent_name FROM nodes "
    "WHERE file_path LIKE '%state_manager%' ORDER BY line_start"
).fetchall()
for n in sm:
    parent = " (" + n["parent_name"] + ")" if n["parent_name"] else ""
    print("  L" + str(n["line_start"]) + "-" + str(n["line_end"]) +
          ": " + n["name"] + parent + " [" + n["kind"] + "]")

# STEP 4: Files depending on state_manager.py
print("\n" + "=" * 70)
print("STEP 4: Files depending on state_manager.py")
print("-" * 50)
deps = conn.execute(
    "SELECT DISTINCT file_path FROM edges "
    "WHERE target_qualified LIKE '%state_manager%' "
    "AND file_path NOT LIKE '%state_manager%' "
    "ORDER BY file_path"
).fetchall()
for d in deps:
    print("  " + short(d["file_path"]))

# STEP 5: Edge kind distribution
print("\n" + "=" * 70)
print("STEP 5: Edge kinds")
print("-" * 50)
kinds = conn.execute(
    "SELECT kind, count(*) as cnt FROM edges GROUP BY kind ORDER BY cnt DESC"
).fetchall()
for k in kinds:
    print("  " + k["kind"] + ": " + str(k["cnt"]))

# STEP 6: What state_manager.py calls outward
print("\n" + "=" * 70)
print("STEP 6: state_manager.py outgoing calls")
print("-" * 50)
outgoing = conn.execute(
    "SELECT source_qualified, target_qualified, kind, line FROM edges "
    "WHERE file_path LIKE '%state_manager%' AND kind = 'calls' "
    "ORDER BY line"
).fetchall()
for o in outgoing:
    src = short_qual(o["source_qualified"])
    tgt = short_qual(o["target_qualified"])
    print("  L" + str(o["line"]) + ": " + src + " -> " + tgt)

conn.close()
print("\n" + "=" * 70)
print("DONE")
