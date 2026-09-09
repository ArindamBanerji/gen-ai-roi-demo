"""Generate label-stripped SOC score-keyed alerts for VLD rho measurement."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

DEFAULT_FIXTURE = Path("support/setup/zero_day_decisions_v5.json")
DEFAULT_OUTPUT = Path("data/score_keyed_alerts.json")
DEFAULT_TRUTH = Path("data/score_keyed_truth.json")
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LEAK_FIELDS = {"category", "alert_type", "category_index"}


def _alerts_from_fixture(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [dict(item) for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        alerts = payload.get("alerts", [])
        return [dict(item) for item in alerts if isinstance(item, dict)]
    return []


def strip_alert(alert: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    truth = alert.get("category") or alert.get("alert_type")
    stripped = {key: value for key, value in alert.items() if key not in LEAK_FIELDS}
    return stripped, str(truth) if truth is not None else None


def generate_score_keyed_alerts(
    fixture_path: str | Path = DEFAULT_FIXTURE,
    output_path: str | Path = DEFAULT_OUTPUT,
    truth_path: str | Path = DEFAULT_TRUTH,
) -> dict[str, Any]:
    fixture = Path(fixture_path)
    output = Path(output_path)
    truth_file = Path(truth_path)
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    alerts = _alerts_from_fixture(payload)
    stripped_alerts: list[dict[str, Any]] = []
    truth: dict[str, str] = {}
    for alert in alerts:
        stripped, label = strip_alert(alert)
        alert_id = str(stripped.get("alert_id") or stripped.get("id") or "")
        if not alert_id:
            continue
        stripped_alerts.append(stripped)
        if label is not None:
            truth[alert_id] = label
    output.parent.mkdir(parents=True, exist_ok=True)
    truth_file.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(stripped_alerts, indent=2, sort_keys=True), encoding="utf-8")
    truth_file.write_text(json.dumps(truth, indent=2, sort_keys=True), encoding="utf-8")
    leaks = [alert.get("alert_id") or alert.get("id") for alert in stripped_alerts if any(field in alert for field in LEAK_FIELDS)]
    if leaks:
        raise AssertionError(f"category leakage in stripped alerts: {leaks[:5]}")
    return {
        "fixture": str(fixture),
        "output": str(output),
        "truth": str(truth_file),
        "alerts": len(stripped_alerts),
        "truth_labels": len(truth),
        "leak_fields": sorted(LEAK_FIELDS),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--truth", default=str(DEFAULT_TRUTH))
    args = parser.parse_args()
    summary = generate_score_keyed_alerts(args.fixture, args.output, args.truth)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
