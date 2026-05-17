from __future__ import annotations

import socket

import pytest


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
