"""Read-only investigation of pre-tagged SOC Decision populations."""

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
    values: list[object] = []
    for row in cur.fetchall():
        parsed_row: list[object] = []
        for value in row:
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    pass
            parsed_row.append(value)
        values.append(parsed_row[0] if columns == 1 else parsed_row)
    return values


def main() -> None:
    queries = [
        ("""
        MATCH (d:Decision)
        WHERE d.domain = 'soc'
        RETURN count(d) AS total_soc
        """, 1),
        ("""
        MATCH (d:Decision)
        WHERE d.domain = 'soc' AND d.domain_source IS NULL
        RETURN count(d) AS no_source
        """, 1),
        ("""
        MATCH (d:Decision)
        WHERE d.domain = 'soc' AND d.domain_source IS NOT NULL
        RETURN d.domain_source AS src, count(d) AS cnt
        """, 2),
        ("""
        MATCH (d:Decision)
        RETURN d.domain AS domain, count(d) AS cnt
        """, 2),
        ("""
        MATCH (d:Decision)
        WHERE d.domain = 'soc' AND d.archived = true
        RETURN count(d) AS archived
        """, 1),
        ("""
        MATCH (d:Decision)
        WHERE d.domain = 'soc'
        RETURN d.status AS status, count(d) AS cnt
        """, 2),
    ]

    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("LOAD 'age'")
            cur.execute("SET search_path = ag_catalog")
            for index, (query, columns) in enumerate(queries, start=1):
                print(f"{index}: {run_cypher(cur, query, columns)}")


if __name__ == "__main__":
    main()
