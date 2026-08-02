"""AE-02 per-variant shadow runner.

This service is separate from app/framework/shadow_mode.py whole-system shadow
mode. Production action is always preserved; shadow execution is an
asynchronous comparison path only. MVP automated shadow supports routing_rule
and scoring_threshold artifacts. context_policy is deferred post-MVP, while
prompt_module and evidence_order require analyst feedback before evaluation.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Optional

log = logging.getLogger(__name__)

SHADOW_BATCH_SIZE = 25
SHADOW_TESTABLE_ARTIFACTS = {"routing_rule", "scoring_threshold"}


@dataclass
class ShadowComparison:
    variant_id: str
    alert_id: str
    category: str
    production_action: str
    variant_action: str
    production_confidence: float
    correct_action: Optional[str]
    timestamp: float


_shadow_buffer: list[ShadowComparison] = []
_flush_lock = asyncio.Lock()


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def compute_variant_action(
    artifact_type: str,
    config: dict[str, Any],
    production_action: str,
    confidence: float,
    category: str,
    alert_data: dict[str, Any],
) -> str:
    """Return the shadow variant action without changing production behavior."""
    try:
        if artifact_type == "routing_rule":
            trigger_categories = config.get("trigger_categories", [])
            min_confidence = _safe_float(config.get("min_confidence", 1.0), 1.0)
            action = str(config.get("action") or production_action)
            if category in trigger_categories and confidence >= min_confidence:
                return action
            return production_action

        if artifact_type == "scoring_threshold":
            config_category = config.get("category")
            if config_category and config_category != category:
                return production_action
            current_value = _safe_float(config.get("current_value", 1.0), 1.0)
            proposed_value = _safe_float(config.get("proposed_value", current_value), current_value)
            low = min(current_value, proposed_value)
            high = max(current_value, proposed_value)
            if low <= confidence < high and confidence >= proposed_value:
                auto_action = str(config.get("auto_approve_action", "suppress"))
                return auto_action
            return production_action

        return production_action
    except Exception as exc:
        log.debug("Shadow variant action computation failed: %s", exc)
        return production_action


def _shadow_variants_for_category(category: str, artifact_type: str) -> list[Any]:
    from app.services.variant_registry import SHADOW, get_all_variants

    return [
        variant
        for variant in get_all_variants(status_filter=SHADOW)
        if variant.artifact_type == artifact_type
        and (variant.category == category or variant.category is None)
    ]


async def maybe_shadow_compare(
    alert_id: str,
    category: str,
    production_action: str,
    production_confidence: float,
    alert_data: dict[str, Any],
) -> None:
    """Record shadow comparisons for eligible shadow variants.

    This function handles its own errors because it is intended for
    fire-and-forget use from the triage response path.
    """
    try:
        for artifact_type in sorted(SHADOW_TESTABLE_ARTIFACTS):
            for variant in _shadow_variants_for_category(category, artifact_type):
                if getattr(variant, "status", None) != "shadow":
                    continue
                variant_action = compute_variant_action(
                    artifact_type=artifact_type,
                    config=getattr(variant, "config", {}) or {},
                    production_action=production_action,
                    confidence=float(production_confidence),
                    category=category,
                    alert_data=alert_data or {},
                )
                _add_to_shadow_buffer(
                    ShadowComparison(
                        variant_id=variant.variant_id,
                        alert_id=alert_id,
                        category=category,
                        production_action=production_action,
                        variant_action=variant_action,
                        production_confidence=float(production_confidence),
                        correct_action=None,
                        timestamp=time.time(),
                    )
                )
    except Exception as exc:
        log.warning("Shadow comparison failed for alert_id=%s: %s", alert_id, exc)


def _add_to_shadow_buffer(comparison: ShadowComparison) -> None:
    _shadow_buffer.append(comparison)


def fill_shadow_outcome(alert_id: str, correct_action: str) -> None:
    try:
        for comparison in _shadow_buffer:
            if comparison.alert_id == alert_id and comparison.correct_action is None:
                comparison.correct_action = correct_action
        _maybe_schedule_flush()
    except Exception as exc:
        log.warning("Shadow outcome fill failed for alert_id=%s: %s", alert_id, exc)


def _maybe_schedule_flush() -> None:
    counts = Counter(
        comparison.variant_id
        for comparison in _shadow_buffer
        if comparison.correct_action is not None
    )
    if not any(count >= SHADOW_BATCH_SIZE for count in counts.values()):
        return

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        log.debug("Shadow flush threshold reached but no running event loop is available")
        return

    from app.db.graph_client import graph_client

    asyncio.create_task(_flush_shadow_batch(graph_client))


async def _flush_shadow_batch(graph_client: Any) -> None:
    async with _flush_lock:
        verified = [
            comparison
            for comparison in _shadow_buffer
            if comparison.correct_action is not None
        ]
        if len(verified) < SHADOW_BATCH_SIZE:
            return

        by_variant: dict[str, list[ShadowComparison]] = defaultdict(list)
        for comparison in verified:
            by_variant[comparison.variant_id].append(comparison)

        flushed_ids: set[int] = set()
        stale_ids: set[int] = set()
        from gae.evolution import SHADOW_RESULT, record_evolution_event
        from app.services.variant_registry import get_variant

        for variant_id, comparisons in by_variant.items():
            if len(comparisons) < SHADOW_BATCH_SIZE:
                continue
            variant = get_variant(variant_id)
            if variant is None or getattr(variant, "status", None) != "shadow":
                log.debug(
                    "Dropping %s stale verified shadow comparisons for variant_id=%s",
                    len(comparisons),
                    variant_id,
                )
                stale_ids.update(id(comparison) for comparison in comparisons)
                continue

            wins = sum(
                1
                for comparison in comparisons
                if comparison.variant_action == comparison.correct_action
                and comparison.production_action != comparison.correct_action
            )
            total = len(comparisons)
            win_rate = wins / total if total else 0.0
            categories = sorted({comparison.category for comparison in comparisons})

            try:
                await record_evolution_event(
                    graph_client=graph_client,
                    event_type=SHADOW_RESULT,
                    variant_id=variant_id,
                    artifact_type=variant.artifact_type,
                    description=f"Shadow batch: {wins}/{total} wins ({win_rate:.1%})",
                    before_state={"production_win_count": total - wins},
                    after_state={"variant_win_count": wins},
                    graph_context={
                        "evidence_type": "contextual_performance",
                        "sample_size": total,
                        "win_rate": round(win_rate, 4),
                        "categories_covered": categories,
                    },
                    metadata={"wins": wins, "total": total, "win": wins > total // 2},
                    impact="medium" if win_rate > 0.55 else "low",
                    magnitude=round(win_rate, 4),
                )
            except Exception as exc:
                log.warning("Shadow batch write failed for variant_id=%s: %s", variant_id, exc)
                continue

            flushed_ids.update(id(comparison) for comparison in comparisons)

        removable_ids = flushed_ids | stale_ids
        if removable_ids:
            _shadow_buffer[:] = [
                comparison
                for comparison in _shadow_buffer
                if comparison.correct_action is None or id(comparison) not in removable_ids
            ]


def reset_shadow_runner() -> None:
    _shadow_buffer.clear()


__all__ = [
    "SHADOW_BATCH_SIZE",
    "SHADOW_TESTABLE_ARTIFACTS",
    "ShadowComparison",
    "_add_to_shadow_buffer",
    "_flush_shadow_batch",
    "_maybe_schedule_flush",
    "_shadow_buffer",
    "compute_variant_action",
    "fill_shadow_outcome",
    "maybe_shadow_compare",
    "reset_shadow_runner",
]
