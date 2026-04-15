"""Query 7: graph_schema.py — all interactions with the codebase.

Checks:
1. Who imports graph_schema?
2. What does graph_schema import?
3. Who calls verify_graph/seed_graph?
4. Does graph_schema call any destructive functions outside itself?
5. Is graph_schema in ALLOWED_FILES for static analysis?
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
print("QUERY 7: graph_schema.py interactions")
print("=" * 60)

# 1. All functions in graph_schema.py
print("\n1. Functions in graph_schema.py:")
print("-" * 50)
gs_fns = conn.execute(
    "SELECT name, kind, line_start, line_end, parent_name, params FROM nodes "
    "WHERE file_path LIKE '%graph_schema%' AND kind = 'Function' "
    "ORDER BY line_start"
).fetchall()
for f in gs_fns:
    parent = " (" + f["parent_name"] + ")" if f["parent_name"] else ""
    params = " " + f["params"] if f["params"] else ""
    print("  L" + str(f["line_start"]) + "-" + str(f["line_end"]) +
          ": " + f["name"] + parent + params)

# 2. Who imports from graph_schema?
print("\n2. Files that import from graph_schema:")
print("-" * 50)
importers = conn.execute(
    "SELECT DISTINCT source_qualified, file_path, line, kind FROM edges "
    "WHERE target_qualified LIKE '%graph_schema%' "
    "AND kind = 'IMPORTS_FROM' "
    "AND file_path NOT LIKE '%graph_schema%' "
    "ORDER BY file_path"
).fetchall()
for i in importers:
    print("  " + short(i["file_path"]) + ":L" + str(i["line"]) +
          " " + short_qual(i["source_qualified"]))
if not importers:
    print("  (none found)")

# 3. Who calls verify_graph or seed_graph?
print("\n3. Callers of verify_graph/seed_graph:")
print("-" * 50)
for fn_name in ["verify_graph", "seed_graph", "_S", "_get_client", "_get_serializer"]:
    callers = conn.execute(
        "SELECT source_qualified, file_path, line FROM edges "
        "WHERE target_qualified LIKE '%" + fn_name + "%' "
        "AND kind = 'CALLS' "
        "AND file_path NOT LIKE '%graph_schema%' "
        "ORDER BY file_path"
    ).fetchall()
    if callers:
        for c in callers:
            print("  " + fn_name + " <- " + short(c["file_path"]) +
                  ":L" + str(c["line"]) + " " +
                  short_qual(c["source_qualified"]))

# 4. What does graph_schema.py import?
print("\n4. graph_schema.py imports:")
print("-" * 50)
gs_imports = conn.execute(
    "SELECT target_qualified, line, kind FROM edges "
    "WHERE file_path LIKE '%graph_schema%' "
    "AND kind = 'IMPORTS_FROM' "
    "ORDER BY line"
).fetchall()
for i in gs_imports:
    print("  L" + str(i["line"]) + " " + short_qual(i["target_qualified"]))

# 5. What does graph_schema.py call externally?
print("\n5. graph_schema.py external calls:")
print("-" * 50)
gs_ext_calls = conn.execute(
    "SELECT source_qualified, target_qualified, line FROM edges "
    "WHERE file_path LIKE '%graph_schema%' "
    "AND kind = 'CALLS' "
    "AND target_qualified NOT LIKE '%graph_schema%' "
    "ORDER BY line"
).fetchall()
for c in gs_ext_calls:
    tgt = short_qual(c["target_qualified"])
    src = short_qual(c["source_qualified"])
    print("  L" + str(c["line"]) + ": " + src + " -> " + tgt)

# 6. Does conftest.py reference graph_schema?
print("\n6. conftest.py references to graph_schema:")
print("-" * 50)
conftest_refs = conn.execute(
    "SELECT source_qualified, target_qualified, line, kind FROM edges "
    "WHERE file_path LIKE '%conftest%' "
    "AND target_qualified LIKE '%graph_schema%' "
    "ORDER BY line"
).fetchall()
for r in conftest_refs:
    print("  L" + str(r["line"]) + " [" + r["kind"] + "] " +
          short_qual(r["source_qualified"]) + " -> " +
          short_qual(r["target_qualified"]))
if not conftest_refs:
    print("  (none found)")

# 7. Does test_no_destructive mention graph_schema in ALLOWED_FILES?
print("\n7. test_no_destructive references to graph_schema:")
print("-" * 50)
destr_refs = conn.execute(
    "SELECT source_qualified, target_qualified, line, kind FROM edges "
    "WHERE file_path LIKE '%test_no_destructive%' "
    "AND target_qualified LIKE '%graph_schema%' "
    "ORDER BY line"
).fetchall()
for r in destr_refs:
    print("  L" + str(r["line"]) + " [" + r["kind"] + "] " +
          short_qual(r["source_qualified"]))
if not destr_refs:
    print("  (none — check if it's in ALLOWED_FILES as a string)")

# 8. Does graph_schema have a __main__ block?
print("\n8. __main__ block check:")
print("-" * 50)
main_nodes = conn.execute(
    "SELECT name, kind, line_start FROM nodes "
    "WHERE file_path LIKE '%graph_schema%' "
    "AND (name = '__main__' OR name LIKE '%main%')"
).fetchall()
if main_nodes:
    for m in main_nodes:
        print("  Found: " + m["name"] + " at L" + str(m["line_start"]))
else:
    print("  NO __main__ BLOCK FOUND — python -m will do nothing!")

# 9. Does graph_schema reference ensure_graph?
print("\n9. ensure_graph references:")
print("-" * 50)
eg_refs = conn.execute(
    "SELECT source_qualified, file_path, line FROM edges "
    "WHERE target_qualified LIKE '%ensure_graph%' "
    "ORDER BY file_path"
).fetchall()
for r in eg_refs:
    print("  " + short(r["file_path"]) + ":L" + str(r["line"]) +
          " " + short_qual(r["source_qualified"]))
if not eg_refs:
    print("  (not found in graph — method may not exist)")

conn.close()
print("\n" + "=" * 60)
print("DONE")
print("=" * 60)
