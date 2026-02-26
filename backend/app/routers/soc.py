"""
SOC Analytics API - Tab 1
Governed security metrics with provenance
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import re


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
        # ====================================================================
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
    # Attempt live ThreatIntel counts from Neo4j
    ti_loaded = 47
    high_severity_iocs = 12
    try:
        from app.db.neo4j import neo4j_client
        results = await neo4j_client.run_query(
            "MATCH (t:ThreatIntel) "
            "RETURN count(t) AS total, "
            "count(CASE WHEN t.severity IN ['critical','high'] THEN 1 END) AS high_sev",
            {},
        )
        if results:
            ti_loaded = int(results[0].get("total") or ti_loaded)
            high_severity_iocs = int(results[0].get("high_sev") or high_severity_iocs)
    except Exception as exc:
        print(f"[SOC] threat-landscape Neo4j query failed (using static fallback): {exc}")

    return {
        "threat_intel": {
            "indicators_loaded": ti_loaded,
            "sources": ["Pulsedive", "GreyNoise"],
            "high_severity_iocs": high_severity_iocs,
            "last_refreshed_minutes_ago": 23,
        },
        "active_alerts": {
            "in_queue": 2,
            "analyzed_today": 14,
            "auto_closed_today": 11,
            "escalated_today": 3,
        },
        "governance": {
            "policy_conflicts_detected": 3,
            "decisions_today": 14,
            "audit_chain_verified": True,
            "avg_confidence": 0.89,
        },
        "graph_coverage": {
            "nodes": 234,
            "relationships": 891,
            "alert_types_modeled": 4,
            "patterns_learned": 127,
        },
        "timestamp": datetime.now().isoformat(),
    }
