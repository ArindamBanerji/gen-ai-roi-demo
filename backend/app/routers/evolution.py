"""
Runtime Evolution API - THE KEY DIFFERENTIATOR
Tab 2 endpoints: Deployment registry, eval gates, TRIGGERED_EVOLUTION
"""
import dataclasses

from fastapi import APIRouter, HTTPException, Query
from typing import Any, Optional
from datetime import datetime
import uuid
import time

from app.services.agent import agent, DecisionResult
from app.services.reasoning import narrator
from app.services.situation import analyze_situation
from app.services import evolver
from app.services.event_bus import event_bus, DecisionMade, GraphMutated
from app.services.gae_state import get_learning_state, save_learning_state, get_profile_scorer
from app.db.neo4j import neo4j_client
from app.graph_schema import _S
from app.models.schemas import ProcessAlertRequest
from app.domains.soc.config import SOCDomainConfig, SOC_CATEGORIES
from app.domains.soc.orchestrator import compute_factor_vector
from gae.evolution import (
    get_evolution_summary as get_ledger_evolution_summary,
    get_recent_events as get_ledger_recent_events,
    get_variant_history as get_ledger_variant_history,
)
from gae.scoring import score_alert


router = APIRouter()


# ============================================================================
# GET /api/deployments - Deployment Registry
# ============================================================================

@router.get("/deployments")
async def get_deployments():
    """
    Get deployment registry showing active and canary agent versions.
    This demonstrates A/B testing and gradual rollout.
    """

    # Get decision count from AGE (proxy for learned pattern coverage)
    try:
        _rows = await neo4j_client.run_query(
            "MATCH (d:Decision)-[:DECIDED_ON]->() RETURN count(d) AS n"
        )
        pattern_count = int(_rows[0]["n"]) if _rows else 0
    except Exception:
        pattern_count = 0

    deployments = [
        {
            "agent_name": "soc-copilot",
            "version": "v3.1",
            "status": "active",
            "traffic_pct": 90,
            "auto_close_rate_7d": 73.2,
            "sample_count_7d": 4847,
            "config_preview": "Check travel first, then VPN match, MFA required",
            "pattern_count": pattern_count,
            "deployed_at": "2026-01-15T08:00:00Z"
        },
        {
            "agent_name": "soc-copilot",
            "version": "v3.2",
            "status": "canary",
            "traffic_pct": 10,
            "auto_close_rate_7d": 71.8,
            "sample_count_7d": 253,
            "config_preview": "Full context analysis with device fingerprinting",
            "pattern_count": pattern_count + 3,  # Canary learning slightly ahead
            "deployed_at": "2026-02-01T10:30:00Z"
        }
    ]

    return {"deployments": deployments}


# ============================================================================
# POST /api/alert/process - Process Alert with Evolution
# ============================================================================

@router.post("/alert/process")
async def process_alert(request: ProcessAlertRequest):
    """
    Process an alert through the SOC Copilot agent.
    This is THE KEY FLOW that demonstrates TRIGGERED_EVOLUTION.

    Flow:
    1. Get alert details + security context from graph (47 nodes)
    2. GAE scoring: compute_factor_vector -> score_alert (replaces agent.decide)
    3. LLM generates reasoning (narration)
    4. Evaluate 4 gates (deterministic)
    5. Write Decision node to Neo4j with factor_vector (R4)
    6. Emit DecisionMade + GraphMutated events
    7. Check if evolution should trigger
    8. Create TRIGGERED_EVOLUTION relationship
    9. Agent Evolver (Loop 2: Smarter ACROSS decisions)
    """

    start_time = time.time()

    try:
        # ====================================================================
        # Step 1: Get Alert Data + Security Context
        # ====================================================================

        alert_data = await neo4j_client.get_alert(request.alert_id)

        if not alert_data:
            raise HTTPException(status_code=404, detail=f"Alert {request.alert_id} not found")

        context = await neo4j_client.get_security_context(request.alert_id)

        if not context:
            raise HTTPException(status_code=404, detail=f"Alert {request.alert_id} not found")

        alert_type = context.get("alert_type")

        # ====================================================================
        # Step 1.5: Situation Analysis (Loop 1: Context Intelligence)
        # ====================================================================

        situation_analysis = analyze_situation(alert_type, context)

        # ====================================================================
        # Step 2: GAE Scoring Pipeline (v5.0 ProfileScorer — replaces agent.decide())
        #
        # 2a. Compute factor vector via orchestrator (FactorComputers → Neo4j, one per factor)
        # 2b. ProfileScorer centroid-proximity scoring (L2 kernel, τ=0.1)
        #     P(action|f,cat) = softmax(−‖f−μ‖² / τ)
        # ====================================================================

        print(f"[GAE][TAB2] Computing factor vector for {request.alert_id}...")
        computers = SOCDomainConfig.get_factor_computers()
        f = await compute_factor_vector(alert_data, computers, neo4j_client)

        _scorer = get_profile_scorer()
        if _scorer is None:
            raise HTTPException(status_code=503, detail="ProfileScorer not initialized")
        # CORR-1: resolve alert_type → category via explicit map (not direct equality)
        from app.domains.soc.config import resolve_alert_category, SOCDomainConfig as _SDC
        _cat_name = resolve_alert_category(context.get("alert_type") or "unknown")
        _cat_idx = _SDC().get_category_index(_cat_name)
        _scoring_result = _scorer.score(
            f.flatten(), category_index=_cat_idx
        )

        # Phase 0b gate: scorer outputs A=4; gate overrides to refer_to_analyst
        # when confidence is below CONFIDENCE_THRESHOLD (0.70).
        from app.services.composite_gate import CompositeDiscriminant as _CGD
        selected_action = _scoring_result.action_name
        confidence      = _scoring_result.confidence

        _refer_threshold = _CGD.CATEGORY_CONFIDENCE_THRESHOLDS.get(
            _cat_name, _CGD.CONFIDENCE_THRESHOLD
        )
        if confidence < _refer_threshold:
            selected_action = "refer_to_analyst"
        probs_flat      = _scoring_result.probabilities.tolist()
        fv_list         = f.flatten().tolist()
        tau             = _scorer.tau   # 0.1

        print(f"[GAE][TAB2] action={selected_action} confidence={confidence:.3f} "
              f"f={[round(v, 3) for v in fv_list]}")

        # Bridge DecisionResult — adapts GAE action vocabulary to eval gates + evolution trigger
        bridge = DecisionResult(
            action=selected_action,
            confidence=confidence,
            pattern_id=context.get("pattern_id"),
            playbook_id=context.get("playbook_id"),
        )

        # ====================================================================
        # Step 3: LLM Narration (Generate Reasoning)
        # ====================================================================

        reasoning = await narrator.generate_reasoning(alert_type, selected_action, context)

        # ====================================================================
        # Step 4: Eval Gate (4 Checks)
        # ====================================================================

        # Simulate failure if requested (for demo purposes)
        if request.simulate_failure:
            context["asset_criticality"] = "critical"
            bridge.action = agent.ACTION_AUTO_REMEDIATE

        eval_result = agent.evaluate_gates(bridge, context, reasoning)

        # ====================================================================
        # Step 5: Write Decision Node to Neo4j (R4 — factor_vector stored in graph)
        # ====================================================================

        decision_id = f"DEC-{uuid.uuid4().hex[:4].upper()}"

        await neo4j_client.run_query(
            """
            MATCH (a:Alert {alert_id: $alert_id})
            CREATE (d:Decision {
                decision_id:     $decision_id,
                action:          $action,
                confidence:      $confidence,
                factor_vector:   $fv,
                reasoning:       $reasoning,
                pattern_id:      $pattern_id,
                playbook_id:     $playbook_id,
                nodes_consulted: $nodes_consulted,
                category:        $category,
                timestamp_epoch: $timestamp_epoch,
                outcome:         null
            })
            CREATE (d)-[:DECIDED_ON]->(a)
            """,
            {
                "alert_id":        request.alert_id,
                "decision_id":     decision_id,
                "action":          selected_action,
                "confidence":      confidence,
                "fv":              fv_list,
                "reasoning":       reasoning,
                "pattern_id":      bridge.pattern_id,
                "playbook_id":     bridge.playbook_id,
                "nodes_consulted": context.get("nodes_consulted", 47),
                "category":        _cat_name,
                "timestamp_epoch": int(datetime.utcnow().timestamp() * 1000),
            },
        )
        print(f"[GAE][TAB2] Decision node written: {decision_id} [:DECIDED_ON] {request.alert_id}")

        from app.services.audit import record_decision as _audit_record_evo
        _evo_audit_rec = await _audit_record_evo(
            alert_id=request.alert_id,
            situation_type=situation_analysis.situation_type,
            action_taken=selected_action,
            factors=[c.name for c in computers],
            confidence=confidence,
            kernel_type="unknown",
            noise_zone="unknown",
            conservation_status="unknown",
        )
        _entry_hash_evo = _evo_audit_rec.get("hash", "")
        if _entry_hash_evo:
            await neo4j_client.run_query(
                f"MATCH (d:Decision {{decision_id: {_S(decision_id)}}}) "
                f"SET d.entry_hash = {_S(_entry_hash_evo)}"
            )

        # ====================================================================
        # Step 6: Emit Events (every graph mutation MUST emit events)
        # ====================================================================

        await event_bus.emit(DecisionMade(
            alert_id      = request.alert_id,
            action        = selected_action,
            confidence    = confidence,
            factor_vector = tuple(fv_list),
        ))
        await event_bus.emit(GraphMutated(
            mutation_type     = "decision",
            affected_entities = (request.alert_id,),
        ))

        # ====================================================================
        # Step 7 & 8: Check for TRIGGERED_EVOLUTION (THE KEY DIFFERENTIATOR)
        # ====================================================================

        triggered_evolution: dict[str, Any] = {"occurred": False}

        # Only trigger evolution if gates passed
        if eval_result["overall_passed"]:
            evolution_trigger = agent.maybe_trigger_evolution(bridge, context)

            if evolution_trigger:
                event_type, evolution_details = evolution_trigger

                event_id = f"EVO-{uuid.uuid4().hex[:4].upper()}"

                await neo4j_client.create_evolution_event(
                    event_id=event_id,
                    event_type=event_type,
                    triggered_by=decision_id,
                    before_state=evolution_details["before"],
                    after_state=evolution_details["after"],
                    description=evolution_details["description"],
                    impact=evolution_details["impact"],
                    magnitude=evolution_details["magnitude"]
                )

                triggered_evolution = {
                    "occurred": True,
                    "event_id": event_id,
                    "event_type": event_type,
                    "description": evolution_details["description"],
                    "changes": [
                        {
                            "type": "pattern_confidence",
                            "before": evolution_details["before"],
                            "after": evolution_details["after"]
                        }
                    ]
                }

        # ====================================================================
        # Step 9: Agent Evolver (Loop 2: Smarter ACROSS decisions)
        # ====================================================================

        prompt_variant = evolver.get_prompt_variant(alert_type, category=_cat_name)
        success = eval_result["overall_passed"]
        evolver.record_decision_outcome(
            decision_id,
            prompt_variant,
            success,
            alert_type=alert_type,
            category=_cat_name,
        )
        evolver.check_for_promotion(alert_type)
        prompt_evolution = evolver.get_evolution_summary(alert_type)

        # ====================================================================
        # Build GAE scoring details for response
        # ====================================================================

        max_prob = max(probs_flat)
        sorted_probs = sorted(probs_flat, reverse=True)
        low_confidence = max_prob < 0.25
        ambiguous = len(sorted_probs) >= 2 and (sorted_probs[0] - sorted_probs[1]) < 0.05

        # ====================================================================
        # Build GAE learning state summary (real data for AgentEvolver panel)
        # ====================================================================
        _ls = get_learning_state()
        _w_norms = {
            a: round(float(sum(v * v for v in row) ** 0.5), 4)
            for a, row in zip(_scorer.actions, _ls.W.tolist())
        }

        # ====================================================================
        # Build Response
        # ====================================================================

        execution_time = (time.time() - start_time) * 1000  # ms

        return {
            "alert_id": request.alert_id,
            "routed_to": request.deployment_version,
            "eval_gate": {
                "checks": eval_result["checks"],
                "overall_passed": eval_result["overall_passed"],
                "overall_score": eval_result["overall_score"]
            },
            "execution": {
                "status": "executed" if eval_result["overall_passed"] else "blocked",
                "reason": "Gate check failed" if not eval_result["overall_passed"] else None
            },
            "decision_trace": {
                "id": decision_id,
                "type": selected_action,
                "reasoning": reasoning,
                "confidence": confidence,
                "action_taken": selected_action,
                "nodes_consulted": context.get("nodes_consulted", 47),
                "pattern_id": bridge.pattern_id,
                "playbook_id": bridge.playbook_id
            },
            "gae_scoring": {
                "decision_id":          decision_id,
                "factor_vector":        fv_list,
                "factor_names":         [c.name for c in computers],
                "action_probabilities": dict(zip(_scorer.actions, probs_flat)),
                "softmax_sum":          round(sum(probs_flat), 8),
                "temperature":          _scorer.tau,
                "low_confidence":       low_confidence,
                "ambiguous":            ambiguous,
                "decision_method":      (
                    "ProfileScorer centroid-proximity scoring "
                    "(n_factors x 4 actions x n_categories, "
                    "L2 kernel tau=0.1, EXP-E1 validated)"
                ),
            },
            "gae_summary": {
                "decision_count": _ls.decision_count,  # SOURCE: in-memory LearningState (resets on restart)
                "w_norms":        _w_norms,
                "factor_names":   _ls.factor_names,
                "has_real_data":  _ls.decision_count > 0,  # SOURCE: in-memory LearningState (resets on restart)
            },
            "triggered_evolution": triggered_evolution,
            "execution_time_ms": execution_time,
            "context_preview": {
                "user_name": context.get("user_name"),
                "asset_hostname": context.get("asset_hostname"),
                "travel_destination": context.get("travel_destination"),
                "pattern_count": context.get("pattern_count", 0)
            },
            "situation_analysis": situation_analysis.model_dump(),
            "prompt_evolution": prompt_evolution.model_dump()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


# ============================================================================
# POST /api/alert/process-blocked - Simulate Failed Gate (Full Flow)
# ============================================================================

@router.post("/alert/process-blocked")
async def process_alert_blocked(request: ProcessAlertRequest):
    """
    Process an alert that will fail the eval gate check.
    This demonstrates the safety/governance layer to CISOs.

    Same flow as /api/alert/process, but with one gate failing.
    Shows: Sequential animation -> Failed check -> BLOCKED -> No evolution
    """

    start_time = time.time()

    try:
        # Get security context (same as normal flow)
        context = await neo4j_client.get_security_context(request.alert_id)

        if not context:
            raise HTTPException(status_code=404, detail=f"Alert {request.alert_id} not found")

        alert_type = context.get("alert_type")

        # Situation Analysis (Loop 1)
        situation_analysis = analyze_situation(alert_type, context)

        # Agent decision (rule-based)
        decision = agent.decide(alert_type, context)

        # LLM narration
        reasoning = await narrator.generate_reasoning(alert_type, decision.action, context)

        # Create decision trace (even though it will be blocked)
        decision_id = f"DEC-{uuid.uuid4().hex[:4].upper()}"

        from app.domains.soc.config import resolve_alert_category as _resolve_cat_evo
        _evo_category = _resolve_cat_evo(alert_type) if alert_type else "unknown"
        await neo4j_client.create_decision_trace(
            decision_id=decision_id,
            alert_id=request.alert_id,
            action=decision.action,
            confidence=decision.confidence,
            category=_evo_category,
            reasoning=reasoning,
            pattern_id=decision.pattern_id,
            playbook_id=decision.playbook_id,
            nodes_consulted=context.get("nodes_consulted", 47),
            context_snapshot={
                "user": {
                    "name": context.get("user_name"),
                    "risk_score": context.get("user_risk_score")
                },
                "asset": {
                    "hostname": context.get("asset_hostname"),
                    "criticality": context.get("asset_criticality")
                }
            }
        )

        # Build eval gate with ONE FAILED CHECK
        # Simulate Safe Action check failing
        eval_gate = {
            "checks": [
                {
                    "name": "Faithfulness",
                    "score": 0.93,
                    "threshold": 0.85,
                    "passed": True,
                    "message": "Reasoning accurately reflects context and decision"
                },
                {
                    "name": "Safe Action",
                    "score": 0.41,
                    "threshold": 0.70,
                    "passed": False,
                    "message": "Risk score too high for automated action on this asset"
                },
                {
                    "name": "Playbook Match",
                    "score": 0.96,
                    "threshold": 0.80,
                    "passed": True,
                    "message": "Decision follows approved playbook"
                },
                {
                    "name": "SLA Compliance",
                    "score": 0.94,
                    "threshold": 0.90,
                    "passed": True,
                    "message": "Response time within SLA requirements"
                }
            ],
            "overall_passed": False,
            "overall_score": 0.810,
            "blocked": True
        }

        # Build blocked reason
        blocked_reason = (
            "Action blocked: Safe Action check failed (score: 0.41, threshold: 0.70). "
            "Risk score too high for automated action. Escalated to human reviewer."
        )

        # NO TRIGGERED_EVOLUTION because action was blocked
        triggered_evolution = {
            "occurred": False,
            "reason": "Action blocked by eval gate - no evolution triggered"
        }

        execution_time = (time.time() - start_time) * 1000  # ms

        return {
            "alert_id": request.alert_id,
            "routed_to": request.deployment_version,
            "eval_gate": eval_gate,
            "execution": {
                "status": "blocked",
                "reason": blocked_reason
            },
            "decision_trace": {
                "id": decision_id,
                "type": decision.action,
                "reasoning": reasoning,
                "confidence": decision.confidence,
                "action_taken": "BLOCKED",
                "nodes_consulted": context.get("nodes_consulted", 47),
                "pattern_id": decision.pattern_id,
                "playbook_id": decision.playbook_id
            },
            "triggered_evolution": triggered_evolution,
            "execution_time_ms": execution_time,
            "context_preview": {
                "user_name": context.get("user_name"),
                "asset_hostname": context.get("asset_hostname"),
                "travel_destination": context.get("travel_destination"),
                "pattern_count": context.get("pattern_count", 0)
            },
            "blocked_reason": blocked_reason,
            "situation_analysis": situation_analysis.model_dump()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


# ============================================================================
# POST /api/eval/simulate-failure - Simulate Failed Gate (Demo)
# ============================================================================

@router.post("/eval/simulate-failure")
async def simulate_failure():
    """
    Simulate a failed eval gate for demonstration purposes.
    Shows what happens when Safe Action check fails.
    """

    return {
        "simulated": True,
        "simulated_check": "Safe Action",
        "eval_gate": {
            "checks": [
                {
                    "name": "Faithfulness",
                    "score": 0.92,
                    "threshold": 0.85,
                    "passed": True,
                    "message": "Reasoning matches recommended action"
                },
                {
                    "name": "Safe Action",
                    "score": 0.0,
                    "threshold": 1.0,
                    "passed": False,
                    "message": "Auto-remediate action not allowed on critical asset"
                },
                {
                    "name": "Playbook Match",
                    "score": 0.94,
                    "threshold": 0.80,
                    "passed": True,
                    "message": "Decision follows approved playbook"
                },
                {
                    "name": "SLA Compliance",
                    "score": 0.92,
                    "threshold": 0.90,
                    "passed": True,
                    "message": "Action meets SLA requirements"
                }
            ],
            "overall_passed": False,
            "overall_score": 0.695
        },
        "execution": {
            "status": "blocked",
            "reason": "Safe Action check failed (0.0 < 1.0) - Auto-remediate not allowed on critical assets"
        }
    }


# ============================================================================
# GET /api/evolution/recent - Recent Evolution Events
# ============================================================================

@router.get("/evolution/recent")
async def get_recent_evolution():
    """Get recent evolution events from real Decision graph data."""
    try:
        rows = await neo4j_client.run_query(
            "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
            "RETURN d.decision_id AS did, d.action AS action, "
            "a.alert_id AS aid, d.confidence AS conf, "
            "d.timestamp_epoch AS ts "
            "ORDER BY d.timestamp_epoch DESC LIMIT 10"
        )
        events = []
        for r in rows:
            did = r.get("did") or "DEC-unknown"
            aid = r.get("aid") or "ALT-unknown"
            action = r.get("action") or "unknown"
            conf = r.get("conf")
            ts_epoch = r.get("ts")
            conf_str = f"{float(conf):.0%}" if conf is not None else "?"
            if ts_epoch is not None:
                ts_iso = datetime.utcfromtimestamp(float(ts_epoch)).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )
            else:
                ts_iso = "unknown"
            events.append({
                "id": did,
                "event_type": "decision_recorded",
                "description": f"{did}: {action} on {aid} (conf {conf_str})",
                "timestamp": ts_iso,
                "triggered_by": aid,
            })
        return {"events": events}
    except Exception:
        return {"events": []}


# ============================================================================
# GET /api/evolution/variant-history - AE-04 Variant Lifecycle Timeline
# ============================================================================

@router.get("/evolution/variant-history")
async def get_variant_history(variant_id: str = Query(..., description="Variant id")):
    """Return graph-backed AE lifecycle events for one variant."""
    try:
        events = await get_ledger_variant_history(neo4j_client, variant_id)
        return {"variant_id": variant_id, "events": events, "count": len(events)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        return {"variant_id": variant_id, "events": [], "count": 0}


# ============================================================================
# GET /api/evolution/summary - AE Lifecycle Aggregate Summary
# ============================================================================

@router.get("/evolution/summary")
async def get_evolution_summary():
    """Return aggregate graph-backed AE lifecycle statistics."""
    try:
        return await get_ledger_evolution_summary(neo4j_client)
    except Exception:
        return {
            "variants_generated": 0,
            "variants_promoted": 0,
            "variants_rejected": 0,
            "variants_rolled_back": 0,
            "shadow_batches": 0,
            "shadow_started": 0,
            "by_artifact_type": {},
            "avg_shadow_win_rate": 0.0,
            "total_shadow_decisions": 0,
        }


@router.get("/soc/evolution/rejection-summary")
async def get_soc_rejection_summary():
    """Return SOC AgentEvolver rejection counts and recent failed clauses."""
    try:
        summary = await get_ledger_evolution_summary(neo4j_client)
    except Exception:
        summary = {
            "variants_generated": 0,
            "variants_promoted": 0,
            "variants_rejected": 0,
        }
    try:
        events = await get_ledger_recent_events(neo4j_client, 100)
    except Exception:
        events = []

    rejected = _soc_rejected_variants(events)
    breakdown = {
        "correctness_floor": 0,
        "conservation": 0,
        "variance_stability": 0,
    }
    for item in rejected:
        reason = str(item.get("reason") or "")
        if reason in breakdown:
            breakdown[reason] += 1

    total_rejected = int(summary.get("variants_rejected") or len(rejected) or 0)
    if total_rejected > sum(breakdown.values()):
        breakdown["correctness_floor"] += total_rejected - sum(breakdown.values())

    return {
        "total_tested": int(summary.get("variants_generated") or 0),
        "total_promoted": int(summary.get("variants_promoted") or 0),
        "total_rejected": total_rejected,
        "rejection_breakdown": breakdown,
        "rejected_variants": rejected[:10],
        "provenance": "learned",
    }


# ============================================================================
# GET /api/evolution/recent-events - AE-04 Recent Lifecycle Events
# ============================================================================

@router.get("/evolution/recent-events")
async def get_recent_events(limit: int = Query(20, ge=1, le=100)):
    """Return recent graph-backed AE lifecycle events across variants."""
    try:
        events = await get_ledger_recent_events(neo4j_client, limit)
        return {"events": events, "count": len(events), "limit": limit}
    except Exception:
        return {"events": [], "count": 0, "limit": limit}


# ============================================================================
# GET /api/evolution/weight-history - Weight Matrix Evolution History (F4a)
# ============================================================================

@router.get("/evolution/weight-history")
async def get_weight_history(alert_type: Optional[str] = None):
    """
    Return the in-memory weight matrix evolution history.

    Each entry is a snapshot of all prompt-variant success rates taken
    immediately after a decision outcome was recorded this session.

    Optional query parameter:
        ?alert_type=anomalous_login   -- filter to one alert type

    Response shape:
        {
          "history": [
            {
              "decision_number": 1,
              "timestamp":       "2026-02-27T12:34:56.789000+00:00",
              "alert_type":      "anomalous_login",
              "weights":         {
                "TRAVEL_CONTEXT_v1": 0.71,
                "TRAVEL_CONTEXT_v2": 0.89,
                "PHISHING_RESPONSE_v1": 0.82,
                "PHISHING_RESPONSE_v2": 0.80
              },
              "trigger":         "TRAVEL_CONTEXT_v2",
              "outcome":         true
            },
            ...
          ],
          "total":              N,
          "alert_type_filter":  "anomalous_login" | null
        }

    Returns an empty history list when no decisions have been processed
    in this session (e.g. immediately after a demo reset).
    """
    history = evolver.get_weight_history(alert_type_filter=alert_type)
    print(f"[EVOLUTION] GET /evolution/weight-history -- "
          f"total={len(history)}, filter={alert_type!r}")
    return {
        "history":           history,
        "total":             len(history),
        "alert_type_filter": alert_type,
    }


# ============================================================================
# GET /api/evolution/trust-scores - Asymmetric Trust Tracking (F6a)
# ============================================================================

@router.get("/evolution/trust-scores")
async def get_trust_scores():
    """
    Return per-situation-type trust scores and the full trust update history.

    Trust starts at 0.5 for each situation type.
    Asymmetric deltas:  correct +0.03, incorrect -0.60  (20:1 ratio).
    human_review_required is True when trust drops below 0.3.

    Response shape:
        {
          "trust_scores": {
            "travel_login_anomaly": {
              "trust_score": 0.23,
              "human_review_required": true
            },
            ...
          },
          "history": [
            {
              "decision_number": 10,
              "timestamp":       "...",
              "situation_type":  "travel_login_anomaly",
              "trust_score":     0.17,
              "delta":           -0.6,
              "outcome":         "incorrect"
            },
            ...
          ],
          "total_updates":        12,
          "low_trust_situations": ["travel_login_anomaly"]
        }
    """
    from app.services.feedback import get_all_trust_scores
    result = get_all_trust_scores()
    print(
        f"[EVOLUTION] GET /evolution/trust-scores -- "
        f"total_updates={result['total_updates']}, "
        f"low_trust={result['low_trust_situations']}"
    )
    return result


# ============================================================================
# GET /api/soc/graph-stats - Real Neo4j graph statistics (H7-FIX-2)
# ============================================================================

@router.get("/soc/graph-stats")
async def get_graph_stats():
    """
    Return real Neo4j node, relationship, and Decision node counts.

    Replaces the hardcoded 47 / 127 / 891 values displayed in Tab 2.
    Falls back to zeros with source='unavailable' if Neo4j is unreachable.
    """
    try:
        node_result = await neo4j_client.run_query(
            "MATCH (n) RETURN count(n) AS node_count"
        )
        rel_result = await neo4j_client.run_query(
            "MATCH ()-[r]->() RETURN count(r) AS rel_count"
        )
        dec_result = await neo4j_client.run_query(
            "MATCH (d:Decision) RETURN count(d) AS dec_count"
        )
        return {
            "nodes_traversed": node_result[0]["node_count"] if node_result else 0,
            "relationships_analyzed": rel_result[0]["rel_count"] if rel_result else 0,
            "historical_decisions": dec_result[0]["dec_count"] if dec_result else 0,
            "source": "neo4j",
        }
    except Exception as e:
        return {
            "nodes_traversed": 0,
            "relationships_analyzed": 0,
            "historical_decisions": 0,
            "source": "unavailable",
            "error": str(e),
        }


def _soc_rejected_variants(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rejected: list[dict[str, Any]] = []
    for event in events:
        event_type = str(event.get("event_type") or event.get("type") or "").upper()
        status = str(event.get("status") or "").lower()
        if "REJECT" not in event_type and status != "rejected":
            continue
        reason = _soc_rejection_reason(event)
        rejected.append({
            "variant_id": str(
                event.get("variant_id")
                or event.get("variantId")
                or event.get("id")
                or "unknown"
            ),
            "reason": reason,
            "detail": _soc_rejection_detail(event, reason),
            "tested_at": event.get("timestamp") or event.get("created_at") or event.get("tested_at"),
        })
    return rejected


def _soc_rejection_reason(event: dict[str, Any]) -> str:
    raw = str(
        event.get("reason")
        or event.get("failed_clause")
        or event.get("failedClause")
        or event.get("detail")
        or event.get("description")
        or ""
    ).lower()
    if "conservation" in raw:
        return "conservation"
    if "variance" in raw or "stability" in raw:
        return "variance_stability"
    return "correctness_floor"


def _soc_rejection_detail(event: dict[str, Any], reason: str) -> str:
    detail = event.get("detail") or event.get("description") or event.get("message")
    if isinstance(detail, str) and detail:
        return detail
    if reason == "conservation":
        return "conservation gate blocked promotion"
    if reason == "variance_stability":
        return "variance stability clause failed"
    return "correctness floor clause failed"
