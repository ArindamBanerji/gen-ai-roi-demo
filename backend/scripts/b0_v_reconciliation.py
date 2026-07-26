"""B0 artifact: verify SOC scorer V against the AGE census after B1.

The pre-injection result is preserved in the migration design document.  This
post-B1 form uses the same GraphConfig/factory path as application startup and
is read-only, so it can be rerun as a reconciliation check.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = BACKEND_ROOT.parent.parent
SDK_ROOT = WORKSPACE_ROOT.parent / "copilot-sdk"
for path in (BACKEND_ROOT, SDK_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


V_SOC_QUERY = (
    "MATCH (d:Decision) "
    "WHERE d.domain = 'soc' "
    "AND (d.archived IS NULL OR d.archived <> true) "
    "AND ((d.status IS NOT NULL AND d.status IN ['confirmed','overridden']) "
    "OR (d.status IS NULL AND d.outcome IS NOT NULL)) "
    "RETURN count(DISTINCT d.decision_id) AS cnt"
)


def _redact_dsn(value: str) -> str:
    value = re.sub(r"(?i)(password=)[^\s]+", r"\1***", value)
    return re.sub(r"(postgres(?:ql)?://[^:/@]+:)[^@]+(@)", r"\1***\2", value)


def _census_v(dsn: str, graph: str) -> int:
    import psycopg2

    conn = psycopg2.connect(dsn)
    try:
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("LOAD 'age'")
        cur.execute('SET search_path = ag_catalog, "$user", public')
        cur.execute(
            f"SELECT * FROM cypher('{graph}', $$ {V_SOC_QUERY} $$) AS (cnt agtype)"
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError("AGE census query returned no row")
        return int(str(row[0]).strip('"'))
    finally:
        conn.close()


def main() -> int:
    from copilot_sdk.config import GraphConfig
    from copilot_sdk.graph.factory import create_graph_store
    from app.domains.soc.scorer_adapter import SOCCompoundingScorerAdapter

    config = GraphConfig.load("soc")
    if not config.dsn:
        raise RuntimeError("SOC GraphConfig resolved an empty AGE DSN")

    graph_store = create_graph_store(
        domain="soc",
        backend=config.backend,
        dsn=config.dsn,
        graph_name=config.graph,
        shared_graph_authorization=config.authorized,
    )
    scorer = SOCCompoundingScorerAdapter(graph_store=graph_store)
    # The adapter exposes the legacy ProfileScorer surface; V is owned by the
    # wrapped CompoundingScorer, which delegates to its GraphStore.
    scorer_v = int(scorer._compound.get_verified_count())
    census_v = _census_v(config.dsn, config.graph)
    delta = scorer_v - census_v

    print("B0 V RECONCILIATION")
    print(f"  scorer_store: {type(scorer._compound._graph_store).__name__}")
    print(f"  graph: {config.graph}")
    print(f"  dsn: {_redact_dsn(config.dsn)}")
    print(f"  scorer_v: {scorer_v}")
    print(f"  census_v: {census_v}")
    print(f"  delta (scorer - census): {delta}")
    print(f"  status: {'MATCH' if delta == 0 else 'RECONCILIATION_REQUIRED'}")
    return 0 if delta == 0 else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"B0 ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
