"""Reproduce: orphan Decision from failed DECIDED_ON edge write."""
import asyncio, os, sys
sys.path.insert(0, ".")
os.environ["GRAPH_BACKEND"] = "age"
from ci_platform.graph import get_graph_client

async def repro():
    c = get_graph_client()

    # Step 1: Create a test alert
    await c.run_query(
        "CREATE (a:Alert {alert_id: 'REPRO-001', category: 'credential_access', "
        "status: 'pending', severity: 'high', alert_type: 'anomalous_login', "
        "timestamp_epoch: 1776000000000})"
    )
    print("Created REPRO-001 alert")

    # Step 2: Try the exact pattern the triage path uses —
    # CREATE Decision + DECIDED_ON in one query
    successes, failures = 0, 0
    for i in range(20):
        try:
            await c.run_query(
                f"MATCH (a:Alert {{alert_id: 'REPRO-001'}}) "
                f"CREATE (d:Decision {{"
                f"decision_id: 'REPRO-DEC-{i:03d}', "
                f"action: 'investigate', category: 'credential_access', "
                f"confidence: 0.85, timestamp_epoch: {1776000000000 + i}"
                f"}}) "
                f"CREATE (d)-[:DECIDED_ON]->(a)"
            )
            successes += 1
        except Exception as e:
            failures += 1
            print(f"  [{i}] FAILED: {e}")

    print(f"\nResults: {successes} ok, {failures} failed")

    # Step 3: Check for orphans
    r = await c.run_query(
        "MATCH (d:Decision) WHERE d.decision_id STARTS WITH 'REPRO-DEC-' "
        "AND NOT EXISTS((d)-[:DECIDED_ON]->()) "
        "RETURN count(d) AS n"
    )
    print(f"Orphan REPRO decisions: {r[0]['n']}")

    # Step 4: Now try concurrent writes (the real trigger)
    import time
    tasks = []
    for i in range(20, 40):
        tasks.append(c.run_query(
            f"MATCH (a:Alert {{alert_id: 'REPRO-001'}}) "
            f"CREATE (d:Decision {{"
            f"decision_id: 'REPRO-DEC-{i:03d}', "
            f"action: 'escalate', category: 'credential_access', "
            f"confidence: 0.9, timestamp_epoch: {1776000000000 + i}"
            f"}}) "
            f"CREATE (d)-[:DECIDED_ON]->(a)"
        ))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    concurrent_ok = sum(1 for r in results if not isinstance(r, Exception))
    concurrent_fail = sum(1 for r in results if isinstance(r, Exception))
    for r in results:
        if isinstance(r, Exception):
            print(f"  [concurrent] FAILED: {r}")
    print(f"\nConcurrent: {concurrent_ok} ok, {concurrent_fail} failed")

    # Step 5: Check orphans again
    r2 = await c.run_query(
        "MATCH (d:Decision) WHERE d.decision_id STARTS WITH 'REPRO-DEC-' "
        "AND NOT EXISTS((d)-[:DECIDED_ON]->()) "
        "RETURN count(d) AS n"
    )
    print(f"Orphan REPRO decisions after concurrent: {r2[0]['n']}")

    # Cleanup
    await c.run_query(
        "MATCH (d:Decision) WHERE d.decision_id STARTS WITH 'REPRO-DEC-' "
        "DETACH DELETE d"
    )
    await c.run_query("MATCH (a:Alert {alert_id: 'REPRO-001'}) DELETE a")
    print("Cleaned up.")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(repro())
