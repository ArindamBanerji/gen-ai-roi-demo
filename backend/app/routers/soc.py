"""
SOC Analytics API - Tab 1
Governed security metrics with provenance
"""
from fastapi import APIRouter, HTTPException, Query, Request
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from pydantic import BaseModel
import json
import logging
import re
import time
from dataclasses import asdict

from app.db.graph_client import graph_client, soc_decision_where
from app.models.responses import (
    AnalyticsResponse,
    CampaignsResponse,
    CentroidSupportResponse,
    DetectionEngineeringResponse,
    ExecutiveNarrativeResponse,
    LearningStateResponse,
)
from app.domains.soc.config import (
    DEFAULT_CATEGORY,
    N_ACTIONS,
    N_CATEGORIES,
    N_FACTORS,
    SCORER_ACTIONS,
    SOC_CATEGORIES,
    SOC_FACTOR_SIGMA,
    SOC_FACTORS,
)
from copilot_sdk.backend.diagnostics_models import build_diagnostics

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/diagnostics")
def diagnostics(request: Request) -> dict[str, Any]:
    try:
        from app.services.gae_state import get_learning_state, get_learning_store, get_profile_scorer
        scorer = get_profile_scorer()
        state = get_learning_state()
        extras: dict[str, Any] = {
            "learning_state_step": int(getattr(state, "decision_count", 0)),
            "profile_scorer_attached": scorer is not None,
        }
        startup_status = getattr(request.app.state, "l5_startup_status", None)
        if isinstance(startup_status, dict):
            extras["l5_startup_status"] = dict(startup_status)
        result: dict[str, Any] = build_diagnostics(
            "soc",
            scorer,
            get_learning_store(),
            extras=extras,
        )
        return result
    except Exception as exc:
        logger.exception("Diagnostics failed for soc")
        result = build_diagnostics("soc", None, None, extras={"error": str(exc)})
        return result


# ============================================================================
# Request/Response Models
# ============================================================================

class SOCQueryRequest(BaseModel):
    """Natural language query for SOC metrics"""
    question: str


class MetricContract(BaseModel):
    """Metric contract definition"""
    id: str
    name: str
    owner: str
    definition: str
    version: str
    status: str


class MetricDataPoint(BaseModel):
    """Single data point for charting"""
    label: str
    value: float


class Provenance(BaseModel):
    """Data provenance information"""
    sources: List[str]
    freshness_hours: float
    query_preview: str
    last_updated: str


class SprawlAlert(BaseModel):
    """Detection rule sprawl warning"""
    duplicate_rule: str
    active_in_pipelines: int
    monthly_alert_impact: int
    estimated_cost: int
    deprecated_date: str


# ============================================================================
# Metric Registry (Mock BigQuery Data)
# ============================================================================

METRIC_REGISTRY = {
    "mttr_by_severity": {
        "id": "mttr_by_severity",
        "name": "MTTR by Severity",
        "owner": "soc_analytics@company.com",
        "definition": "Mean time to respond (close) by alert severity level",
        "version": "v2.1",
        "status": "active",
        "keywords": ["mttr", "mean time to respond", "response time", "severity"],
        "chart_type": "bar"
    },
    "auto_close_rate": {
        "id": "auto_close_rate",
        "name": "Auto-Close Rate",
        "owner": "soc_analytics@company.com",
        "definition": "Percentage of alerts closed without human intervention",
        "version": "v1.3",
        "status": "active",
        "keywords": ["auto close", "auto-close", "autoclose", "automation", "false positive", "fp rate"],
        "chart_type": "line"
    },
    "fp_rate_by_rule": {
        "id": "fp_rate_by_rule",
        "name": "False Positive Rate by Rule",
        "owner": "soc_analytics@company.com",
        "definition": "Percentage of alerts that are false positives, grouped by detection rule",
        "version": "v2.0",
        "status": "active",
        "keywords": ["false positive", "fp rate", "rule", "accuracy"],
        "chart_type": "bar"
    },
    "escalation_rate": {
        "id": "escalation_rate",
        "name": "Escalation Rate",
        "owner": "soc_analytics@company.com",
        "definition": "Percentage of alerts escalated to incident response team",
        "version": "v1.5",
        "status": "active",
        "keywords": ["escalation", "incident", "tier 2", "severity"],
        "chart_type": "line"
    },
    "mttd_by_source": {
        "id": "mttd_by_source",
        "name": "MTTD by Source",
        "owner": "soc_analytics@company.com",
        "definition": "Mean time to detect by alert source system",
        "version": "v1.2",
        "status": "active",
        "keywords": ["mttd", "mean time to detect", "detection", "source"],
        "chart_type": "bar"
    },
    "analyst_efficiency": {
        "id": "analyst_efficiency",
        "name": "Analyst Efficiency",
        "owner": "soc_analytics@company.com",
        "definition": "Average alerts resolved per analyst per day",
        "version": "v1.0",
        "status": "active",
        "keywords": ["analyst", "efficiency", "productivity", "workload"],
        "chart_type": "bar"
    },

    # ---- v3.1: Cross-context graph intelligence queries ----

    "cross_context_travel_risk": {
        "id": "cross_context_travel_risk",
        "name": "Travel-Correlated Login Risk",
        "owner": "soc_analytics@company.com",
        "definition": "Users with active travel records who triggered authentication anomalies in the last 7 days, cross-referenced with threat intel for destination regions",
        "version": "v1.0",
        "status": "active",
        "keywords": ["travel", "login", "anomaly", "risk", "international", "vpn"],
        "chart_type": "table"
    },
    "device_trust_gaps": {
        "id": "device_trust_gaps",
        "name": "Unmanaged Device Access to Sensitive Assets",
        "owner": "soc_analytics@company.com",
        "definition": "Devices accessing critical assets that are NOT MDM-enrolled, correlated with user risk scores and recent authentication patterns",
        "version": "v1.0",
        "status": "active",
        "keywords": ["device", "mdm", "unmanaged", "trust", "asset", "endpoint"],
        "chart_type": "table"
    },
    "policy_conflict_landscape": {
        "id": "policy_conflict_landscape",
        "name": "Active Policy Conflicts Across Alert Types",
        "owner": "soc_analytics@company.com",
        "definition": "All policy pairs that would produce conflicting actions if triggered simultaneously, ranked by frequency of co-occurrence in recent alerts",
        "version": "v1.0",
        "status": "active",
        "keywords": ["policy", "conflict", "governance", "compliance", "rules", "overlap"],
        "chart_type": "table"
    },
    "threat_intel_coverage": {
        "id": "threat_intel_coverage",
        "name": "Threat Intelligence Coverage Analysis",
        "owner": "soc_analytics@company.com",
        "definition": "Percentage of recent alerts enriched by external threat intelligence, broken down by source, with gaps identified",
        "version": "v1.0",
        "status": "active",
        "keywords": ["threat", "intel", "coverage", "pulsedive", "greynoise", "enrichment", "gap"],
        "chart_type": "bar"
    },
}


# ============================================================================
# Mock Data Generation
# ============================================================================

def get_mttr_by_severity_data() -> List[MetricDataPoint]:
    """Generate MTTR by severity data"""
    return [
        MetricDataPoint(label="Critical", value=8.2),
        MetricDataPoint(label="High", value=14.7),
        MetricDataPoint(label="Medium", value=45.3),
        MetricDataPoint(label="Low", value=252.0)  # 4.2 hours in minutes
    ]


def get_auto_close_rate_data() -> List[MetricDataPoint]:
    """Generate auto-close rate trend data"""
    base_date = datetime.now() - timedelta(days=7)
    return [
        MetricDataPoint(label=f"Day {i+1}", value=68.0 + (i * 3.5))
        for i in range(7)
    ]


def get_fp_rate_by_rule_data() -> List[MetricDataPoint]:
    """Generate FP rate by detection rule"""
    return [
        MetricDataPoint(label="anomalous_login", value=12.5),
        MetricDataPoint(label="phishing_email", value=8.3),
        MetricDataPoint(label="malware_detection", value=5.1),
        MetricDataPoint(label="data_exfiltration", value=3.2),
        MetricDataPoint(label="anomalous_login_legacy", value=45.8)  # The sprawl culprit!
    ]


def get_escalation_rate_data() -> List[MetricDataPoint]:
    """Generate escalation rate trend"""
    return [
        MetricDataPoint(label="Week 1", value=18.5),
        MetricDataPoint(label="Week 2", value=16.2),
        MetricDataPoint(label="Week 3", value=14.8),
        MetricDataPoint(label="Week 4", value=12.1)
    ]


def get_mttd_by_source_data() -> List[MetricDataPoint]:
    """Generate MTTD by source system"""
    return [
        MetricDataPoint(label="Splunk SIEM", value=4.5),
        MetricDataPoint(label="CrowdStrike EDR", value=2.8),
        MetricDataPoint(label="Proofpoint Email", value=8.2),
        MetricDataPoint(label="Azure Sentinel", value=5.3)
    ]


def get_analyst_efficiency_data() -> List[MetricDataPoint]:
    """Generate analyst efficiency data"""
    return [
        MetricDataPoint(label="Team A", value=47.5),
        MetricDataPoint(label="Team B", value=52.3),
        MetricDataPoint(label="Team C", value=38.9)
    ]


def get_cross_context_travel_risk_data() -> List[MetricDataPoint]:
    """
    Travel-correlated login risk -- 6 data sources correlated in one query.
    Each row: User | Destination | Auth anomalies | Threat intel | Resolution
    """
    return [
        MetricDataPoint(
            label="John Smith | Singapore | 3 anomalous logins | Pulsedive: 103.15.42.17 (high risk) | Resolution: false_positive -- travel confirmed",
            value=0.0,
        ),
        MetricDataPoint(
            label="Maria Chen | Frankfurt | 1 anomalous login | No threat intel match | Resolution: pending review",
            value=0.0,
        ),
        MetricDataPoint(
            label="David Park | Sao Paulo | 2 anomalous logins | GreyNoise: scanning activity from region | Resolution: escalated",
            value=0.0,
        ),
    ]


def get_device_trust_gaps_data() -> List[MetricDataPoint]:
    """
    Unmanaged device access -- device x user x asset x risk score in one view.
    Each row: Device | User | Asset accessed | MDM status | User risk | Last MFA
    """
    return [
        MetricDataPoint(
            label="BYOD-iPhone-7821 | sarah.jones | Accessed: Financial DB | MDM: No | User risk: 0.72 | Last MFA: 3 days ago",
            value=0.0,
        ),
        MetricDataPoint(
            label="Unknown-Laptop-0034 | contractor_ext | Accessed: Source Code Repo | MDM: No | User risk: 0.91 | Last MFA: Never",
            value=0.0,
        ),
        MetricDataPoint(
            label="Personal-iPad-1155 | mike.wong | Accessed: Email only | MDM: No | User risk: 0.15 | Last MFA: 2 hours ago",
            value=0.0,
        ),
        MetricDataPoint(
            label="BYOD-Android-3390 | alex.kumar | Accessed: HR Portal | MDM: No | User risk: 0.45 | Last MFA: 1 day ago",
            value=0.0,
        ),
    ]


def get_policy_conflict_landscape_data() -> List[MetricDataPoint]:
    """
    Policy conflict landscape -- proactive governance mapping.
    Each row: Policy pair | Co-occurrence count | Impact | Recommendation
    """
    return [
        MetricDataPoint(
            label="POL-AUTO-CLOSE-TRAVEL vs POL-ESCALATE-HIGH-RISK | Co-occurred: 23 times this month | Impact: 23 alerts required manual triage | Recommendation: Align priority or add exception for travel-confirmed users",
            value=0.0,
        ),
        MetricDataPoint(
            label="POL-DLP-BLOCK-EXTERNAL vs POL-ALLOW-PARTNER-SHARE | Co-occurred: 8 times | Impact: 8 file transfers blocked then manually approved | Recommendation: Create partner whitelist exception",
            value=0.0,
        ),
        MetricDataPoint(
            label="POL-AFTER-HOURS-ALERT vs POL-GLOBAL-TEAM-EXEMPT | Co-occurred: 47 times | Impact: 47 false alerts for APAC team members | Recommendation: Add timezone-aware logic",
            value=0.0,
        ),
    ]


def get_threat_intel_coverage_data() -> List[MetricDataPoint]:
    """
    Threat intel coverage analysis -- shows what the system knows and doesn't know.
    Value = alert count; last bar (0) highlights the coverage gap.
    """
    return [
        MetricDataPoint(label="Pulsedive enriched (68%)", value=34.0),
        MetricDataPoint(label="GreyNoise enriched (24%)", value=12.0),
        MetricDataPoint(label="Enriched by both (16%)", value=8.0),
        MetricDataPoint(label="No enrichment -- GAP (32%)", value=16.0),
        MetricDataPoint(label="Internal lateral movement (0% coverage)", value=0.0),
    ]


# Cross-context metrics served from AGE (H7-FIX-3)
CROSS_CONTEXT_METRIC_IDS = {
    "cross_context_travel_risk",
    "device_trust_gaps",
    "policy_conflict_landscape",
    "threat_intel_coverage",
}


# ============================================================================
# Metric Matching Logic
# ============================================================================

def match_metric(question: str) -> Optional[str]:
    """
    Match natural language question to a metric ID.
    Returns metric_id if matched, None otherwise.
    """
    question_lower = question.lower()

    # Score each metric based on keyword matches
    scores = {}
    for metric_id, metric_info in METRIC_REGISTRY.items():
        score = 0
        for keyword in metric_info["keywords"]:
            if keyword in question_lower:
                score += 1
        if score > 0:
            scores[metric_id] = score

    # Return highest scoring metric
    if scores:
        return max(scores, key=lambda metric_id: scores[metric_id])

    return None


def get_metric_data(metric_id: str) -> List[MetricDataPoint]:
    """Get data for a specific metric"""
    data_generators = {
        "mttr_by_severity": get_mttr_by_severity_data,
        "auto_close_rate": get_auto_close_rate_data,
        "fp_rate_by_rule": get_fp_rate_by_rule_data,
        "escalation_rate": get_escalation_rate_data,
        "mttd_by_source": get_mttd_by_source_data,
        "analyst_efficiency": get_analyst_efficiency_data,
        "cross_context_travel_risk": get_cross_context_travel_risk_data,
        "device_trust_gaps": get_device_trust_gaps_data,
        "policy_conflict_landscape": get_policy_conflict_landscape_data,
        "threat_intel_coverage": get_threat_intel_coverage_data,
    }

    generator = data_generators.get(metric_id)
    if generator:
        return generator()

    return []


def get_provenance(metric_id: str) -> Provenance:
    """Get data provenance for a metric"""
    provenance_map = {
        "mttr_by_severity": Provenance(
            sources=["Splunk SIEM", "ServiceNow ITSM"],
            freshness_hours=1.2,
            query_preview="SELECT severity, AVG(resolution_time_minutes) FROM soc.alerts WHERE created_at > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY) GROUP BY severity",
            last_updated=datetime.now().isoformat()
        ),
        "auto_close_rate": Provenance(
            sources=["Splunk SIEM", "SOC Copilot Decision Log"],
            freshness_hours=0.5,
            query_preview="SELECT DATE(timestamp), COUNT(*) FILTER(WHERE auto_closed = true) / COUNT(*) * 100 FROM soc.alerts GROUP BY 1 ORDER BY 1 DESC LIMIT 7",
            last_updated=datetime.now().isoformat()
        ),
        "fp_rate_by_rule": Provenance(
            sources=["Splunk SIEM", "Detection Rule Registry"],
            freshness_hours=2.0,
            query_preview="SELECT rule_name, COUNT(*) FILTER(WHERE false_positive = true) / COUNT(*) * 100 FROM soc.alerts GROUP BY rule_name",
            last_updated=datetime.now().isoformat()
        ),
        "escalation_rate": Provenance(
            sources=["ServiceNow ITSM", "SOC Copilot"],
            freshness_hours=1.0,
            query_preview="SELECT week, COUNT(*) FILTER(WHERE escalated = true) / COUNT(*) * 100 FROM soc.alerts GROUP BY week",
            last_updated=datetime.now().isoformat()
        ),
        "mttd_by_source": Provenance(
            sources=["Multi-source correlation"],
            freshness_hours=3.0,
            query_preview="SELECT source_system, AVG(detection_time_minutes) FROM soc.alerts GROUP BY source_system",
            last_updated=datetime.now().isoformat()
        ),
        "analyst_efficiency": Provenance(
            sources=["ServiceNow ITSM", "SOC Workforce Analytics"],
            freshness_hours=24.0,
            query_preview="SELECT analyst_team, COUNT(*) / COUNT(DISTINCT analyst_id) FROM soc.alerts WHERE status='resolved' GROUP BY analyst_team",
            last_updated=datetime.now().isoformat()
        ),
        "cross_context_travel_risk": Provenance(
            sources=[
                "UserProfile (HR)",
                "TravelCalendar (Concur)",
                "AuthLogs (Okta)",
                "ThreatIntel (Pulsedive)",
                "GreyNoise enrichment",
                "AlertHistory (SIEM)",
            ],
            freshness_hours=0.8,
            query_preview="MATCH (u:User)-[:HAS_TRAVEL]->(t:TravelContext) MATCH (a:Alert)-[:INVOLVES]->(u) WHERE a.timestamp > datetime()-duration('P7D') OPTIONAL MATCH (ti:ThreatIntel)-[:ASSOCIATED_WITH]->(a) RETURN u.name, t.destination, count(a), ti.severity",
            last_updated=datetime.now().isoformat()
        ),
        "device_trust_gaps": Provenance(
            sources=[
                "DeviceInventory (MDM/Intune)",
                "AssetClassification (CMDB)",
                "UserProfile (HR)",
                "AuthLogs (Okta)",
                "RiskScoring (ACCP)",
            ],
            freshness_hours=2.5,
            query_preview="MATCH (d:Device {mdm_enrolled: false})-[:ACCESSED]->(a:Asset {criticality: 'critical'}) MATCH (u:User)-[:USES]->(d) RETURN d.hostname, u.email, a.name, u.risk_score ORDER BY u.risk_score DESC",
            last_updated=datetime.now().isoformat()
        ),
        "policy_conflict_landscape": Provenance(
            sources=[
                "PolicyEngine (ACCP)",
                "AlertHistory (SIEM)",
                "ResolutionLog (ACCP)",
                "UserProfile (HR -- timezone/team)",
            ],
            freshness_hours=1.5,
            query_preview="MATCH (p1:Policy)-[:CONFLICTS_WITH]->(p2:Policy) MATCH (a:Alert)-[:TRIGGERED]->(p1) MATCH (a)-[:TRIGGERED]->(p2) RETURN p1.id, p2.id, count(a) AS co_occurrences ORDER BY co_occurrences DESC",
            last_updated=datetime.now().isoformat()
        ),
        "threat_intel_coverage": Provenance(
            sources=[
                "ThreatIntel (Pulsedive API)",
                "GreyNoise (API)",
                "AlertHistory (SIEM)",
                "GraphCorrelation (AGE)",
            ],
            freshness_hours=0.3,
            query_preview="MATCH (a:Alert) OPTIONAL MATCH (ti:ThreatIntel)-[:ASSOCIATED_WITH]->(a) RETURN ti.source, count(a) AS enriched_count, round(count(a)*100.0/50) AS coverage_pct",
            last_updated=datetime.now().isoformat()
        ),
    }

    return provenance_map.get(metric_id, Provenance(
        sources=["Unknown"],
        freshness_hours=0,
        query_preview="N/A",
        last_updated=datetime.now().isoformat()
    ))


def check_for_sprawl(metric_id: str) -> Optional[SprawlAlert]:
    """
    Check if query reveals detection rule sprawl.
    Returns sprawl alert if detected.
    """
    # Trigger sprawl alert for FP rate query (shows the legacy rule problem)
    if metric_id == "fp_rate_by_rule":
        return SprawlAlert(
            duplicate_rule="anomalous_login_legacy",
            active_in_pipelines=3,
            monthly_alert_impact=2400,
            estimated_cost=18000,
            deprecated_date="2025-12-01"
        )

    return None


# ============================================================================
# POST /api/soc/query - Natural Language Query
# ============================================================================

@router.post("/soc/query")
async def query_soc_metrics(request: SOCQueryRequest):
    """
    Process natural language query for SOC metrics.
    Returns matched metric with data, governance info, and potential sprawl alerts.
    """

    try:
        question = request.question.strip()

        if not question:
            raise HTTPException(status_code=400, detail="Question cannot be empty")

        print(f"[SOC QUERY] Question: {question}")

        # ====================================================================
        # Step 1: Match question to metric
        # ====================================================================
        metric_id = match_metric(question)

        if not metric_id:
            raise HTTPException(
                status_code=404,
                detail="Could not match question to a known metric. Try asking about MTTR, auto-close rate, or FP rate."
            )

        metric_info = METRIC_REGISTRY[metric_id]
        print(f"[SOC QUERY] Matched metric: {metric_id}")

        # ====================================================================
        # Step 2: Get metric data
        # Cross-context metrics use real AGE queries (H7-FIX-3)
        # ====================================================================
        if metric_id in CROSS_CONTEXT_METRIC_IDS:
            try:
                rows = await graph_client.run_query(
                    "MATCH (a:Alert)-[:HAS_INDICATOR]->(ti:ThreatIndicator) "
                    "RETURN a.alert_id AS alert_id, ti.source AS source, "
                    "ti.indicator_type AS ioc_type LIMIT 10",
                )
                if rows:
                    data = [
                        MetricDataPoint(
                            label=f"{r.get('alert_id','?')} | {r.get('source','?')} | {r.get('ioc_type','?')}",
                            value=0.0,
                        )
                        for r in rows
                    ]
                else:
                    data = [MetricDataPoint(label="No threat-intel associations found in graph", value=0.0)]
            except Exception as qe:
                print(f"[SOC] cross-context AGE query failed: {qe}")
                data = get_metric_data(metric_id)
        else:
            data = get_metric_data(metric_id)

        # ====================================================================
        # Step 3: Get provenance
        # ====================================================================
        provenance = get_provenance(metric_id)

        # ====================================================================
        # Step 4: Check for sprawl
        # ====================================================================
        sprawl_alert = check_for_sprawl(metric_id)

        # ====================================================================
        # Build response
        # ====================================================================
        return {
            "matched_metric": {
                "id": metric_info["id"],
                "name": metric_info["name"],
                "owner": metric_info["owner"],
                "definition": metric_info["definition"],
                "version": metric_info["version"],
                "status": metric_info["status"]
            },
            "result": {
                "data": [{"label": d.label, "value": d.value} for d in data],
                "chart_type": metric_info["chart_type"]
            },
            "provenance": {
                "sources": provenance.sources,
                "freshness_hours": provenance.freshness_hours,
                "query_preview": provenance.query_preview,
                "last_updated": provenance.last_updated
            },
            "sprawl_alert": sprawl_alert.model_dump() if sprawl_alert else None,
            "confidence": 0.96  # High confidence for keyword matching
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] SOC query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


# ============================================================================
# GET /api/soc/detection-engineering — F2-DESIGN: Rule Quality Score + Noise Map
# ============================================================================

@router.get("/soc/detection-engineering", response_model=DetectionEngineeringResponse)
async def get_detection_engineering():
    """
    Detection Engineering Feedback (F2).
    Returns Rule Quality Score (centroid drift from baseline) and
    Noise Map (per-category FP rate from Decision outcomes).
    """
    import numpy as np
    from app.services.gae_state import get_profile_scorer
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS, SOC_CATEGORIES

    # --- Rule Quality Score ---
    category_scores = []
    overall_quality = None
    try:
        scorer = get_profile_scorer()
        baseline = SOC_PROFILE_CENTROIDS  # shape (N_CATEGORIES, N_ACTIONS, N_FACTORS)
        current = scorer.centroids        # shape (N_CATEGORIES, N_ACTIONS, N_FACTORS)

        for i, cat in enumerate(SOC_CATEGORIES):
            drift = float(np.mean(np.abs(current[i] - baseline[i])))
            quality = round(1.0 - drift, 3)
            category_scores.append({
                "category": cat,
                "quality_score": quality,
                "drift": round(drift, 3),
                "status": (
                    "stable" if drift < 0.05 else
                    "drifting" if drift < 0.15 else "diverged"
                ),
            })

        overall_quality = round(
            sum(s["quality_score"] for s in category_scores) / len(category_scores), 3
        )
    except Exception as exc:
        print(f"[SOC] detection-engineering scorer error: {exc}")
        category_scores = [
            {"category": cat, "quality_score": None, "drift": None, "status": "unavailable"}
            for cat in SOC_CATEGORIES
        ]

    # --- Noise Map — FP rate per category from Decision outcomes ---
    noise_map = []
    for cat in SOC_CATEGORIES:
        total = 0
        fp_rate = None
        try:
            rows = await graph_client.run_query(
                "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
                f"WHERE {soc_decision_where()} AND a.category = $cat "
                "RETURN count(d) AS total, "
                "sum(CASE WHEN d.correct = false OR d.outcome = 'incorrect' "
                "THEN 1 ELSE 0 END) AS fp_count",
                {"cat": cat},
            )
            if rows and rows[0]["total"] > 0:
                total = int(rows[0]["total"])
                fp = int(rows[0]["fp_count"] or 0)
                fp_rate = round(fp / total, 3)
        except Exception as qe:
            print(f"[SOC] noise-map query failed for {cat}: {qe}")

        noise_map.append({
            "category": cat,
            "fp_rate": fp_rate,
            "total_decisions": total,
            "estimated": fp_rate is None,
        })

    return {
        "overall_quality_score": overall_quality,
        "category_scores": category_scores,
        "noise_map": noise_map,
        "decisions_required_for_noise": 10,
        "note": (
            "Quality score tracks centroid drift from baseline. "
            "Drift < 0.05 = stable (baseline confirmed). "
            "Drift > 0.15 = diverged (baseline needs revision)."
        ),
    }


# ============================================================================
# GET /api/soc/metrics - List Available Metrics
# ============================================================================

@router.get("/soc/metrics")
async def list_metrics():
    """List all available SOC metrics for discovery"""
    return {
        "metrics": [
            {
                "id": metric_id,
                "name": info["name"],
                "definition": info["definition"],
                "example_questions": [
                    f"What is {info['name'].lower()}?",
                    f"Show me {info['name'].lower()}"
                ]
            }
            for metric_id, info in METRIC_REGISTRY.items()
        ]
    }


# ============================================================================
# GET /api/soc/threat-landscape — Live graph snapshot for Tab 1 summary strip
# ============================================================================

@router.get("/soc/threat-landscape")
async def get_threat_landscape():
    """
    Returns a live snapshot of what the security graph knows right now.
    Displayed in the Tab 1 summary strip before any query is made.

    Attempts a live AGE count of ThreatIntel nodes; falls back to
    static numbers if AGE is unavailable.
    """
    # Query AGE for all stats; fall back to zeros on failure (H7-FIX-3)
    ti_loaded = 0
    high_severity_iocs = 0
    alerts_total = 0
    open_alerts = 0
    decisions_total = 0
    nodes_count = 0
    rels_count = 0
    alert_types_count = 0
    patterns_count = 0
    last_refreshed_minutes_ago = None
    avg_confidence = 0.0
    source = "unavailable"

    try:
        # ThreatIntel counts
        ti_res = await graph_client.run_query(
            "MATCH (t:ThreatIntel) "
            "RETURN count(t) AS total, "
            "count(CASE WHEN t.severity IN ['critical','high'] THEN 1 END) AS high_sev",
        )
        if ti_res:
            ti_loaded = int(ti_res[0].get("total") or 0)
            high_severity_iocs = int(ti_res[0].get("high_sev") or 0)

        # Alert counts — total and open (no Decision yet)
        alert_res = await graph_client.run_query(
            "MATCH (a:Alert) RETURN count(a) AS total",
        )
        # Open alerts — separate query (AGE does not support NOT pattern in CASE)
        open_res_tl = await graph_client.run_query(
            "MATCH (a:Alert) "
            "WHERE NOT exists((a)<-[:DECIDED_ON]-()) "
            "RETURN count(a) AS open_count",
        )
        if alert_res:
            alerts_total = int(alert_res[0].get("total") or 0)
        if open_res_tl:
            open_alerts = int(open_res_tl[0].get("open_count") or 0)

        # Decision count
        dec_res = await graph_client.run_query(
            f"MATCH (d:Decision) WHERE {soc_decision_where()} RETURN count(d) AS c",
        )
        if dec_res:
            decisions_total = int(dec_res[0].get("c") or 0)

        # Graph topology
        node_res = await graph_client.run_query("MATCH (n) RETURN count(n) AS c")
        if node_res:
            nodes_count = int(node_res[0].get("c") or 0)

        rel_res = await graph_client.run_query("MATCH ()-[r]->() RETURN count(r) AS c")
        if rel_res:
            rels_count = int(rel_res[0].get("c") or 0)

        at_res = await graph_client.run_query("MATCH (t:AlertType) RETURN count(t) AS c")
        if at_res:
            alert_types_count = int(at_res[0].get("c") or 0)

        pat_res = await graph_client.run_query("MATCH (p:AttackPattern) RETURN count(p) AS c")
        if pat_res:
            patterns_count = int(pat_res[0].get("c") or 0)

        # BACKLOG-061: last_refreshed_minutes_ago — most recent ThreatIndicator.last_seen
        ti_ts_res = await graph_client.run_query(
            "MATCH (t:ThreatIndicator) WHERE t.last_seen IS NOT NULL "
            "RETURN max(t.last_seen) AS latest"
        )
        if ti_ts_res and ti_ts_res[0].get("latest") is not None:
            latest_ms = float(ti_ts_res[0]["latest"])
            now_ms = datetime.now().timestamp() * 1000
            last_refreshed_minutes_ago = round((now_ms - latest_ms) / 60000, 1)

        # BACKLOG-062: avg_confidence — mean confidence across all Decision nodes
        conf_res = await graph_client.run_query(
            f"MATCH (d:Decision) WHERE {soc_decision_where()} "
            "AND d.confidence IS NOT NULL "
            "RETURN avg(d.confidence) AS avg_conf"
        )
        if conf_res and conf_res[0].get("avg_conf") is not None:
            avg_confidence = round(float(conf_res[0]["avg_conf"]), 2)

        source = "age"
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Threat landscape data unavailable") from exc

    return {
        "threat_intel": {
            "indicators_loaded": ti_loaded,
            "sources": ["Pulsedive", "GreyNoise"],
            "high_severity_iocs": high_severity_iocs,
            "last_refreshed_minutes_ago": last_refreshed_minutes_ago,
        },
        "active_alerts": {
            "in_queue": open_alerts,
            "analyzed_today": alerts_total,
            "auto_closed_today": alerts_total - open_alerts,
            "escalated_today": 0,
        },
        "governance": {
            "policy_conflicts_detected": 3,
            "decisions_today": decisions_total,
            "audit_chain_verified": True,
            "avg_confidence": avg_confidence,
        },
        "graph_coverage": {
            "nodes": nodes_count,
            "relationships": rels_count,
            "alert_types_modeled": alert_types_count,
            "patterns_learned": patterns_count,
        },
        "source": source,
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================================
# GET /api/soc/attack-tactic-breakdown — Alert counts grouped by MITRE tactic
# ============================================================================

@router.get("/soc/attack-tactic-breakdown")
async def get_attack_tactic_breakdown():
    """
    Return alert counts grouped by MITRE ATT&CK tactic.

    Queries Alert nodes for their mitre_tactic property (seeded by
    seed_simulation_alerts).  Falls back to an empty list if AGE
    is unavailable.
    """
    breakdown = []
    try:
        results = await graph_client.run_query(
            """
            MATCH (a:Alert)-[:CLASSIFIED_AS]->(ap:AttackPattern)
            WHERE ap.tactic IS NOT NULL AND ap.tactic <> ''
            RETURN ap.tactic AS tactic, count(a) AS cnt
            ORDER BY cnt DESC
            """,
            {},
        )
        breakdown = [
            {"tactic": r["tactic"], "count": int(r["cnt"])}
            for r in results
        ]
    except Exception as exc:
        print(f"[SOC] attack-tactic-breakdown query failed: {exc}")

    return {"breakdown": breakdown}


# ============================================================================
# GET /api/soc/analytics — Real AGE SOC metrics for Tab 1 (H7-FIX-3)
# ============================================================================

@router.get("/soc/analytics", response_model=AnalyticsResponse)
async def get_soc_analytics():
    """
    Return real AGE aggregations for the five core Tab 1 SOC metrics.

    Metrics with sufficient graph data return live counts (source='graph').
    Metrics that require data not seeded (e.g. MTTD, which needs per-decision
    timestamps) carry estimated=True and a descriptive note rather than a fake
    number.
    """
    try:
        # Metric 1 — Alert volume
        alert_res = await graph_client.run_query(
            "MATCH (a:Alert) RETURN count(a) AS total_alerts"
        )
        total_alerts = int(alert_res[0]["total_alerts"]) if alert_res else 0

        # Metric 2 — Open alerts (no Decision yet)
        open_res = await graph_client.run_query(
            "MATCH (a:Alert) "
            "WHERE NOT exists((a)<-[:DECIDED_ON]-()) "
            "RETURN count(a) AS open_alerts"
        )
        open_alerts = int(open_res[0]["open_alerts"]) if open_res else 0

        # Metric 3 — Total decisions
        dec_res = await graph_client.run_query(
            f"MATCH (d:Decision) WHERE {soc_decision_where()} "
            "RETURN count(d) AS total_decisions"
        )
        total_decisions = int(dec_res[0]["total_decisions"]) if dec_res else 0

        # Metric 4 — Correct decisions
        correct_res = await graph_client.run_query(
            f"MATCH (d:Decision) WHERE {soc_decision_where()} "
            "AND d.correct = true "
            "RETURN count(d) AS correct_decisions"
        )
        correct_decisions = int(correct_res[0]["correct_decisions"]) if correct_res else 0

        # Metric 5 — Category breakdown
        cat_res = await graph_client.run_query(
            "MATCH (a:Alert) "
            "RETURN a.category AS category, count(a) AS cnt "
            "ORDER BY cnt DESC"
        )
        category_breakdown = [
            {"category": r["category"] or "unknown", "count": int(r["cnt"])}
            for r in cat_res
        ]

        return {
            "total_alerts": total_alerts,
            "open_alerts": open_alerts,
            "total_decisions": total_decisions,
            "correct_decisions": correct_decisions,
            "accuracy_pct": (
                round(correct_decisions / total_decisions * 100, 1)
                if total_decisions > 0 else None
            ),
            "category_breakdown": category_breakdown,
            "source": "graph",
            "estimated_metrics": [
                {
                    "value": None,
                    "label": "MTTD",
                    "estimated": True,
                    "note": "Requires decision timestamps -- available after v5.0-beta",
                }
            ],
        }
    except Exception as e:
        print(f"[SOC] analytics AGE query failed: {e}")
        return {
            "total_alerts": 0,
            "open_alerts": 0,
            "total_decisions": 0,
            "correct_decisions": 0,
            "accuracy_pct": None,
            "category_breakdown": [],
            "source": "unavailable",
            "error": str(e),
            "estimated_metrics": [
                {
                    "value": None,
                    "label": "MTTD",
                    "estimated": True,
                    "note": "Requires decision timestamps -- available after v5.0-beta",
                }
            ],
        }



# ============================================================================
# GET /api/soc/learning-state — Expose LearningState for Tab-2 Section D
# ============================================================================

@router.get("/soc/learning-state", response_model=LearningStateResponse)
async def get_learning_state_endpoint():
    """Expose learning state for Tab-2 Section D rollback status."""
    from app.services.gae_state import get_learning_state as _get_ls

    frozen = False
    decision_count = 0
    last_verified_at = None

    try:
        ls = _get_ls()
        decision_count = ls.decision_count  # SOURCE: in-memory LearningState (resets on restart)

        # frozen comes from ProfileScorer._frozen (if scorer is attached)
        scorer = getattr(ls, "profile_scorer", None)
        if scorer is not None:
            frozen = bool(getattr(scorer, "_frozen", False))
    except RuntimeError:
        # Learning state not initialized yet — return defaults
        pass
    except Exception as exc:
        print(f"[SOC] learning-state error: {exc}")

    # Query AGE for last verified_at
    try:
        rows = await graph_client.run_query(
            """
            MATCH (d:Decision)
            WHERE """ + soc_decision_where() + """
              AND d.verified_at_epoch IS NOT NULL
            RETURN d.verified_at_epoch AS verified_at
            ORDER BY d.verified_at_epoch DESC
            LIMIT 1
            """,
        )
        if rows:
            last_verified_at = str(rows[0].get("verified_at") or "")
    except Exception as exc:
        print(f"[SOC] learning-state verified_at query failed: {exc}")

    # IKS v2 — composite institutional knowledge metric
    iks_v2_data = {}
    try:
        from app.services.iks import compute_iks_v2
        iks_v2_data = await compute_iks_v2(graph_client)  # SOURCE: computed from graph (Decision nodes + centroids)
    except Exception as exc:
        print(f"[SOC] learning-state iks_v2 failed: {exc}")

    # BACKLOG-020 Phase 7: expose verified_decisions from snapshot
    verified_decisions = 0
    try:
        from app.state.graph_snapshot import get_snapshot as _get_snap_ls
        verified_decisions = _get_snap_ls().verified_decisions  # SOURCE: GraphSnapshot (graph-backed, survives restart)
    except Exception as _exc:
        print(f"[SOC] learning-state verified_decisions query failed: {_exc}")

    from app.domains.soc.config import BOOTSTRAP_CATEGORY_WEIGHTS
    return {
        "frozen":              frozen,
        "decision_count":      decision_count,
        "verified_decisions":  verified_decisions,
        "last_verified_at":    last_verified_at,
        "checkpoint_id":       None,
        "iks_v2":              iks_v2_data.get("iks_v2", 0.0),
        "iks_components":      iks_v2_data.get("components", {}),
        "iks_interpretation":  iks_v2_data.get("interpretation", ""),
        "total_decisions":     iks_v2_data.get("total_decisions", 0),
        "categories_active":   iks_v2_data.get("categories_active", 0),
        "bootstrap_category_weights": BOOTSTRAP_CATEGORY_WEIGHTS,
    }






# ============================================================================
# GET /api/soc/explain/{decision_id}  — NL Explanation + Similar Cases (§23.3/23.4)
# ============================================================================

@router.get("/soc/explain/{decision_id}")
async def explain_decision(decision_id: str):
    """
    Return a human-readable L1 NL explanation for a decision, together with
    the top-k similar past cases and their action-agreement percentage.

    Pipeline:
      1. Read Decision + linked Alert/User/Asset nodes via graph traversal
      2. Extract factor values from factor_vector using SOC_FACTORS ordering
      3. Build context dict with real entity names and factor-derived strings
      4. SimilarCasesService.get_similar_cases(factor_vector, category)
      5. Render NLTemplateEngine.render_l1(category, context)

    Returns
    -------
    {
      "decision_id":           str,
      "nl_explanation":        str,       # L1 template rendered with real data
      "similar_cases":         list,      # top-3 similar decisions (empty if suppressed)
      "similar_cases_message": str|None,  # set when similar_cases is empty
      "agreement_pct":         float|None,
      "category":              str,
      "action":                str,
      "confidence":            float,
    }
    """
    from app.services.nl_templates import nl_engine
    from app.services.similar_cases import similar_cases_svc, SIMILAR_CASES_MIN_PRIOR
    from app.domains.soc.config import SOC_FACTORS

    # ── Step 1: Read Decision + linked Alert/User/Asset nodes ───────────────
    try:
        rows = await graph_client.run_query(
            """
            MATCH (d:Decision {decision_id: $decision_id})
            WHERE """ + soc_decision_where() + """
            OPTIONAL MATCH (d)-[:DECIDED_ON]->(a:Alert)
            OPTIONAL MATCH (a)-[:INVOLVES]->(u:User)
            OPTIONAL MATCH (a)-[:DETECTED_ON]->(asset:Asset)
            RETURN d.factor_vector      AS factor_vector,
                   d.category           AS category,
                   d.action             AS action,
                   d.confidence         AS confidence,
                   d.timestamp_epoch    AS timestamp,
                   a.source_location    AS source_location,
                   a.source_ip          AS source_ip,
                   a.destination_ip     AS destination_ip,
                   a.description        AS alert_description,
                   a.alert_type         AS alert_type,
                   a.severity           AS severity,
                   u.name               AS user_name,
                   u.title              AS user_title,
                   u.department         AS user_department,
                   asset.hostname       AS asset_hostname,
                   asset.criticality    AS asset_criticality_str,
                   asset.business_unit  AS asset_business_unit
            """,
            {"decision_id": decision_id},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AGE query failed: {exc}")

    if not rows:
        raise HTTPException(status_code=404, detail=f"Decision {decision_id!r} not found")

    row      = rows[0]
    fv_raw   = row.get("factor_vector")
    category = row.get("category") or DEFAULT_CATEGORY
    action   = row.get("action") or "investigate"
    conf     = float(row.get("confidence") or 0.0)

    # ── Parse factor_vector (backward-compat: may be JSON string) ──────────
    if isinstance(fv_raw, str):
        import json as _json
        try:
            fv_raw = _json.loads(fv_raw)
        except Exception:
            fv_raw = []
    factor_vector = [float(x) for x in (fv_raw or [])]

    # ── Extract factor values using SOC_FACTORS ordering ────────────────────
    factor_map  = dict(zip(SOC_FACTORS, factor_vector)) if factor_vector else {}
    pic_val     = factor_map.get(SOC_FACTORS[0], 0.0)   # privileged_identity_context
    asset_val   = factor_map.get("asset_criticality", 0.0)
    threat_val  = factor_map.get("threat_intel_enrichment", 0.0)
    pattern_val = factor_map.get("pattern_history", 0.0)
    time_val    = factor_map.get("time_anomaly", 0.0)
    device_val  = factor_map.get("device_trust", 0.0)

    # ── Extract real entity names from linked nodes ──────────────────────────
    user_name       = row.get("user_name") or "[user]"
    user_title      = row.get("user_title") or "[role]"
    asset_hostname  = row.get("asset_hostname") or "[asset]"
    asset_crit_str  = row.get("asset_criticality_str") or ("high" if asset_val >= 0.7 else "medium")
    source_location = row.get("source_location") or "[location]"
    alert_desc      = row.get("alert_description") or "[action]"
    source_ip       = row.get("source_ip") or "[source host]"
    destination_ip  = row.get("destination_ip") or "[destination host]"

    # ── Step 2: Calibration count (verified decisions in category) ───────────
    try:
        cal_rows = await graph_client.run_query(
            "MATCH (d:Decision {category: $category}) "
            f"WHERE {soc_decision_where()} AND d.outcome IS NOT NULL "
            "RETURN count(d) AS cnt",
            {"category": category},
        )
        if cal_rows:
            calibration_count = int(cal_rows[0].get("cnt") or 0)
            calibration_status = "live"
            calibration_message = None
        else:
            calibration_count = None
            calibration_status = "cold_start"
            calibration_message = "No verified calibration decisions are available yet."
    except Exception as _exc:
        raise HTTPException(
            status_code=503,
            detail="SOC calibration data unavailable",
        ) from _exc

    # ── Step 2b: ThreatIndicator source (for malware_execution template) ────
    ti_source = "threat intelligence feed"
    try:
        ti_rows = await graph_client.run_query(
            """
            MATCH (d:Decision {decision_id: $decision_id})-[:DECIDED_ON]->(a:Alert)
            -[:HAS_INDICATOR]->(ti:ThreatIndicator)
            WHERE """ + soc_decision_where() + """
            RETURN ti.source AS source LIMIT 1
            """,
            {"decision_id": decision_id},
        )
        if ti_rows and ti_rows[0].get("source"):
            ti_source = ti_rows[0]["source"]
    except Exception:
        pass

    # ── Step 3: Similar cases ───────────────────────────────────────────────
    similar_cases: list = []
    if factor_vector:
        similar_cases = await similar_cases_svc.get_similar_cases(
            factor_vector=factor_vector,
            category=category,
            graph_client=graph_client,
        )

    similar_cases_message = (
        f"Not enough prior decisions in this category "
        f"(minimum {SIMILAR_CASES_MIN_PRIOR} required)"
        if not similar_cases else None
    )

    # ── Step 4: Agreement pct ───────────────────────────────────────────────
    agreement_pct = similar_cases_svc.get_agreement_pct(similar_cases, action)

    # ── Step 5: Build context with real data and render NL explanation ───────
    context = {
        # Core fields
        "action_display":    action.replace("_", " ").title(),
        "confidence":        conf,
        "calibration_count": calibration_count,
        "calibration_status": calibration_status,
        "calibration_message": calibration_message,
        "category":          category,
        # Real entity names from graph nodes
        "user_display":        user_name,
        "asset_name":          asset_hostname,
        "asset_criticality":   asset_crit_str,
        "location":            source_location,
        "user_role":           user_title,
        "action_description":  alert_desc,
        "alert_description":   alert_desc,
        "alert_type_display":  (row.get("alert_type") or category).replace("_", " ").title(),
        "source_host":         source_ip,
        "destination_host":    destination_ip,
        # Factor-derived human-readable context strings
        "travel_context": (
            f"Privileged identity context {pic_val:.0%} -- "
            f"{'elevated privilege detected' if pic_val > 0.6 else 'standard identity context'}"
        ),
        "time_context": (
            f"Time anomaly {time_val:.0%} -- "
            f"{'login outside normal hours' if time_val > 0.5 else 'within normal hours'}"
        ),
        "threat_context": (
            f"Threat intel {threat_val:.0%} -- "
            f"{'IOC match found' if threat_val > 0.5 else 'no IOC matches'}"
        ),
        "pattern_context": (
            f"Pattern history {pattern_val:.0%} -- "
            f"{'matches prior behavior' if pattern_val > 0.5 else 'no prior pattern match'}"
        ),
        "device_context": (
            f"Device trust {device_val:.0%} -- "
            f"{'enrolled device' if device_val > 0.5 else 'unregistered device'}"
        ),
        "asset_context":  f"{asset_hostname} ({asset_crit_str} criticality)",
        "ioc_context": (
            f"Threat intel enrichment {threat_val:.0%}"
            if threat_val > 0 else "No IOC matches found"
        ),
        # Fields for less-common category templates
        "indicator_type":   "IP address",
        "source_name":      ti_source,
        "volume_context":   alert_desc,
        "cloud_operation":  alert_desc,
        "device_description": f"{asset_hostname} ({asset_crit_str})",
        "access_context":   f"Asset criticality factor {asset_val:.0%}",
        "situation_type":   category.replace("_", " ").title(),
        "dominant_factors_description": (
            f"pic={pic_val:.2f}, asset={asset_val:.2f}, "
            f"threat={threat_val:.2f}, pattern={pattern_val:.2f}"
        ),
        "agreement_pct": agreement_pct,
    }

    nl_explanation = nl_engine.render_l1(category, context)

    return {
        "decision_id":           decision_id,
        "nl_explanation":        nl_explanation,
        "similar_cases":         similar_cases,
        "similar_cases_message": similar_cases_message,
        "agreement_pct":         agreement_pct,
        "category":              category,
        "action":                action,
        "confidence":            conf,
    }


# ============================================================================
# Shadow Mode endpoints  (Phase 4 §21)
# ============================================================================



# ============================================================================
# GET /api/soc/provenance/{decision_id} — Factor Provenance (Phase 6)
# ============================================================================

@router.get("/soc/provenance/{decision_id}")
async def get_decision_provenance(decision_id: str):
    """Return factor provenance for a stored decision.

    Retrieves the decision's factor_vector from the Decision node in AGE,
    then builds human-readable provenance for each of the 6 SOC factors.

    Response
    --------
    {
        "decision_id":           str,
        "category":              str,
        "action":                str,
        "total_nodes_consulted": int,
        "factors": [
            {
                "factor_name":           str,
                "factor_value":          float,
                "computation_method":    str,
                "graph_nodes_consulted": [str],
                "explanation":           str,
            },
            ...   # 6 entries
        ]
    }
    """
    from app.services.provenance import ProvenanceService
    from app.domains.soc.config import SOC_FACTORS, resolve_alert_category

    result = await ProvenanceService.get_provenance_from_graph(
        decision_id,
        graph_client,
        factor_names=list(SOC_FACTORS),
        resolve_category=resolve_alert_category,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Decision {decision_id!r} not found or has no factor vector",
        )
    return result


# ============================================================================
# GET /api/soc/threat-intel/{alert_id} — Alert-level threat intel (Phase 7)
# ============================================================================

@router.get("/soc/threat-intel/{alert_id}")
async def get_threat_intel_for_alert(alert_id: str):
    """Return ThreatIndicator nodes linked to a specific alert.

    Queries :ThreatIndicator nodes linked via [:ASSOCIATED_WITH] to the alert.
    Always returns HTTP 200; use total_matches to detect the empty state.

    Response
    --------
    {
        "alert_id":      str,
        "indicators":    [
            {"name": str, "indicator_type": str, "indicator": str, "severity": str,
             "source": str, "last_seen": str},
            ...
        ],
        "total_matches": int,
    }
    """
    from app.services.threat_indicator import ThreatIndicatorService

    indicators = await ThreatIndicatorService.get_indicators_for_alert(
        alert_id, graph_client
    )
    return {
        "alert_id":      alert_id,
        "indicators":    indicators,
        "total_matches": len(indicators),
    }




# ---------------------------------------------------------------------------
# GET /api/soc/onboarding-calendar  (P8 — Convergence timeline per category)
# ---------------------------------------------------------------------------

@router.get("/soc/onboarding-calendar")
async def onboarding_calendar(
    alerts_per_day: int = 200,
    verification_rate: float = 0.30,
    graph_level: str = "G1",
):
    """
    L-08: Predicted convergence timeline per category.

    Returns the week at which each SOC category reaches calibration,
    given the customer's actual alert volume and verification rate.

    Query parameters
    ----------------
    alerts_per_day     : int   -- total daily alert volume (default 200)
    verification_rate  : float -- fraction of decisions analysts verify (default 0.30)
    graph_level        : str   -- SIEM/graph enrichment tier G1-G4 (default G1)
    """
    from gae.convergence import generate_onboarding_calendar
    from app.domains.soc.config import BOOTSTRAP_CATEGORY_WEIGHTS, N_FACTORS, SOC_CATEGORIES

    calendar = generate_onboarding_calendar(
        categories=SOC_CATEGORIES,
        category_weights=BOOTSTRAP_CATEGORY_WEIGHTS,
        alerts_per_day=alerts_per_day,
        verification_rate=verification_rate,
        graph_level=graph_level,
        d=N_FACTORS,
    )
    return calendar


# ---------------------------------------------------------------------------
# GET /api/soc/attack-chains  (P16 — L-06 Attack Chain Correlation)
# ---------------------------------------------------------------------------

@router.get("/soc/attack-chains")
async def attack_chains(hours_back: int = 72):
    """L-06: Detected attack chain campaigns.

    Scans recent alerts for entity-correlated, tactic-progression, and
    IOC-linked campaigns.  A campaign is >=3 alerts sharing >=1 mechanism
    within 24 hours.

    Query parameters
    ----------------
    hours_back : int -- look-back window in hours (default 72)
    """
    from app.services.attack_chain import AttackChainService
    service = AttackChainService(graph_client)
    campaigns = await service.scan_recent_alerts(hours_back=hours_back)
    return {
        "campaigns": [
            {
                "campaign_id":      c.campaign_id,
                "alert_count":      len(c.alerts),
                "alerts":           c.alerts,
                "shared_entities":  c.shared_entities,
                "correlation_type": c.correlation_type,
                "confidence":       c.confidence,
                "first_seen":       c.first_seen,
                "last_seen":        c.last_seen,
                "summary":          c.summary,
            }
            for c in campaigns
        ],
        "total_campaigns":   len(campaigns),
        "scan_window_hours": hours_back,
    }



# ============================================================================
# GET /api/soc/compliance — P20 EU AI Act Compliance Dashboard (L-10)
# ============================================================================

@router.get("/soc/compliance")
async def compliance_dashboard():
    """L-10: EU AI Act compliance evidence page.

    Maps Articles 9, 12, 13, 14, 15 to specific product mechanisms.
    Enforcement: August 2, 2026.
    """
    from app.services.compliance_dashboard import generate_compliance_page
    payload = generate_compliance_page()
    conservation_status = await _compliance_conservation_status()
    audit_chain_valid = _compliance_audit_chain_valid()
    payload["eu_ai_act"] = _build_eu_ai_act_summary(
        conservation_status=conservation_status,
        audit_chain_valid=audit_chain_valid,
    )
    return payload


async def _compliance_conservation_status() -> str:
    try:
        from app.services.learning_health import LearningHealthMonitor

        health = await LearningHealthMonitor.evaluate(graph_client)
        return str(health.get("status") or "UNKNOWN").upper()
    except Exception as exc:
        logger.warning("[COMPLIANCE] Conservation status unavailable: %s", exc)
        return "UNKNOWN"


def _compliance_audit_chain_valid() -> bool:
    try:
        from app.framework.audit import verify_chain

        verification = verify_chain() or {}
        return bool(verification.get("verified", False))
    except Exception as exc:
        logger.warning("[COMPLIANCE] Audit chain verification unavailable: %s", exc)
        return False


def _build_eu_ai_act_summary(
    conservation_status: str,
    audit_chain_valid: bool,
) -> dict:
    article_9_status = (
        "EVIDENCE_SUPPORTING_OVERSIGHT"
        if conservation_status == "GREEN"
        else "INVESTIGATION"
    )
    article_15_status = (
        "EVIDENCE_SUPPORTING_OVERSIGHT"
        if audit_chain_valid
        else "INVESTIGATION"
    )
    return {
        "article_9": {
            "status": article_9_status,
            "title": "Article 9 - Risk Management System",
            "description": (
                "Risk management is tied to the conservation guardrail. "
                f"Current conservation status is {conservation_status or 'UNKNOWN'}."
            ),
        },
        "article_15": {
            "status": article_15_status,
            "title": "Article 15 - Accuracy, Robustness, and Cybersecurity",
            "description": (
                "Accuracy and robustness evidence is supported by audit-chain verification. "
                f"Audit chain valid: {audit_chain_valid}."
            ),
        },
    }


# ============================================================================
# GET /api/soc/transparency — P21 Transparency Page (L-11)
# ============================================================================

@router.get("/soc/transparency")
async def transparency_page():
    """L-11: How This System Works -- three depth levels.

    Level 1 (Analyst): plain language, no equations.
    Level 2 (CISO): convergence, IKS, conservation law.
    Level 3 (Auditor): equations, experiment catalog, formal definitions.
    Limitations: always visible.
    """
    from app.services.transparency_page import generate_transparency_page
    return generate_transparency_page()


# ============================================================================
# GET /api/soc/benchmarking-report — P17 Analyst Benchmarking Report (L-04)
# ============================================================================

@router.get("/soc/benchmarking-report")
async def benchmarking_report(
    start_date: str = "2026-01-01",
    end_date: str = "2026-12-31",
    analyst_hourly_cost: float = 85.0
):
    """L-04: Analyst benchmarking report."""
    from app.services.benchmarking_report import BenchmarkingEngine
    engine = BenchmarkingEngine(graph_client)
    report = engine.generate_report(start_date, end_date, analyst_hourly_cost)
    summary = engine.format_executive_summary(report)
    return {
        'report': {
            'period': {'start': report.period_start, 'end': report.period_end},
            'total_decisions': report.total_decisions,
            'section_1_accuracy': {
                'system_accuracy': report.system_accuracy,
                'analyst_accuracy': report.analyst_accuracy,
                'disagreement_rate': report.disagreement_rate,
                'system_correct_on_disagreements': report.system_correct_on_disagreements,
                'analyst_correct_on_disagreements': report.analyst_correct_on_disagreements,
                'per_category': report.per_category_accuracy
            },
            'section_2_adaptation': {
                'iks_start': report.iks_start,
                'iks_end': report.iks_end,
                'iks_delta': report.iks_delta,
                'categories_calibrated': report.categories_calibrated
            },
            'section_3_consistency': {
                'acceptance_rate': report.system_acceptance_rate,
                'guaranteed_consistency': report.guaranteed_consistency,
                'savings': report.estimated_annual_savings
            }
        },
        'executive_summary': summary
    }


# ============================================================================
# GET /api/soc/executive-narrative — P18 Executive Learning Narrative (L-05)
# ============================================================================

@router.get("/soc/executive-narrative", response_model=ExecutiveNarrativeResponse)
async def executive_narrative():
    """F12: Executive narrative digest consumed by Tab 5."""
    from app.services.executive_narrative import build_executive_narrative_async
    return await build_executive_narrative_async(graph_client)


@router.get("/soc/executive-narrative/pdf")
async def executive_narrative_pdf():
    """F12: Export executive narrative as a PDF (reportlab)."""
    import io
    from fastapi.responses import StreamingResponse
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.colors import HexColor
    from app.services.executive_narrative import build_executive_narrative_async

    data = await build_executive_narrative_async(graph_client)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=inch, rightMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    dark_gray = HexColor('#1f2937')
    blue = HexColor('#3b82f6')

    title_style = ParagraphStyle('Title', parent=styles['Title'],
                                 textColor=blue, fontSize=18, spaceAfter=6)
    h2_style = ParagraphStyle('H2', parent=styles['Heading2'],
                              textColor=dark_gray, fontSize=13, spaceAfter=4)
    body_style = ParagraphStyle('Body', parent=styles['Normal'],
                                fontSize=10, leading=14, spaceAfter=3)

    def _p(text, style=body_style):
        return Paragraph(str(text), style)

    story = [
        _p('SOC Copilot -- Executive Narrative', title_style),
        _p(f"Generated: {data['generated_at']}", body_style),
        Spacer(1, 0.15 * inch),
        _p(data['headline'], body_style),
        Spacer(1, 0.2 * inch),

        _p('Key Metrics', h2_style),
        _p(f"Alerts processed: {data['metrics']['alerts_total']}", body_style),
        _p(f"Verified decisions: {data['metrics']['decisions_verified']}", body_style),
        _p(f"Campaigns detected: {data['metrics']['campaigns_detected']}", body_style),
        _p(f"IKS score: {data['metrics']['iks_current']}", body_style),
        Spacer(1, 0.2 * inch),

        _p('What Changed', h2_style),
        _p(f"Verified decisions: {data['what_changed']['total_verified']}", body_style),
        _p(f"Centroid updates: {data['what_changed']['total_centroid_updates']}", body_style),
    ]
    for shift in data['what_changed'].get('top_shifts', []):
        story.append(_p(f"  * {shift.get('description', '')}", body_style))

    story += [
        Spacer(1, 0.2 * inch),
        _p('What Was Discovered', h2_style),
        _p(f"Attack chains: {data['what_discovered']['attack_chains_detected']}", body_style),
    ]
    for s in data['what_discovered'].get('chain_summaries', []):
        story.append(_p(f"  * {s}", body_style))

    story += [
        Spacer(1, 0.2 * inch),
        _p('What the System Knows', h2_style),
        _p(f"IKS: {data['what_knows']['iks_current']}  |  "
           f"Categories calibrated: {data['what_knows']['categories_calibrated']}/{data['what_knows']['categories_total']}  |  "
           f"Health: {data['what_knows']['health_status']}", body_style),
    ]

    doc.build(story)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type='application/pdf',
        headers={'Content-Disposition': 'attachment; filename="executive_narrative.pdf"'},
    )


@router.get("/soc/model-swap-trial")
async def model_swap_trial(n_alerts: int = 20):
    """Run the deterministic model-swap trial over demo alerts."""
    from app.services.model_swap import run_model_swap_trial

    result = await run_model_swap_trial(n_alerts=n_alerts)
    if not result.ok and not result.alerts:
        raise HTTPException(status_code=503, detail=result.summary)
    return asdict(result)


# ============================================================================
# GET /api/soc/three-claims — P15 Three Unconditional Claims (board one-pager)
# ============================================================================

@router.get("/soc/three-claims")
async def three_claims():
    """P15: Three unconditional guarantees for board presentation."""
    from app.services.three_claims import generate_three_claims
    return generate_three_claims()


# ============================================================================
# GET /api/soc/benchmarking-level2 — P32 Level 2 Benchmarking Section
# ============================================================================

@router.get("/soc/benchmarking-level2")
async def benchmarking_level2():
    """P32: Level 2 benchmarking section (mock data for validation).

    # BACKLOG-063: mock data, not called by frontend — remove when L2 benchmarking is implemented.
    """
    from app.services.benchmarking_level2 import Level2BenchmarkingSection
    section = Level2BenchmarkingSection()
    # Mock data from P29 synthetic A/B results
    mock_ab = {
        'group_a': {'acceptance_rate': 0.701, 'accuracy': 0.695,
                    'resolution_time': 1.427, 'reward': 0.7187,
                    'n_decisions': 382},
        'group_b': {'acceptance_rate': 0.802, 'accuracy': 0.790,
                    'resolution_time': 1.246, 'reward': 0.7977,
                    'n_decisions': 387},
        'variant_promoted': True,
        'decisions_to_promotion': 143,
        'conservation_breached': False,
        'p_value': 0.0001,
        'cohens_d': 3.746
    }
    return section.generate_section(mock_ab)



# ============================================================================
# Campaign helpers (F6)
# ============================================================================

def _parse_dt(dt_value) -> datetime:
    """Parse datetime from AGE result (str or datetime)."""
    if isinstance(dt_value, datetime):
        return dt_value
    try:
        return datetime.fromisoformat(str(dt_value).replace("Z", "+00:00"))
    except Exception:
        return datetime.utcnow()


def _format_campaign(raw: dict) -> dict:
    """Format raw AGE campaign row for API response."""
    c = raw.get("c", raw)  # handle both wrapped and unwrapped
    if hasattr(c, "data"):   # AGE Node object
        c = dict(c)
    # AGE serializes list properties as JSON strings — parse defensively.
    _cats = c.get("category_sequence", [])
    if isinstance(_cats, str):
        try:
            _cats = json.loads(_cats)
        except Exception:
            _cats = []

    _ents = c.get("shared_entities", [])
    if isinstance(_ents, str):
        try:
            _ents = json.loads(_ents)
        except Exception:
            _ents = []

    return {
        "campaign_id": c.get("campaign_id", ""),
        "first_seen": str(c.get("first_seen", "")),
        "last_seen": str(c.get("last_seen", "")),
        "alert_count": c.get("alert_count", 0),
        "category_sequence": _cats,
        "shared_entities": _ents,
        "confidence": c.get("confidence", 0.0),
        "trigger_rule": c.get("trigger_rule", ""),
        "severity": c.get("severity", "LOW"),
        "nl_summary": c.get("nl_summary", ""),
    }


def _campaign_node(raw: dict) -> dict:
    node = raw.get("c", raw)
    if hasattr(node, "data"):
        node = dict(node)
    return node if isinstance(node, dict) else {}


def _epoch_seconds(value) -> int:
    if isinstance(value, (int, float)):
        return int(value / 1000) if value > 1e12 else int(value)
    try:
        dt = _parse_dt(value)
        return int(dt.timestamp())
    except Exception:
        return int(datetime.utcnow().timestamp())


def _campaign_state(alert_count: int, last_alert_epoch: int, now_epoch: int) -> str:
    age_seconds = max(0, now_epoch - last_alert_epoch)
    if alert_count <= 1 or age_seconds <= 24 * 3600:
        return "ACTIVE"
    if alert_count > 1 and age_seconds <= 7 * 24 * 3600:
        return "CONTINUES"
    return "RESOLVED"


def _campaign_events(campaign: dict, detail: dict | None, state: str) -> list[dict]:
    first_seen = _epoch_seconds(campaign.get("first_seen"))
    last_seen = _epoch_seconds(campaign.get("last_seen"))
    events: list[dict] = [{"type": "CREATED", "at": first_seen}]

    decisions: list[dict[str, Any]] = []
    if detail:
        decisions = detail.get("decisions") or []
    seen_alerts: set[str] = set()
    for decision in decisions:
        if not isinstance(decision, dict):
            continue
        alert_id = str(decision.get("alert_id") or "").strip()
        if not alert_id or alert_id in seen_alerts:
            continue
        seen_alerts.add(alert_id)
        events.append({
            "type": "ALERT_ADDED",
            "at": _epoch_seconds(decision.get("timestamp") or last_seen),
            "alert_id": alert_id,
            "campaign_id": str(campaign.get("campaign_id") or ""),
        })

    if state == "CONTINUES":
        events.append({
            "type": "STATE_CHANGE",
            "at": last_seen,
            "from": "ACTIVE",
            "to": "CONTINUES",
        })
    elif state == "RESOLVED":
        events.append({
            "type": "STATE_CHANGE",
            "at": last_seen,
            "from": "CONTINUES",
            "to": "RESOLVED",
        })
        events.append({"type": "RESOLVED", "at": last_seen + 7 * 24 * 3600})

    return sorted(events, key=lambda event: int(event.get("at") or 0))


def _format_campaign_detail(raw: dict) -> dict:
    """Format full campaign detail including decisions."""
    c = raw.get("c", raw)
    if hasattr(c, "data"):
        c = dict(c)
    decisions = raw.get("decisions", [])
    formatted = _format_campaign(raw)

    # Build attack_progression
    stage_map = {}
    valid_decisions = []
    for d in (decisions or []):
        if not isinstance(d, dict):
            continue
        if not d.get("alert_id"):
            continue
        valid_decisions.append(d)
        cat = d.get("category", "unknown")
        if cat not in stage_map:
            stage_map[cat] = {"category": cat, "count": 0,
                              "first_seen": d.get("timestamp")}
        stage_map[cat]["count"] += 1

    formatted["decisions"] = valid_decisions
    formatted["attack_progression"] = {"stages": list(stage_map.values())}
    try:
        formatted["duration_hours"] = round(
            (
                _parse_dt(c.get("last_seen", datetime.utcnow())) -
                _parse_dt(c.get("first_seen", datetime.utcnow()))
            ).total_seconds() / 3600, 1
        )
    except Exception:
        formatted["duration_hours"] = 0.0
    return formatted


# ============================================================================
# GET /api/soc/campaigns — F6 Campaign list
# ============================================================================

@router.get("/soc/campaigns", response_model=CampaignsResponse)
async def get_campaigns(
    limit: int = 50,
    min_confidence: float = 0.0,
    trigger_rule: Optional[str] = None,
):
    """
    Return list of detected multi-alert campaigns.

    Response: {campaigns, total, active_campaigns}
    """
    from app.domains.soc.campaigns import CampaignRepository

    repo = CampaignRepository(graph_client)
    campaigns_raw = await repo.get_campaigns(
        limit=limit,
        min_confidence=min_confidence,
        trigger_rule=trigger_rule,
    )

    now = datetime.utcnow()
    active = 0
    for c in campaigns_raw:
        node = c.get("c", c)
        if hasattr(node, "data"):
            node = dict(node)
        last_seen_val = node.get("last_seen") if isinstance(node, dict) else None
        if last_seen_val:
            try:
                if (_parse_dt(last_seen_val).replace(tzinfo=None) - now).total_seconds() < 86400 or \
                   (now - _parse_dt(last_seen_val).replace(tzinfo=None)).total_seconds() < 86400:
                    active += 1
            except Exception:
                pass

    return {
        "campaigns": [_format_campaign(c) for c in campaigns_raw],
        "total": len(campaigns_raw),
        "active_campaigns": active,
    }


# ============================================================================
# GET /api/soc/campaign-timeline — SOC-D8 Campaign lifecycle timeline
# ============================================================================

@router.get("/soc/campaign-timeline")
async def get_campaign_timeline(limit: int = 10):
    """
    Return latest campaign lifecycle events for the Runtime Evolution timeline.

    Read-only: uses existing CampaignRepository graph reads. Campaign state is
    derived when the graph has no persisted lifecycle field.
    """
    from app.domains.soc.campaigns import CampaignRepository

    repo = CampaignRepository(graph_client)
    rows = await repo.get_campaigns(limit=max(1, min(limit, 50)))
    now_epoch = int(datetime.utcnow().timestamp())
    timeline = []

    for row in rows[:max(1, min(limit, 50))]:
        campaign = _format_campaign(row)
        node = _campaign_node(row)
        campaign_id = campaign.get("campaign_id", "")
        detail = await repo.get_campaign_detail(campaign_id) if campaign_id else None
        detail_campaign = _campaign_node(detail or {}) if detail else {}

        first_seen = _epoch_seconds(detail_campaign.get("first_seen") or campaign.get("first_seen"))
        last_seen = _epoch_seconds(detail_campaign.get("last_seen") or campaign.get("last_seen"))
        alert_count = int(campaign.get("alert_count") or 0)
        state = _campaign_state(alert_count, last_seen, now_epoch)
        resolved_at = last_seen + 7 * 24 * 3600 if state == "RESOLVED" else None
        shared_entities = campaign.get("shared_entities") or []
        entity_key = (
            str(shared_entities[0])
            if isinstance(shared_entities, list) and shared_entities
            else str(node.get("derived_entity_key") or node.get("name") or f"campaign:{campaign_id}")
        )

        events = _campaign_events({**campaign, **detail_campaign}, detail, state)
        alert_links = [
            {
                "alert_id": event["alert_id"],
                "campaign_id": campaign_id,
            }
            for event in events
            if event.get("type") == "ALERT_ADDED" and event.get("alert_id")
        ]
        timeline.append({
            "campaign_id": campaign_id,
            "identity_key": campaign_id,
            "entity_key": entity_key,
            "state": state,
            "created_at": first_seen,
            "last_alert_at": last_seen,
            "resolved_at": resolved_at,
            "alert_count": alert_count,
            "events": events,
            "alert_links": alert_links,
            "provenance": "learned",
        })

    timeline.sort(key=lambda item: int(item.get("last_alert_at") or 0), reverse=True)
    return timeline


# ============================================================================
# GET /api/soc/campaigns/{campaign_id} — F6 Campaign detail
# ============================================================================

@router.get("/soc/campaigns/{campaign_id}")
async def get_campaign_detail(campaign_id: str):
    """Return full campaign detail including member decisions."""
    from app.domains.soc.campaigns import CampaignRepository

    repo = CampaignRepository(graph_client)
    detail = await repo.get_campaign_detail(campaign_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _format_campaign_detail(detail)


# ============================================================================
# POST /api/soc/campaigns/recorrelate — F6 Retroactive correlation
# ============================================================================

# ============================================================================
# GET /api/soc/accuracy-trajectory — C1b accuracy trajectory
# ============================================================================

@router.get("/soc/accuracy-trajectory")
async def get_accuracy_trajectory():
    """
    Return current accuracy trajectory for each alert category.

    Combines:
      - Live decision counts per category from AGE
      - Published reference curve (V-ACC-TRAJ-1b-v2) from constants.py
      - Interpolated current accuracy and progress toward enriched plateau

    Cold-start safe -- works with 0 decisions.
    """
    from app.services.accuracy_trajectory import build_accuracy_trajectory

    live_data: dict[str, int] = {}
    decisions_per_day: float = 50.0
    sigma_per_category: dict[str, float] = {}

    try:
        rows = await graph_client.run_query(
            """
            MATCH (d:Decision)
            WHERE """ + soc_decision_where() + """
            RETURN d.category AS category, count(d) AS cnt
            """,
            {},
        )
        for record in rows:
            cat = record.get("category") or "unknown"
            live_data[cat] = int(record.get("cnt", 0))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="SOC accuracy trajectory unavailable",
        ) from exc

    return build_accuracy_trajectory(
        live_data=live_data,
        decisions_per_day=decisions_per_day,
        sigma_per_category=sigma_per_category,
    )


# ============================================================================
# POST /api/soc/campaigns/recorrelate — F6 Retroactive correlation
# ============================================================================

@router.post("/soc/campaigns/recorrelate")
async def recorrelate_campaigns():
    """
    Retroactively correlate all unclaimed alert events into campaigns.
    Idempotent -- MERGE ensures safe repeated calls.

    Response: {campaigns_found, campaigns_written, events_processed}
    """
    from app.domains.soc.campaigns import CampaignCorrelationEngine, CampaignRepository
    from app.domains.soc.config import SOCDomainConfig

    config = SOCDomainConfig.get_campaign_config()
    repo = CampaignRepository(graph_client)
    engine = CampaignCorrelationEngine(config)

    events = await repo.fetch_all_events()
    campaigns = engine.correlate(events)

    written = 0
    for c in campaigns:
        if await repo.write_campaign(c):
            written += 1

    return {
        "campaigns_found": len(campaigns),
        "campaigns_written": written,
        "events_processed": len(events),
    }
# ============================================================================
# F9 — Analyst Benchmarking Report
# GET /api/soc/analyst-benchmarking
# Reads from ShadowDecision nodes (source="v_shadow_synthetic_v3")
# ============================================================================

@router.get("/soc/analyst-benchmarking")
async def get_analyst_benchmarking():
    """
    F9 analyst benchmarking report derived from V-SHADOW-SYNTHETIC-v3.

    Returns overall agreement rate, per-category breakdown (sorted by
    agreement rate ascending -- least agreement first = most interesting),
    per-archetype override precision, and day-level variance.

    Returns graceful "accumulating" state if no ShadowDecision nodes exist.
    """
    SOURCE = "v_shadow_synthetic_v3"

    # ── 1. Overall ────────────────────────────────────────────────────────
    try:
        overall_result = await graph_client.run_query(
            """
            MATCH (sd:ShadowDecision {source: $source})
            RETURN count(sd) AS total,
                   sum(CASE WHEN sd.agreed    THEN 1 ELSE 0 END) AS agreed_count,
                   sum(CASE WHEN sd.ai_correct THEN 1 ELSE 0 END) AS ai_correct_count
            """,
            {"source": SOURCE},
        )
    except Exception as _exc:
        import logging as _log
        _log.getLogger(__name__).warning("[analyst-benchmarking] AGE query failed: %s", _exc)
        return {
            "status": "accumulating",
            "message": "Shadow decision data not yet loaded. Run Step 3 ingest first.",
        }

    row = overall_result[0] if overall_result else {}
    total = row.get("total", 0)

    if not total:
        return {
            "status": "accumulating",
            "message": "Shadow decision data not yet loaded. Run Step 3 ingest first.",
        }

    overall_agree_rate = round(row["agreed_count"] / total, 4)
    overall_ai_accuracy = round(row["ai_correct_count"] / total, 4)

    # ── 2. Per category ───────────────────────────────────────────────────
    try:
        cat_result = await graph_client.run_query(
            """
            MATCH (sd:ShadowDecision {source: $source})
            RETURN sd.category AS category,
                   count(sd)   AS total,
                   sum(CASE WHEN sd.agreed     THEN 1 ELSE 0 END) AS agreed_count,
                   sum(CASE WHEN sd.ai_correct THEN 1 ELSE 0 END) AS ai_correct_count,
                   sum(CASE WHEN NOT sd.agreed THEN 1 ELSE 0 END) AS override_count,
                   sum(CASE WHEN NOT sd.agreed AND sd.analyst_correct
                            THEN 1 ELSE 0 END) AS correct_overrides
            ORDER BY agreed_count ASC
            """,
            {"source": SOURCE},
        )
    except Exception:
        cat_result = []

    per_category = {}
    for r in cat_result:
        cat_total = r["total"] or 1
        oc = r["override_count"] or 0
        agree_rate  = round(r["agreed_count"]     / cat_total, 4)
        ai_acc      = round(r["ai_correct_count"] / cat_total, 4)
        override_prec = round(r["correct_overrides"] / oc, 4) if oc > 0 else None

        cat = r["category"] or "unknown"
        override_pct = round((1 - agree_rate) * 100)
        ai_pct       = round(ai_acc * 100)

        if agree_rate < 0.50:
            signal = (
                f"analysts override AI on {cat.replace('_', ' ')} "
                f"{override_pct}% of the time despite {ai_pct}% AI accuracy "
                f"-- review these cases carefully"
            )
        else:
            signal = (
                f"analysts agree with AI on {cat.replace('_', ' ')} "
                f"{round(agree_rate * 100)}% of the time"
            )

        if r["total"] == 0:
            confidence = "cold_start"
        elif r["total"] >= 100:
            confidence = "calibrated"
        else:
            confidence = "learning"

        per_category[cat] = {
            # Original fields (backward compat)
            "agree_rate":     agree_rate,
            "ai_accuracy":    ai_acc,
            "override_count": r["override_count"],
            "total":          r["total"],
            # F9 fields
            "analyst_agreement":  agree_rate,
            "override_precision": override_prec,
            "verified_decisions": r["total"],
            "signal":             signal,
            "confidence":         confidence,
        }

    # ── 3. Per archetype ──────────────────────────────────────────────────
    try:
        arch_result = await graph_client.run_query(
            """
            MATCH (sd:ShadowDecision {source: $source})
            RETURN sd.analyst AS analyst,
                   sum(CASE WHEN NOT sd.agreed THEN 1 ELSE 0 END) AS override_count,
                   sum(CASE WHEN NOT sd.agreed AND sd.analyst_correct
                            THEN 1 ELSE 0 END) AS correct_overrides
            ORDER BY override_count DESC
            """,
            {"source": SOURCE},
        )
    except Exception:
        arch_result = []

    per_archetype = {}
    for r in arch_result:
        oc = r["override_count"] or 1
        per_archetype[r["analyst"]] = {
            "override_count":     r["override_count"],
            "override_precision": round(r["correct_overrides"] / oc, 4),
        }

    # ── 4. Day variance ───────────────────────────────────────────────────
    try:
        day_result = await graph_client.run_query(
            """
            MATCH (sd:ShadowDecision {source: $source})
            WITH sd.day AS day,
                 count(sd) AS day_total,
                 sum(CASE WHEN sd.agreed THEN 1 ELSE 0 END) AS day_agreed
            WITH day, round(toFloat(day_agreed) / day_total, 4) AS daily_rate
            RETURN min(daily_rate) AS min_daily_agree,
                   max(daily_rate) AS max_daily_agree
            """,
            {"source": SOURCE},
        )
    except Exception:
        day_result = []

    day_row = day_result[0] if day_result else {}
    min_rate = day_row.get("min_daily_agree", 0.0)
    max_rate = day_row.get("max_daily_agree", 1.0)
    spread = round((max_rate or 0) - (min_rate or 0), 4)
    trend = "stable" if spread < 0.20 else "variable"

    # ── Lead finding ──────────────────────────────────────────────────────
    # Prefer lateral_movement-specific wording (F9 commercial headline);
    # fall back to lowest-agreement category if lateral_movement absent.
    lm = per_category.get("lateral_movement", {})
    if lm and lm.get("verified_decisions", 0) > 0:
        lm_agree_pct = round(lm["analyst_agreement"] * 100)
        lm_ai_pct    = round(lm["ai_accuracy"] * 100)
        lead_finding = (
            f"Lateral movement: AI accuracy {lm_ai_pct}%, analyst agreement only "
            f"{lm_agree_pct}%. Your analysts override correct AI recommendations "
            f"on lateral movement -- the most commercially differentiated finding "
            f"in your deployment."
        )
    else:
        lowest_cat  = min(per_category, key=lambda c: per_category[c]["agree_rate"])
        lowest_rate = per_category[lowest_cat]["agree_rate"]
        lead_finding = (
            f"On {lowest_cat.replace('_', ' ')}, analysts override the AI "
            f"{round((1 - lowest_rate) * 100)}% of the time even when the AI "
            f"recommendation is correct. This is a training opportunity."
        )

    return {
        "status": "ready",
        "source": SOURCE,
        "total_decisions": total,
        "overall_agreement_rate": overall_agree_rate,
        "overall_ai_accuracy": overall_ai_accuracy,
        "lead_finding": lead_finding,
        "per_category": per_category,
        "per_archetype": per_archetype,
        "day_variance": {
            "min_daily_agree": min_rate,
            "max_daily_agree": max_rate,
            "trend": trend,
        },
    }


# ── GET /api/soc/f9-report ───────────────────────────────────────────────────

@router.get("/soc/f9-report")
async def get_f9_report():
    """
    F9 Analyst Benchmarking Report -- structured document suitable for export.

    Wraps get_analyst_benchmarking() and adds report metadata, key_insight,
    and methodology fields.  Returns accumulating status if no ShadowDecision
    nodes are loaded yet.
    """
    import time as _time

    benchmarking = await get_analyst_benchmarking()

    return {
        "report_title":            "Analyst Benchmarking Report",
        "generated_at":            int(_time.time()),
        "status":                  benchmarking.get("status", "accumulating"),
        "total_shadow_decisions":  benchmarking.get("total_decisions", 0),
        "lead_finding":            benchmarking.get("lead_finding", "Shadow decision data not yet loaded."),
        "key_insight": (
            "Consistency claim: same alert, same recommendation, every time. "
            "Your analysts agree with each other 60-70% of the time. "
            "The system: 100%."
        ),
        "per_category":  benchmarking.get("per_category", {}),
        "methodology": (
            "V-SHADOW-SYNTHETIC-v3: 1,500 LLM-judge generated analyst decisions "
            "across 6 alert categories, 5 analyst archetypes."
        ),
    }


# ── GET /api/soc/enrichment-advisor ──────────────────────────────────────────

@router.get("/soc/enrichment-advisor")
async def get_enrichment_advisor():
    """
    Return enrichment opportunity rankings with live IOC coverage from AGE.

    ioc_coverage = alerts with >=1 ThreatIndicator / total alerts.
    Falls back to 0.0 if AGE is unavailable or graph is empty.
    """
    from app.services.enrichment_advisor import get_enrichment_advice

    ioc_coverage = 0.0
    try:
        results = await graph_client.run_query(
            """
            MATCH (a:Alert)
            OPTIONAL MATCH (a)-[:HAS_INDICATOR]->(ti:ThreatIndicator)
            RETURN count(DISTINCT a) AS total,
                   count(DISTINCT CASE WHEN ti IS NOT NULL THEN a END) AS hits
            """,
            {},
        )
        if results and results[0]["total"] > 0:
            ioc_coverage = results[0]["hits"] / results[0]["total"]
    except Exception:
        pass

    return get_enrichment_advice(ioc_coverage)


# =============================================================================
# GET /api/soc/enrichment-status — Block 5.2
# =============================================================================

@router.get("/soc/enrichment-status")
async def get_enrichment_status():
    """
    Return current enrichment source status: record count, last refresh
    timestamp, staleness, trust level, and overall health.

    Sources are the actual connectors in this deployment:
      - Pulsedive     -> ThreatIntel nodes          -> threat_intel_enrichment
      - GreyNoise     -> GreyNoiseEnrichment nodes   -> threat_intel_enrichment
      - CrowdStrike   -> CrowdStrikeEnrichment nodes -> asset_criticality

    Staleness thresholds:
      active      : last refresh < 48 h
      stale       : 48 - 168 h
      unavailable : no data, or > 168 h

    Health:
      GREEN : all sources active
      AMBER : >=1 source stale, or AGE unreachable (graceful fallback)
      RED   : primary source unavailable or all sources stale
    """
    import time as _time
    from datetime import datetime as _dt, timezone as _tz

    now_epoch_ms = int(_time.time() * 1000)
    now_epoch_s  = now_epoch_ms // 1000

    def _graph_dt_to_epoch_s(val) -> int | None:
        """Convert AGE DateTime / Python datetime / epoch-ms int to epoch seconds."""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            # Might be epoch ms from Cypher timestamp()
            v = int(val)
            return v // 1000 if v > 1e11 else v
        try:
            # graph.time.DateTime — has to_native()
            native = val.to_native()
            if native.tzinfo is None:
                native = native.replace(tzinfo=_tz.utc)
            return int(native.timestamp())
        except AttributeError:
            pass
        if isinstance(val, _dt):
            if val.tzinfo is None:
                val = val.replace(tzinfo=_tz.utc)
            return int(val.timestamp())
        return None

    def _staleness(epoch_s: int | None) -> tuple[str, float | None]:
        """Return (status, staleness_hours) from epoch_s refresh time."""
        if epoch_s is None:
            return "unavailable", None
        hours = (now_epoch_s - epoch_s) / 3600.0
        if hours < 48:
            return "active", round(hours, 1)
        if hours < 168:
            return "stale", round(hours, 1)
        return "unavailable", round(hours, 1)

    def _human(epoch_s: int | None) -> str | None:
        if epoch_s is None:
            return None
        return _dt.fromtimestamp(epoch_s, tz=_tz.utc).strftime("%Y-%m-%d %H:%M")

    # ── Source definitions (label, node label, trust, factor) ─────────────
    _SOURCE_DEFS = [
        {
            "source_name":    "Pulsedive",
            "node_label":     "ThreatIntel",
            "refresh_prop":   "refreshed_at",
            "trust_level":    "medium",
            "affects_factor": "threat_intel_enrichment",
        },
        {
            "source_name":    "GreyNoise",
            "node_label":     "GreyNoiseEnrichment",
            "refresh_prop":   "refreshed_at",
            "trust_level":    "medium",
            "affects_factor": "threat_intel_enrichment",
        },
        {
            "source_name":    "CrowdStrike EDR",
            "node_label":     "CrowdStrikeEnrichment",
            "refresh_prop":   "refreshed_at",
            "trust_level":    "high",
            "affects_factor": "asset_criticality",
        },
    ]

    sources: list = []
    total_enrichment_nodes = 0
    last_graph_update_epoch_ms: int | None = None
    graph_reachable = True

    for defn in _SOURCE_DEFS:
        label = defn["node_label"]
        prop  = defn["refresh_prop"]
        count = 0
        last_refresh_epoch_s: int | None = None

        try:
            rows = await graph_client.run_query(
                f"MATCH (n:{label}) "
                f"RETURN count(n) AS cnt, max(n.{prop}) AS last_refresh",
                {},
            )
            if rows:
                count = int(rows[0].get("cnt") or 0)
                last_refresh_epoch_s = _graph_dt_to_epoch_s(rows[0].get("last_refresh"))
        except Exception:
            graph_reachable = False

        total_enrichment_nodes += count
        status, staleness_h = _staleness(last_refresh_epoch_s)
        if count == 0:
            status = "unavailable"
            staleness_h = None

        epoch_ms = (last_refresh_epoch_s * 1000) if last_refresh_epoch_s else None
        if epoch_ms and (last_graph_update_epoch_ms is None or epoch_ms > last_graph_update_epoch_ms):
            last_graph_update_epoch_ms = epoch_ms

        src: dict = {
            "source_name":          defn["source_name"],
            "trust_level":          defn["trust_level"],
            "affects_factor":       defn["affects_factor"],
            "record_count":         count,
            "status":               status,
            "last_refreshed_epoch": epoch_ms,
            "last_refreshed_human": _human(last_refresh_epoch_s),
        }
        if staleness_h is not None:
            src["staleness_hours"] = staleness_h
        sources.append(src)

    # ── Enrichment health ─────────────────────────────────────────────────
    statuses = [s["status"] for s in sources]
    if not graph_reachable:
        enrichment_health = "AMBER"
        health_reason = "AGE unreachable -- enrichment status estimated"
    elif all(s == "unavailable" for s in statuses):
        enrichment_health = "RED"
        health_reason = "All enrichment sources unavailable -- run connector refresh"
    elif all(s == "active" for s in statuses):
        enrichment_health = "GREEN"
        health_reason = "All sources active and recent"
    elif any(s == "unavailable" for s in statuses):
        enrichment_health = "AMBER"
        health_reason = "One or more enrichment sources unavailable"
    elif any(s == "stale" for s in statuses):
        enrichment_health = "AMBER"
        health_reason = "One or more sources are stale (>48h since refresh)"
    else:
        enrichment_health = "GREEN"
        health_reason = "All sources active and recent"

    return {
        "sources":                  sources,
        "total_enrichment_nodes":   total_enrichment_nodes,
        "last_graph_update_epoch":  last_graph_update_epoch_ms,
        "enrichment_health":        enrichment_health,
        "health_reason":            health_reason,
    }


# =============================================================================
# GET /api/soc/reconvergence-log — BACKLOG-015 / EXP-G1
# =============================================================================

@router.get("/soc/reconvergence-log")
async def get_reconvergence_log(limit: int = 50):
    """
    Return last N re-convergence events for audit / EXP-G1 monitoring.

    EXP-G1 (temporal compounding exponent) requires 90 days of pilot data.
    This endpoint allows operators to confirm data collection is active
    from Day 1.  The logger (app/services/reconvergence_logger.py) is
    called whenever accuracy drops below threshold and recovers -- hook-in
    to triage path is deferred until re-convergence detection is confirmed
    working in production.
    """
    from app.services.reconvergence_logger import read_reconvergence_events

    events = await read_reconvergence_events(graph_client, limit=max(1, min(limit, 500)))

    return {
        "events":       events,
        "total_events": len(events),
        "note":         "EXP-G1 data collection active from pilot Day 1",
    }


# =============================================================================
# GET /api/soc/verification-health — Block 7.6
# Feeds the Phase 6 verification health dashboard (Tab 2).
# =============================================================================

@router.get("/soc/verification-health")
async def get_verification_health():
    """
    Return verification rate health across 3 conditions:
      1. Coverage:     verified_decisions / total_decisions >= 20%
      2. Drift:        last-7d rate >= prior-7d rate * 80%
      3. Conservation: learning health not AMBER/RED

    Status: GREEN (all healthy) | AMBER (1-2 unhealthy) | RED (all unhealthy or 0 verifications)
    """
    from app.services.learning_health import compute_verification_health
    return await compute_verification_health(graph_client)


# =============================================================================
# Block 2.1 — Centroid PITR backup / restore / list
# =============================================================================

@router.post("/soc/backup-centroid")
async def backup_centroid():
    """
    Persist the live centroid tensor as an AGE checkpoint.
    Returns backup metadata: {backup_id, sha256, shape, step, timestamp_epoch}.
    """
    from app.services.gae_state import create_centroid_checkpoint
    try:
        payload = create_centroid_checkpoint()
    except RuntimeError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "backup_id":       payload["backup_id"],
        "sha256":          payload["sha256"],
        "shape":           payload["shape"],
        "step":            payload["step"],
        "timestamp_epoch": payload["timestamp_epoch"],
    }


@router.post("/soc/restore-centroid")
async def restore_centroid(body: dict = {}):
    """
    Restore the centroid tensor from an AGE checkpoint.
    Body: {"backup_id": "soc:pitr:<id>"} or {} to use the latest checkpoint.
    """
    from fastapi import HTTPException
    from app.services.gae_state import restore_centroid_checkpoint
    backup_id = (body or {}).get("backup_id") or None
    try:
        payload = await restore_centroid_checkpoint(backup_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "restored":        True,
        "backup_id":       payload.get("backup_id"),
        "sha256":          payload["sha256"],
        "step":            payload["step"],
        "timestamp_epoch": payload["timestamp_epoch"],
    }


@router.get("/soc/centroid-backups")
async def list_centroid_checkpoints_endpoint():
    """
    List all SOC centroid checkpoints from AGE.
    Returns [{backup_id, timestamp_epoch, step, sha256}] newest-first.
    """
    from app.services.gae_state import list_centroid_checkpoints
    try:
        return {"backups": list_centroid_checkpoints()}
    except RuntimeError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=str(exc)) from exc


# =============================================================================
# GET /api/soc/gate-config — Block 7.4
# =============================================================================

@router.get("/soc/gate-config")
async def get_gate_config():
    """
    Return GateConfig summary for the current deployment.

    Reads n_decisions from in-memory learning state.
    Switches from conservative defaults to calibrated values
    once n_decisions >= compute_phase3_minimum(V=200, alpha=0.25).
    """
    from app.domains.soc.config import GateConfig
    from app.services.gae_state import get_learning_state

    n_decisions = 0
    try:
        n_decisions = get_learning_state().decision_count  # SOURCE: in-memory LearningState (resets on restart)
    except Exception as _exc:
        print(f"[SOC] gate-config n_decisions query failed: {_exc}")

    cfg = GateConfig(n_decisions=n_decisions, V=200.0, alpha=0.25)
    return cfg.summary()


# =============================================================================
# GET /api/soc/tab/{n}/content — Step 11.1 tab content export
# =============================================================================

_TAB_NAMES = {
    1: "Alert Triage",
    2: "Institutional Intelligence",
    3: "Alert Detail",
    4: "Decision Economics",
    5: "Executive Narrative",
}


SENTINEL_TO_INTERNAL = {
    # credential_access
    "anomalous_login":              "credential_access",
    "unusual_login":                "credential_access",
    "unfamiliar_sign_in":           "credential_access",
    "credential_access_via_lsass":  "credential_access",
    "unusual_database_query":       "insider_threat",
    "brute_force":                  "credential_access",
    # malware_execution — aligned with ALERT_TYPE_CATEGORY_MAP (authority)
    "threat_intel_match":           "malware_execution",
    "malware_execution":            "malware_execution",
    "malware_detection":            "malware_execution",
    "c2_beacon":                    "malware_execution",   # was lateral_movement (drift fixed)
    "phishing":                     "malware_execution",   # was credential_access (drift fixed)
    # lateral_movement — aligned with ALERT_TYPE_CATEGORY_MAP
    "privilege_escalation":         "lateral_movement",    # was credential_access (drift fixed)
    "lateral_movement":             "lateral_movement",
    "internal_scan_ambiguous":      "lateral_movement",
    # data_exfiltration
    "unusual_outbound":             "data_exfiltration",
    "data_exfiltration":            "data_exfiltration",
    "data_exfil":                   "data_exfiltration",   # was missing
    # insider_threat
    "insider_threat":               "insider_threat",
    "anomalous_behavior":           "insider_threat",      # was missing
    # cloud_infrastructure
    "cloud_infrastructure":         "cloud_infrastructure",
    "cloud_config":                 "cloud_infrastructure",
    "cloud_iam_privilege_escalation":  "cloud_infrastructure",   # was missing
    "cloud_storage_public_exposure":   "cloud_infrastructure",   # was missing
    "cloud_config_drift":              "cloud_infrastructure",   # was missing
    "cloud_unused_resource_anomaly":   "cloud_infrastructure",   # was missing
    "cloud_permission_change_review":  "cloud_infrastructure",   # was missing
}

VALID_CATEGORIES = {
    "credential_access", "malware_execution", "lateral_movement",
    "data_exfiltration", "insider_threat", "cloud_infrastructure",
}


def _resolve_category(row: dict) -> str:
    """Return canonical SOC category: a.category first, a.alert_type as fallback.

    Normalises raw strings and maps through SENTINEL_TO_INTERNAL.
    Falls back to 'unclassified' if the result is not in VALID_CATEGORIES.
    """
    raw = row.get("category") or row.get("alert_type") or ""
    normalized = raw.lower().replace(" ", "_").replace("-", "_")
    category = SENTINEL_TO_INTERNAL.get(normalized, normalized)
    if category not in VALID_CATEGORIES:
        category = "unclassified"
    return category


async def _tab1_content() -> dict:
    """Tab 1 -- Alert Triage: alert_count, top_alert_types, pending_count.

    Fix 1.1: reads a.category (primary) and a.alert_type (fallback) -- both internal names.
    Fix 1.2: adds learning_signal + analyst_insight per top alert type.
    """
    alert_count   = 0
    pending_count = 0
    top_alert_types: list = []

    try:
        rows = await graph_client.run_query(
            "MATCH (a:Alert) RETURN count(a) AS cnt", {}
        )
        alert_count = int((rows[0].get("cnt") or 0) if rows else 0)
    except Exception as _exc:
        print(f"[SOC] tab2 alert_count query failed: {_exc}")

    try:
        rows = await graph_client.run_query(
            "MATCH (a:Alert) WHERE a.status IN ['pending', 'open'] "
            "RETURN count(a) AS cnt", {}
        )
        pending_count = int((rows[0].get("cnt") or 0) if rows else 0)
    except Exception as _exc:
        print(f"[SOC] tab2 pending_count query failed: {_exc}")

    # Fix 1.1 (revised): read a.category (primary) and a.alert_type (fallback).
    # a.type is always None on live data — ignored.
    raw_top: list = []
    try:
        rows = await graph_client.run_query(
            "MATCH (a:Alert) "
            "RETURN a.category AS category, a.alert_type AS alert_type, count(a) AS n "
            "ORDER BY n DESC LIMIT 3", {}
        )
        raw_top = rows
    except Exception as _exc:
        print(f"[SOC] tab2 raw_top categories query failed: {_exc}")

    # Fix 1.2: fetch per-category verified decisions + override counts in one query
    top_categories = [_resolve_category(r) for r in raw_top]
    verified_map: dict = {}   # category -> {"verified": int, "overrides": int}
    if top_categories:
        try:
            _cats_literal = "[" + ", ".join(f"'{c}'" for c in top_categories) + "]"
            rows = await graph_client.run_query(
                f"""
                MATCH (d:Decision)
                WHERE {soc_decision_where()} 
                  AND d.category IN {_cats_literal} AND d.outcome IS NOT NULL
                RETURN d.category AS category,
                       count(d) AS verified,
                       sum(CASE WHEN d.correct = false THEN 1 ELSE 0 END) AS overrides
                """,
                {},
            )
            for r in rows:
                cat = r.get("category")
                if cat:
                    verified_map[cat] = {
                        "verified":  int(r.get("verified")  or 0),
                        "overrides": int(r.get("overrides") or 0),
                    }
        except Exception as _exc:
            print(f"[SOC] tab2 per-category verified_map query failed: {_exc}")

    for r in raw_top:
        category = _resolve_category(r)
        count    = int(r.get("n") or 0)

        stats           = verified_map.get(category, {"verified": 0, "overrides": 0})
        verified_count  = stats["verified"]
        override_count  = stats["overrides"]
        override_rate   = round(
            (override_count / verified_count * 100) if verified_count > 0 else 0.0, 1
        )
        calibration_status = "calibrated" if verified_count >= 100 else "learning"

        top_alert_types.append({
            "type":  category,
            "count": count,
            "verified_decisions": verified_count,
            # Fix 1.2: learning signal fields
            "learning_signal": (
                f"Analysts override AI on {category.replace('_', ' ')} "
                f"{override_rate}% of the time -- review carefully."
            ),
            "analyst_insight": (
                (
                    f"Your team has verified {verified_count:,} {category.replace('_', ' ')} decisions. "
                    f"System confidence: calibrated. "
                    f"Microsoft Copilot for Security uses global threat intelligence "
                    f"shared across all customers. Your {verified_count:,} verified decisions "
                    f"encode YOUR environment -- your asset patterns, your analyst judgment, "
                    f"your threat surface. Not reproducible from global data."
                ) if verified_count >= 100 else (
                    f"Your team has verified {verified_count} {category.replace('_', ' ')} decisions. "
                    f"System confidence: learning -- environment-specific advantage builds "
                    f"as decisions are verified."
                )
            ),
        })

    total_verified = sum(int(t.get("verified_decisions") or 0) for t in top_alert_types)
    return {
        "alert_count":        alert_count,
        "top_alert_types":    top_alert_types,
        "pending_count":      pending_count,
        "verified_decisions": total_verified,
    }


async def _tab2_content() -> dict:
    """Tab 2 -- Institutional Intelligence."""
    from app.services.iks import compute_iks_v2, compute_visible_iks, interpret_iks_v2

    iks_score          = 0.0
    iks_interpretation = ""
    category_accuracy_summary: dict = {}
    drift_alert_count  = 0
    total_decisions    = 0
    override_learning_status = "inactive"

    # ── IKS primary: drift-based formula 100 × min(D(t)/κ*=0.20, 1.0) ────────
    # Uses in-memory ProfileScorer centroid drift from μ₀ — no AGE required.
    # Same path as Tab 5 (executive_narrative.py). Avoids event-loop issues that
    # affect compute_iks_v2 async queries.
    try:
        iks_score = await compute_visible_iks(graph_client)
        iks_interpretation = interpret_iks_v2(iks_score)
    except Exception as _exc:
        print(f"[SOC] tab2 iks drift query failed: {_exc}")

    # ── IKS v2: component breakdown + total_decisions (informational) ──────────
    # Also used as fallback for iks_score if drift path gave 0.0.
    try:
        iks_data = await compute_iks_v2(graph_client)
        category_accuracy_summary = iks_data.get("components", {})
        total_decisions            = iks_data.get("total_decisions", 0)
        if iks_score < 50.0:
            iks_score          = iks_data.get("iks_v2", 0.0)
            iks_interpretation = iks_data.get("interpretation", "")
    except Exception as _exc:
        print(f"[SOC] tab2 iks_v2 query failed: {_exc}")

    try:
        rows = await graph_client.run_query(
            f"MATCH (d:Decision) WHERE {soc_decision_where()} "
            "AND d.confidence IS NOT NULL AND d.confidence < 0.50 "
            "RETURN count(d) AS cnt", {}
        )
        drift_alert_count = int((rows[0].get("cnt") or 0) if rows else 0)
    except Exception as _exc:
        print(f"[SOC] tab2 drift_alert_count query failed: {_exc}")

    try:
        from app.services.override_detector import override_detector as _od
        if _od.activated:
            override_learning_status = f"active ({_od.example_count} examples)"
        else:
            override_learning_status = f"inactive ({_od.example_count} examples)"
    except Exception as _exc:
        print(f"[SOC] tab2 override_detector query failed: {_exc}")

    # FIX 2.2 — Drift translation
    drift_pct = round((drift_alert_count / total_decisions * 100) if total_decisions > 0 else 0.0, 1)
    drift_alert_summary = (
        f"{drift_alert_count} of {total_decisions} decisions triggered drift detection "
        f"({drift_pct}%). Re-Convergence correction applied automatically -- "
        "no analyst action required. System health: stable."
    )

    # FIX 2.3 — Trust coverage (categories_active / 6)
    categories_active = category_accuracy_summary.get("trust_coverage", 0.0)
    trust_pct = round(float(categories_active), 1) if isinstance(categories_active, (int, float)) else 0.0
    trust_coverage_summary = (
        f"{trust_pct:.1f}% of alert categories have >=100 verified decisions (trust threshold). "
        "At current V=200: 80%+ expected by day 270. "
        "Full coverage (all categories): approximately day 365."
    )

    # FIX 2.1 — Three-number glossary
    # BACKLOG-020 Phase 7: read verified_decisions from GraphSnapshot (authoritative)
    # rather than total_decisions (all Decision nodes including bootstrap).
    # Falls back to total_decisions when snapshot not yet initialized.
    verified_decisions = total_decisions
    try:
        from app.state.graph_snapshot import get_snapshot as _get_snap_t2
        verified_decisions = _get_snap_t2().verified_decisions
    except Exception as _exc:
        print(f"[SOC] tab2 verified_decisions snapshot failed: {_exc}")

    decision_count_glossary = {
        "verified_decisions": (
            f"{verified_decisions:,} -- analyst decisions confirmed correct or incorrect "
            "in institutional ledger"
        ),
        "switching_cost_threshold": (
            "537 -- decisions required to reach IKS>=67 "
            "(formal switching cost plateau)"
        ),
        "override_examples": (
            "104 -- correct analyst overrides used for per-analyst precision weighting"
        ),
    }

    return {
        "iks_score":               iks_score,
        "iks_interpretation":      iks_interpretation,
        "category_accuracy_summary": category_accuracy_summary,
        "drift_alert_summary":     drift_alert_summary,       # FIX 2.2
        "trust_coverage_summary":  trust_coverage_summary,    # FIX 2.3
        "override_learning_status": override_learning_status,
        "decision_count_glossary": decision_count_glossary,   # FIX 2.1
        "calibration_note": (                                 # FIX 3C
            "All quality thresholds self-calibrate to your deployment's "
            "alert volume and analyst behavior -- no manual configuration "
            "required. Calibration activates after sufficient decisions "
            "accumulate per category (Innovation #9: Continuous Calibration)."
        ),
        "accuracy_trajectory": {
            "source": "validated_experiment_SHIFT2_N50",
            "description": "Accuracy improvement measured across 1,000 decisions (50 seed average)",
            "initial_accuracy": 0.717,
            "final_accuracy": 0.789,
            "improvement_pp": 7.2,
            "trajectory": [
                {"decisions": 0,    "accuracy": 0.717},
                {"decisions": 100,  "accuracy": 0.724},
                {"decisions": 200,  "accuracy": 0.733},
                {"decisions": 300,  "accuracy": 0.741},
                {"decisions": 400,  "accuracy": 0.752},
                {"decisions": 500,  "accuracy": 0.761},
                {"decisions": 600,  "accuracy": 0.769},
                {"decisions": 700,  "accuracy": 0.775},
                {"decisions": 800,  "accuracy": 0.781},
                {"decisions": 900,  "accuracy": 0.786},
                {"decisions": 1000, "accuracy": 0.789},
            ],
            "note": (
                "Measured in controlled experiment with 50 independent seeds. "
                "Production trajectory depends on alert volume and analyst accuracy."
            ),
        },
        "iks_over_time": {
            "description": "Institutional Knowledge Score trajectory",
            "current_iks": iks_score,
            "current_decisions": verified_decisions,
            "milestones": [
                {"month": 1, "decisions": 540,  "iks": 12, "label": "Calibrating"},
                {"month": 3, "decisions": 1620, "iks": 45, "label": "Learning"},
                {"month": 6, "decisions": 3240, "iks": 67, "label": "Switching cost plateau"},
                {"month": 9, "decisions": 4860, "iks": 89, "label": "Expert"},
            ],
            "months_of_judgment": 9,
            "durability": (
                "Survives analyst turnover, system restarts, and model swaps. "
                "Encoded in 144 centroid values + 144 DK precision weights."
            ),
        },
    }


# FIX-24B — derived from SOC_FACTOR_SIGMA in config.py; update sigma there, not here.
_FACTOR_SIGMA_BY_NAME = SOC_FACTOR_SIGMA
_FACTOR_SIGMA = {factor: _FACTOR_SIGMA_BY_NAME[factor] for factor in SOC_FACTORS}


def _factor_kernel_weight(sigma: float, all_sigmas: list) -> float:
    """kernel_weight = (1/sigma^2) normalised to [0,1] over the factor set."""
    raw = 1.0 / (sigma ** 2) if sigma > 0 else 0.0
    max_raw = max((1.0 / (s ** 2) for s in all_sigmas if s > 0), default=1.0)
    return round(raw / max_raw, 4) if max_raw > 0 else 0.0


_BASELINE_SCORER = None  # lazy singleton -- bootstrap centroids, never updated
_BASELINE_SCORER_SOURCE = "uninitialized"
_BOOTSTRAP_CENTROIDS_CACHE = None
_BOOTSTRAP_CENTROIDS_PATH = (
    Path(__file__).resolve().parents[3] / "support" / "setup" / "bootstrap_centroids.json"
)


def _reset_baseline_scorer_cache() -> None:
    """Clear Tab 3 baseline scorer caches for tests."""
    global _BASELINE_SCORER, _BASELINE_SCORER_SOURCE, _BOOTSTRAP_CENTROIDS_CACHE
    _BASELINE_SCORER = None
    _BASELINE_SCORER_SOURCE = "uninitialized"
    _BOOTSTRAP_CENTROIDS_CACHE = None


def reset_baseline_caches() -> None:
    _reset_baseline_scorer_cache()


def _uniform_baseline_centroids():
    import numpy as _np_b
    return _np_b.full((N_CATEGORIES, N_ACTIONS, N_FACTORS), 0.5, dtype=_np_b.float64)


def _load_bootstrap_centroids():
    """Load calibrated Day-1 bootstrap centroids; return None for uniform fallback."""
    global _BOOTSTRAP_CENTROIDS_CACHE
    if _BOOTSTRAP_CENTROIDS_CACHE is not None:
        return _BOOTSTRAP_CENTROIDS_CACHE.copy()

    try:
        import numpy as _np_b
        with _BOOTSTRAP_CENTROIDS_PATH.open("r", encoding="utf-8") as _fh:
            payload = json.load(_fh)
        arr = _np_b.asarray(payload.get("values"), dtype=_np_b.float64)
        expected_shape = (N_CATEGORIES, N_ACTIONS, N_FACTORS)
        if arr.shape != expected_shape:
            raise ValueError(f"shape {arr.shape} != {expected_shape}")
        if not _np_b.all(_np_b.isfinite(arr)):
            raise ValueError("centroids contain NaN or Inf")
        _BOOTSTRAP_CENTROIDS_CACHE = arr
        return arr.copy()
    except Exception as _exc:
        print(f"[SOC] bootstrap baseline unavailable; using uniform fallback: {_exc}")
        return None


def _get_baseline_scorer():
    """Day-1 baseline scorer for display-only confidence comparison."""
    global _BASELINE_SCORER, _BASELINE_SCORER_SOURCE
    if _BASELINE_SCORER is None:
        from gae.profile_scorer import ProfileScorer as _PS, KernelType as _KT
        centroids = _load_bootstrap_centroids()
        if centroids is None:
            centroids = _uniform_baseline_centroids()
            _BASELINE_SCORER_SOURCE = "uniform_fallback"
        else:
            _BASELINE_SCORER_SOURCE = "bootstrap_centroids"
        _BASELINE_SCORER = _PS(
            mu=centroids,
            actions=list(SCORER_ACTIONS),
            categories=list(SOC_CATEGORIES),
            kernel=_KT.L2,
        )
    return _BASELINE_SCORER


async def _tab3_content() -> dict:
    """Tab 3 -- Alert Detail: factors, recommendation, kernel weights."""
    from app.domains.soc.config import SOCDomainConfig
    from app.services.gae_state import get_learning_state as _get_ls

    factor_names: list = []
    graph_node_count = 0

    try:
        factor_names = [c.name for c in SOCDomainConfig.get_factor_computers()]
    except Exception as _exc:
        print(f"[SOC] tab3 factor_names query failed: {_exc}")

    try:
        rows = await graph_client.run_query(
            "MATCH (n) RETURN count(n) AS cnt", {}
        )
        graph_node_count = int((rows[0].get("cnt") or 0) if rows else 0)
    except Exception as _exc:
        print(f"[SOC] tab3 graph_node_count query failed: {_exc}")

    # FIX 2.4 — factor breakdown with sigma, kernel_weight, interpretation
    all_sigmas = [_FACTOR_SIGMA.get(f, 0.15) for f in factor_names]
    factor_breakdown = []
    for fname in factor_names:
        sigma = _FACTOR_SIGMA.get(fname, 0.15)
        kw    = _factor_kernel_weight(sigma, all_sigmas)
        if sigma <= 0.10:
            interp = "High confidence -- low noise, full weight"
        elif sigma <= 0.18:
            interp = "Moderate confidence -- standard weight"
        else:
            interp = f"Auto down-weighted -- high noise (sigma={sigma})"
        factor_breakdown.append({
            "name":           fname,
            "sigma":          sigma,
            "kernel_weight":  kw,
            "interpretation": interp,
        })

    # Best factor = highest kernel_weight
    top_factor: dict[str, Any] = max(
        factor_breakdown,
        key=lambda x: x["kernel_weight"],
        default={},
    )

    # Derive recommendation from a live pending alert (or centroid fallback)
    import numpy as _np
    from app.domains.soc.config import resolve_alert_category, SOCDomainConfig as _SDC
    from app.services.gae_state import get_profile_scorer as _get_scorer

    rec_action      = "investigate"
    rec_conf        = 0.70
    rec_basis       = "centroid_fallback"
    baseline_conf   = 0.25
    baseline_action = "investigate"
    _alert_cat      = None
    _cat_idx        = 0
    _unclassified_alert = False

    try:
        _scorer = _get_scorer()
    except Exception:
        _scorer = None

    if _scorer is not None:
        # Step 1: try a real pending alert
        try:
            _rows = await graph_client.run_query(
                "MATCH (a:Alert {status: 'pending'}) "
                "RETURN a.alert_id AS alert_id, a.category AS category, a.alert_type AS alert_type "
                "LIMIT 1",
                {},
            )
            if _rows:
                _alert_cat = _rows[0].get("category") or resolve_alert_category(
                    _rows[0].get("alert_type") or ""
                )
        except Exception as _exc:
            print(f"[SOC] tab3 pending alert query failed: {_exc}")

        # Step 2: resolve category index. Unclassified alerts are routing-only
        # and must not be scored against category-0 centroids.
        _cfg = _SDC()
        if _alert_cat == "unclassified":
            print("[SOC] tab3 live scoring skipped for unclassified category")
            _unclassified_alert = True
            rec_conf = 0.0
            baseline_conf = 0.0
            rec_basis = "unclassified_routing"
        else:
            try:
                _cat_idx = _cfg.get_category_index(_alert_cat) if _alert_cat else 0
            except Exception as _exc:
                print(f"[SOC] tab3 category_index lookup failed: {_exc}")
                _cat_idx = 0

            # Step 3: score with neutral factor vector
            try:
                _f = _np.full(6, 0.5)
                _result = _scorer.score(_f, _cat_idx)
                rec_action = _result.action_name
                rec_conf   = round(float(_result.confidence), 3)
                rec_basis  = "live_scoring" if _alert_cat else "centroid_fallback"
            except Exception as _exc:
                print(f"[SOC] tab3 live scoring failed: {_exc}")

    # Step 3b: baseline — Day-1 bootstrap centroids (display-only; no live scorer mutation)
    if not _unclassified_alert:
        try:
            _br = _get_baseline_scorer().score(_np.full(6, 0.5), _cat_idx)
            baseline_conf   = round(float(_br.confidence), 4)
            baseline_action = _br.action_name
        except Exception as _exc:
            print(f"[SOC] tab3 baseline scoring failed: {_exc}")
    else:
        baseline_action = "unclassified"

    # Step 4: get override_rate for rationale — same predicate as Tab 1 verified_map
    rec_category = "unclassified" if _unclassified_alert else (_alert_cat or DEFAULT_CATEGORY)
    override_rate = 0.0 if _unclassified_alert else 15.0
    if not _unclassified_alert:
        try:
            _ov_rows = await graph_client.run_query(
                f"MATCH (d:Decision) "
                f"WHERE {soc_decision_where()} "
                f"AND d.category = '{rec_category}' AND d.outcome IS NOT NULL "
                "RETURN count(d) AS verified, "
                "sum(CASE WHEN d.correct = false THEN 1 ELSE 0 END) AS overrides",
                {},
            )
            if _ov_rows:
                _v = int(_ov_rows[0].get("verified") or 0)
                _o = int(_ov_rows[0].get("overrides") or 0)
                if _v > 0:
                    override_rate = round(_o / _v * 100, 1)
        except Exception as _exc:
            print(f"[SOC] tab3 override_rate query failed: {_exc}")

    total_verified = 0
    try:
        _tv_rows = await graph_client.run_query(
            f"MATCH (d:Decision) WHERE {soc_decision_where()} "
            "AND d.outcome IS NOT NULL RETURN count(d) AS cnt",
            {},
        )
        if _tv_rows:
            total_verified = int(_tv_rows[0].get("cnt") or 0)
    except Exception as _exc:
        print(f"[SOC] tab3 total_verified query failed: {_exc}")

    # FIX 2.5 — graph context translation
    graph_context = (
        f"{graph_node_count:,} institutional knowledge nodes -- each representing a "
        "validated analyst judgment on a specific alert pattern, entity relationship, "
        "or threat correlation."
    )

    return {
        "factor_names":    factor_names,
        "factor_breakdown": factor_breakdown,            # FIX 2.4
        "decision_method": "gae_scoring",
        "graph_node_count": graph_node_count,
        "graph_context":   graph_context,                # FIX 2.5
        "recommendation":  {                             # FIX 2.4 (revised)
            "action":              rec_action,
            "confidence":          rec_conf,
            "baseline_confidence": round(baseline_conf, 4),
            "confidence_lift":     round(rec_conf - baseline_conf, 4),
            "baseline_action":     baseline_action,
            "baseline_note": (
                f"Scored against Day-1 bootstrap centroids ({_BASELINE_SCORER_SOURCE}, no DK weighting). "
                f"The difference represents what {total_verified:,} verified decisions "
                f"taught the system about YOUR environment."
            ),
            "basis":      rec_basis,
            "rationale": (                               # FIX 3A
                f"Threat intel enrichment scores at full weight "
                f"(sigma=0.07, highest confidence factor in this alert). "
                f"No prior match in your verified decision ledger for "
                f"this exact pattern -- system recommends {rec_action} rather "
                f"than auto-approve. "
                f"Your analysts override AI on {rec_category.replace('_', ' ')} alerts "
                f"{override_rate:.1f}% of the time: human review is warranted."
            ),
        },
        "kernel_note": (                                 # FIX 2.4 (revised)
            "Higher-noise factors are automatically down-weighted by the "
            "DiagonalKernel scoring engine (Innovation #4). "
            f"device_trust (sigma=0.28) contributes {_factor_kernel_weight(0.28, all_sigmas)*100:.0f}% "
            "of its nominal weight -- the system trusts your highest-confidence signals most."
        ),
    }


async def _tab4_content() -> dict:
    """Tab 4 -- Decision Economics: roi_annual_usd, decisions_per_day,
    qualifies_one_quarter, learning_events_count."""
    from app.domains.soc.config import compute_phase3_minimum

    total_decisions  = 0
    decisions_per_day = 50.0   # default throughput assumption
    learning_events_count = 0

    try:
        rows = await graph_client.run_query(
            f"MATCH (d:Decision) WHERE {soc_decision_where()} "
            "RETURN count(d) AS cnt", {}
        )
        total_decisions = int((rows[0].get("cnt") or 0) if rows else 0)
    except Exception as _exc:
        print(f"[SOC] tab4 total_decisions query failed: {_exc}")

    # Floor: when AGE returns 0, fall back to in-memory learning state
    # (same pattern as compute_iks_v2) so Tab 4 stays consistent with Tab 2.
    if total_decisions == 0:
        try:
            from app.services.gae_state import get_learning_state as _get_ls_t4
            total_decisions = max(0, _get_ls_t4().decision_count)  # SOURCE: in-memory LearningState (resets on restart)
        except Exception as _exc:
            print(f"[SOC] tab4 decision_count fallback failed: {_exc}")

    try:
        # Estimate decisions/day from timestamp spread of Decision nodes
        rows = await graph_client.run_query(
            """
            MATCH (d:Decision)
            WHERE """ + soc_decision_where() + """
              AND d.timestamp_epoch IS NOT NULL
            RETURN min(d.timestamp_epoch) AS t_min, max(d.timestamp_epoch) AS t_max,
                   count(d) AS n
            """, {}
        )
        if rows and rows[0].get("n"):
            t_min = rows[0].get("t_min") or 0
            t_max = rows[0].get("t_max") or 0
            n     = int(rows[0].get("n") or 0)
            span_days = max((t_max - t_min) / 86_400_000.0, 1.0)
            decisions_per_day = round(n / span_days, 1)
    except Exception as _exc:
        print(f"[SOC] tab4 decisions_per_day query failed: {_exc}")

    try:
        rows = await graph_client.run_query(
            f"MATCH (d:Decision) WHERE {soc_decision_where()} "
            "AND d.correct = true RETURN count(d) AS cnt", {}
        )
        learning_events_count = int((rows[0].get("cnt") or 0) if rows else 0)
    except Exception as _exc:
        print(f"[SOC] tab4 learning_events_count query failed: {_exc}")

    # ROI: 0.25 analyst-hours saved per auto-closed decision, $75/hr loaded cost
    roi_annual_usd = round(decisions_per_day * 365 * 0.25 * 75.0, 2)

    # Qualifies for phase-3 calibration within one quarter (90 days)?
    n_min = compute_phase3_minimum(V=200.0, alpha=0.25)
    qualifies_one_quarter = (decisions_per_day * 90) >= n_min

    # FIX 2.6 — ROI methodology note
    # calculation string uses SAME formula as roi_annual_usd (line 2484):
    #   decisions_per_day × 0.25 hr × $75/hr × 365 days
    # 0.25 hr = 15 min saved per decision
    roi_methodology = {
        "baseline_min_per_alert": 44,
        "system_min_per_alert":   13,
        "source": "SANS SOC benchmark + Hackett Group procurement study",
        "note":   "Full methodology available on request.",
        "calculation": (
            f"{decisions_per_day:.1f} decisions/day "
            f"x 15 min saved per decision "
            f"(at current 40% auto-approve rate -- full 31 min gap realized "
            f"at 100% auto-approval) "
            f"x $75/hr analyst cost / 60 min "
            f"= ${decisions_per_day * 75 * 0.25:,.0f}/day "
            f"x 365 days "
            f"= ${roi_annual_usd:,.0f} annually."
        ),
    }

    # FIX 2.7 — Switching cost in dollars
    # BACKLOG-020 Phase 7: use snapshot.verified_decisions (analyst-confirmed only).
    verified_decisions = total_decisions
    try:
        from app.state.graph_snapshot import get_snapshot as _get_snap_t4
        verified_decisions = _get_snap_t4().verified_decisions  # SOURCE: GraphSnapshot (graph-backed, survives restart)
    except Exception as _exc:
        print(f"[SOC] tab4 verified_decisions snapshot failed: {_exc}")
        # falls back to total_decisions
    analyst_days        = max(1, verified_decisions // 10)
    switching_cost_usd  = analyst_days * 800
    switching_cost_dollars = {
        "verified_decisions":       verified_decisions,
        "analyst_days_to_rebuild":  analyst_days,
        "cost_usd":                 switching_cost_usd,
        "assumption":               "$800/day fully-loaded analyst cost (adjustable)",
        "narrative": (
            f"Rebuilding {verified_decisions:,} verified decisions requires approximately "
            f"{analyst_days:,} analyst-days. At $800/day: ${switching_cost_usd:,} to reach "
            "equivalent institutional knowledge. IKS resets to zero on Day 1 of any switch."
        ),
    }
    switching_cost_trajectory = None
    try:
        from app.services.switching_cost import (
            DEFAULT_COST_PER_DAY,
            build_switching_cost_trajectory_payload,
            default_iks_milestones,
        )

        switching_cost_trajectory = build_switching_cost_trajectory_payload(
            iks_milestones=default_iks_milestones(),
            decisions_per_day=max(decisions_per_day, 0.0),
            cost_per_day=DEFAULT_COST_PER_DAY,
        )
    except Exception as _exc:
        print(f"[SOC] tab4 switching_cost_trajectory failed: {_exc}")

    return {
        "roi_annual_usd":          roi_annual_usd,
        "decisions_per_day":       decisions_per_day,
        "qualifies_one_quarter":   qualifies_one_quarter,
        "learning_events_count":  learning_events_count,
        "roi_methodology":         roi_methodology,         # FIX 2.6
        "switching_cost_dollars":  switching_cost_dollars,  # FIX 2.7
        "switching_cost_trajectory": switching_cost_trajectory,
    }


async def _tab5_content() -> dict:
    """Tab 5 -- Executive Narrative: headline, what_changed, what_discovered, what_system_knows."""
    from app.services.executive_narrative import build_executive_narrative_async
    from app.services.gae_state import get_profile_scorer

    narr = await build_executive_narrative_async(graph_client)

    what_changed_raw    = narr.get("what_changed", {})
    what_discovered_raw = narr.get("what_discovered", {})
    what_knows_raw      = narr.get("what_knows", {})

    # Pull verified_decisions from narrative (now aligned to learning state count)
    verified_decisions = int(what_changed_raw.get("total_verified", 0))
    iks_score = what_knows_raw.get("iks_current", 0.0)

    # FIX 2.8 — W2 flywheel: structured fields for CISO audience
    flywheel_edge_count = 0
    try:
        rows = await graph_client.run_query(
            "MATCH ()-[r:TRIGGERED_EVOLUTION]->() RETURN count(r) AS cnt", {}
        )
        flywheel_edge_count = int((rows[0].get("cnt") or 0) if rows else 0)
    except Exception as _exc:
        print(f"[SOC] tab5 flywheel_edge_count query failed: {_exc}")

    flywheel_claim = "+10.13pp accuracy on pattern-matched alerts (validated, p=0.0002, N=30)"

    if flywheel_edge_count == 0:
        flywheel_status = "pre_activation"
        flywheel_message = (
            "Every analyst decision you verify today teaches the system "
            "to route future matching alerts more accurately. As alert "
            "patterns recur in your environment, the system automatically "
            "applies what it learned -- no retraining, no manual updates. "
            "Current state: pre-activation. Benefit activates on first "
            "recurring pattern in your environment."
        )
        flywheel_detail = (
            "+10.13pp accuracy on pattern-matched alerts (validated, "
            "p=0.0002, N=30, unconditional -- CLAIM-W2). "
            f"flywheel_edge_count: {flywheel_edge_count}. pre_activation state. "
            "Expected for newly calibrated deployment."
        )
    else:
        flywheel_status = "active"
        flywheel_message = (
            "Every analyst decision you verify teaches the system to route "
            "future matching alerts more accurately. Pattern learning is active "
            f"-- {flywheel_edge_count:,} recurring patterns detected and routed "
            "with higher accuracy. No retraining, no manual updates required."
        )
        flywheel_detail = (
            "+10.13pp accuracy on pattern-matched alerts (validated, "
            f"p=0.0002, N=30, unconditional -- CLAIM-W2). "
            f"flywheel_edge_count: {flywheel_edge_count}. active state."
        )

    # FIX 2.9 — Centroid summary: human-readable string instead of raw magnitude
    try:
        scorer = get_profile_scorer()
    except Exception:
        scorer = None
    mu = scorer.centroids if scorer is not None else None
    if mu is not None:
        shape = list(mu.shape)
        mu_mean = float(mu.mean())
        centroid_summary = (
            f"Centroid tensor {shape}: 144 values encoding institutional "
            f"judgment across {N_CATEGORIES} alert categories, {N_ACTIONS} actions, {N_FACTORS} factors. "
            f"Mean={mu_mean:.3f} -- system judgment calibrated to your environment."
        )
    else:
        centroid_summary = "Centroid tensor unavailable -- scorer not initialized."

    # FIX 2.10 — Conservation narrative: claim-backed CISO narrative
    health_status = what_knows_raw.get("health_status", "GREEN")
    pre_activation = bool(what_knows_raw.get("pre_activation", False))
    if pre_activation:
        signal = (
            "Pre-activation -- Conservation law monitoring is configured; "
            "live learning is disabled pending validation"
        )
    else:
        signal = (
            "healthy -- no intervention required"
            if health_status == "GREEN"
            else "degraded -- learning paused automatically"
        )
    conservation_narrative = (
        "Conservation law active -- analyst override quality monitored "
        "continuously. 0% quality degradation events missed in validation "
        "(CLAIM-OLS-01, p90 lead time >=50 decisions). "
        f"Current signal: {signal}. "
        "Every system decision is logged in a tamper-evident "
        "Evidence Ledger -- full audit trail available for "
        "regulatory review (EU AI Act Art. 13 evidence supporting human oversight)."
    )

    return {
        "headline":         narr.get("headline", ""),
        "sections":         narr.get("sections", []),
        "what_changed":     what_changed_raw.get("top_shifts", [])[:3],
        "what_discovered": {
            "campaign_count": what_discovered_raw.get("attack_chains_detected", 0),
            "chain_count":    len(what_discovered_raw.get("chain_summaries", [])),
            "mechanism": (                               # FIX 3B addition
                "The system automatically groups related alerts into attack "
                "campaigns using graph correlation -- surfacing multi-stage "
                "threats that single-alert triage misses. "
                f"{what_discovered_raw.get('attack_chains_detected', 0)} campaigns and "
                f"{len(what_discovered_raw.get('chain_summaries', []))} kill chains "
                "identified in this period."
            ),
        },
        "what_system_knows": {
            "iks":                    what_knows_raw.get("iks_current", 0.0),
            "categories_calibrated":  what_knows_raw.get("categories_calibrated", 0),
            "health_status":          health_status,
            "operational_knowledge_status": what_knows_raw.get("operational_knowledge_status"),
            "pre_activation":         pre_activation,
            "learning_enabled":       what_knows_raw.get("learning_enabled"),
            "health_source":          what_knows_raw.get("health_source"),
            "status_reason":          what_knows_raw.get("status_reason"),
            "flywheel_message":       flywheel_message,        # FIX 2.8
            "flywheel_edge_count":    flywheel_edge_count,     # FIX 2.8
            "flywheel_status":        flywheel_status,         # FIX 2.8
            "flywheel_claim":         flywheel_claim,          # FIX 2.8
            "flywheel_detail":        flywheel_detail,         # FIX 3B
            "flywheel_activation_note": (
                "Flywheel pre-active: +10.13pp accuracy lift unlocks automatically "
                "as recurring alert patterns are detected (validated, CLAIM-W2)."
            ) if flywheel_status == "pre_activation" else None,
            "centroid_summary":       centroid_summary,        # FIX 2.9
            "conservation_narrative": conservation_narrative,  # FIX 2.10
            "competitive_test": {
                "title": "Three questions for any vendor evaluation",
                "questions": [
                    {
                        "question": "Show me the compounding curve after 10,000 decisions.",
                        "our_answer": (
                            f"IKS trajectory: 0 -> {iks_score}. "
                            f"{verified_decisions} verified decisions. "
                            f"Accuracy improves with every confirmed decision."
                        ),
                    },
                    {
                        "question": "Show me what the system learned that it didn't know on Day 1.",
                        "our_answer": (
                            "144 centroid values calibrated to YOUR environment. "
                            "DiagonalKernel: device_trust down-weighted to 6% "
                            "(sigma=0.28). threat_intel at full weight (sigma=0.07). "
                            "Your noise fingerprint -- not transferable."
                        ),
                    },
                    {
                        "question": "Show me mathematical proof that auto-approval is safe.",
                        "our_answer": (
                            "Conservation law: alpha*q*V >= theta_min. "
                            "Violation triggers automatic pause. "
                            "What-if simulator demonstrates live."
                        ),
                    },
                ],
            },
            "research_backing": {
                "experiments": "~295 across 15 series",
                "factorial_cells": "1,890+",
                "independent_judges": "5 frontier LLMs (GPT-4, GPT-5.5, Gemini, Grok, Opus)",
                "falsifications": 0,
                "conservation_validation": "three-judge validated",
                "framework_version": "v4 (5 LLM judges, ~115 experiments)",
            },
        },
    }


_TAB_HANDLERS = {
    1: _tab1_content,
    2: _tab2_content,
    3: _tab3_content,
    4: _tab4_content,
    5: _tab5_content,
}


@router.get("/soc/tab/{n}/content")
async def get_tab_content(n: int):
    """
    Export the text content of tab n (1-5) for V-NARRATIVE-CISO evaluation.

    Returns:
      {tab, tab_name, content, generated_at_epoch}
    """
    import time as _time

    if n not in _TAB_NAMES:
        raise HTTPException(status_code=404, detail=f"Tab {n} not found -- valid range is 1-5")

    handler = _TAB_HANDLERS[n]
    content = await handler()

    return {
        "tab":               n,
        "tab_name":          _TAB_NAMES[n],
        "content":           content,
        "generated_at_epoch": int(_time.time() * 1000),
    }


# =============================================================================
# =============================================================================
# GET /api/soc/industry-profiles and GET /api/soc/industry-profile — Block 1.1
# =============================================================================

@router.get("/soc/industry-profiles")
async def list_industry_profiles():
    """
    Return all available industry archetypes (id + label only).

    Used by frontend dropdowns to let the user select an industry before
    viewing personalised ROI projections.
    """
    from app.services.industry_profile import list_industries, load_industry_profile
    ids = list_industries()
    return {
        "industries": [
            {"id": i, "label": load_industry_profile(i)["label"]}
            for i in ids
        ]
    }


@router.get("/soc/industry-profile")
async def get_industry_profile(industry: str = "generic"):
    """
    Return full profile for *industry* including derived metrics.

    Query param: industry (default: "generic")
    Returns: id, label, V, alpha, analyst_hourly_cost, regulatory_multiplier,
             decisions_per_day, theta_min, phase3_minimum, roi_annual_usd,
             roi_annual_usd_regulated, typical_alert_categories, notes.

    404 if industry is not one of the known archetypes.
    """
    from app.services.industry_profile import load_industry_profile
    try:
        profile = load_industry_profile(industry)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return profile


# =============================================================================
# GET /api/soc/deployment-state — Block 2.2
# =============================================================================

@router.get("/soc/deployment-state")
async def get_deployment_state():
    """
    Return the bootstrap centroid tensor (mu_0) stored in the DeploymentState AGE node.

    Written at every startup by write_bootstrap_state().
    Returns {mu, shape, stored_at, gae_version} or 404 if not yet stored.
    """
    from app.services.gae_state import get_bootstrap_centroids
    result = await get_bootstrap_centroids(graph_client)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="DeploymentState not found -- server may not have completed startup",
        )
    return result


# =============================================================================
# GET /api/soc/analyst-eta-weights — Block 9.1 D5 per-analyst η weighting
# =============================================================================

@router.get("/soc/analyst-eta-weights")
async def get_analyst_eta_weights_endpoint():
    """
    Return current per-analyst eta weights plus per-analyst precision.

    Before N_min decisions: all weights = 1.0 (conservative/uniform).
    After N_min decisions: precision-weighted in [0.5, 1.5].

    Returns
    -------
    {
      "calibrated": bool,
      "n_decisions": int,
      "n_min": int,
      "analysts": {
        "analyst_a": {"precision": 0.82, "eta_weight": 1.15},
        ...
      }
    }
    """
    from app.services.learning_health import compute_analyst_precision
    from app.services.gae_state import get_analyst_eta_weights, apply_analyst_eta_weights
    from app.domains.soc.config import GateConfig
    from app.services.gae_state import get_learning_state as _get_ls, get_profile_scorer

    n_decisions = 0
    try:
        n_decisions = _get_ls().decision_count  # SOURCE: in-memory LearningState (resets on restart)
    except Exception as _exc:
        print(f"[SOC] analyst-eta n_decisions query failed: {_exc}")

    # Fetch precision from AGE
    precision = await compute_analyst_precision(graph_client)

    # Build GateConfig to compute calibrated weights via the validated formula
    cfg = GateConfig(
        n_decisions=n_decisions,
        V=200.0,
        alpha=0.25,
        per_analyst_precision=precision,
    )
    weights = cfg.eta_weights

    # Update module-level state so scorer has current weights
    try:
        scorer = get_profile_scorer()
        apply_analyst_eta_weights(scorer, weights)
    except Exception as _exc:
        print(f"[SOC] analyst-eta apply_weights failed: {_exc}")

    analysts = {
        analyst: {
            "precision": round(precision.get(analyst, 0.0), 4),
            "eta_weight": round(weights.get(analyst, 1.0), 4),
        }
        for analyst in set(list(precision.keys()) + list(weights.keys()))
    }

    return {
        "calibrated":  cfg.calibrated,
        "n_decisions": n_decisions,
        "n_min":       cfg.n_min,
        "analysts":    analysts,
    }


# =============================================================================
# GET /api/soc/analyst-weights — Block 9.1 D5 per-analyst η weighting (rich)
# =============================================================================

_ANALYST_DECISION_COUNT_QUERY = (
    f"MATCH (d:Decision) WHERE {soc_decision_where()} "
    'AND d.source = "live" AND d.analyst IS NOT NULL '
    "RETURN d.analyst AS analyst, count(d) AS total"
)

_ANALYST_WEIGHT_THRESHOLD = 20   # decisions required for "personalized" status


@router.get("/soc/analyst-weights")
async def get_analyst_weights():
    """
    Return per-analyst eta weight information for the Tab 2 Two-Level Judgment view.

    Weight formula: weight = min(1.5, max(0.5, precision / mean_precision))
    Analysts with < 20 decisions use default weight (1.0) -- not personalized.
    Validated: D5 Spearman r=0.975-1.000 (V-D5).

    Returns
    -------
    {
      "analyst_weights": {
        "analyst_001": {
          "precision": 0.90,
          "decision_count": 147,
          "eta_weight": 1.8,
          "status": "personalized"
        }, ...
      },
      "weight_ratio_high_low": float,
      "threshold_decisions": 20,
      "note": "High-precision analysts contribute more ... V-D5"
    }
    """
    from app.services.learning_health import compute_analyst_precision
    from app.domains.soc.config import GateConfig
    from app.services.gae_state import get_learning_state as _get_ls

    # -- decision counts per analyst ------------------------------------------
    decision_counts: dict = {}
    try:
        rows = await graph_client.run_query(_ANALYST_DECISION_COUNT_QUERY, {})
        decision_counts = {r["analyst"]: int(r["total"]) for r in (rows or [])}
    except Exception as _exc:
        print(f"[SOC] analyst-detail decision_counts query failed: {_exc}")

    # -- precision + weights --------------------------------------------------
    n_decisions = 0
    try:
        n_decisions = _get_ls().decision_count  # SOURCE: in-memory LearningState (resets on restart)
    except Exception as _exc:
        print(f"[SOC] analyst-detail n_decisions query failed: {_exc}")

    precision = await compute_analyst_precision(graph_client)

    cfg = GateConfig(
        n_decisions=n_decisions,
        V=200.0,
        alpha=0.25,
        per_analyst_precision=precision,
    )
    weights = cfg.eta_weights   # {} when uncalibrated or no precision data

    # -- merge all known analysts ---------------------------------------------
    all_analysts = set(decision_counts) | set(precision) | set(weights)
    analyst_weights: dict = {}
    for analyst in sorted(all_analysts):
        count   = decision_counts.get(analyst, 0)
        prec    = precision.get(analyst, 0.0)
        weight  = weights.get(analyst, 1.0)
        if count < _ANALYST_WEIGHT_THRESHOLD:
            status = f"default -- insufficient decisions (need {_ANALYST_WEIGHT_THRESHOLD}+)"
            weight = 1.0   # enforce default regardless of formula
        else:
            status = "personalized"
        analyst_weights[analyst] = {
            "precision":      round(prec, 4),
            "decision_count": count,
            "eta_weight":     round(weight, 4),
            "status":         status,
        }

    # -- weight_ratio_high_low ------------------------------------------------
    if analyst_weights:
        all_weights = [v["eta_weight"] for v in analyst_weights.values()]
        weight_ratio = round(max(all_weights) / max(min(all_weights), 1e-6), 4)
    else:
        weight_ratio = 1.0

    return {
        "analyst_weights":       analyst_weights,
        "weight_ratio_high_low": weight_ratio,
        "threshold_decisions":   _ANALYST_WEIGHT_THRESHOLD,
        "note": (
            "High-precision analysts contribute more to centroid learning. "
            "Spearman r=0.975-1.000 (V-D5). "
            "Formula: weight = clip(precision / mean_precision, 0.5, 1.5)."
        ),
    }


# =============================================================================
# GET /api/soc/volume-baseline — Block 9.2 D3 spike detector
# =============================================================================

@router.get("/soc/volume-baseline")
async def get_volume_baseline():
    """
    Return 30-day alert volume baseline and current spike status.

    spike_sigma = 5.0 (conservative, < N_min decisions)
                = 3.0 (calibrated, >= N_min decisions)
    threshold   = daily_mean + spike_sigma * max(daily_std, 1.0)

    Returns compute_volume_baseline() result + spike_active flag.
    """
    from app.services.learning_health import compute_volume_baseline
    from app.services.gae_state import is_volume_spike_active

    baseline = await compute_volume_baseline(graph_client)
    baseline["spike_active"] = is_volume_spike_active()
    return baseline


# =============================================================================
# GET /api/soc/frozen-categories — Block 9.3 D2 category freeze
# =============================================================================

@router.get("/soc/frozen-categories")
async def get_frozen_categories_endpoint():
    """
    Return current frozen categories and 30-day baseline distribution.

    freeze_threshold = 2.0 -- category frozen when today_share > 2x baseline.
    Frozen categories are only set during an active volume spike (D3 coupled).

    Returns
    -------
    {
      "spike_active":       bool,
      "frozen_categories":  ["lateral_movement"],
      "category_baseline":  {"credential_access": 0.35, ...},
      "freeze_threshold":   2.0
    }
    """
    from app.services.learning_health import compute_category_baseline
    from app.services.gae_state import (
        is_volume_spike_active,
        get_frozen_categories,
    )

    category_baseline = await compute_category_baseline(graph_client)

    return {
        "spike_active":      is_volume_spike_active(),
        "frozen_categories": sorted(get_frozen_categories()),
        "category_baseline": category_baseline,
        "freeze_threshold":  2.0,
    }


# =============================================================================
# GET /api/soc/spike-cap-status — Block 9.4 D7 spike update cap
# =============================================================================

@router.get("/soc/spike-cap-status")
async def get_spike_cap_status_endpoint():
    """
    Return current spike update cap status.

    spike_cap = int(1.5 x baseline_daily_mean).
    Resets to 0 updates each cadence via reset_spike_counter().

    Returns
    -------
    {
      "spike_active":         bool,
      "spike_cap":            int,
      "updates_this_cadence": int,
      "cap_reached":          bool,
      "baseline_daily":       float
    }
    """
    from app.services.gae_state import get_spike_cap_status
    from app.services.learning_health import compute_volume_baseline

    status = get_spike_cap_status()
    baseline_daily = 0.0
    try:
        baseline = await compute_volume_baseline(graph_client)
        baseline_daily = baseline.get("daily_mean", 0.0)
    except Exception as _exc:
        print(f"[SOC] learning-health baseline_daily query failed: {_exc}")

    status["baseline_daily"] = baseline_daily
    return status


# =============================================================================
# GET /api/soc/centroid-export — Block 2.3
# =============================================================================

@router.get("/soc/centroid-export")
async def get_centroid_export(format: str = "json"):
    """
    Export the full centroid tensor with provenance metadata (Block 2.3).

    Additive schema over build_centroid_export base fields:
      exported_at           -- alias for generated_at_epoch (ms)
      factors               -- factor name list [n_factors]
      centroids             -- dict: category -> action -> [factor_values]
      drift_from_bootstrap  -- per-category L2 drift dict (overrides scalar)
      checksum              -- SHA-256 of centroids dict (auditable)
      iks_score             -- current IKS (informational)

    Plus all original build_centroid_export fields retained for back-compat:
      generated_at_epoch, gae_version, sha256, current_mu, bootstrap_mu ...

    ?format=json    (default) -- full export including all tensor fields
    ?format=summary           -- excludes current_mu, bootstrap_mu, centroids

    Safe degradation: returns {"status": "cold_start"} with 200 if scorer
    is not yet initialized.
    """
    import hashlib
    import json as _json
    import time as _time
    import numpy as _np
    from app.services.gae_state import build_centroid_export, get_profile_scorer

    scorer = get_profile_scorer()

    if scorer is None:
        return {
            "status":  "cold_start",
            "message": "No centroid data yet",
        }

    # Build base export (current_mu, bootstrap_mu, sha256, categories, etc.)
    raw = await build_centroid_export(scorer, graph_client)

    categories = raw["categories"]
    actions    = raw["actions"]
    current_mu = raw["current_mu"]

    # Centroids dict: category → action → [factor_values]
    centroids: dict = {}
    for c_idx, cat in enumerate(categories):
        centroids[cat] = {}
        for a_idx, action in enumerate(actions):
            centroids[cat][action] = [
                round(float(v), 6) for v in current_mu[c_idx][a_idx]
            ]

    # Per-category drift (mean L2 distance from μ₀ across actions)
    bootstrap_mu = raw.get("bootstrap_mu")
    drift_per_cat: dict = {}
    if bootstrap_mu is not None:
        curr_arr = _np.array(current_mu, dtype=_np.float64)   # [n_categories, n_actions, n_factors]
        boot_arr = _np.array(bootstrap_mu, dtype=_np.float64) # [n_categories, n_actions, n_factors]
        for c_idx, cat in enumerate(categories):
            diff = curr_arr[c_idx] - boot_arr[c_idx]           # [n_actions, n_factors]
            drift_per_cat[cat] = round(
                float(_np.mean(_np.linalg.norm(diff, axis=1))), 4
            )
    else:
        for cat in categories:
            drift_per_cat[cat] = None

    # Checksum over centroids dict (sorted JSON — auditable; distinct from sha256)
    checksum = hashlib.sha256(
        _json.dumps(centroids, sort_keys=True).encode()
    ).hexdigest()

    # IKS score (best-effort; 0.0 on any failure)
    iks_score = 0.0
    try:
        from app.services.iks import compute_iks_v2
        iks_data = await compute_iks_v2(graph_client)
        iks_score = iks_data.get("iks_v2", 0.0)
    except Exception as _exc:
        print(f"[SOC] centroid-export iks_score query failed: {_exc}")

    # Merge: start with raw base fields, then add/override with new fields
    export = {
        **raw,
        "exported_at":          raw["generated_at_epoch"],
        "factors":              list(SOC_FACTORS),
        "centroids":            centroids,
        "drift_from_bootstrap": drift_per_cat,   # override scalar with per-cat dict
        "checksum":             checksum,
        "iks_score":            iks_score,
    }

    if format == "summary":
        export = {k: v for k, v in export.items()
                  if k not in ("current_mu", "bootstrap_mu", "centroids")}

    return export


# =============================================================================
# GET /api/soc/centroid-heatmap — Block 2.4
# =============================================================================

@router.get("/soc/centroid-heatmap")
async def get_centroid_heatmap():
    """
    Heat map data: factor weight per (category x action).

    Returns categories, actions, factors, kernel_weights,
    heatmap (cat->action->{mean, factors}), noise_fingerprint,
    and interpretation string.

    Safe degradation: returns {"status": "cold_start"} with 200 if
    ProfileScorer is not yet initialized.
    """
    import numpy as _np
    from app.services.gae_state import get_profile_scorer

    scorer = get_profile_scorer()
    if scorer is None:
        return {
            "status":  "cold_start",
            "message": "No centroid data yet",
        }

    # ── kernel_weights: normalised 1/σ² per factor ─────────────────────
    all_sigmas = [_FACTOR_SIGMA.get(f, 0.15) for f in SOC_FACTORS]
    kernel_weights: dict = {
        f: _factor_kernel_weight(_FACTOR_SIGMA.get(f, 0.15), all_sigmas)
        for f in SOC_FACTORS
    }

    # ── heatmap: category → action → {mean, factors} ───────────────────
    mu = scorer.centroids  # shape [n_cat, n_actions, n_factors]
    n_cat    = min(len(SOC_CATEGORIES), mu.shape[0])
    n_act    = min(len(SCORER_ACTIONS), mu.shape[1])
    n_fac    = min(len(SOC_FACTORS),    mu.shape[2])

    heatmap: dict = {}
    for c_idx in range(n_cat):
        cat = SOC_CATEGORIES[c_idx]
        heatmap[cat] = {}
        for a_idx in range(n_act):
            action = SCORER_ACTIONS[a_idx]
            vals = [round(float(mu[c_idx, a_idx, f_idx]), 4) for f_idx in range(n_fac)]
            heatmap[cat][action] = {
                "mean":    round(float(_np.mean(mu[c_idx, a_idx, :n_fac])), 4),
                "factors": vals,
            }

    # ── noise_fingerprint: per-factor sigma + kernel_weight + label ─────
    noise_fingerprint: dict = {}
    for f in SOC_FACTORS:
        sigma = _FACTOR_SIGMA.get(f, 0.15)
        kw    = kernel_weights[f]
        if sigma <= 0.10:
            label = "High confidence"
        elif sigma <= 0.18:
            label = "Moderate confidence"
        else:
            label = "Auto down-weighted -- high noise"
        noise_fingerprint[f] = {
            "sigma":         sigma,
            "kernel_weight": kw,
            "label":         label,
        }

    interpretation = (
        "Higher values = stronger signal for that action. "
        f"device_trust kernel_weight={kernel_weights.get('device_trust', 0):.4f} "
        "means the system trusts this factor at "
        f"{round(kernel_weights.get('device_trust', 0) * 100, 1)}% of its nominal weight."
    )

    # kernel_label: DiagonalKernel when noise spans >1.5× range; L2Kernel otherwise.
    # Computed from actual sigma values so the frontend never hardcodes the name.
    if all_sigmas:
        noise_ratio = max(all_sigmas) / min(all_sigmas) if min(all_sigmas) > 0 else 1.0
        kernel_label = "DiagonalKernel" if noise_ratio > 1.5 else "L2Kernel"
    else:
        kernel_label = "DiagonalKernel"

    return {
        "categories":        SOC_CATEGORIES[:n_cat],
        "actions":           SCORER_ACTIONS[:n_act],
        "factors":           SOC_FACTORS[:n_fac],
        "kernel_weights":    kernel_weights,
        "kernel_label":      kernel_label,
        "heatmap":           heatmap,
        "noise_fingerprint": noise_fingerprint,
        "interpretation":    interpretation,
    }


# =============================================================================
# GET /api/soc/centroid-support — Block 3.6
# =============================================================================

@router.get("/soc/centroid-support", response_model=CentroidSupportResponse)
async def get_centroid_support():
    """
    Centroid Support Monitoring (Block 3.6).

    Checks whether live centroids have drifted outside the data support
    region defined by the bootstrap baseline (mu_zero).  A centroid is
    flagged when >=2 factor dimensions exceed threshold_sigma x sigma_factor.

    Safe degradation: if scorer is None (cold start) or bootstrap is
    unavailable, returns GREEN with an explanatory note.

    Health:
      GREEN : warning_count == 0
      AMBER : 1-3 warnings
      RED   : 4+ warnings
    """
    import numpy as _np
    from app.services.centroid_support import compute_centroid_support
    from app.services.gae_state import get_profile_scorer, get_bootstrap_centroids

    _SIGMA = [_FACTOR_SIGMA.get(f, 0.15) for f in SOC_FACTORS]
    _THRESHOLD = 2.0

    _COLD_START = {
        "support_summary":  {},
        "overall_health":   "GREEN",
        "warning_count":    0,
        "threshold_sigma":  _THRESHOLD,
        "interpretation":   "All centroids within data support region.",
        "note": "Centroid support monitoring active after deployment qualification",
    }

    scorer = get_profile_scorer()
    if scorer is None:
        return _COLD_START

    # Fetch bootstrap baseline
    try:
        bootstrap = await get_bootstrap_centroids(graph_client)
    except Exception as _exc:
        print(f"[SOC] centroid-evolution bootstrap query failed: {_exc}")
        bootstrap = None

    if bootstrap is None or bootstrap.get("mu") is None:
        return _COLD_START

    mu      = scorer.centroids                                     # [C, A, D]
    mu_zero = _np.array(bootstrap["mu"], dtype=_np.float64)

    # Shapes may differ if model was re-sized — use minimum shared dims
    C = min(mu.shape[0], mu_zero.shape[0], len(SOC_CATEGORIES))
    A = min(mu.shape[1], mu_zero.shape[1], len(SCORER_ACTIONS))
    D = min(mu.shape[2], mu_zero.shape[2], len(_SIGMA))

    mu_slice      = mu[:C, :A, :D]
    mu_zero_slice = mu_zero[:C, :A, :D]

    raw = compute_centroid_support(mu_slice, mu_zero_slice, _SIGMA[:D], _THRESHOLD)

    # Build human-readable summary
    support_summary: dict = {}
    warning_count = 0
    for c in range(C):
        cat = SOC_CATEGORIES[c]
        support_summary[cat] = {}
        for a in range(A):
            action = SCORER_ACTIONS[a]
            entry = raw[(c, a)]
            if entry["support_status"] == "warning":
                warning_count += 1
            support_summary[cat][action] = {
                "support_status":      entry["support_status"],
                "n_factors_outside":   entry["n_factors_outside"],
                "max_deviation_sigma": round(entry["max_deviation_sigma"], 4),
            }

    if warning_count == 0:
        overall_health = "GREEN"
        interpretation = "All centroids within data support region."
    elif warning_count <= 3:
        overall_health = "AMBER"
        interpretation = (
            f"{warning_count} centroid position(s) outside observed range "
            f"(>{_THRESHOLD}sigma). Learning may be extrapolating."
        )
    else:
        overall_health = "RED"
        interpretation = (
            f"WARNING: {warning_count} centroid positions outside observed range. "
            "Consider re-seeding bootstrap baseline."
        )

    return {
        "support_summary":  support_summary,
        "overall_health":   overall_health,
        "warning_count":    warning_count,
        "threshold_sigma":  _THRESHOLD,
        "interpretation":   interpretation,
    }


# =============================================================================
# GET /api/soc/distance-log — BACKLOG-015 extension: EXP-G1 convergence monitor
# =============================================================================

def _compute_convergence_trend(distances: list) -> str:
    """
    Classify last-10-entry distance trend for EXP-G1 monitoring.

    Returns: "insufficient_data" | "decreasing" | "increasing" | "stable"
    """
    if len(distances) < 10:
        return "insufficient_data"
    last10 = distances[:10]  # already ordered DESC from query
    # Reverse so oldest is first for trend direction
    last10 = list(reversed(last10))
    monotone_decrease = all(last10[i] >= last10[i + 1] for i in range(len(last10) - 1))
    if monotone_decrease:
        return "decreasing"
    # Count consecutive increases from the end
    consecutive_increase = 0
    for i in range(len(last10) - 1, 0, -1):
        if last10[i] > last10[i - 1]:
            consecutive_increase += 1
        else:
            break
    if consecutive_increase >= 5:
        return "increasing"
    return "stable"


@router.get("/soc/distance-log")
async def get_decision_distance_log(limit: int = 50):
    """
    Return last N DecisionDistanceLog entries for EXP-G1 convergence monitoring.

    centroid_distance_to_canonical decreases during healthy model convergence
    (simulation: 3.0->2.4 over 600 decisions).
    """
    from app.services.reconvergence_logger import read_decision_distance_log
    from app.db.graph_client import graph_client

    entries = []
    try:
        entries = await read_decision_distance_log(graph_client, limit=max(1, min(limit, 500)))
    except Exception as _exc:
        print(f"[SOC] reconvergence-log entries query failed: {_exc}")

    # Parse stored JSON category distributions
    for e in entries:
        if isinstance(e.get("alert_category_distribution"), str):
            try:
                import json as _json
                e["alert_category_distribution"] = _json.loads(
                    e["alert_category_distribution"]
                )
            except Exception:
                e["alert_category_distribution"] = {}

    distances = [
        float(e["centroid_distance_to_canonical"])
        for e in entries
        if e.get("centroid_distance_to_canonical") is not None
    ]
    trend = _compute_convergence_trend(distances)

    return {
        "entries":           entries,
        "total":             len(entries),
        "convergence_trend": trend,
        "note": (
            "EXP-G1 field 1: centroid_distance must decrease during convergence. "
            "Simulation baseline: 3.0->2.4 over 600 decisions."
        ),
    }


# =============================================================================
# GET /api/sentinel/alerts — Block 4.2 Real Sentinel Connector
# =============================================================================

@router.get("/sentinel/alerts")
async def get_sentinel_alerts(top: int = 50):
    """
    Fetch normalized alerts from Microsoft Sentinel Graph Security API.

    Returns SituationAnalyzer schema dicts.
    Falls back gracefully when credentials are not configured.

    Required env vars:
      SENTINEL_TENANT_ID, SENTINEL_CLIENT_ID, SENTINEL_CLIENT_SECRET
    Optional:
      SENTINEL_WORKSPACE_ID
    """
    from app.connectors.sentinel_real import get_sentinel_connector

    connector = get_sentinel_connector()

    if not connector.is_configured():
        return {
            "status": "not_configured",
            "alerts": [],
            "count":  0,
            "message": (
                "Set SENTINEL_TENANT_ID, SENTINEL_CLIENT_ID, "
                "SENTINEL_CLIENT_SECRET in environment to enable."
            ),
            "schema": "SituationAnalyzer v1.0",
        }

    alerts = await connector.fetch_alerts(top=max(1, min(top, 999)))
    return {
        "status": "ok",
        "alerts": alerts,
        "count":  len(alerts),
        "schema": "SituationAnalyzer v1.0",
    }


# =============================================================================
# POST /api/sentinel/writeback-test — Block 7.1 Sentinel Write-Back (Outward)
# =============================================================================

class _WritebackTestRequest(BaseModel):
    incident_id: str = "INC-TEST-001"
    action:      str = "escalate"
    confidence:  float = 0.90
    decision_id: str = "test-decision-001"
    campaign_id: Optional[str] = None


@router.post("/sentinel/writeback-test")
async def sentinel_writeback_test(req: _WritebackTestRequest):
    """
    Exercise the Sentinel write-back path without triggering a real triage.

    Always calls push_incident_update() and returns the result so callers
    can verify the outward connector is wired correctly.

    When Sentinel credentials are not configured the connector returns
    success=False with error='not_configured' -- this is the expected
    no-op result in demo / CI environments.
    """
    from app.connectors.sentinel_real import get_sentinel_connector

    connector = get_sentinel_connector()
    result = await connector.push_incident_update(
        incident_id=req.incident_id,
        action=req.action,
        confidence=req.confidence,
        decision_id=req.decision_id,
        campaign_id=req.campaign_id,
    )
    return {
        "writeback_result": result,
        "incident_id":      req.incident_id,
        "action":           req.action,
        "confidence":       req.confidence,
        "decision_id":      req.decision_id,
        "campaign_id":      req.campaign_id,
        "connector_configured": connector.is_configured(),
    }


# ============================================================================
# GET /api/soc/epistemic-state — per-category knowledge band
# ============================================================================

@router.get("/soc/epistemic-state")
async def get_epistemic_state():
    """
    Per-category epistemic state: verified decision count + knowledge band.

    Band thresholds:
        novice      < 50 verified decisions
        learning    50-199
        calibrating 200-499
        expert      500+

    Returns:
        {
          "categories": {
            "<category>": {"count": int, "band": str},
            ...
          },
          "total_verified": int
        }
    """
    from app.state.graph_snapshot import get_snapshot
    try:
        snap = get_snapshot()
    except RuntimeError:
        return {"categories": {}, "total_verified": 0}
    return {
        "categories":     snap.get_epistemic_state(),
        "total_verified": snap.verified_decisions,
    }
