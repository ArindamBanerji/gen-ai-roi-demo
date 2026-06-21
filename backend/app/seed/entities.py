from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from app.seed.config import SeedConfig

DEFAULT_SEED_PATH = (
    Path(__file__).resolve().parents[2]
    / "support"
    / "setup"
    / "zero_day_decisions_v5.json"
)

T1537_TEMPLATE = {
    "pattern_id": "T1537",
    "name": "Transfer Data to Cloud Account",
    "mitre_id": "T1537",
    "tactic": "Exfiltration",
    "category": "data_exfiltration",
    "origin": "zero_day_synthetic",
}


@dataclass(frozen=True)
class EntityTemplates:
    users: list[dict[str, Any]]
    assets: list[dict[str, Any]]
    attack_patterns: list[dict[str, Any]]
    threat_indicators: list[dict[str, Any]]
    campaigns: list[dict[str, Any]]
    existing_alerts: list[dict[str, Any]]
    existing_demo_alerts: list[dict[str, Any]]


def load_existing_seed(path: Path | str = DEFAULT_SEED_PATH) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return cast(dict[str, Any], json.load(fh))


def load_curated_templates(data: dict[str, Any] | None = None) -> EntityTemplates:
    source = data if data is not None else load_existing_seed()
    return EntityTemplates(
        users=copy.deepcopy(source.get("users", [])),
        assets=copy.deepcopy(source.get("assets", [])),
        attack_patterns=copy.deepcopy(source.get("attack_patterns", [])),
        threat_indicators=copy.deepcopy(source.get("threat_indicators", [])),
        campaigns=copy.deepcopy(source.get("campaigns", [])),
        existing_alerts=copy.deepcopy(source.get("alerts", [])),
        existing_demo_alerts=copy.deepcopy(source.get("demo_alerts", [])),
    )


def _cycle_records(
    records: list[dict[str, Any]],
    count: int,
    id_field: str,
    prefix: str,
) -> list[dict[str, Any]]:
    if count == 0:
        return []
    if not records:
        raise ValueError(f"Cannot generate {count} {id_field} records without templates")

    generated: list[dict[str, Any]] = []
    for i in range(count):
        item = copy.deepcopy(records[i % len(records)])
        if i >= len(records):
            item[id_field] = f"{prefix}-{i + 1:03d}"
            if "name" in item:
                item["name"] = f"{item['name']} {i + 1}"
            if "hostname" in item:
                item["hostname"] = f"{prefix.lower()}-{i + 1:03d}.corp.local"
        generated.append(item)
    return generated


def generate_users(config: SeedConfig, templates: EntityTemplates) -> list[dict[str, Any]]:
    return _cycle_records(templates.users, config.n_users, "user_id", "USR")


def generate_assets(config: SeedConfig, templates: EntityTemplates) -> list[dict[str, Any]]:
    return _cycle_records(templates.assets, config.n_assets, "asset_id", "AST")


def generate_threat_indicators(
    config: SeedConfig,
    templates: EntityTemplates,
) -> list[dict[str, Any]]:
    return _cycle_records(
        templates.threat_indicators,
        config.n_threat_indicators,
        "indicator",
        "IOC",
    )


def generate_attack_patterns(
    config: SeedConfig,
    templates: EntityTemplates,
) -> list[dict[str, Any]]:
    records = _cycle_records(
        templates.attack_patterns,
        config.n_attack_patterns,
        "pattern_id",
        "TGEN",
    )
    pattern_ids = {p.get("pattern_id") for p in records}
    referenced = {
        a.get("attack_pattern_id")
        for a in templates.existing_alerts + templates.existing_demo_alerts
        if a.get("attack_pattern_id")
    }
    if "T1537" in referenced and "T1537" not in pattern_ids:
        records.append(copy.deepcopy(T1537_TEMPLATE))
    return records


def generate_entities(
    config: SeedConfig,
    templates: EntityTemplates | None = None,
) -> dict[str, list[dict[str, Any]]]:
    source = templates or load_curated_templates()
    users = generate_users(config, source)
    assets = generate_assets(config, source)
    attack_patterns = generate_attack_patterns(config, source)
    threat_indicators = generate_threat_indicators(config, source)
    campaigns = _cycle_records(
        source.campaigns,
        config.n_campaigns,
        "campaign_id",
        "CAMP",
    )
    return {
        "users": users,
        "assets": assets,
        "attack_patterns": attack_patterns,
        "threat_indicators": threat_indicators,
        "campaigns": campaigns,
    }
