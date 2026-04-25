"""Tab content structural analysis via code-review-graph.
Run from gen-ai-roi-demo-v4-v50/ after 'code-review-graph build'.
Shows what each _tabN_content function calls and depends on.
"""
import sqlite3
import os

db_path = os.path.join(".code-review-graph", "graph.db")
if not os.path.exists(db_path):
    print("ERROR: Run 'code-review-graph build' first")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

SEPARATOR = "=" * 70

# ── SECTION 1: Tab content functions — size and location ────────────
print(SEPARATOR)
print("SECTION 1: TAB CONTENT FUNCTIONS")
print(SEPARATOR)

tab_fns = conn.execute(
    "SELECT name, line_start, line_end, file_path FROM nodes "
    "WHERE name LIKE '_tab%_content' AND kind = 'Function' "
    "ORDER BY name"
).fetchall()

for fn in tab_fns:
    size = (fn["line_end"] or 0) - (fn["line_start"] or 0)
    parts = fn["file_path"].replace("\\", "/").split("/")
    print(f"\n  {fn['name']}  L{fn['line_start']}-{fn['line_end']} ({size} lines)")
    print(f"  File: {'/'.join(parts[-3:])}")

# Also find the dispatcher
dispatcher = conn.execute(
    "SELECT name, line_start, line_end FROM nodes "
    "WHERE name = 'get_tab_content' AND kind = 'Function'"
).fetchall()
for d in dispatcher:
    size = (d["line_end"] or 0) - (d["line_start"] or 0)
    print(f"\n  DISPATCHER: {d['name']}  L{d['line_start']}-{d['line_end']} ({size} lines)")

# ── SECTION 2: What each tab function calls ─────────────────────────
print(f"\n{SEPARATOR}")
print("SECTION 2: CALL GRAPH PER TAB")
print(SEPARATOR)

for tab_num in range(1, 6):
    fn_name = f"_tab{tab_num}_content"

    # Get line range for this function
    fn_info = conn.execute(
        "SELECT line_start, line_end, file_path FROM nodes "
        "WHERE name = ? AND kind = 'Function'",
        (fn_name,)
    ).fetchone()

    if not fn_info:
        print(f"\n{'─' * 50}")
        print(f"TAB {tab_num}: {fn_name} — NOT FOUND")
        continue

    print(f"\n{'─' * 50}")
    print(f"TAB {tab_num}: {fn_name} (L{fn_info['line_start']}-{fn_info['line_end']})")
    print(f"{'─' * 50}")

    # Get all calls FROM this function
    calls = conn.execute(
        "SELECT DISTINCT target_qualified, line FROM edges "
        "WHERE file_path = ? "
        "AND line >= ? AND line <= ? "
        "AND kind = 'CALLS' "
        "ORDER BY line",
        (fn_info["file_path"], fn_info["line_start"], fn_info["line_end"])
    ).fetchall()

    # Categorize calls
    data_calls = []    # Calls that fetch data
    compute_calls = [] # Calls that compute/transform
    utility_calls = [] # Python builtins, formatting

    data_keywords = ["get_", "fetch_", "compute_", "count_", "run_query",
                     "build_", "load_", "list_", "read_", "query"]
    utility_keywords = ["dict", "list", "str", "int", "float", "len",
                        "round", "sum", "max", "min", "items", "get",
                        "keys", "values", "append", "join", "format",
                        "isinstance", "hasattr", "getattr", "bool",
                        "sorted", "enumerate", "range", "zip", "any", "all"]

    for c in calls:
        target = c["target_qualified"].split("::")[-1] if c["target_qualified"] else "?"
        if target.lower() in utility_calls:
            utility_calls.append((c["line"], target))
        elif any(kw in target.lower() for kw in data_keywords):
            data_calls.append((c["line"], target))
        elif target.lower() in utility_keywords:
            utility_calls.append((c["line"], target))
        else:
            compute_calls.append((c["line"], target))

    if data_calls:
        print("\n  DATA SOURCES:")
        for line, target in data_calls:
            print(f"    L{line:>4}  {target}")

    if compute_calls:
        print("\n  OTHER CALLS:")
        for line, target in compute_calls:
            print(f"    L{line:>4}  {target}")

    print(f"\n  Total calls: {len(calls)} ({len(data_calls)} data, "
          f"{len(compute_calls)} compute/other, {len(utility_calls)} utility)")

# ── SECTION 3: Tab test coverage ────────────────────────────────────
print(f"\n{SEPARATOR}")
print("SECTION 3: TAB CONTENT TEST COVERAGE")
print(SEPARATOR)

# Find test_tab_content.py
tab_tests = conn.execute(
    "SELECT name, line_start, line_end FROM nodes "
    "WHERE file_path LIKE '%test_tab_content%' "
    "AND kind IN ('Function', 'Method', 'Test') "
    "ORDER BY line_start"
).fetchall()

if tab_tests:
    print(f"\ntest_tab_content.py — {len(tab_tests)} functions:")
    for t in tab_tests:
        size = (t["line_end"] or 0) - (t["line_start"] or 0)
        print(f"  L{t['line_start']:>4}  {t['name']} ({size} lines)")
else:
    print("\n  (test_tab_content.py not found in graph or has no test functions)")

# ── SECTION 4: Helper functions used by tabs ────────────────────────
print(f"\n{SEPARATOR}")
print("SECTION 4: HELPER FUNCTIONS USED BY TABS")
print(SEPARATOR)

helpers = ["_resolve_category", "_factor_kernel_weight", "_get_ps",
           "_get_ls", "_get_snap", "_get_scorer", "_compute_iks_drift",
           "_interp_v2", "_get_snap_t2", "_get_ls_t4", "_get_snap_t4",
           "_SDC", "_compute_iks_snap", "_get_ps_snap"]

for h in helpers:
    info = conn.execute(
        "SELECT line_start, line_end FROM nodes "
        "WHERE name = ? AND kind = 'Function' "
        "AND file_path LIKE '%soc.py'",
        (h,)
    ).fetchone()
    if info:
        size = (info["line_end"] or 0) - (info["line_start"] or 0)
        # Count how many tabs call this helper
        tab_callers = conn.execute(
            "SELECT COUNT(DISTINCT source_qualified) as cnt FROM edges "
            "WHERE target_qualified LIKE ? AND kind = 'CALLS' "
            "AND source_qualified LIKE '%_tab%_content%'",
            (f"%{h}%",)
        ).fetchone()
        tabs_using = tab_callers["cnt"] if tab_callers else 0
        print(f"  {h:<30} L{info['line_start']:>4} ({size:>3} lines)  used by {tabs_using} tabs")

# ── SECTION 5: Epistemic state endpoint ─────────────────────────────
print(f"\n{SEPARATOR}")
print("SECTION 5: EPISTEMIC STATE ENDPOINT")
print(SEPARATOR)

ep_fn = conn.execute(
    "SELECT name, line_start, line_end FROM nodes "
    "WHERE name = 'get_epistemic_state' AND kind = 'Function' "
    "AND file_path LIKE '%soc.py'"
).fetchone()
if ep_fn:
    size = (ep_fn["line_end"] or 0) - (ep_fn["line_start"] or 0)
    print(f"  get_epistemic_state: L{ep_fn['line_start']} ({size} lines)")

    # What it calls
    ep_calls = conn.execute(
        "SELECT target_qualified, line FROM edges "
        "WHERE source_qualified LIKE '%get_epistemic_state%' "
        "AND kind = 'CALLS' ORDER BY line"
    ).fetchall()
    for c in ep_calls:
        target = c["target_qualified"].split("::")[-1] if c["target_qualified"] else "?"
        print(f"    L{c['line']:>4}  → {target}")

# ── SUMMARY ─────────────────────────────────────────────────────────
print(f"\n{SEPARATOR}")
print("TAB CONTENT ANALYSIS COMPLETE")
print(f"To see LIVE tab content, start backend and run:")
print(f"  python scripts/collect_tab_content.py")
print(SEPARATOR)

conn.close()
