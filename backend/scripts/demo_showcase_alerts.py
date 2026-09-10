"""Generate the four SOC multi-hop showcase alerts for the VLD panel."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.multihop_scenarios import SHOWCASE_SCENARIO_IDS, scenario_by_id, run_stage1_investigation

OUTPUT_PATH = ROOT / "data" / "demo_showcase_alerts.json"


def _trace_summary(result: Any) -> list[dict[str, Any]]:
    return [
        {
            "step": step.step,
            "pattern": step.pattern,
            "evidence_keys": step.evidence_keys,
            "selected_edge": step.selected_edge,
            "halt_reason": step.halt_reason,
        }
        for step in result.trace
    ]


async def build_showcase_payload() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    stories = {
        "SOC-MH-002-v1": "Insider vs compromised: employment context plus peer baseline explains escalation.",
        "SOC-MH-004-v1": "Maintenance window: approved change context suppresses a noisy drift alert.",
        "SOC-MH-005-v1": "Privilege chain: nested group traversal exposes delegated admin rights.",
        "SOC-MH-003-v1": "Campaign correlation: moderate alerts become a campaign-level escalation.",
    }
    for scenario_id in SHOWCASE_SCENARIO_IDS:
        scenario = scenario_by_id(scenario_id)
        if scenario is None:
            continue
        result = await run_stage1_investigation(scenario)
        alert = dict(scenario.get("alert", {}))
        items.append(
            {
                "scenario_id": scenario_id,
                "alert_id": alert.get("alert_id"),
                "scenario_type": scenario.get("scenario_type"),
                "story": stories.get(scenario_id, scenario.get("description")),
                "expected_action": result.action,
                "expected_category": result.category,
                "expected_steps": result.steps,
                "trace": _trace_summary(result),
            }
        )
    return {"showcases": items}


def main() -> int:
    payload = asyncio.run(build_showcase_payload())
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    for item in payload["showcases"]:
        print(f"{item['scenario_id']} {item['alert_id']}: {item['expected_steps']} steps -> {item['expected_action']}")
    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
