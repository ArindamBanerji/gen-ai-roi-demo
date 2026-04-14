"""Query the code-review-graph SQLite DB directly for BACKLOG-069 verification."""
import sqlite3, os

db_path = os.path.join(".code-review-graph", "graph.db")
if not os.path.exists(db_path):
    print(f"ERROR: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

print("=" * 70)
print("BACKLOG-069 CODE REVIEW — Direct Graph Query")
print("=" * 70)

# 1. What tables exist?
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print(f"\nTables: {tables}")

# 2. Schema of nodes and edges
for t in ["nodes", "edges"]:
    if t in tables:
        cols = conn.execute(f"PRAGMA table_info({t})").fetchall()
        print(f"\n{t} columns: {[c['name'] for c in cols]}")

# 3. Find all nodes referencing StateManager methods
print("\n" + "=" * 70)
print("STEP 1: StateManager method callers")
print("=" * 70)
for method in ["soft_reset", "hard_reset", "clear_session_decisions", "delete_session_decisions", "_verify_deletion_safety"]:
    nodes = conn.execute(
        "SELECT * FROM nodes WHERE name = ? OR name LIKE ?",
        (method, f"%{method}%")
    ).fetchall()
    if nodes:
        for n in nodes:
            print(f"\n  {method} defined in: {dict(n)}")
            # Find callers via edges
            if "id" in [c["name"] for c in conn.execute("PRAGMA table_info(nodes)").fetchall()]:
                callers = conn.execute(
                    "SELECT n2.name, n2.file_path FROM edges e "
                    "JOIN nodes n2 ON e.source_id = n2.id "
                    "WHERE e.target_id = ? AND e.edge_type IN ('calls', 'call')",
                    (n["id"],)
                ).fetchall()
                for c in callers:
                    print(f"    <- called by: {c['name']} in {c['file_path']}")
    else:
        print(f"  {method}: not found in graph")

# 4. Find seed_neo4j references
print("\n" + "=" * 70)
print("STEP 2: seed_neo4j references")
print("=" * 70)
refs = conn.execute(
    "SELECT name, file_path, node_type FROM nodes WHERE name LIKE '%seed_neo4j%' OR file_path LIKE '%seed_neo4j%'"
).fetchall()
for r in refs:
    print(f"  {r['file_path']}: {r['name']} ({r['node_type']})")

# 5. Find imports of seed_neo4j
imports = conn.execute(
    "SELECT DISTINCT n.file_path, n.name FROM edges e "
    "JOIN nodes n ON e.source_id = n.id "
    "JOIN nodes n2 ON e.target_id = n2.id "
    "WHERE n2.file_path LIKE '%seed_neo4j%' AND e.edge_type IN ('imports', 'import')"
).fetchall()
if imports:
    print("\n  Imported by:")
    for i in imports:
        print(f"    {i['file_path']}: {i['name']}")
else:
    print("\n  No import edges found for seed_neo4j")

# 6. Find nodes in state_manager.py
print("\n" + "=" * 70)
print("STEP 3: All functions in state_manager.py")
print("=" * 70)
sm_nodes = conn.execute(
    "SELECT name, node_type, start_line, end_line FROM nodes WHERE file_path LIKE '%state_manager%' ORDER BY start_line"
).fetchall()
for n in sm_nodes:
    print(f"  L{n['start_line']}-{n['end_line']}: {n['name']} ({n['node_type']})")

# 7. Impact radius — what depends on state_manager.py?
print("\n" + "=" * 70)
print("STEP 4: Files that depend on state_manager.py")
print("=" * 70)
sm_ids = [n["id"] for n in conn.execute(
    "SELECT id FROM nodes WHERE file_path LIKE '%state_manager%'"
).fetchall()]
if sm_ids:
    placeholders = ",".join("?" * len(sm_ids))
    dependents = conn.execute(
        f"SELECT DISTINCT n.file_path FROM edges e "
        f"JOIN nodes n ON e.source_id = n.id "
        f"WHERE e.target_id IN ({placeholders})",
        sm_ids
    ).fetchall()
    for d in dependents:
        print(f"  {d['file_path']}")

# 8. All edge types (to understand the schema)
print("\n" + "=" * 70)
print("STEP 5: Edge type distribution")
print("=" * 70)
edge_types = conn.execute(
    "SELECT edge_type, count(*) as cnt FROM edges GROUP BY edge_type ORDER BY cnt DESC"
).fetchall()
for e in edge_types:
    print(f"  {e['edge_type']}: {e['cnt']}")

conn.close()
print("\n" + "=" * 70)
print("DONE")
print("=" * 70)
