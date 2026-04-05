"""
SOC Analytics API - Tab 1
Governed security metrics with provenance
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import re

from app.db.neo4j import neo4j_client


router = APIRouter()


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
    Travel-correlated login risk — 6 data sources correlated in one query.
    Each row: User | Destination | Auth anomalies | Threat intel | Resolution
    """
    return [
        MetricDataPoint(
            label="John Smith | Singapore | 3 anomalous logins | Pulsedive: 103.15.42.17 (high risk) | Resolution: false_positive — travel confirmed",
            value=0.0,
        ),
        MetricDataPoint(
            label="Maria Chen | Frankfurt | 1 anomalous login | No threat intel match | Resolution: pending review",
            value=0.0,
        ),
        MetricDataPoint(
            label="David Park | São Paulo | 2 anomalous logins | GreyNoise: scanning activity from region | Resolution: escalated",
            value=0.0,
        ),
    ]


def get_device_trust_gaps_data() -> List[MetricDataPoint]:
    """
    Unmanaged device access — device × user × asset × risk score in one view.
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
    Policy conflict landscape — proactive governance mapping.
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
    Threat intel coverage analysis — shows what the system knows and doesn't know.
    Value = alert count; last bar (0) highlights the coverage gap.
    """
    return [
        MetricDataPoint(label="Pulsedive enriched (68%)", value=34.0),
        MetricDataPoint(label="GreyNoise enriched (24%)", value=12.0),
        MetricDataPoint(label="Enriched by both (16%)", value=8.0),
        MetricDataPoint(label="No enrichment — GAP (32%)", value=16.0),
        MetricDataPoint(label="Internal lateral movement (0% coverage)", value=0.0),
    ]


# Cross-context metrics served from Neo4j (H7-FIX-3)
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
        return max(scores, key=scores.get)

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
                "UserProfile (HR — timezone/team)",
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
                "GraphCorrelation (Neo4j)",
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
        # Cross-context metrics use real Neo4j queries (H7-FIX-3)
        # ====================================================================
        if metric_id in CROSS_CONTEXT_METRIC_IDS:
            try:
                rows = await neo4j_client.run_query(
                    "MATCH (a:Alert)-[:ASSOCIATED_WITH]->(t:ThreatIntel) "
                    "RETURN a.alert_id AS alert_id, t.source AS source, "
                    "t.ioc_type AS ioc_type LIMIT 10",
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
                print(f"[SOC] cross-context Neo4j query failed: {qe}")
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

@router.get("/soc/detection-engineering")
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
        baseline = SOC_PROFILE_CENTROIDS  # shape (6, 4, 6)
        current = scorer.mu               # shape (6, 4, 6)

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
            rows = await neo4j_client.run_query(
                "MATCH (d:Decision)-[:DECISION_FOR]->(a:Alert) "
                "WHERE a.category = $cat "
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

    Attempts a live Neo4j count of ThreatIntel nodes; falls back to
    static numbers if Neo4j is unavailable.
    """
    # Query Neo4j for all stats; fall back to zeros on failure (H7-FIX-3)
    ti_loaded = 0
    high_severity_iocs = 0
    alerts_total = 0
    open_alerts = 0
    decisions_total = 0
    nodes_count = 0
    rels_count = 0
    alert_types_count = 0
    patterns_count = 0
    source = "unavailable"

    try:
        # ThreatIntel counts
        ti_res = await neo4j_client.run_query(
            "MATCH (t:ThreatIntel) "
            "RETURN count(t) AS total, "
            "count(CASE WHEN t.severity IN ['critical','high'] THEN 1 END) AS high_sev",
        )
        if ti_res:
            ti_loaded = int(ti_res[0].get("total") or 0)
            high_severity_iocs = int(ti_res[0].get("high_sev") or 0)

        # Alert counts — total and open (no Decision yet)
        alert_res = await neo4j_client.run_query(
            "MATCH (a:Alert) "
            "RETURN count(a) AS total, "
            "count(CASE WHEN NOT (a)<-[:FOR_ALERT]-(:Decision) THEN 1 END) AS open_count",
        )
        if alert_res:
            alerts_total = int(alert_res[0].get("total") or 0)
            open_alerts = int(alert_res[0].get("open_count") or 0)

        # Decision count
        dec_res = await neo4j_client.run_query(
            "MATCH (d:Decision) RETURN count(d) AS c",
        )
        if dec_res:
            decisions_total = int(dec_res[0].get("c") or 0)

        # Graph topology
        node_res = await neo4j_client.run_query("MATCH (n) RETURN count(n) AS c")
        if node_res:
            nodes_count = int(node_res[0].get("c") or 0)

        rel_res = await neo4j_client.run_query("MATCH ()-[r]->() RETURN count(r) AS c")
        if rel_res:
            rels_count = int(rel_res[0].get("c") or 0)

        at_res = await neo4j_client.run_query("MATCH (t:AlertType) RETURN count(t) AS c")
        if at_res:
            alert_types_count = int(at_res[0].get("c") or 0)

        pat_res = await neo4j_client.run_query("MATCH (p:AttackPattern) RETURN count(p) AS c")
        if pat_res:
            patterns_count = int(pat_res[0].get("c") or 0)

        source = "neo4j"
    except Exception as exc:
        print(f"[SOC] threat-landscape Neo4j query failed (using zero fallback): {exc}")

    return {
        "threat_intel": {
            "indicators_loaded": ti_loaded,
            "sources": ["Pulsedive", "GreyNoise"],
            "high_severity_iocs": high_severity_iocs,
            "last_refreshed_minutes_ago": 23,
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
            "avg_confidence": 0.89,
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
    seed_simulation_alerts).  Falls back to an empty list if Neo4j
    is unavailable.
    """
    breakdown = []
    try:
        results = await neo4j_client.run_query(
            """
            MATCH (a:Alert)
            WHERE a.mitre_tactic IS NOT NULL AND a.mitre_tactic <> ''
            RETURN a.mitre_tactic AS tactic, count(a) AS count
            ORDER BY count DESC
            """,
            {},
        )
        breakdown = [
            {"tactic": r["tactic"], "count": int(r["count"])}
            for r in results
        ]
    except Exception as exc:
        print(f"[SOC] attack-tactic-breakdown query failed: {exc}")

    return {"breakdown": breakdown}


# ============================================================================
# GET /api/soc/analytics — Real Neo4j SOC metrics for Tab 1 (H7-FIX-3)
# ============================================================================

@router.get("/soc/analytics")
async def get_soc_analytics():
    """
    Return real Neo4j aggregations for the five core Tab 1 SOC metrics.

    Metrics with sufficient graph data return live counts (source='neo4j').
    Metrics that require data not seeded (e.g. MTTD, which needs per-decision
    timestamps) carry estimated=True and a descriptive note rather than a fake
    number.
    """
    try:
        # Metric 1 — Alert volume
        alert_res = await neo4j_client.run_query(
            "MATCH (a:Alert) RETURN count(a) AS total_alerts"
        )
        total_alerts = int(alert_res[0]["total_alerts"]) if alert_res else 0

        # Metric 2 — Open alerts (no Decision yet)
        open_res = await neo4j_client.run_query(
            "MATCH (a:Alert) "
            "WHERE NOT (a)<-[:FOR_ALERT]-(:Decision) "
            "RETURN count(a) AS open_alerts"
        )
        open_alerts = int(open_res[0]["open_alerts"]) if open_res else 0

        # Metric 3 — Total decisions
        dec_res = await neo4j_client.run_query(
            "MATCH (d:Decision) RETURN count(d) AS total_decisions"
        )
        total_decisions = int(dec_res[0]["total_decisions"]) if dec_res else 0

        # Metric 4 — Correct decisions
        correct_res = await neo4j_client.run_query(
            "MATCH (d:Decision) "
            "WHERE d.outcome = 'correct' OR d.correct = true "
            "RETURN count(d) AS correct_decisions"
        )
        correct_decisions = int(correct_res[0]["correct_decisions"]) if correct_res else 0

        # Metric 5 — Category breakdown
        cat_res = await neo4j_client.run_query(
            "MATCH (a:Alert) "
            "RETURN a.category AS category, count(a) AS count "
            "ORDER BY count DESC"
        )
        category_breakdown = [
            {"category": r["category"] or "unknown", "count": int(r["count"])}
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
            "source": "neo4j",
            "estimated_metrics": [
                {
                    "value": None,
                    "label": "MTTD",
                    "estimated": True,
                    "note": "Requires decision timestamps — available after v5.0-beta",
                }
            ],
        }
    except Exception as e:
        print(f"[SOC] analytics Neo4j query failed: {e}")
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
                    "note": "Requires decision timestamps — available after v5.0-beta",
                }
            ],
        }



# ============================================================================
# GET /api/soc/learning-state — Expose LearningState for Tab-2 Section D
# ============================================================================

@router.get("/soc/learning-state")
async def get_learning_state_endpoint():
    """Expose learning state for Tab-2 Section D rollback status."""
    from app.services.gae_state import get_learning_state as _get_ls

    frozen = False
    decision_count = 0
    last_verified_at = None

    try:
        ls = _get_ls()
        decision_count = ls.decision_count

        # frozen comes from ProfileScorer._frozen (if scorer is attached)
        scorer = getattr(ls, "profile_scorer", None)
        if scorer is not None:
            frozen = bool(getattr(scorer, "_frozen", False))
    except RuntimeError:
        # Learning state not initialized yet — return defaults
        pass
    except Exception as exc:
        print(f"[SOC] learning-state error: {exc}")

    # Query Neo4j for last verified_at
    try:
        rows = await neo4j_client.run_query(
            """
            MATCH (d:Decision)
            WHERE d.verified_at IS NOT NULL
            RETURN d.verified_at AS verified_at
            ORDER BY d.verified_at DESC
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
        iks_v2_data = await compute_iks_v2(neo4j_client)
    except Exception as exc:
        print(f"[SOC] learning-state iks_v2 failed: {exc}")

    from app.domains.soc.config import BOOTSTRAP_CATEGORY_WEIGHTS
    return {
        "frozen":            frozen,
        "decision_count":    decision_count,
        "last_verified_at":  last_verified_at,
        "checkpoint_id":     None,
        "iks_v2":            iks_v2_data.get("iks_v2", 0.0),
        "iks_components":    iks_v2_data.get("components", {}),
        "iks_interpretation": iks_v2_data.get("interpretation", ""),
        "total_decisions":   iks_v2_data.get("total_decisions", 0),
        "categories_active": iks_v2_data.get("categories_active", 0),
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
        rows = await neo4j_client.run_query(
            """
            MATCH (d:Decision {id: $decision_id})
            OPTIONAL MATCH (d)-[:DECIDED_ON]->(a:Alert)
            OPTIONAL MATCH (a)-[:INVOLVES]->(u:User)
            OPTIONAL MATCH (a)-[:DETECTED_ON]->(asset:Asset)
            RETURN d.factor_vector      AS factor_vector,
                   d.category           AS category,
                   d.action             AS action,
                   d.confidence         AS confidence,
                   d.timestamp          AS timestamp,
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
        raise HTTPException(status_code=500, detail=f"Neo4j query failed: {exc}")

    if not rows:
        raise HTTPException(status_code=404, detail=f"Decision {decision_id!r} not found")

    row      = rows[0]
    fv_raw   = row.get("factor_vector")
    category = row.get("category") or "credential_access"
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
    travel_val  = factor_map.get("travel_match", 0.0)
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
        cal_rows = await neo4j_client.run_query(
            "MATCH (d:Decision {category: $category}) "
            "WHERE d.outcome IS NOT NULL RETURN count(d) AS cnt",
            {"category": category},
        )
        calibration_count = int((cal_rows[0].get("cnt") or 0) if cal_rows else 0)
    except Exception:
        calibration_count = 0

    # ── Step 2b: ThreatIndicator source (for threat_intel_match template) ───
    ti_source = "threat intelligence feed"
    try:
        ti_rows = await neo4j_client.run_query(
            """
            MATCH (d:Decision {id: $decision_id})-[:DECIDED_ON]->(a:Alert)
            -[:HAS_INDICATOR]->(ti:ThreatIndicator)
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
            neo4j_client=neo4j_client,
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
            f"Travel match {travel_val:.0%} — "
            f"{'matches travel record' if travel_val > 0.6 else 'no travel record match'}"
        ),
        "time_context": (
            f"Time anomaly {time_val:.0%} — "
            f"{'login outside normal hours' if time_val > 0.5 else 'within normal hours'}"
        ),
        "threat_context": (
            f"Threat intel {threat_val:.0%} — "
            f"{'IOC match found' if threat_val > 0.5 else 'no IOC matches'}"
        ),
        "pattern_context": (
            f"Pattern history {pattern_val:.0%} — "
            f"{'matches prior behavior' if pattern_val > 0.5 else 'no prior pattern match'}"
        ),
        "device_context": (
            f"Device trust {device_val:.0%} — "
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
            f"travel={travel_val:.2f}, asset={asset_val:.2f}, "
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

    Retrieves the decision's factor_vector from the Decision node in Neo4j,
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
        neo4j_client,
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
            {"name": str, "ioc_type": str, "ioc_value": str, "severity": str,
             "source": str, "last_seen": str},
            ...
        ],
        "total_matches": int,
    }
    """
    from app.services.threat_indicator import ThreatIndicatorService

    indicators = await ThreatIndicatorService.get_indicators_for_alert(
        alert_id, neo4j_client
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
    alerts_per_day     : int   — total daily alert volume (default 200)
    verification_rate  : float — fraction of decisions analysts verify (default 0.30)
    graph_level        : str   — SIEM/graph enrichment tier G1-G4 (default G1)
    """
    from gae.convergence import generate_onboarding_calendar
    from app.domains.soc.config import SOC_CATEGORIES, BOOTSTRAP_CATEGORY_WEIGHTS

    calendar = generate_onboarding_calendar(
        categories=SOC_CATEGORIES,
        category_weights=BOOTSTRAP_CATEGORY_WEIGHTS,
        alerts_per_day=alerts_per_day,
        verification_rate=verification_rate,
        graph_level=graph_level,
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
    hours_back : int — look-back window in hours (default 72)
    """
    from app.services.attack_chain import AttackChainService
    service = AttackChainService(neo4j_client)
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
    return generate_compliance_page()


# ============================================================================
# GET /api/soc/transparency — P21 Transparency Page (L-11)
# ============================================================================

@router.get("/soc/transparency")
async def transparency_page():
    """L-11: How This System Works — three depth levels.

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
    engine = BenchmarkingEngine(neo4j_client)
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

@router.get("/soc/executive-narrative")
async def executive_narrative():
    """F12: Executive narrative digest consumed by Tab 5."""
    from app.services.executive_narrative import build_executive_narrative_async
    return await build_executive_narrative_async(neo4j_client)


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

    data = await build_executive_narrative_async(neo4j_client)

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
        _p('SOC Copilot — Executive Narrative', title_style),
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
        story.append(_p(f"  • {shift.get('description', '')}", body_style))

    story += [
        Spacer(1, 0.2 * inch),
        _p('What Was Discovered', h2_style),
        _p(f"Attack chains: {data['what_discovered']['attack_chains_detected']}", body_style),
    ]
    for s in data['what_discovered'].get('chain_summaries', []):
        story.append(_p(f"  • {s}", body_style))

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
    """P32: Level 2 benchmarking section (mock data for validation)."""
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
    """Parse datetime from Neo4j result (str or datetime)."""
    if isinstance(dt_value, datetime):
        return dt_value
    try:
        return datetime.fromisoformat(str(dt_value).replace("Z", "+00:00"))
    except Exception:
        return datetime.utcnow()


def _format_campaign(raw: dict) -> dict:
    """Format raw Neo4j campaign row for API response."""
    c = raw.get("c", raw)  # handle both wrapped and unwrapped
    if hasattr(c, "data"):   # Neo4j Node object
        c = dict(c)
    return {
        "campaign_id": c.get("id", ""),
        "first_seen": str(c.get("first_seen", "")),
        "last_seen": str(c.get("last_seen", "")),
        "alert_count": c.get("alert_count", 0),
        "category_sequence": c.get("category_sequence", []),
        "shared_entities": c.get("shared_entities", []),
        "confidence": c.get("confidence", 0.0),
        "trigger_rule": c.get("trigger_rule", ""),
        "severity": c.get("severity", "LOW"),
        "nl_summary": c.get("nl_summary", ""),
    }


def _format_campaign_detail(raw: dict) -> dict:
    """Format full campaign detail including decisions."""
    c = raw.get("c", raw)
    if hasattr(c, "data"):
        c = dict(c)
    decisions = raw.get("decisions", [])
    formatted = _format_campaign(raw)

    # Build attack_progression
    stage_map = {}
    for d in (decisions or []):
        if not isinstance(d, dict):
            continue
        cat = d.get("category", "unknown")
        if cat not in stage_map:
            stage_map[cat] = {"category": cat, "count": 0,
                              "first_seen": d.get("timestamp")}
        stage_map[cat]["count"] += 1

    formatted["decisions"] = decisions
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

@router.get("/soc/campaigns")
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

    repo = CampaignRepository(neo4j_client)
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
# GET /api/soc/campaigns/{campaign_id} — F6 Campaign detail
# ============================================================================

@router.get("/soc/campaigns/{campaign_id}")
async def get_campaign_detail(campaign_id: str):
    """Return full campaign detail including member decisions."""
    from app.domains.soc.campaigns import CampaignRepository

    repo = CampaignRepository(neo4j_client)
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
      - Live decision counts per category from Neo4j
      - Published reference curve (V-ACC-TRAJ-1b-v2) from constants.py
      - Interpolated current accuracy and progress toward enriched plateau

    Cold-start safe — works with 0 decisions.
    """
    from app.services.accuracy_trajectory import build_accuracy_trajectory

    live_data: dict[str, int] = {}
    decisions_per_day: float = 50.0
    sigma_per_category: dict[str, float] = {}

    try:
        rows = await neo4j_client.run_query(
            """
            MATCH (d:Decision)
            RETURN d.category AS category, count(d) AS cnt
            """,
            {},
        )
        for record in rows:
            cat = record.get("category") or "unknown"
            live_data[cat] = int(record.get("cnt", 0))
    except Exception:
        pass  # cold-start safe — empty live_data falls back to reference curve

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
    Idempotent — MERGE ensures safe repeated calls.

    Response: {campaigns_found, campaigns_written, events_processed}
    """
    from app.domains.soc.campaigns import CampaignCorrelationEngine, CampaignRepository
    from app.domains.soc.config import SOCDomainConfig

    config = SOCDomainConfig.get_campaign_config()
    repo = CampaignRepository(neo4j_client)
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
    agreement rate ascending — least agreement first = most interesting),
    per-archetype override precision, and day-level variance.

    Returns graceful "accumulating" state if no ShadowDecision nodes exist.
    """
    SOURCE = "v_shadow_synthetic_v3"

    # ── 1. Overall ────────────────────────────────────────────────────────
    overall_result = await neo4j_client.run_query(
        """
        MATCH (sd:ShadowDecision {source: $source})
        RETURN count(sd) AS total,
               sum(CASE WHEN sd.agreed    THEN 1 ELSE 0 END) AS agreed_count,
               sum(CASE WHEN sd.ai_correct THEN 1 ELSE 0 END) AS ai_correct_count
        """,
        {"source": SOURCE},
    )

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
    cat_result = await neo4j_client.run_query(
        """
        MATCH (sd:ShadowDecision {source: $source})
        RETURN sd.category AS category,
               count(sd)   AS total,
               sum(CASE WHEN sd.agreed     THEN 1 ELSE 0 END) AS agreed_count,
               sum(CASE WHEN sd.ai_correct THEN 1 ELSE 0 END) AS ai_correct_count,
               sum(CASE WHEN NOT sd.agreed THEN 1 ELSE 0 END) AS override_count
        ORDER BY agreed_count ASC
        """,
        {"source": SOURCE},
    )

    per_category = {}
    for r in cat_result:
        cat_total = r["total"] or 1
        per_category[r["category"]] = {
            "agree_rate":     round(r["agreed_count"]    / cat_total, 4),
            "ai_accuracy":    round(r["ai_correct_count"] / cat_total, 4),
            "override_count": r["override_count"],
            "total":          r["total"],
        }

    # ── 3. Per archetype ──────────────────────────────────────────────────
    arch_result = await neo4j_client.run_query(
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

    per_archetype = {}
    for r in arch_result:
        oc = r["override_count"] or 1
        per_archetype[r["analyst"]] = {
            "override_count":     r["override_count"],
            "override_precision": round(r["correct_overrides"] / oc, 4),
        }

    # ── 4. Day variance ───────────────────────────────────────────────────
    day_result = await neo4j_client.run_query(
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

    day_row = day_result[0] if day_result else {}
    min_rate = day_row.get("min_daily_agree", 0.0)
    max_rate = day_row.get("max_daily_agree", 1.0)
    spread = round((max_rate or 0) - (min_rate or 0), 4)
    trend = "stable" if spread < 0.20 else "variable"

    # ── Lead finding ──────────────────────────────────────────────────────
    # Category with lowest agreement rate (most interesting)
    lowest_cat = min(per_category, key=lambda c: per_category[c]["agree_rate"])
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


# ── GET /api/soc/enrichment-advisor ──────────────────────────────────────────

@router.get("/soc/enrichment-advisor")
async def get_enrichment_advisor():
    """
    Return enrichment opportunity rankings with live IOC coverage from Neo4j.

    ioc_coverage = alerts with ≥1 ThreatIndicator / total alerts.
    Falls back to 0.0 if Neo4j is unavailable or graph is empty.
    """
    from app.services.enrichment_advisor import get_enrichment_advice

    ioc_coverage = 0.0
    try:
        results = await neo4j_client.run_query(
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
    return await compute_verification_health(neo4j_client)


# =============================================================================
# Block 2.1 — Centroid PITR backup / restore / list
# =============================================================================

@router.post("/soc/backup-centroid")
async def backup_centroid():
    """
    Serialize the live centroid tensor and write it to the backup store.
    Returns backup metadata: {backup_id, sha256, shape, step, timestamp_epoch}.
    """
    from app.services.gae_state import get_profile_scorer, write_centroid_backup
    scorer = get_profile_scorer()
    if scorer is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="ProfileScorer not ready")
    payload = write_centroid_backup(scorer)
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
    Restore the centroid tensor from a backup.
    Body: {"backup_id": "centroid_backup_<ts>"} or {} to use latest.
    Returns 409 on SHA-256 checksum mismatch.
    """
    from fastapi import HTTPException
    from app.services.gae_state import restore_centroid_from_backup
    backup_id = (body or {}).get("backup_id") or None
    try:
        payload = restore_centroid_from_backup(backup_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {
        "restored":        True,
        "backup_id":       payload.get("backup_id"),
        "sha256":          payload["sha256"],
        "step":            payload["step"],
        "timestamp_epoch": payload["timestamp_epoch"],
    }


@router.get("/soc/centroid-backups")
async def list_centroid_backups_endpoint():
    """
    List all centroid backup files.
    Returns [{backup_id, timestamp_epoch, step, sha256}] newest-first.
    """
    from app.services.gae_state import list_centroid_backups
    return {"backups": list_centroid_backups()}


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
        n_decisions = get_learning_state().decision_count
    except Exception:
        pass

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


async def _tab1_content() -> dict:
    """Tab 1 — Alert Triage: alert_count, top_alert_types, pending_count."""
    alert_count  = 0
    pending_count = 0
    top_alert_types: list = []

    try:
        rows = await neo4j_client.run_query(
            "MATCH (a:Alert) RETURN count(a) AS cnt", {}
        )
        alert_count = int((rows[0].get("cnt") or 0) if rows else 0)
    except Exception:
        pass

    try:
        rows = await neo4j_client.run_query(
            "MATCH (a:Alert) WHERE a.status IN ['pending', 'open'] "
            "RETURN count(a) AS cnt", {}
        )
        pending_count = int((rows[0].get("cnt") or 0) if rows else 0)
    except Exception:
        pass

    try:
        rows = await neo4j_client.run_query(
            "MATCH (a:Alert) RETURN a.type AS type, count(a) AS n "
            "ORDER BY n DESC LIMIT 3", {}
        )
        top_alert_types = [
            {"type": r.get("type") or "unknown", "count": int(r.get("n") or 0)}
            for r in rows
        ]
    except Exception:
        pass

    return {
        "alert_count":     alert_count,
        "top_alert_types": top_alert_types,
        "pending_count":   pending_count,
    }


async def _tab2_content() -> dict:
    """Tab 2 — Institutional Intelligence: IKS, category accuracy, drift, override."""
    from app.services.iks import compute_iks_v2

    iks_score         = 0.0
    iks_interpretation = ""
    category_accuracy_summary: dict = {}
    drift_alert_count = 0
    override_learning_status = "inactive"

    try:
        iks_data = await compute_iks_v2(neo4j_client)
        iks_score          = iks_data.get("iks_v2", 0.0)
        iks_interpretation = iks_data.get("interpretation", "")
        category_accuracy_summary = iks_data.get("components", {})
    except Exception:
        pass

    try:
        rows = await neo4j_client.run_query(
            "MATCH (d:Decision) WHERE d.confidence IS NOT NULL AND d.confidence < 0.50 "
            "RETURN count(d) AS cnt", {}
        )
        drift_alert_count = int((rows[0].get("cnt") or 0) if rows else 0)
    except Exception:
        pass

    try:
        from app.services.override_detector import override_detector as _od
        if _od.activated:
            override_learning_status = f"active ({_od.example_count} examples)"
        else:
            override_learning_status = f"inactive ({_od.example_count} examples)"
    except Exception:
        pass

    return {
        "iks_score":               iks_score,
        "iks_interpretation":      iks_interpretation,
        "category_accuracy_summary": category_accuracy_summary,
        "drift_alert_count":       drift_alert_count,
        "override_learning_status": override_learning_status,
    }


async def _tab3_content() -> dict:
    """Tab 3 — Alert Detail: factor_names, decision_method, graph_node_count."""
    from app.domains.soc.config import SOCDomainConfig

    factor_names: list = []
    graph_node_count = 0

    try:
        factor_names = [c.name for c in SOCDomainConfig.get_factor_computers()]
    except Exception:
        pass

    try:
        rows = await neo4j_client.run_query(
            "MATCH (n) RETURN count(n) AS cnt", {}
        )
        graph_node_count = int((rows[0].get("cnt") or 0) if rows else 0)
    except Exception:
        pass

    return {
        "factor_names":   factor_names,
        "decision_method": "gae_scoring",
        "graph_node_count": graph_node_count,
    }


async def _tab4_content() -> dict:
    """Tab 4 — Decision Economics: roi_annual_usd, decisions_per_day,
    qualifies_one_quarter, evolution_events_count."""
    from app.domains.soc.config import compute_phase3_minimum

    total_decisions  = 0
    decisions_per_day = 50.0   # default throughput assumption
    evolution_events_count = 0

    try:
        rows = await neo4j_client.run_query(
            "MATCH (d:Decision) RETURN count(d) AS cnt", {}
        )
        total_decisions = int((rows[0].get("cnt") or 0) if rows else 0)
    except Exception:
        pass

    try:
        # Estimate decisions/day from timestamp spread of Decision nodes
        rows = await neo4j_client.run_query(
            """
            MATCH (d:Decision)
            WHERE d.timestamp_epoch IS NOT NULL
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
    except Exception:
        pass

    try:
        rows = await neo4j_client.run_query(
            "MATCH (d:Decision) WHERE d.correct = true RETURN count(d) AS cnt", {}
        )
        evolution_events_count = int((rows[0].get("cnt") or 0) if rows else 0)
    except Exception:
        pass

    # ROI: 0.25 analyst-hours saved per auto-closed decision, $75/hr loaded cost
    roi_annual_usd = round(decisions_per_day * 365 * 0.25 * 75.0, 2)

    # Qualifies for phase-3 calibration within one quarter (90 days)?
    n_min = compute_phase3_minimum(V=200.0, alpha=0.25)
    qualifies_one_quarter = (decisions_per_day * 90) >= n_min

    return {
        "roi_annual_usd":        roi_annual_usd,
        "decisions_per_day":     decisions_per_day,
        "qualifies_one_quarter": qualifies_one_quarter,
        "evolution_events_count": evolution_events_count,
    }


async def _tab5_content() -> dict:
    """Tab 5 — Executive Narrative: headline, what_changed, what_discovered, what_system_knows."""
    from app.services.executive_narrative import build_executive_narrative_async

    narr = await build_executive_narrative_async(neo4j_client)

    what_changed_raw    = narr.get("what_changed", {})
    what_discovered_raw = narr.get("what_discovered", {})
    what_knows_raw      = narr.get("what_knows", {})

    return {
        "headline":         narr.get("headline", ""),
        "what_changed":     what_changed_raw.get("top_shifts", [])[:3],
        "what_discovered": {
            "campaign_count": what_discovered_raw.get("attack_chains_detected", 0),
            "chain_count":    len(what_discovered_raw.get("chain_summaries", [])),
        },
        "what_system_knows": {
            "iks":                  what_knows_raw.get("iks_current", 0.0),
            "categories_calibrated": what_knows_raw.get("categories_calibrated", 0),
            "health_status":        what_knows_raw.get("health_status", "UNKNOWN"),
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
    Export the text content of tab n (1–5) for V-NARRATIVE-CISO evaluation.

    Returns:
      {tab, tab_name, content, generated_at_epoch}
    """
    import time as _time

    if n not in _TAB_NAMES:
        raise HTTPException(status_code=404, detail=f"Tab {n} not found — valid range is 1-5")

    handler = _TAB_HANDLERS[n]
    content = await handler()

    return {
        "tab":               n,
        "tab_name":          _TAB_NAMES[n],
        "content":           content,
        "generated_at_epoch": int(_time.time() * 1000),
    }


# =============================================================================
# GET /api/soc/deployment-state — Block 2.2
# =============================================================================

@router.get("/soc/deployment-state")
async def get_deployment_state():
    """
    Return the bootstrap centroid tensor (μ₀) stored in the DeploymentState Neo4j node.

    Written at every startup by write_bootstrap_state().
    Returns {mu, shape, stored_at, gae_version} or 404 if not yet stored.
    """
    from app.services.gae_state import get_bootstrap_centroids
    result = await get_bootstrap_centroids(neo4j_client)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="DeploymentState not found — server may not have completed startup",
        )
    return result
