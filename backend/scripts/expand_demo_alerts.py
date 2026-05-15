"""Expand zero-day demo alerts deterministically.

Run from the backend directory:
    python scripts/expand_demo_alerts.py
"""

from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DATA_PATH = Path("support/setup/zero_day_decisions_v5.json")
TARGET_PER_CATEGORY = 17
BASE_EPOCH = 1_714_521_600
TIMESTAMP_STEP = 25_920
RNG_SEED = 42

CATEGORY_META = {
    "credential_access": {
        "code": "CA",
        "alert_type": "anomalous_login",
        "attack_pattern_id": "T1078",
    },
    "lateral_movement": {
        "code": "LM",
        "alert_type": "privilege_escalation",
        "attack_pattern_id": "T1021",
    },
    "data_exfiltration": {
        "code": "DE",
        "alert_type": "data_exfil",
        "attack_pattern_id": "T1048",
    },
    "malware_execution": {
        "code": "ME",
        "alert_type": "threat_intel_match",
        "attack_pattern_id": "T1588",
    },
    "insider_threat": {
        "code": "IT",
        "alert_type": "insider_threat",
        "attack_pattern_id": "T1078.004",
    },
    "cloud_infrastructure": {
        "code": "CI",
        "alert_type": "cloud_iam_privilege_escalation",
        "attack_pattern_id": "T1537",
    },
}

SEVERITY_TARGET = {
    "critical": 2,
    "high": 4,
    "medium": 7,
    "low": 4,
}

SOURCE_LOCATIONS = [
    "10.0.1.54",
    "vpn-gw.corp.local",
    "10.4.8.12",
    "cloudtrail.amazonaws.com",
    "okta-prod.corp.local",
    "172.16.22.41",
    "m365-defender",
    "edr-sensor-07",
]


def _ordered_alert(raw: dict[str, Any], schema_keys: list[str]) -> dict[str, Any]:
    return {key: raw[key] for key in schema_keys}


def _existing_number(alert_id: str, code: str) -> int | None:
    prefix = f"ALERT-{code}-"
    if not alert_id.startswith(prefix):
        return None
    suffix = alert_id[len(prefix) :]
    return int(suffix) if suffix.isdigit() else None


def _severity_plan(existing: list[dict[str, Any]], needed: int) -> list[str]:
    current = Counter(str(alert.get("severity", "")).lower() for alert in existing)
    plan: list[str] = []
    for severity, target in SEVERITY_TARGET.items():
        plan.extend([severity] * max(0, target - current[severity]))
    if len(plan) < needed:
        cycle = ["medium", "low", "high", "critical"]
        for i in range(needed - len(plan)):
            plan.append(cycle[i % len(cycle)])
    return plan[:needed]


def _next_alert_id(existing_ids: set[str], code: str, start_at: int) -> tuple[str, int]:
    number = start_at
    while True:
        alert_id = f"ALERT-{code}-{number:03d}"
        if alert_id not in existing_ids:
            return alert_id, number + 1
        number += 1


def _expand(data: dict[str, Any]) -> tuple[int, int, Counter[str]]:
    alerts = data.get("demo_alerts", [])
    if not alerts:
        raise ValueError("demo_alerts is empty")

    schema_keys = list(alerts[0].keys())
    users = sorted(data.get("users", []), key=lambda item: str(item.get("user_id", "")))
    assets = sorted(data.get("assets", []), key=lambda item: str(item.get("asset_id", "")))
    if not users:
        raise ValueError("users is empty")
    if not assets:
        raise ValueError("assets is empty")

    rng = random.Random(RNG_SEED)
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for alert in alerts:
        by_category[str(alert.get("category"))].append(alert)

    existing_ids = {str(alert.get("alert_id")) for alert in alerts}
    before = len(alerts)
    generated_index = 0

    for category, meta in CATEGORY_META.items():
        existing = by_category.get(category, [])
        if len(existing) >= TARGET_PER_CATEGORY:
            continue
        if not existing:
            raise ValueError(f"no template alert exists for category {category}")

        needed = TARGET_PER_CATEGORY - len(existing)
        severities = _severity_plan(existing, needed)
        code = meta["code"]
        existing_numbers = [
            number
            for alert in existing
            for number in [_existing_number(str(alert.get("alert_id", "")), code)]
            if number is not None
        ]
        next_number = max(existing_numbers, default=0) + 1

        for offset in range(needed):
            template = dict(existing[offset % len(existing)])
            user = users[(generated_index + offset) % len(users)]
            asset = assets[(generated_index * 3 + offset) % len(assets)]
            alert_id, next_number = _next_alert_id(existing_ids, code, next_number)
            existing_ids.add(alert_id)

            raw = dict(template)
            raw.update(
                {
                    "alert_id": alert_id,
                    "category": category,
                    "severity": severities[offset],
                    "alert_type": meta["alert_type"],
                    "timestamp_epoch": BASE_EPOCH + generated_index * TIMESTAMP_STEP,
                    "origin": "zero_day_demo",
                    "source_location": SOURCE_LOCATIONS[
                        rng.randrange(len(SOURCE_LOCATIONS))
                    ],
                    "user_id": user["user_id"],
                    "asset_id": asset["asset_id"],
                    "user_name": user.get("name", user["user_id"]),
                    "asset_hostname": asset.get("hostname", asset["asset_id"]),
                    "attack_pattern_id": meta["attack_pattern_id"],
                    "status": "pending",
                }
            )
            if not isinstance(raw.get("indicator_ids"), list):
                raw["indicator_ids"] = []

            alert = _ordered_alert(raw, schema_keys)
            alerts.append(alert)
            by_category[category].append(alert)
            generated_index += 1

    return before, len(alerts), Counter(alert["category"] for alert in alerts)


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    before, after, categories = _expand(data)
    if after != before:
        DATA_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    severities = Counter(alert["severity"] for alert in data["demo_alerts"])
    print(f"before: {before}")
    print(f"after: {after}")
    print(f"added: {after - before}")
    print(f"categories: {dict(sorted(categories.items()))}")
    print(f"severities: {dict(sorted(severities.items()))}")


if __name__ == "__main__":
    main()
