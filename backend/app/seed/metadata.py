from __future__ import annotations

from collections import Counter
import hashlib
import json
from typing import Any

from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES
from app.seed.config import SeedConfig


def compute_seed_hash(data: dict[str, Any]) -> str:
    payload = {key: value for key, value in data.items() if key != "metadata"}
    serialized = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def derive_metadata(data: dict[str, Any], config: SeedConfig) -> dict[str, Any]:
    decisions = data.get("decisions", [])
    correct_by_cat: Counter[str] = Counter()
    total_by_cat: Counter[str] = Counter()
    for decision in decisions:
        cat = decision.get("category")
        if cat:
            total_by_cat[cat] += 1
            if decision.get("correct") is True:
                correct_by_cat[cat] += 1

    p_correct_by_cat = {
        cat: round(correct_by_cat[cat] / total_by_cat[cat], 3)
        if total_by_cat[cat]
        else 0.0
        for cat in SOC_CATEGORIES
    }
    total_decisions = len(decisions)
    correct = sum(1 for d in decisions if d.get("correct") is True)
    return {
        "generator": "deterministic_seed_generator",
        "version": "6.0",
        "based_on": "zero_day_decisions_v5.json",
        "total_alerts": len(data.get("alerts", [])),
        "total_demo_alerts": len(data.get("demo_alerts", [])),
        "total_decisions": total_decisions,
        "total_users": len(data.get("users", [])),
        "total_assets": len(data.get("assets", [])),
        "total_attack_patterns": len(data.get("attack_patterns", [])),
        "total_threat_indicators": len(data.get("threat_indicators", [])),
        "total_campaigns": len(data.get("campaigns", [])),
        "days_simulated": config.time_range_days,
        "category_order": list(SOC_CATEGORIES),
        "action_order": list(SCORER_ACTIONS),
        "p_correct_by_cat": p_correct_by_cat,
        "rng_seed": config.seed,
        "seed_hash": compute_seed_hash(data),
        "provenance": "sample",
        "overall_correct_rate": round(correct / total_decisions, 3)
        if total_decisions
        else 0.0,
    }
