"""Prompt 0: Structural map of key SOC copilot source files.
Run from gen-ai-roi-demo-v4-v50/ after 'code-review-graph build'.
Outputs: function inventory, cross-file call graph, and test coverage map
for the critical files Claude needs to understand.
"""
import sqlite3
import os

db_path = os.path.join(".code-review-graph", "graph.db")
if not os.path.exists(db_path):
    print("ERROR: Run 'code-review-graph build' first")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

KEY_FILES = [
    "triage.py",
    "graph_snapshot.py",
    "audit.py",
    "gae_state.py",
    "state_manager.py",
    "simulation.py",
    "soc.py",
    "orchestrator.py",
    "factors.py",
    "config.py",
]

SEPARATOR = "=" * 70

# ── SECTION 1: Function inventory per key file ──────────────────────
print(SEPARATOR)
print("SECTION 1: FUNCTION INVENTORY — KEY SOURCE FILES")
print(SEPARATOR)

for kf in KEY_FILES:
    funcs = conn.execute(
        "SELECT name, kind, line_start, line_end FROM nodes "
        "WHERE file_path LIKE ? AND kind IN ('Function', 'Method', 'Class') "
        "ORDER BY line_start",
        (f"%app%{kf}",)
    ).fetchall()
    if not funcs:
        continue
    # Get actual file path
    fp = conn.execute(
        "SELECT DISTINCT file_path FROM nodes WHERE file_path LIKE ?",
        (f"%app%{kf}",)
    ).fetchall()
    print(f"\n{'─' * 50}")
    for f in fp:
        parts = f["file_path"].replace("\\", "/").split("/")
        print(f"FILE: {'/'.join(parts[-4:])}")
    print(f"  Functions/Methods: {len(funcs)}")
    for fn in funcs:
        size = (fn["line_end"] or 0) - (fn["line_start"] or 0)
        print(f"  L{fn['line_start']:>4}  [{fn['kind']:<8}] {fn['name']} ({size} lines)")

# ── SECTION 2: Cross-file call graph for key files ──────────────────
print(f"\n{SEPARATOR}")
print("SECTION 2: CROSS-FILE CALL GRAPH (who calls what)")
print(SEPARATOR)

for kf in KEY_FILES:
    # Outgoing calls FROM this file to other files
    outgoing = conn.execute(
        "SELECT DISTINCT e.target_qualified, e.line, n.file_path as target_file "
        "FROM edges e "
        "LEFT JOIN nodes n ON e.target_qualified = n.qualified_name "
        "WHERE e.file_path LIKE ? "
        "AND e.kind = 'CALLS' "
        "AND (n.file_path IS NULL OR n.file_path NOT LIKE ?)"
        "ORDER BY e.line",
        (f"%app%{kf}", f"%{kf}")
    ).fetchall()
    if not outgoing:
        continue
    print(f"\n{kf} → calls into:")
    seen = set()
    for o in outgoing:
        target = o["target_qualified"].split("::")[-1] if o["target_qualified"] else "?"
        tf = ""
        if o["target_file"]:
            parts = o["target_file"].replace("\\", "/").split("/")
            tf = parts[-1] if parts else ""
        key = f"{target}|{tf}"
        if key not in seen:
            seen.add(key)
            print(f"  L{o['line']:>4} → {target} ({tf})")

# ── SECTION 3: Scorer usage patterns ────────────────────────────────
print(f"\n{SEPARATOR}")
print("SECTION 3: SCORER USAGE PATTERNS")
print(SEPARATOR)

# Check for scorer.mu (should be ZERO)
mu_refs = conn.execute(
    "SELECT file_path, line FROM edges "
    "WHERE target_qualified LIKE '%scorer%mu%' "
    "OR target_qualified LIKE '%.mu%' "
    "ORDER BY file_path"
).fetchall()
print(f"\nscorer.mu references (MUST BE 0): {len(mu_refs)}")
for m in mu_refs:
    parts = m["file_path"].replace("\\", "/").split("/")
    print(f"  VIOLATION: {'/'.join(parts[-3:])}:L{m['line']}")

# Check for centroids usage
centroid_refs = conn.execute(
    "SELECT file_path, line FROM edges "
    "WHERE target_qualified LIKE '%centroids%' "
    "AND file_path LIKE '%app%' "
    "ORDER BY file_path"
).fetchall()
print(f"\nscorer.centroids references: {len(centroid_refs)}")

# ── SECTION 4: _S() vs $PARAM pattern ──────────────────────────────
print(f"\n{SEPARATOR}")
print("SECTION 4: AGE QUERY PATTERNS")
print(SEPARATOR)

# Look for any $param references (FORBIDDEN)
param_refs = conn.execute(
    "SELECT file_path, line, source_qualified FROM edges "
    "WHERE source_qualified LIKE '%$%' OR target_qualified LIKE '%$param%' "
    "ORDER BY file_path"
).fetchall()
print(f"\n$param references (MUST BE 0): {len(param_refs)}")
for p in param_refs:
    parts = p["file_path"].replace("\\", "/").split("/")
    print(f"  VIOLATION: {'/'.join(parts[-3:])}:L{p['line']}")

# ── SECTION 5: Test coverage map ────────────────────────────────────
print(f"\n{SEPARATOR}")
print("SECTION 5: TEST FILE INVENTORY")
print(SEPARATOR)

test_files = conn.execute(
    "SELECT DISTINCT file_path FROM nodes "
    "WHERE file_path LIKE '%test_%' AND kind = 'Function' "
    "ORDER BY file_path"
).fetchall()

test_counts = {}
for tf in test_files:
    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM nodes "
        "WHERE file_path = ? AND kind = 'Function' AND name LIKE 'test_%'",
        (tf["file_path"],)
    ).fetchone()
    parts = tf["file_path"].replace("\\", "/").split("/")
    short = "/".join(parts[-3:])
    test_counts[short] = count["cnt"]

for path, cnt in sorted(test_counts.items()):
    print(f"  {cnt:>3} tests  {path}")

print(f"\n  Total test functions: {sum(test_counts.values())}")

# ── SECTION 6: Audit chain flow ─────────────────────────────────────
print(f"\n{SEPARATOR}")
print("SECTION 6: AUDIT CHAIN — record_decision / record_outcome callers")
print(SEPARATOR)

for fn_name in ["record_decision", "record_outcome", "verify_chain"]:
    callers = conn.execute(
        "SELECT source_qualified, file_path, line FROM edges "
        "WHERE target_qualified LIKE ? AND kind = 'CALLS' "
        "ORDER BY file_path",
        (f"%{fn_name}%",)
    ).fetchall()
    print(f"\n{fn_name}() called by:")
    for c in callers:
        parts = c["file_path"].replace("\\", "/").split("/")
        short = "/".join(parts[-3:])
        src = c["source_qualified"].split("::")[-1]
        print(f"  {short}:L{c['line']} — {src}")
    if not callers:
        print("  (no callers found)")

# ── SECTION 7: Conservation law wiring ──────────────────────────────
print(f"\n{SEPARATOR}")
print("SECTION 7: CONSERVATION / LEARNING HEALTH WIRING")
print(SEPARATOR)

conservation_fns = [
    "set_conservation_status", "get_conservation_status",
    "LearningHealthMonitor", "compute_eta_override",
    "freeze", "unfreeze", "q_window", "rolling_accuracy"
]
for fn in conservation_fns:
    refs = conn.execute(
        "SELECT file_path, line FROM edges "
        "WHERE (target_qualified LIKE ? OR source_qualified LIKE ?) "
        "AND file_path LIKE '%app%' "
        "ORDER BY file_path",
        (f"%{fn}%", f"%{fn}%")
    ).fetchall()
    count = len(refs)
    print(f"  {fn}: {count} references")
    for r in refs[:3]:  # Show first 3
        parts = r["file_path"].replace("\\", "/").split("/")
        print(f"    {'/'.join(parts[-3:])}:L{r['line']}")
    if count > 3:
        print(f"    ... and {count - 3} more")

# ── SECTION 8: Epistemic state wiring ───────────────────────────────
print(f"\n{SEPARATOR}")
print("SECTION 8: EPISTEMIC STATE WIRING")
print(SEPARATOR)

for fn in ["get_epistemic_state", "_band", "category_counts", "epistemic"]:
    refs = conn.execute(
        "SELECT file_path, line FROM edges "
        "WHERE target_qualified LIKE ? AND file_path LIKE '%app%' "
        "ORDER BY file_path",
        (f"%{fn}%",)
    ).fetchall()
    print(f"  {fn}: {len(refs)} call sites")

# ── SUMMARY ─────────────────────────────────────────────────────────
print(f"\n{SEPARATOR}")
print("PROMPT 0 STRUCTURAL MAP COMPLETE")
print(SEPARATOR)

conn.close()
