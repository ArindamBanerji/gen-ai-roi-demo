"""
support/setup/seed_zero_day.py — Load zero-day synthetic decisions into AGE.

Usage:
    python support/setup/seed_zero_day.py --dry-run
    python support/setup/seed_zero_day.py --live [--clean] [--file=path]

REQUIRES: GRAPH_BACKEND=age
"""
from __future__ import annotations
import asyncio, json, os, sys
from collections import Counter
from pathlib import Path

GRAPH_BACKEND = os.getenv("GRAPH_BACKEND", "neo4j")
if GRAPH_BACKEND != "age":
    print(f"[ERROR] GRAPH_BACKEND={GRAPH_BACKEND!r}. Set GRAPH_BACKEND=age.")
    sys.exit(1)

_args = set(sys.argv[1:])
DRY_RUN = "--dry-run" in _args
LIVE = "--live" in _args
CLEAN = "--clean" in _args
if not DRY_RUN and not LIVE:
    print("Usage: --dry-run or --live [--clean] [--file=path]")
    sys.exit(1)

_file_arg = [a for a in sys.argv[1:] if a.startswith("--file=")]
_json_path = (
    Path(_file_arg[0].split("=", 1)[1]) if _file_arg
    else Path(__file__).parent / "zero_day_decisions.json"
)
if not _json_path.exists():
    print(f"[ERROR] Not found: {_json_path}")
    sys.exit(1)

with open(_json_path, "r", encoding="utf-8") as f:
    data = json.load(f)
alerts = data["alerts"]
decisions = data["decisions"]
metadata = data.get("metadata", {})
print(f"[INFO] {len(alerts)} alerts, {len(decisions)} decisions from {_json_path.name}")
if metadata:
    print(f"[INFO] Generator: {metadata.get('generator','?')}, days: {metadata.get('days_simulated','?')}")


def print_plan():
    cats = Counter(d["category"] for d in decisions)
    print(f"\n[DRY-RUN] Create {len(alerts)} Alerts + {len(decisions)} Decisions:")
    for cat, n in cats.most_common():
        c = sum(1 for d in decisions if d["category"] == cat and d["correct"])
        print(f"  {cat}: {n} ({c}/{n} = {c/n:.0%} correct)")

    errors = []
    aids = {a["alert_id"] for a in alerts}
    for i, d in enumerate(decisions):
        if not d.get("decision_id"):
            errors.append(f"[{i}]: no decision_id")
        if d.get("alert_id") not in aids:
            errors.append(f"[{i}]: orphan alert_id {d.get('alert_id')}")
        fv = d.get("factor_vector")
        if not isinstance(fv, list) or len(fv) != 6:
            errors.append(f"[{i}]: bad factor_vector (len={len(fv) if isinstance(fv,list) else type(fv).__name__})")
        if d.get("action") not in ("escalate", "investigate", "suppress", "monitor"):
            errors.append(f"[{i}]: bad action '{d.get('action')}'")
        if len(errors) >= 10:
            break

    if errors:
        print(f"\n  [ERRORS] {len(errors)} issues found:")
        for e in errors:
            print(f"    {e}")
    else:
        print(f"\n  [OK] All {len(decisions)} decisions passed validation.")
    print(f"\n  No changes made. Run with --live to load.")


async def run_live():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from ci_platform.graph.age_client import AGEClient
    client = AGEClient()
    S = AGEClient.serialize_for_age

    try:
        await client.ensure_graph()
        print("[OK] AGE connected.\n")
    except Exception as e:
        print(f"[ERROR] Cannot connect: {e}")
        sys.exit(1)

    if CLEAN:
        print("[CLEAN] Deleting existing zero_day_synthetic nodes...")
        await client.run_query(
            "MATCH (d:Decision {origin: 'zero_day_synthetic'}) DETACH DELETE d"
        )
        await client.run_query(
            "MATCH (a:Alert {origin: 'zero_day_synthetic'}) DETACH DELETE a"
        )
        print("[CLEAN] Done.\n")

    ex = await client.run_query(
        "MATCH (a:Alert) WHERE a.alert_id STARTS WITH 'SYN-' RETURN count(a) AS cnt"
    )
    if int(ex[0]["cnt"]) > 0 and not CLEAN:
        print(f"[WARN] {ex[0]['cnt']} synthetic alerts already exist. Use --clean or Ctrl+C.")
        import time
        time.sleep(3)

    print(f"[STEP 1] Creating {len(alerts)} alerts...")
    for i, a in enumerate(alerts):
        await client.run_query(
            f"CREATE (n:Alert {{"
            f"alert_id: {S(a['alert_id'])}, category: {S(a['category'])},"
            f"severity: {S(a.get('severity', 'medium'))},"
            f"alert_type: {S(a.get('alert_type', a['category']))},"
            f"timestamp_epoch: {S(a['timestamp_epoch'])},"
            f"origin: 'zero_day_synthetic',"
            f"source_location: {S(a.get('source_location', 'synthetic'))},"
            f"user_id: {S(a.get('user_id', ''))}, status: 'decided'"
            f"}})"
        )
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(alerts)} alerts...")

    print(f"[STEP 2] Creating {len(decisions)} decisions with DECIDED_ON edges...")
    ok, fail = 0, 0
    for d in decisions:
        try:
            await client.run_query(
                f"MATCH (a:Alert {{alert_id: {S(d['alert_id'])}}}) "
                f"CREATE (dd:Decision {{"
                f"decision_id: {S(d['decision_id'])}, category: {S(d['category'])},"
                f"action: {S(d['action'])}, factor_vector: {S(d['factor_vector'])},"
                f"confidence: {S(d['confidence'])}, correct: {S(d['correct'])},"
                f"outcome: {S(d['outcome'])}, timestamp_epoch: {S(d['timestamp_epoch'])},"
                f"origin: 'zero_day_synthetic',"
                f"source_id: {S(d.get('source_id', 'synthetic'))},"
                f"user_id: {S(d.get('user_id', ''))}"
                f"}}) CREATE (dd)-[:DECIDED_ON]->(a)"
            )
            ok += 1
        except Exception as e:
            fail += 1
            if fail <= 5:
                print(f"  [WARN] {d['decision_id']}: {e}")
        if (ok + fail) % 500 == 0:
            print(f"  {ok} ok, {fail} fail...")

    print(f"\n[STEP 3] Verification:")
    for lbl, q in [
        ("Syn alerts", "MATCH (a:Alert {origin: 'zero_day_synthetic'}) RETURN count(a) AS cnt"),
        ("Syn decisions", "MATCH (d:Decision {origin: 'zero_day_synthetic'}) RETURN count(d) AS cnt"),
        ("With DECIDED_ON", "MATCH (d:Decision {origin: 'zero_day_synthetic'})-[:DECIDED_ON]->() RETURN count(d) AS cnt"),
        ("Orphans (must=0)", "MATCH (d:Decision) WHERE NOT EXISTS((d)-[:DECIDED_ON]->()) RETURN count(d) AS cnt"),
        ("Total decisions", "MATCH (d:Decision) RETURN count(d) AS cnt"),
    ]:
        r = await client.run_query(q)
        print(f"  {lbl}: {r[0]['cnt']}")
    print("\n[OK] Done. Restart uvicorn.")


if __name__ == "__main__":
    if DRY_RUN:
        print_plan()
    elif LIVE:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run_live())
