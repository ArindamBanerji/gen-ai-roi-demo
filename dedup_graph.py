"""Dedup Decision and Alert nodes — keep one copy of each, delete duplicates.

Usage:
    python dedup_graph.py --dry-run    # show what would be deleted
    python dedup_graph.py --live       # actually delete duplicates
"""
import asyncio
import os
import sys

sys.path.insert(0, "backend")
os.environ["GRAPH_BACKEND"] = "age"

from ci_platform.graph import get_graph_client


async def dedup(live=False):
    c = get_graph_client()
    mode = "LIVE" if live else "DRY-RUN"
    print(f"[{mode}] Dedup starting...")

    # --- Decisions ---
    # Find all decision_ids with duplicates
    dupes = await c.run_query(
        "MATCH (d:Decision) "
        "WITH d.decision_id AS did, count(d) AS cnt "
        "WHERE cnt > 1 "
        "RETURN did, cnt ORDER BY cnt DESC"
    )
    print(f"\nDecisions: {len(dupes)} IDs have duplicates")
    total_to_delete = sum(int(d['cnt']) - 1 for d in dupes)
    print(f"  Will delete {total_to_delete} duplicate nodes (keeping 1 each)")

    if live and dupes:
        deleted = 0
        batch_size = 100
        for i in range(0, len(dupes), batch_size):
            batch = dupes[i:i+batch_size]
            for d in batch:
                did = d['did']
                # Get all node IDs for this decision_id, ordered so we keep the first
                nodes = await c.run_query(
                    "MATCH (d:Decision) "
                    "WHERE d.decision_id = '" + str(did).replace("'", "''") + "' "
                    "RETURN id(d) AS nid "
                    "ORDER BY id(d) ASC"
                )
                if len(nodes) <= 1:
                    continue
                # Keep first, delete rest
                keep_id = nodes[0]['nid']
                for node in nodes[1:]:
                    del_id = node['nid']
                    await c.run_query(
                        "MATCH (d:Decision) "
                        "WHERE id(d) = " + str(del_id) + " "
                        "DETACH DELETE d"
                    )
                    deleted += 1
            print(f"  Deleted {deleted}/{total_to_delete} duplicate decisions...")
        print(f"  Done: {deleted} duplicate Decision nodes deleted")

    # --- Alerts ---
    alert_dupes = await c.run_query(
        "MATCH (a:Alert) "
        "WITH a.alert_id AS aid, count(a) AS cnt "
        "WHERE cnt > 1 "
        "RETURN aid, cnt ORDER BY cnt DESC"
    )
    print(f"\nAlerts: {len(alert_dupes)} IDs have duplicates")
    alert_to_delete = sum(int(a['cnt']) - 1 for a in alert_dupes)
    print(f"  Will delete {alert_to_delete} duplicate nodes (keeping 1 each)")

    if live and alert_dupes:
        deleted = 0
        for a in alert_dupes:
            aid = a['aid']
            nodes = await c.run_query(
                "MATCH (a:Alert) "
                "WHERE a.alert_id = '" + str(aid).replace("'", "''") + "' "
                "RETURN id(a) AS nid "
                "ORDER BY id(a) ASC"
            )
            if len(nodes) <= 1:
                continue
            keep_id = nodes[0]['nid']
            for node in nodes[1:]:
                del_id = node['nid']
                await c.run_query(
                    "MATCH (a:Alert) "
                    "WHERE id(a) = " + str(del_id) + " "
                    "DETACH DELETE a"
                )
                deleted += 1
        print(f"  Done: {deleted} duplicate Alert nodes deleted")

    # --- Verify ---
    r1 = await c.run_query("MATCH (d:Decision) RETURN count(d) AS n")
    r2 = await c.run_query("MATCH (a:Alert) RETURN count(a) AS n")
    r3 = await c.run_query(
        "MATCH (d:Decision) WHERE d.origin = 'zero_day_synthetic' "
        "AND d.correct IS NOT NULL RETURN count(d) AS n"
    )
    print(f"\nPost-dedup state:")
    print(f"  Decisions: {r1[0]['n']}")
    print(f"  Alerts: {r2[0]['n']}")
    print(f"  Zero-day with correct: {r3[0]['n']}")


if __name__ == "__main__":
    if "--live" in sys.argv:
        asyncio.run(dedup(live=True))
    elif "--dry-run" in sys.argv:
        asyncio.run(dedup(live=False))
    else:
        print("Usage: python dedup_graph.py --dry-run | --live")
