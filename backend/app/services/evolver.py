"""
Agent Evolver service.

The SOC service keeps the historical public module API used by routers/tests, while
delegating prompt variant selection, outcome stats, and promotion decisions to the
SDK PromptVariantEvolver.
"""
import asyncio
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable, Dict, List, Optional, cast

from pydantic import BaseModel

from copilot_sdk.evolution.conservation_contract import (
    CachedAsyncProvider,
    ConservationState,
    normalize_conservation_state,
)
from copilot_sdk.evolution.prompt_evolver import PromptEvolverConfig, PromptVariantEvolver
from copilot_sdk.evolution.variant_store import (
    CategoryVariantStats,
    InMemoryVariantStore,
    VariantSpec,
    VariantStats,
    VariantStore,
)


class AGEVariantStore(InMemoryVariantStore):
    """VariantStore whose complete state is persisted as AGE EvolutionState."""

    def __init__(self, graph_store: Any, domain: str = "soc") -> None:
        super().__init__()
        self._graph_store = graph_store
        self._domain = domain
        states = graph_store.list_evolutions(domain)
        for state in states:
            self._restore(state)

    def _persist(self, variant_id: str) -> None:
        spec = self.get_variant(variant_id)
        if spec is None:
            raise ValueError(f"Unknown variant: {variant_id}")
        global_stats = self.get_global_stats(variant_id)
        categories = {
            category: self.get_category_stats(category, variant_id).__dict__
            for category in self._category_stats
            if variant_id in self._category_stats[category]
        }
        self._graph_store.save_evolution(self._domain, variant_id, {
            "spec": spec.__dict__,
            "global_stats": global_stats.__dict__,
            "category_stats": categories,
        })

    def _restore(self, payload: dict[str, Any]) -> None:
        spec_data = payload.get("spec")
        if not isinstance(spec_data, dict):
            return
        spec = VariantSpec(**spec_data)
        if spec.id in self._variants:
            return
        super().register_variant(spec)
        global_data = payload.get("global_stats", {})
        self._global_stats[spec.id] = VariantStats(**{
            key: int(global_data.get(key, 0))
            for key in ("successes", "total", "failures")
        })
        for category, data in payload.get("category_stats", {}).items():
            if isinstance(data, dict):
                self._category_stats.setdefault(category, {})[spec.id] = CategoryVariantStats(
                    category=category,
                    variant_id=spec.id,
                    successes=int(data.get("successes", 0)),
                    total=int(data.get("total", 0)),
                    failures=int(data.get("failures", 0)),
                )

    def register_variant(self, spec: VariantSpec) -> None:
        if self.get_variant(spec.id) is None:
            super().register_variant(spec)
        self._persist(spec.id)

    def record_outcome(self, variant_id: str, success: bool, category: str | None = None) -> None:
        super().record_outcome(variant_id, success, category)
        self._persist(variant_id)

    def record_category_outcome(self, category: str, variant_id: str, success: bool) -> None:
        super().record_category_outcome(category, variant_id, success)
        self._persist(variant_id)

    def update_variant_status(self, variant_id: str, new_status: str) -> None:
        super().update_variant_status(variant_id, new_status)
        self._persist(variant_id)

    def reset(self) -> None:
        for state in self._graph_store.list_evolutions(self._domain):
            key = state.get("key")
            if key is not None:
                self._graph_store.delete_evolution(self._domain, str(key))
        super().reset()

    def reset_stats_only(self) -> None:
        super().reset_stats_only()
        for spec in self.get_all_variants():
            self._persist(spec.id)


def _initial_prompt_stats() -> Dict[str, Dict[str, float]]:
    return {
        "TRAVEL_CONTEXT_v1": {"success": 24, "total": 34, "success_rate": 0.71},
        "TRAVEL_CONTEXT_v2": {"success": 42, "total": 47, "success_rate": 0.89},
        "PHISHING_RESPONSE_v1": {"success": 31, "total": 38, "success_rate": 0.82},
        "PHISHING_RESPONSE_v2": {"success": 12, "total": 15, "success_rate": 0.80},
    }


def _initial_active_prompts() -> Dict[str, str]:
    return {
        "anomalous_login": "TRAVEL_CONTEXT_v2",
        "phishing": "PHISHING_RESPONSE_v1",
    }


# Legacy SOC-facing compatibility mirrors. Routers use functions, but existing
# tests and demos also inspect/mutate these maps directly.
PROMPT_STATS: Dict[str, Dict[str, Any]] = _initial_prompt_stats()
CATEGORY_PROMPT_STATS: Dict[str, Dict[str, Dict[str, Any]]] = {}
ACTIVE_PROMPTS: Dict[str, str] = _initial_active_prompts()
RECENT_PROMOTIONS: Dict[str, Dict[str, Any]] = {}
WEIGHT_HISTORY: List[Dict[str, Any]] = []
_UCB_EXPLORATION = 1.0


class SOCConservationProvider:
    """Synchronous promotion snapshot fed by async learning-health evaluations."""

    def __init__(
        self,
        freshness_ttl: float = 30.0,
        clock: Callable[[], float] | None = None,
        refresh_timeout: float = 5.0,
    ) -> None:
        self._ttl = float(freshness_ttl)
        self._refresh_timeout = float(refresh_timeout)
        self._clock = clock or __import__("time").time
        self._lock = RLock()
        self._updated_at = 0.0
        self._snapshot: ConservationState = normalize_conservation_state(
            {"status": "UNKNOWN", "reason": "no_learning_health_snapshot"},
            domain="soc",
            source="learning_health_monitor",
        )
        self._cached = CachedAsyncProvider(
            self._read_snapshot,
            freshness_ttl=self._ttl,
            clock=self._clock,
        )

    def _read_snapshot(self) -> ConservationState:
        with self._lock:
            if float(self._clock()) - self._updated_at > self._ttl:
                return normalize_conservation_state(
                    {"status": "UNKNOWN", "reason": "learning_health_snapshot_stale"},
                    domain="soc",
                    source="learning_health_monitor",
                )
            return dict(self._snapshot)

    def update_from_health(self, health: dict[str, Any]) -> None:
        status = health.get("status") or (health.get("conservation") or {}).get("status")
        components = health.get("components") or {}
        with self._lock:
            self._snapshot = normalize_conservation_state(
                {
                    "status": status,
                    "domain": "soc",
                    "source": str(health.get("health_source") or "learning_health_monitor"),
                    "observed_at": datetime.now(timezone.utc).isoformat(),
                    "verified_count": components.get("n", health.get("decision_count", 0)),
                    "reason": health.get("status_reason"),
                },
                domain="soc",
                source=str(health.get("health_source") or "learning_health_monitor"),
            )
            self._updated_at = float(self._clock())
            self._cached.invalidate()

    def mark_unknown(self, reason: str) -> None:
        self.update_from_health({"status": "UNKNOWN", "status_reason": reason})

    async def refresh(self, graph_service: Any = None) -> ConservationState:
        try:
            from app.services.learning_health import LearningHealthMonitor

            health = await asyncio.wait_for(
                LearningHealthMonitor.evaluate(graph_service),
                timeout=self._refresh_timeout,
            )
            self.update_from_health(health)
        except Exception as exc:
            self.mark_unknown(f"learning_health_error:{exc}")
        return self.get_state()

    def get_state(self) -> ConservationState:
        return self._cached.get_state()

    def __call__(self) -> ConservationState:
        return self.get_state()


_SOC_CONSERVATION_PROVIDER = SOCConservationProvider()


def get_soc_conservation_provider() -> SOCConservationProvider:
    return _SOC_CONSERVATION_PROVIDER


class OperationalImpact(BaseModel):
    """Quantified operational impact of prompt evolution."""

    analyst_time_saved_hours: float
    false_positive_reduction: float
    accuracy_improvement: float
    estimated_value: float


class PromptEvolution(BaseModel):
    """Prompt evolution summary for UI."""

    alert_type: str
    current_prompt: str
    success_rate: float
    improvement: float
    what_changed: str
    operational_impact: OperationalImpact
    promotion_reason: Optional[str] = None


def _get_soc_categories() -> List[str]:
    try:
        from app.domains.soc.config import SOC_CATEGORIES

        return [getattr(category, "name", category) for category in SOC_CATEGORIES]
    except Exception:
        return []


def _variant_family(variant_id: str) -> str:
    if "_v" in variant_id:
        return variant_id.rsplit("_v", 1)[0]
    parts = variant_id.split("_")
    return "_".join(parts[:-1]) if len(parts) > 1 else variant_id


def _variant_version(variant_id: str) -> int:
    if "_v" not in variant_id:
        return 1
    suffix = variant_id.rsplit("_v", 1)[1]
    try:
        return max(1, int(suffix))
    except ValueError:
        return 1


def _category_has_recorded_stats(category: str) -> bool:
    return any(
        int(stats.get("total", 0)) > 0
        for stats in CATEGORY_PROMPT_STATS.get(category, {}).values()
    )


def _build_variant_specs() -> List[VariantSpec]:
    variant_ids: List[str] = []
    for variant_id in PROMPT_STATS:
        if variant_id not in variant_ids:
            variant_ids.append(variant_id)
    for category_stats in CATEGORY_PROMPT_STATS.values():
        for variant_id in category_stats:
            if variant_id not in variant_ids:
                variant_ids.append(variant_id)
    for variant_id in ACTIVE_PROMPTS.values():
        if variant_id not in variant_ids:
            variant_ids.append(variant_id)

    active_variants = set(ACTIVE_PROMPTS.values())
    category_variants = {
        variant_id
        for category_stats in CATEGORY_PROMPT_STATS.values()
        for variant_id in category_stats
    }

    specs: List[VariantSpec] = []
    for variant_id in variant_ids:
        status = "active" if variant_id in active_variants or variant_id in category_variants else "shadow"
        specs.append(
            VariantSpec(
                id=variant_id,
                family=_variant_family(variant_id),
                version=_variant_version(variant_id),
                status=status,
                metadata={"source": "soc_adapter"},
            )
        )
    return specs


def _seed_store_stats(store: VariantStore) -> None:
    for variant_id, stats in PROMPT_STATS.items():
        successes = int(stats.get("success", 0))
        total = int(stats.get("total", 0))
        if store.get_global_stats(variant_id).total == 0 and total > 0:
            for index in range(total):
                store.record_outcome(variant_id, index < successes)

    for category, category_stats in CATEGORY_PROMPT_STATS.items():
        for variant_id, stats in category_stats.items():
            successes = int(stats.get("success", 0))
            total = int(stats.get("total", 0))
            if store.get_category_stats(category, variant_id).total == 0 and total > 0:
                for index in range(total):
                    store.record_category_outcome(category, variant_id, index < successes)


def _sdk_config() -> PromptEvolverConfig:
    return PromptEvolverConfig(
        categories=_get_soc_categories(),
        exploration_constant=_UCB_EXPLORATION,
        promotion_improvement_threshold=0.05,
        promotion_min_samples=10,
        category_resolver=_category_resolver,
        conservation_state_provider=get_soc_conservation_provider(),
    )


_SOC_VARIANT_STORE: VariantStore | None = None


def _soc_variant_store() -> VariantStore:
    global _SOC_VARIANT_STORE
    if _SOC_VARIANT_STORE is None:
        from app.db.graph_client import graph_client
        from app.services.graph_store_adapter import create_soc_graph_store
        from copilot_sdk.config import GraphConfig

        config = GraphConfig.load("soc")
        _SOC_VARIANT_STORE = AGEVariantStore(
            create_soc_graph_store(graph_client, config),
            domain="soc",
        )
    return _SOC_VARIANT_STORE


def _new_sdk_evolver_from_compat_state() -> PromptVariantEvolver:
    store = _soc_variant_store()
    for spec in _build_variant_specs():
        store.register_variant(spec)
    _seed_store_stats(store)
    return PromptVariantEvolver(config=_sdk_config(), store=store)


def get_sdk_evolver() -> PromptVariantEvolver:
    """Return the live SDK evolver used by the compatibility service."""
    global _evolver
    if _evolver is None:
        _evolver = _new_sdk_evolver_from_compat_state()
    return _evolver


def _sync_sdk_from_compat_state() -> None:
    global _evolver
    _evolver = _new_sdk_evolver_from_compat_state()


def _refresh_compat_stats_from_sdk() -> None:
    evolver = get_sdk_evolver()
    PROMPT_STATS.clear()
    for spec in evolver.store.get_all_variants():
        stats = evolver.store.get_global_stats(spec.id)
        PROMPT_STATS[spec.id] = {
            "success": stats.successes,
            "total": stats.total,
            "success_rate": stats.success_rate,
        }

    category_names = set(CATEGORY_PROMPT_STATS) | set(_get_soc_categories())
    CATEGORY_PROMPT_STATS.clear()
    for category in category_names:
        category_stats = evolver.store.get_all_category_stats(category)
        CATEGORY_PROMPT_STATS[category] = {}
        for variant_id, stats in category_stats.items():
            CATEGORY_PROMPT_STATS[category][variant_id] = {
                "success": stats.successes,
                "total": stats.total,
                "success_rate": stats.success_rate,
            }


def _normalize_category(
    alert_type: Optional[str] = None,
    category: Optional[str] = None,
) -> Optional[str]:
    """Map SOC alert type/category inputs to the canonical category name."""
    try:
        from app.domains.soc.config import (
            ALERT_TYPE_CATEGORY_MAP,
            SOC_CATEGORIES,
            UNCLASSIFIED_CATEGORY,
        )
    except Exception:
        return category or alert_type

    valid_names = {getattr(cat, "name", cat) for cat in SOC_CATEGORIES}

    if category:
        cat_name = getattr(category, "name", category)
        if cat_name in valid_names:
            return cat_name

    if alert_type:
        mapped = ALERT_TYPE_CATEGORY_MAP.get(alert_type)
        if mapped in valid_names:
            return cast(str, mapped)

    if category:
        return cast(str, getattr(category, "name", category))

    return UNCLASSIFIED_CATEGORY if alert_type else None


def _category_resolver(context_key: str) -> Optional[str]:
    return _normalize_category(alert_type=context_key)


_evolver: PromptVariantEvolver | None = None


def _select_category_ucb_variant(category: Optional[str]) -> Optional[str]:
    if not category or not _category_has_recorded_stats(category):
        return None
    _sync_sdk_from_compat_state()
    variant_ids = list(CATEGORY_PROMPT_STATS.get(category, {}).keys())
    stats_by_variant = {
        variant_id: get_sdk_evolver().store.get_category_stats(category, variant_id)
        for variant_id in variant_ids
    }
    return cast(Optional[str], get_sdk_evolver()._select_ucb(stats_by_variant, variant_ids))


def _legacy_prompt_variant(
    alert_type: Optional[str] = None,
    category: Optional[str] = None,
) -> str:
    try:
        from app.services.variant_registry import (
            ARTIFACT_PROMPT_MODULE,
            get_active_variant_for_category,
        )

        candidates = []
        if category:
            candidates.append(category)
        if alert_type:
            candidates.append(alert_type)

        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            module = get_active_variant_for_category(candidate, ARTIFACT_PROMPT_MODULE)
            if module:
                artifact = module.config
                for attr in ("prompt_id_variant", "prompt_variant", "variant_id"):
                    value = artifact.get(attr)
                    if value:
                        return cast(str, value)
                return cast(str, module.variant_id)
    except Exception:
        pass

    if alert_type:
        return ACTIVE_PROMPTS.get(alert_type, "DEFAULT_v1")

    return "DEFAULT_v1"


def get_prompt_variant(
    alert_type: Optional[str] = None,
    *,
    category: Optional[str] = None,
) -> str:
    """Get the current best prompt variant for an alert/category."""
    resolved_category = _normalize_category(alert_type=alert_type, category=category)
    category_variant = _select_category_ucb_variant(resolved_category)
    if category_variant:
        return category_variant
    return _legacy_prompt_variant(alert_type=alert_type, category=resolved_category)


def get_prompt_stats() -> Dict[str, Dict[str, Any]]:
    """Return prompt statistics including registry-backed variants."""
    stats = {variant: data.copy() for variant, data in PROMPT_STATS.items()}

    try:
        from app.services.variant_registry import ARTIFACT_PROMPT_MODULE, get_all_variants

        for module in get_all_variants():
            if module.artifact_type != ARTIFACT_PROMPT_MODULE:
                continue
            artifact = module.config
            prompt_variant = (
                artifact.get("prompt_id_variant")
                or artifact.get("prompt_variant")
                or artifact.get("variant_id")
                or module.variant_id
            )
            stats.setdefault(
                prompt_variant,
                {
                    "success": 0,
                    "total": 0,
                    "success_rate": 0.0,
                    "status": getattr(module.status, "value", module.status),
                    "source": "variant_registry",
                    "variant_id": module.variant_id,
                },
            )
    except Exception:
        pass

    return stats


def record_decision_outcome(
    decision_id: str,
    prompt_variant: str,
    success: bool,
    alert_type: str = "unknown",
    category: Optional[str] = None,
) -> None:
    """Record outcome for SDK-backed global/category prompt evolution stats."""
    if prompt_variant not in PROMPT_STATS:
        PROMPT_STATS[prompt_variant] = {"success": 0, "total": 0, "success_rate": 0.0}

    resolved_category = _normalize_category(alert_type=alert_type, category=category)
    _sync_sdk_from_compat_state()
    get_sdk_evolver().record_outcome(prompt_variant, success, category=resolved_category)
    _refresh_compat_stats_from_sdk()

    WEIGHT_HISTORY.append(
        {
            "decision_id": decision_id,
            "alert_type": alert_type,
            "category": resolved_category,
            "prompt_variant": prompt_variant,
            "success": success,
            "trigger": prompt_variant,
            "weights": {
                variant: stats["success_rate"]
                for variant, stats in PROMPT_STATS.items()
            },
        }
    )

    print(f"Recorded outcome: {prompt_variant} success={success}")


def check_for_promotion(
    alert_type: str,
    conservation_state: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """Check if a prompt variant should be promoted for an alert type."""
    current = ACTIVE_PROMPTS.get(alert_type)
    if not current:
        return None

    family = _variant_family(current)
    _sync_sdk_from_compat_state()
    result = get_sdk_evolver().check_for_promotion(
        family=family,
        conservation_state=conservation_state,
    )
    if not result:
        return None
    if result.get("promoted") is False:
        _refresh_compat_stats_from_sdk()
        return {
            "promoted": False,
            "old_variant": result.get("previous_id"),
            "new_variant": result.get("candidate_id"),
            "old_rate": result.get("active_rate"),
            "new_rate": result.get("candidate_rate"),
            "reason": result.get("message") or result.get("reason"),
        }

    ACTIVE_PROMPTS[alert_type] = result["promoted_id"]
    _refresh_compat_stats_from_sdk()

    promotion = {
        "promoted": True,
        "old_variant": result["previous_id"],
        "new_variant": result["promoted_id"],
        "old_rate": result["active_rate"],
        "new_rate": result["candidate_rate"],
        "reason": f"Success rate improved by {result['improvement']:.1%}",
    }
    RECENT_PROMOTIONS[alert_type] = promotion
    return promotion


def generate_what_changed_narrative(
    old_variant: str,
    new_variant: str,
    alert_type: str,
) -> str:
    """Generate human-readable explanation of prompt change."""
    narratives = {
        ("TRAVEL_CONTEXT_v1", "TRAVEL_CONTEXT_v2"): (
            "Added travel calendar context and geo-velocity analysis. "
            "Now checks if login location matches user's travel schedule before escalating."
        ),
        ("PHISHING_RESPONSE_v1", "PHISHING_RESPONSE_v2"): (
            "Improved sender reputation scoring and attachment sandbox results. "
            "Reduces false positives from trusted business partners."
        ),
    }

    return narratives.get(
        (old_variant, new_variant),
        f"Evolved from {old_variant} to {new_variant} based on learning outcomes.",
    )


def calculate_operational_impact(alert_type: str, improvement: float) -> OperationalImpact:
    """Calculate operational impact of prompt improvement."""
    volume_per_day = {
        "anomalous_login": 150,
        "phishing": 300,
        "malware": 80,
        "data_exfil": 40,
    }.get(alert_type, 100)

    false_positive_reduction = improvement * volume_per_day * 0.3
    time_saved_minutes = false_positive_reduction * 8
    time_saved_hours = time_saved_minutes / 60
    annual_hours = time_saved_hours * 250
    hourly_cost = 85
    estimated_value = annual_hours * hourly_cost

    return OperationalImpact(
        analyst_time_saved_hours=round(annual_hours, 1),
        false_positive_reduction=round(false_positive_reduction * 250, 0),
        accuracy_improvement=round(improvement, 3),
        estimated_value=round(estimated_value, 0),
    )


def get_evolution_summary(alert_type: str) -> PromptEvolution:
    """Get evolution summary for an alert type."""
    current = ACTIVE_PROMPTS.get(alert_type, "DEFAULT_v1")
    current_stats = PROMPT_STATS.get(current, {"success_rate": 0.0})

    promotion = RECENT_PROMOTIONS.get(alert_type)
    if promotion:
        old_variant = promotion["old_variant"]
        new_variant = promotion["new_variant"]
        improvement = promotion["new_rate"] - promotion["old_rate"]
        what_changed = generate_what_changed_narrative(old_variant, new_variant, alert_type)
        reason = promotion["reason"]
    else:
        family_prefix = _variant_family(current)
        family_variants = [
            (variant, stats)
            for variant, stats in PROMPT_STATS.items()
            if _variant_family(variant) == family_prefix
        ]

        if len(family_variants) > 1:
            best_old = min(family_variants, key=lambda x: x[1]["success_rate"])
            improvement = current_stats["success_rate"] - best_old[1]["success_rate"]
            what_changed = generate_what_changed_narrative(best_old[0], current, alert_type)
        else:
            improvement = 0.0
            what_changed = "No evolution yet - baseline prompt active."

        reason = None

    impact = calculate_operational_impact(alert_type, improvement)

    return PromptEvolution(
        alert_type=alert_type,
        current_prompt=current,
        success_rate=current_stats["success_rate"],
        improvement=improvement,
        what_changed=what_changed,
        operational_impact=impact,
        promotion_reason=reason,
    )


def get_variant_comparison(alert_type: str) -> Dict[str, Any]:
    """Get comparison of prompt variants for an alert type."""
    current = ACTIVE_PROMPTS.get(alert_type, "DEFAULT_v1")
    family_prefix = _variant_family(current)

    variants = []
    for variant, stats in PROMPT_STATS.items():
        if _variant_family(variant) == family_prefix:
            variants.append(
                {
                    "variant": variant,
                    "success_rate": stats["success_rate"],
                    "total_decisions": stats["total"],
                    "is_active": variant == current,
                    "confidence": min(1.0, stats["total"] / 50),
                }
            )

    return {
        "alert_type": alert_type,
        "active_variant": current,
        "variants": variants,
        "recommendation": "Current variant performing well"
        if not RECENT_PROMOTIONS.get(alert_type)
        else "Recently promoted - monitoring performance",
    }


def reset_evolver_state() -> None:
    """Reset compatibility and durable evolver state for deterministic resets."""
    PROMPT_STATS.clear()
    PROMPT_STATS.update(_initial_prompt_stats())

    ACTIVE_PROMPTS.clear()
    ACTIVE_PROMPTS.update(_initial_active_prompts())

    RECENT_PROMOTIONS.clear()
    CATEGORY_PROMPT_STATS.clear()
    WEIGHT_HISTORY.clear()
    _soc_variant_store().reset()
    _sync_sdk_from_compat_state()

    try:
        from gae.evolution import reset_evolution_ledger

        reset_evolution_ledger()
    except Exception:
        pass

    try:
        from app.services.promotion_gate import reset_promotion_gate

        reset_promotion_gate()
    except Exception:
        pass

    try:
        from app.services.shadow_runner import reset_shadow_runner

        reset_shadow_runner()
    except Exception:
        pass

    try:
        from app.services.variant_registry import reset_variant_registry

        reset_variant_registry()
    except Exception:
        pass

    seed_weight_history()


def get_weight_history(alert_type_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get historical weight changes for visualization."""
    if alert_type_filter:
        return [
            snapshot
            for snapshot in WEIGHT_HISTORY
            if snapshot.get("alert_type") == alert_type_filter
        ]
    return WEIGHT_HISTORY.copy()


def seed_weight_history() -> None:
    """Seed weight history with synthetic evolution data for demo."""
    if WEIGHT_HISTORY:
        return

    for i in range(15):
        progress = i / 14

        travel_v1_weight = 0.71 - (progress * 0.15)
        travel_v2_weight = 0.60 + (progress * 0.29)

        WEIGHT_HISTORY.append(
            {
                "decision_id": f"historical_{i}",
                "alert_type": "anomalous_login",
                "prompt_variant": "TRAVEL_CONTEXT_v2" if i > 5 else "TRAVEL_CONTEXT_v1",
                "success": i > 3,
                "weights": {
                    "TRAVEL_CONTEXT_v1": round(travel_v1_weight, 3),
                    "TRAVEL_CONTEXT_v2": round(travel_v2_weight, 3),
                    "PHISHING_RESPONSE_v1": 0.82,
                    "PHISHING_RESPONSE_v2": 0.80,
                },
            }
        )

        phishing_v1_weight = 0.82 - (progress * 0.10)
        phishing_v2_weight = 0.65 + (progress * 0.15)

        WEIGHT_HISTORY.append(
            {
                "decision_id": f"historical_phish_{i}",
                "alert_type": "phishing",
                "prompt_variant": "PHISHING_RESPONSE_v2" if i > 8 else "PHISHING_RESPONSE_v1",
                "success": i > 4,
                "weights": {
                    "TRAVEL_CONTEXT_v1": 0.71,
                    "TRAVEL_CONTEXT_v2": 0.89,
                    "PHISHING_RESPONSE_v1": round(phishing_v1_weight, 3),
                    "PHISHING_RESPONSE_v2": round(phishing_v2_weight, 3),
                },
            }
        )


_sync_sdk_from_compat_state()
_refresh_compat_stats_from_sdk()
seed_weight_history()
