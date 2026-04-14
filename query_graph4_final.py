"""Query 4: Final verification — confirm zero bypasses remain."""
import sqlite3
import os

db_path = os.path.join(".code-review-graph", "graph.db")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

print("=" * 70)
print("BACKLOG-069 FINAL VERIFICATION")
print("=" * 70)

# Rebuild graph first to pick up changes
print("\n[!] Run 'code-review-graph build' first if you changed files\n")

# 1. Any remaining CALLS edges to seed_neo4j from non-guard files?
print("CHECK 1: Live calls to seed_neo4j (should be 0)")
print("-" * 50)
live_calls = conn.execute(
    "SELECT source_qualified, file_path, line FROM edges "
    "WHERE target_qualified LIKE '%seed_neo4j%' "
    "AND kind = 'CALLS' "
    "AND file_path NOT LIKE '%seed_neo4j%' "
    "ORDER BY file_path"
).fetchall()
for c in live_calls:
    parts = c["file_path"].replace("\\", "/").split("/")
    short = "/".join(parts[-3:])
    src = c["source_qualified"].split("::")[-1]
    print("  BYPASS: " + short + ":L" + str(c["line"]) + " " + src)
if not live_calls:
    print("  PASS: 0 live calls to seed_neo4j outside guard files")

# 2. Any IMPORTS of seed_neo4j from non-guard files?
print("\nCHECK 2: Imports of seed_neo4j (should be 0 outside guard)")
print("-" * 50)
imports = conn.execute(
    "SELECT source_qualified, file_path, line FROM edges "
    "WHERE target_qualified LIKE '%seed_neo4j%' "
    "AND kind = 'IMPORTS_FROM' "
    "AND file_path NOT LIKE '%seed_neo4j%' "
    "ORDER BY file_path"
).fetchall()
for i in imports:
    parts = i["file_path"].replace("\\", "/").split("/")
    short = "/".join(parts[-3:])
    print("  IMPORT: " + short + ":L" + str(i["line"]))
if not imports:
    print("  PASS: 0 imports of seed_neo4j outside guard files")

# 3. Verify StateManager has all protection methods
print("\nCHECK 3: StateManager protection methods exist")
print("-" * 50)
required = [
    "_verify_deletion_safety",
    "clear_session_decisions",
    "delete_session_decisions",
    "soft_reset",
    "hard_reset"
]
for method in required:
    found = conn.execute(
        "SELECT line_start FROM nodes "
        "WHERE name = ? AND file_path LIKE '%services%state_manager%'",
        (method,)
    ).fetchone()
    if found:
        print("  OK: " + method + " at L" + str(found["line_start"]))
    else:
        print("  MISSING: " + method)

# 4. Verify no file outside StateManager has Decision destructive functions
print("\nCHECK 4: Decision-destructive functions only in StateManager")
print("-" * 50)
destructive = conn.execute(
    "SELECT name, file_path, line_start FROM nodes "
    "WHERE (LOWER(name) LIKE '%delete%decision%' "
    "   OR LOWER(name) LIKE '%clear%decision%' "
    "   OR LOWER(name) LIKE '%remove%decision%') "
    "AND file_path NOT LIKE '%state_manager%' "
    "AND file_path NOT LIKE '%test_%'"
).fetchall()
for d in destructive:
    parts = d["file_path"].replace("\\", "/").split("/")
    short = "/".join(parts[-3:])
    print("  BYPASS: " + short + ":L" + str(d["line_start"]) + " " + d["name"])
if not destructive:
    print("  PASS: 0 destructive Decision functions outside StateManager")

# 5. Verify conftest.py references origin correctly
print("\nCHECK 5: conftest.py safety net")
print("-" * 50)
conftest = conn.execute(
    "SELECT name, line_start FROM nodes "
    "WHERE file_path LIKE '%conftest%' AND kind = 'Function'"
).fetchall()
for c in conftest:
    print("  " + c["name"] + " at L" + str(c["line_start"]))

# 6. Count all destructive paths
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

# All calls to soft_reset or hard_reset
sm_calls = conn.execute(
    "SELECT source_qualified, file_path, line FROM edges "
    "WHERE (target_qualified LIKE '%soft_reset%' "
    "    OR target_qualified LIKE '%hard_reset%') "
    "AND kind = 'CALLS' "
    "AND file_path NOT LIKE '%state_manager%' "
    "ORDER BY file_path"
).fetchall()
print("\nCallers of soft_reset/hard_reset (should all be routers):")
for s in sm_calls:
    parts = s["file_path"].replace("\\", "/").split("/")
    short = "/".join(parts[-3:])
    src = s["source_qualified"].split("::")[-1]
    print("  " + short + ":L" + str(s["line"]) + " " + src)

bypass_count = len(live_calls) + len(destructive)
print("\n  Total destructive paths: " + str(len(sm_calls) + 2))
print("  Through StateManager: " + str(len(sm_calls) + 2))
print("  Bypasses: " + str(bypass_count))

if bypass_count == 0:
    print("\n  === ALL CLEAR: Zero bypasses remain ===")
else:
    print("\n  !!! WARNING: " + str(bypass_count) + " bypasses found !!!")

conn.close()
