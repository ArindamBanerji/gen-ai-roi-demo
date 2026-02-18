"""
Pydantic schemas for SOC Copilot Demo
Defines data models for alerts, decisions, contexts, and evolution events.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


# ============================================================================
# Alert Models
# ============================================================================

class Alert(BaseModel):
    """Security alert from SIEM"""
    id: str
    alert_type: str  # anomalous_login, phishing, malware_detection, data_exfiltration
    severity: str
    source_ip: Optional[str] = None
    source_location: Optional[str] = None
    destination_ip: Optional[str] = None
    timestamp: datetime
    description: str
    asset_id: str
    user_id: str
    status: str = "pending"


# ============================================================================
# Request Models
# ============================================================================

class ProcessAlertRequest(BaseModel):
    """Request to process an alert through the agent"""
    alert_id: str
    deployment_version: Optional[str] = "v3.1"
    simulate_failure: bool = False


class OutcomeRequest(BaseModel):
    """Request to report decision outcome (v2.5 - Feedback Loop)"""
    alert_id: str
    decision_id: str
    outcome: Literal["correct", "incorrect"]


# ============================================================================
# Security Context Models
# ============================================================================

class SecurityContext(BaseModel):
    """Context gathered from graph traversal"""
    user_id: str
    user_name: str
    user_title: str
    user_risk_score: float
    asset_id: str
    asset_hostname: str
    asset_criticality: str
    user_traveling: bool = False
    travel_destination: Optional[str] = None
    vpn_matches_location: bool = False
    vpn_provider: Optional[str] = None
    mfa_completed: bool = False
    device_fingerprint_match: bool = False
    known_campaign_signature: bool = False
    pattern_count: int = 0
    pattern_id: Optional[str] = None
    fp_rate: float = 0.0
    nodes_consulted: int = 0


# ============================================================================
# Decision Models
# ============================================================================

class Decision(BaseModel):
    """Agent decision output"""
    action: str  # false_positive_close, auto_remediate, escalate_tier2, escalate_incident
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    pattern_id: Optional[str] = None
    playbook_id: Optional[str] = None
    nodes_consulted: int = 0


class DecisionTrace(BaseModel):
    """Full decision trace with context"""
    decision_id: str
    alert_id: str
    action: str
    confidence: float
    reasoning: str
    pattern_id: Optional[str] = None
    playbook_id: Optional[str] = None
    context: SecurityContext
    timestamp: datetime


# ============================================================================
# Evolution Models
# ============================================================================

class EvolutionEvent(BaseModel):
    """Agent evolution event triggered by decision"""
    id: str
    event_type: str  # pattern_learned, threshold_adjusted, playbook_updated
    triggered_by: str  # decision_id
    before_state: Dict[str, Any]
    after_state: Dict[str, Any]
    description: str
    impact: str  # low, medium, high
    magnitude: float
    timestamp: datetime


class TriggeredEvolution(BaseModel):
    """Evolution triggered by current decision"""
    triggered: bool
    event: Optional[EvolutionEvent] = None
    reason: Optional[str] = None


# ============================================================================
# Eval Gate Models
# ============================================================================

class EvalGateCheck(BaseModel):
    """Single eval gate check result"""
    name: str
    passed: bool
    score: float
    threshold: float
    message: str


class EvalGateResult(BaseModel):
    """Complete eval gate evaluation"""
    passed: bool
    checks: List[EvalGateCheck]
    overall_score: float


# ============================================================================
# Deployment Models
# ============================================================================

class Deployment(BaseModel):
    """Agent deployment version"""
    id: str
    version: str
    status: str  # active, canary, archived
    model_name: str
    deployed_at: datetime
    pattern_count: int
    auto_close_rate: float
    fp_rate: float


# ============================================================================
# Pattern Models
# ============================================================================

class AttackPattern(BaseModel):
    """Learned attack pattern"""
    id: str
    name: str
    occurrence_count: int
    fp_rate: float
    confidence: float
    first_seen: datetime
    last_seen: datetime


# ============================================================================
# Response Models
# ============================================================================

class ProcessAlertResponse(BaseModel):
    """Response from processing an alert"""
    alert: Alert
    decision: Decision
    context: SecurityContext
    eval_gate: EvalGateResult
    triggered_evolution: TriggeredEvolution
    execution_time_ms: float


class CompoundingMetrics(BaseModel):
    """Week-over-week compounding metrics"""
    week: int
    pattern_count: int
    auto_close_rate: float
    avg_confidence: float
    fp_rate: float
    mttr_minutes: float
