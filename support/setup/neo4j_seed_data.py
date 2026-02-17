# Neo4j Seed Data Reference
# Copy this file to: C:\Projects\gen-ai-roi-demo\support\setup\neo4j_seed_data.py
# Claude Code should use this as reference to create backend/app/services/seed_neo4j.py

"""
This file contains the canonical seed data for the SOC Copilot Demo.
Use this to create a proper seed script in the backend.
"""

# =============================================================================
# ASSETS (5)
# =============================================================================
assets = [
    {
        "asset_id": "LAPTOP-JSMITH",
        "hostname": "LAPTOP-JSMITH",
        "type": "endpoint",
        "os": "Windows 11 Enterprise",
        "criticality": "high",
        "business_unit": "Finance",
        "owner_id": "jsmith@company.com",
    },
    {
        "asset_id": "SRV-DB-PROD-01",
        "hostname": "SRV-DB-PROD-01",
        "type": "server",
        "os": "RHEL 8.6",
        "criticality": "critical",
        "business_unit": "IT",
        "owner_id": "db_admin@company.com",
    },
    {
        "asset_id": "LAPTOP-MCHEN",
        "hostname": "LAPTOP-MCHEN",
        "type": "endpoint",
        "os": "macOS Sonoma",
        "criticality": "high",
        "business_unit": "Engineering",
        "owner_id": "mchen@company.com",
    },
    {
        "asset_id": "LAPTOP-AGARCIA",
        "hostname": "LAPTOP-AGARCIA",
        "type": "endpoint",
        "os": "macOS Sonoma",
        "criticality": "medium",
        "business_unit": "Engineering",
        "owner_id": "agarcia@company.com",
    },
    {
        "asset_id": "MAIL-GW-01",
        "hostname": "MAIL-GW-01",
        "type": "network",
        "os": "Proofpoint Appliance",
        "criticality": "critical",
        "business_unit": "IT",
        "owner_id": "mail_admin@company.com",
    },
]

# =============================================================================
# USERS (5)
# =============================================================================
users = [
    {
        "user_id": "jsmith@company.com",
        "name": "John Smith",
        "title": "VP Finance",
        "department": "Finance",
        "risk_score": 0.85,
        "is_privileged": True,
    },
    {
        "user_id": "mchen@company.com",
        "name": "Mary Chen",
        "title": "Director Engineering",
        "department": "Engineering",
        "risk_score": 0.72,
        "is_privileged": True,
    },
    {
        "user_id": "agarcia@company.com",
        "name": "Ana Garcia",
        "title": "Senior Developer",
        "department": "Engineering",
        "risk_score": 0.35,
        "is_privileged": False,
    },
    {
        "user_id": "cjohnson@company.com",
        "name": "Chris Johnson",
        "title": "CEO",
        "department": "Executive",
        "risk_score": 0.95,
        "is_privileged": True,
    },
    {
        "user_id": "blee@company.com",
        "name": "Bob Lee",
        "title": "SOC Analyst",
        "department": "Security",
        "risk_score": 0.25,
        "is_privileged": False,
    },
]

# =============================================================================
# ALERT_TYPES (4)
# =============================================================================
alert_types = [
    {"id": "anomalous_login", "name": "Anomalous Login", "severity": "medium", "mitre": "T1078"},
    {"id": "phishing", "name": "Phishing", "severity": "high", "mitre": "T1566"},
    {"id": "malware_detection", "name": "Malware Detection", "severity": "critical", "mitre": "T1204"},
    {"id": "data_exfiltration", "name": "Data Exfiltration", "severity": "high", "mitre": "T1048"},
]

# =============================================================================
# ATTACK_PATTERNS (5) - Key for compounding intelligence
# =============================================================================
patterns = [
    {
        "pattern_id": "PAT-TRAVEL-001",
        "name": "Travel Login False Positive",
        "fp_rate": 0.94,
        "occurrence_count": 127,
        "confidence": 0.91,  # IMPORTANT: Start at 0.91, not 0.92 or higher
    },
    {
        "pattern_id": "PAT-PHISH-KNOWN",
        "name": "Known Phishing Campaign",
        "fp_rate": 0.02,
        "occurrence_count": 89,
        "confidence": 0.96,
    },
    {
        "pattern_id": "PAT-MALWARE-ISOLATE",
        "name": "Standard Malware Isolation",
        "fp_rate": 0.08,
        "occurrence_count": 34,
        "confidence": 0.91,
    },
    {
        "pattern_id": "PAT-VPN-KNOWN",
        "name": "Known VPN Provider",
        "fp_rate": 0.96,
        "occurrence_count": 245,
        "confidence": 0.94,
    },
    {
        "pattern_id": "PAT-LOGIN-NORMAL",
        "name": "Normal Location Login",
        "fp_rate": 0.98,
        "occurrence_count": 2847,
        "confidence": 0.97,
    },
]

# =============================================================================
# PLAYBOOKS (4)
# =============================================================================
playbooks = [
    {"playbook_id": "PB-LOGIN-001", "name": "Anomalous Login Response", "sla_minutes": 15},
    {"playbook_id": "PB-PHISH-001", "name": "Phishing Response", "sla_minutes": 30},
    {"playbook_id": "PB-MALWARE-001", "name": "Malware Response", "sla_minutes": 10},
    {"playbook_id": "PB-DLP-001", "name": "Data Exfiltration Response", "sla_minutes": 5},
]

# =============================================================================
# SLAs (3)
# =============================================================================
slas = [
    {"id": "SLA-CRITICAL", "name": "Critical SLA", "response_time_minutes": 10, "severity": "critical"},
    {"id": "SLA-HIGH", "name": "High SLA", "response_time_minutes": 30, "severity": "high"},
    {"id": "SLA-MEDIUM", "name": "Medium SLA", "response_time_minutes": 60, "severity": "medium"},
]

# =============================================================================
# TRAVEL_CONTEXT (2)
# =============================================================================
travel_records = [
    {
        "travel_id": "TRAVEL-001",
        "user_id": "jsmith@company.com",
        "destination": "Singapore",
        "start_date": "2026-01-28",
        "end_date": "2026-02-05",
    },
    {
        "travel_id": "TRAVEL-002",
        "user_id": "agarcia@company.com",
        "destination": "Denver",
        "start_date": "2026-01-30",
        "end_date": "2026-02-01",
    },
]

# =============================================================================
# ALERTS (5) - All status: 'pending'
# =============================================================================
alerts = [
    {
        "alert_id": "ALERT-7823",
        "alert_type": "anomalous_login",
        "severity": "medium",
        "source": "Splunk",
        "asset_id": "LAPTOP-JSMITH",
        "user_id": "jsmith@company.com",
        "source_location": "Singapore",
        "status": "pending",
        "description": "Login from unusual location: Singapore at 3:47 AM local time",
    },
    {
        "alert_id": "ALERT-7822",
        "alert_type": "phishing",
        "severity": "high",
        "source": "Proofpoint",
        "asset_id": "MAIL-GW-01",
        "user_id": "finance_team@company.com",
        "source_location": "External",
        "status": "pending",
        "description": "Phishing email detected targeting Finance team",
    },
    {
        "alert_id": "ALERT-7821",
        "alert_type": "malware_detection",
        "severity": "critical",
        "source": "CrowdStrike",
        "asset_id": "SRV-DB-PROD-01",
        "user_id": "system",
        "source_location": "Internal",
        "status": "pending",
        "description": "Known malware hash detected on production database server",
    },
    {
        "alert_id": "ALERT-7820",
        "alert_type": "data_exfiltration",
        "severity": "high",
        "source": "DLP",
        "asset_id": "LAPTOP-MCHEN",
        "user_id": "mchen@company.com",
        "source_location": "Internal",
        "status": "pending",
        "description": "Large data transfer to external cloud storage",
    },
    {
        "alert_id": "ALERT-7819",
        "alert_type": "anomalous_login",
        "severity": "low",
        "source": "Splunk",
        "asset_id": "LAPTOP-AGARCIA",
        "user_id": "agarcia@company.com",
        "source_location": "Denver",
        "status": "pending",
        "description": "Login from Denver (user normally in San Francisco)",
    },
]

# =============================================================================
# DECISIONS (5) - Original seed decisions
# =============================================================================
decision_nodes = [
    {
        "id": "DEC-7823",
        "type": "alert_triage",
        "reasoning": "User has active travel to Singapore. VPN from Marriott Hotels matches known provider. Pattern PAT-TRAVEL-001 matched with 127 similar cases.",
        "confidence": 0.92,
        "timestamp": "2026-01-31T03:48:00Z",
        "alert_id": "ALERT-7823",
        "action_taken": "false_positive_close"
    },
    {
        "id": "DEC-7822",
        "type": "alert_triage",
        "reasoning": "Email matches known Q4 phishing campaign. Auto-quarantine executed.",
        "confidence": 0.96,
        "timestamp": "2026-01-31T08:16:00Z",
        "alert_id": "ALERT-7822",
        "action_taken": "auto_remediate"
    },
    {
        "id": "DEC-7821",
        "type": "alert_triage",
        "reasoning": "Malware detected on CRITICAL production database server. Immediate IR escalation required.",
        "confidence": 0.96,
        "timestamp": "2026-01-31T09:31:00Z",
        "alert_id": "ALERT-7821",
        "action_taken": "escalate_incident"
    },
    {
        "id": "DEC-7820",
        "type": "alert_triage",
        "reasoning": "Potential data exfiltration from privileged user. Escalating to IR per policy.",
        "confidence": 0.97,
        "timestamp": "2026-01-31T10:16:00Z",
        "alert_id": "ALERT-7820",
        "action_taken": "escalate_incident"
    },
    {
        "id": "DEC-7819",
        "type": "alert_triage",
        "reasoning": "User Ana Garcia has active travel to Denver. Login location matches travel destination.",
        "confidence": 0.91,
        "timestamp": "2026-01-31T07:31:00Z",
        "alert_id": "ALERT-7819",
        "action_taken": "false_positive_close"
    },
]

# =============================================================================
# DECISION_CONTEXTS (5)
# =============================================================================
context_nodes = [
    {"id": "CTX-7823", "decision_id": "DEC-7823", "patterns_matched": ["PAT-TRAVEL-001"], "nodes_consulted": 47},
    {"id": "CTX-7822", "decision_id": "DEC-7822", "patterns_matched": ["PAT-PHISH-KNOWN"], "nodes_consulted": 23},
    {"id": "CTX-7821", "decision_id": "DEC-7821", "patterns_matched": [], "nodes_consulted": 31},
    {"id": "CTX-7820", "decision_id": "DEC-7820", "patterns_matched": [], "nodes_consulted": 28},
    {"id": "CTX-7819", "decision_id": "DEC-7819", "patterns_matched": ["PAT-TRAVEL-001"], "nodes_consulted": 35},
]

# =============================================================================
# EVOLUTION_EVENTS (3) - THE KEY DIFFERENTIATOR
# =============================================================================
evolution_nodes = [
    {
        "id": "EVO-0891",
        "event_type": "pattern_confidence",
        "triggered_by": "DEC-7823",
        "before_state": '{"confidence": 0.91, "occurrence_count": 126}',
        "after_state": '{"confidence": 0.94, "occurrence_count": 127}',
        "description": "Pattern PAT-TRAVEL-001 confidence increased based on successful false positive close",
        "timestamp": "2026-01-31T03:48:30Z"
    },
    {
        "id": "EVO-0890",
        "event_type": "threshold_adjustment",
        "triggered_by": "DEC-7819",
        "before_state": '{"auto_close_threshold": 0.88}',
        "after_state": '{"auto_close_threshold": 0.90}',
        "description": "Auto-close threshold for travel alerts adjusted based on sustained accuracy",
        "timestamp": "2026-01-31T07:32:00Z"
    },
    {
        "id": "EVO-0889",
        "event_type": "new_pattern",
        "triggered_by": "DEC-7822",
        "before_state": '{}',
        "after_state": '{"pattern_id": "PAT-PHISH-Q1-2026", "confidence": 0.94}',
        "description": "New phishing campaign pattern identified from Q1 2026 campaign",
        "timestamp": "2026-01-31T08:17:00Z"
    },
]

# =============================================================================
# RELATIONSHIPS
# =============================================================================

# User -[:ASSIGNED_TO]-> Asset
user_asset_mappings = [
    ("jsmith@company.com", "LAPTOP-JSMITH"),
    ("mchen@company.com", "LAPTOP-MCHEN"),
    ("agarcia@company.com", "LAPTOP-AGARCIA"),
]

# AlertType -[:HANDLED_BY]-> Playbook
alert_playbook_mappings = [
    ("anomalous_login", "PB-LOGIN-001"),
    ("phishing", "PB-PHISH-001"),
    ("malware_detection", "PB-MALWARE-001"),
    ("data_exfiltration", "PB-DLP-001"),
]

# Asset -[:SUBJECT_TO]-> SLA
asset_sla_mappings = [
    ("LAPTOP-JSMITH", "SLA-HIGH"),
    ("SRV-DB-PROD-01", "SLA-CRITICAL"),
    ("LAPTOP-MCHEN", "SLA-HIGH"),
    ("LAPTOP-AGARCIA", "SLA-MEDIUM"),
    ("MAIL-GW-01", "SLA-CRITICAL"),
]

# Alert -[:MATCHES]-> AttackPattern
alert_pattern_mappings = [
    ("ALERT-7823", "PAT-TRAVEL-001"),
    ("ALERT-7822", "PAT-PHISH-KNOWN"),
    ("ALERT-7821", "PAT-MALWARE-ISOLATE"),
    ("ALERT-7820", "PAT-VPN-KNOWN"),
    ("ALERT-7819", "PAT-LOGIN-NORMAL"),
]

# TRIGGERED_EVOLUTION - THE KEY DIFFERENTIATOR
triggered_evolutions = [
    {"decision_id": "DEC-7823", "evolution_id": "EVO-0891", "impact": "pattern_confidence_increase", "magnitude": 0.03},
    {"decision_id": "DEC-7819", "evolution_id": "EVO-0890", "impact": "threshold_adjustment", "magnitude": 0.02},
    {"decision_id": "DEC-7822", "evolution_id": "EVO-0889", "impact": "new_pattern_created", "magnitude": 1.0},
]

# =============================================================================
# EXPECTED COUNTS AFTER SEEDING
# =============================================================================
# Nodes: ~46
#   - Asset: 5
#   - User: 5
#   - AlertType: 4
#   - AttackPattern: 5
#   - Playbook: 4
#   - SLA: 3
#   - TravelContext: 2
#   - Alert: 5
#   - Decision: 5
#   - DecisionContext: 5
#   - EvolutionEvent: 3
#
# Relationships: ~55+
#   - ASSIGNED_TO: 3
#   - HAS_TRAVEL: 2
#   - HANDLED_BY: 4
#   - SUBJECT_TO: 5
#   - DETECTED_ON: 5 (Alert -> Asset)
#   - INVOLVES: 5 (Alert -> User)
#   - CLASSIFIED_AS: 5 (Alert -> AlertType)
#   - MATCHES: 5 (Alert -> AttackPattern)
#   - FOR_ALERT: 5 (Decision -> Alert)
#   - HAD_CONTEXT: 5 (Decision -> DecisionContext)
#   - TRIGGERED_EVOLUTION: 3 (THE KEY!)
