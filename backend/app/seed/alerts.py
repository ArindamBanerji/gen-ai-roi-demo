from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from app.domains.soc.config import ALERT_TYPE_CATEGORY_MAP, SOC_CATEGORIES
from app.seed.config import SeedConfig

SEVERITIES = ("low", "medium", "high", "critical")
SOURCE_LOCATIONS = (
    "synthetic",
    "10.0.1.54",
    "172.16.4.21",
    "192.168.10.42",
    "corp-network",
)


def category_to_alert_types() -> dict[str, list[str]]:
    grouped = {cat: [] for cat in SOC_CATEGORIES}
    for alert_type, category in ALERT_TYPE_CATEGORY_MAP.items():
        if category in grouped:
            grouped[category].append(alert_type)
    missing = [cat for cat, types in grouped.items() if not types]
    if missing:
        raise ValueError(f"No mapped alert types for categories: {missing}")
    return {cat: sorted(types) for cat, types in grouped.items()}


def _weighted_categories(config: SeedConfig, count: int) -> list[str]:
    if count <= 0:
        return []
    categories = list(SOC_CATEGORIES)
    raw_counts = {
        cat: int(count * float(config.category_weights[cat]))
        for cat in categories
    }
    for cat in categories[: min(len(categories), count)]:
        raw_counts[cat] = max(raw_counts[cat], 1)

    assigned = sum(raw_counts.values())
    ranked = sorted(
        categories,
        key=lambda c: float(config.category_weights[c]),
        reverse=True,
    )
    while assigned < count:
        raw_counts[ranked[assigned % len(ranked)]] += 1
        assigned += 1
    while assigned > count:
        for cat in reversed(ranked):
            if raw_counts[cat] > 1:
                raw_counts[cat] -= 1
                assigned -= 1
                break
        else:
            break

    result: list[str] = []
    for cat in categories:
        result.extend([cat] * raw_counts[cat])
    return result[:count]


def _balanced_categories(count: int) -> list[str]:
    if count <= 0:
        return []
    categories = list(SOC_CATEGORIES)
    base = count // len(categories)
    remainder = count % len(categories)
    result: list[str] = []
    for idx, category in enumerate(categories):
        result.extend([category] * (base + (1 if idx < remainder else 0)))
    return result[:count]


def _iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()


def _pattern_for_category(
    category: str,
    attack_patterns: list[dict[str, Any]],
    index: int,
) -> str:
    matching = [p["pattern_id"] for p in attack_patterns if p.get("category") == category]
    if matching:
        return matching[index % len(matching)]
    return attack_patterns[index % len(attack_patterns)]["pattern_id"] if attack_patterns else ""


def _indicator_ids(
    indicators: list[dict[str, Any]],
    rng: random.Random,
    max_count: int = 2,
) -> list[str]:
    if not indicators:
        return []
    count = rng.randint(0, min(max_count, len(indicators)))
    if count == 0:
        return []
    return [i["indicator"] for i in rng.sample(indicators, count)]


def generate_alerts(
    config: SeedConfig,
    users: list[dict[str, Any]],
    assets: list[dict[str, Any]],
    attack_patterns: list[dict[str, Any]],
    threat_indicators: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng = random.Random(config.seed)
    types_by_category = category_to_alert_types()

    training_categories = _weighted_categories(
        config,
        config.n_training_alerts if config.include_training_alerts else 0,
    )
    demo_categories = _balanced_categories(
        config.n_demo_alerts if config.include_demo_alerts else 0,
    )
    rng.shuffle(training_categories)
    rng.shuffle(demo_categories)

    training: list[dict[str, Any]] = []
    for i, category in enumerate(training_categories):
        user = users[i % len(users)]
        asset = assets[(i * 3 + 1) % len(assets)]
        alert_type = rng.choice(types_by_category[category])
        ts = config.base_epoch_ms + i * 60 * 60 * 1000
        training.append({
            "alert_id": f"SYN-{_category_code(category)}-D{i + 1:03d}-001",
            "category": ALERT_TYPE_CATEGORY_MAP[alert_type],
            "severity": SEVERITIES[(i + rng.randint(0, 3)) % len(SEVERITIES)],
            "alert_type": alert_type,
            "timestamp_epoch": ts,
            "origin": config.training_origin,
            "source_location": SOURCE_LOCATIONS[i % len(SOURCE_LOCATIONS)],
            "user_id": user["user_id"],
            "status": config.training_status,
            "asset_id": asset["asset_id"],
            "attack_pattern_id": _pattern_for_category(category, attack_patterns, i),
            "indicator_ids": _indicator_ids(threat_indicators, rng),
            "provenance": "sample",
        })
    _apply_jdoe_storyline(config, training, users, assets, attack_patterns, threat_indicators)

    demo: list[dict[str, Any]] = []
    for i, category in enumerate(demo_categories):
        user = users[(i * 2 + 3) % len(users)]
        asset = assets[(i * 5) % len(assets)]
        alert_type = rng.choice(types_by_category[category])
        ts = config.demo_base_epoch_ms + i * 15 * 60 * 1000
        demo.append({
            "alert_id": f"ALERT-{_category_code(category)}-{i + 1:03d}",
            "category": ALERT_TYPE_CATEGORY_MAP[alert_type],
            "severity": SEVERITIES[(i + 1) % len(SEVERITIES)],
            "alert_type": alert_type,
            "timestamp_epoch": ts,
            "origin": config.demo_origin,
            "source_location": SOURCE_LOCATIONS[(i + 1) % len(SOURCE_LOCATIONS)],
            "user_id": user["user_id"],
            "asset_id": asset["asset_id"],
            "user_name": user.get("name", user["user_id"]),
            "asset_hostname": asset.get("hostname", asset["asset_id"]),
            "attack_pattern_id": _pattern_for_category(category, attack_patterns, i),
            "indicator_ids": _indicator_ids(threat_indicators, rng, max_count=1),
            "status": config.demo_status,
            "provenance": "sample",
        })

    return training, demo


def _category_code(category: str) -> str:
    return "".join(part[0] for part in category.split("_")).upper()


def _apply_jdoe_storyline(
    config: SeedConfig,
    alerts: list[dict[str, Any]],
    users: list[dict[str, Any]],
    assets: list[dict[str, Any]],
    attack_patterns: list[dict[str, Any]],
    threat_indicators: list[dict[str, Any]],
) -> None:
    if len(alerts) < 3:
        return
    user_ids = {user.get("user_id") for user in users}
    asset_ids = {asset.get("asset_id") for asset in assets}
    indicator_ids = {indicator.get("indicator") for indicator in threat_indicators}
    if "jdoe" not in user_ids or "DC-PROD-07" not in asset_ids:
        return
    if "CISA-AA-2026-0419" not in indicator_ids:
        return

    storyline = [
        ("ALT-JDOE-001", "credential_access", "credential_stuffing", "T1078", 0.35, "103.253.40.10"),
        ("ALT-JDOE-002", "lateral_movement", "privilege_escalation", "T1021", 0.55, "103.253.41.22"),
        ("ALT-JDOE-003", "credential_access", "anomalous_login", "T1110", 0.78, "103.253.42.33"),
    ]
    for index, (alert_id, category, alert_type, pattern_id, history, source_location) in enumerate(storyline):
        ts = config.base_epoch_ms + index * 6 * 60 * 60 * 1000
        selected_pattern_id = _storyline_pattern_for_category(
            category,
            pattern_id,
            attack_patterns,
            index,
        )
        alerts[index].update({
            "alert_id": alert_id,
            "category": category,
            "severity": "high" if index < 2 else "critical",
            "alert_type": alert_type,
            "timestamp_epoch": ts,
            "timestamp": _iso(ts),
            "origin": config.training_origin,
            "source_location": source_location,
            "user_id": "jdoe",
            "status": config.training_status,
            "asset_id": "DC-PROD-07",
            "attack_pattern_id": selected_pattern_id,
            "indicator_ids": ["CISA-AA-2026-0419"],
            "factors": {
                "pattern_history": history,
            },
            "ti_match": {
                "advisory": "CISA-AA-2026-0419",
                "ip_ranges": ["103.253.40.0/22"],
            },
        })


def _storyline_pattern_for_category(
    category: str,
    preferred_pattern_id: str,
    attack_patterns: list[dict[str, Any]],
    index: int,
) -> str:
    pattern_ids = {pattern.get("pattern_id") for pattern in attack_patterns}
    if preferred_pattern_id in pattern_ids:
        return preferred_pattern_id
    return _pattern_for_category(category, attack_patterns, index)
