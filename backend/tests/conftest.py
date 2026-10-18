from __future__ import annotations

import uuid
import json
import os
import sys
import threading
import time
import urllib.request
import urllib.error
import warnings
from http.client import HTTPException
from collections.abc import Iterator

import pytest

from copilot_sdk.config import GraphConfig

# Test processes create and destroy many complete app lifespans. Select the
# explicit fresh AGE mode before importing any app module so collection cannot
# initialize a pooled production client. Production defaults remain pooled.
os.environ["AGE_USE_POOL"] = "0"

from app.routers import triage
from support import SOCTriageHarness


_HEALTH_TIMEOUT = 30.0
_POLL_INTERVAL = 0.5
_AGE_GRAPH_DROP_LOCK = threading.Lock()


def _backend_url() -> str:
    return os.environ.get("SOC_BACKEND_URL", "http://localhost:8001").rstrip("/")


def _backend_is_ready(timeout: float = 5.0) -> bool:
    """Read the readiness contract, rather than just service identity."""
    try:
        with urllib.request.urlopen(f"{_backend_url()}/api/health", timeout=timeout) as response:
            data = json.load(response)
            if response.status != 200 or not isinstance(data, dict) or data.get("ready") is not True:
                return False
            graph_status = data.get("graph_status")
            if not isinstance(graph_status, dict):
                return False
            components = graph_status.get("components")
            return (
                isinstance(components, dict)
                and all(components.get(key) == "ready" for key in ("decisions", "topology", "learning_restore"))
                and not data.get("learning_counts_stale", False)
            )
    except (OSError, urllib.error.URLError, ValueError, HTTPException):
        return False


def _wait_until_backend_ready() -> None:
    deadline = time.monotonic() + _HEALTH_TIMEOUT
    announced = False
    while (remaining := deadline - time.monotonic()) > 0:
        if _backend_is_ready(timeout=min(5.0, remaining)):
            return
        if not announced:
            print(f"Waiting for SOC backend readiness at {_backend_url()} (up to {_HEALTH_TIMEOUT:g}s)", flush=True)
            announced = True
        time.sleep(min(_POLL_INTERVAL, max(0.0, deadline - time.monotonic())))
    warnings.warn(
        f"SOC backend did not become ready within {_HEALTH_TIMEOUT:g}s at {_backend_url()}. "
        "live_backend tests will run and may fail with their endpoint errors.",
        RuntimeWarning,
        stacklevel=2,
    )


@pytest.fixture(autouse=True, scope="session")
def _wait_for_backend_ready(request: pytest.FixtureRequest) -> None:
    if any(item.get_closest_marker("live_backend") for item in request.session.items):
        _wait_until_backend_ready()


@pytest.fixture(autouse=True, scope="session")
def _close_shared_age_clients_before_root_teardown() -> Iterator[None]:
    """Release keyed pools before root graph-contract teardown probes AGE."""
    yield
    from ci_platform.graph import reset_graph_clients

    reset_graph_clients()


def _configured_test_dsn() -> str:
    """Capture the app graph destination before tests patch the environment."""
    explicit = os.environ.get("AGE_TEST_DSN", "").strip()
    if explicit:
        return explicit
    configured = os.environ.get("GRAPH_DSN", "").strip()
    if configured:
        return configured
    return str(GraphConfig.load("soc").dsn or "").strip()


# Configuration-contract tests temporarily patch GRAPH_DSN. AGE fixtures must
# remain on the application destination captured at session setup.
_SESSION_GRAPH_DSN = _configured_test_dsn()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-live-backend",
        action="store_true",
        default=False,
        help="Compatibility flag; live_backend tests always use the session readiness gate.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "age: requires live AGE")
    config.addinivalue_line(
        "markers",
        "live_backend: requires SOC_BACKEND_URL (default http://localhost:8001)",
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
def soc_test_profile(
    monkeypatch: pytest.MonkeyPatch,
    _isolate_registry_handle_after_lifespan_shutdown: None,
) -> None:
    """Make the test profile explicit instead of relying on pytest detection."""
    monkeypatch.setenv("SOC_PROFILE", "test")
    # Disposable per-test graph clients use explicit fresh mode. Production
    # startup remains pooled, while the suite avoids retaining two worker
    # connections for every short-lived test graph namespace.
    monkeypatch.setenv("AGE_USE_POOL", "0")
    # A production shutdown permanently retires its stable proxy. The test
    # process runs many complete app lifespans in one interpreter, so close
    # only the current registry generation here; R5 proxy lifecycle tests use
    # separate handles and still exercise permanent shutdown directly.
    import app.db.graph_client as graph_module

    async def close_test_generation() -> None:
        from ci_platform.graph import reset_graph_client

        reset_graph_client(
            graph_module._GRAPH_CONFIG.dsn,
            graph_module._GRAPH_CONFIG.graph,
        )

    monkeypatch.setattr(graph_module.graph_client, "close", close_test_generation)


@pytest.fixture(autouse=True)
def _isolate_registry_handle_after_lifespan_shutdown() -> None:
    """Model a new process after a test runs the full application shutdown.

    Production handles are permanently dead after ``close()``. Pytest runs
    multiple complete lifespan cycles in one interpreter, so replace that
    dead generation before the next test and update app modules that imported
    the prior handle by value.
    """
    import app.db.graph_client as graph_module

    previous = graph_module.graph_client
    replacement = previous
    if getattr(previous, "_shutdown", False):
        replacement = graph_module._RegistryBackedAGEClient(
            graph_module._GRAPH_CONFIG.dsn,
            graph_module._GRAPH_CONFIG.graph,
        )
        graph_module.graph_client = replacement
    for name, loaded_module in tuple(sys.modules.items()):
        if not name.startswith("app.") or loaded_module is None:
            continue
        bound = getattr(loaded_module, "graph_client", None)
        if (
            type(bound).__name__ == "_RegistryBackedAGEClient"
            and bound is not replacement
        ):
            setattr(loaded_module, "graph_client", replacement)


@pytest.fixture
def soc_stress_test_graph():
    """Create a disposable AGE graph namespace for one test."""
    # Generic application DSNs may be changed by configuration-contract tests.
    # An explicit test destination must remain authoritative for live fixtures.
    graph_dsn = _SESSION_GRAPH_DSN
    if not graph_dsn:
        pytest.skip("GRAPH_DSN not set")
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
                with _AGE_GRAPH_DROP_LOCK:
                    for attempt in range(1, 4):
                        try:
                            conn.execute("LOAD 'age'")
                            conn.execute('SET search_path = ag_catalog, "$user", public')
                            conn.execute("SET lock_timeout = '5s'")
                            conn.execute("SELECT drop_graph(%s, true)", (graph_name,))
                            break
                        except psycopg.errors.DeadlockDetected as exc:
                            if attempt == 3:
                                warnings.warn(
                                    f"Could not drop disposable AGE graph {graph_name!r} "
                                    f"after {attempt} attempts: {exc}",
                                    RuntimeWarning,
                                    stacklevel=2,
                                )
                                break
                            time.sleep(0.5 * attempt)
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
