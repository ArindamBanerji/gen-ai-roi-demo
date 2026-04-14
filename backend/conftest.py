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
def verify_persistent_data_intact():
    """
    BACKLOG-069 Layer 5 — Guard zero-day training data across the full test run.

    Counts zero-day Decision nodes before and after the session.
    Fails loudly if any were deleted or had correct=true stripped.
    Runs only when AGE is reachable (skips silently in CI without NEO4J_URI).
    """
    import asyncio

    async def _count():
        try:
            from app.clients.neo4j_client import neo4j_client
            total = await neo4j_client.run_query(
                "MATCH (d:Decision) WHERE d.source STARTS WITH 'zero_day_' "
                "RETURN count(d) AS n, "
                "sum(CASE WHEN d.correct = true THEN 1 ELSE 0 END) AS correct_n"
            )
            if not total:
                return None, None
            return int(total[0]["n"]), int(total[0]["correct_n"])
        except Exception:
            return None, None

    before_total, before_correct = asyncio.get_event_loop().run_until_complete(_count())

    yield  # run the full test suite

    if before_total is None:
        # AGE not reachable — skip verification silently
        return

    after_total, after_correct = asyncio.get_event_loop().run_until_complete(_count())
    if after_total is None:
        return

    print(
        f"\n[POST-TEST] Zero-day data intact: {after_total} decisions "
        f"({after_correct} correct=true)"
    )
    assert after_total >= before_total, (
        f"Zero-day Decision nodes were deleted during the test run! "
        f"Before: {before_total}, After: {after_total}. "
        f"A test called hard_reset() or ran a raw DETACH DELETE on Decision nodes."
    )
    assert after_correct >= before_correct, (
        f"Zero-day correct=true count dropped during the test run! "
        f"Before: {before_correct}, After: {after_correct}. "
        f"A test called soft_reset() or ran a raw REMOVE d.correct on Decision nodes."
    )
