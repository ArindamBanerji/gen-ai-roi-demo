"""AGE Behavior Validation -- 6 experiments testing trust assumptions."""
import asyncio, os, sys, re
sys.path.insert(0, ".")
os.environ["GRAPH_BACKEND"] = "age"
from ci_platform.graph import get_graph_client

async def experiments():
    c = get_graph_client()

    # EXP 1: SET d = {} vs SET d.prop = val
    print("=" * 60)
    print("EXP 1: SET d = {} vs SET d.prop = val")
    print("=" * 60)

    await c.run_query(
        "CREATE (t:TestIntegrity {test_id: 'exp1', a: 1, b: 2, c: 3})"
    )
    r = await c.run_query(
        "MATCH (t:TestIntegrity {test_id: 'exp1'}) "
        "RETURN t.a AS a, t.b AS b, t.c AS c"
    )
    print(f"  Before SET: a={r[0]['a']}, b={r[0]['b']}, c={r[0]['c']}")

    try:
        await c.run_query(
            "MATCH (t:TestIntegrity {test_id: 'exp1'}) SET t = {a: 99}"
        )
        r = await c.run_query(
            "MATCH (t:TestIntegrity) WHERE t.a = 99 "
            "RETURN t.a AS a, t.b AS b, t.c AS c, t.test_id AS test_id"
        )
        if r:
            row = r[0]
            print(f"  After SET t = {{a:99}}: a={row['a']}, b={row.get('b', 'WIPED')}, c={row.get('c', 'WIPED')}, test_id={row.get('test_id', 'WIPED')}")
            if row.get("b") is None:
                print("  >>> CONFIRMED: SET t = {} WIPES other properties in AGE")
            else:
                print("  >>> SAFE: SET t = {} preserves other properties in AGE")
        else:
            print("  >>> Node not found after SET -- even test_id was wiped and MATCH failed")
    except Exception as e:
        print(f"  >>> SET t = {{}} raised error: {e}")
        print("  >>> AGE may not support whole-node SET syntax")

    await c.run_query("MATCH (t:TestIntegrity) WHERE t.test_id = 'exp1' OR t.a = 99 DETACH DELETE t")

    # EXP 2: Does failed MATCH still CREATE in compound statement?
    print()
    print("=" * 60)
    print("EXP 2: Does failed MATCH still CREATE in compound statement?")
    print("=" * 60)

    try:
        await c.run_query(
            "MATCH (a:Alert {alert_id: 'DOES_NOT_EXIST_12345'}) "
            "CREATE (d:Decision {decision_id: 'exp2-orphan-test', category: 'test'}) "
            "CREATE (d)-[:DECIDED_ON]->(a)"
        )
        print("  Query returned without error")
    except Exception as e:
        print(f"  Query raised: {e}")

    r = await c.run_query(
        "MATCH (d:Decision {decision_id: 'exp2-orphan-test'}) "
        "RETURN d.decision_id AS did"
    )
    if r:
        print("  >>> ORPHAN CREATED: Decision exists without Alert match")
        r2 = await c.run_query(
            "MATCH (d:Decision {decision_id: 'exp2-orphan-test'})-[r:DECIDED_ON]->() "
            "RETURN count(r) AS edges"
        )
        print(f"  >>> Edges: {r2[0]['edges'] if r2 else 0}")
        await c.run_query("MATCH (d:Decision {decision_id: 'exp2-orphan-test'}) DETACH DELETE d")
    else:
        print("  >>> SAFE: No orphan created when MATCH finds nothing")
        print("  >>> The compound statement is atomic -- if MATCH fails, CREATE is skipped")

    # EXP 3: Does CREATE silently drop properties?
    print()
    print("=" * 60)
    print("EXP 3: Does CREATE silently drop properties? (11 props)")
    print("=" * 60)

    await c.run_query(
        "CREATE (d:Decision {"
        "decision_id: 'exp3-test', "
        "category: 'credential_access', "
        "action: 'escalate', "
        "factor_vector: '[0.1, 0.2, 0.3, 0.4, 0.5, 0.6]', "
        "confidence: 0.85, "
        "correct: true, "
        "outcome: 'correct', "
        "timestamp_epoch: 1234567890, "
        "origin: 'test', "
        "source_id: 'test', "
        "user_id: 'test-user'"
        "})"
    )

    r = await c.run_query(
        "MATCH (d:Decision {decision_id: 'exp3-test'}) "
        "RETURN d.correct AS correct, d.outcome AS outcome, "
        "d.confidence AS confidence, d.factor_vector AS fv, "
        "d.origin AS origin, d.source_id AS source_id, "
        "d.category AS category, d.action AS action, "
        "d.timestamp_epoch AS ts, d.user_id AS uid"
    )
    if r:
        row = r[0]
        missing = [k for k, v in row.items() if v is None]
        present = [k for k, v in row.items() if v is not None]
        print(f"  Present ({len(present)}): {present}")
        if missing:
            print(f"  >>> MISSING ({len(missing)}): {missing}")
            print(f"  >>> CREATE SILENTLY DROPPED PROPERTIES")
        else:
            print(f"  >>> ALL 10 PROPERTIES PRESENT -- CREATE is reliable")

    await c.run_query("MATCH (d:Decision {decision_id: 'exp3-test'}) DETACH DELETE d")

    # EXP 4: Concurrent SET on same node
    print()
    print("=" * 60)
    print("EXP 4: Concurrent SET on same node (10 concurrent writes)")
    print("=" * 60)

    await c.run_query(
        "CREATE (t:TestIntegrity {test_id: 'exp4', counter: 0, preserved: 'original'})"
    )

    async def update(i):
        await c.run_query(
            f"MATCH (t:TestIntegrity {{test_id: 'exp4'}}) SET t.counter = {i}"
        )

    results = await asyncio.gather(*[update(i) for i in range(10)], return_exceptions=True)
    errors = [r for r in results if isinstance(r, Exception)]
    if errors:
        print(f"  {len(errors)} concurrent SET errors:")
        for e in errors[:3]:
            print(f"    {e}")

    r = await c.run_query(
        "MATCH (t:TestIntegrity {test_id: 'exp4'}) "
        "RETURN t.counter AS counter, t.preserved AS preserved"
    )
    if r:
        print(f"  counter={r[0]['counter']}, preserved={r[0].get('preserved', 'WIPED')}")
        if r[0].get("preserved") == "original":
            print("  >>> Concurrent SET preserved other properties")
        else:
            print("  >>> CONCURRENT SET WIPED preserved property")
    else:
        print("  >>> Node not found after concurrent SET")

    await c.run_query("MATCH (t:TestIntegrity {test_id: 'exp4'}) DETACH DELETE t")

    # EXP 5: Triage.py and simulation.py Decision creation pattern
    print()
    print("=" * 60)
    print("EXP 5: Decision creation pattern in triage.py + simulation.py")
    print("=" * 60)

    for filename in ["app/routers/triage.py", "app/services/simulation.py"]:
        try:
            with open(filename, "r") as f:
                content = f.read()
            creates = [(m.start(), content[max(0, m.start() - 200):m.end() + 200])
                       for m in re.finditer(r"CREATE \(d:Decision", content)]
            if not creates:
                creates = [(m.start(), content[max(0, m.start() - 200):m.end() + 200])
                           for m in re.finditer(r"CREATE \(dd:Decision", content)]
            print(f"  {filename}:")
            if not creates:
                print(f"    No CREATE Decision found -- uses a different pattern")
            for i, (pos, ctx) in enumerate(creates):
                has_edge = "DECIDED_ON" in ctx
                line_no = content[:pos].count("\n") + 1
                print(f"    CREATE #{i+1} at line ~{line_no}: DECIDED_ON in same block = {has_edge}")
                if not has_edge:
                    print(f"    >>> TWO-QUERY PATTERN -- potential orphan source")
        except FileNotFoundError:
            print(f"  {filename}: NOT FOUND")

    # EXP 6: Current graph integrity
    print()
    print("=" * 60)
    print("EXP 6: Current graph integrity snapshot")
    print("=" * 60)

    r = await c.run_query("MATCH (d:Decision) RETURN count(d) AS total")
    print(f"  Total Decision nodes: {r[0]['total']}")

    r = await c.run_query("MATCH (d:Decision)-[:DECIDED_ON]->() RETURN count(d) AS connected")
    print(f"  Connected (DECIDED_ON): {r[0]['connected']}")

    r = await c.run_query(
        "MATCH (d:Decision) WHERE NOT EXISTS((d)-[:DECIDED_ON]->()) RETURN count(d) AS orphans"
    )
    print(f"  Orphans: {r[0]['orphans']}")

    r = await c.run_query(
        "MATCH (d:Decision) RETURN "
        "count(d) AS total, "
        "sum(CASE WHEN d.correct IS NOT NULL THEN 1 ELSE 0 END) AS has_correct, "
        "sum(CASE WHEN d.outcome IS NOT NULL THEN 1 ELSE 0 END) AS has_outcome, "
        "sum(CASE WHEN d.factor_vector IS NOT NULL THEN 1 ELSE 0 END) AS has_fv"
    )
    print(f"  Property coverage: {r[0]}")

    await c.run_query("MATCH (t:TestIntegrity) DETACH DELETE t")
    print()
    print("All experiments complete. Cleanup done.")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(experiments())
