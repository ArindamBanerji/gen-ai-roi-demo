"""Real loopback transport checks; never retry ambiguous seed writes."""
from __future__ import annotations

import importlib.util
import json
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any

import pytest

pytestmark = pytest.mark.no_data_guard


@pytest.fixture
def transport() -> Iterator[tuple[Any, list[str]]]:
    calls: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def respond(self) -> None:
            calls.append(self.path)
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if self.path == "/disconnect" and calls.count(self.path) == 1:
                self.close_connection = True
                return
            status = 423 if self.path == "/blocked" else 200
            payload = b"invalid JSON" if self.path == "/invalid" else json.dumps({
                "points": ["measured"] * 20000, "blocked": status == 423,
            }).encode()
            self.send_response(status)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        do_GET = respond
        do_POST = respond

        def log_message(self, format: str, *args: object) -> None:
            pass

    path = Path(__file__).resolve().parents[2] / "scripts/preseed_demo_scenarios.py"
    spec = importlib.util.spec_from_file_location("soc_preseed_transport", path)
    assert spec is not None and spec.loader is not None
    module: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    module.BASE_URL = f"http://127.0.0.1:{server.server_port}"
    try:
        yield module, calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_large_comparison_body_and_query(transport: tuple[Any, list[str]]) -> None:
    module, calls = transport
    status, body = module.http_json("GET", "/comparison?demo=true")
    assert status == 200 and len(body["points"]) == 20000
    assert calls == ["/comparison?demo=true"]


def test_read_transport_failure_retried_once(transport: tuple[Any, list[str]]) -> None:
    module, calls = transport
    status, body = module.http_json("GET", "/disconnect")
    assert status == 200 and len(body["points"]) == 20000
    assert calls == ["/disconnect", "/disconnect"]


@pytest.mark.parametrize("path,expected", [("/disconnect", 0), ("/blocked", 423)])
def test_ambiguous_or_rejected_write_never_retried(
    transport: tuple[Any, list[str]], path: str, expected: int,
) -> None:
    module, calls = transport
    status, body = module.http_json("POST", path, {"decision_id": "one"})
    assert status == expected
    assert body["error"] if expected == 0 else body["blocked"]
    assert calls == [path]


def test_invalid_json_fails_closed(transport: tuple[Any, list[str]]) -> None:
    module, calls = transport
    status, body = module.http_json("GET", "/invalid")
    assert status == 0 and body["error"] == "invalid_json"
    assert calls == ["/invalid"]
