from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
DEFAULT_TRACE = REPO_ROOT / "scratch" / "temp" / "soc_perf_trace_phase_c_smoke.jsonl"
DEFAULT_REPORT_DIR = REPO_ROOT / "docs" / "implementation_plans" / "perf"


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


def _stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "min_ms": None,
            "avg_ms": None,
            "p50_ms": None,
            "p95_ms": None,
            "p99_ms": None,
            "max_ms": None,
        }
    return {
        "count": len(values),
        "min_ms": round(min(values), 3),
        "avg_ms": round(statistics.fmean(values), 3),
        "p50_ms": round(_percentile(values, 0.50) or 0.0, 3),
        "p95_ms": round(_percentile(values, 0.95) or 0.0, 3),
        "p99_ms": round(_percentile(values, 0.99) or 0.0, 3),
        "max_ms": round(max(values), 3),
    }


def _resolve_path(value: str | None, default: Path) -> Path:
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _event_timestamp(event: dict[str, Any]) -> float:
    if event.get("timestamp_epoch_ms") is not None:
        try:
            return float(event["timestamp_epoch_ms"])
        except (TypeError, ValueError):
            pass
    if event.get("started_epoch") is not None:
        try:
            return float(event["started_epoch"]) * 1000.0
        except (TypeError, ValueError):
            pass
    return 0.0


def _event_duration(event: dict[str, Any]) -> float | None:
    try:
        return float(event.get("duration_ms"))
    except (TypeError, ValueError):
        return None


def _read_events(path: Path, route: str | None, phase: str | None) -> tuple[list[dict[str, Any]], int]:
    events: list[dict[str, Any]] = []
    malformed = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if event.get("event_type") != "phase_timing":
                continue
            if route and event.get("route") != route:
                continue
            if phase and event.get("phase") != phase:
                continue
            if _event_duration(event) is None:
                malformed += 1
                continue
            events.append(event)
    return events, malformed


def _aggregate(events: list[dict[str, Any]], key_fn) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for event in events:
        duration = _event_duration(event)
        if duration is None:
            continue
        key = key_fn(event)
        buckets[str(key if key not in (None, "") else "<missing>")].append(duration)
    return {key: _stats(values) for key, values in sorted(buckets.items())}


def _top_events(events: list[dict[str, Any]], top_n: int) -> list[dict[str, Any]]:
    ordered = sorted(events, key=lambda event: _event_duration(event) or 0.0, reverse=True)
    top: list[dict[str, Any]] = []
    for event in ordered[: max(0, top_n)]:
        top.append(
            {
                "route": event.get("route"),
                "phase": event.get("phase"),
                "alert_id": event.get("alert_id"),
                "decision_id": event.get("decision_id"),
                "attempt_index": event.get("attempt_index"),
                "duration_ms": round(float(event.get("duration_ms") or 0.0), 3),
                "status": event.get("status"),
            }
        )
    return top


def _waterfalls(events: list[dict[str, Any]], top_n: int) -> list[dict[str, Any]]:
    by_alert: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        alert_id = event.get("alert_id")
        if alert_id:
            by_alert[str(alert_id)].append(event)

    rows: list[dict[str, Any]] = []
    for alert_id, alert_events in by_alert.items():
        ordered = sorted(alert_events, key=_event_timestamp)
        total_observed = sum(float(event.get("duration_ms") or 0.0) for event in ordered)
        authoritative_total = max(
            (
                float(event.get("duration_ms") or 0.0)
                for event in ordered
                if event.get("phase") in {"analyze_request_total", "outcome_request_total", "total_attempt"}
            ),
            default=None,
        )
        rows.append(
            {
                "alert_id": alert_id,
                "event_count": len(ordered),
                "total_observed_ms": round(total_observed, 3),
                "authoritative_total_ms": round(authoritative_total, 3) if authoritative_total is not None else None,
                "phases": [
                    {
                        "route": event.get("route"),
                        "phase": event.get("phase"),
                        "duration_ms": round(float(event.get("duration_ms") or 0.0), 3),
                        "status": event.get("status"),
                    }
                    for event in ordered
                ],
            }
        )
    rows.sort(key=lambda row: row["authoritative_total_ms"] or row["total_observed_ms"], reverse=True)
    return rows[: max(0, top_n)]


def _windows(events: list[dict[str, Any]], window_size: int | None) -> list[dict[str, Any]]:
    if not window_size or window_size <= 0:
        return []
    with_attempts = []
    for event in events:
        attempt = event.get("attempt_index")
        if attempt is None:
            continue
        try:
            with_attempts.append((int(attempt), event))
        except (TypeError, ValueError):
            continue
    if not with_attempts:
        return []

    grouped: dict[tuple[int, int, str], list[float]] = defaultdict(list)
    for attempt, event in with_attempts:
        start = ((attempt - 1) // window_size) * window_size + 1
        end = start + window_size - 1
        duration = _event_duration(event)
        if duration is not None:
            grouped[(start, end, str(event.get("phase") or "<missing>"))].append(duration)

    rows: list[dict[str, Any]] = []
    for (start, end, phase), values in sorted(grouped.items()):
        rows.append(
            {
                "attempt_start": start,
                "attempt_end": end,
                "phase": phase,
                **_stats(values),
            }
        )
    return rows


def _table(rows: list[dict[str, Any]], columns: list[str], limit: int | None = None) -> str:
    selected = rows[:limit] if limit is not None else rows
    if not selected:
        return "(none)"
    widths = {column: len(column) for column in columns}
    for row in selected:
        for column in columns:
            widths[column] = max(widths[column], len(str(row.get(column, ""))))
    lines = [
        "  ".join(column.ljust(widths[column]) for column in columns),
        "  ".join("-" * widths[column] for column in columns),
    ]
    for row in selected:
        lines.append("  ".join(str(row.get(column, "")).ljust(widths[column]) for column in columns))
    return "\n".join(lines)


def _stats_rows(stats_by_key: dict[str, dict[str, Any]], key_name: str) -> list[dict[str, Any]]:
    return [
        {key_name: key, **stats}
        for key, stats in sorted(
            stats_by_key.items(),
            key=lambda item: (item[1].get("max_ms") or 0.0, item[1].get("avg_ms") or 0.0),
            reverse=True,
        )
    ]


def _markdown(payload: dict[str, Any]) -> str:
    top_events = payload["top_slow_events"]
    route_phase_rows = _stats_rows(payload["aggregates"]["route_phase"], "route_phase")
    phase_rows = _stats_rows(payload["aggregates"]["phase"], "phase")
    graph_rows = _stats_rows(payload["aggregates"]["graph_name"], "graph_name")
    window_rows = payload["windows"]
    waterfall_rows = payload["waterfalls"]
    lines = [
        f"# {payload['title']}",
        "",
        "## Safety",
        "- Read-only summary of existing JSONL trace events.",
        "- No backend, graph, proof, or seed operations are performed.",
        "- Nested phases are not additive; request-total phases are the authoritative route totals.",
        "",
        "## Input",
        f"- trace_jsonl: `{payload['trace_jsonl']}`",
        f"- events_loaded: {payload['events_loaded']}",
        f"- malformed_lines: {payload['malformed_lines']}",
        f"- route_filter: {payload.get('route_filter') or 'None'}",
        f"- phase_filter: {payload.get('phase_filter') or 'None'}",
        "",
        "## Route + Phase Aggregates",
        "```text",
        _table(route_phase_rows, ["route_phase", "count", "avg_ms", "p50_ms", "p95_ms", "p99_ms", "max_ms"], limit=40),
        "```",
        "",
        "## Phase Aggregates",
        "```text",
        _table(phase_rows, ["phase", "count", "avg_ms", "p50_ms", "p95_ms", "p99_ms", "max_ms"], limit=40),
        "```",
        "",
        "## Graph Aggregates",
        "```text",
        _table(graph_rows, ["graph_name", "count", "avg_ms", "p50_ms", "p95_ms", "p99_ms", "max_ms"], limit=40),
        "```",
        "",
        "## Top Slow Events",
        "```text",
        _table(top_events, ["duration_ms", "route", "phase", "alert_id", "decision_id", "attempt_index", "status"]),
        "```",
        "",
        "## Early/Mid/Late Windows",
        "```text",
        _table(window_rows, ["attempt_start", "attempt_end", "phase", "count", "avg_ms", "max_ms"], limit=80),
        "```",
        "",
        "## Per-Alert Waterfall",
    ]
    if not waterfall_rows:
        lines.append("(none)")
    for row in waterfall_rows:
        lines.extend(
            [
                "",
                f"### {row['alert_id']}",
                f"- event_count: {row['event_count']}",
                f"- total_observed_ms: {row['total_observed_ms']}",
                f"- authoritative_total_ms: {row['authoritative_total_ms']}",
                "```text",
                _table(row["phases"], ["duration_ms", "route", "phase", "status"]),
                "```",
            ]
        )
    lines.extend(
        [
            "",
            "## Nested Phase Warning",
            payload["nested_phase_warning"],
            "",
        ]
    )
    return "\n".join(lines)


def build_summary(args: argparse.Namespace) -> tuple[dict[str, Any], Path, Path]:
    trace_path = _resolve_path(args.trace_jsonl, DEFAULT_TRACE)
    if not trace_path.exists():
        raise FileNotFoundError(f"Trace JSONL not found: {trace_path}")
    events, malformed = _read_events(trace_path, args.route, args.phase)
    aggregates = {
        "route": _aggregate(events, lambda event: event.get("route")),
        "phase": _aggregate(events, lambda event: event.get("phase")),
        "route_phase": _aggregate(events, lambda event: f"{event.get('route') or '<missing>'} | {event.get('phase') or '<missing>'}"),
        "graph_name": _aggregate(events, lambda event: event.get("graph_name")),
    }
    report_name = trace_path.stem.replace("soc_perf_trace_", "soc_perf_trace_summary_")
    default_json = DEFAULT_REPORT_DIR / f"{report_name}.json"
    default_md = DEFAULT_REPORT_DIR / f"{report_name}.md"
    json_path = _resolve_path(args.output_json, default_json) if args.output_json else default_json
    md_path = _resolve_path(args.output_md, default_md) if args.output_md else default_md
    payload = {
        "title": "SOC Perf Trace Summary",
        "trace_jsonl": str(trace_path),
        "events_loaded": len(events),
        "malformed_lines": malformed,
        "route_filter": args.route,
        "phase_filter": args.phase,
        "top_n": args.top_n,
        "window_size": args.window_size,
        "aggregates": aggregates,
        "top_slow_events": _top_events(events, args.top_n),
        "waterfalls": _waterfalls(events, args.top_n),
        "windows": _windows(events, args.window_size),
        "nested_phase_warning": (
            "Nested phase durations should not be summed blindly. "
            "Use analyze_request_total, outcome_request_total, or total_attempt as authoritative totals."
        ),
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_markdown(payload), encoding="utf-8")
    return payload, json_path, md_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize SOC perf JSONL trace events.")
    parser.add_argument("--trace-jsonl", default=str(DEFAULT_TRACE), help="Trace JSONL path.")
    parser.add_argument("--output-json", default=None, help="Optional JSON report path.")
    parser.add_argument("--output-md", default=None, help="Optional Markdown report path.")
    parser.add_argument("--top-n", type=int, default=20, help="Number of slow events and waterfalls to include.")
    parser.add_argument("--window-size", type=int, default=25, help="Attempt window size for early/mid/late summaries.")
    parser.add_argument("--route", default=None, help="Optional route filter, e.g. /api/alert/analyze.")
    parser.add_argument("--phase", default=None, help="Optional phase filter.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload, json_path, md_path = build_summary(args)
    print("SOC Perf Trace Summary", flush=True)
    print(f"trace_jsonl: {payload['trace_jsonl']}", flush=True)
    print(f"events_loaded: {payload['events_loaded']}", flush=True)
    print(f"malformed_lines: {payload['malformed_lines']}", flush=True)
    print("", flush=True)
    route_phase_rows = _stats_rows(payload["aggregates"]["route_phase"], "route_phase")
    print(_table(route_phase_rows, ["route_phase", "count", "avg_ms", "p50_ms", "p95_ms", "p99_ms", "max_ms"], limit=20), flush=True)
    print("", flush=True)
    print("Top slow events", flush=True)
    print(_table(payload["top_slow_events"], ["duration_ms", "route", "phase", "alert_id", "decision_id", "attempt_index", "status"]), flush=True)
    print("", flush=True)
    print(payload["nested_phase_warning"], flush=True)
    print(f"json_report: {json_path}", flush=True)
    print(f"md_report: {md_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
