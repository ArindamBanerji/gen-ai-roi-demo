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
