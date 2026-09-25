from __future__ import annotations

import socket
import uuid
import os
from collections.abc import Iterator

import pytest

from copilot_sdk.testing.fixtures import age_available
from app.routers import triage
from support import SOCTriageHarness


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
    config.addinivalue_line("markers", "age: requires live AGE")
    config.addinivalue_line(
        "markers",
        "live_backend: requires the SOC backend running on 127.0.0.1:8001",
    )


@pytest.fixture
def memory_store():
    from copilot_sdk.graph.memory_store import InMemoryGraphStore
    return InMemoryGraphStore(domain="soc")


@pytest.fixture
def age_graph(soc_stress_test_graph):
    from support.real_graph import SOCGraphFixture
    graph = SOCGraphFixture(*soc_stress_test_graph)
    try:
        yield graph
    finally:
        graph.close()


@pytest.fixture(autouse=True)
def soc_test_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the test profile explicit instead of relying on pytest detection."""
    monkeypatch.setenv("SOC_PROFILE", "test")


def _live_backend_reachable(timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection((LIVE_BACKEND_HOST, LIVE_BACKEND_PORT), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.fixture
def soc_stress_test_graph():
    """Create a disposable AGE graph namespace for one test."""
    # Generic application DSNs may be changed by configuration-contract tests.
    # An explicit test destination must remain authoritative for live fixtures.
    graph_dsn = os.environ.get("AGE_TEST_DSN", "").strip() or os.environ.get("GRAPH_DSN", "").strip()
    if not graph_dsn:
        pytest.skip("GRAPH_DSN not set")
    if not age_available():
        pytest.skip("AGE not reachable (no DSN configured or connection failed)")

    import psycopg

    # Include the process id and full UUID so interrupted or concurrently
    # collected suites cannot reuse a disposable AGE namespace.
    graph_name = f"soc_stress_test_{os.getpid()}_{uuid.uuid4().hex}"
    try:
        conn = psycopg.connect(graph_dsn, connect_timeout=3, autocommit=True)
    except psycopg.OperationalError as exc:
        pytest.skip(f"AGE connection failed: {exc}")
    try:
        conn.execute("LOAD 'age'")
        conn.execute('SET search_path = ag_catalog, "$user", public')
        conn.execute("SELECT create_graph(%s)", (graph_name,))
        yield graph_dsn, graph_name
    finally:
        try:
            if not conn.closed:
                conn.execute("LOAD 'age'")
                conn.execute('SET search_path = ag_catalog, "$user", public')
                conn.execute("SELECT drop_graph(%s, true)", (graph_name,))
        finally:
            conn.close()


@pytest.fixture
def soc_triage_harness(tmp_path, request) -> Iterator[SOCTriageHarness]:
    """Inject one stateful Decision authority into the triage route."""
    previous_scorer = triage.get_profile_scorer
    previous_client = triage.graph_client
    previous_outbox = os.environ.get("CI_PERSISTENCE_OUTBOX_PATH")
    os.environ["CI_PERSISTENCE_OUTBOX_PATH"] = str(tmp_path / "soc-outbox")
    graph = request.getfixturevalue("age_graph") if getattr(request, "param", None) == "age" else None
    harness = SOCTriageHarness(graph=graph)
    triage.get_profile_scorer = harness.get_scorer
    triage.graph_client = harness.graph_client
    try:
        yield harness
    finally:
        triage.get_profile_scorer = previous_scorer
        triage.graph_client = previous_client
        if previous_outbox is None:
            os.environ.pop("CI_PERSISTENCE_OUTBOX_PATH", None)
        else:
            os.environ["CI_PERSISTENCE_OUTBOX_PATH"] = previous_outbox


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
