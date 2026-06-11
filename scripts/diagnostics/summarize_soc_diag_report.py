from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def load_report(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        raise SystemExit(2)
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON in {path}: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except OSError as exc:
        print(f"ERROR: cannot read {path}: {exc}", file=sys.stderr)
        raise SystemExit(2)

    if not isinstance(payload, dict):
        print("ERROR: unsupported report shape: top-level JSON is not an object", file=sys.stderr)
        raise SystemExit(3)
    return payload


def extract_result(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("result"), dict):
        result = dict(payload["result"])
        result.setdefault("report_json_path", payload.get("json_report"))
        result.setdefault("report_md_path", payload.get("md_report"))
        return result
    if "verdict" in payload or "readback" in payload or "loops" in payload:
        return payload

    print("ERROR: unsupported report shape: expected direct result or {'result': {...}}", file=sys.stderr)
    raise SystemExit(3)


def first_count(value: Any) -> Any:
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return first.get("cnt", first.get("count", first.get("n", first)))
    if isinstance(value, dict):
        return value.get("cnt", value.get("count", value.get("n", value)))
    return value


def max_n_decisions_used(rows: Any) -> Any:
    if not isinstance(rows, list):
        return None
    values: list[int] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw = row.get("n_decisions_used")
        try:
            values.append(int(raw))
        except (TypeError, ValueError):
            continue
    return max(values) if values else None


def fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def kv_line(label: str, value: Any) -> str:
    return f"{label}: {fmt(value)}"


def top_loops(loops: Any, field: str, limit: int = 3) -> list[dict[str, Any]]:
    if not isinstance(loops, list):
        return []

    def score(row: Any) -> float:
        if not isinstance(row, dict):
            return float("-inf")
        value = row.get(field)
        try:
            return float(value)
        except (TypeError, ValueError):
            return float("-inf")

    rows = [row for row in loops if isinstance(row, dict) and score(row) != float("-inf")]
    return sorted(rows, key=score, reverse=True)[:limit]


def append_loop_table(lines: list[str], title: str, rows: list[dict[str, Any]]) -> None:
    lines.append("")
    lines.append(title)
    if not rows:
        lines.append("- none")
        return
    lines.append("alert_id | action | confidence | analyze_seconds | outcome_seconds")
    for row in rows:
        lines.append(
            " | ".join([
                fmt(row.get("alert_id")),
                fmt(row.get("action")),
                fmt(row.get("confidence")),
                fmt(row.get("analyze_seconds")),
                fmt(row.get("outcome_seconds")),
            ])
        )


def build_summary_lines(
    result: dict[str, Any],
    json_report: str | Path | None = None,
    md_report: str | Path | None = None,
) -> list[str]:
    result = dict(result)
    if json_report is not None:
        result["report_json_path"] = str(json_report)
    if md_report is not None:
        result["report_md_path"] = str(md_report)
    readback = result.get("readback") if isinstance(result.get("readback"), dict) else {}
    contract = result.get("backend_contract") if isinstance(result.get("backend_contract"), dict) else {}
    criteria_failures = result.get("criteria_failures")

    lines = [
        "SOC Diagnostic Summary",
        kv_line("verdict", result.get("verdict")),
        kv_line("proof_passed", result.get("proof_passed")),
        kv_line("graph_name", result.get("graph_name")),
        kv_line("backend_url", result.get("backend_url")),
        kv_line("prefix", result.get("prefix")),
        kv_line("valid_outcomes", result.get("valid_outcomes")),
        kv_line("analyze_attempts", result.get("analyze_attempts")),
        kv_line("outcome_attempts", result.get("outcome_attempts")),
        kv_line("seed_failures", result.get("seed_failures")),
        kv_line("seed_visibility_status", result.get("seed_visibility_status")),
        "",
        "Timing",
    ]
    for key in (
        "avg_analyze_seconds",
        "max_analyze_seconds",
        "avg_outcome_seconds",
        "max_outcome_seconds",
        "avg_seed_seconds",
        "max_seed_seconds",
    ):
        if key in result:
            lines.append(kv_line(key, result.get(key)))

    lines.extend([
        "",
        "Readback",
        kv_line("decisions", first_count(readback.get("decisions"))),
        kv_line("verified", first_count(readback.get("verified"))),
        kv_line("outcome_present", first_count(readback.get("outcome_present"))),
        kv_line("l5_centroid", first_count(readback.get("l5_centroid"))),
        kv_line("shaped_by", first_count(readback.get("shaped_by"))),
        kv_line("l5_dk_weight", first_count(readback.get("l5_dk_weight"))),
    ])
    dk_rows = readback.get("dk_welford_rows")
    lines.append(kv_line("dk_welford_rows", len(dk_rows) if isinstance(dk_rows, list) else first_count(dk_rows)))
    lines.append(kv_line("max_n_decisions_used", max_n_decisions_used(dk_rows)))

    lines.extend(["", "Backend Contract"])
    for key in (
        "mode",
        "graph_name",
        "backend_port",
        "age_use_pool_requested",
        "connection_mode",
        "pool_available",
    ):
        if key in contract:
            lines.append(kv_line(key, contract.get(key)))

    lines.extend(["", "Criteria Failures"])
    if criteria_failures:
        for item in criteria_failures:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    append_loop_table(lines, "Top Analyze Loops", top_loops(result.get("loops"), "analyze_seconds"))
    append_loop_table(lines, "Top Outcome Loops", top_loops(result.get("loops"), "outcome_seconds"))

    lines.extend([
        "",
        "Reports",
        kv_line("report_json_path", result.get("report_json_path")),
        kv_line("report_md_path", result.get("report_md_path")),
    ])
    return lines


def print_summary(
    result: dict[str, Any],
    json_report: str | Path | None = None,
    md_report: str | Path | None = None,
) -> None:
    print("\n".join(build_summary_lines(result, json_report=json_report, md_report=md_report)), flush=True)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: summarize_soc_diag_report.py <soc_diag_report.json>", file=sys.stderr)
        return 2
    result = extract_result(load_report(Path(argv[1])))
    print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
