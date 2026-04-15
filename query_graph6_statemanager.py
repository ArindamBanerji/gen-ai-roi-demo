"""Query 6: How to construct StateManager correctly.

The stress test failed because StateManager.__init__() needs 4 args:
  self, audit_store, neo4j_service, domain_config

Find:
1. StateManager.__init__ signature
2. How other tests construct StateManager
3. How routers construct StateManager
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

print("=" * 60)
print("QUERY 6: StateManager constructor")
print("=" * 60)

# 1. StateManager.__init__ — where is it, what params?
print("\n1. StateManager.__init__ definition:")
print("-" * 50)
init_nodes = conn.execute(
    "SELECT name, file_path, line_start, line_end, params FROM nodes "
    "WHERE name = '__init__' AND parent_name = 'StateManager'"
).fetchall()
for n in init_nodes:
    print("  " + short(n["file_path"]) + ":L" + str(n["line_start"]) +
          "-" + str(n["line_end"]))
    print("  params: " + str(n["params"]))

# 2. Who calls StateManager() constructor?
print("\n2. All calls to StateManager():")
print("-" * 50)
sm_calls = conn.execute(
    "SELECT source_qualified, file_path, line FROM edges "
    "WHERE target_qualified LIKE '%StateManager%' "
    "AND kind = 'CALLS' "
    "ORDER BY file_path, line"
).fetchall()
for c in sm_calls:
    print("  " + short(c["file_path"]) + ":L" + str(c["line"]) +
          " " + short_qual(c["source_qualified"]))

# 3. How do TEST files construct StateManager?
print("\n3. Test files that reference StateManager:")
print("-" * 50)
test_refs = conn.execute(
    "SELECT source_qualified, file_path, line, kind FROM edges "
    "WHERE target_qualified LIKE '%StateManager%' "
    "AND file_path LIKE '%test_%' "
    "ORDER BY file_path, line"
).fetchall()
for t in test_refs:
    print("  " + short(t["file_path"]) + ":L" + str(t["line"]) +
          " [" + t["kind"] + "] " + short_qual(t["source_qualified"]))

# 4. What does StateManager.__init__ call?
print("\n4. StateManager.__init__ outgoing calls:")
print("-" * 50)
init_qn = None
for n in init_nodes:
    if "services" in str(n["file_path"]):
        init_qn = conn.execute(
            "SELECT qualified_name FROM nodes "
            "WHERE name = '__init__' AND parent_name = 'StateManager' "
            "AND file_path LIKE '%services%state_manager%'"
        ).fetchone()
        if init_qn:
            init_qn = init_qn["qualified_name"]
if init_qn:
    init_calls = conn.execute(
        "SELECT target_qualified, line FROM edges "
        "WHERE source_qualified = ? AND kind = 'CALLS' ORDER BY line",
        (init_qn,)
    ).fetchall()
    for c in init_calls:
        print("  L" + str(c["line"]) + " -> " + short_qual(c["target_qualified"]))

# 5. How do routers construct StateManager? (actual usage pattern)
print("\n5. Router files that call StateManager:")
print("-" * 50)
router_refs = conn.execute(
    "SELECT source_qualified, file_path, line FROM edges "
    "WHERE target_qualified LIKE '%StateManager%' "
    "AND kind = 'CALLS' "
    "AND file_path LIKE '%routers%' "
    "ORDER BY file_path, line"
).fetchall()
for r in router_refs:
    print("  " + short(r["file_path"]) + ":L" + str(r["line"]) +
          " " + short_qual(r["source_qualified"]))

conn.close()
print("\n" + "=" * 60)
print("DONE — use params + router pattern to fix stress test")
print("=" * 60)
