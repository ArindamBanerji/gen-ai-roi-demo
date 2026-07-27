from __future__ import annotations

import socket
import uuid

import pytest

from copilot_sdk.config import GraphConfig
from copilot_sdk.testing.fixtures import age_available


LIVE_BACKEND_HOST = "127.0.0.1"
LIVE_BACKEND_PORT = 8001


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-live-backend",
        action="store_true",
        default=False,
        help="Run tests marked live_backend when 127.0.0.1:8001 is reachable.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "live_backend: requires the SOC backend running on 127.0.0.1:8001",
    )


def _live_backend_reachable(timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection((LIVE_BACKEND_HOST, LIVE_BACKEND_PORT), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def soc_stress_test_graph():
    """Create an isolated AGE graph for destructive SOC contract tests."""
    if not age_available():
        pytest.skip("AGE not reachable (no DSN configured or connection failed)")

    config = GraphConfig.load("soc")
    if not config.dsn:
        pytest.skip("SOC AGE DSN is not configured")

    import psycopg

    graph_name = f"soc_stress_test_{uuid.uuid4().hex[:12]}"
    conn = psycopg.connect(config.dsn, connect_timeout=3, autocommit=True)
    try:
        conn.execute("LOAD 'age'")
        conn.execute('SET search_path = ag_catalog, "$user", public')
        conn.execute("SELECT create_graph(%s)", (graph_name,))
        yield config.dsn, graph_name
    finally:
        try:
            if not conn.closed:
                conn.execute("LOAD 'age'")
                conn.execute('SET search_path = ag_catalog, "$user", public')
                conn.execute("SELECT drop_graph(%s, true)", (graph_name,))
        finally:
            conn.close()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    marked = [item for item in items if item.get_closest_marker("live_backend")]
    if not marked:
        return

    if config.getoption("--run-live-backend") and _live_backend_reachable():
        return

    reason = "requires live SOC backend at 127.0.0.1:8001; use --run-live-backend"
    skip_marker = pytest.mark.skip(reason=reason)
    for item in marked:
        item.add_marker(skip_marker)
