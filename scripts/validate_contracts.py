#!/usr/bin/env python3
"""Validate the API contracts against a running backend."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx
import yaml  # type: ignore[import]


DEFAULT_READ_TIMEOUT_SECONDS = 15.0
QUEUE_PLACEHOLDER = "__FROM_QUEUE__"


class FixtureResolutionError(RuntimeError):
    """Raised when a dynamic contract fixture cannot be resolved."""


def load_contracts(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as contract_file:
        data = yaml.safe_load(contract_file)
    return list(data.get("endpoints", []))


def _timeout(read_seconds: float = DEFAULT_READ_TIMEOUT_SECONDS) -> httpx.Timeout:
    return httpx.Timeout(connect=5.0, read=read_seconds, write=5.0, pool=5.0)


def _body_timeout_message(
    read_seconds: float,
    bytes_received: int,
    content_length: int | None,
) -> str:
    if content_length and content_length > 0:
        percent = round(bytes_received / content_length * 100)
        return (
            f"Body-read timeout after {read_seconds:.1f}s: received "
            f"{bytes_received:,} of {content_length:,} bytes ({percent}%)"
        )
    return (
        f"Body-read timeout after {read_seconds:.1f}s: received "
        f"{bytes_received:,} bytes (Content-Length unavailable)"
    )


def _request_once(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    body: Any,
    query: dict[str, Any] | None,
    read_seconds: float,
    attempt_number: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    request_kwargs: dict[str, Any] = {
        "params": query,
        "timeout": _timeout(read_seconds),
    }
    if method in {"POST", "PUT", "PATCH", "DELETE"}:
        request_kwargs["json"] = body or {}

    try:
        with client.stream(method, url, **request_kwargs) as response:
            content_length_header = response.headers.get("content-length")
            content_length = (
                int(content_length_header)
                if content_length_header and content_length_header.isdigit()
                else None
            )
            chunks: list[bytes] = []
            bytes_received = 0
            try:
                for chunk in response.iter_bytes():
                    chunks.append(chunk)
                    bytes_received += len(chunk)
            except httpx.ReadTimeout:
                duration_ms = (time.perf_counter() - started) * 1000
                return {
                    "attempt": attempt_number,
                    "status": response.status_code,
                    "body": b"",
                    "duration_ms": duration_ms,
                    "content_length": content_length,
                    "bytes_received": bytes_received,
                    "phase": "body-read",
                    "error": _body_timeout_message(
                        read_seconds, bytes_received, content_length
                    ),
                }

            return {
                "attempt": attempt_number,
                "status": response.status_code,
                "body": b"".join(chunks),
                "duration_ms": (time.perf_counter() - started) * 1000,
                "content_length": content_length,
                "bytes_received": bytes_received,
                "phase": "complete",
                "error": None,
            }
    except httpx.ConnectTimeout:
        phase = "connect"
        error = "Connect timeout after 5.0s"
    except httpx.ReadTimeout:
        phase = "header"
        error = f"Header timeout after {read_seconds:.1f}s"
    except httpx.PoolTimeout:
        phase = "connect"
        error = "Connection pool timeout after 5.0s"
    except httpx.WriteTimeout:
        phase = "write"
        error = "Write timeout after 5.0s"
    except httpx.ConnectError as exc:
        phase = "connect"
        error = f"Connection failed: {exc}"

    return {
        "attempt": attempt_number,
        "status": None,
        "body": b"",
        "duration_ms": (time.perf_counter() - started) * 1000,
        "content_length": None,
        "bytes_received": 0,
        "phase": phase,
        "error": error,
    }


def _request_with_diagnostics(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    body: Any = None,
    query: dict[str, Any] | None = None,
    read_seconds: float = DEFAULT_READ_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    max_attempts = 2 if method == "GET" else 1

    for attempt_number in range(1, max_attempts + 1):
        attempt = _request_once(
            client,
            method,
            url,
            body=body,
            query=query,
            read_seconds=read_seconds,
            attempt_number=attempt_number,
        )
        attempts.append(attempt)
        body_timeout = (
            attempt["phase"] == "body-read" and attempt["status"] == 200
        )
        if body_timeout and attempt_number < max_attempts:
            continue
        return {**attempt, "attempts": attempts}

    raise AssertionError("request attempt loop exited unexpectedly")


def _resolve_queue_alert_id(base_url: str, client: httpx.Client) -> str:
    """Return a real queue alert id or report fixture resolution failure."""
    request_result = _request_with_diagnostics(
        client,
        "GET",
        f"{base_url}/api/alerts/queue",
    )
    if request_result["error"]:
        raise FixtureResolutionError(
            f"fixture resolution failed: {request_result['error']}"
        )
    if request_result["status"] != 200:
        raise FixtureResolutionError(
            "fixture resolution failed: "
            f"queue returned HTTP {request_result['status']}"
        )

    try:
        payload = json.loads(request_result["body"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FixtureResolutionError(
            "fixture resolution failed: queue response is not valid JSON"
        ) from exc

    alerts = payload if isinstance(payload, list) else payload.get("alerts", [])
    if not alerts or not isinstance(alerts[0], dict):
        raise FixtureResolutionError(
            "fixture resolution failed: queue contains no alerts"
        )
    alert_id = alerts[0].get("alert_id") or alerts[0].get("id")
    if not isinstance(alert_id, str) or not alert_id.strip():
        raise FixtureResolutionError(
            "fixture resolution failed: first queue alert has no alert id"
        )
    return alert_id


_cached_alert_ids: dict[str, str] = {}


def _get_queue_alert_id(base_url: str, client: httpx.Client) -> str:
    if base_url not in _cached_alert_ids:
        _cached_alert_ids[base_url] = _resolve_queue_alert_id(base_url, client)
    return _cached_alert_ids[base_url]


def _replace_in_json(value: Any, replacement: str) -> Any:
    if value is None:
        return None
    serialized = json.dumps(value)
    if QUEUE_PLACEHOLDER not in serialized:
        return value
    return json.loads(serialized.replace(QUEUE_PLACEHOLDER, replacement))


def _resolve_contract_placeholders(
    base_url: str,
    path: str,
    body: Any,
    query: dict[str, Any] | None,
    client: httpx.Client,
) -> tuple[str, Any, dict[str, Any] | None]:
    has_placeholder = (
        QUEUE_PLACEHOLDER in path
        or QUEUE_PLACEHOLDER in json.dumps(body)
        or QUEUE_PLACEHOLDER in json.dumps(query)
    )
    if not has_placeholder:
        return path, body, query

    alert_id = _get_queue_alert_id(base_url, client)
    return (
        path.replace(QUEUE_PLACEHOLDER, alert_id),
        _replace_in_json(body, alert_id),
        _replace_in_json(query, alert_id),
    )


def validate_endpoint(
    base_url: str,
    ep: dict[str, Any],
    verbose: bool,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Hit one endpoint and check status plus required fields."""
    original_path = str(ep["path"])
    method = str(ep.get("method", "GET")).upper()
    body = ep.get("body")
    query = ep.get("query")
    required = list(ep.get("required_fields", []))
    read_seconds = float(ep.get("timeout_seconds", DEFAULT_READ_TIMEOUT_SECONDS))
    result: dict[str, Any] = {
        "path": original_path,
        "resolved_path": original_path,
        "method": method,
        "status": None,
        "pass": False,
        "missing_fields": [],
        "error": None,
        "attempts": [],
        "duration_ms": 0.0,
        "content_length": None,
        "bytes_received": 0,
    }

    owns_client = client is None
    active_client = client or httpx.Client(timeout=_timeout())
    try:
        path, body, query = _resolve_contract_placeholders(
            base_url, original_path, body, query, active_client
        )
        result["resolved_path"] = path
        request_result = _request_with_diagnostics(
            active_client,
            method,
            f"{base_url}{path}",
            body=body,
            query=query,
            read_seconds=read_seconds,
        )
        for key in (
            "status",
            "attempts",
            "duration_ms",
            "content_length",
            "bytes_received",
        ):
            result[key] = request_result[key]
        if request_result["error"]:
            result["error"] = request_result["error"]
            return result

        response_body = request_result["body"].decode("utf-8", errors="replace")
        if request_result["status"] is None or request_result["status"] >= 400:
            result["error"] = f"HTTP {request_result['status']}"
            result["error_detail"] = response_body[:200]
            return result

        try:
            response_json = json.loads(response_body)
        except json.JSONDecodeError:
            if not required:
                result["pass"] = True
            else:
                result["error"] = "Response is not JSON"
            return result

        missing = [field for field in required if field not in response_json]
        result["missing_fields"] = missing
        result["pass"] = not missing
        if verbose and missing and isinstance(response_json, dict):
            result["actual_keys"] = list(response_json.keys())[:20]
        return result
    except FixtureResolutionError as exc:
        result["error"] = str(exc)
        return result
    except httpx.HTTPError as exc:
        result["error"] = f"HTTP client error: {exc}"
        return result
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result
    finally:
        if owns_client:
            active_client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate API contracts")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--tab", help="Only validate endpoints for this tab")
    parser.add_argument(
        "--contracts",
        default=str(Path(__file__).parents[1] / "contracts" / "api_contracts.yaml"),
    )
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"
    contracts_path = Path(args.contracts)
    if not contracts_path.exists():
        print(f"FATAL: {contracts_path} not found")
        sys.exit(1)

    endpoints = load_contracts(contracts_path)
    if args.tab:
        endpoints = [
            ep for ep in endpoints if args.tab in ep.get("consumed_by", [])
        ]

    print(f"Validating {len(endpoints)} endpoints against {base_url}")
    print("=" * 70)
    passed = 0
    failed = 0
    errors: list[dict[str, Any]] = []
    _cached_alert_ids.clear()

    with httpx.Client(timeout=_timeout()) as client:
        for ep in endpoints:
            result = validate_endpoint(base_url, ep, args.verbose, client)
            if result["pass"]:
                passed += 1
                status_str = "\033[32mPASS\033[0m"
            else:
                failed += 1
                status_str = "\033[31mFAIL\033[0m"
                errors.append(result)

            status_code = result["status"] or "---"
            timing = f"{result['duration_ms']:.0f}ms"
            size = f"{result['bytes_received']:,}B"
            print(
                f"  {status_str}  {result['method']:4s} "
                f"{result['path']:<50s} [{status_code}] {timing} {size}"
            )
            for attempt in result["attempts"]:
                if len(result["attempts"]) > 1:
                    detail = attempt["error"] or "completed"
                    print(
                        f"         Attempt {attempt['attempt']}: "
                        f"{attempt['phase']} in {attempt['duration_ms']:.0f}ms; {detail}"
                    )

            if args.verbose and not result["pass"]:
                if result.get("error"):
                    print(f"         Error: {result['error']}")
                if result.get("error_detail"):
                    print(f"         Detail: {result['error_detail'][:150]}")
                if result.get("missing_fields"):
                    print(f"         Missing: {result['missing_fields']}")
                if result.get("actual_keys"):
                    print(f"         Got keys: {result['actual_keys']}")

    print("=" * 70)
    print(f"TOTAL: {passed} passed, {failed} failed, {len(endpoints)} total")
    if errors:
        print("\n--- FAILURES ---")
        for error in errors:
            message = error.get("error") or f"missing fields: {error['missing_fields']}"
            print(f"  {error['method']:4s} {error['path']}: {message}")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
