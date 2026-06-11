from __future__ import annotations

import asyncio
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Awaitable, Callable


DEFAULT_DSN = "host=localhost port=5433 dbname=soc_copilot user=postgres password=postgres"
DEFAULT_BACKEND_URL = "http://127.0.0.1:8001"
RULE40_HINT = (
    "RULE #40: Windows-side AGE/PostgreSQL DSNs must use localhost, not 127.0.0.1. "
    "Only commands running inside WSL2 may use 127.0.0.1."
)
NETWORK_SPLIT_HINT = (
    "Network Split Rule: AGE/PostgreSQL DSNs use host=localhost on Windows, "
    "while local FastAPI/uvicorn HTTP calls should use http://127.0.0.1:<port>."
)

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
PROJECTS_ROOT = REPO_ROOT.parent
REPORT_DIR = REPO_ROOT / "docs" / "implementation_plans" / "perf"

_WRITE_TOKENS = re.compile(r"\b(CREATE|DELETE|SET|MERGE|REMOVE|DROP|ALTER|INSERT|UPDATE)\b", re.IGNORECASE)
_UNSAFE_CALL = re.compile(r"\bCALL\s+(db|cypher)\b", re.IGNORECASE)


def ensure_repo_paths() -> None:
    """Prepend local source repos needed by standalone diagnostics."""
    paths = [
        PROJECTS_ROOT / "ci-platform",
        REPO_ROOT / "backend",
        REPO_ROOT,
    ]
    for path in reversed(paths):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)


def redact_dsn(dsn: str | None) -> str | None:
    if dsn is None:
        return None
    parts: list[str] = []
    for part in str(dsn).split():
        parts.append("password=***" if part.lower().startswith("password=") else part)
    return " ".join(parts)


def validate_rule40_dsn(dsn: str) -> bool:
    if os.name == "nt" and "127.0.0.1" in str(dsn):
        raise ValueError(f"{RULE40_HINT} Received graph DSN {redact_dsn(dsn)!r}.")
    return True


def validate_network_split(graph_dsn: str, backend_url: str) -> list[str]:
    """Validate the Windows AGE/HTTP split; warn on slow HTTP localhost."""
    validate_rule40_dsn(graph_dsn)
    warnings: list[str] = []
    if "localhost" in str(backend_url).lower():
        warnings.append(
            f"{NETWORK_SPLIT_HINT} backend_url={backend_url!r} uses localhost; "
            "use http://127.0.0.1:<port> to avoid IPv6 localhost fallback latency."
        )
    return warnings


def configure_age_env(graph_name: str, graph_dsn: str) -> None:
    validate_rule40_dsn(graph_dsn)
    os.environ["GRAPH_BACKEND"] = "age"
    os.environ["GRAPH_DSN"] = graph_dsn
    os.environ["AGE_GRAPH_NAME"] = graph_name


def assert_read_only_cypher(query: str) -> None:
    cleaned = re.sub(r"//.*?$", "", str(query), flags=re.MULTILINE)
    if ";" in cleaned:
        raise ValueError(f"Unsafe Cypher: semicolons are not allowed: {query!r}")
    if _WRITE_TOKENS.search(cleaned):
        raise ValueError(f"Unsafe Cypher: write token found in read-only benchmark: {query!r}")
    if _UNSAFE_CALL.search(cleaned):
        raise ValueError(f"Unsafe Cypher: CALL db/cypher is not allowed: {query!r}")


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percentile
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def summarize_durations(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min_s": None, "max_s": None, "avg_s": None, "p50_s": None, "p95_s": None}
    return {
        "min_s": round(min(values), 6),
        "max_s": round(max(values), 6),
        "avg_s": round(statistics.fmean(values), 6),
        "p50_s": round(_percentile(values, 0.50) or 0.0, 6),
        "p95_s": round(_percentile(values, 0.95) or 0.0, 6),
    }


def timed_sync(label: str, fn: Callable[[], Any], reps: int) -> dict[str, Any]:
    durations: list[float] = []
    error: str | None = None
    last_result: Any = None
    for _ in range(max(1, reps)):
        started = time.perf_counter()
        try:
            last_result = fn()
        except Exception as exc:  # noqa: BLE001 - diagnostics must capture failures.
            error = str(exc)
            break
        finally:
            durations.append(time.perf_counter() - started)
    return {
        "label": label,
        "reps": len(durations),
        **summarize_durations(durations),
        "error": error,
        "last_result": last_result,
    }


async def timed_async(label: str, coro_fn: Callable[[], Awaitable[Any]], reps: int) -> dict[str, Any]:
    durations: list[float] = []
    error: str | None = None
    last_result: Any = None
    for _ in range(max(1, reps)):
        started = time.perf_counter()
        try:
            last_result = await coro_fn()
        except Exception as exc:  # noqa: BLE001 - diagnostics must capture failures.
            error = str(exc)
            break
        finally:
            durations.append(time.perf_counter() - started)
    return {
        "label": label,
        "reps": len(durations),
        **summarize_durations(durations),
        "error": error,
        "last_result": last_result,
    }


def print_table(rows: list[dict[str, Any]]) -> None:
    headers = ("label", "reps", "avg_s", "p50_s", "p95_s", "max_s", "error")
    widths = {header: len(header) for header in headers}
    for row in rows:
        for header in headers:
            widths[header] = max(widths[header], len(str(row.get(header, ""))))
    print("  ".join(header.ljust(widths[header]) for header in headers), flush=True)
    print("  ".join("-" * widths[header] for header in headers), flush=True)
    for row in rows:
        print("  ".join(str(row.get(header, "")).ljust(widths[header]) for header in headers), flush=True)


def write_json_and_md(
    report_name: str,
    payload: dict[str, Any],
    sections: list[tuple[str, str]],
    *,
    json_output: str | Path | None = None,
    md_output: str | Path | None = None,
) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = Path(json_output) if json_output else REPORT_DIR / f"{report_name}.json"
    md_path = Path(md_output) if md_output else REPORT_DIR / f"{report_name}.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    lines = [f"# {payload.get('title', report_name)}", ""]
    for heading, body in sections:
        lines.extend([f"## {heading}", body.rstrip(), ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


async def run_read_query(client: Any, query: str) -> Any:
    assert_read_only_cypher(query)
    return await client.run_query(query)


def run(coro: Awaitable[Any]) -> Any:
    return asyncio.run(coro)
