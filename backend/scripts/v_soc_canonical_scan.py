"""Read-only V_soc reconciliation scans against PostgreSQL+AGE."""

from __future__ import annotations

import json

import psycopg


DSN = (
    "host=localhost port=5433 dbname=soc_copilot user=postgres "
    "password=postgres sslmode=disable"
)
GRAPH = "soc_graph"


def run_scan(cur: psycopg.Cursor, cypher: str, alias: str) -> int:
    cur.execute(
        f"SELECT * FROM cypher('soc_graph', $$ {cypher} $$) AS (result agtype)"
    )
    row = cur.fetchone()
    if row is None:
        return 0
    value = row[0]
    if isinstance(value, str):
        value = json.loads(value)
    if isinstance(value, dict):
        return int(value.get(alias) or 0)
    return 0


def main() -> None:
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("LOAD 'age'")
            cur.execute("SET search_path = ag_catalog")

            scan_a = run_scan(
                cur,
                """
                MATCH (d:Decision)
                WHERE d.domain = 'soc'
                  AND (
                    (d.status IS NOT NULL AND d.status IN ['confirmed', 'overridden'])
                    OR (d.status IS NULL AND d.outcome IS NOT NULL)
                  )
                RETURN count(d) AS v_soc_total
                """,
                "v_soc_total",
            )
            scan_b = run_scan(
                cur,
                """
                MATCH (d:Decision)
                WHERE d.domain IS NULL
                  AND (
                    (d.status IS NOT NULL AND d.status IN ['confirmed', 'overridden'])
                    OR (d.status IS NULL AND d.outcome IS NOT NULL)
                  )
                RETURN count(d) AS v_null_domain
                """,
                "v_null_domain",
            )
            scan_c = run_scan(
                cur,
                """
                MATCH (d:Decision)
                WHERE d.domain_source IS NOT NULL
                RETURN count(d) AS with_provenance
                """,
                "with_provenance",
            )

    print(f"SCAN_A: {scan_a}")
    print(f"SCAN_B: {scan_b}")
    print(f"SCAN_C: {scan_c}")


if __name__ == "__main__":
    main()
