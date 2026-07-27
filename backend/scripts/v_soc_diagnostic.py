"""Diagnostic scans for the V_soc verified-Decision census discrepancy."""

from __future__ import annotations

import json

import psycopg


DSN = (
    "host=localhost port=5433 dbname=soc_copilot user=postgres "
    "password=postgres sslmode=disable"
)


def run_cypher(cur: psycopg.Cursor, cypher: str) -> list[tuple]:
    cur.execute(f"SELECT * FROM cypher('soc_graph', $$ {cypher} $$) AS (result agtype)")
    rows = cur.fetchall()
    parsed: list[tuple] = []
    for row in rows:
        value = row[0]
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        parsed.append((value,))
    return parsed


def print_result(label: str, result: object) -> None:
    print(f"{label}: {result}")


def main() -> None:
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 AS alive")
            print_result("1", cur.fetchall())

            cur.execute("LOAD 'age'")
            cur.execute("SET search_path = ag_catalog")

            queries = [
                "MATCH (d:Decision) RETURN count(d) AS total",
                "MATCH (d:Decision) WHERE d.domain = 'soc' RETURN count(d) AS soc_total",
                "MATCH (d:Decision) WHERE d.domain = 'soc' RETURN d LIMIT 5",
                "MATCH (d:Decision) WHERE d.status IS NOT NULL RETURN count(d) AS has_status",
                "MATCH (d:Decision) WHERE d.outcome IS NOT NULL RETURN count(d) AS has_outcome",
                """
                MATCH (d:Decision)
                WHERE d.domain = 'soc'
                  AND (d.archived IS NULL OR d.archived <> true)
                  AND (
                    (d.status IS NOT NULL AND d.status IN ['confirmed', 'overridden'])
                    OR (d.status IS NULL AND d.outcome IS NOT NULL)
                  )
                RETURN count(DISTINCT d.decision_id) AS cnt
                """,
            ]
            for index, query in enumerate(queries, start=2):
                print_result(str(index), run_cypher(cur, query))


if __name__ == "__main__":
    main()
