from __future__ import annotations

from typing import Any

from app.seed.alerts import generate_alerts
from app.seed.campaigns import generate_campaigns
from app.seed.config import SeedConfig
from app.seed.decisions import generate_decisions
from app.seed.entities import generate_entities, load_curated_templates
from app.seed.metadata import derive_metadata
from app.seed.validate import validate_seed


def generate_seed(config: SeedConfig | None = None) -> dict[str, Any]:
    seed_config = config or SeedConfig()
    templates = load_curated_templates()
    entities = generate_entities(seed_config, templates)
    alerts, demo_alerts = generate_alerts(
        seed_config,
        entities["users"],
        entities["assets"],
        entities["attack_patterns"],
        entities["threat_indicators"],
    )
    campaigns = generate_campaigns(seed_config, entities["campaigns"], alerts)
    decisions = generate_decisions(seed_config, alerts)
    data: dict[str, Any] = {
        "metadata": {},
        "users": entities["users"],
        "assets": entities["assets"],
        "attack_patterns": entities["attack_patterns"],
        "threat_indicators": entities["threat_indicators"],
        "campaigns": campaigns,
        "alerts": alerts,
        "demo_alerts": demo_alerts,
        "decisions": decisions,
    }
    data["metadata"] = derive_metadata(data, seed_config)
    result = validate_seed(data)
    if result.errors:
        raise ValueError("Generated seed failed validation:\n  " + "\n  ".join(result.errors[:20]))
    return data
