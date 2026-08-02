"""AE-03 conservation-bounded promotion gate for AgentEvolver variants.

The gate evaluates shadow-tested variants against superiority, correctness,
conservation, and variance criteria. It reads ProfileScorer / learning-health
state without mutating Level 1 scorer, centroid, or gae_state objects.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from statistics import pstdev
from typing import Any, Optional, overload

from gae.evolution import (
    PROMOTION_APPROVED,
    PROMOTION_REJECTED,
    ROLLBACK,
    SHADOW_RESULT,
    get_shadow_summary,
    get_variant_history,
    record_evolution_event,
)
from app.services.variant_registry import (
    ACTIVE,
    REJECTED,
    ROLLED_BACK,
    SHADOW,
    get_all_variants,
    get_variant,
    transition_status,
)

log = logging.getLogger(__name__)

DELTA_MIN = 0.05
Q_FLOOR = 0.80
SIGMA_MAX = 0.10
MIN_SHADOW_SAMPLES = 50
MIN_SHADOW_BATCHES = 3
DISAGREEMENT_RATE = 0.20
ROLLBACK_MIN_HOURS = 48
ROLLBACK_MIN_DECISIONS = 100

_REGISTERED_STATE_MACHINES: set[int] = set()
_ROLLBACK_LOOP: asyncio.AbstractEventLoop | None = None


@dataclass
class PromotionResult:
    verdict: str
    reason: str
    gate_evidence: Optional[dict[str, Any]] = None


@overload
def _as_float(value: Any, default: float = 0.0) -> float:
    ...


@overload
def _as_float(value: Any, default: None) -> float | None:
    ...


def _as_float(value: Any, default: float | None = 0.0) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _get_health_components() -> dict[str, Any] | None:
    """Return read-only alpha/q/V components from live learning-health history."""
    components: dict[str, Any] = {}
    try:
        from app.services.gae_state import get_learning_state
        from app.services.learning_health import LearningHealthMonitor

        state = get_learning_state()
        history = getattr(state, "history", None) or []
        extracted = LearningHealthMonitor._extract_components(history)
        for key in ("q", "alpha", "V"):
            if key in extracted and extracted[key] is not None:
                value = _as_float(extracted[key], None)
                if value is not None:
                    components[key] = value
        if components:
            components["source"] = "learning_health"
    except Exception as exc:
        log.debug("Promotion gate learning-health components unavailable: %s", exc)

    if "alpha" not in components:
        try:
            from app.services.gae_state import get_profile_scorer

            scorer = get_profile_scorer()
            if scorer is not None and hasattr(scorer, "get_alpha"):
                alpha = _as_float(scorer.get_alpha(0), None)
                if alpha is not None:
                    components["alpha"] = alpha
                    components.setdefault("source", "profile_scorer")
        except Exception as exc:
            log.debug("Promotion gate scorer alpha unavailable: %s", exc)

    return components or None


def _production_q() -> float | None:
    components = _get_health_components()
    if components is None:
        return None
    value = components.get("q")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


async def evaluate_promotion(variant_id: str, graph_client) -> PromotionResult:
    variant = get_variant(variant_id)
    if variant is None:
        return PromotionResult("reject", f"variant {variant_id} not found", None)
    if variant.status != SHADOW:
        return PromotionResult(
            "continue",
            f"variant status {variant.status} is not shadow",
            {"status": variant.status},
        )

    summary = get_shadow_summary(variant_id)
    if not summary or not summary.get("shadow_tested"):
        return PromotionResult("continue", "shadow results are not available", summary)

    total = int(summary.get("total") or 0)
    win_rate = _as_float(summary.get("win_rate"), 0.0)
    if total < MIN_SHADOW_SAMPLES:
        return PromotionResult(
            "continue",
            f"insufficient shadow samples: {total} < {MIN_SHADOW_SAMPLES}",
            {"total": total, "win_rate": win_rate},
        )

    threshold = 0.50 + DELTA_MIN
    if win_rate < threshold:
        return PromotionResult(
            "reject",
            f"shadow win_rate {win_rate:.4f} below promotion threshold {threshold:.4f}",
            {"total": total, "win_rate": win_rate, "superiority_pp": round((win_rate - 0.50) * 100, 2)},
        )

    projected_q = _estimate_projected_accuracy(summary)
    if projected_q < Q_FLOOR:
        return PromotionResult(
            "reject",
            f"projected_q {projected_q:.4f} below correctness floor {Q_FLOOR:.4f}",
            {"projected_q": projected_q, "correctness_floor": Q_FLOOR, "total": total, "win_rate": win_rate},
        )

    conservation = await _check_conservation_for_variant(projected_q, graph_client)
    if not conservation.get("passed"):
        return PromotionResult(
            "reject",
            "conservation check failed",
            {
                "total": total,
                "win_rate": win_rate,
                "projected_q": projected_q,
                "conservation": conservation,
                "conservation_status": conservation.get("status"),
            },
        )

    batch_stats = await _get_shadow_batch_stats(variant_id, graph_client)
    batch_count = int(batch_stats.get("batch_count") or 0)
    if batch_count < MIN_SHADOW_BATCHES:
        return PromotionResult(
            "continue",
            f"Need {MIN_SHADOW_BATCHES} shadow batches, have {batch_count}",
            {
                "total": total,
                "win_rate": win_rate,
                "projected_q": projected_q,
                "conservation_status": conservation.get("status"),
                "shadow_batches": batch_count,
                "min_shadow_batches": MIN_SHADOW_BATCHES,
            },
        )

    batch_std = _as_float(batch_stats.get("batch_std"), 0.0)
    if batch_std > SIGMA_MAX:
        return PromotionResult(
            "reject",
            f"shadow batch variance {batch_std:.4f} exceeds {SIGMA_MAX:.4f}",
            {
                "variance_std": batch_std,
                "shadow_batches": batch_count,
                "total": total,
                "win_rate": win_rate,
            },
        )

    evidence = {
        "superiority_pp": round((win_rate - 0.50) * 100, 2),
        "correctness_floor": Q_FLOOR,
        "conservation_status": conservation.get("status"),
        "conservation": conservation,
        "variance_std": batch_std,
        "shadow_batches": batch_count,
        "projected_q": projected_q,
        "win_rate": win_rate,
        "total": total,
    }
    return PromotionResult("promote", "all promotion gates passed", evidence)


def _estimate_projected_accuracy(summary: dict[str, Any]) -> float:
    production_q = _production_q()
    if production_q is None:
        production_q = Q_FLOOR
    win_rate = _as_float(summary.get("win_rate"), 0.0)
    improvement = (win_rate - 0.50) * DISAGREEMENT_RATE
    return round(min(production_q + improvement, 0.95), 4)


async def _check_conservation_for_variant(projected_q: float, graph_client) -> dict[str, Any]:
    components = _get_health_components()
    if components is None:
        return {"passed": True, "status": "UNKNOWN"}

    alpha = _as_float(components.get("alpha"), 0.0)
    volume = _as_float(components.get("V"), 0.0)
    if alpha <= 0 or volume <= 0:
        return {
            "passed": True,
            "status": "COLD_START",
            "alpha": alpha,
            "projected_q": projected_q,
            "V": volume,
        }

    try:
        from gae.calibration import compute_theta_min

        theta_min = float(compute_theta_min(alpha, volume))
    except Exception:
        theta_min = 23.53 / (alpha * volume)
    signal = alpha * projected_q * volume
    passed = signal >= theta_min
    return {
        "passed": passed,
        "status": "GREEN" if passed else "RED",
        "alpha": alpha,
        "projected_q": projected_q,
        "V": volume,
        "signal": round(signal, 6),
        "theta_min": round(theta_min, 6),
    }


def _shadow_win_rates(events: list[dict[str, Any]]) -> list[float]:
    rates: list[float] = []
    for event in events or []:
        if event.get("event_type") != SHADOW_RESULT:
            continue
        graph_context = event.get("graph_context") or {}
        metadata = event.get("metadata") or {}
        raw_rate = graph_context.get("win_rate")
        if raw_rate is None:
            raw_rate = metadata.get("win_rate")
        if raw_rate is None and metadata.get("total"):
            raw_rate = _as_float(metadata.get("wins"), 0.0) / max(_as_float(metadata.get("total"), 0.0), 1.0)
        if raw_rate is not None:
            rates.append(float(raw_rate))
    return rates


async def _get_shadow_batch_stats(variant_id: str, graph_client) -> dict[str, Any]:
    try:
        events = await get_variant_history(graph_client, variant_id)
        rates = _shadow_win_rates(events or [])
        batch_std = round(float(pstdev(rates)), 6) if len(rates) >= MIN_SHADOW_BATCHES else 0.0
        return {
            "batch_count": len(rates),
            "batch_std": batch_std,
            "win_rates": rates,
        }
    except Exception as exc:
        log.debug("Shadow batch stats unavailable for %s: %s", variant_id, exc)
        return {"batch_count": 0, "batch_std": 0.0, "win_rates": []}


async def _compute_batch_std(variant_id: str, graph_client) -> float:
    stats = await _get_shadow_batch_stats(variant_id, graph_client)
    return _as_float(stats.get("batch_std"), 0.0)


async def execute_promotion(variant_id: str, gate_evidence: dict[str, Any], graph_client):
    variant = get_variant(variant_id)
    if variant is None:
        raise ValueError(f"variant {variant_id} not found")
    if variant.status != SHADOW:
        raise ValueError(f"variant {variant_id} is not shadow")

    await record_evolution_event(
        graph_client=graph_client,
        event_type=PROMOTION_APPROVED,
        variant_id=variant_id,
        artifact_type=variant.artifact_type,
        description=f"Promotion approved for {variant_id}",
        before_state={"status": SHADOW},
        after_state={"status": ACTIVE},
        graph_context=variant.graph_trigger or {},
        metadata={"gate_evidence": gate_evidence, "trigger_key": variant.trigger_key},
        impact="operational",
        magnitude=_as_float(gate_evidence.get("win_rate"), 0.0),
    )
    return transition_status(variant_id, ACTIVE)


async def execute_rejection(variant_id: str, reason: str, graph_client):
    variant = get_variant(variant_id)
    if variant is None:
        raise ValueError(f"variant {variant_id} not found")
    if variant.status != SHADOW:
        raise ValueError(f"variant {variant_id} is not shadow")

    await record_evolution_event(
        graph_client=graph_client,
        event_type=PROMOTION_REJECTED,
        variant_id=variant_id,
        artifact_type=variant.artifact_type,
        description=f"Promotion rejected for {variant_id}: {reason}",
        before_state={"status": SHADOW},
        after_state={"status": REJECTED},
        graph_context=variant.graph_trigger or {},
        metadata={"reason": reason, "trigger_key": variant.trigger_key},
        impact="operational",
        magnitude=0.0,
    )
    return transition_status(variant_id, REJECTED)


def _rollback_window_hours(daily_volume: float) -> float:
    daily_volume = _as_float(daily_volume, 0.0)
    if daily_volume <= 0:
        return ROLLBACK_MIN_HOURS * 5
    return max(ROLLBACK_MIN_HOURS, ROLLBACK_MIN_DECISIONS / daily_volume * 24)


def _get_daily_volume() -> float:
    components = _get_health_components()
    if components is None:
        return 200.0
    volume = _as_float(components.get("V"), 0.0)
    return volume if volume > 0 else 200.0


async def check_rollback(graph_client, category: str | None = None):
    candidates = [
        variant
        for variant in get_all_variants(status_filter=ACTIVE)
        if category is None or variant.category == category
    ]
    if not candidates:
        return None

    most_recent = max(candidates, key=lambda variant: variant.promoted_at or 0.0)
    promoted_at = most_recent.promoted_at or 0.0
    window_seconds = _rollback_window_hours(_get_daily_volume()) * 3600
    if promoted_at <= 0 or time.time() - promoted_at > window_seconds:
        return None
    return await _execute_rollback(most_recent, graph_client)


async def _execute_rollback(variant, graph_client):
    await record_evolution_event(
        graph_client=graph_client,
        event_type=ROLLBACK,
        variant_id=variant.variant_id,
        artifact_type=variant.artifact_type,
        description=f"Rollback triggered for {variant.variant_id}",
        before_state={"status": ACTIVE},
        after_state={"status": ROLLED_BACK},
        graph_context=variant.graph_trigger or {},
        metadata={"trigger_key": variant.trigger_key, "promoted_at": variant.promoted_at},
        impact="operational",
        magnitude=0.0,
    )
    return transition_status(variant.variant_id, ROLLED_BACK)


async def _async_rollback_check(graph_client):
    return await check_rollback(graph_client)


def _state_machine_for_scorer(scorer: Any) -> Any:
    if scorer is None:
        return None
    state_machine = getattr(scorer, "conservation_state_machine", None)
    if state_machine is None:
        state_machine = getattr(scorer, "_conservation_sm", None)
    return state_machine


def _loop_is_open(loop: Any) -> bool:
    if loop is None:
        return False
    is_closed = getattr(loop, "is_closed", None)
    return not (callable(is_closed) and is_closed())


def _create_rollback_task(loop: Any, graph_client) -> None:
    loop.create_task(_async_rollback_check(graph_client))


def _schedule_rollback_check(graph_client) -> bool:
    loop = _ROLLBACK_LOOP
    if _loop_is_open(loop):
        try:
            call_soon = getattr(loop, "call_soon_threadsafe", None)
            if callable(call_soon):
                call_soon(_create_rollback_task, loop, graph_client)
            else:
                _create_rollback_task(loop, graph_client)
            return True
        except RuntimeError as exc:
            log.warning("Promotion rollback scheduling failed on captured loop: %s", exc)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        log.warning("Promotion rollback handler fired without an available event loop")
        return False
    loop.create_task(_async_rollback_check(graph_client))
    return True


def register_rollback_handler(graph_client) -> bool:
    global _ROLLBACK_LOOP
    try:
        from app.services.gae_state import get_profile_scorer

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        scorer = get_profile_scorer()
        state_machine = _state_machine_for_scorer(scorer)
        if state_machine is None or not hasattr(state_machine, "register_handler"):
            return False
        state_machine_id = id(state_machine)
        if loop is not None:
            _ROLLBACK_LOOP = loop
        if state_machine_id in _REGISTERED_STATE_MACHINES:
            return True

        def _handler(old_state: str, new_state: str) -> None:
            _schedule_rollback_check(graph_client)

        state_machine.register_handler("*", "AMBER", _handler)
        state_machine.register_handler("*", "RED", _handler)
        _REGISTERED_STATE_MACHINES.add(state_machine_id)
        return True
    except Exception as exc:
        log.debug("Promotion rollback handler registration failed: %s", exc)
        return False


def reset_promotion_gate() -> None:
    global _ROLLBACK_LOOP
    _REGISTERED_STATE_MACHINES.clear()
    _ROLLBACK_LOOP = None


__all__ = [
    "DELTA_MIN",
    "DISAGREEMENT_RATE",
    "MIN_SHADOW_BATCHES",
    "MIN_SHADOW_SAMPLES",
    "PromotionResult",
    "Q_FLOOR",
    "ROLLBACK_MIN_DECISIONS",
    "ROLLBACK_MIN_HOURS",
    "SIGMA_MAX",
    "_async_rollback_check",
    "_check_conservation_for_variant",
    "_compute_batch_std",
    "_estimate_projected_accuracy",
    "_execute_rollback",
    "_get_daily_volume",
    "_get_shadow_batch_stats",
    "_rollback_window_hours",
    "check_rollback",
    "evaluate_promotion",
    "execute_promotion",
    "execute_rejection",
    "register_rollback_handler",
    "reset_promotion_gate",
]
