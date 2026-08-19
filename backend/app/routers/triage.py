"""
Alert Triage API - Tab 3
Graph-based reasoning and closed-loop execution
"""
import contextlib
import inspect
import json
import logging
import os
import time
from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import List, Dict, Any, Iterator, cast
from datetime import datetime
import uuid

from app.services.agent import agent
from app.services.reasoning import narrator
from app.services.situation import analyze_situation
from app.services.narrative import get_narrative_provider
from app.services.feedback import (
    process_outcome,
    get_feedback_status,
    get_feedback_record,
    get_reward_summary,
)
from app.services.policy import detect_policy_conflicts, get_conflict_history
from app.services.triage import get_decision_factors, append_confidence_snapshot
from app.domains.soc.factor_vector import validated_factor_vector
from app.services.audit import record_decision
from app.services.event_bus import event_bus, DecisionMade, OutcomeVerified, GraphMutated
from app.services.soc_context_split import split_soc_security_context
from app.services.soc_situation_pattern import build_campaign_context_payload
from ci_platform.copilot_core import EntityCache, EntityContextCacheAdapter


def _node_id(entity: dict, prefix: str = "") -> str:
    """Get node ID from entity dict -- AGE uses alert_id/user_id/etc, AGE uses id."""
    return entity.get("id") or entity.get(f"{prefix}_id") or entity.get(f"{prefix}id") or "unknown"
from app.services.gae_state import get_learning_state, save_learning_state, get_profile_scorer
import dataclasses
import numpy as np
from app.core.state_manager import state_manager
from app.db.graph_client import graph_client
from app.graph_schema import _S
from app.models.responses import AlertQueueResponse, DecisionFactorsResponse, ProfileResponse
from app.models.schemas import ProcessAlertRequest, OutcomeRequest
from app.domains.soc.config import (
    SOCDomainConfig,
    SOC_AUTO_APPROVE_THRESHOLDS,
    SOC_CATEGORY_CONFIDENCE_FLOORS,
    SOC_AGENT_ZONE_ELEVATED,
    LEARNING_ENABLED,
    is_learning_enabled,
    N_FACTORS,
    SOC_FACTORS,
)
from app.domains.soc.orchestrator import (
    compute_factor_vector as _compute_factor_vector,
    compute_factor_vector_with_provenance,
)
from gae.scoring import score_alert

logger = logging.getLogger(__name__)
_REFERRAL_COUNT_SOURCE = os.environ.get("REFERRAL_COUNT_SOURCE", "legacy").strip().lower()
_shadow_log = logging.getLogger("soc.referral.shadow")


async def _legacy_sequence_count(source_id: str | None) -> int:
    method = getattr(graph_client, "_legacy_sequence_count", None)
    if method is not None:
        result = method(source_id)
        if not inspect.isawaitable(result):
            return int(await graph_client.get_sequence_count(source_id))
        return int((await result) or 0)
    # AGE deployments without the legacy helper retain the established count
    # semantics until the Alert-based implementation is provided by the client.
    return int(await graph_client.get_sequence_count(source_id))


async def _legacy_cross_category_count(user_id: str | None) -> int:
    method = getattr(graph_client, "_legacy_cross_category_count", None)
    if method is not None:
        result = method(user_id)
        if not inspect.isawaitable(result):
            return int(await graph_client.get_cross_category_count(user_id))
        return int((await result) or 0)
    # See _legacy_sequence_count: preserve behavior until the client exposes
    # a dedicated Alert-based legacy query.
    return int(await graph_client.get_cross_category_count(user_id))

# Backward-compatible monkeypatch hook used by existing tests.
compute_factor_vector = _compute_factor_vector


_SOC_PERF_FALSE_VALUES = {"", "0", "false", "no", "off"}
_SOC_ENTITY_CACHE_FALSE_VALUES = _SOC_PERF_FALSE_VALUES
_SOC_DECISION_PIPELINE_SHADOW_FALSE_VALUES = _SOC_PERF_FALSE_VALUES
_SOC_ENTITY_CACHE = EntityCache(max_size=4096, source="soc.entity_context_cache")
_SOC_ENTITY_CONTEXT_CACHE = EntityContextCacheAdapter(_SOC_ENTITY_CACHE, enabled=True)
_SOC_PERF_ALWAYS_SUMMARY_PHASES = {
    "analyze_request_total",
    "outcome_request_total",
}


def _soc_perf_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _soc_perf_enabled() -> bool:
    return os.getenv("SOC_PERF_TRACE_ENABLED", "false").strip().lower() not in _SOC_PERF_FALSE_VALUES


def _soc_entity_cache_enabled() -> bool:
    return os.getenv("USE_ENTITY_CACHE", "false").strip().lower() not in _SOC_ENTITY_CACHE_FALSE_VALUES


def _soc_decision_pipeline_shadow_enabled() -> bool:
    return (
        os.getenv("USE_SOC_DECISION_PIPELINE_SHADOW", "false").strip().lower()
        not in _SOC_DECISION_PIPELINE_SHADOW_FALSE_VALUES
    )


def _soc_entity_cache_diagnostics() -> Dict[str, Any]:
    stats = _SOC_ENTITY_CONTEXT_CACHE.stats()
    status = _SOC_ENTITY_CONTEXT_CACHE.get_status()
    return {
        "enabled": _soc_entity_cache_enabled(),
        "adapter_enabled": status.enabled,
        "hits": stats.hits,
        "misses": stats.misses,
        "loads": stats.loads,
        "invalidations": stats.invalidations,
        "evictions": stats.evictions,
        "size": stats.size,
        "max_size": stats.max_size,
    }


def _soc_reset_entity_cache_for_tests() -> None:
    global _SOC_ENTITY_CACHE, _SOC_ENTITY_CONTEXT_CACHE
    _SOC_ENTITY_CACHE = EntityCache(max_size=4096, source="soc.entity_context_cache")
    _SOC_ENTITY_CONTEXT_CACHE = EntityContextCacheAdapter(_SOC_ENTITY_CACHE, enabled=True)


def _soc_invalidate_entity_context(domain: str, kind: str, identifier: str) -> bool:
    return cast(bool, _SOC_ENTITY_CONTEXT_CACHE.invalidate(domain, kind, identifier))


async def _soc_maybe_attach_decision_pipeline_shadow(
    response: Dict[str, Any],
    *,
    alert_data: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    if not _soc_decision_pipeline_shadow_enabled():
        return response

    from app.services.soc_domain_profile import run_soc_decision_pipeline_shadow

    try:
        shadow = await run_soc_decision_pipeline_shadow(
            response,
            alert=alert_data,
            context=context,
        )
    except Exception as exc:
        shadow = {
            "enabled": True,
            "matched": False,
            "status": "shadow_failed",
            "error_type": type(exc).__name__,
            "error": "shadow pipeline unavailable",
            "differences": [],
            "excluded_fields": [
                "decision_id",
                "elapsed_seconds",
                "narrative",
                "rationale",
                "timestamp",
                "timestamp_epoch",
            ],
            "field_coverage": [],
            "phase_order": [],
            "background_status": {},
            "persistence_strategy": "shadow_noop",
            "side_effects": {
                "decision_writes": 0,
                "outcome_writes": 0,
                "proof_writes": 0,
                "counter_updates": 0,
                "graph_mutations": 0,
            },
        }
    diagnostics = dict(response.get("_diagnostics") or {})
    diagnostics["soc_decision_pipeline_shadow"] = shadow
    response["_diagnostics"] = diagnostics
    return response


async def _soc_get_security_context_for_analyze(alert_id: str) -> Dict[str, Any]:
    if not _soc_entity_cache_enabled():
        return cast(Dict[str, Any], await graph_client.get_security_context(alert_id))

    flat_context = cast(Dict[str, Any], await graph_client.get_security_context(alert_id))
    split = split_soc_security_context(flat_context)
    if split.cache_key is None:
        return split.recompose_for_current_route()

    async def _stable_entity_loader() -> Dict[str, Any]:
        return dict(split.stable_entity)

    stable_entity = await _SOC_ENTITY_CONTEXT_CACHE.get_context(
        split.cache_key.domain,
        split.cache_key.kind,
        split.cache_key.identifier,
        _stable_entity_loader,
        metadata={"route": "/api/alert/analyze", "context_bucket": "stable_entity"},
        source="soc.analyze.security_context_split",
    )
    return {
        **split.fresh_alert,
        **dict(stable_entity or {}),
        **split.non_cacheable,
        **split.ambiguous,
    }


def _soc_perf_trace_level() -> str:
    level = os.getenv("SOC_PERF_TRACE_LEVEL", "summary").strip().lower()
    return level if level in {"summary", "detailed"} else "summary"


def _soc_perf_output_path() -> Path:
    raw = os.getenv("SOC_PERF_TRACE_OUTPUT", "scratch/temp/soc_perf_trace.jsonl")
    path = Path(raw)
    return path if path.is_absolute() else _soc_perf_repo_root() / path


def _soc_perf_slow_ms() -> float:
    try:
        return float(os.getenv("SOC_PERF_TRACE_SLOW_MS", "500"))
    except ValueError:
        return 500.0


def _soc_perf_safe_value(key: str, value: Any) -> Any:
    key_l = key.lower()
    if any(secret in key_l for secret in ("password", "secret", "token", "authorization", "dsn")):
        return "***"
    if "factor_vector" in key_l or key_l in {"f", "fv", "vector"}:
        try:
            return {"len": len(value)}
        except Exception:
            return "<redacted>"
    if "cypher" in key_l or "query" in key_l:
        return "<redacted>"
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple, set)):
        return {"len": len(value)}
    if isinstance(value, dict):
        return {str(k): _soc_perf_safe_value(str(k), v) for k, v in value.items()}
    return str(value)


def _soc_perf_sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    return {
        str(key): _soc_perf_safe_value(str(key), value)
        for key, value in (metadata or {}).items()
        if value is not None
    }


def _soc_perf_start() -> float:
    return time.perf_counter()


def _soc_perf_emit_duration(
    phase: str,
    started: float,
    *,
    route: str,
    status: str = "ok",
    exception_type: str | None = None,
    alert_id: str | None = None,
    decision_id: str | None = None,
    category: str | None = None,
    action: str | None = None,
    **metadata: Any,
) -> None:
    if not _soc_perf_enabled():
        return
    duration_ms = (time.perf_counter() - started) * 1000.0
    if (
        _soc_perf_trace_level() != "detailed"
        and phase not in _SOC_PERF_ALWAYS_SUMMARY_PHASES
        and duration_ms < _soc_perf_slow_ms()
    ):
        return
    event = {
        "event_type": "phase_timing",
        "phase": phase,
        "route": route,
        "duration_ms": round(duration_ms, 3),
        "status": status,
        "exception_type": exception_type,
        "graph_name": os.getenv("AGE_GRAPH_NAME"),
        "alert_id": alert_id,
        "decision_id": decision_id,
        "category": category,
        "action": action,
        "metadata": _soc_perf_sanitize_metadata(metadata),
        "timestamp_epoch_ms": int(time.time() * 1000),
    }
    try:
        output_path = _soc_perf_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, sort_keys=True) + "\n")
    except Exception:
        pass


@contextlib.contextmanager
def _soc_perf_phase(
    phase: str,
    *,
    route: str,
    alert_id: str | None = None,
    decision_id: str | None = None,
    category: str | None = None,
    action: str | None = None,
    **metadata: Any,
) -> Iterator[None]:
    started = _soc_perf_start()
    status = "ok"
    exception_type = None
    try:
        yield
    except Exception as exc:
        status = "error"
        exception_type = type(exc).__name__
        raise
    finally:
        _soc_perf_emit_duration(
            phase,
            started,
            route=route,
            status=status,
            exception_type=exception_type,
            alert_id=alert_id,
            decision_id=decision_id,
            category=category,
            action=action,
            **metadata,
        )


def _soc_learning_enabled() -> bool:
    """Runtime SOC learning gate with legacy route-level monkeypatch support."""
    from app.domains.soc import config as _soc_config

    if LEARNING_ENABLED != _soc_config.LEARNING_ENABLED:
        return bool(LEARNING_ENABLED)
    return is_learning_enabled()


def _soc_effective_conservation_status(health: Dict[str, Any]) -> tuple[str, str | None]:
    """Return the verified conservation status without manufacturing GREEN."""
    raw_status = str((health or {}).get("status") or "UNKNOWN").upper()
    if bool((health or {}).get("auto_pause_active")):
        return "RED", "auto_pause_active"

    if raw_status not in {"GREEN", "AMBER", "RED", "CALIBRATING", "UNKNOWN"}:
        return "UNKNOWN", "unrecognized_learning_health_status"

    return raw_status, None


router = APIRouter()


def _validate_scoring_factor_vector(factor_vector) -> np.ndarray:
    if factor_vector is None:
        raise ValueError(f"factor_vector must have {N_FACTORS} elements, got None")
    try:
        vector = np.asarray(factor_vector, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"factor_vector must have {N_FACTORS} elements, got invalid") from exc
    actual = int(vector.size)
    if actual != N_FACTORS:
        raise ValueError(f"factor_vector must have {N_FACTORS} elements, got {actual}")
    if not np.all(np.isfinite(vector)):
        raise ValueError(f"factor_vector must have {N_FACTORS} finite elements")
    return vector.reshape(1, -1)


def _rl_soc_config():
    from app.domains.soc import config as soc_config

    return soc_config


def _rl_bool(value: Any) -> bool:
    return value is True or str(value).lower() == "true"


# ============================================================================
# GET /api/alerts/queue - Alert Queue
# ============================================================================

@router.get("/alerts/queue", response_model=AlertQueueResponse)
async def get_alert_queue():
    """
    Get list of pending alerts for triage.
    Returns simplified alert list for the sidebar.
    """
    print("[TRIAGE] GET /alerts/queue called")

    try:
        # Query AGE for pending alerts
        query = """
        MATCH (alert:Alert {status: 'pending'})
        MATCH (alert)-[:INVOLVES]->(user:User)
        MATCH (alert)-[:DETECTED_ON]->(asset:Asset)
        RETURN alert, user.name as user_name, asset.hostname as asset_hostname
        ORDER BY alert.timestamp_epoch DESC
        LIMIT 50
        """

        print("[TRIAGE] Querying AGE for pending alerts...")
        results = await graph_client.run_query(query)
        print(f"[TRIAGE] AGE returned {len(results)} results")

        alerts = []
        for record in results:
            alert = record["alert"]
            alerts.append({
                "id": _node_id(alert, "alert"),
                "alert_type": alert.get("alert_type", "unknown"),
                "severity": alert.get("severity", "medium"),
                "asset_hostname": record.get("asset_hostname", "unknown"),
                "user_name": record.get("user_name", "unknown"),
                "timestamp": alert.get("timestamp_epoch", alert.get("timestamp", 0)),
                "status": alert.get("status", "pending"),
                "source_location": alert.get("source_location", "Unknown")
            })

        print(f"[TRIAGE] Returning {len(alerts)} alerts from AGE")
        response = {"alerts": alerts}
        print(f"[TRIAGE] Response structure: {response}")
        return response

    except Exception as e:
        print(f"[ERROR] Failed to fetch alert queue: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch alerts from AGE: {str(e)}"
        )


# ============================================================================
# POST /api/alert/analyze - Analyze Alert with Graph Traversal
# ============================================================================

@router.post("/alert/analyze")
async def analyze_alert(request: ProcessAlertRequest):
    """
    Analyze an alert by traversing the security graph.
    Returns full context, recommendation, and graph data for visualization.

    GAE-2d: Uses GAE scoring pipeline (Eq. 4) instead of hardcoded factors.
    Writes Decision node to AGE after scoring.  Emits DecisionMade +
    GraphMutated events (design principle: every graph mutation emits events).
    """
    _perf_route = "/api/alert/analyze"
    _perf_alert_id = getattr(request, "alert_id", None)
    _perf_total_started = _soc_perf_start()
    _perf_total_status = "ok"
    _perf_total_exception = None

    # Guard: ProfileScorer must be attached before any scoring attempt
    with _soc_perf_phase("scorer_readiness", route=_perf_route, alert_id=_perf_alert_id):
        from app.services.gae_state import get_profile_scorer as _get_scorer, init_learning_state as _init_ls
        _scorer = _get_scorer()
        if _scorer is None:
            try:
                _init_ls()
                _scorer = _get_scorer()
            except Exception:
                pass
        if _scorer is None:
            _perf_total_status = "error"
            _perf_total_exception = "HTTPException"
            raise HTTPException(
                status_code=503,
                detail="Scorer not ready -- backend restarting or reset in progress"
            )

    try:
        with _soc_perf_phase("request_parse", route=_perf_route, alert_id=_perf_alert_id):
            alert_id = request.alert_id

        # ====================================================================
        # Step 1: Get full alert details
        # ====================================================================
        with _soc_perf_phase("alert_lookup", route=_perf_route, alert_id=alert_id):
            alert_data = await graph_client.get_alert(alert_id)

        if not alert_data:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

        # ====================================================================
        # Step 2: Get security context (47 nodes) — kept for key_facts/narrative
        # ====================================================================
        with _soc_perf_phase("security_context_lookup", route=_perf_route, alert_id=alert_id):
            context = await _soc_get_security_context_for_analyze(alert_id)

        if not context:
            raise HTTPException(status_code=404, detail=f"Context for {alert_id} not found")

        # ====================================================================
        # Step 3: Situation Analysis (Loop 1: Context Intelligence)
        # ====================================================================
        with _soc_perf_phase("category_resolution", route=_perf_route, alert_id=alert_id):
            alert_type = context.get("alert_type") or "unknown"
            situation_analysis = analyze_situation(alert_type, context)
            from app.domains.soc.config import resolve_alert_category
            alert_category = resolve_alert_category(alert_type)
        if alert_category == "unclassified":
            logger.warning(
                "[TRIAGE] Unclassified alert_type=%r for alert_id=%s; skipping ProfileScorer",
                alert_type,
                alert_id,
            )
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "unclassified_alert_type",
                    "alert_type": alert_type,
                    "message": "Alert type is not mapped to a scorable SOC category.",
                },
            )

        # ====================================================================
        # Step 4: GAE Scoring Pipeline (GAE-2d — replaces agent.decide())
        #
        # 4a. Compute factor vector via orchestrator (FactorComputers → AGE, one per factor)
        # 4b. score_alert: Eq. 4  P(action|alert) = softmax(f·Wᵀ / τ)
        # ====================================================================
        with _soc_perf_phase(
            "factor_vector_construction",
            route=_perf_route,
            alert_id=alert_id,
            category=alert_category,
        ):
            print(f"[GAE] Computing factor vector for {alert_id}...")
            computers = SOCDomainConfig.get_factor_computers()
            if compute_factor_vector is not _compute_factor_vector:
                f = await compute_factor_vector(alert_data, computers, graph_client)
                factor_provenance = {
                    name: {
                        "value": float(value),
                        "source": "test_override",
                        "detail": "factor vector supplied by compatibility hook",
                    }
                    for name, value in zip(SOC_FACTORS, f.flatten().tolist())
                }
            else:
                f, factor_provenance = await compute_factor_vector_with_provenance(
                    alert_data, computers, graph_client
                )
            f_2d = f.reshape(1, -1)  # kept for legacy reference; ProfileScorer uses f.flatten()

        # DEPRECATED v5.0: W-matrix scoring replaced by ProfileScorer
        # W       = get_learning_state().W
        # scoring = score_alert(f_2d, W, actions, tau)

        with _soc_perf_phase(
            "scorer_decision",
            route=_perf_route,
            alert_id=alert_id,
            category=alert_category,
            factor_vector_len=len(f.flatten()),
        ):
            from app.domains.soc.config import SCORER_ACTIONS
            scorer_actions = list(SCORER_ACTIONS)  # A=4 classification actions (ProfileScorer axis-1)
            tau     = SOCDomainConfig.get_temperature()  # tau=0.1 (V3B validated, ECE=0.036)

            # v5.0: ProfileScorer centroid-proximity scoring (EXP-E1 validated L2, τ=0.1)
            _cfg = SOCDomainConfig()
            # CORR-1: resolve alert_type → category via explicit map (not direct equality)
            _cat_idx = _cfg.get_category_index(alert_category)
            _scoring_result = _scorer.score(f.flatten(), category_index=_cat_idx)
            triage_entropy = _scoring_result.entropy if hasattr(_scoring_result, 'entropy') else None
            triage_confidence_gap = _scoring_result.confidence_gap if hasattr(_scoring_result, 'confidence_gap') else None

        # Phase 0b gate: scorer outputs A=4 (escalate/investigate/suppress/monitor).
        # refer_to_analyst is NOT a scorer action — the gate adds it when confidence
        # is below CONFIDENCE_THRESHOLD (0.70).  This replaces the v5.5 ReferralPolicy
        # centroid-proximity gate and raises accuracy ceiling from 80.6% → ~90-95%.
        with _soc_perf_phase(
            "post_scorer_confidence_gate",
            route=_perf_route,
            alert_id=alert_id,
            category=alert_category,
        ):
            from app.services.composite_gate import CompositeDiscriminant as _CGD
            selected_action = _scoring_result.action_name
            confidence = _scoring_result.confidence

            _refer_threshold = _CGD.CATEGORY_CONFIDENCE_THRESHOLDS.get(
                alert_category, _CGD.CONFIDENCE_THRESHOLD
            )
            if confidence < _refer_threshold:
                selected_action = "refer_to_analyst"
                logger.info(
                    "[TRIAGE-Phase0b] conf=%.3f < %.2f -- gate overrides to refer_to_analyst (cat=%s)",
                    confidence, _refer_threshold, alert_category,
                )

        # v5.0 routing: auto-approve / agent zone / human review
        with _soc_perf_phase(
            "routing_threshold_lookup",
            route=_perf_route,
            alert_id=alert_id,
            category=alert_category,
            action=selected_action,
        ):
            _threshold = SOC_AUTO_APPROVE_THRESHOLDS.get(selected_action)
            _cat_floor = SOC_CATEGORY_CONFIDENCE_FLOORS.get(alert_category, _threshold)
            _effective_threshold = _cat_floor if _cat_floor else _threshold
            _elevated = SOC_AGENT_ZONE_ELEVATED.get(alert_category, False)

        _rl_exploration_decision = None
        _rl_original_action_name = _scoring_result.action_name
        _rl_explored_action_name = None
        _rl_explored_but_referred = False
        _rl_exploration_executed = False
        _rl_exploration_status = "available"
        _rl_decision_method = "gae_scoring"
        try:
            with _soc_perf_phase(
                "rl_exploration_proposal",
                route=_perf_route,
                alert_id=alert_id,
                category=alert_category,
                action=selected_action,
            ):
                _soc_cfg_rl = _rl_soc_config()
                if (
                    getattr(_soc_cfg_rl, "RL_EXPLORATION_ENABLED", False)
                    and selected_action in scorer_actions
                ):
                    _headroom_ratio = 0.0
                    try:
                        from app.services.learning_health import LearningHealthMonitor as _RLHealth

                        _health = await _RLHealth.evaluate(graph_client)
                        from app.services.evolver import get_soc_conservation_provider

                        get_soc_conservation_provider().update_from_health(_health)
                        _headroom_ratio = float(
                            (_health.get("conservation") or {}).get("headroom") or 0.0
                        )
                    except Exception as _rl_health_exc:
                        logger.warning("[RL] Exploration health check failed: %s", _rl_health_exc)
                    from app.services.rl_engine import get_exploration_policy

                    _scorer_probs = _scoring_result.probabilities.tolist()[:len(scorer_actions)]
                    _rl_exploration_decision = get_exploration_policy().propose(
                        _scorer_probs,
                        _cat_idx,
                        _headroom_ratio,
                    )
                    if (
                        _rl_exploration_decision.explored
                        and _rl_exploration_decision.explored_action is not None
                        and 0 <= _rl_exploration_decision.explored_action < len(scorer_actions)
                    ):
                        _rl_explored_action_name = scorer_actions[
                            _rl_exploration_decision.explored_action
                        ]
                        # G1 boundary (Option A strict): exploration proposes,
                        # but never overrides the live centroid-selected action.
                        # The proposal remains available for shadow evaluation
                        # and learning; the decision path stays centroidal.
                        _rl_exploration_executed = False
                        _rl_decision_method = "gae_scoring_explore_proposed"
        except Exception as _rl_explore_exc:
            logger.warning("[RL] Exploration proposal failed: %s", _rl_explore_exc)
            _rl_exploration_decision = None
            _rl_explored_action_name = None
            _rl_exploration_executed = False
            _rl_exploration_status = "unavailable"

        with _soc_perf_phase(
            "routing_zone_resolution",
            route=_perf_route,
            alert_id=alert_id,
            category=alert_category,
            action=selected_action,
        ):
            if selected_action == "refer_to_analyst":
                routing_zone = "human_review"   # graduated dispatch -- always routes to human
            elif selected_action == "monitor":
                routing_zone = "agent_zone"   # monitor never auto-approved
            elif _elevated:
                routing_zone = "agent_zone"   # malware_execution + cloud_infra elevated
            elif _effective_threshold and confidence >= _effective_threshold:
                routing_zone = "auto_approve"
            elif confidence >= 0.60:
                routing_zone = "agent_zone"
            else:
                routing_zone = "human_review"

            fv_list = validated_factor_vector(f)

        # SOC-03: novelty inspection is a read-only view over the same live
        # centroids used for scoring. It never updates scorer or centroid state.
        _no_precedent_payload = None
        try:
            from app.services.soc_explainability import build_detector

            _no_precedent_payload = build_detector(_scorer).detect(
                fv_list,
                alert_category,
                confidence=confidence,
            ).to_dict()
        except Exception as _novelty_exc:
            logger.warning("[EXPLAIN] No-precedent inspection unavailable: %s", _novelty_exc)

        # SOC-02 / SR-82: authority is a decision-path control, not a dashboard
        # label.  The shared promotion state owns the persisted rung; the live
        # SOC conservation provider supplies the RED veto input.
        from app.services.authority_ladder import get_authority_manager
        from app.services.evolver import get_soc_conservation_provider

        _authority_manager = get_authority_manager()
        _authority_state = get_soc_conservation_provider().get_state()
        try:
            _authority_decision = _authority_manager.evaluate(
                alert_category,
                selected_action,
                _authority_state,
                decision_id=alert_id,
            )
            _authority_veto_payload = _authority_decision.to_dict()
            if not _authority_decision.allowed:
                selected_action = "refer_to_analyst"
                routing_zone = "human_review"
        except Exception as _authority_exc:
            # Authority is a safety layer, never a reason to take down triage.
            # Preserve the original scorer action if the authority subsystem is
            # unavailable or malformed; downstream referral rules still run.
            logger.warning(
                "[AUTHORITY] evaluation unavailable for %s: %s",
                alert_category,
                _authority_exc,
            )
            _authority_decision = None
            _authority_veto_payload = None

        # ====================================================================
        # Step 4b: Referral VETO — independent of ProfileScorer (EXP-REFER-LAYERED)
        #
        # Evaluate before any action-dependent side effects. Referral must be
        # authoritative over explored proposals for Decision, audit, Sentinel,
        # events, and response surfaces.
        # ====================================================================
        from gae.referral import ReferralEngine
        from app.services.referral_rules import get_soc_referral_rules

        # R2/R7: query Decision nodes for sequence and cross-category counts
        with _soc_perf_phase(
            "referral_history_counts",
            route=_perf_route,
            alert_id=alert_id,
            category=alert_category,
            action=selected_action,
        ):
            _source_id = alert_data.get('source_location')
            _user_id   = context.get('user_id')
            _new_seq = await graph_client.get_sequence_count(_source_id)
            _legacy_seq = await _legacy_sequence_count(_source_id)
            _new_cross = await graph_client.get_cross_category_count(_user_id)
            _legacy_cross = await _legacy_cross_category_count(_user_id)
            if _new_seq != _legacy_seq:
                _shadow_log.warning(
                    "SHADOW MISMATCH seq: decision=%d alert=%d source_id=%s",
                    _new_seq, _legacy_seq, _source_id,
                )
            if _new_cross != _legacy_cross:
                _shadow_log.warning(
                    "SHADOW MISMATCH cross_cat: decision=%d alert=%d user_id=%s",
                    _new_cross, _legacy_cross, _user_id,
                )
            if _REFERRAL_COUNT_SOURCE == "decision":
                _sequence_count, _cross_category_count = _new_seq, _new_cross
            else:
                _sequence_count, _cross_category_count = _legacy_seq, _legacy_cross
        # Referral runs before Decision creation so final-action side effects are
        # safe. The DB helpers count persisted Decisions only, so include the
        # current candidate decision in-memory to preserve previous R2/R7 semantics.
        _referral_sequence_count = _sequence_count + 1
        _referral_cross_category_count = _cross_category_count + 1
        logger.debug(
            "[TRIAGE-Referral] source_id=%r seq=%d(+current=%d) user_id=%r cross_cat=%d(+current=%d)",
            _source_id, _sequence_count, _referral_sequence_count,
            _user_id, _cross_category_count, _referral_cross_category_count,
        )

        with _soc_perf_phase(
            "referral_gate_evaluation",
            route=_perf_route,
            alert_id=alert_id,
            category=alert_category,
            action=selected_action,
            sequence_count=_referral_sequence_count,
            cross_category_count=_referral_cross_category_count,
        ):
            _alert_context = {
                # R1: executive account
                'identity_tier':        alert_data.get('identity_tier', 'standard'),
                # R2: rapid succession — live AGE count
                'sequence_count':       _referral_sequence_count,
                # R3: compliance mandate
                'category':             alert_category,
                'compliance_mode':      False,
                # R4: high value data
                'asset_criticality':    fv_list[1] if len(fv_list) > 1 else 0.0,
                'stage1_action':        _scoring_result.action_name,
                # R5: active incident
                'incident_active':      False,
                # R6: new asset
                'asset_age_days':       alert_data.get('asset_age_days', 365),
                # R7: cross-category — live AGE count
                'cross_category_count': _referral_cross_category_count,
                # full factor vector for future rules
                'factor_values':        fv_list,
            }

            _referral_engine = ReferralEngine(rules=get_soc_referral_rules())
            _referral = _referral_engine.evaluate(_alert_context)

            if _referral.should_refer:
                selected_action = "refer_to_analyst"
                routing_zone = "human_review"
                if _rl_exploration_decision and _rl_exploration_decision.explored:
                    _rl_explored_but_referred = True
                    _rl_exploration_executed = False
                logger.info(
                    "[TRIAGE-Referral] VETO fired -- rules=%s audit=%s",
                    _referral.reason_codes,
                    _referral.audit_summary,
                )

            _referral_payload = {
                'should_refer':  _referral.should_refer,
                'reasons':       _referral.reason_codes,
                'audit_summary': _referral.audit_summary,
            }
            if _authority_decision is not None and not _authority_decision.allowed:
                _referral_payload["should_refer"] = True
                _referral_payload["reasons"] = list(_referral_payload["reasons"]) + [
                    _authority_decision.reason or "authority_veto"
                ]
                _referral_payload["authority_veto"] = _authority_veto_payload

        logger.info(
            "[TRIAGE-v5] action=%s conf=%.3f zone=%s",
            selected_action, confidence, routing_zone,
        )
        print(f"[GAE] action={selected_action} confidence={confidence:.3f} "
              f"f={[round(v, 3) for v in fv_list]}")

        # Generate reasoning using GAE-selected action
        with _soc_perf_phase(
            "reasoning_generation",
            route=_perf_route,
            alert_id=alert_id,
            category=alert_category,
            action=selected_action,
        ):
            reasoning = await narrator.generate_reasoning(alert_type, selected_action, context)

        # ====================================================================
        # Step 5: Write Decision node to AGE (R4 — f(t) stored in graph)
        #
        # MATCH (a:Alert {id: $alert_id})
        # CREATE (d:Decision {id:..., action:..., confidence:..., factor_vector:...,
        #                     timestamp: datetime(), outcome: null})
        # CREATE (d)-[:DECIDED_ON]->(a)
        # ====================================================================
        decision_id = str(uuid.uuid4())
        _ts_analyze = int(datetime.utcnow().timestamp() * 1000)
        with _soc_perf_phase(
            "decision_node_and_edge_write",
            route=_perf_route,
            alert_id=alert_id,
            decision_id=decision_id,
            category=alert_category,
            action=selected_action,
            factor_vector_len=len(fv_list),
        ):
            await graph_client.run_query(
                f"""
                MATCH (a:Alert {{alert_id: {_S(alert_id)}}})
                CREATE (d:Decision {{
                    decision_id:           {_S(decision_id)},
                    domain:                'soc',
                    action:                {_S(selected_action)},
                    confidence:            {confidence},
                    factor_vector:         {_S(json.dumps(fv_list))},
                    factor_provenance:     {_S(json.dumps(factor_provenance, sort_keys=True))},
                    category:              {_S(alert_category)},
                    source_id:             {_S(alert_data.get("source_location", ""))},
                    user_id:               {_S(context.get("user_id", ""))},
                    status:                'pending',
                    timestamp_epoch:       {_ts_analyze},
                    outcome:               null,
                    triage_entropy:        {triage_entropy},
                    triage_confidence_gap: {triage_confidence_gap}
                }})
                CREATE (d)-[:DECIDED_ON]->(a)
                """
            )
        print(f"[GAE] Decision node written: id={decision_id} [:DECIDED_ON] {alert_id}")

        with _soc_perf_phase(
            "audit_write",
            route=_perf_route,
            alert_id=alert_id,
            decision_id=decision_id,
            category=alert_category,
            action=selected_action,
        ):
            _audit_rec_analyze = await record_decision(
                alert_id=alert_id,
                # Evidence Room exposes this field as the audit category;
                # persist the canonical SOC category resolved above rather
                # than the narrative situation label (for example,
                # insider_threat_detected).
                situation_type=alert_category,
                action_taken=selected_action,
                factors=[c.name for c in computers],
                confidence=confidence,
                kernel_type="unknown",
                noise_zone="unknown",
                conservation_status="unknown",
            )
            _entry_hash_analyze = _audit_rec_analyze.get("hash", "")
            _chain_index_analyze = _audit_rec_analyze.get("chain_index", -1)
            if _entry_hash_analyze:
                await graph_client.run_query(
                    f"MATCH (d:Decision {{decision_id: {_S(decision_id)}}}) "
                    "WHERE d.domain = 'soc' "
                    f"SET d.entry_hash = {_S(_entry_hash_analyze)}, "
                    f"d.decision_chain_index = {_chain_index_analyze}"
                )

        # F4b: Record confidence snapshot for trajectory tracking
        # Placed AFTER successful graph write — prevents phantom entries on failure.
        with _soc_perf_phase(
            "metadata_logging_snapshot_write",
            route=_perf_route,
            alert_id=alert_id,
            decision_id=decision_id,
            category=alert_category,
            action=selected_action,
        ):
            append_confidence_snapshot(
                alert_id       = alert_id,
                alert_type     = alert_type,
                situation_type = situation_analysis.situation_type,
                confidence     = confidence,
            )

        # ====================================================================
        # Step 5b: Campaign correlation (F6) — non-blocking
        # ====================================================================
        _campaign_id = None
        _campaign_context_payload = None
        _campaign_context_flags: dict[str, bool | str | None] = {
            "is_campaign_alert": False,
            "campaign_context_shown": False,
        }
        try:
            with _soc_perf_phase(
                "campaign_correlation",
                route=_perf_route,
                alert_id=alert_id,
                decision_id=decision_id,
                category=alert_category,
                action=selected_action,
            ):
                from app.domains.soc.campaigns import (
                    CampaignCorrelationEngine, CampaignRepository, CampaignMatcher,
                )
                _camp_config = SOCDomainConfig.get_campaign_config()
                _camp_engine = CampaignCorrelationEngine(_camp_config)
                _camp_repo = CampaignRepository(graph_client)
                _camp_matcher = CampaignMatcher(
                    graph_client, _camp_config, _camp_engine, _camp_repo
                )
                _campaign_id = await _camp_matcher.check_alert(alert_id)
                _campaign_context_payload, _campaign_context_flags = build_campaign_context_payload(
                    campaign_id=_campaign_id,
                    async_state=_camp_matcher.async_state,
                    alert_id=alert_id,
                )
        except Exception as _camp_exc:
            logger.warning("[TRIAGE] Campaign wiring failed for %s: %s", alert_id, _camp_exc)
        try:
            _campaign_set_clauses = [
                f"d.is_campaign_alert = {_S(_campaign_context_flags['is_campaign_alert'])}",
                f"d.campaign_context_shown = {_S(_campaign_context_flags['campaign_context_shown'])}",
            ]
            if _campaign_id:
                _campaign_set_clauses.insert(0, f"d.campaign_id = {_S(_campaign_id)}")
            if _campaign_context_flags.get("is_campaign_alert"):
                _campaign_set_clauses.append(
                    "d.campaign_advisory_version = "
                    f"{_S(_campaign_context_flags.get('campaign_advisory_version'))}"
                )
            await graph_client.run_query(
                f"MATCH (d:Decision {{decision_id: {_S(decision_id)}}}) "
                "WHERE d.domain = 'soc' "
                f"SET {', '.join(_campaign_set_clauses)}"
            )
        except Exception as _camp_flag_exc:
            logger.warning(
                "[TRIAGE] Campaign Decision flag write failed for %s: %s",
                alert_id,
                _camp_flag_exc,
            )

        # ====================================================================
        # Step 5c: Sentinel write-back (Block 7.1) — fire-and-forget
        #
        # Triggered when:
        #   - confidence >= 0.85
        #   - action is escalate or investigate
        #   - alert_data contains incident_id (i.e., alert originated from Sentinel)
        # Never blocks triage response.
        # ====================================================================
        _incident_id = alert_data.get("incident_id", "")
        if (
            confidence >= 0.85
            and selected_action in ("escalate", "investigate")
            and _incident_id
        ):
            with _soc_perf_phase(
                "sentinel_writeback_schedule",
                route=_perf_route,
                alert_id=alert_id,
                decision_id=decision_id,
                category=alert_category,
                action=selected_action,
                has_incident_id=bool(_incident_id),
            ):
                from app.connectors.sentinel_real import get_sentinel_connector as _get_sentinel
                import asyncio as _asyncio
                _sentinel_connector = _get_sentinel()
                _asyncio.create_task(
                    _sentinel_connector.push_incident_update(
                        incident_id=_incident_id,
                        action=selected_action,
                        confidence=confidence,
                        decision_id=decision_id,
                        campaign_id=locals().get("_campaign_id"),
                    )
                )
            logger.info(
                "[Sentinel-WB] fire-and-forget scheduled -- incident=%s action=%s conf=%.3f",
                _incident_id, selected_action, confidence,
            )

        # ====================================================================
        # Step 6: Emit events (every graph mutation MUST emit events)
        # ====================================================================
        with _soc_perf_phase(
            "decision_event_emit",
            route=_perf_route,
            alert_id=alert_id,
            decision_id=decision_id,
            category=alert_category,
            action=selected_action,
        ):
            await event_bus.emit(DecisionMade(
                alert_id      = alert_id,
                action        = selected_action,
                confidence    = confidence,
                factor_vector = tuple(fv_list),
            ))
            await event_bus.emit(GraphMutated(
                mutation_type     = "decision",
                affected_entities = (alert_id,),
            ))

        # ====================================================================
        # Step 7: Composite discriminant gate (Phase 5 / DISC-1)
        # ====================================================================
        from app.services.composite_gate import CompositeDiscriminant
        from app.services.shadow_mode import ShadowModeService
        try:
            with _soc_perf_phase(
                "composite_gate_evaluation",
                route=_perf_route,
                alert_id=alert_id,
                decision_id=decision_id,
                category=alert_category,
                action=selected_action,
                factor_vector_len=len(fv_list),
            ):
                _composite = await CompositeDiscriminant.evaluate(
                    score_result=_scoring_result,
                    category=alert_category,
                    factor_vector=f.flatten(),
                    decision_position=0.0,
                    graph_service=graph_client,
                )
                if _composite["auto_approve"] and not ShadowModeService.SHADOW_ENABLED:
                    await graph_client.run_query(
                        f"MATCH (d:Decision {{decision_id: {_S(decision_id)}}}) "
                        "WHERE d.domain = 'soc' SET d.auto_approved = true"
                    )
        except Exception as _cg_exc:
            logger.warning("[TRIAGE] composite gate failed: %s", _cg_exc)
            _composite = {
                "auto_approve": False,
                "approval_score": 0.0,
                "reason_codes": [f"gate error: {_cg_exc}"],
                "features": {},
            }

        # ====================================================================
        # Step 8a: Build factor provenance (Phase 6)
        # ====================================================================
        from app.services.provenance import ProvenanceService
        try:
            with _soc_perf_phase(
                "provenance_build",
                route=_perf_route,
                alert_id=alert_id,
                decision_id=decision_id,
                category=alert_category,
                action=selected_action,
                factor_count=len(fv_list),
            ):
                _prov = ProvenanceService.build_provenance(
                    decision_id=decision_id,
                    factor_names=[c.name for c in computers],
                    factor_values=fv_list,
                    category=alert_category,
                    action=selected_action,
                )
                _provenance_payload = {
                    "decision_id":           _prov.decision_id,
                    "category":              _prov.category,
                    "action":                _prov.action,
                    "total_nodes_consulted": _prov.total_nodes_consulted,
                    "factors": [
                        {
                            "factor_name":           fp.factor_name,
                            "factor_value":          fp.factor_value,
                            "computation_method":    fp.computation_method,
                            "graph_nodes_consulted": fp.graph_nodes_consulted,
                            "explanation":           fp.explanation,
                        }
                        for fp in _prov.factors
                    ],
                }
        except Exception as _prov_exc:
            logger.warning("[TRIAGE] provenance build failed: %s", _prov_exc)
            _provenance_payload = {"decision_id": decision_id, "factors": [], "error": str(_prov_exc)}

        # ====================================================================
        # Step 8: Get graph data for visualization
        # ====================================================================
        with _soc_perf_phase(
            "graph_visualization_fetch",
            route=_perf_route,
            alert_id=alert_id,
            decision_id=decision_id,
            category=alert_category,
            action=selected_action,
        ):
            graph_data = await get_graph_data(alert_id)

        # ====================================================================
        # Step 8: Extract key facts from context
        # ====================================================================
        with _soc_perf_phase(
            "response_context_enrichment",
            route=_perf_route,
            alert_id=alert_id,
            decision_id=decision_id,
            category=alert_category,
            action=selected_action,
            factor_count=len(fv_list),
        ):
            key_facts = []

            if context.get("user_traveling"):
                key_facts.append({
                    "source": "TravelContext",
                    "fact": f"User traveling to {context.get('travel_destination')}"
                })

            if context.get("pattern_id"):
                key_facts.append({
                    "source": "AttackPattern",
                    "fact": f"Pattern {context.get('pattern_id')} matched ({context.get('pattern_count')} occurrences)"
                })

            if context.get("mfa_completed"):
                key_facts.append({
                    "source": "Alert",
                    "fact": "MFA authentication completed"
                })

            # Build action_probabilities dict for verification + frontend display
            probs_flat = _scoring_result.probabilities.tolist()
            action_probabilities = {a: round(p, 6) for a, p in zip(scorer_actions, probs_flat)}

            # Scoring quality flags
            max_prob = max(probs_flat)
            sorted_probs = sorted(probs_flat, reverse=True)
            low_confidence = max_prob < 0.25
            ambiguous      = (
                len(sorted_probs) >= 2 and
                (sorted_probs[0] - sorted_probs[1]) < 0.05
            )

        if _rl_exploration_decision and _rl_exploration_decision.explored:
            try:
                with _soc_perf_phase(
                    "rl_exploration_metadata_write",
                    route=_perf_route,
                    alert_id=alert_id,
                    decision_id=decision_id,
                    category=alert_category,
                    action=selected_action,
                ):
                    _meta_ts = int(datetime.utcnow().timestamp() * 1000)
                    await graph_client.run_query(
                        f"""
                        MATCH (d:Decision {{decision_id: {_S(decision_id)}}})
                        WHERE d.domain = 'soc'
                        SET d.action                  = {_S(selected_action)},
                            d.explored                = true,
                            d.exploration_rate        = {float(_rl_exploration_decision.exploration_rate)},
                            d.original_action         = {_S(_rl_original_action_name)},
                            d.explored_action         = {_S(_rl_explored_action_name or '')},
                            d.explored_but_referred   = {'true' if _rl_explored_but_referred else 'false'},
                            d.exploration_executed    = {'true' if _rl_exploration_executed else 'false'},
                            d.exploration_reason      = {_S(_rl_exploration_decision.reason)},
                            d.exploration_updated_at  = {_meta_ts}
                        """
                    )
            except Exception as _rl_meta_exc:
                logger.warning("[RL] Exploration metadata write failed: %s", _rl_meta_exc)

        with _soc_perf_phase(
            "referral_debug_build",
            route=_perf_route,
            alert_id=alert_id,
            decision_id=decision_id,
            category=alert_category,
            action=selected_action,
            sequence_count=_sequence_count,
            cross_category_count=_cross_category_count,
        ):
            _referral_debug = {
                'r2_sequence_count':       _sequence_count,
                'r7_cross_category_count': _cross_category_count,
                'rules_evaluated':         [r.rule_id for r in get_soc_referral_rules()],
                'rules_fired':             list(_referral.reason_codes),
            }

        # ====================================================================
        # Step 8c: AE-02 per-variant shadow comparison — fire-and-forget
        # ====================================================================
        from app.services.shadow_runner import SHADOW_TESTABLE_ARTIFACTS, maybe_shadow_compare
        from app.services.variant_registry import SHADOW as _AE_SHADOW, get_all_variants as _ae_variants
        import asyncio as _shadow_asyncio

        with _soc_perf_phase(
            "shadow_compare_schedule",
            route=_perf_route,
            alert_id=alert_id,
            decision_id=decision_id,
            category=alert_category,
            action=selected_action,
        ):
            _has_shadow_variant = any(
                variant.artifact_type in SHADOW_TESTABLE_ARTIFACTS
                and (variant.category == alert_category or variant.category is None)
                for variant in _ae_variants(status_filter=_AE_SHADOW)
            )
            if _has_shadow_variant:
                _shadow_asyncio.create_task(
                    maybe_shadow_compare(
                        alert_id=alert_id,
                        category=alert_category,
                        production_action=selected_action,
                        production_confidence=confidence,
                        alert_data=alert_data,
                    )
                )

        # ====================================================================
        # Build Response — existing structure preserved; gae_scoring added
        # ====================================================================
        # ATT&CK fields: prefer AGE Alert node properties; fall back to
        # MITRE_ATTACK_MAP via situation_analysis (already populated above).
        attack_technique = (
            alert_data.get("mitre_technique") or situation_analysis.mitre_technique
        )
        attack_tactic = (
            alert_data.get("mitre_tactic") or situation_analysis.mitre_tactic
        )

        _cluster_history_payload = None
        try:
            with _soc_perf_phase(
                "cluster_history_fetch",
                route=_perf_route,
                alert_id=alert_id,
                decision_id=decision_id,
                category=alert_category,
                action=selected_action,
            ):
                from app.services.cluster_history import get_cluster_history as _get_cluster_history

                _cluster_history = await _get_cluster_history(
                    source_user=context.get("user_id") or alert_data.get("user_id"),
                    current_decision_id=decision_id,
                    graph_client=graph_client,
                )
                if _cluster_history is not None:
                    _cluster_history_payload = dataclasses.asdict(_cluster_history)
        except Exception as _cluster_exc:
            logger.warning("[TRIAGE] Cluster history failed for %s: %s", alert_id, _cluster_exc)

        _perf_response_started = _soc_perf_start()
        response = {
            "alert": alert_data,
            "attack_technique": attack_technique,
            "attack_tactic":    attack_tactic,
            "analysis": {
                "root_cause": f"Anomalous {alert_type} from {alert_data.get('source_location', 'unknown location')}",
                "severity_assessment": f"{alert_data.get('severity', 'medium').upper()} severity based on context"
            },
            "context": {
                "nodes_count": context.get("nodes_consulted", 47),
                "subgraphs_traversed": ["User Profile", "Asset Inventory", "Travel Calendar", "Pattern Library", "Playbook Registry"],
                "patterns_matched": 1 if context.get("pattern_id") else 0,
                "key_facts": key_facts
            },
            "recommendation": {
                "action":       selected_action,
                "confidence":   confidence,
                "routing_zone": routing_zone,
                "reasoning":    reasoning,
                "pattern_id":   context.get("pattern_id"),
                "playbook_id":  context.get("playbook_id"),
                "decision_id":  decision_id,   # needed by GAE-3a feedback
            },
            # GAE scoring details — verification: probs sum to ~1.0
            "gae_scoring": {
                "decision_id":          decision_id,
                "factor_vector":        fv_list,
                "factor_names":         [c.name for c in computers],
                "action_probabilities": action_probabilities,
                "softmax_sum":          round(sum(probs_flat), 8),
                "temperature":          _scorer.tau,
                "low_confidence":       low_confidence,
                "ambiguous":            ambiguous,
                "routing_zone":         routing_zone,
                "decision_method":      (
                    "ProfileScorer centroid-proximity scoring "
                    "(n_factors x 5 actions x n_categories, "
                    "L2 kernel tau=0.1, EXP-E1 validated)"
                ),
            },
            "graph_data": graph_data,
            "situation_analysis": situation_analysis.model_dump(),
            "campaign_context": _campaign_context_payload,
            "composite_gate": {
                "auto_approve":   _composite["auto_approve"],
                "approval_score": _composite["approval_score"],
                "reason_codes":   _composite["reason_codes"],
            },
            "provenance":      _provenance_payload,
            "referral":        _referral_payload,
            "referral_debug":  _referral_debug,
            "exploration_status": _rl_exploration_status,
            "decision_method": "referral_override" if _referral.should_refer else _rl_decision_method,
            "authority": _authority_veto_payload,
            "no_precedent": _no_precedent_payload,
        }
        if _cluster_history_payload is not None:
            response["cluster_history"] = _cluster_history_payload
        # ====================================================================
        # NAR-1: Build calibration_context and generate structured narrative
        # ====================================================================
        with _soc_perf_phase(
            "narrative_context_build",
            route=_perf_route,
            alert_id=alert_id,
            decision_id=decision_id,
            category=alert_category,
            action=selected_action,
            factor_count=len(fv_list),
        ):
            _ls = get_learning_state()
            _factor_names_list = [c.name for c in computers]
            _factors_for_narr  = [
                {"name": n, "value": v}
                for n, v in zip(_factor_names_list, fv_list)
            ]
            _top_f = (
                max(_factors_for_narr, key=lambda x: x["value"])
                if _factors_for_narr else {}
            )
            _bot_f = (
                min(_factors_for_narr, key=lambda x: x["value"])
                if _factors_for_narr else {}
            )
            calibration_context = {
                "decision_count": _ls.decision_count,  # SOURCE: in-memory LearningState (resets on restart)
                "category_count": _ls.decision_count,  # SOURCE: in-memory LearningState (resets on restart)
                "category":       alert_category,
                "top_factor":     _top_f,
                "bottom_factor":  _bot_f,
            }
            _alert_for_narr = {**alert_data, **situation_analysis.model_dump()}
            _decision_for_narr = {
                "action":     selected_action,
                "confidence": confidence,
                "pattern_id": context.get("pattern_id"),
            }
        with _soc_perf_phase(
            "narrative_generation",
            route=_perf_route,
            alert_id=alert_id,
            decision_id=decision_id,
            category=alert_category,
            action=selected_action,
            factor_count=len(_factors_for_narr),
        ):
            response["narrative"] = get_narrative_provider().generate(
                _alert_for_narr, _decision_for_narr, _factors_for_narr, calibration_context
            )
        with _soc_perf_phase(
            "decision_pipeline_shadow_compare",
            route=_perf_route,
            alert_id=alert_id,
            decision_id=decision_id,
            category=alert_category,
            action=selected_action,
        ):
            response = await _soc_maybe_attach_decision_pipeline_shadow(
                response,
                alert_data=alert_data,
                context=context,
            )
        _soc_perf_emit_duration(
            "response_serialization",
            _perf_response_started,
            route=_perf_route,
            alert_id=alert_id,
            decision_id=decision_id,
            category=alert_category,
            action=selected_action,
        )
        return response

    except HTTPException as exc:
        _perf_total_status = "error"
        _perf_total_exception = type(exc).__name__
        raise
    except Exception as e:
        _perf_total_status = "error"
        _perf_total_exception = type(e).__name__
        print(f"[ERROR] Failed to analyze alert: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        _soc_perf_emit_duration(
            "analyze_request_total",
            _perf_total_started,
            route=_perf_route,
            status=_perf_total_status,
            exception_type=_perf_total_exception,
            alert_id=_perf_alert_id,
            decision_id=locals().get("decision_id"),
            category=locals().get("alert_category"),
            action=locals().get("selected_action"),
        )


# ============================================================================
# POST /api/action/execute - Execute Closed Loop
# ============================================================================

@router.post("/action/execute")
async def execute_action(request: ProcessAlertRequest):
    """
    Execute the recommended action with full closed-loop verification.

    Closed Loop Steps:
    1. EXECUTED - Action taken in target system
    2. VERIFIED - Outcome confirmed
    3. EVIDENCE - Decision trace captured
    4. KPI IMPACT - Metrics attributed
    """

    try:
        alert_id = request.alert_id

        # Get context for decision trace
        context = await graph_client.get_security_context(alert_id)

        if not context:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

        # Get decision
        alert_type = context.get("alert_type")
        decision = agent.decide(alert_type, context)
        reasoning = await narrator.generate_reasoning(alert_type, decision.action, context)

        # Resolve correct situation_type and factor list for the audit ledger (H-1).
        # context never carries these keys; derive them from the same functions
        # used by /alert/analyze. Graceful fallback keeps the execute path safe.
        situation_type_str = "unknown"
        factor_names: list = []
        factor_vector = [0.5] * 6
        try:
            situation = analyze_situation(alert_type, context)
            situation_type_str = situation.situation_type
        except Exception as exc:
            print(f"[EXECUTE] analyze_situation failed for {alert_id}: {exc}")
        try:
            factors_result = await get_decision_factors(alert_id)
            if factors_result:
                factors = factors_result.get("factors", [])
                factor_names = [f["name"] for f in factors]
                values = [f.get("value", 0.5) for f in factors]
                factor_vector = validated_factor_vector(values + [0.5] * (6 - len(values)))
        except Exception as exc:
            print(f"[EXECUTE] get_decision_factors failed for {alert_id}: {exc}")

        # ====================================================================
        # Step 1: EXECUTED - Take action in target system
        # ====================================================================
        receipt_id = f"RCP-{uuid.uuid4().hex[:6].upper()}"

        target_system = "Splunk SIEM" if decision.action == "false_positive_close" else "ServiceNow"
        target_response = f"Alert {alert_id} marked as resolved" if decision.action == "false_positive_close" else f"Incident ticket INC-{uuid.uuid4().hex[:4].upper()} created"

        # ====================================================================
        # Step 2: VERIFIED - Confirm outcome
        # ====================================================================
        verification_method = "API status check" if decision.action == "false_positive_close" else "Ticket existence verification"

        # ====================================================================
        # Step 3: EVIDENCE - Create decision trace in AGE
        # ====================================================================
        decision_id = f"DEC-{uuid.uuid4().hex[:4].upper()}"

        from app.domains.soc.config import resolve_alert_category as _resolve_cat_exec
        _exec_category = _resolve_cat_exec(alert_type) if alert_type else "unknown"
        # Atomic MATCH+CREATE: Decision node linked to Alert via DECIDED_ON.
        # Replaces create_decision_trace() which used FOR_ALERT (wrong schema)
        # and had a signature mismatch (category kwarg) that caused TypeError.
        _ts_execute = int(datetime.utcnow().timestamp() * 1000)
        await graph_client.run_query(
            f"""
            MATCH (a:Alert {{alert_id: {_S(alert_id)}}})
            CREATE (d:Decision {{
                decision_id:     {_S(decision_id)},
                action:          {_S(decision.action)},
                confidence:      {decision.confidence},
                factor_vector:   {_S(json.dumps(factor_vector))},
                category:        {_S(_exec_category)},
                domain:          'soc',
                source_id:       {_S(context.get("source_location", ""))},
                user_id:         {_S(context.get("user_id", ""))},
                timestamp_epoch: {_ts_execute},
                outcome:         null
            }})
            CREATE (d)-[:DECIDED_ON]->(a)
            """
        )

        # Record decision in the in-memory audit ledger after graph write succeeds.
        # EU AI Act Art. 15 epistemic fields: supply "unknown" when not yet available.
        _audit_rec_execute = await record_decision(
            alert_id=alert_id,
            situation_type=situation_type_str,
            action_taken=decision.action,
            factors=factor_names,
            confidence=decision.confidence,
            kernel_type="unknown",
            noise_zone="unknown",
            conservation_status="unknown",
        )
        _entry_hash_execute = _audit_rec_execute.get("hash", "")
        _chain_index_execute = _audit_rec_execute.get("chain_index", -1)
        if _entry_hash_execute:
            await graph_client.run_query(
                f"MATCH (d:Decision {{decision_id: {_S(decision_id)}}}) "
                "WHERE d.domain = 'soc' "
                f"SET d.entry_hash = {_S(_entry_hash_execute)}, "
                f"d.decision_chain_index = {_chain_index_execute}"
            )

        # Emit events — every graph write MUST emit events (TD-020)
        await event_bus.emit(DecisionMade(
            alert_id      = alert_id,
            action        = decision.action,
            confidence    = decision.confidence,
            factor_vector = (),  # rule-based path; no GAE factor vector here
        ))
        await event_bus.emit(GraphMutated(
            mutation_type     = "decision",
            affected_entities = (alert_id,),
        ))

        # Update alert status in AGE
        await graph_client.run_query(
            f"MATCH (alert:Alert {{alert_id: {_S(alert_id)}}}) SET alert.status = 'resolved'"
        )
        await event_bus.emit(GraphMutated(
            mutation_type     = "alert_status",
            affected_entities = (alert_id,),
        ))

        # ====================================================================
        # Step 4: KPI IMPACT - Calculate metrics impact
        # ====================================================================
        # Simulate MTTR improvement
        mttr_reduction = 4.2 if decision.action == "false_positive_close" else 2.1

        return {
            "receipt": {
                "id": receipt_id,
                "action": decision.action,
                "timestamp": datetime.now().isoformat(),
                "target_system": target_system,
                "target_system_response": target_response
            },
            "verification": {
                "verified": True,
                "verification_method": verification_method
            },
            "evidence": {
                "decision_id": decision_id,
                "trace_captured": True,
                "nodes_consulted": context.get("nodes_consulted", 47)
            },
            "kpi_impact": {
                "metric": "MTTR",
                "contribution": f"down{mttr_reduction} minutes",
                "previous_avg": 15.3,
                "new_avg": 15.3 - mttr_reduction
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to execute action: {e}")
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


# ============================================================================
# POST /api/alerts/reset - Reset Demo Alerts
# ============================================================================

@router.post("/alerts/reset")
async def reset_demo_alerts():
    """
    Reset all alert statuses back to 'pending' for demo purposes.
    Also resets feedback and policy conflict state.
    Allows the demo to be run multiple times.
    """
    print("[TRIAGE] POST /alerts/reset called - resetting all demo state")

    try:
        # Reset only demo alerts (origin=zero_day_demo) — zero_day_synthetic training data is never touched
        query = """
        MATCH (alert:Alert)
        WHERE alert.origin = 'zero_day_demo'
        SET alert.status = 'pending'
        RETURN count(alert) as reset_count
        """

        print("[TRIAGE] Running Cypher query to reset ALERT- demo alert statuses...")
        result = await graph_client.run_query(query)
        reset_count = result[0]["reset_count"] if result else 0

        print(f"[TRIAGE] Reset {reset_count} ALERT- demo alerts to 'pending' status")

        # Reset demo-cycle state only — deliberately skip 'learning_state' so
        # ProfileScorer centroids (IKS) survive demo resets (BACKLOG-020).
        # Full hard reset (including learning_state) is POST /api/admin/reset.
        await state_manager.reset_except(["learning_state"])
        try:
            from app.services.rl_engine import reset_rl_state

            reset_rl_state()
        except Exception as _rl_reset_exc:
            logger.warning("[RL] Demo-cycle RL reset failed: %s", _rl_reset_exc)
        from app.services.servicenow_mock import get_servicenow_mock
        get_servicenow_mock().reset()

        return {
            "status": "success",
            "message": f"Reset {reset_count} alerts to 'pending' status. Cleared feedback, policy, audit, and evolver state.",
            "reset_count": reset_count,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"[ERROR] Failed to reset alerts: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset alerts: {str(e)}"
        )


# ============================================================================
# POST /api/alert/outcome - Report Decision Outcome (v2.5 - Feedback Loop)
# ============================================================================

@router.post("/alert/outcome")
async def report_decision_outcome(request: OutcomeRequest):
    """
    Report whether a decision outcome was correct or incorrect.
    Updates graph based on feedback (self-correction).

    This answers the CISO question: "What happens when the system is wrong?"

    Args:
        request: OutcomeRequest with alert_id, decision_id, and outcome

    Returns:
        OutcomeResponse with graph updates and narrative
    """
    print(f"[FEEDBACK] POST /alert/outcome called for {request.alert_id}")
    print(f"[FEEDBACK] Outcome: {request.outcome}")
    _perf_route = "/api/alert/outcome"
    _perf_alert_id = getattr(request, "alert_id", None)
    _perf_decision_id = getattr(request, "decision_id", None)
    _perf_total_started = _soc_perf_start()
    _perf_total_status = "ok"
    _perf_total_exception = None
    # Keep this available to response and integration paths even when
    # learning is disabled or gated before the conditional learning branch.
    _analyst_action = request.analyst_action

    try:
        with _soc_perf_phase(
            "request_parse",
            route=_perf_route,
            alert_id=_perf_alert_id,
            decision_id=_perf_decision_id,
        ):
            _perf_outcome_label = request.outcome

        # Check if feedback already given
        with _soc_perf_phase(
            "duplicate_feedback_guard",
            route=_perf_route,
            alert_id=request.alert_id,
            decision_id=request.decision_id,
        ):
            previous = get_feedback_record(request.alert_id, request.decision_id)
            if previous is not None:
                if previous.get("outcome") != request.outcome:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            f"Conflicting feedback already provided for decision "
                            f"{request.decision_id}."
                        ),
                    )
                return {
                    "alert_id": request.alert_id,
                    "outcome": previous["outcome"],
                    "graph_updates": previous.get("graph_updates", []),
                    "consequence": "Outcome already recorded; no additional learning applied.",
                    "next_alerts_override": None,
                    "narrative": "The identical outcome was already recorded.",
                }

        # ====================================================================
        # GAE-3a: Retrieve f(t) from Decision node, apply Hebbian learning
        #
        # MATCH (d:Decision {id: $decision_id})
        # Record the outcome through the shared GraphStore contract, then read
        # the decision context needed by the existing learning path.
        # ====================================================================
        outcome_int   = +1 if request.outcome == "correct" else -1
        correct_bool  = outcome_int == +1
        outcome_label = request.outcome   # "correct" | "incorrect"

        centroid_update_payload = None  # populated below if wu.centroid_update is present
        l5_persistence_status = {
            "l5_centroid_persisted": False,
            "l5_shaped_by_attempted": False,
            "l5_persistence_skipped_reason": "not_attempted",
            "l5_persistence_source": None,
            "conservation_status": None,
            "raw_conservation_status": None,
            "conservation_status_reason": None,
        }
        _resolved_category = ""  # BACKLOG-047: category for process_outcome()

        # Per-analyst η: identity from SAML JWT "sub" claim; "anonymous" when auth is off
        try:
            analyst_id = (cast(Any, request).state.user or {}).get("sub", "anonymous")
        except AttributeError:
            analyst_id = "anonymous"
        _analyst_eta = None  # populated below after quality lookup

        _ts_outcome = int(datetime.utcnow().timestamp() * 1000)
        reward_result = None
        _rl_reward_ledger = None
        _rl_posterior_updated = False
        with _soc_perf_phase(
            "decision_lookup_and_outcome_update",
            route=_perf_route,
            alert_id=request.alert_id,
            decision_id=request.decision_id,
            action=getattr(request, "analyst_action", None),
        ):
            _soc_scorer = get_profile_scorer()
            _soc_store = getattr(_soc_scorer, "graph_store", None)
            if _soc_store is None:
                raise RuntimeError("SOC GraphStore is not available through the live scorer")
            _decision_before = _soc_store.get_decision(
                request.decision_id,
                domain="soc",
            )
            if _decision_before is None:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Decision {request.decision_id} not found in graph. "
                        "Outcome not recorded."
                    ),
                )
            _recommended_action = _decision_before.get("recommended_action")
            _actual_action = request.analyst_action or ""
            _was_override = (
                request.analyst_action is not None
                and _recommended_action != request.analyst_action
            )
            _outcome_write_kwargs = {
                "decision_id": request.decision_id,
                "actual_action": _actual_action,
                "is_correct": correct_bool,
                "domain": "soc",
                "outcome": outcome_label,
                "verified_at_epoch": float(_ts_outcome),
                "quality_signal": 1.0 if correct_bool else 0.0,
                "override_comment": request.override_comment or "",
                "verified_by": analyst_id,
                "analyst_action": request.analyst_action,
                "final_action": request.analyst_action,
                "recommended_action": (
                    str(_recommended_action) if _recommended_action is not None else None
                ),
                "was_override": _was_override,
                "metadata": {"verified_at": _ts_outcome / 1000.0},
            }
            gae_result = await graph_client.run_query(
                f"""
                MATCH (d:Decision {{decision_id: {_S(request.decision_id)}}})
                WHERE d.domain = 'soc'
                OPTIONAL MATCH (d)-[:DECIDED_ON]->(a:Alert)
                RETURN d.factor_vector AS factor_vector,
                       d.action        AS action,
                       d.confidence    AS confidence,
                       d.campaign_id    AS campaign_id,
                       d.explored       AS explored,
                       d.explored_but_referred AS explored_but_referred,
                       d.exploration_executed AS exploration_executed,
                       d.explored_action AS explored_action,
                       a.category      AS category,
                       coalesce(a.alert_type, 'unknown') AS alert_type
                """
            )
        if not gae_result:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Decision {request.decision_id} not found in graph. "
                    "Outcome not recorded."
                ),
            )

        # Audit chain — record outcome as separate event
        try:
            with _soc_perf_phase(
                "outcome_audit_write",
                route=_perf_route,
                alert_id=request.alert_id,
                decision_id=request.decision_id,
            ):
                from app.framework.audit import record_outcome as _audit_outcome
                _outcome_rec = await _audit_outcome(
                    decision_id=request.decision_id,
                    outcome=outcome_label,
                    analyst_override=(request.analyst_action is not None),
                )
                if _outcome_rec:
                    _oc_hash = _outcome_rec.get("hash", "")
                    _oc_idx = _outcome_rec.get("chain_index", -1)
                    await graph_client.run_query(
                        f"MATCH (d:Decision {{decision_id: {_S(request.decision_id)}}}) "
                        "WHERE d.domain = 'soc' "
                        f"SET d.outcome_entry_hash = {_S(_oc_hash)}, "
                        f"d.outcome_chain_index = {_oc_idx}"
                    )
        except Exception as _e:
            logger.warning("[AUDIT] Outcome audit failed: %s", _e)

        # Per-analyst η: query verified outcome history for this analyst
        if analyst_id != "anonymous":
            try:
                with _soc_perf_phase(
                    "analyst_history_scan",
                    route=_perf_route,
                    alert_id=request.alert_id,
                    decision_id=request.decision_id,
                ):
                    _q_rows = await graph_client.run_query(
                        f"MATCH (d:Decision) "
                        f"WHERE d.domain = 'soc' AND d.verified_by = {_S(analyst_id)} AND d.correct IS NOT NULL "
                        f"RETURN d.correct AS correct"
                    )
                if len(_q_rows) >= 5:
                    _total = len(_q_rows)
                    _correct_cnt = sum(1 for r in _q_rows if r.get("correct") is True)
                    from gae.calibration import compute_eta_override
                    _analyst_eta = compute_eta_override(
                        worst_case_quality=_correct_cnt / _total
                    )
                    logger.debug("[ETA] analyst=%s quality=%.2f eta=%.4f",
                                 analyst_id, _correct_cnt / _total, _analyst_eta)
            except Exception as _qe:
                logger.debug("[ETA] Analyst quality query: %s", _qe)

        print(f"[GAE] Outcome lookup: decision_id={request.decision_id!r} -> {len(gae_result) if gae_result else 0} result(s)")
        if gae_result:
            record      = gae_result[0]
            fv          = record.get("factor_vector")
            if isinstance(fv, str):
                try:
                    fv = json.loads(fv)
                except (json.JSONDecodeError, ValueError):
                    fv = None
                    print("[GAE] factor_vector string parse failed")
            if isinstance(fv, list):
                print(f"[GAE] factor_vector parsed: len={len(fv)}")
            action_name = record.get("action", "")
            alert_type_for_cat = record.get("alert_type", "unknown")
            confidence_at_decision = float(record.get("confidence") or 0.0)
            from app.domains.soc.config import resolve_alert_category as _resolve_cat_po
            # BACKLOG-047b: prefer a.category (already canonical); only fall back to
            # resolve_alert_category(alert_type) when category is absent, avoiding
            # the H7-FIX-1 mapping on every outcome submission.
            _resolved_category = (
                record.get("category")
                or _resolve_cat_po(alert_type_for_cat)
            )

            try:
                _soc_cfg_rl = _rl_soc_config()
                if getattr(_soc_cfg_rl, "RL_REWARD_LEDGER_ENABLED", False):
                    from app.services.rl_engine import get_reward_computer, get_reward_ledger

                    reward_result = get_reward_computer().compute(
                        action=action_name,
                        outcome="correct" if correct_bool else "incorrect",
                        category=_resolved_category,
                        context={
                            "campaign_id": record.get("campaign_id"),
                            "confidence": confidence_at_decision,
                        },
                    )
                    _rl_reward_ledger = get_reward_ledger()
            except Exception as _rl_reward_exc:
                logger.warning("[RL] Reward computation failed: %s", _rl_reward_exc)
                reward_result = None
                _rl_reward_ledger = None

            from app.domains.soc.config import SCORER_ACTIONS

            # refer_to_analyst is a routing decision, not a classification
            # action.  ProfileScorer has A=4 (SCORER_ACTIONS); skip learning.
            if action_name not in SCORER_ACTIONS:
                l5_persistence_status["l5_persistence_skipped_reason"] = "routing_action_not_scorable"
                # Capture state even though routing actions do not update
                # centroids or enter the shared learn path.
                try:
                    from app.services.gae_state import acquire_scorer as _acquire_scorer_non_scorable
                    from app.domains.soc.scorer_adapter import SOCCompoundingScorerAdapter

                    async with _acquire_scorer_non_scorable() as _ps_non_scorable:
                        if isinstance(_ps_non_scorable, SOCCompoundingScorerAdapter):
                            _ps_non_scorable.capture_existing_state(
                                capture_reason="non_scorable",
                                decision_id=request.decision_id,
                            )
                except Exception as _snapshot_exc:
                    logger.warning(
                        "[GAE][LEARN] SOC non-scorable state capture failed: %s",
                        _snapshot_exc,
                    )
                if fv is None:
                    print(f"[GAE] Decision node found but factor_vector is NULL -- skipping weight update")
                else:
                    print(
                        f"[GAE] Skipping learning update for routing action "
                        f"{action_name!r} (not in SCORER_ACTIONS)"
                    )
                # Routing actions are intentionally excluded from centroid
                # learning, but their verified outcome must still be written
                # to the authoritative Decision node.  Without this write,
                # analytics never observes d.correct for the learning-loop
                # flow even though the decision was confirmed.
                _soc_store.write_outcome(**_outcome_write_kwargs)
                wu = None
                # Still count this verified outcome so decision_count reflects
                # all verified decisions, not only scorable actions.
                with _soc_perf_phase(
                    "learning_state_update",
                    route=_perf_route,
                    alert_id=request.alert_id,
                    decision_id=request.decision_id,
                    category=_resolved_category,
                    action=action_name,
                ):
                    _ref_ls = get_learning_state()
                    if _ref_ls:
                        _ref_ls.decision_count += 1
                        save_learning_state()
            else:
                with _soc_perf_phase(
                    "learning_state_update",
                    route=_perf_route,
                    alert_id=request.alert_id,
                    decision_id=request.decision_id,
                    category=_resolved_category,
                    action=action_name,
                ):
                    f = _validate_scoring_factor_vector(fv)
                    action_index = list(SCORER_ACTIONS).index(action_name)
                    wu = None

                try:
                    _soc_cfg_rl = _rl_soc_config()
                    if getattr(_soc_cfg_rl, "RL_EXPLORATION_ENABLED", False):
                        _explored = _rl_bool(record.get("explored"))
                        _vetoed = _rl_bool(record.get("explored_but_referred"))
                        _executed = _rl_bool(record.get("exploration_executed"))
                        _explored_action = record.get("explored_action") or action_name
                        if (
                            _explored and _executed and not _vetoed
                            and _explored_action in SCORER_ACTIONS
                            and _resolved_category != "unclassified"
                        ):
                            from app.domains.soc.config import SOCDomainConfig as _SDC_rl
                            from app.services.rl_engine import get_exploration_policy

                            _posterior_cat_idx = _SDC_rl().get_category_index(_resolved_category)
                            _posterior_action_idx = list(SCORER_ACTIONS).index(_explored_action)
                            get_exploration_policy().update_posterior(
                                _posterior_cat_idx,
                                _posterior_action_idx,
                                correct_bool,
                            )
                            _rl_posterior_updated = True
                except Exception as _rl_posterior_exc:
                    logger.warning("[RL] Posterior update failed: %s", _rl_posterior_exc)

                # SOC-Q3 / DRIFT-01: Wire conservation status → scorer auto-pause.
                # auto_pause_active (14+ RED days) overrides current status to RED
                # so that a brief GREEN window cannot clear an accumulated freeze.
                # FIX 1: fail-closed — if health check throws, block learning (treat as RED).
                _conservation_block = False
                _eff_status = "UNKNOWN"
                try:
                    with _soc_perf_phase(
                        "conservation_monitor",
                        route=_perf_route,
                        alert_id=request.alert_id,
                        decision_id=request.decision_id,
                        category=_resolved_category,
                        action=action_name,
                    ):
                        from app.services.learning_health import LearningHealthMonitor
                        with _soc_perf_phase(
                            "l5_conservation_write",
                            route=_perf_route,
                            alert_id=request.alert_id,
                            decision_id=request.decision_id,
                            category=_resolved_category,
                            action=action_name,
                        ):
                            _health = await LearningHealthMonitor.evaluate(graph_client)
                        from app.services.evolver import get_soc_conservation_provider

                        get_soc_conservation_provider().update_from_health(_health)
                        _eff_status, _eff_reason = _soc_effective_conservation_status(_health)
                        l5_persistence_status["conservation_status"] = _eff_status
                        l5_persistence_status["raw_conservation_status"] = str(
                            _health.get("status", "UNKNOWN")
                        ).upper()
                        l5_persistence_status["conservation_status_reason"] = _eff_reason
                except Exception as _cse:
                    logger.warning("Conservation status update failed: %s", _cse)
                    _conservation_block = True  # fail-closed: unknown health -> block

                # CORR-2 fix: ProfileScorer.update() — gated by LEARNING_ENABLED (default False).
                # gt_action_index = analyst's actual chosen action when provided;
                # falls back to predicted action_index only when analyst_action is absent.
                # is_correct is re-derived from the comparison so it stays consistent.
                _soc_learning_active = _soc_learning_enabled()
                _unclassified_alert = False
                if _soc_learning_active and action_name in SCORER_ACTIONS:
                    from app.domains.soc.config import resolve_alert_category

                    _unclassified_alert = (
                        resolve_alert_category(alert_type_for_cat) == "unclassified"
                    )
                    if _unclassified_alert:
                        logger.warning(
                            "[GAE][LEARN] Skipping ProfileScorer.update for unclassified alert_type=%r",
                            alert_type_for_cat,
                        )
                        l5_persistence_status["l5_persistence_skipped_reason"] = (
                            "unclassified_alert_type"
                        )
                if not _soc_learning_active and action_name in SCORER_ACTIONS:
                    l5_persistence_status["l5_persistence_skipped_reason"] = "soc_learning_disabled"
                if _soc_learning_active and action_name in SCORER_ACTIONS and not _unclassified_alert:
                    from app.domains.soc.config import resolve_alert_category, SOCDomainConfig as _SDC_out
                    _cat_name_out = resolve_alert_category(alert_type_for_cat)
                    _cat_idx_out  = _SDC_out().get_category_index(_cat_name_out)

                    _analyst_action = request.analyst_action
                    _scorer_acts = list(SCORER_ACTIONS)
                    if _analyst_action and _analyst_action in _scorer_acts:
                        # Analyst supplied their action — authoritative GT
                        _gt_idx  = _scorer_acts.index(_analyst_action)
                        _correct = (action_index == _gt_idx)
                    else:
                        # No analyst action: use outcome flag; GT = predicted (correct)
                        # or unknown (incorrect — predicted is the best proxy available)
                        _gt_idx  = action_index
                        _correct = correct_bool

                    from app.services.gae_state import (
                        acquire_scorer as _acquire_scorer,
                        get_profile_scorer as _get_live_profile_scorer,
                        get_soc_centroid as _get_soc_centroid,
                        guarded_update as _guarded_update,
                        persist_soc_outcome_and_centroid as _persist_soc_outcome_and_centroid,
                        persist_soc_dk_weights as _persist_soc_dk_weights,
                        update_dk_welford_tracker as _update_dk_welford_tracker,
                    )
                    from app.domains.soc.scorer_adapter import SOCCompoundingScorerAdapter
                    # A detached process-wide scorer is a cold-start guard
                    # condition.  Preserve explicitly injected acquire
                    # contexts (used by alternate runtimes and tests).
                    if (
                        _get_live_profile_scorer() is None
                        and getattr(_acquire_scorer, "__module__", "")
                        == "app.services.gae_state"
                    ):
                        _conservation_block = True
                        l5_persistence_status["l5_persistence_skipped_reason"] = (
                            "scorer_not_attached"
                        )
                    if _conservation_block:
                        logger.warning("[B5] Conservation check failed -- learning blocked (fail-closed)")
                        if l5_persistence_status["l5_persistence_skipped_reason"] is None:
                            l5_persistence_status["l5_persistence_skipped_reason"] = (
                                "conservation_check_failed"
                            )
                        _soc_store.write_outcome(**_outcome_write_kwargs)
                        try:
                            async with _acquire_scorer() as _ps_blocked:
                                if isinstance(_ps_blocked, SOCCompoundingScorerAdapter):
                                    try:
                                        _ps_blocked.capture_existing_state(
                                            capture_reason="guarded_pause",
                                            decision_id=request.decision_id,
                                        )
                                    except Exception as _snapshot_exc:
                                        logger.warning(
                                            "[GAE][LEARN] SOC guarded-pause state capture failed: %s",
                                            _snapshot_exc,
                                        )
                        except Exception as _acquire_exc:
                            # The outcome write above remains authoritative. A
                            # cold-start scorer snapshot is only an optional
                            # learning artifact and must not turn the route into
                            # a 500 response.
                            logger.warning(
                                "[GAE][LEARN] SOC guarded-pause snapshot unavailable: %s",
                                _acquire_exc,
                            )
                    else:
                        _cu = None
                        _guard_block_reason = None
                        # D-05: acquire lock and capture scorer atomically so a concurrent
                        # reset cannot replace _learning_state between capture and update.
                        async with _acquire_scorer() as _ps_out:
                            _orig_eta_out = getattr(_ps_out, "eta", None)
                            _orig_eta_neg_out = getattr(_ps_out, "eta_neg", None)
                            _orig_eta_override_out = getattr(_ps_out, "eta_override", None)
                            _pre_centroids = {
                                action_index: _get_soc_centroid(_ps_out, _cat_idx_out, action_index)
                            }
                            if _gt_idx != action_index:
                                _pre_centroids[_gt_idx] = _get_soc_centroid(
                                    _ps_out, _cat_idx_out, _gt_idx
                                )
                            try:
                                if _analyst_eta is not None:
                                    _ps_out.eta_override = _analyst_eta
                                try:
                                    _soc_cfg_rl = _rl_soc_config()
                                    if (
                                        getattr(_soc_cfg_rl, "RL_ETA_MODULATION_ENABLED", False)
                                        and reward_result is not None
                                    ):
                                        _rl_weight = float(reward_result.reward_weight)
                                        if hasattr(_ps_out, "eta") and _ps_out.eta is not None:
                                            _ps_out.eta = _ps_out.eta * _rl_weight
                                        if hasattr(_ps_out, "eta_neg") and _ps_out.eta_neg is not None:
                                            _ps_out.eta_neg = _ps_out.eta_neg * _rl_weight
                                        if (
                                            hasattr(_ps_out, "eta_override")
                                            and _ps_out.eta_override is not None
                                        ):
                                            _ps_out.eta_override = _ps_out.eta_override * _rl_weight
                                except Exception as _rl_eta_exc:
                                    logger.warning("[RL] Eta modulation failed: %s", _rl_eta_exc)
                                # FIX 3: status write inside lock prevents concurrent race
                                if hasattr(_ps_out, "set_conservation_status"):
                                    _ps_out.set_conservation_status(_eff_status)
                                # DRIFT-03: route through guarded_update() so D3/D2/D7
                                # spike guards AND conservation freeze are enforced.
                                with _soc_perf_phase(
                                    "profile_scorer_update",
                                    route=_perf_route,
                                    alert_id=request.alert_id,
                                    decision_id=request.decision_id,
                                    category=_cat_name_out,
                                    action=action_name,
                                    factor_vector_len=len(f.flatten()),
                                ):
                                    _cu = _guarded_update(
                                        _ps_out,
                                        f=f.flatten(),
                                        category_index=_cat_idx_out,
                                        action_index=action_index,
                                        correct=_correct,
                                        category_name=_cat_name_out,
                                        gt_action_index=_gt_idx,
                                    )
                                if isinstance(_ps_out, SOCCompoundingScorerAdapter):
                                    _compound_scorer = _ps_out._compound
                                    if _cu is None:
                                        # Conservation can pause the raw profile scorer before
                                        # guarded_update returns. Record the current state even
                                        # though no outcome or learning artifact exists yet.
                                        try:
                                            _ps_out.capture_existing_state(
                                                capture_reason="guarded_pause",
                                                decision_id=request.decision_id,
                                            )
                                        except Exception as _snapshot_exc:
                                            logger.warning(
                                                "[GAE][LEARN] SOC guarded-pause state capture failed: %s",
                                                _snapshot_exc,
                                            )
                                if _cu is not None:
                                    _actual_action_index = _gt_idx
                                    _actual_action_name = _scorer_acts[_actual_action_index]
                                    l5_persistence_status["l5_persistence_source"] = "profile_scorer"
                                    try:
                                        with _soc_perf_phase(
                                            "l5_dk_weight_write",
                                            route=_perf_route,
                                            alert_id=request.alert_id,
                                            decision_id=request.decision_id,
                                            category=_cat_name_out,
                                            action=_actual_action_name,
                                        ):
                                            _update_dk_welford_tracker(f.flatten(), bool(_correct))
                                    except Exception as _welford_exc:
                                        logger.warning(
                                            "[GAE][LEARN] SOC DK Welford update failed: %s",
                                            _welford_exc,
                                        )
                                    _reestimate_ok = False
                                    try:
                                        _reestimate_dk = getattr(_ps_out, "reestimate_dk", None)
                                        if callable(_reestimate_dk):
                                            _reestimate_dk()
                                            _reestimate_ok = True
                                    except Exception as _dk_exc:
                                        logger.warning(
                                            "[GAE][LEARN] SOC DK reestimate failed: %s",
                                            _dk_exc,
                                        )
                                    _checkpoint_writer = None
                                    if isinstance(_ps_out, SOCCompoundingScorerAdapter):
                                        def _checkpoint_writer(transaction):
                                            try:
                                                return _compound_scorer._persist_learning_artifacts(
                                                    request.decision_id,
                                                    actual_action=_scorer_acts[_gt_idx],
                                                    outcome=outcome_label,
                                                    is_correct=bool(_correct),
                                                    category=_cat_name_out,
                                                    evidence_already_persisted=True,
                                                    skip_history_scan=True,
                                                    transaction=transaction,
                                                    raise_on_error=True,
                                                )
                                            except KeyError as _checkpoint_exc:
                                                # The authoritative graph outcome and
                                                # centroid write already succeeded.
                                                # A stale scorer-local decision index
                                                # must not convert that result to 500.
                                                logger.warning(
                                                    "[GAE][LEARN] scorer checkpoint skipped: %s",
                                                    _checkpoint_exc,
                                                )
                                                return None
                                    try:
                                        with _soc_perf_phase(
                                            "l5_centroid_write",
                                            route=_perf_route,
                                            alert_id=request.alert_id,
                                            decision_id=request.decision_id,
                                            category=getattr(_cu, "category_name", _cat_name_out),
                                            action=_actual_action_name,
                                        ):
                                            _centroid_persisted = await _persist_soc_outcome_and_centroid(
                                                store=_soc_store,
                                                outcome=_outcome_write_kwargs,
                                                centroid={
                                                    "scorer": _ps_out,
                                                    "category": getattr(_cu, "category_name", _cat_name_out),
                                                    "category_index": getattr(_cu, "category_index", _cat_idx_out),
                                                    "action": _actual_action_name,
                                                    "action_index": _actual_action_index,
                                                    "caused_by_decision_id": request.decision_id,
                                                    "pre_centroid": _pre_centroids.get(
                                                        _actual_action_index
                                                    ),
                                                },
                                                checkpoint_writer=_checkpoint_writer,
                                                logger=logger,
                                            )
                                        l5_persistence_status["l5_centroid_persisted"] = bool(
                                            _centroid_persisted
                                        )
                                        l5_persistence_status["l5_shaped_by_attempted"] = bool(
                                            _centroid_persisted and request.decision_id
                                        )
                                        l5_persistence_status["l5_persistence_skipped_reason"] = (
                                            None if _centroid_persisted
                                            else "persist_soc_centroid_returned_false"
                                        )
                                    except Exception as _centroid_exc:
                                        logger.exception(
                                            "[GAE][LEARN] SOC L5 centroid persistence failed: %s",
                                            _centroid_exc,
                                        )
                                        raise
                                    if _reestimate_ok:
                                        try:
                                            with _soc_perf_phase(
                                                "l5_dk_weight_write",
                                                route=_perf_route,
                                                alert_id=request.alert_id,
                                                decision_id=request.decision_id,
                                                category=_cat_name_out,
                                                action=action_name,
                                            ):
                                                _persist_soc_dk_weights(_ps_out, logger=logger)
                                        except Exception as _dk_persist_exc:
                                            logger.warning(
                                                "[GAE][LEARN] SOC L5 DK persistence failed: %s",
                                                _dk_persist_exc,
                                            )
                            finally:
                                if _orig_eta_out is not None and hasattr(_ps_out, "eta"):
                                    _ps_out.eta = _orig_eta_out
                                if _orig_eta_neg_out is not None and hasattr(_ps_out, "eta_neg"):
                                    _ps_out.eta_neg = _orig_eta_neg_out
                                if hasattr(_ps_out, "eta_override"):
                                    _ps_out.eta_override = _orig_eta_override_out
                        if _cu is None:
                            _soc_store.write_outcome(**_outcome_write_kwargs)
                            if "_ps_out" in locals() and getattr(_ps_out, "is_paused", False):
                                _guard_block_reason = "conservation_paused"
                            if not _guard_block_reason:
                                _guard_block_reason = "guarded_update_returned_none"
                            l5_persistence_status["l5_persistence_skipped_reason"] = _guard_block_reason
                            logger.info("[GAE][LEARN] Update blocked by conservation/spike/freeze guard")
                else:
                    # Learning may be disabled, or the alert may be
                    # intentionally unclassified.  In either case the
                    # verified outcome still belongs on the Decision node;
                    # only scorer learning is skipped.
                    _soc_store.write_outcome(**_outcome_write_kwargs)
                    if l5_persistence_status["l5_persistence_skipped_reason"] == "not_attempted":
                        l5_persistence_status["l5_persistence_skipped_reason"] = (
                            "soc_learning_disabled"
                            if not _soc_learning_active
                            else "unclassified_alert_type"
                        )

                # Keep the convergence endpoint's LearningState counter in sync
                # with every verified scorable outcome.  The SOC adapter owns the
                # wrapped ProfileScorer counter, so it cannot update this separate
                # convergence-state counter for us.
                with _soc_perf_phase(
                    "learning_state_update",
                    route=_perf_route,
                    alert_id=request.alert_id,
                    decision_id=request.decision_id,
                    category=_resolved_category,
                    action=action_name,
                ):
                    _ref_ls = get_learning_state()
                    if _ref_ls:
                        _ref_ls.decision_count += 1
                        save_learning_state()

                # Change 5: ProfileSnapshot every 50 decisions
                if wu is not None:
                    with _soc_perf_phase(
                        "snapshot_evolution_logging",
                        route=_perf_route,
                        alert_id=request.alert_id,
                        decision_id=request.decision_id,
                        category=_resolved_category,
                        action=action_name,
                        ):
                            from app.services.snapshots import maybe_write_profile_snapshot
                            await maybe_write_profile_snapshot(get_learning_state().decision_count)

                if wu and wu.centroid_update is not None:
                    cu = wu.centroid_update
                    # Write centroid_delta_norm back to the Decision node
                    await graph_client.run_query(
                        f"""
                        MATCH (d:Decision {{decision_id: {_S(request.decision_id)}}})
                        WHERE d.domain = 'soc'
                        SET d.centroid_delta_norm = {cu.centroid_delta_norm},
                            d.category            = {_S(cu.category_name)}
                        """
                    )
                    print(
                        f"[GAE] Centroid updated: action={cu.action_name} "
                        f"category={cu.category_name} "
                        f"outcome={outcome_int:+d} "
                        f"centroid_delta_norm={cu.centroid_delta_norm:.4f} "
                        f"step={cu.decision_count}"
                    )
                    centroid_update_payload = {
                        "centroid_delta_norm": cu.centroid_delta_norm,
                        "category_name":       cu.category_name,
                        "action_name":         cu.action_name,
                        "category_index":      cu.category_index,
                        "action_index":        cu.action_index,
                        "correct":             correct_bool,
                    }

                # ============================================================
                # BACKLOG-020 Phase 7: Update GraphSnapshot after graph write.
                # Called AFTER the graph write succeeds — snapshot stays
                # consistent if the write raises before this point.
                # ============================================================
                try:
                    from app.state.graph_snapshot import get_snapshot as _get_snap
                    from app.domains.soc.config import resolve_alert_category as _resolve_cat
                    _snap = _get_snap()
                    _cat_snap = _resolve_cat(alert_type_for_cat)
                    if _cat_snap == "unclassified":
                        logger.warning(
                            "[SNAPSHOT] Skipping unclassified alert_type=%r",
                            alert_type_for_cat,
                        )
                        raise ValueError("unclassified alert type is not snapshottable")
                    _was_override = bool(
                        request.analyst_action
                        and request.analyst_action != action_name
                    )
                    try:
                        _snap.on_verified_decision(
                            category=_cat_snap,
                            was_override=_was_override,
                            quality_signal=1.0 if correct_bool else 0.0,
                            is_correct=correct_bool,
                        )
                    except Exception as _snap_exc:
                        logger.warning(
                            "[SNAPSHOT] verified_decisions increment failed: %s",
                            _snap_exc,
                        )
                    # Recompute IKS after centroid update (if centroid changed).
                    if wu and wu.centroid_update is not None:
                        try:
                            from app.services.gae_state import get_profile_scorer as _get_ps_snap
                            from app.services.iks import compute_visible_iks as _compute_visible_iks
                            _ps_snap = _get_ps_snap()
                            if _ps_snap is not None:
                                _snap.on_iks_recalculated(
                                    await _compute_visible_iks(graph_client, scorer=_ps_snap)
                                )
                        except Exception as _snap_exc:
                            logger.warning(
                                "[SNAPSHOT] IKS recalculation failed: %s",
                                _snap_exc,
                            )
                except Exception as _snap_exc:
                    logger.warning(
                        "[SNAPSHOT] Snapshot update failed (non-blocking): %s",
                        _snap_exc,
                    )

                # ============================================================
                # EXP-G1 (BACKLOG-015 extension): log per-decision distance
                # fields to DecisionDistanceLog node.  Fire-and-forget —
                # never blocks the outcome response.
                # Requires: mu from ProfileScorer, mu_zero from bootstrap JSON.
                # PatternHistory is factor index 4 in SOC_FACTORS.
                # ============================================================
                try:
                    import asyncio as _asyncio
                    from app.services.reconvergence_logger import (
                        log_decision_distance as _log_dist,
                        fetch_category_distribution as _fetch_cat_dist,
                    )
                    from app.services.gae_state import get_mu_zero as _get_mu_zero, get_profile_scorer as _get_ps
                    _mu_zero = _get_mu_zero()
                    _ps_dist = _get_ps()
                    if _mu_zero is not None and _ps_dist is not None:
                        _ph_value = float(fv[4]) if len(fv) > 4 else 0.0

                        async def _g1_task():
                            _cat_dist = await _fetch_cat_dist(graph_client)
                            await _log_dist(
                                graph_client=graph_client,
                                decision_id=request.decision_id,
                                mu=_ps_dist.centroids,
                                mu_zero=_mu_zero,
                                pattern_history_value=_ph_value,
                                alert_category_distribution=_cat_dist,
                            )

                        _asyncio.create_task(_g1_task())
                        logger.info(
                            "[EXP-G1] DecisionDistanceLog task queued: id=%s",
                            request.decision_id,
                        )
                except Exception as _g1_exc:
                    logger.warning("[EXP-G1] Distance log scheduling failed: %s", _g1_exc)

                # ============================================================
                # FLYWHEEL: Create TRIGGERED_EVOLUTION edge for correct scorer
                # actions — feeds PatternHistoryFactorComputer (CLAIM-W2).
                # Only fires on correct outcomes for SCORER_ACTIONS (not
                # refer_to_analyst). Fire-and-forget; never blocks response.
                # ============================================================
                _triggered_evolution_written = False
                if correct_bool and action_name in SCORER_ACTIONS:
                    try:
                        with _soc_perf_phase(
                            "snapshot_evolution_logging",
                            route=_perf_route,
                            alert_id=request.alert_id,
                            decision_id=request.decision_id,
                            category=_resolved_category,
                            action=action_name,
                        ):
                            _evo_id = f"EVO-{uuid.uuid4().hex[:4].upper()}"
                            _evo_ts = int(datetime.utcnow().timestamp() * 1000)
                            _evo_dec_num = int(get_learning_state().decision_count)
                            _evo_ph = float(fv[3]) if (isinstance(fv, list) and len(fv) > 3) else 0.4
                            await graph_client.run_query(
                                f"""
                                MATCH (d:Decision {{decision_id: {_S(request.decision_id)}}})
                                WHERE d.domain = 'soc'
                                CREATE (evo:EvolutionEvent {{
                                    id:              {_S(_evo_id)},
                                    event_type:      'verified_outcome',
                                    triggered_by:    {_S(request.decision_id)},
                                    category:        {_S(_resolved_category)},
                                    correct:         true,
                                    action:          {_S(action_name)},
                                    timestamp_epoch: {_evo_ts}
                                }})
                                CREATE (d)-[:TRIGGERED_EVOLUTION {{
                                    timestamp_epoch: {_evo_ts},
                                    decision_id:     {_S(request.decision_id)},
                                    category:        {_S(_resolved_category)},
                                    correct:         true,
                                    action:          {_S(action_name)}
                                }}]->(evo)
                                SET d.verified_correct  = true,
                                    d.factor_snapshot   = {_S(json.dumps(fv if isinstance(fv, list) else []))},
                                    d.decision_number   = {_evo_dec_num},
                                    d.action_index      = {action_index}
                                """
                            )
                        _triggered_evolution_written = True
                        await event_bus.emit(GraphMutated(
                            mutation_type="evolution",
                            affected_entities=(request.decision_id, request.alert_id),
                        ))
                        logger.info(
                            "[FLYWHEEL] TRIGGERED_EVOLUTION edge created: %s -> %s",
                            request.decision_id,
                            request.alert_id,
                        )
                    except Exception as _evo_exc:
                        logger.warning(
                            "[FLYWHEEL] TRIGGERED_EVOLUTION creation failed (non-blocking): %s",
                            _evo_exc,
                        )

                try:
                    _soc_cfg_rl = _rl_soc_config()
                    if (
                        getattr(_soc_cfg_rl, "RL_CHAIN_CREDIT_ENABLED", False)
                        and correct_bool
                        and action_name in SCORER_ACTIONS
                        and _triggered_evolution_written
                    ):
                        from app.services.rl_engine import get_credit_assigner, get_reward_ledger

                        await get_credit_assigner().assign_chain_credit(
                            source_decision_id=request.decision_id,
                            category=_resolved_category,
                            action_index=action_index,
                            current_decision_number=int(get_learning_state().decision_count),
                            reward=(
                                reward_result.graded_reward
                                if reward_result is not None
                                else 1.0
                            ),
                            reward_ledger=_rl_reward_ledger or get_reward_ledger(),
                        )
                except Exception as _rl_chain_exc:
                    logger.warning("[RL] Chain credit assignment failed: %s", _rl_chain_exc)

                # ============================================================
                # FEATURE-04: Auto-snapshot centroids every SNAPSHOT_INTERVAL
                # verified decisions for the Centroid Time Machine.
                # Fire-and-forget — never blocks the outcome response.
                # ============================================================
                try:
                    from app.services.gae_state import (
                        maybe_write_centroid_snapshot as _maybe_snap,
                        get_profile_scorer as _get_ps_snap2,
                    )
                    _ps_snap2 = _get_ps_snap2()
                    if _ps_snap2 is not None:
                        _maybe_snap(
                            _ps_snap2,
                            decision_id=str(request.decision_id),
                            category=_resolved_category,
                        )
                except Exception as _snap2_exc:
                    logger.warning(
                        "[SNAPSHOT] Centroid auto-snapshot failed (non-blocking): %s",
                        _snap2_exc,
                    )

        if reward_result is not None and _rl_reward_ledger is not None and gae_result:
            try:
                _record_for_reward = gae_result[0]
                _rl_reward_ledger.append(
                    decision_id=request.decision_id,
                    reward_result=reward_result,
                    category=_resolved_category,
                    action=action_name,
                    alert_id=request.alert_id,
                    explored=_rl_bool(_record_for_reward.get("explored")),
                    explored_but_referred=_rl_bool(
                        _record_for_reward.get("explored_but_referred")
                    ),
                    posterior_updated=_rl_posterior_updated,
                )
            except Exception as _rl_ledger_exc:
                logger.warning("[RL] Reward ledger append failed: %s", _rl_ledger_exc)

        _shadow_verified_action = None
        if request.analyst_action:
            _shadow_verified_action = request.analyst_action
        elif correct_bool and gae_result:
            _shadow_verified_action = action_name
        if _shadow_verified_action:
            from app.services.shadow_runner import fill_shadow_outcome
            fill_shadow_outcome(request.alert_id, _shadow_verified_action)

        # ====================================================================
        # Emit events (every graph mutation MUST emit events)
        # ====================================================================
        await event_bus.emit(OutcomeVerified(
            alert_id    = request.alert_id,
            decision_id = request.decision_id,
            outcome     = outcome_label,
            correct     = correct_bool,
        ))
        await event_bus.emit(GraphMutated(
            mutation_type     = "outcome",
            affected_entities = (request.alert_id, request.decision_id),
        ))

        # ====================================================================
        # Process trust / pattern / narrative (existing feedback loop)
        # ====================================================================
        result = process_outcome(
            alert_id=request.alert_id,
            decision_id=request.decision_id,
            outcome=request.outcome,
            alert_category=_resolved_category,
        )

        print(f"[FEEDBACK] Processed {request.outcome} outcome for {request.alert_id}")
        print(f"[FEEDBACK] Graph updates: {len(result.graph_updates)}")
        print(f"[FEEDBACK] Consequence: {result.consequence}")
        print(f"[FEEDBACK] centroid_update in response: {centroid_update_payload is not None}")

        if gae_result and correct_bool and action_name == "escalate":
            try:
                from app.services.servicenow_mock import get_servicenow_mock
                _result_payload = result.model_dump()
                get_servicenow_mock().create_incident(
                    decision_id=str(getattr(request, "decision_id", "")),
                    alert_id=str(getattr(request, "alert_id", "")),
                    alert_type=str(locals().get("alert_type_for_cat", "Unknown") or "Unknown"),
                    category=str(locals().get("_resolved_category", "Security") or "Security"),
                    confidence=float(locals().get("confidence_at_decision", 0.5) or 0.5),
                    nl_explanation=str(_result_payload.get("narrative", "") or ""),
                )
            except Exception as _sn_exc:
                logger.warning("ServiceNow mock creation failed: %s", _sn_exc)

        with _soc_perf_phase(
            "response_serialization",
            route=_perf_route,
            alert_id=request.alert_id,
            decision_id=request.decision_id,
            category=_resolved_category,
            action=locals().get("action_name"),
        ):
            response_body = result.model_dump()
            response_body["centroid_update"] = centroid_update_payload
            response_body["l5_centroid_persisted"] = l5_persistence_status[
                "l5_centroid_persisted"
            ]
            response_body["l5_shaped_by_attempted"] = l5_persistence_status[
                "l5_shaped_by_attempted"
            ]
            response_body["l5_persistence_skipped_reason"] = l5_persistence_status[
                "l5_persistence_skipped_reason"
            ]
            response_body["l5_persistence"] = l5_persistence_status
        return response_body

    except HTTPException as exc:
        _perf_total_status = "error"
        _perf_total_exception = type(exc).__name__
        raise
    except ValueError as exc:
        _perf_total_status = "error"
        _perf_total_exception = type(exc).__name__
        raise
    except Exception as e:
        _perf_total_status = "error"
        _perf_total_exception = type(e).__name__
        print(f"[ERROR] Failed to process outcome: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process outcome: {str(e)}"
        )
    finally:
        _soc_perf_emit_duration(
            "outcome_request_total",
            _perf_total_started,
            route=_perf_route,
            status=_perf_total_status,
            exception_type=_perf_total_exception,
            alert_id=_perf_alert_id,
            decision_id=_perf_decision_id,
            category=locals().get("_resolved_category"),
            action=locals().get("action_name"),
        )


# ============================================================================
# GET /api/alert/outcome/status - Get Feedback Status
# ============================================================================

@router.get("/alert/outcome/status")
async def get_outcome_status(alert_id: str):
    """
    Get feedback status for an alert.
    Used by frontend to show/hide feedback buttons.

    Args:
        alert_id: Alert identifier (query parameter)

    Returns:
        Dictionary with feedback status
    """
    print(f"[FEEDBACK] GET /alert/outcome/status called for {alert_id}")

    try:
        status = get_feedback_status(alert_id)
        print(f"[FEEDBACK] Status for {alert_id}: has_feedback={status['has_feedback']}")
        return status

    except Exception as e:
        print(f"[ERROR] Failed to get feedback status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get feedback status: {str(e)}"
        )


# ============================================================================
# GET /api/alert/policy-check - Check Policy Conflicts
# ============================================================================

_LEGACY_POLICY_CONTEXTS = {
    "ALERT-7823": {
        "user_risk_score": 0.85,
        "user_traveling": True,
        "vpn_matches_location": True,
        "alert_type": "anomalous_login",
    },
    "ALERT-7824": {
        "user_risk_score": 0.45,
        "alert_type": "phishing",
        "known_campaign_signature": True,
    },
}


async def _build_policy_context(alert_id: str) -> Dict[str, Any]:
    """Build policy context from graph Alert data; legacy demo IDs are fallback only."""
    rows = await graph_client.run_query(
        f"""
        MATCH (alert:Alert {{alert_id: {_S(alert_id)}}})
        OPTIONAL MATCH (alert)-[:INVOLVES]->(user:User)
        OPTIONAL MATCH (alert)-[:DETECTED_ON]->(detected_asset:Asset)
        OPTIONAL MATCH (alert)-[:INVOLVES]->(involved_asset:Asset)
        OPTIONAL MATCH (alert)-[:MATCHES]->(pattern:AttackPattern)
        OPTIONAL MATCH (user)-[:HAS_TRAVEL]->(travel:TravelContext)
        RETURN
            alert.alert_type AS alert_type,
            alert.category AS category,
            alert.source_location AS source_location,
            user.risk_score AS user_risk_score,
            detected_asset.criticality AS detected_asset_criticality,
            involved_asset.criticality AS involved_asset_criticality,
            travel.destination AS travel_destination,
            CASE WHEN pattern IS NOT NULL THEN true ELSE false END AS known_campaign_signature
        LIMIT 1
        """
    )

    if not rows:
        context = dict(_LEGACY_POLICY_CONTEXTS.get(alert_id, {}))
        context.setdefault("user_risk_score", 0.5)
        context.setdefault("alert_type", "unknown")
        return context

    row = rows[0]
    alert_type = row.get("alert_type") or row.get("category") or "unknown"
    source_location = row.get("source_location")
    travel_destination = row.get("travel_destination")
    context = {
        "user_risk_score": row.get("user_risk_score") or 0.5,
        "alert_type": alert_type,
        "asset_criticality": (
            row.get("detected_asset_criticality")
            or row.get("involved_asset_criticality")
            or "medium"
        ),
        "user_traveling": travel_destination is not None,
        "vpn_matches_location": (
            travel_destination is not None
            and source_location == travel_destination
        ),
        "known_campaign_signature": bool(row.get("known_campaign_signature")),
    }
    return context


@router.get("/alert/policy-check")
async def check_policy_conflicts(alert_id: str):
    """
    Check if an alert has conflicting policies.

    Args:
        alert_id: Alert identifier (query parameter)

    Returns:
        PolicyConflict object with conflict detection results
    """
    print(f"[POLICY] GET /alert/policy-check called for {alert_id}")

    try:
        context = await _build_policy_context(alert_id)
        alert_type = context.get("alert_type") or "unknown"
        logger.debug("[POLICY] Resolved alert_type=%s for %s", alert_type, alert_id)

        print(f"[POLICY] Context: {context}")

        # Detect policy conflicts
        result = detect_policy_conflicts(alert_id, context)

        print(f"[POLICY] Conflict detected: {result.has_conflict}")
        if result.has_conflict:
            resolution = cast(Any, result.resolution)
            print(f"[POLICY] Policies in conflict: {[p.id for p in result.conflicting_policies]}")
            print(f"[POLICY] Winner: {resolution.winning_policy}")
        else:
            print(f"[POLICY] Policies applied: {[p.id for p in result.policies_applied]}")

        return result.model_dump()

    except Exception as e:
        print(f"[ERROR] Failed to check policy conflicts: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check policy conflicts: {str(e)}"
        )


# ============================================================================
# GET /api/alert/policy-history - Get Conflict Resolution History
# ============================================================================

@router.get("/alert/policy-history")
async def get_policy_history():
    """
    Get all resolved policy conflicts for audit/reporting.

    Returns:
        List of PolicyResolution objects
    """
    print("[POLICY] GET /alert/policy-history called")

    try:
        history = get_conflict_history()
        print(f"[POLICY] Returning {len(history)} resolved conflicts")

        return {
            "conflicts": [resolution.model_dump() for resolution in history],
            "total_count": len(history)
        }

    except Exception as e:
        print(f"[ERROR] Failed to get policy history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get policy history: {str(e)}"
        )


# ============================================================================
# GET /api/soc/profile - ProfileScorer state for Tab 2 centroid heatmap
# ============================================================================

@router.get("/soc/profile", response_model=ProfileResponse)
async def get_profile_state():
    """
    Return current ProfileScorer state for frontend display.
    Used by Tab 2 centroid heatmap (SOC-PROF-3).
    Includes IKS (Institutional Knowledge Score).
    """
    scorer = get_profile_scorer()
    from app.domains.soc.config import SOC_CATEGORIES, SCORER_ACTIONS
    from app.services.iks import compute_iks, interpret, _compute_delta_7d

    if scorer is None:
        import numpy as _np
        n_cats = len(SOC_CATEGORIES)
        n_actions = len(SCORER_ACTIONS)
        return {
            "categories": SOC_CATEGORIES,
            "actions": SCORER_ACTIONS,
            "centroids": _np.zeros((n_cats, n_actions, 6)).tolist(),
            "counts": _np.zeros((n_cats, n_actions), dtype=int).tolist(),
            "decision_count": 0,
            "iks": {
                "current": 0.0,
                "delta_7d": 0.0,
                "interpretation": "No decisions recorded yet.",
                "decision_count": 0,
                "estimated": 0.0,
                "trend": [],
                "switching_cost": {
                    "decisions_accumulated": 0,
                    "equivalent_calendar": "0 decisions accumulated",
                    "common_categories_days": 14,
                    "rare_categories_note": "Rare categories take longer -- all context lost on switch.",
                    "competitor_iks": 0,
                    "decisions_per_day": 0.0,
                    "qualifies_one_quarter": False,
                    "interpretation": "No decisions recorded yet. A competitor starting fresh starts at IKS=0.",
                },
            },
        }

    # Use scorer.counts.shape[1] as source of truth — not len(SOC_ACTIONS).
    # SOC_ACTIONS has 5 elements (includes refer_to_analyst for referral policy);
    # ProfileScorer uses A=4 only (SCORER_ACTIONS). Iterating range(5) on a
    # (6,4) array causes IndexError at index 4.
    n_cats, n_actions = scorer.counts.shape
    decision_count = int(sum(  # SOURCE: in-memory ProfileScorer counts (resets on restart)
        scorer.counts[c, a]
        for c in range(n_cats)
        for a in range(n_actions)
    ))

    iks_result = compute_iks(scorer.centroids)  # SOURCE: computed from in-memory centroids (resets on restart)
    delta_7d = await _compute_delta_7d(iks_result["current"])
    trend = []  # populated lazily via /api/soc/profile/iks-trend if needed

    # V-SWITCHING-COST-FACTORIAL: decisions_per_day = V × α
    # V = daily alert volume, α = override/verification rate.
    # Defaults: V=200, α=0.25 → 50.0 decisions/day.
    _V     = 200.0
    _alpha = 0.25
    try:
        from app.services.gae_state import get_learning_state as _get_ls
        _ls = _get_ls()
        _prof = getattr(_ls, "profile_scorer", None)
        if _prof is not None:
            # ProfileScorer may expose tau (temperature); V and alpha come from
            # deployment config which is not yet wired — use defaults for now.
            pass
    except Exception:
        pass
    decisions_per_day: float = round(_V * _alpha, 4)
    qualifies_one_quarter: bool = decisions_per_day >= 20.0

    _base_interpretation = (
        f"{decision_count} verified analyst decisions are embedded in your system. "
        f"A competitor starting fresh starts at IKS=0."
    )
    if not qualifies_one_quarter:
        _base_interpretation += (
            f" At {decisions_per_day:.1f} decisions/day, full learning plateau"
            f" takes longer than one quarter."
        )

    return {
        "categories": SOC_CATEGORIES,
        "actions": SCORER_ACTIONS,         # A=4 -- matches counts/centroids shape
        "centroids": scorer.centroids.tolist(),   # shape (n_categories, n_actions, n_factors)
        "counts": scorer.counts.tolist(),  # shape (6, 4)
        "decision_count": decision_count,
        "iks": {
            "current":       iks_result["current"],
            "delta_7d":      delta_7d,
            "interpretation": interpret(iks_result["current"]),
            "decision_count": decision_count,
            "estimated":     iks_result["estimated"],
            "trend":         trend,
            "switching_cost": {
                "decisions_accumulated": decision_count,
                "equivalent_calendar": (
                    "full quarter at V=200"
                    if decision_count >= 537
                    else f"{decision_count} decisions accumulated"
                ),
                "common_categories_days": 14,
                "rare_categories_note": "Rare categories take longer -- all context lost on switch.",
                "competitor_iks": 0,
                "decisions_per_day":      decisions_per_day,
                "qualifies_one_quarter":  qualifies_one_quarter,
                "interpretation": _base_interpretation,
            },
        },
    }


# ============================================================================
# GET /api/rl/reward-summary - RL Reward Summary (Loop 3 governance)
# ============================================================================

@router.get("/rl/reward-summary")
async def rl_reward_summary():
    """
    Return aggregated RL reward signal from all outcome feedback recorded
    in this session.

    Reward signal: correct -> +0.3, incorrect -> -6.0 (asymmetric ratio 20:1).
    loop3_status is "active" once at least one decision has been recorded.
    """
    print("[RL] GET /rl/reward-summary called")

    try:
        summary = get_reward_summary()
        print(f"[RL] total_decisions={summary['total_decisions']}, cumulative_r_t={summary['cumulative_r_t']}")
        return summary

    except Exception as e:
        print(f"[ERROR] Failed to get reward summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get reward summary: {str(e)}"
        )


# ============================================================================
# GET /api/triage/decision-factors/{alert_id} - Decision Factor Breakdown (v3.0)
# ============================================================================

@router.get("/triage/decision-factors/{alert_id}", response_model=DecisionFactorsResponse)
async def decision_factors(alert_id: str):
    """
    Return the factor explainability matrix for an agent decision.

    Factor 3 (threat_intel_enrichment) is queried live from AGE using the
    ASSOCIATED_WITH relationship written by the Threat Intel refresh endpoint.
    The remaining 5 factors are pre-computed from demo context.

    Returns:
        {
          "alert_id":           str,
          "factors":            list of 6 factor dicts,
          "recommended_action": str,
          "confidence":         float,
          "decision_method":    str,
          "weights_note":       str
        }

    Each factor dict:
        { name, value, weight, contribution, explanation }
        contribution: "high" | "medium" | "low" | "none"
    """
    print(f"[TRIAGE] GET /triage/decision-factors/{alert_id} called")

    try:
        result = await get_decision_factors(alert_id)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"No analysis found for {alert_id}",
            )

        print(
            f"[TRIAGE] Returning {len(result['factors'])} factors "
            f"for {alert_id}"
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to get decision factors: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get decision factors: {str(e)}",
        )


# ============================================================================
# Helper: Get Graph Data for Visualization
# ============================================================================

async def get_graph_data(alert_id: str) -> Dict[str, Any]:
    """
    Get graph data for visualization.
    Returns nodes and relationships in a format suitable for graph rendering.
    """

    query = f"""
    MATCH (alert:Alert {{alert_id: {_S(alert_id)}}})
    MATCH (alert)-[:DETECTED_ON]->(asset:Asset)
    MATCH (alert)-[:INVOLVES]->(user:User)
    OPTIONAL MATCH (alert)-[:CLASSIFIED_AS]->(ap:AttackPattern)
    OPTIONAL MATCH (user)-[:HAS_TRAVEL]->(travel:TravelContext)
    OPTIONAL MATCH (alert)-[:MATCHES]->(pattern:AttackPattern)
    OPTIONAL MATCH (ap)-[:HANDLED_BY]->(playbook:Playbook)

    RETURN alert, asset, user, ap, travel, pattern, playbook
    """

    try:
        results = await graph_client.run_query(query)

        if not results:
            return {"nodes": [], "relationships": []}

        record = results[0]

        # Build nodes
        nodes = []
        relationships = []

        # Add alert node
        alert = record.get("alert")
        alert_id = _node_id(alert, "alert") if alert else "unknown"
        if alert:
            nodes.append({
                "id": alert_id,
                "label": alert_id,
                "type": "Alert",
                "properties": {
                    "alert_type": alert.get("alert_type"),
                    "severity": alert.get("severity")
                }
            })

        # Add user node
        user = record.get("user")
        user_id = _node_id(user, "user") if user else "unknown"
        if user:
            nodes.append({
                "id": user_id,
                "label": user.get("name", user_id),
                "type": "User",
                "properties": {
                    "title": user.get("title"),
                    "risk_score": user.get("risk_score")
                }
            })
            relationships.append({
                "source": alert_id,
                "target": user_id,
                "type": "INVOLVES"
            })

        # Add asset node
        asset = record.get("asset")
        asset_id = _node_id(asset, "asset") if asset else "unknown"
        if asset:
            nodes.append({
                "id": asset_id,
                "label": asset.get("hostname", asset_id),
                "type": "Asset",
                "properties": {
                    "criticality": asset.get("criticality")
                }
            })
            relationships.append({
                "source": alert_id,
                "target": asset_id,
                "type": "DETECTED_ON"
            })

        # Add travel node
        travel = record.get("travel")
        travel_id = _node_id(travel, "travel") if travel else "unknown"
        if travel:
            nodes.append({
                "id": travel_id,
                "label": travel.get("destination", travel_id),
                "type": "TravelContext",
                "properties": {
                    "destination": travel.get("destination")
                }
            })
            relationships.append({
                "source": user_id,
                "target": travel_id,
                "type": "HAS_TRAVEL"
            })

        # Add pattern node
        pattern = record.get("pattern")
        pattern_id = _node_id(pattern, "pattern") if pattern else "unknown"
        if pattern:
            nodes.append({
                "id": pattern_id,
                "label": pattern.get("name", pattern_id),
                "type": "AttackPattern",
                "properties": {
                    "occurrence_count": pattern.get("occurrence_count"),
                    "confidence": pattern.get("confidence")
                }
            })
            relationships.append({
                "source": alert_id,
                "target": pattern_id,
                "type": "MATCHES"
            })

        # Add playbook node
        playbook = record.get("playbook")
        playbook_id = _node_id(playbook, "playbook") if playbook else "unknown"
        if playbook:
            ap = record.get("ap")
            nodes.append({
                "id": playbook_id,
                "label": playbook.get("name", playbook_id),
                "type": "Playbook",
                "properties": {
                    "sla_minutes": playbook.get("sla_minutes")
                }
            })
            if ap:
                relationships.append({
                    "source": _node_id(ap, "ap"),
                    "target": playbook_id,
                    "type": "HANDLED_BY"
                })

        return {
            "nodes": nodes,
            "relationships": relationships
        }

    except Exception as e:
        print(f"[ERROR] Failed to get graph data: {e}")
        return {"nodes": [], "relationships": []}
