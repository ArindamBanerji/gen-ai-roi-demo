import json
import re
import statistics
import time
from pathlib import Path

import psycopg


DSN = "host=localhost port=5433 dbname=soc_copilot user=postgres password=postgres"
GRAPH = "soc_graph_diag_f8"
N = 10
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "spike_decision.json"


try:
    from psycopg_pool import ConnectionPool
except ImportError:
    ConnectionPool = None


def q(s):
    return s.replace("\\", "\\\\").replace("'", "\\'")


def clean_agtype(value):
    if value is None:
        return None
    text = str(value)
    for suffix in ("::vertex", "::edge", "::path"):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
    if text == "null":
        return None
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text[1:-1]
    return text


def parse_vertex(value):
    text = clean_agtype(value)
    if not isinstance(text, str):
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def connect():
    conn = psycopg.connect(DSN, autocommit=True)
    with conn.cursor() as cur:
        cur.execute("LOAD 'age'")
        cur.execute('SET search_path = ag_catalog, "$user", public')
    return conn


def cypher(conn, query, columns):
    with conn.cursor() as cur:
        cur.execute(f"SELECT * FROM cypher('{GRAPH}', $$ {query} $$) AS ({columns})")
        return cur.fetchall()


def scalar_cypher(conn, query, columns="v agtype"):
    rows = cypher(conn, query, columns)
    if not rows:
        return None
    return clean_agtype(rows[0][0])


def graph_node_count(conn):
    return int(clean_agtype(scalar_cypher(conn, "MATCH (n) RETURN count(n)", "n agtype")))


def graph_exists(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM ag_catalog.ag_graph WHERE name = %s", (GRAPH,))
        return cur.fetchone()[0] == 1


def discover_entity(conn):
    user_id = scalar_cypher(conn, "MATCH (u:User) RETURN u.id LIMIT 1", "id agtype")
    if user_id not in (None, ""):
        return {
            "entity_label": "User",
            "entity_property": "id",
            "entity_key": user_id,
            "evidence": "MATCH (u:User) RETURN u.id LIMIT 1",
            "substitution": None,
        }

    rows = cypher(conn, "MATCH (n) RETURN n LIMIT 100", "n agtype")
    for row in rows:
        vertex = parse_vertex(row[0])
        if not vertex:
            continue
        label = vertex.get("label")
        props = vertex.get("properties") or {}
        for prop, key in props.items():
            if key is not None and not isinstance(key, (dict, list)):
                return {
                    "entity_label": label,
                    "entity_property": prop,
                    "entity_key": clean_agtype(key),
                    "evidence": (
                        "User.id absent; substituted first primitive property from "
                        "MATCH (n) RETURN n LIMIT 100"
                    ),
                    "substitution": f"{label}.{prop}",
                }

    raise RuntimeError("Could not find a representative entity property in existing graph nodes")


def keyed_read(conn, label, prop, key):
    key_literal = q(str(key))
    query = f"MATCH (n:{label} {{{prop}: '{key_literal}'}}) RETURN n.{prop} LIMIT 1"
    value = scalar_cypher(conn, query, "v agtype")
    if value is None:
        raise RuntimeError(f"Representative keyed lookup returned no row for {label}.{prop}={key!r}")
    return value


def timed_ms(fn):
    start = time.perf_counter()
    fn()
    return (time.perf_counter() - start) * 1000.0


def summarize(values):
    return {
        "n": len(values),
        "mean_ms": statistics.fmean(values),
        "median_ms": statistics.median(values),
        "min_ms": min(values),
        "max_ms": max(values),
        "values_ms": values,
    }


def run_fresh_reads(entity):
    timings = []
    for _ in range(N):
        def one():
            with connect() as conn:
                keyed_read(conn, entity["entity_label"], entity["entity_property"], entity["entity_key"])

        timings.append(timed_ms(one))
    return timings


def configure_conn(conn):
    with conn.cursor() as cur:
        cur.execute("LOAD 'age'")
        cur.execute('SET search_path = ag_catalog, "$user", public')


def run_pool_reads(entity):
    timings = []
    with ConnectionPool(DSN, min_size=1, max_size=2, configure=configure_conn) as pool:
        pool.wait()
        for _ in range(N):
            def one():
                with pool.connection() as conn:
                    keyed_read(conn, entity["entity_label"], entity["entity_property"], entity["entity_key"])

            timings.append(timed_ms(one))
        write_ms, before_count, after_count = run_write_with_pool(pool, entity)
    return timings, write_ms, before_count, after_count


def run_write_with_pool(pool, entity):
    with pool.connection() as conn:
        return run_write_transaction(conn)


def run_warm_reads(entity):
    timings = []
    with connect() as conn:
        for _ in range(N):
            timings.append(
                timed_ms(
                    lambda: keyed_read(
                        conn,
                        entity["entity_label"],
                        entity["entity_property"],
                        entity["entity_key"],
                    )
                )
            )
        write_ms, before_count, after_count = run_write_transaction(conn)
    return timings, write_ms, before_count, after_count


def spike_dummy_count(conn):
    return int(clean_agtype(scalar_cypher(conn, "MATCH (d:SpikeDummy) RETURN count(d)", "n agtype")))


def run_write_transaction(conn):
    before_count = spike_dummy_count(conn)
    was_autocommit = conn.autocommit
    conn.autocommit = False
    try:
        start = time.perf_counter()
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM cypher('{GRAPH}', $$ CREATE (d:SpikeDummy {{id:'spike'}}) RETURN d $$) AS (d agtype)")
            cur.fetchone()
        write_ms = (time.perf_counter() - start) * 1000.0
        conn.rollback()
    finally:
        conn.autocommit = was_autocommit
    after_count = spike_dummy_count(conn)
    return write_ms, before_count, after_count


def main():
    with connect() as conn:
        if not graph_exists(conn):
            raise RuntimeError(f"AGE reachable, but graph {GRAPH!r} does not exist")
        node_count = graph_node_count(conn)
        if node_count <= 0:
            raise RuntimeError(f"Graph {GRAPH!r} exists but has no nodes")
        entity = discover_entity(conn)
        keyed_read(conn, entity["entity_label"], entity["entity_property"], entity["entity_key"])

    baseline = run_fresh_reads(entity)
    baseline_detail = summarize(baseline)
    baseline_per_query_ms = baseline_detail["mean_ms"]

    if ConnectionPool is not None:
        pool_mode = "psycopg_pool"
        pooled_or_warm, pooled_write_ms, before_count, after_count = run_pool_reads(entity)
    else:
        pool_mode = "warm_connection_fallback"
        pooled_or_warm, pooled_write_ms, before_count, after_count = run_warm_reads(entity)

    pooled_or_warm_detail = summarize(pooled_or_warm)
    pooled_or_warm_per_query_ms = pooled_or_warm_detail["mean_ms"]
    connection_tax_ms = baseline_per_query_ms - pooled_or_warm_per_query_ms

    if pooled_or_warm_per_query_ms < 10 and pooled_write_ms < 100:
        branch = "cache_model_viable"
    elif connection_tax_ms > pooled_or_warm_per_query_ms:
        branch = "reassess: dominant cost is CONNECTION TAX - pooling helps"
    else:
        branch = "reassess: pooled/warm reads still slow - AGE QUERY cost, not connection tax"

    result = {
        "graph": GRAPH,
        "node_count": node_count,
        "entity_label": entity["entity_label"],
        "entity_property": entity["entity_property"],
        "entity_key": entity["entity_key"],
        "entity_evidence": entity["evidence"],
        "entity_substitution": entity["substitution"],
        "pool_mode": pool_mode,
        "baseline_per_query_ms": baseline_per_query_ms,
        "pooled_or_warm_per_query_ms": pooled_or_warm_per_query_ms,
        "connection_tax_ms": connection_tax_ms,
        "pooled_write_ms": pooled_write_ms,
        "baseline_detail": baseline_detail,
        "pooled_or_warm_detail": pooled_or_warm_detail,
        "rollback_before_count": before_count,
        "rollback_after_count": after_count,
        "branch": branch,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print("Step 0 SOC AGE connection-tax spike")
    print(f"graph={GRAPH} node_count={node_count}")
    print(f"entity={entity['entity_label']}.{entity['entity_property']} key={entity['entity_key']!r}")
    if entity["substitution"]:
        print(f"entity_substitution={entity['substitution']} evidence={entity['evidence']}")
    print(f"pool_mode={pool_mode}")
    print(f"baseline_per_query_ms={baseline_per_query_ms:.3f}")
    print(f"pooled_or_warm_per_query_ms={pooled_or_warm_per_query_ms:.3f}")
    print(f"connection_tax_ms={connection_tax_ms:.3f}")
    print(f"pooled_write_ms={pooled_write_ms:.3f}")
    print(f"rollback_before_count={before_count} rollback_after_count={after_count}")
    print(f"branch={branch}")
    print(f"wrote={OUT}")


if __name__ == "__main__":
    main()
