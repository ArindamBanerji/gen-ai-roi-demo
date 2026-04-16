"""
Root conftest for the backend test suite.

Static-analysis tests (test_h7_fix3, test_h7_fix4) read router files via
relative paths such as ``pathlib.Path("app/routers/soc.py")``.  Those paths
are only valid when CWD == backend/.  This module-level chdir ensures the
tests work regardless of the directory from which pytest is invoked.

Neo4j marker
------------
Tests that require a live Neo4j connection should be decorated with
``@pytest.mark.neo4j`` (or ``pytestmark = pytest.mark.neo4j`` at module
level).  When the NEO4J_URI environment variable is not set (e.g. in CI),
those tests are automatically skipped.  Locally, with NEO4J_URI set in
your .env, they run as normal.
"""
import os
import pathlib
import pytest

# Load .env BEFORE reading GRAPH_BACKEND so that values set only in .env
# (not exported to the shell) are visible to the policy check below.
try:
    from dotenv import load_dotenv as _load_dotenv
    for _env_path in ["../.env", ".env"]:
        if pathlib.Path(_env_path).exists():
            _load_dotenv(_env_path, override=False)  # shell env takes precedence
            break
except ImportError:
    pass

os.chdir(pathlib.Path(__file__).parent)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "neo4j: mark test as requiring a live Neo4j connection",
    )


def pytest_collection_modifyitems(config, items):
    if os.getenv("NEO4J_URI"):
        return  # Neo4j available — run all tests
    skip_neo4j = pytest.mark.skip(reason="requires live Neo4j (NEO4J_URI not set)")
    for item in items:
        if "neo4j" in item.keywords:
            item.add_marker(skip_neo4j)


@pytest.fixture(scope="session", autouse=True)
def verify_persistent_data(request):
    """
    BACKLOG-069 Layer 5 — Guard zero-day training data across the full test run.

    PRE-TEST: Counts persistent Decision nodes with correct IS NOT NULL.
    Aborts the entire session (pytest.exit) if fewer than 3,000 found — means
    seed_zero_day.py --backfill has not been run and the data is not ready.

    POST-TEST: Re-counts. Fails loudly if the count dropped by more than 10
    (allows for minor transient variance but catches bulk wipes).

    Skips silently when GRAPH_BACKEND != 'age' (unit-test / CI runs).
    """
    import asyncio
    import os as _os

    if _os.getenv("GRAPH_BACKEND") != "age":
        yield
        return

    async def _count_persistent() -> int:
        try:
            from app.db.neo4j import neo4j_client
            r = await neo4j_client.run_query(
                "MATCH (d:Decision) WHERE d.origin = 'zero_day_synthetic' "
                "AND d.correct IS NOT NULL "
                "RETURN count(d) AS n"
            )
            return int(r[0]["n"]) if r else 0
        except Exception:
            return -1  # AGE unreachable — sentinel, skip checks

    n_before = asyncio.run(_count_persistent())

    if n_before == -1:
        # AGE not reachable — skip silently
        yield
        return

    if n_before < 3000:
        pytest.exit(
            f"ZERO-DAY DATA MISSING: only {n_before} persistent decisions with "
            f"correct IS NOT NULL (need >= 3000). "
            f"Run: python backend/support/setup/seed_zero_day.py --backfill",
            returncode=1,
        )

    yield  # run the full test suite

    n_after = asyncio.run(_count_persistent())
    if n_after == -1:
        return  # AGE unreachable post-test — skip

    print(
        f"\n[POST-TEST] Zero-day data intact: {n_after} decisions "
        f"(correct IS NOT NULL, origin='zero_day_synthetic')"
    )
    if n_after < n_before - 10:
        pytest.fail(
            f"ZERO-DAY DATA WIPED: {n_before} before → {n_after} after. "
            f"A test called hard_reset(), demo/reset-all, or ran a raw "
            f"DETACH DELETE on Decision nodes."
        )


@pytest.fixture(scope="session", autouse=True)
def report_graph_contract(request):
    """
    BACKLOG-070b — Post-session graph contract health report.

    Runs verify_graph() after the full test suite and prints a summary.
    Non-blocking: prints issues as warnings, does NOT fail the suite.
    Lets the operator know if backbone nodes (User/Asset/Campaign) are missing.

    Skips when GRAPH_BACKEND != 'age'.
    """
    yield  # let the full suite run first

    import os as _os
    if _os.getenv("GRAPH_BACKEND") != "age":
        return

    import asyncio

    async def _check():
        try:
            from app.graph_schema import verify_graph
            return await verify_graph()
        except Exception as exc:
            return {"healthy": None, "issues": [str(exc)], "counts": {}}

    report = asyncio.run(_check())

    if report.get("healthy") is None:
        print("\n[GRAPH CONTRACT] Could not run: " + str(report["issues"]))
        return

    counts = report.get("counts", {})
    print(
        f"\n[GRAPH CONTRACT] "
        f"Alert={counts.get('Alert', '?')} "
        f"Decision={counts.get('Decision', '?')} "
        f"User={counts.get('User', '?')} "
        f"Asset={counts.get('Asset', '?')} "
        f"Campaign={counts.get('Campaign', '?')}"
    )
    if report["healthy"]:
        print("[GRAPH CONTRACT] All contract checks passed.")
    else:
        print(f"[GRAPH CONTRACT] {len(report['issues'])} issue(s) — run seed_graph() to fix:")
        for issue in report["issues"]:
            print(f"  WARNING: {issue}")
