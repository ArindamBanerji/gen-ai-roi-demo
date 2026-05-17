from __future__ import annotations

import hashlib
import random
from datetime import datetime, timezone
from typing import Any

from app.domains.soc.config import (
    N_FACTORS,
    SCORER_ACTIONS,
    SOC_CATEGORIES,
    SOC_PROFILE_CENTROIDS,
)
from app.seed.config import SeedConfig


def generate_decisions(
    config: SeedConfig,
    training_alerts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if config.n_decisions == 0:
        return []
    if not training_alerts:
        raise ValueError("Cannot generate decisions without training alerts")

    rng = random.Random(config.seed + 101)
    step_ms = config.decision_timestamp_step_ms
    per_alert_counts = _decision_alert_sequence(config, len(training_alerts))
    decisions: list[dict[str, Any]] = []
    correct_so_far = 0

    for i, alert_index in enumerate(per_alert_counts):
        alert = training_alerts[alert_index]
        category = alert["category"]
        category_index = SOC_CATEGORIES.index(category)
        action = _choose_action(i, category_index, rng)
        action_index = SCORER_ACTIONS.index(action)
        target_accuracy = _target_accuracy(config, i)
        correct = rng.random() < target_accuracy
        decision_id = f"SYN-DEC-{_stable_id(config.seed, i, alert['alert_id'])}"
        if i < 2 and alert["alert_id"] in {"ALT-JDOE-001", "ALT-JDOE-002"}:
            decision_id = "DEC-JDOE-001" if alert["alert_id"] == "ALT-JDOE-001" else "DEC-JDOE-002"
            correct = True
        if correct:
            correct_so_far += 1
        timestamp_epoch = config.base_epoch_ms + i * step_ms
        decisions.append({
            "decision_id": decision_id,
            "alert_id": alert["alert_id"],
            "category": category,
            "action": action,
            "factor_vector": _factor_vector(category_index, action_index, rng),
            "confidence": round(0.55 + 0.4 * _running_accuracy(correct_so_far, i + 1), 3),
            "correct": bool(correct),
            "outcome": "correct" if correct else "incorrect",
            "timestamp_epoch": timestamp_epoch,
            "origin": config.training_origin,
            "source_id": "synthetic",
            "user_id": alert.get("user_id", ""),
            "timestamp": _iso(timestamp_epoch),
        })

    return decisions


def _decision_alert_sequence(config: SeedConfig, n_alerts: int) -> list[int]:
    counts = [0] * n_alerts
    sequence: list[int] = []
    cursor = 0
    while len(sequence) < config.n_decisions:
        if counts[cursor] < config.max_decisions_per_alert:
            sequence.append(cursor)
            counts[cursor] += 1
        cursor = (cursor + 1) % n_alerts
        if all(c >= config.max_decisions_per_alert for c in counts):
            counts = [0] * n_alerts
    return sequence


def _choose_action(index: int, category_index: int, rng: random.Random) -> str:
    if rng.random() < 0.65:
        return SCORER_ACTIONS[(category_index + index) % len(SCORER_ACTIONS)]
    return rng.choice(SCORER_ACTIONS)


def _target_accuracy(config: SeedConfig, index: int) -> float:
    if config.n_decisions <= 1:
        return config.accuracy_target
    progress = index / (config.n_decisions - 1)
    start = max(0.5, config.accuracy_target - 0.12)
    return min(0.98, start + (config.accuracy_target - start) * progress)


def _running_accuracy(correct: int, total: int) -> float:
    return correct / max(total, 1)


def _factor_vector(category_index: int, action_index: int, rng: random.Random) -> list[float]:
    base = SOC_PROFILE_CENTROIDS[category_index, action_index]
    values = []
    for value in base:
        noisy = float(value) + rng.uniform(-0.08, 0.08)
        values.append(round(min(1.0, max(0.0, noisy)), 3))
    if len(values) != N_FACTORS:
        raise ValueError("Generated factor vector length does not match N_FACTORS")
    return values


def _stable_id(seed: int, index: int, alert_id: str) -> str:
    digest = hashlib.sha1(f"{seed}:{index}:{alert_id}".encode("utf-8")).hexdigest()
    return digest[:8]


def _iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()
