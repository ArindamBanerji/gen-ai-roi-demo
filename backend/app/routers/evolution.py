"""
Runtime Evolution API - THE KEY DIFFERENTIATOR
Tab 2 endpoints: Deployment registry, eval gates, TRIGGERED_EVOLUTION
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime
import uuid
import time

from app.services.agent import agent
from app.services.reasoning import narrator
from app.db.neo4j import neo4j_client
from app.models.schemas import ProcessAlertRequest


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

    # Get pattern count from Neo4j
    try:
        pattern_count = await neo4j_client.get_pattern_count()
    except Exception:
        pattern_count = 127  # Fallback

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
    1. Get security context from graph (47 nodes)
    2. Agent makes decision (rule-based)
    3. LLM generates reasoning (narration)
    4. Evaluate 4 gates (deterministic)
    5. Create decision trace in Neo4j
    6. Check if evolution should trigger
    7. Create TRIGGERED_EVOLUTION relationship
    """

    start_time = time.time()

    try:
        # ====================================================================
        # Step 1: Get Security Context (47 nodes from graph)
        # ====================================================================

        context = await neo4j_client.get_security_context(request.alert_id)

        if not context:
            raise HTTPException(status_code=404, detail=f"Alert {request.alert_id} not found")

        alert_type = context.get("alert_type")

        # ====================================================================
        # Step 2: Agent Decision (Rule-Based)
        # ====================================================================

        decision = agent.decide(alert_type, context)

        # ====================================================================
        # Step 3: LLM Narration (Generate Reasoning)
        # ====================================================================

        reasoning = await narrator.generate_reasoning(alert_type, decision.action, context)

        # ====================================================================
        # Step 4: Eval Gate (4 Checks)
        # ====================================================================

        # Simulate failure if requested (for demo purposes)
        if request.simulate_failure:
            context["asset_criticality"] = "critical"
            decision.action = agent.ACTION_AUTO_REMEDIATE

        eval_result = agent.evaluate_gates(decision, context, reasoning)

        # ====================================================================
        # Step 5: Create Decision Trace in Neo4j
        # ====================================================================

        decision_id = f"DEC-{uuid.uuid4().hex[:4].upper()}"

        await neo4j_client.create_decision_trace(
            decision_id=decision_id,
            alert_id=request.alert_id,
            action=decision.action,
            confidence=decision.confidence,
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

        # ====================================================================
        # Step 6 & 7: Check for TRIGGERED_EVOLUTION (THE KEY DIFFERENTIATOR)
        # ====================================================================

        triggered_evolution = {"occurred": False}

        # Only trigger evolution if gates passed
        if eval_result["overall_passed"]:
            evolution_trigger = agent.maybe_trigger_evolution(decision, context)

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
                "type": decision.action,
                "reasoning": reasoning,
                "confidence": decision.confidence,
                "action_taken": decision.action,
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
            }
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
    Shows: Sequential animation → Failed check → BLOCKED → No evolution
    """

    start_time = time.time()

    try:
        # Get security context (same as normal flow)
        context = await neo4j_client.get_security_context(request.alert_id)

        if not context:
            raise HTTPException(status_code=404, detail=f"Alert {request.alert_id} not found")

        alert_type = context.get("alert_type")

        # Agent decision (rule-based)
        decision = agent.decide(alert_type, context)

        # LLM narration
        reasoning = await narrator.generate_reasoning(alert_type, decision.action, context)

        # Create decision trace (even though it will be blocked)
        decision_id = f"DEC-{uuid.uuid4().hex[:4].upper()}"

        await neo4j_client.create_decision_trace(
            decision_id=decision_id,
            alert_id=request.alert_id,
            action=decision.action,
            confidence=decision.confidence,
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
            "blocked_reason": blocked_reason
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
    """Get recent evolution events for display"""

    try:
        events = await neo4j_client.get_recent_evolution_events(limit=10)
        return {"events": events}
    except Exception as e:
        # Fallback mock data
        return {
            "events": [
                {
                    "id": "EVO-0891",
                    "event_type": "pattern_confidence",
                    "description": "PAT-TRAVEL-001 confidence: 91% → 94% (+3 pts)",
                    "timestamp": "2026-02-06T10:23:00Z",
                    "triggered_by": "DEC-7823"
                },
                {
                    "id": "EVO-0890",
                    "event_type": "threshold_adjustment",
                    "description": "Auto-close threshold for travel alerts: 88% → 90%",
                    "timestamp": "2026-02-05T14:12:00Z",
                    "triggered_by": "DEC-7801"
                },
                {
                    "id": "EVO-0889",
                    "event_type": "pattern_learned",
                    "description": "New pattern identified: PAT-PHISH-Q4-CAMPAIGN",
                    "timestamp": "2026-02-04T09:45:00Z",
                    "triggered_by": "DEC-7789"
                }
            ]
        }
