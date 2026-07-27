"""V_soc §3.1a real-vs-synthetic Decision check."""

from __future__ import annotations

import json

import psycopg


DSN = (
    "host=localhost port=5433 dbname=soc_copilot user=postgres "
    "password=postgres sslmode=disable"
)


def run_cypher(cur: psycopg.Cursor, cypher: str, columns: int) -> list[object]:
    definition = ", ".join(f"column_{i} agtype" for i in range(columns))
    cur.execute(f"SELECT * FROM cypher('soc_graph', $$ {cypher} $$) AS ({definition})")
    rows: list[object] = []
    for row in cur.fetchall():
        values: list[object] = []
        for value in row:
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    pass
            values.append(value)
        rows.append(values[0] if columns == 1 else values)
    return rows


def main() -> None:
    queries = [
        ("""
        MATCH (d:Decision) WHERE d.domain = 'soc'
        RETURN d.outcome AS outcome_value, count(*) AS n
        ORDER BY n DESC
        """, 2),
        ("""
        MATCH (d:Decision) WHERE d.domain = 'soc'
        RETURN d.provenance AS tier, count(*) AS n
        """, 2),
        ("""
        MATCH (d:Decision) WHERE d.domain = 'soc'
        RETURN d.source AS source, count(*) AS n
        ORDER BY n DESC LIMIT 10
        """, 2),
        ("""
        MATCH (d:Decision) WHERE d.domain = 'soc'
        RETURN d.decision_id AS did
        ORDER BY d.decision_id LIMIT 10
        """, 1),
        ("""
        MATCH (d:Decision) WHERE d.domain = 'soc'
        RETURN min(d.timestamp_epoch) AS earliest,
               max(d.timestamp_epoch) AS latest
        """, 2),
    ]

    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("LOAD 'age'")
            cur.execute("SET search_path = ag_catalog")
            results = [run_cypher(cur, query, columns) for query, columns in queries]

    print(f"OUTCOME_DISTRIBUTION: {results[0]}")
    print(f"PROVENANCE_TIER: {results[1]}")
    print(f"SOURCE_DISTRIBUTION: {results[2]}")
    print(f"ID_PATTERN: {results[3]}")
    print(f"TIMESTAMP_SPREAD: {results[4]}")


if __name__ == "__main__":
    main()
