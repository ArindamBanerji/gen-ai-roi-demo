from __future__ import annotations

import copy
from typing import Any

from app.seed.config import SeedConfig


def generate_campaigns(
    config: SeedConfig,
    templates: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if config.n_campaigns == 0:
        return []
    if not templates:
        raise ValueError("Cannot generate campaigns without templates")

    campaigns: list[dict[str, Any]] = []
    alert_count = len(alerts)
    chunk_size = max(1, alert_count // max(config.n_campaigns, 1))
    for i in range(config.n_campaigns):
        item = copy.deepcopy(templates[i % len(templates)])
        item["campaign_id"] = item.get("campaign_id") if i < len(templates) else f"CAMP-{i + 1:03d}"
        members = alerts[i * chunk_size : (i + 1) * chunk_size][: max(1, min(12, chunk_size))]
        if not members and alerts:
            members = [alerts[i % alert_count]]
        member_ids = [a["alert_id"] for a in members]
        item["member_alert_ids"] = member_ids
        item["alert_ids"] = list(member_ids)
        item["alert_count"] = len(member_ids)
        if members:
            timestamps = [int(a["timestamp_epoch"]) for a in members]
            item["first_seen"] = min(timestamps)
            item["last_seen"] = max(timestamps)
            item["category_sequence"] = [a["category"] for a in members]
        item.setdefault("origin", config.training_origin)
        item.setdefault("shared_entities", [])
        item.setdefault("technique_sequence", [])
        item.setdefault("correlation_window_hours", 24)
        campaigns.append(item)
    return campaigns
