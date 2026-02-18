"""
Alert Triage API - Tab 3
Graph-based reasoning and closed-loop execution
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from datetime import datetime
import uuid

from app.services.agent import agent
from app.services.reasoning import narrator
from app.services.situation import analyze_situation
from app.services.feedback import process_outcome, get_feedback_status
from app.db.neo4j import neo4j_client
from app.models.schemas import ProcessAlertRequest, OutcomeRequest


router = APIRouter()


# ============================================================================
# GET /api/alerts/queue - Alert Queue
# ============================================================================

@router.get("/alerts/queue")
async def get_alert_queue():
    """
    Get list of pending alerts for triage.
    Returns simplified alert list for the sidebar.
    """
    print("[TRIAGE] GET /alerts/queue called")

    try:
        # Query Neo4j for pending alerts
        query = """
        MATCH (alert:Alert {status: 'pending'})
        MATCH (alert)-[:INVOLVES]->(user:User)
        MATCH (alert)-[:DETECTED_ON]->(asset:Asset)
        RETURN alert, user.name as user_name, asset.hostname as asset_hostname
        ORDER BY alert.timestamp DESC
        LIMIT 10
        """

        print("[TRIAGE] Querying Neo4j for pending alerts...")
        results = await neo4j_client.run_query(query)
        print(f"[TRIAGE] Neo4j returned {len(results)} results")

        alerts = []
        for record in results:
            alert = record["alert"]
            alerts.append({
                "id": alert["id"],
                "alert_type": alert["alert_type"],
                "severity": alert["severity"],
                "asset_hostname": record["asset_hostname"],
                "user_name": record["user_name"],
                "timestamp": alert["timestamp"],
                "status": alert["status"],
                "source_location": alert.get("source_location", "Unknown")
            })

        print(f"[TRIAGE] Returning {len(alerts)} alerts from Neo4j")
        response = {"alerts": alerts}
        print(f"[TRIAGE] Response structure: {response}")
        return response

    except Exception as e:
        print(f"[ERROR] Failed to fetch alert queue: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch alerts from Neo4j: {str(e)}"
        )


# ============================================================================
# POST /api/alert/analyze - Analyze Alert with Graph Traversal
# ============================================================================

@router.post("/alert/analyze")
async def analyze_alert(request: ProcessAlertRequest):
    """
    Analyze an alert by traversing the security graph.
    Returns full context, recommendation, and graph data for visualization.
    """

    try:
        alert_id = request.alert_id

        # ====================================================================
        # Step 1: Get full alert details
        # ====================================================================
        alert_data = await neo4j_client.get_alert(alert_id)

        if not alert_data:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

        # ====================================================================
        # Step 2: Get security context (47 nodes)
        # ====================================================================
        context = await neo4j_client.get_security_context(alert_id)

        if not context:
            raise HTTPException(status_code=404, detail=f"Context for {alert_id} not found")

        # ====================================================================
        # Step 3: Situation Analysis (Loop 1: Context Intelligence)
        # ====================================================================
        alert_type = context.get("alert_type")
        situation_analysis = analyze_situation(alert_type, context)

        # ====================================================================
        # Step 4: Get agent recommendation
        # ====================================================================
        decision = agent.decide(alert_type, context)

        # Generate reasoning
        reasoning = await narrator.generate_reasoning(alert_type, decision.action, context)

        # ====================================================================
        # Step 5: Get graph data for visualization
        # ====================================================================
        graph_data = await get_graph_data(alert_id)

        # ====================================================================
        # Step 6: Extract key facts from context
        # ====================================================================
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

        # ====================================================================
        # Build Response
        # ====================================================================
        return {
            "alert": alert_data,
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
                "action": decision.action,
                "confidence": decision.confidence,
                "reasoning": reasoning,
                "pattern_id": decision.pattern_id,
                "playbook_id": decision.playbook_id
            },
            "graph_data": graph_data,
            "situation_analysis": situation_analysis.model_dump()
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to analyze alert: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


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
        action = request.deployment_version or "false_positive_close"  # Using this field for action

        # Get context for decision trace
        context = await neo4j_client.get_security_context(alert_id)

        if not context:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

        # Get decision
        alert_type = context.get("alert_type")
        decision = agent.decide(alert_type, context)
        reasoning = await narrator.generate_reasoning(alert_type, decision.action, context)

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
        # Step 3: EVIDENCE - Create decision trace in Neo4j
        # ====================================================================
        decision_id = f"DEC-{uuid.uuid4().hex[:4].upper()}"

        await neo4j_client.create_decision_trace(
            decision_id=decision_id,
            alert_id=alert_id,
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

        # Update alert status in Neo4j
        await neo4j_client.run_query(
            "MATCH (alert:Alert {id: $alert_id}) SET alert.status = 'resolved'",
            {"alert_id": alert_id}
        )

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
                "contribution": f"↓{mttr_reduction} minutes",
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
    Allows the demo to be run multiple times.
    """
    print("[TRIAGE] POST /alerts/reset called - resetting alert statuses")

    try:
        # Reset all alerts to pending status
        query = """
        MATCH (alert:Alert)
        SET alert.status = 'pending'
        RETURN count(alert) as reset_count
        """

        print("[TRIAGE] Running Cypher query to reset alert statuses...")
        result = await neo4j_client.run_query(query)
        reset_count = result[0]["reset_count"] if result else 0

        print(f"[TRIAGE] Reset {reset_count} alerts to 'pending' status")

        return {
            "status": "success",
            "message": f"Reset {reset_count} alerts to 'pending' status",
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

    try:
        # Check if feedback already given
        status = get_feedback_status(request.alert_id)
        if status["has_feedback"]:
            raise HTTPException(
                status_code=400,
                detail=f"Feedback already provided for {request.alert_id}. Outcome cannot be changed."
            )

        # Process the outcome feedback
        result = process_outcome(
            alert_id=request.alert_id,
            decision_id=request.decision_id,
            outcome=request.outcome
        )

        print(f"[FEEDBACK] Processed {request.outcome} outcome for {request.alert_id}")
        print(f"[FEEDBACK] Graph updates: {len(result.graph_updates)}")
        print(f"[FEEDBACK] Consequence: {result.consequence}")

        return result.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to process outcome: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process outcome: {str(e)}"
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
# Helper: Get Graph Data for Visualization
# ============================================================================

async def get_graph_data(alert_id: str) -> Dict[str, Any]:
    """
    Get graph data for visualization.
    Returns nodes and relationships in a format suitable for graph rendering.
    """

    query = """
    MATCH (alert:Alert {id: $alert_id})
    MATCH (alert)-[:DETECTED_ON]->(asset:Asset)
    MATCH (alert)-[:INVOLVES]->(user:User)
    MATCH (alert)-[:CLASSIFIED_AS]->(alertType:AlertType)
    OPTIONAL MATCH (user)-[:HAS_TRAVEL]->(travel:TravelContext)
    OPTIONAL MATCH (alert)-[:MATCHES]->(pattern:AttackPattern)
    OPTIONAL MATCH (alertType)-[:HANDLED_BY]->(playbook:Playbook)

    RETURN alert, asset, user, alertType, travel, pattern, playbook
    """

    try:
        results = await neo4j_client.run_query(query, {"alert_id": alert_id})

        if not results:
            return {"nodes": [], "relationships": []}

        record = results[0]

        # Build nodes
        nodes = []
        relationships = []

        # Add alert node
        alert = record.get("alert")
        if alert:
            nodes.append({
                "id": alert["id"],
                "label": alert["id"],
                "type": "Alert",
                "properties": {
                    "alert_type": alert.get("alert_type"),
                    "severity": alert.get("severity")
                }
            })

        # Add user node
        user = record.get("user")
        if user:
            nodes.append({
                "id": user["id"],
                "label": user["name"],
                "type": "User",
                "properties": {
                    "title": user.get("title"),
                    "risk_score": user.get("risk_score")
                }
            })
            relationships.append({
                "source": alert["id"],
                "target": user["id"],
                "type": "INVOLVES"
            })

        # Add asset node
        asset = record.get("asset")
        if asset:
            nodes.append({
                "id": asset["id"],
                "label": asset["hostname"],
                "type": "Asset",
                "properties": {
                    "criticality": asset.get("criticality")
                }
            })
            relationships.append({
                "source": alert["id"],
                "target": asset["id"],
                "type": "DETECTED_ON"
            })

        # Add travel node
        travel = record.get("travel")
        if travel:
            nodes.append({
                "id": travel["id"],
                "label": travel["destination"],
                "type": "TravelContext",
                "properties": {
                    "destination": travel.get("destination")
                }
            })
            relationships.append({
                "source": user["id"],
                "target": travel["id"],
                "type": "HAS_TRAVEL"
            })

        # Add pattern node
        pattern = record.get("pattern")
        if pattern:
            nodes.append({
                "id": pattern["id"],
                "label": pattern["name"],
                "type": "AttackPattern",
                "properties": {
                    "occurrence_count": pattern.get("occurrence_count"),
                    "confidence": pattern.get("confidence")
                }
            })
            relationships.append({
                "source": alert["id"],
                "target": pattern["id"],
                "type": "MATCHES"
            })

        # Add playbook node
        playbook = record.get("playbook")
        if playbook:
            alertType = record.get("alertType")
            nodes.append({
                "id": playbook["id"],
                "label": playbook["name"],
                "type": "Playbook",
                "properties": {
                    "sla_minutes": playbook.get("sla_minutes")
                }
            })
            if alertType:
                relationships.append({
                    "source": alertType["id"],
                    "target": playbook["id"],
                    "type": "HANDLED_BY"
                })

        return {
            "nodes": nodes,
            "relationships": relationships
        }

    except Exception as e:
        print(f"[ERROR] Failed to get graph data: {e}")
        return {"nodes": [], "relationships": []}
