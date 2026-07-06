"""Property name audit -- cross-reference Cypher property refs vs actual AGE node properties."""
import asyncio, os, sys, re
from pathlib import Path
from collections import Counter

sys.path.insert(0, ".")
os.environ["GRAPH_BACKEND"] = "age"
from ci_platform.graph import get_graph_client

# --- Step 1: Extract all property references from Cypher in source code ---

def extract_props(prefix, files):
    pattern = re.compile(rf'{prefix}\.(\w+)')
    props = Counter()
    for f in files:
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        for m in pattern.finditer(text):
            props[m.group(1)] += 1
    return props

routers = list(Path("app/routers").glob("*.py"))
services = list(Path("app/services").glob("*.py"))
state = list(Path("app/state").glob("*.py")) if Path("app/state").exists() else []
all_py = routers + services + state

print("=" * 70)
print("STEP 1: Property references in Cypher queries (source code)")
print("=" * 70)

for prefix, label in [("d", "Decision"), ("a", "Alert"), ("sd", "ShadowDecision"), ("ti", "ThreatIntel")]:
    props = extract_props(prefix, all_py)
    if props:
        print(f"\n  {prefix}.* ({label}) -- {len(props)} unique properties:")
        for prop, count in props.most_common():
            print(f"    {prefix}.{prop:30s} referenced {count}x")

# --- Step 2: Actual properties on AGE nodes ---

async def audit_graph():
    c = get_graph_client()

    print("\n" + "=" * 70)
    print("STEP 2: Actual properties on AGE nodes")
    print("=" * 70)

    for label, query in [
        ("Decision (connected)", "MATCH (d:Decision)-[:DECIDED_ON]->() RETURN d LIMIT 10"),
        ("Alert", "MATCH (a:Alert) RETURN a LIMIT 10"),
        ("ShadowDecision", "MATCH (sd:ShadowDecision) RETURN sd LIMIT 5"),
        ("Campaign", "MATCH (c:Campaign) RETURN c LIMIT 5"),
        ("ThreatIntel", "MATCH (ti:ThreatIntel) RETURN ti LIMIT 5"),
    ]:
        try:
            rows = await c.run_query(query)
            all_keys = set()
            for r in rows:
                val = list(r.values())[0] if r else {}
                if isinstance(val, dict):
                    all_keys.update(val.keys())
            print(f"\n  {label}: {sorted(all_keys) if all_keys else 'NO NODES FOUND'}")
        except Exception as e:
            print(f"\n  {label}: ERROR -- {e}")

    # --- Step 3: Cross-reference ---

    print("\n" + "=" * 70)
    print("STEP 3: Mismatches -- properties referenced in code but NOT on nodes")
    print("=" * 70)

    # Get actual Decision properties
    rows = await c.run_query("MATCH (d:Decision)-[:DECIDED_ON]->() RETURN d LIMIT 20")
    decision_keys = set()
    for r in rows:
        val = list(r.values())[0] if r else {}
        if isinstance(val, dict):
            decision_keys.update(val.keys())

    # Get actual Alert properties
    rows = await c.run_query("MATCH (a:Alert) RETURN a LIMIT 20")
    alert_keys = set()
    for r in rows:
        val = list(r.values())[0] if r else {}
        if isinstance(val, dict):
            alert_keys.update(val.keys())

    code_decision_props = extract_props("d", all_py)
    code_alert_props = extract_props("a", all_py)

    # Filter out non-property refs (Python attrs like d.get, d.items, etc.)
    python_attrs = {"get", "items", "keys", "values", "append", "pop", "update",
                    "copy", "setdefault", "clear", "encode", "decode", "strip",
                    "replace", "split", "join", "lower", "upper", "startswith",
                    "endswith", "format", "isoformat"}

    print("\n  Decision (d.*) -- in code but NOT on any node:")
    mismatches = 0
    for prop in sorted(code_decision_props):
        if prop in python_attrs:
            continue
        if prop not in decision_keys:
            print(f"    WARNING d.{prop:30s} (used {code_decision_props[prop]}x) -- NOT FOUND on Decision nodes")
            mismatches += 1
    if mismatches == 0:
        print("    [OK] All properties match")

    print(f"\n  Alert (a.*) -- in code but NOT on any node:")
    mismatches = 0
    for prop in sorted(code_alert_props):
        if prop in python_attrs:
            continue
        if prop not in alert_keys:
            print(f"    WARNING a.{prop:30s} (used {code_alert_props[prop]}x) -- NOT FOUND on Alert nodes")
            mismatches += 1
    if mismatches == 0:
        print("    [OK] All properties match")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(audit_graph())
