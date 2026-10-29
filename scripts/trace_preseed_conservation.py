#!/usr/bin/env python3
"""Trace conservation evaluation path during preseed mode.

Run from repo root:
    python scripts/trace_preseed_conservation.py

Requires: AGE/PostgreSQL running, GRAPH_DSN set or repository graph config.
Outputs: docs/preseed_conservation_trace.md
"""

from __future__ import annotations

import ast
import asyncio
from datetime import datetime
import inspect
import json
import os
from pathlib import Path
import sys
import traceback
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
OUTPUT_PATH = ROOT / "docs" / "preseed_conservation_trace.md"

# These must be set before any app import. GraphConfig loads the repository
# .env itself, without overriding explicitly supplied values.
os.environ["COPILOT_PRESEED_MODE"] = "true"
os.environ["SOC_DEMO_RESEED_ENABLED"] = "true"
os.environ["SOC_PROFILE"] = "production"
os.environ.setdefault("GRAPH_BACKEND", "age")
sys.path.insert(0, str(BACKEND))


def _exception(exc: BaseException) -> dict[str, str]:
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback": "".join(traceback.format_exception(exc)),
    }


def _json_default(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, (set, frozenset, tuple)):
        return list(value)
    if isinstance(value, Path):
        return str(value)
    return repr(value)


def _pretty(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, default=_json_default)


def _section(title: str, value: Any) -> str:
    return f"## {title}\n\n```json\n{_pretty(value)}\n```\n"


def _preseed_source_probe(evaluate: Any) -> dict[str, Any]:
    source_lines, start_line = inspect.getsourcelines(evaluate)
    source = "".join(source_lines)
    locations = [
        {
            "line": start_line + offset,
            "text": line.strip(),
        }
        for offset, line in enumerate(source_lines)
        if "PRESEED" in line
    ]
    tree = ast.parse(inspect.cleandoc(source))
    return_locations: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Return):
            continue
        rendered = ast.unparse(node.value) if node.value is not None else ""
        if "PRESEED" in rendered:
            return_locations.append(
                {"line": start_line + node.lineno - 1, "text": rendered}
            )
    return {
        "found": bool(locations),
        "locations": locations,
        "found_in_return_statement": bool(return_locations),
        "return_locations": return_locations,
    }


def _state_snapshot(state: Any, source: str) -> dict[str, Any]:
    history = getattr(state, "history", None) or []
    preseed_attributes = {
        name: getattr(state, name)
        for name in dir(state)
        if "preseed" in name.lower() and not name.startswith("__")
    }
    return {
        "source": source,
        "type": type(state).__name__,
        "decision_count": getattr(state, "decision_count", None),
        "history_length": len(history),
        "preseed_attributes": preseed_attributes,
    }


async def _read_only_l5_persist(_: dict[str, Any]) -> dict[str, Any]:
    """Suppress evaluate()'s diagnostic snapshot write in this read-only tool."""
    return {
        "attempted": False,
        "persisted": False,
        "reason": "suppressed_by_read_only_tracer",
    }


async def run_trace() -> dict[str, Any]:
    results: dict[str, Any] = {}
    graph_client: Any = None
    learning_store: Any = None

    try:
        from app.domains.soc.config import LEARNING_ENABLED
        from app.db.graph_client import graph_client as live_graph_client
        import app.services.gae_state as gae_state
        import app.services.learning_health as learning_health
        from app.services.learning_health import LearningHealthMonitor, _is_learning_enabled
        from app.routers.triage import _soc_effective_conservation_status
    except BaseException as exc:
        results["probe_1"] = {
            "environment": {
                "COPILOT_PRESEED_MODE": os.environ.get("COPILOT_PRESEED_MODE"),
                "SOC_DEMO_RESEED_ENABLED": os.environ.get("SOC_DEMO_RESEED_ENABLED"),
                "SOC_PROFILE": os.environ.get("SOC_PROFILE"),
                "GRAPH_BACKEND": os.environ.get("GRAPH_BACKEND"),
            },
            "import_error": _exception(exc),
        }
        results["diagnosis"] = (
            "Application imports failed before the conservation path could be evaluated. "
            "The trace contains the import exception and environment values available "
            "before the failure."
        )
        return results

    graph_client = live_graph_client
    results["probe_1"] = {
        "COPILOT_PRESEED_MODE": os.environ.get("COPILOT_PRESEED_MODE"),
        "SOC_DEMO_RESEED_ENABLED": os.environ.get("SOC_DEMO_RESEED_ENABLED"),
        "SOC_PROFILE": os.environ.get("SOC_PROFILE"),
        "GRAPH_BACKEND": os.environ.get("GRAPH_BACKEND"),
        "GRAPH_DSN_configured": bool(
            os.environ.get("GRAPH_DSN")
            or os.environ.get("AGE_DSN")
            or os.environ.get("DATABASE_URL")
        ),
        "LEARNING_ENABLED": LEARNING_ENABLED,
        "_is_learning_enabled": _is_learning_enabled(),
        "graph_client_type": type(graph_client).__name__,
        "graph_dsn": getattr(graph_client, "redacted_dsn", lambda: "unavailable")(),
    }

    try:
        results["probe_6"] = _preseed_source_probe(LearningHealthMonitor.evaluate)
    except Exception as exc:
        results["probe_6"] = {"error": _exception(exc)}

    try:
        manual_result = _soc_effective_conservation_status({"status": "PRESEED"})
        results["probe_7"] = {
            "input": {"status": "PRESEED"},
            "output": list(manual_result),
            "matches_expected": manual_result
            == ("GREEN", "conservation_preseed_allowed"),
        }
    except Exception as exc:
        results["probe_7"] = {"error": _exception(exc)}

    connection_error: BaseException | None = None
    try:
        await asyncio.wait_for(graph_client.connect(), timeout=15.0)
        results["age_connection"] = {"connected": True}
    except BaseException as exc:
        connection_error = exc
        results["age_connection"] = {
            "connected": False,
            "error": _exception(exc),
        }

    try:
        state = gae_state.get_learning_state()
        results["probe_2"] = _state_snapshot(state, "existing_process_singleton")
    except Exception as initial_exc:
        try:
            if connection_error is not None:
                raise RuntimeError("AGE unavailable; cannot hydrate learning state") from connection_error
            learning_store = gae_state._init_learning_store()
            stored_state = learning_store.get_posterior("soc", "soc_learning_state")
            if stored_state is None:
                state = gae_state._make_fresh_state()
                state_source = "fresh_in_memory_no_age_posterior"
            else:
                state = gae_state._state_from_payload(stored_state)
                state_source = "age_posterior_read_only"
            # A standalone process has no ASGI lifespan to populate the singleton.
            # Install the read-only hydrated state so evaluate() sees what startup
            # would have loaded, without calling init_learning_state(), which can write.
            gae_state._learning_state = state
            results["probe_2"] = _state_snapshot(state, state_source)
            results["probe_2"]["initial_get_learning_state_error"] = str(initial_exc)
        except Exception as exc:
            results["probe_2"] = {
                "initial_get_learning_state_error": _exception(initial_exc),
                "hydration_error": _exception(exc),
            }

    health: dict[str, Any] | None = None
    evaluate_error: BaseException | None = None
    try:
        # Production evaluate() writes a diagnostic L5 snapshot after calibration.
        # Suppress that write while leaving all state extraction, AGE reads, and
        # conservation calculations unchanged.
        learning_health._persist_l5_conservation_state = _read_only_l5_persist
        health = await asyncio.wait_for(
            LearningHealthMonitor.evaluate(graph_client), timeout=30.0
        )
        results["probe_3"] = health
    except BaseException as exc:
        evaluate_error = exc
        results["probe_3"] = {"error": _exception(exc)}

    effective_status = "UNKNOWN"
    effective_reason: str | None = None
    if health is not None:
        try:
            effective_status, effective_reason = _soc_effective_conservation_status(health)
            results["probe_4"] = {
                "effective_status": effective_status,
                "reason": effective_reason,
            }
        except Exception as exc:
            evaluate_error = exc
            results["probe_4"] = {"error": _exception(exc)}
    else:
        results["probe_4"] = {"skipped": "evaluate() did not return a health dict"}

    if evaluate_error is not None:
        results["probe_5"] = {
            "_conservation_block": True,
            "trigger": "LearningHealthMonitor.evaluate() or effective-status evaluation raised; triage fail-closed branch",
            "exception": f"{type(evaluate_error).__name__}: {evaluate_error}",
        }
    elif effective_status == "RED":
        results["probe_5"] = {
            "_conservation_block": True,
            "trigger": f"effective status RED ({effective_reason or 'no reason supplied'})",
        }
    else:
        results["probe_5"] = {
            "_conservation_block": False,
            "trigger": f"effective status {effective_status}",
        }

    probe_6 = results.get("probe_6", {})
    probe_7 = results.get("probe_7", {})
    if evaluate_error is not None:
        results["diagnosis"] = (
            "During the standalone preseed trace, LearningHealthMonitor.evaluate() "
            f"raised {type(evaluate_error).__name__}: {evaluate_error}. The outcome "
            "route catches that exception and sets _conservation_block=True, so L5 "
            "learning is blocked by the fail-closed branch. The manual PRESEED probe "
            f"returned {probe_7.get('output')}, while evaluate() contains PRESEED in a "
            f"return statement: {probe_6.get('found_in_return_statement', False)}."
        )
    else:
        raw_status = str((health or {}).get("status", "UNKNOWN"))
        nested = (health or {}).get("conservation")
        nested_status = nested.get("status") if isinstance(nested, dict) else None
        results["diagnosis"] = (
            f"With preseed environment flags set, evaluate() returned outer status "
            f"{raw_status!r} and nested conservation status {nested_status!r}; the SOC "
            f"helper resolved that to {effective_status!r} ({effective_reason!r}), making "
            f"_conservation_block={results['probe_5']['_conservation_block']}. The manual "
            f"PRESEED probe returned {probe_7.get('output')}, while evaluate() contains "
            f"PRESEED in a return statement: {probe_6.get('found_in_return_statement', False)}."
        )

    try:
        await graph_client.close()
    except BaseException as exc:
        results["graph_close_error"] = _exception(exc)
    return results


def write_findings(results: dict[str, Any]) -> None:
    timestamp = datetime.now().astimezone().isoformat()
    parts = [
        "# Preseed Conservation Trace\n",
        f"Date: {timestamp}\n",
        f"COPILOT_PRESEED_MODE: {os.environ['COPILOT_PRESEED_MODE']}\n",
        "Read-only note: the tracer suppresses only evaluate()'s L5 diagnostic "
        "snapshot write; all conservation calculations and graph reads use production code.\n",
    ]
    titles = (
        ("probe_1", "PROBE 1: Environment"),
        ("probe_2", "PROBE 2: Learning State"),
        ("probe_3", "PROBE 3: LearningHealthMonitor.evaluate() Full Output"),
        ("probe_4", "PROBE 4: _soc_effective_conservation_status() Result"),
        ("probe_5", "PROBE 5: Conservation Gate Decision"),
        ("probe_6", "PROBE 6: PRESEED in evaluate() source"),
        ("probe_7", "PROBE 7: Manual PRESEED bypass test"),
    )
    if "age_connection" in results:
        parts.append(_section("AGE Connection", results["age_connection"]))
    for key, title in titles:
        parts.append(_section(title, results.get(key, {"not_run": True})))
    parts.extend(("## DIAGNOSIS\n\n", str(results.get("diagnosis", "No diagnosis available.")), "\n"))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(parts), encoding="utf-8")


def main() -> int:
    try:
        results = asyncio.run(run_trace())
    except BaseException as exc:
        results = {
            "fatal_error": _exception(exc),
            "diagnosis": "The tracer hit an unexpected top-level error; see fatal_error.",
        }
    write_findings(results)
    print(f"Wrote {OUTPUT_PATH}")
    if "fatal_error" in results:
        print(_pretty(results["fatal_error"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
