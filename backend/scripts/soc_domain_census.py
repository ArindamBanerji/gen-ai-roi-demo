"""SOC domain census and backfill.

Per soc_domain_scoping_v1.1 §5:
- Census: read-only audit of NULL-domain Decisions
- Backfill: SET domain='soc' on NULL-domain Decisions (--apply)

Requires: GRAPH_DSN and GRAPH_NAME env vars.

Usage:
    python backend/scripts/soc_domain_census.py              # census only
    python backend/scripts/soc_domain_census.py --apply       # census + backfill
    python backend/scripts/soc_domain_census.py --apply --batch-size 500
"""
import argparse
import os
import sys
import psycopg2


def main():
    parser = argparse.ArgumentParser(description="SOC domain census + backfill")
    parser.add_argument("--apply", action="store_true", help="Apply backfill (default: dry-run census only)")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch size for backfill (default 500)")
    args = parser.parse_args()

    dsn = os.environ.get("GRAPH_DSN", os.environ.get("AGE_DSN", ""))
    graph = os.environ.get("GRAPH_NAME", os.environ.get("AGE_GRAPH_NAME", "soc_graph"))

    if not dsn:
        print("ERROR: set GRAPH_DSN or AGE_DSN")
        sys.exit(1)

    try:
        conn = psycopg2.connect(dsn)
    except Exception as e:
        print(f"ERROR: cannot connect — {e}")
        sys.exit(1)

    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("LOAD 'age'")
    cur.execute('SET search_path = ag_catalog, "$user", public')

    def cypher_int(query: str) -> int:
        cur.execute(
            f"SELECT * FROM cypher('{graph}', $$ {query} $$) as (c agtype)"
        )
        return int(str(cur.fetchone()[0]).strip('"'))

    def cypher_rows(query: str, cols: str) -> list:
        cur.execute(
            f"SELECT * FROM cypher('{graph}', $$ {query} $$) as ({cols})"
        )
        return cur.fetchall()

    print("=" * 60)
    print("SOC DOMAIN CENSUS")
    print(f"  Graph: {graph}")
    print("=" * 60)

    # 1. Count by domain
    print("\n--- Decision counts by domain ---")
    null_count = cypher_int(
        "MATCH (d:Decision) WHERE d.domain IS NULL RETURN count(d)"
    )
    soc_count = cypher_int(
        "MATCH (d:Decision) WHERE d.domain = 'soc' RETURN count(d)"
    )
    trading_count = cypher_int(
        "MATCH (d:Decision) WHERE d.domain = 'trading' RETURN count(d)"
    )
    purchasing_count = cypher_int(
        "MATCH (d:Decision) WHERE d.domain = 'purchasing' RETURN count(d)"
    )
    dataops_count = cypher_int(
        "MATCH (d:Decision) WHERE d.domain = 'dataops' RETURN count(d)"
    )
    s2p_count = cypher_int(
        "MATCH (d:Decision) WHERE d.domain = 's2p' RETURN count(d)"
    )
    total = cypher_int("MATCH (d:Decision) RETURN count(d)")

    print(f"  domain IS NULL:    {null_count}")
    print(f"  domain = 'soc':    {soc_count}")
    print(f"  domain = 'trading':    {trading_count}")
    print(f"  domain = 'purchasing': {purchasing_count}")
    print(f"  domain = 'dataops':    {dataops_count}")
    print(f"  domain = 's2p':        {s2p_count}")
    print(f"  Total:             {total}")
    print(f"  Sum check:         {null_count + soc_count + trading_count + purchasing_count + dataops_count + s2p_count} (should = {total})")

    # 2. NULL-domain verified counts
    print("\n--- NULL-domain verified breakdown ---")
    null_verified = cypher_int(
        "MATCH (d:Decision) WHERE d.domain IS NULL "
        "AND ((d.status IS NOT NULL AND d.status IN ['confirmed','overridden']) "
        "OR (d.status IS NULL AND d.outcome IS NOT NULL)) "
        "RETURN count(d)"
    )
    soc_verified = cypher_int(
        "MATCH (d:Decision) WHERE d.domain = 'soc' "
        "AND ((d.status IS NOT NULL AND d.status IN ['confirmed','overridden']) "
        "OR (d.status IS NULL AND d.outcome IS NOT NULL)) "
        "RETURN count(d)"
    )
    print(f"  NULL-domain verified: {null_verified}")
    print(f"  SOC-domain verified:  {soc_verified}")
    print(f"  Combined V_soc:       {null_verified + soc_verified} (should be 4,899)")

    # 3. NULL-domain correct counts
    null_correct = cypher_int(
        "MATCH (d:Decision) WHERE d.domain IS NULL AND d.correct = true RETURN count(d)"
    )
    soc_correct = cypher_int(
        "MATCH (d:Decision) WHERE d.domain = 'soc' AND d.correct = true RETURN count(d)"
    )
    print(f"  NULL-domain correct:  {null_correct}")
    print(f"  SOC-domain correct:   {soc_correct}")
    print(f"  Combined correct:     {null_correct + soc_correct}")

    # 4. NULL-domain archived check
    null_archived = cypher_int(
        "MATCH (d:Decision) WHERE d.domain IS NULL AND d.archived = true RETURN count(d)"
    )
    print(f"  NULL-domain archived: {null_archived}")

    # 5. NULL-domain Alert linkage
    print("\n--- NULL-domain Alert linkage ---")
    null_with_alert = cypher_int(
        "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
        "WHERE d.domain IS NULL RETURN count(DISTINCT d)"
    )
    null_without_alert = null_count - null_with_alert
    print(f"  Linked to Alert:     {null_with_alert}")
    print(f"  Not linked to Alert: {null_without_alert}")

    # 6. V_soc baseline (using the scoped query)
    print("\n--- V_soc baseline (compatibility predicate) ---")
    v_soc = cypher_int(
        "MATCH (d:Decision) "
        "WHERE (d.domain = 'soc' OR d.domain IS NULL) "
        "AND (d.archived IS NULL OR d.archived <> true) "
        "AND ((d.status IS NOT NULL AND d.status IN ['confirmed','overridden']) "
        "OR (d.status IS NULL AND d.outcome IS NOT NULL)) "
        "RETURN count(d)"
    )
    print(f"  V_soc (compat predicate): {v_soc}")

    # Summary
    print("\n" + "=" * 60)
    print("CENSUS SUMMARY")
    print(f"  NULL-domain Decisions: {null_count}")
    print(f"  SOC-domain Decisions:  {soc_count}")
    print(f"  V_soc:                 {v_soc}")
    print(f"  NULL with Alert link:  {null_with_alert}")

    # Alert linkage is diagnostic, not a hard gate. SOC decisions created
    # by evolution, bootstrap, or timestamp backfill may lack Alert edges.
    # Safety comes from the sum check: if all domains sum to total, no
    # unaccounted NULL-domain rows exist from other copilots.
    known_sum = null_count + soc_count + trading_count + purchasing_count + dataops_count + s2p_count
    safe_to_backfill = null_count > 0 and known_sum == total
    if null_without_alert > 0:
        print(f"\n  NOTE: {null_without_alert} NULL-domain Decisions have no Alert link.")
        print("  Expected for evolution/bootstrap/backfill-created decisions.")
    if known_sum != total:
        print(f"\n  WARNING: sum of known domains ({known_sum}) != total ({total}).")
        print("  Unknown domain values exist. Manual review required.")
        safe_to_backfill = False

    if not args.apply:
        print("\n  DRY RUN — no changes made.")
        if safe_to_backfill:
            print("  Census indicates safe to backfill. Re-run with --apply.")
        else:
            print("  Census requires manual review before --apply.")
        conn.close()
        sys.exit(0)

    # === BACKFILL ===
    if not safe_to_backfill:
        print("\n  ABORT: census does not confirm safe backfill.")
        print("  Review NULL-domain Decisions without Alert links.")
        conn.close()
        sys.exit(1)

    print("\n" + "=" * 60)
    print("BACKFILL — SET domain='soc' on NULL-domain Decisions")
    print("=" * 60)

    # Get all NULL-domain decision IDs
    rows = cypher_rows(
        "MATCH (d:Decision) WHERE d.domain IS NULL "
        "RETURN d.decision_id ORDER BY d.decision_id",
        "did agtype"
    )
    all_ids = [str(r[0]).strip('"') for r in rows]
    print(f"  Found {len(all_ids)} NULL-domain Decisions to backfill")

    # Batch update
    total_updated = 0
    batch_size = args.batch_size
    for i in range(0, len(all_ids), batch_size):
        batch = all_ids[i:i + batch_size]
        id_list = ", ".join(f"'{did}'" for did in batch)
        cur.execute(
            f"SELECT * FROM cypher('{graph}', $$ "
            f"MATCH (d:Decision) "
            f"WHERE d.domain IS NULL "
            f"AND d.decision_id IN [{id_list}] "
            f"SET d.domain = 'soc' "
            f"RETURN count(d) $$) as (c agtype)"
        )
        updated = int(str(cur.fetchone()[0]).strip('"'))
        total_updated += updated
        print(f"  Batch {i // batch_size + 1}: {updated} updated "
              f"({total_updated}/{len(all_ids)})")

    # Verify
    print("\n--- Post-backfill verification ---")
    remaining_null = cypher_int(
        "MATCH (d:Decision) WHERE d.domain IS NULL RETURN count(d)"
    )
    new_soc_count = cypher_int(
        "MATCH (d:Decision) WHERE d.domain = 'soc' RETURN count(d)"
    )
    post_v_soc = cypher_int(
        "MATCH (d:Decision) "
        "WHERE d.domain = 'soc' "
        "AND (d.archived IS NULL OR d.archived <> true) "
        "AND ((d.status IS NOT NULL AND d.status IN ['confirmed','overridden']) "
        "OR (d.status IS NULL AND d.outcome IS NOT NULL)) "
        "RETURN count(d)"
    )

    print(f"  NULL-domain remaining: {remaining_null}")
    print(f"  SOC-domain total:      {new_soc_count}")
    print(f"  V_soc (exact predicate): {post_v_soc}")
    print(f"  V_soc match:           {'PASS' if post_v_soc == v_soc else 'FAIL'}")
    print(f"  Zero NULL gate:        {'PASS' if remaining_null == 0 else 'FAIL'}")

    if remaining_null == 0 and post_v_soc == v_soc:
        print("\n  BACKFILL: PASS — safe to switch helper to exact mode.")
    else:
        print("\n  BACKFILL: ISSUE — review above.")

    conn.close()
    sys.exit(0 if (remaining_null == 0 and post_v_soc == v_soc) else 1)


if __name__ == "__main__":
    main()
