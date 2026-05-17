from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from app.domains.soc.config import BOOTSTRAP_CATEGORY_WEIGHTS, SOC_CATEGORIES


@dataclass(frozen=True)
class SeedConfig:
    n_training_alerts: int = 543
    n_demo_alerts: int = 102
    n_decisions: int = 4862
    n_users: int = 21
    n_assets: int = 16
    n_campaigns: int = 4
    n_attack_patterns: int = 9
    n_threat_indicators: int = 9
    time_range_days: int = 90
    accuracy_target: float = 0.816
    decisions_per_alert_mean: float = 7.5
    max_decisions_per_alert: int = 9
    seed: int = 42
    category_weights: Mapping[str, float] = field(
        default_factory=lambda: dict(BOOTSTRAP_CATEGORY_WEIGHTS)
    )
    include_demo_alerts: bool = True
    include_training_alerts: bool = True
    base_epoch_ms: int = 1741046400000
    demo_base_epoch_ms: int = 1748217600000
    demo_status: str = "pending"
    training_status: str = "decided"
    training_origin: str = "zero_day_synthetic"
    demo_origin: str = "zero_day_demo"
    timestamp_step_ms: int | None = None

    def __post_init__(self) -> None:
        for name in (
            "n_training_alerts",
            "n_demo_alerts",
            "n_decisions",
            "n_users",
            "n_assets",
            "n_campaigns",
            "n_attack_patterns",
            "n_threat_indicators",
            "time_range_days",
            "max_decisions_per_alert",
            "seed",
        ):
            value = getattr(self, name)
            if not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
            if name in {"time_range_days", "max_decisions_per_alert"}:
                if value <= 0:
                    raise ValueError(f"{name} must be positive")
            elif value < 0:
                raise ValueError(f"{name} must be non-negative")

        if not 0.0 <= self.accuracy_target <= 1.0:
            raise ValueError("accuracy_target must be between 0 and 1")
        if self.decisions_per_alert_mean < 0:
            raise ValueError("decisions_per_alert_mean must be non-negative")
        if self.n_decisions > 0 and self.n_training_alerts <= 0:
            raise ValueError("n_training_alerts must be positive when n_decisions > 0")
        if self.timestamp_step_ms is not None and self.timestamp_step_ms <= 0:
            raise ValueError("timestamp_step_ms must be positive when provided")

        weights = dict(self.category_weights)
        missing = set(SOC_CATEGORIES) - set(weights)
        extra = set(weights) - set(SOC_CATEGORIES)
        if missing or extra:
            raise ValueError(
                "category_weights must cover SOC_CATEGORIES exactly: "
                f"missing={sorted(missing)}, extra={sorted(extra)}"
            )
        total = sum(float(v) for v in weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"category_weights must sum to 1.0, got {total}")
        if any(float(v) < 0 for v in weights.values()):
            raise ValueError("category_weights cannot contain negative values")

    @property
    def decision_timestamp_step_ms(self) -> int:
        if self.timestamp_step_ms is not None:
            return self.timestamp_step_ms
        total_window_ms = self.time_range_days * 24 * 60 * 60 * 1000
        return max(1, total_window_ms // max(self.n_decisions - 1, 1))
