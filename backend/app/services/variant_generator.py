"""AE-01 graph-signal variant generator for AgentEvolver."""

from __future__ import annotations

import importlib
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Optional, Protocol, overload

from gae.evolution import (
    ARTIFACT_CONTEXT_POLICY,
    ARTIFACT_EVIDENCE_ORDER,
    ARTIFACT_PROMPT_MODULE,
    ARTIFACT_ROUTING_RULE,
    ARTIFACT_SCORING_THRESHOLD,
    VARIANT_CREATED,
    record_evolution_event,
)
from app.services import variant_registry as default_registry
from app.domains.soc.config import DEFAULT_CATEGORY
from app.services.variant_registry import CANDIDATE, VariantRecord
from app.db.graph_client import soc_decision_where

log = logging.getLogger(__name__)

WARM_START_REJECTION_COOLDOWN_DAYS = 30
COVERAGE_GAP_RATIO = 0.15
COVERAGE_GAP_MIN_TOTAL = 50
COVERAGE_GAP_MIN_MAX = 100


@dataclass
class GraphSignal:
    rule_id: str
    trigger_id: str
    artifact_type: str
    evidence: dict[str, Any]
    category: Optional[str]
    description: str


class EvolutionRule(Protocol):
    rule_id: str
    artifact_type: str
    description: str

    async def detect(self, graph_client: Any) -> Optional[GraphSignal]:
        ...

    def generate_variant(self, signal: GraphSignal) -> VariantRecord:
        ...


def _safe_slug(value: Any) -> str:
    text = str(value or "unknown").lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "unknown"


def _variant_id(rule_id: str, trigger_id: str) -> str:
    return f"ae_{_safe_slug(rule_id)}_{_safe_slug(trigger_id)}"[:96]


def _trigger_key(signal: GraphSignal) -> str:
    return f"{signal.rule_id}_{signal.trigger_id}"


def _event_epoch_seconds(event: dict[str, Any]) -> float:
    epoch = _as_float(event.get("timestamp_epoch"), 0.0)
    if epoch > 1e12:
        epoch = epoch / 1000
    return epoch


async def _consult_history(graph_client: Any, variant_id: str) -> dict[str, Any]:
    try:
        module = importlib.import_module("app.framework.evolution_ledger")
        get_variant_history = getattr(module, "get_variant_history")
        variant_created = getattr(module, "VARIANT_CREATED")
        promotion_approved = getattr(module, "PROMOTION_APPROVED")
        promotion_rejected = getattr(module, "PROMOTION_REJECTED")
        rollback = getattr(module, "ROLLBACK")
        events = await get_variant_history(graph_client, variant_id)
    except Exception as exc:
        log.debug("Variant history unavailable for %s: %s", variant_id, exc)
        return {"action": "proceed"}

    if not isinstance(events, list) or not events:
        return {"action": "proceed"}

    cooldown_epoch = time.time() - WARM_START_REJECTION_COOLDOWN_DAYS * 86400
    for event in reversed(events):
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("event_type") or "")
        if event_type == rollback:
            return {"action": "skip", "reason": "prior rollback"}
        if event_type == promotion_rejected:
            if _event_epoch_seconds(event) > cooldown_epoch:
                return {"action": "skip", "reason": "recent rejection"}
            return {"action": "proceed"}
        if event_type == promotion_approved:
            for earlier in events:
                if not isinstance(earlier, dict):
                    continue
                if earlier.get("event_type") != variant_created:
                    continue
                baseline_config = earlier.get("after_state")
                if isinstance(baseline_config, dict) and baseline_config:
                    return {
                        "action": "warm_start",
                        "baseline_config": dict(baseline_config),
                    }
            return {"action": "proceed"}

    return {"action": "proceed"}


def _record(
    signal: GraphSignal,
    config: dict[str, Any],
) -> VariantRecord:
    return VariantRecord(
        variant_id=_variant_id(signal.rule_id, signal.trigger_id),
        artifact_type=signal.artifact_type,
        category=signal.category,
        config=config,
        status=CANDIDATE,
        trigger_key=_trigger_key(signal),
        graph_trigger=signal.evidence,
        created_at=float(signal.evidence.get("timestamp_epoch") or 0.0),
    )


@overload
def _first_string(*values: Any, default: str = "") -> str:
    ...


@overload
def _first_string(*values: Any, default: None) -> str | None:
    ...


def _first_string(*values: Any, default: str | None = "") -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


async def _maybe_call(target: Any, *args: Any, **kwargs: Any) -> Any:
    result = target(*args, **kwargs) if callable(target) else target
    if hasattr(result, "__await__"):
        return await result
    return result


def _flatten_weights(raw: Any) -> list[float]:
    if raw is None:
        return []
    if hasattr(raw, "tolist"):
        raw = raw.tolist()
    if isinstance(raw, tuple):
        raw = list(raw)
    if isinstance(raw, list) and raw and isinstance(raw[0], (list, tuple)):
        raw = raw[0]
    if not isinstance(raw, list):
        return []
    return [_as_float(weight, 0.0) for weight in raw]


def _trajectory_mean(category_item: dict[str, Any], current: float) -> Optional[float]:
    for key in ("mean_14d_accuracy", "mean"):
        if key in category_item:
            return _as_float(category_item.get(key), current)

    for key in ("accuracy_14d", "rolling_accuracy_14d", "recent_accuracy"):
        values = category_item.get(key)
        if isinstance(values, list) and values:
            numeric = [_as_float(value, 0.0) for value in values[-14:]]
            return sum(numeric) / len(numeric)

    points = category_item.get("trajectory_points")
    if not isinstance(points, list):
        return None
    decision_count = int(_as_float(category_item.get("decision_count"), 0.0))
    relevant = [
        point
        for point in points
        if isinstance(point, dict)
        and int(_as_float(point.get("decisions"), 0.0)) <= decision_count
    ]
    if not relevant:
        relevant = [point for point in points if isinstance(point, dict)]
    recent = relevant[-14:]
    if not recent:
        return None
    accuracies = [_as_float(point.get("accuracy"), current) for point in recent]
    return sum(accuracies) / len(accuracies)


async def _load_accuracy_trajectory(graph_client: Any) -> dict[str, Any] | None:
    try:
        module = importlib.import_module("app.services.accuracy_trajectory")
    except ImportError:
        return None

    builder = getattr(module, "build_accuracy_trajectory", None)
    if builder is None:
        return None

    live_data: dict[str, int] = {}
    if graph_client is not None and hasattr(graph_client, "run_query"):
        try:
            rows = await graph_client.run_query(
                """
                MATCH (d:Decision)
                WHERE """ + soc_decision_where() + """
                RETURN d.category AS category, count(d) AS cnt
                """
            )
            for row in rows or []:
                if not isinstance(row, dict):
                    continue
                category = _first_string(row.get("category"))
                if not category or category == "unknown":
                    continue
                live_data[category] = int(_as_float(row.get("cnt"), 0.0))
        except Exception as exc:
            log.debug("Accuracy trajectory live decision query failed: %s", exc)

    trajectory = builder(live_data=live_data)
    return trajectory if isinstance(trajectory, dict) else None


def _live_dk_learning_state(category: str | None = None) -> dict[str, Any] | None:
    try:
        state_module = importlib.import_module("app.services.gae_state")
        config_module = importlib.import_module("app.domains.soc.config")
    except ImportError:
        return None

    get_scorer = getattr(state_module, "get_profile_scorer", None)
    categories = list(getattr(config_module, "SOC_CATEGORIES", []))
    factors = list(getattr(config_module, "SOC_FACTORS", []))
    if get_scorer is None or not categories:
        return None

    try:
        scorer = get_scorer()
    except Exception as exc:
        log.debug("Profile scorer unavailable for DK scan: %s", exc)
        return None

    if scorer is None or getattr(scorer, "_learning_strategy", None) is None:
        return None

    candidate_categories = [category] if category in categories else categories
    for candidate in candidate_categories:
        cat_index = categories.index(candidate)
        dk_weights = None
        if hasattr(scorer, "get_dk_weights"):
            try:
                dk_weights = scorer.get_dk_weights(cat_index)
            except Exception as exc:
                log.debug("DK weight read failed for %s: %s", candidate, exc)
                dk_weights = None
        weights = _flatten_weights(dk_weights)
        if not weights:
            continue

        phase = None
        if hasattr(scorer, "get_phase"):
            try:
                phase_raw = scorer.get_phase(cat_index)
                phase = str(getattr(phase_raw, "value", phase_raw))
            except Exception:
                phase = None

        return {
            "strategy": "two_phase",
            "category": candidate,
            "phase": phase,
            "dk_weights": weights,
            "factor_labels": factors[: len(weights)] or None,
            "evidence_type": "dk_weight_shift",
        }

    return None


class CampaignEscalateRule:
    rule_id = "RULE-CAMPAIGN-ESCALATE"
    artifact_type = ARTIFACT_ROUTING_RULE
    description = "Escalate graph-correlated campaign patterns"

    async def detect(self, graph_client: Any) -> Optional[GraphSignal]:
        try:
            module = importlib.import_module("app.services.cross_graph_discovery")
        except ImportError:
            return None
        service = getattr(module, "discovery_service", None)
        if service is None or not hasattr(service, "refresh"):
            return None
        envelope = await service.refresh("soc", graph_client)
        discoveries = envelope.get("discoveries", []) if isinstance(envelope, dict) else []
        for discovery in discoveries:
            if not isinstance(discovery, dict):
                continue
            haystack = " ".join(
                str(discovery.get(key, ""))
                for key in ("type", "title", "description", "category_summary")
            ).lower()
            discovered_campaign_id = _first_string(
                discovery.get("campaign_id"),
                discovery.get("pattern_id"),
                discovery.get("discovery_id"),
            )
            if "campaign" not in haystack and not str(discovered_campaign_id).lower().startswith("c-"):
                continue
            campaign_id = discovered_campaign_id or "C-007"
            evidence = dict(discovery)
            evidence.setdefault("campaign_id", campaign_id)
            category = _first_string(discovery.get("category"), default=DEFAULT_CATEGORY)
            return GraphSignal(
                rule_id=self.rule_id,
                trigger_id=campaign_id,
                artifact_type=self.artifact_type,
                evidence=evidence,
                category=category,
                description=f"Campaign pattern {campaign_id} suggests escalation routing",
            )
        return None

    def generate_variant(self, signal: GraphSignal) -> VariantRecord:
        campaign_id = _first_string(signal.evidence.get("campaign_id"), signal.trigger_id, default="C-007")
        config = {
            "action": "escalate",
            "trigger_categories": signal.evidence.get(
                "trigger_categories",
                ["credential_access", "lateral_movement"],
            ),
            "campaign_pattern": campaign_id,
            "min_confidence": 0.70,
        }
        return _record(signal, config)


DRIFT_WINDOW_DAYS = 14
DECLINE_THRESHOLD_PP = 3.0
MIN_DRIFT_DECISIONS = 10


def _is_correct_decision(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "correct", "yes"}:
            return True
        if normalized in {"false", "0", "incorrect", "wrong", "no"}:
            return False
    return None


def _aggregate_accuracy_rows(rows: Any) -> dict[str, dict[str, int]]:
    totals: dict[str, dict[str, int]] = {}
    if not isinstance(rows, list):
        return totals
    for row in rows:
        if not isinstance(row, dict):
            continue
        category = _first_string(row.get("category"))
        correct = _is_correct_decision(row.get("correct"))
        if not category or correct is None:
            continue
        stats = totals.setdefault(category, {"total": 0, "correct": 0})
        stats["total"] += 1
        if correct:
            stats["correct"] += 1
    return totals


async def _get_per_category_accuracy_trends(graph_client: Any) -> dict[str, dict[str, Any]]:
    run_query = getattr(graph_client, "run_query", None)
    if run_query is None:
        return {}

    now_ms = int(time.time() * 1000)
    window_ms = DRIFT_WINDOW_DAYS * 86400 * 1000
    recent_cutoff = now_ms - window_ms
    prior_cutoff = now_ms - (2 * window_ms)

    recent_query = (
        f"MATCH (d:Decision) WHERE {soc_decision_where()} "
        f"AND d.outcome IS NOT NULL AND d.correct IS NOT NULL "
        f"AND d.category IS NOT NULL AND d.verified_at_epoch >= {recent_cutoff} "
        f"AND d.verified_at_epoch < {now_ms} "
        "RETURN d.category AS category, d.correct AS correct"
    )
    prior_query = (
        f"MATCH (d:Decision) WHERE {soc_decision_where()} "
        f"AND d.outcome IS NOT NULL AND d.correct IS NOT NULL "
        f"AND d.category IS NOT NULL AND d.verified_at_epoch >= {prior_cutoff} "
        f"AND d.verified_at_epoch < {recent_cutoff} "
        "RETURN d.category AS category, d.correct AS correct"
    )

    try:
        recent_rows = await run_query(recent_query)
        prior_rows = await run_query(prior_query)
    except Exception as exc:
        log.warning("Unable to load per-category accuracy drift trends: %s", exc)
        return {}

    recent = _aggregate_accuracy_rows(recent_rows)
    prior = _aggregate_accuracy_rows(prior_rows)
    trends: dict[str, dict[str, Any]] = {}
    for category in sorted(set(recent) & set(prior)):
        recent_total = recent[category]["total"]
        prior_total = prior[category]["total"]
        if recent_total < MIN_DRIFT_DECISIONS or prior_total < MIN_DRIFT_DECISIONS:
            continue
        recent_accuracy = recent[category]["correct"] / recent_total
        prior_accuracy = prior[category]["correct"] / prior_total
        decline_pp = (prior_accuracy - recent_accuracy) * 100
        if decline_pp + 1e-9 < DECLINE_THRESHOLD_PP:
            continue
        trends[category] = {
            "recent_accuracy": recent_accuracy,
            "prior_accuracy": prior_accuracy,
            "recent_total": recent_total,
            "prior_total": prior_total,
            "decline_pp": decline_pp,
        }
    return trends


class DriftThresholdRule:
    rule_id = "RULE-DRIFT-THRESHOLD"
    artifact_type = ARTIFACT_SCORING_THRESHOLD
    description = "Lower threshold for AMBER drift categories"

    async def detect(self, graph_client: Any) -> Optional[GraphSignal]:
        try:
            trends = await _get_per_category_accuracy_trends(graph_client)
        except Exception as exc:
            log.warning("Drift threshold detection failed: %s", exc)
            return None

        if not trends:
            return None
        category, trend = max(
            trends.items(),
            key=lambda item: (_as_float(item[1].get("decline_pp")), item[0]),
        )
        decline_pp = _as_float(trend.get("decline_pp"))
        evidence = {
            "category": category,
            "recent_accuracy": round(_as_float(trend.get("recent_accuracy")), 4),
            "prior_accuracy": round(_as_float(trend.get("prior_accuracy")), 4),
            "decline_pp": round(decline_pp, 1),
            "recent_decisions": int(_as_float(trend.get("recent_total"))),
            "prior_decisions": int(_as_float(trend.get("prior_total"))),
            "detection_method": "per_category_accuracy_trend",
        }
        return GraphSignal(
            rule_id=self.rule_id,
            trigger_id=f"{category}_drift",
            artifact_type=self.artifact_type,
            evidence=evidence,
            category=category,
            description=f"Accuracy declined {decline_pp:.1f}pp for {category} over 14 days",
        )

    def generate_variant(self, signal: GraphSignal) -> VariantRecord:
        current_value = _as_float(signal.evidence.get("current_value"), 0.90)
        proposed_value = _as_float(signal.evidence.get("proposed_value"), 0.85)
        category = _first_string(signal.category, signal.evidence.get("category"))
        config = {
            "category": category,
            "parameter": "auto_approve_threshold",
            "current_value": current_value,
            "proposed_value": proposed_value,
            "auto_approve_action": "suppress",
            "reduction_pp": round((current_value - proposed_value) * 100, 2),
        }
        return _record(signal, config)


class OverridePromptRule:
    rule_id = "RULE-OVERRIDE-PROMPT"
    artifact_type = ARTIFACT_PROMPT_MODULE
    description = "Revise prompt framing for activated override patterns"

    async def detect(self, graph_client: Any) -> Optional[GraphSignal]:
        try:
            module = importlib.import_module("app.services.override_detector")
        except ImportError:
            return None
        detector = getattr(module, "override_detector", None)
        if detector is None:
            return None
        status = detector.status() if hasattr(detector, "status") else {}
        activated = bool(status.get("activated", getattr(detector, "activated", False)))
        if not activated:
            return None
        examples = getattr(detector, "examples", [])
        first = examples[0] if examples else {}
        pattern = _first_string(
            status.get("pattern"),
            first.get("pattern") if isinstance(first, dict) else None,
            default="high_conf_suppress_override",
        )
        category = _first_string(first.get("category") if isinstance(first, dict) else None, default=None)
        evidence = {
            "override_pattern": pattern,
            "example_count": status.get("example_count", getattr(detector, "example_count", 0)),
            "threshold": status.get("threshold"),
            "category": category,
        }
        return GraphSignal(
            rule_id=self.rule_id,
            trigger_id=pattern,
            artifact_type=self.artifact_type,
            evidence=evidence,
            category=category,
            description=f"Override pattern {pattern} is activated",
        )

    def generate_variant(self, signal: GraphSignal) -> VariantRecord:
        pattern = _first_string(signal.evidence.get("override_pattern"), signal.trigger_id)
        config = {
            "override_pattern": pattern,
            "prompt_id_current": "SUPPRESSION_v1",
            "prompt_id_variant": "SUPPRESSION_v2",
            "framing_change": "Add explicit factor contribution breakdown",
        }
        return _record(signal, config)


class DKReorderRule:
    rule_id = "RULE-DK-REORDER"
    artifact_type = ARTIFACT_EVIDENCE_ORDER
    description = "Reorder evidence presentation from DK weights"
    _default_factors = [
        "identity_risk",
        "asset_criticality",
        "threat_intel_enrichment",
        "behavioral_anomaly",
        "policy_context",
        "campaign_correlation",
    ]

    async def detect(self, graph_client: Any) -> Optional[GraphSignal]:
        data = _live_dk_learning_state()
        if not isinstance(data, dict):
            return None
        if data.get("strategy") == "continuous" or data.get("dk_weights") is None:
            return None
        numeric = _flatten_weights(data.get("dk_weights"))
        if not numeric:
            return None
        if max(numeric) <= 0:
            return None
        evidence = dict(data)
        evidence["weights"] = numeric
        return GraphSignal(
            rule_id=self.rule_id,
            trigger_id="dk_reorder",
            artifact_type=self.artifact_type,
            evidence=evidence,
            category=data.get("category"),
            description="Two-phase DK weights changed evidence ordering",
        )

    def generate_variant(self, signal: GraphSignal) -> VariantRecord:
        weights = [_as_float(weight, 0.0) for weight in signal.evidence.get("weights", [])]
        labels = signal.evidence.get("factor_labels") or self._default_factors
        labels = [str(label) for label in labels]
        pairs = list(zip(labels, weights))
        pairs.sort(key=lambda item: item[1], reverse=True)
        top_factor, top_weight = pairs[0] if pairs else ("threat_intel_enrichment", 0.34)
        config = {
            "new_order": [factor for factor, _weight in pairs],
            "top_factor": top_factor,
            "top_weight": round(float(top_weight), 4),
        }
        return _record(signal, config)


class PlateauContextRule:
    rule_id = "RULE-PLATEAU-CONTEXT"
    artifact_type = ARTIFACT_CONTEXT_POLICY
    description = "Expand graph context when accuracy is flat below target"

    async def detect(self, graph_client: Any) -> Optional[GraphSignal]:
        trajectory = await _load_accuracy_trajectory(graph_client)
        if not isinstance(trajectory, dict):
            return None
        categories = trajectory.get("categories")
        if not isinstance(categories, list):
            return None
        for item in categories:
            if not isinstance(item, dict):
                continue
            category = _first_string(item.get("category"))
            if not category or category == "overall":
                continue
            current = _as_float(
                item.get("rolling_14d_accuracy", item.get("current_accuracy", item.get("accuracy"))),
                0.0,
            )
            mean = _trajectory_mean(item, current)
            if mean is None:
                continue
            if current < 0.85 and abs(current - mean) <= 0.01:
                evidence = dict(item)
                evidence["current_accuracy"] = current
                evidence["mean_14d_accuracy"] = mean
                return GraphSignal(
                    rule_id=self.rule_id,
                    trigger_id=f"{category}_plateau",
                    artifact_type=self.artifact_type,
                    evidence=evidence,
                    category=category,
                    description=f"Accuracy plateau below target for {category}",
                )
        return None

    def generate_variant(self, signal: GraphSignal) -> VariantRecord:
        config = {
            "category": signal.category or DEFAULT_CATEGORY,
            "current_accuracy": round(_as_float(signal.evidence.get("current_accuracy"), 0.83), 4),
            "theta_target": 0.85,
            "traversal_add": "campaign_correlation",
            "traversal_remove": None,
        }
        return _record(signal, config)


class CoverageGapRule:
    rule_id = "RULE-COVERAGE-GAP"
    artifact_type = ARTIFACT_CONTEXT_POLICY
    description = "Detect under-covered categories for graph traversal enrichment"

    async def detect(self, graph_client: Any) -> Optional[GraphSignal]:
        try:
            rows = await graph_client.run_query(
                f"MATCH (d:Decision) WHERE {soc_decision_where()} "
                "AND d.category IS NOT NULL "
                "RETURN d.category AS category, count(*) AS cnt"
            )
            counts: dict[str, int] = {}
            for row in rows or []:
                if not isinstance(row, dict):
                    continue
                category = _first_string(row.get("category"))
                if not category:
                    continue
                count = int(_as_float(row.get("cnt"), 0.0))
                if count < 0:
                    continue
                counts[category] = count

            if not counts:
                return None

            max_count = max(counts.values())
            if max_count < COVERAGE_GAP_MIN_MAX:
                return None

            candidates: list[tuple[float, int, str]] = []
            for category, count in counts.items():
                ratio = count / max_count if max_count else 0.0
                if ratio < COVERAGE_GAP_RATIO and count < COVERAGE_GAP_MIN_TOTAL:
                    candidates.append((ratio, count, category))

            if not candidates:
                return None

            coverage_ratio, current_decisions, category = min(candidates, key=lambda item: (item[0], item[1], item[2]))
            evidence = {
                "category": category,
                "current_decisions": current_decisions,
                "max_category_decisions": max_count,
                "coverage_ratio": round(coverage_ratio, 4),
                "gap_threshold": COVERAGE_GAP_RATIO,
                "detection_method": "per_category_coverage_gap",
            }
            return GraphSignal(
                rule_id=self.rule_id,
                trigger_id=f"{category}_coverage_gap",
                artifact_type=self.artifact_type,
                evidence=evidence,
                category=category,
                description=(
                    f"Coverage gap: {category} has {current_decisions} decisions "
                    f"({coverage_ratio:.2%} of max {max_count})"
                ),
            )
        except Exception as exc:
            log.debug("Coverage gap detection failed: %s", exc)
            return None

    def generate_variant(self, signal: GraphSignal) -> VariantRecord:
        category = signal.evidence.get("category") or signal.category or "unknown"
        return _record(
            signal,
            {
                "category": category,
                "policy": "deep_context",
                "current_decisions": signal.evidence.get("current_decisions"),
                "max_category_decisions": signal.evidence.get("max_category_decisions"),
                "coverage_ratio": signal.evidence.get("coverage_ratio"),
                "description": f"Extended graph traversal for under-covered {category}",
            },
        )


class VariantGenerator:
    def __init__(self, rules: list[EvolutionRule] | None = None, registry: Any = None):
        self.rules = list(rules) if rules is not None else [
            CampaignEscalateRule(),
            DriftThresholdRule(),
            OverridePromptRule(),
            DKReorderRule(),
            PlateauContextRule(),
            CoverageGapRule(),
        ]
        self.registry = registry or default_registry

    def register_rule(self, rule: EvolutionRule) -> None:
        self.rules.append(rule)

    async def scan_for_opportunities(self, graph_client: Any) -> list[VariantRecord]:
        generated: list[VariantRecord] = []
        for rule in self.rules:
            try:
                signal = await rule.detect(graph_client)
                if signal is None:
                    continue
                trigger_key = _trigger_key(signal)
                if self.registry.has_active_or_shadow(trigger_key):
                    continue
                candidate_id = _variant_id(signal.rule_id, signal.trigger_id)
                history = await _consult_history(graph_client, candidate_id)
                history_action = history.get("action")
                if history_action == "skip":
                    log.info(
                        "Skipping variant %s due to history: %s",
                        candidate_id,
                        history.get("reason", "unspecified"),
                    )
                    continue
                record = rule.generate_variant(signal)
                warm_started = history_action == "warm_start"
                metadata = {
                    "trigger_key": trigger_key,
                    "rule_id": signal.rule_id,
                    "warm_started": warm_started,
                }
                if warm_started:
                    baseline_config = history.get("baseline_config")
                    if isinstance(baseline_config, dict) and baseline_config:
                        warm_config = dict(baseline_config)
                        warm_config["category"] = record.config.get("category") or record.category
                        record = VariantRecord(
                            variant_id=record.variant_id,
                            artifact_type=record.artifact_type,
                            category=record.category,
                            config=warm_config,
                            status=record.status,
                            trigger_key=record.trigger_key,
                            graph_trigger=record.graph_trigger,
                            created_at=record.created_at,
                            promoted_at=record.promoted_at,
                        )
                        metadata["baseline_variant_id"] = candidate_id
                    else:
                        warm_started = False
                        metadata["warm_started"] = False
                await record_evolution_event(
                    graph_client,
                    event_type=VARIANT_CREATED,
                    variant_id=record.variant_id,
                    artifact_type=record.artifact_type,
                    description=signal.description,
                    before_state={},
                    after_state=record.config,
                    graph_context=signal.evidence,
                    metadata=metadata,
                )
                registered = self.registry.register_variant(record)
                generated.append(registered)
            except Exception as exc:
                log.warning(
                    "Evolution rule %s failed: %s",
                    getattr(rule, "rule_id", type(rule).__name__),
                    exc,
                )
        return generated


__all__ = [
    "CampaignEscalateRule",
    "CoverageGapRule",
    "DKReorderRule",
    "DriftThresholdRule",
    "EvolutionRule",
    "GraphSignal",
    "OverridePromptRule",
    "PlateauContextRule",
    "VariantGenerator",
]
