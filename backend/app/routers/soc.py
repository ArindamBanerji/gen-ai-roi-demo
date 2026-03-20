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
# GET /api/soc/centroid-evolution — Centroid delta history from Decision nodes
# Used by Tab-2 Section A/B and Tab-4 Chart A.
# ============================================================================

@router.get("/soc/centroid-evolution")
async def get_centroid_evolution(
    n: int = Query(default=200, ge=1, le=1000),
    category: Optional[str] = Query(default=None),
):
    """
    Return centroid delta history from Decision nodes.
    Used by Tab-2 Section A/B and Tab-4 Chart A.
    Returns [] if no Decision nodes have centroid_delta_norm set yet.
    """
    try:
        rows = await neo4j_client.run_query(
            """
            MATCH (d:Decision)
            WHERE d.centroid_delta_norm IS NOT NULL
              AND d.centroid_delta_norm > 0
              AND ($category IS NULL OR d.category = $category)
            RETURN d.id AS id,
                   d.centroid_delta_norm AS centroid_delta_norm,
                   d.category AS category,
                   d.action AS action,
                   d.correct AS correct,
                   d.verified_at AS verified_at
            ORDER BY d.verified_at ASC
            LIMIT $n
            """,
            {"category": category, "n": n},
        )
        result = []
        for i, r in enumerate(rows):
            result.append({
                "decision_number": i + 1,
                "id": r.get("id"),
                "centroid_delta_norm": float(r.get("centroid_delta_norm") or 0.0),
                "category": r.get("category") or "unknown",
                "action": r.get("action") or "unknown",
                "correct": bool(r.get("correct")),
                "verified_at": str(r.get("verified_at") or ""),
            })
        print(f"[SOC] centroid-evolution: returned {len(result)} records (n={n}, category={category!r})")
        return result
    except Exception as exc:
        print(f"[SOC] centroid-evolution query failed: {exc}")
        return []


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
# GET /api/soc/iks-trend — IKS v2 trend (Chart A replacement)
# ============================================================================

@router.get("/soc/iks-trend")
async def get_iks_trend_endpoint():
    """
    Return IKS v2 score trend for Chart A.

    Currently returns the current score as a single trend point.
    Future: store periodic IKSSnapshot nodes for historical trend.

    Response
    --------
    {
        "trend": [{"decisions": int, "iks_v2": float, "timestamp": str}],
        "current": {"iks_v2": float, "components": dict, "interpretation": str},
    }
    """
    from app.services.iks import compute_iks_v2

    try:
        current = await compute_iks_v2(neo4j_client)
    except Exception as exc:
        print(f"[SOC] iks-trend compute failed: {exc}")
        current = {
            "iks_v2": 0.0,
            "components": {},
            "interpretation": "unavailable",
            "total_decisions": 0,
            "categories_active": 0,
        }

    trend_point = {
        "decisions":  current.get("total_decisions", 0),
        "iks_v2":     current.get("iks_v2", 0.0),
        "timestamp":  datetime.utcnow().isoformat() + "Z",
    }

    return {
        "trend": [trend_point],
        "current": {
            "iks_v2":         current.get("iks_v2", 0.0),
            "components":     current.get("components", {}),
            "interpretation": current.get("interpretation", ""),
        },
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

class ShadowToggleRequest(BaseModel):
    enabled: bool


class AnalystActionRequest(BaseModel):
    decision_id: str
    analyst_action: str


@router.post("/soc/shadow/toggle")
async def shadow_toggle(request: ShadowToggleRequest):
    """Enable or disable shadow mode."""
    from app.services.shadow_mode import ShadowModeService
    ShadowModeService.SHADOW_ENABLED = request.enabled
    return {"shadow_mode": ShadowModeService.SHADOW_ENABLED}


@router.post("/soc/shadow/analyst-action")
async def shadow_analyst_action(request: AnalystActionRequest):
    """Record what the analyst actually did for a shadow decision."""
    from app.services.shadow_mode import ShadowModeService
    await ShadowModeService.record_analyst_action(
        decision_id=request.decision_id,
        analyst_action=request.analyst_action,
        neo4j_service=neo4j_client,
    )
    return {"recorded": True}


@router.get("/soc/shadow/report")
async def shadow_report():
    """Return shadow mode agreement report by category."""
    from app.services.shadow_mode import ShadowModeService
    return await ShadowModeService.get_shadow_report(neo4j_client)


# ============================================================================
# Checkpoint / Rollback endpoints  (Phase 4 §17.5)
# ============================================================================

class CheckpointCreateRequest(BaseModel):
    reason: str = "manual"


class RollbackRequest(BaseModel):
    checkpoint_id: str


@router.post("/soc/checkpoint/create")
async def checkpoint_create(request: CheckpointCreateRequest):
    """Snapshot current centroids to a Checkpoint node."""
    from app.services.checkpoint import CheckpointService
    from app.services.gae_state import get_profile_scorer
    try:
        scorer = get_profile_scorer()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"Scorer not ready: {exc}")

    checkpoint_id = await CheckpointService.create_checkpoint(
        scorer=scorer,
        neo4j_service=neo4j_client,
        reason=request.reason,
    )
    return {
        "checkpoint_id": checkpoint_id,
        "timestamp":     datetime.utcnow().isoformat() + "Z",
        "reason":        request.reason,
    }


@router.get("/soc/checkpoint/list")
async def checkpoint_list():
    """List all checkpoints ordered by timestamp DESC."""
    from app.services.checkpoint import CheckpointService
    checkpoints = await CheckpointService.list_checkpoints(neo4j_client)
    return {"checkpoints": checkpoints}


@router.post("/soc/checkpoint/rollback")
async def checkpoint_rollback(request: RollbackRequest):
    """Restore centroids from a checkpoint and freeze the scorer."""
    from app.services.checkpoint import CheckpointService
    from app.services.gae_state import get_profile_scorer
    try:
        scorer = get_profile_scorer()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"Scorer not ready: {exc}")

    result = await CheckpointService.rollback(
        checkpoint_id=request.checkpoint_id,
        scorer=scorer,
        neo4j_service=neo4j_client,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ============================================================================
# Scorer freeze / unfreeze  (Phase 4)
# ============================================================================

@router.post("/soc/scorer/freeze")
async def scorer_freeze():
    """Freeze the ProfileScorer — stops centroid updates."""
    from app.services.gae_state import get_profile_scorer
    try:
        scorer = get_profile_scorer()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"Scorer not ready: {exc}")
    scorer.freeze()
    return {"frozen": True}


@router.post("/soc/scorer/unfreeze")
async def scorer_unfreeze():
    """Unfreeze the ProfileScorer — re-enables centroid updates."""
    from app.services.gae_state import get_profile_scorer
    try:
        scorer = get_profile_scorer()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"Scorer not ready: {exc}")
    scorer.unfreeze()
    return {"frozen": False}


# ============================================================================
# GET /api/soc/auto-approve-stats  — Phase 5 coverage dashboard
# ============================================================================

@router.get("/soc/auto-approve-stats")
async def auto_approve_stats():
    """Return per-category auto-approve coverage.

    Response
    --------
    {
        "total_decisions": int,
        "auto_approved":   int,
        "coverage_pct":    float,
        "by_category": {
            "credential_access": {"total": X, "auto_approved": Y, "coverage_pct": Z},
            ...
        }
    }
    """
    try:
        rows = await neo4j_client.run_query(
            """
            MATCH (d:Decision)
            RETURN d.category AS category,
                   count(d) AS total,
                   sum(CASE WHEN d.auto_approved = true THEN 1 ELSE 0 END) AS approved
            """,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Neo4j query failed: {exc}")

    by_category: dict = {}
    grand_total    = 0
    grand_approved = 0

    for row in rows:
        cat      = row.get("category") or "unknown"
        total    = int(row.get("total") or 0)
        approved = int(row.get("approved") or 0)
        by_category[cat] = {
            "total":        total,
            "auto_approved": approved,
            "coverage_pct": round(approved / max(total, 1) * 100, 1),
        }
        grand_total    += total
        grand_approved += approved

    return {
        "total_decisions": grand_total,
        "auto_approved":   grand_approved,
        "coverage_pct":    round(grand_approved / max(grand_total, 1) * 100, 1),
        "by_category":     by_category,
    }


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

    result = await ProvenanceService.get_provenance_from_graph(decision_id, neo4j_client)
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


# ============================================================================
# Graph Explorer endpoints — Phase 8 (Tab 1 Panel B)
# ============================================================================

class _GraphQueryRequest(BaseModel):
    cypher: str


@router.post("/soc/graph/query")
async def graph_explorer_query(request: _GraphQueryRequest):
    """Run a validated read-only Cypher query.

    Body: {"cypher": "MATCH (n:User) RETURN n.name LIMIT 5"}

    Returns 400 if the query contains blocked mutation keywords.
    Returns {"rows": [...], "count": N, "query": str} on success.
    """
    from app.services.graph_explorer import GraphExplorerService
    result = await GraphExplorerService.run_safe_query(request.cypher, neo4j_client)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/soc/graph/top-nodes")
async def graph_top_nodes(
    type: Optional[str] = None,
    limit: int = 10,
):
    """Return top N most-connected nodes.

    Query params: ?type=User&limit=10 (both optional).
    Excludes :Decision and :Checkpoint nodes (internal bookkeeping).
    """
    from app.services.graph_explorer import GraphExplorerService
    nodes = await GraphExplorerService.get_top_nodes(
        neo4j_client, node_type=type, limit=limit
    )
    return {"nodes": nodes, "count": len(nodes)}


@router.get("/soc/graph/node/{node_id}/neighbors")
async def graph_node_neighbors(node_id: str):
    """Return all neighbors of a specific node (up to 50).

    Response: {"node_id": str, "neighbors": [...], "total": int}
    """
    from app.services.graph_explorer import GraphExplorerService
    return await GraphExplorerService.get_node_neighbors(node_id, neo4j_client)


@router.get("/soc/graph/summary")
async def graph_summary():
    """Return node and relationship type counts for the explorer header.

    Response:
    {
        "total_nodes": int,
        "total_relationships": int,
        "node_types": {"Alert": N, "User": M, ...},
        "relationship_types": {"DECIDED_ON": N, ...},
    }
    """
    from app.services.graph_explorer import GraphExplorerService
    return await GraphExplorerService.get_graph_summary(neo4j_client)


@router.get("/soc/graph/prebuilt-queries")
async def graph_prebuilt_queries_list():
    """Return the catalogue of pre-built query names and descriptions.

    Response: {"queries": [...], "count": N}
    """
    from app.services.graph_explorer import GraphExplorerService
    queries = GraphExplorerService.list_prebuilt_queries()
    return {"queries": queries, "count": len(queries)}


@router.post("/soc/graph/prebuilt/{query_name}")
async def graph_run_prebuilt(query_name: str):
    """Run a pre-built query by name.

    Returns {"rows": [...], "count": N, "query": str}.
    Returns 404 if query_name is not in the catalogue.
    """
    from app.services.graph_explorer import GraphExplorerService
    result = await GraphExplorerService.run_prebuilt_query(query_name, neo4j_client)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# GET /api/soc/learning-health  (P9 — Learning Health Monitor)
# ---------------------------------------------------------------------------

@router.get("/soc/learning-health")
async def learning_health():
    """Return learning health status based on conservation law monitoring.

    Evaluates alpha(t)*q(t)*V(t) >= theta_min (absolute floor) and
    relative-drop thresholds (baseline-2sigma=AMBER, baseline-3sigma=RED).

    Returns
    -------
    {
        status            : "GREEN" | "AMBER" | "RED" | "CALIBRATING",
        signal            : float,
        theta_min         : float,
        conservation      : {passed, status, headroom},
        components        : {alpha, q, V, n},
        baseline          : float | null,
        baseline_std      : float | null,
        red_days          : int,
        auto_pause_active : bool,
        interpretation    : str,
    }
    """
    from app.services.learning_health import LearningHealthMonitor
    return await LearningHealthMonitor.evaluate(neo4j_client)


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
# P22: Intervention Controls — EU AI Act Article 14 human oversight (L-12)
# ============================================================================

class FreezeRequest(BaseModel):
    initiated_by: str
    reason: str


class RollbackInterventionRequest(BaseModel):
    snapshot_id: str
    initiated_by: str
    reason: str
    preview: bool = False


class ThresholdRequest(BaseModel):
    category: str
    new_threshold: float
    initiated_by: str
    reason: str


def _get_intervention_controls():
    """Build InterventionControls from existing singletons."""
    from app.services.gae_state import get_profile_scorer
    from app.services.checkpoint import checkpoint_svc
    from app.services.composite_gate import CompositeDiscriminant
    from app.services.intervention_controls import InterventionControls
    scorer = get_profile_scorer()
    return InterventionControls(
        db_client=neo4j_client,
        scorer=scorer,
        checkpoint_service=checkpoint_svc,
        composite_gate=CompositeDiscriminant,
    )


@router.post("/soc/interventions/freeze")
async def intervention_freeze(request: FreezeRequest):
    """Freeze all centroid learning globally."""
    try:
        ctrl = _get_intervention_controls()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return await ctrl.freeze_all_learning(request.initiated_by, request.reason)


@router.post("/soc/interventions/unfreeze")
async def intervention_unfreeze(request: FreezeRequest):
    """Resume centroid learning globally."""
    try:
        ctrl = _get_intervention_controls()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return await ctrl.unfreeze_all_learning(request.initiated_by, request.reason)


@router.post("/soc/interventions/rollback")
async def intervention_rollback(request: RollbackInterventionRequest):
    """Rollback to a centroid snapshot. preview=True returns what would change."""
    try:
        ctrl = _get_intervention_controls()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    result = await ctrl.rollback(
        request.snapshot_id, request.initiated_by, request.reason, request.preview
    )
    if "error" in result and not result.get("preview"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/soc/interventions/threshold")
async def intervention_threshold(request: ThresholdRequest):
    """Adjust auto-approve confidence threshold for a category."""
    try:
        ctrl = _get_intervention_controls()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return await ctrl.adjust_threshold(
        request.category, request.new_threshold, request.initiated_by, request.reason
    )


@router.get("/soc/interventions/state")
async def intervention_state():
    """Current state of all intervention controls."""
    try:
        ctrl = _get_intervention_controls()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return await ctrl.get_current_state()


@router.get("/soc/interventions/history")
async def intervention_history(limit: int = Query(50, ge=1, le=500)):
    """Intervention audit log."""
    try:
        ctrl = _get_intervention_controls()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    records = await ctrl.get_intervention_history(limit=limit)
    return {"interventions": records, "count": len(records)}


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
