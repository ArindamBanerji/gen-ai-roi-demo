"""
SIM-3a: Expanded simulation alert pool — 5 categories, 20 alerts.

Categories and their GAE factor signatures:
  credential_access   — TravelMatchFactor HIGH, TimeAnomaly HIGH, DeviceTrust LOW
  threat_intel_match  — ThreatIntelFactor HIGH, AssetCriticality CRITICAL
  lateral_movement    — DeviceTrust LOW, AssetCriticality CRITICAL, TimeAnomaly HIGH
  data_exfiltration   — AssetCriticality+DataClass HIGH, TimeAnomaly HIGH
  insider_threat      — DeviceTrust HIGH (trusted insider paradox), AssetCriticality HIGH

Oracle success rates reflect how reliably GAE selects the optimal action per category.
"""
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Category metadata
# ---------------------------------------------------------------------------

ALERT_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "credential_access": {
        "display":             "Credential Access / Travel Login",
        "oracle_success_rate": 0.75,
        "attack_technique":    "T1078 - Valid Accounts",
        "alert_type":          "anomalous_login",
        # Expert-defined optimal action for this category (ground truth).
        # Credential access with confirmed travel context → suppress (travel FP).
        "ground_truth_action": "suppress",
    },
    "threat_intel_match": {
        "display":             "Threat Intelligence Match",
        "oracle_success_rate": 0.85,
        "attack_technique":    "T1588 - Obtain Capabilities",
        "alert_type":          "threat_intel_match",
        # Confirmed IOC from authoritative feed → escalate to Tier 2 immediately.
        "ground_truth_action": "escalate",
    },
    "lateral_movement": {
        "display":             "Lateral Movement",
        "oracle_success_rate": 0.65,
        "attack_technique":    "T1021 - Remote Services",
        "alert_type":          "privilege_escalation",
        # Critical server lateral movement → escalate (highest priority).
        "ground_truth_action": "escalate",
    },
    "data_exfiltration": {
        "display":             "Data Exfiltration",
        "oracle_success_rate": 0.70,
        "attack_technique":    "T1048 - Exfiltration Over Alternative Protocol",
        "alert_type":          "data_exfil",
        # Active data loss → escalate immediately.
        "ground_truth_action": "escalate",
    },
    "insider_threat": {
        "display":             "Insider Threat",
        "oracle_success_rate": 0.55,
        "attack_technique":    "T1078.004 - Valid Accounts: Cloud Accounts",
        "alert_type":          "insider_threat",
        # Trusted insider: cannot escalate without evidence; investigate first.
        "ground_truth_action": "investigate",
    },
}


# ---------------------------------------------------------------------------
# Individual category pools (4 alerts each)
# Fields required by FactorComputers:
#   TravelMatchFactor     → user_id, source_location
#   TimeAnomalyFactor     → business_hours_login, weekend_login
#   DeviceTrustFactor     → mfa_completed, device_fingerprint_match, vpn_provider
#   AssetCriticality/TI   → graph-based; seeded by seed_simulation_alerts()
# ---------------------------------------------------------------------------

_CA: List[Dict[str, Any]] = [
    # credential_access: travel login anomaly — TravelRecord seeded in Neo4j
    {
        "alert_id": "SIM-CA-001", "id": "SIM-CA-001",
        "alert_type": "anomalous_login", "category": "credential_access",
        "user_id": "sim-ca-user1@company.com", "source_location": "Tokyo",
        "business_hours_login": False, "weekend_login": False,
        "mfa_completed": False,  "device_fingerprint_match": False,
        "vpn_provider": None,
    },
    {
        "alert_id": "SIM-CA-002", "id": "SIM-CA-002",
        "alert_type": "anomalous_login", "category": "credential_access",
        "user_id": "sim-ca-user2@company.com", "source_location": "Berlin",
        "business_hours_login": False, "weekend_login": True,
        "mfa_completed": False,  "device_fingerprint_match": False,
        "vpn_provider": "hotel-vpn",
    },
    {
        "alert_id": "SIM-CA-003", "id": "SIM-CA-003",
        "alert_type": "anomalous_login", "category": "credential_access",
        "user_id": "sim-ca-user1@company.com", "source_location": "Tokyo",
        "business_hours_login": False, "weekend_login": False,
        "mfa_completed": True,  "device_fingerprint_match": False,
        "vpn_provider": "hotel-vpn",
    },
    {
        "alert_id": "SIM-CA-004", "id": "SIM-CA-004",
        "alert_type": "anomalous_login", "category": "credential_access",
        "user_id": "sim-ca-user2@company.com", "source_location": "Berlin",
        "business_hours_login": False, "weekend_login": True,
        "mfa_completed": False,  "device_fingerprint_match": True,
        "vpn_provider": None,
    },
]

_TI: List[Dict[str, Any]] = [
    # threat_intel_match: ThreatIntel nodes + ASSOCIATED_WITH seeded in Neo4j
    {
        "alert_id": "SIM-TI-001", "id": "SIM-TI-001",
        "alert_type": "threat_intel_match", "category": "threat_intel_match",
        "user_id": "sim-ti-user@company.com", "source_location": "External",
        "business_hours_login": True,  "weekend_login": False,
        "mfa_completed": True,  "device_fingerprint_match": True,
        "vpn_provider": "corporate-vpn",
    },
    {
        "alert_id": "SIM-TI-002", "id": "SIM-TI-002",
        "alert_type": "threat_intel_match", "category": "threat_intel_match",
        "user_id": "sim-ti-user@company.com", "source_location": "External",
        "business_hours_login": True,  "weekend_login": False,
        "mfa_completed": False, "device_fingerprint_match": True,
        "vpn_provider": None,
    },
    {
        "alert_id": "SIM-TI-003", "id": "SIM-TI-003",
        "alert_type": "threat_intel_match", "category": "threat_intel_match",
        "user_id": "sim-ti-user@company.com", "source_location": "External",
        "business_hours_login": True,  "weekend_login": False,
        "mfa_completed": True,  "device_fingerprint_match": True,
        "vpn_provider": "corporate-vpn",
    },
    {
        "alert_id": "SIM-TI-004", "id": "SIM-TI-004",
        "alert_type": "threat_intel_match", "category": "threat_intel_match",
        "user_id": "sim-ti-user@company.com", "source_location": "External",
        "business_hours_login": False, "weekend_login": True,
        "mfa_completed": True,  "device_fingerprint_match": True,
        "vpn_provider": "corporate-vpn",
    },
]

_LM: List[Dict[str, Any]] = [
    # lateral_movement: untrusted service account, critical server, off-hours
    {
        "alert_id": "SIM-LM-001", "id": "SIM-LM-001",
        "alert_type": "privilege_escalation", "category": "lateral_movement",
        "user_id": "sim-lm-svc@internal", "source_location": "Internal",
        "business_hours_login": False, "weekend_login": False,
        "mfa_completed": False,  "device_fingerprint_match": False,
        "vpn_provider": None,
    },
    {
        "alert_id": "SIM-LM-002", "id": "SIM-LM-002",
        "alert_type": "privilege_escalation", "category": "lateral_movement",
        "user_id": "sim-lm-svc@internal", "source_location": "Internal",
        "business_hours_login": False, "weekend_login": True,
        "mfa_completed": False,  "device_fingerprint_match": False,
        "vpn_provider": None,
    },
    {
        "alert_id": "SIM-LM-003", "id": "SIM-LM-003",
        "alert_type": "privilege_escalation", "category": "lateral_movement",
        "user_id": "sim-lm-svc@internal", "source_location": "Internal",
        "business_hours_login": False, "weekend_login": False,
        "mfa_completed": False,  "device_fingerprint_match": True,
        "vpn_provider": None,
    },
    {
        "alert_id": "SIM-LM-004", "id": "SIM-LM-004",
        "alert_type": "privilege_escalation", "category": "lateral_movement",
        "user_id": "sim-lm-svc@internal", "source_location": "Internal",
        "business_hours_login": True,  "weekend_login": False,
        "mfa_completed": False,  "device_fingerprint_match": False,
        "vpn_provider": None,
    },
]

_DE: List[Dict[str, Any]] = [
    # data_exfiltration: critical asset with PII DataClass, off-hours / weekend
    {
        "alert_id": "SIM-DE-001", "id": "SIM-DE-001",
        "alert_type": "data_exfil", "category": "data_exfiltration",
        "user_id": "sim-de-user@company.com", "source_location": "External",
        "business_hours_login": False, "weekend_login": True,
        "mfa_completed": False,  "device_fingerprint_match": False,
        "vpn_provider": None,
    },
    {
        "alert_id": "SIM-DE-002", "id": "SIM-DE-002",
        "alert_type": "data_exfil", "category": "data_exfiltration",
        "user_id": "sim-de-user@company.com", "source_location": "External",
        "business_hours_login": False, "weekend_login": False,
        "mfa_completed": False,  "device_fingerprint_match": False,
        "vpn_provider": None,
    },
    {
        "alert_id": "SIM-DE-003", "id": "SIM-DE-003",
        "alert_type": "data_exfil", "category": "data_exfiltration",
        "user_id": "sim-de-user@company.com", "source_location": "External",
        "business_hours_login": False, "weekend_login": True,
        "mfa_completed": True,   "device_fingerprint_match": False,
        "vpn_provider": None,
    },
    {
        "alert_id": "SIM-DE-004", "id": "SIM-DE-004",
        "alert_type": "data_exfil", "category": "data_exfiltration",
        "user_id": "sim-de-user@company.com", "source_location": "External",
        "business_hours_login": False, "weekend_login": False,
        "mfa_completed": False,  "device_fingerprint_match": True,
        "vpn_provider": None,
    },
]

_IT: List[Dict[str, Any]] = [
    # insider_threat: trusted insider paradox — all signals look benign
    {
        "alert_id": "SIM-IT-001", "id": "SIM-IT-001",
        "alert_type": "insider_threat", "category": "insider_threat",
        "user_id": "sim-it-user@company.com", "source_location": "Office",
        "business_hours_login": True,  "weekend_login": False,
        "mfa_completed": True,  "device_fingerprint_match": True,
        "vpn_provider": "corporate-vpn",
    },
    {
        "alert_id": "SIM-IT-002", "id": "SIM-IT-002",
        "alert_type": "insider_threat", "category": "insider_threat",
        "user_id": "sim-it-user@company.com", "source_location": "Office",
        "business_hours_login": True,  "weekend_login": False,
        "mfa_completed": True,  "device_fingerprint_match": True,
        "vpn_provider": "corporate-vpn",
    },
    {
        "alert_id": "SIM-IT-003", "id": "SIM-IT-003",
        "alert_type": "insider_threat", "category": "insider_threat",
        "user_id": "sim-it-user@company.com", "source_location": "Office",
        "business_hours_login": True,  "weekend_login": False,
        "mfa_completed": True,  "device_fingerprint_match": True,
        "vpn_provider": "corporate-vpn",
    },
    {
        "alert_id": "SIM-IT-004", "id": "SIM-IT-004",
        "alert_type": "insider_threat", "category": "insider_threat",
        "user_id": "sim-it-user@company.com", "source_location": "Office",
        "business_hours_login": True,  "weekend_login": False,
        "mfa_completed": True,  "device_fingerprint_match": True,
        "vpn_provider": "corporate-vpn",
    },
]

# Interleaved: one per category per round → 5 categories × 4 rounds = 20 alerts.
# Round-robin at step % 20 cycles credential_access → threat_intel_match →
# lateral_movement → data_exfiltration → insider_threat → repeat, advancing
# within each category on each full cycle.
# Each alert is enriched with ground_truth_action from ALERT_CATEGORIES.
_CATEGORY_ORDER = [
    ("credential_access",  _CA),
    ("threat_intel_match", _TI),
    ("lateral_movement",   _LM),
    ("data_exfiltration",  _DE),
    ("insider_threat",     _IT),
]
ALERT_POOL: List[Dict[str, Any]] = []
for _i in range(4):
    for _cat_name, _cat_list in _CATEGORY_ORDER:
        _entry = dict(_cat_list[_i])
        _entry["ground_truth_action"] = ALERT_CATEGORIES[_cat_name]["ground_truth_action"]
        ALERT_POOL.append(_entry)


# ---------------------------------------------------------------------------
# Public accessor
# ---------------------------------------------------------------------------

def get_alert_pool() -> List[Dict[str, Any]]:
    """Return the canonical simulation alert pool (20 alerts, 4 per category)."""
    return list(ALERT_POOL)


# ---------------------------------------------------------------------------
# Neo4j seed function
# ---------------------------------------------------------------------------

async def seed_simulation_alerts() -> None:
    """
    Create simulation alert graph entities in Neo4j.

    Called from seed_neo4j.seed_data() AFTER the main corpus and GAE factor
    data are seeded.  Expects neo4j_client to be already connected.

    Creates per category:
      credential_access  → User + TravelRecord + HAS_TRAVEL, Asset, Alert nodes
      threat_intel_match → User + ThreatIntel + ASSOCIATED_WITH, Asset, Alert nodes
      lateral_movement   → User (service account), Asset (CRITICAL server), Alert nodes
      data_exfiltration  → User, Asset + DataClass + STORES (PII), Alert nodes
      insider_threat     → User, Asset + DataClass + STORES (RESTRICTED), Alert nodes

    All Alert nodes include the properties read by TimeAnomalyFactor and
    DeviceTrustFactor directly (business_hours_login, weekend_login,
    mfa_completed, device_fingerprint_match, vpn_provider).
    """
    from app.db.neo4j import neo4j_client

    print("\n[SIM-3a] Seeding simulation alerts (20 alerts, 5 categories)...")

    # -----------------------------------------------------------------------
    # Users
    # -----------------------------------------------------------------------
    await neo4j_client.run_query("""
        MERGE (u:User {id: 'sim-ca-user1@company.com'})
        SET u.name = 'SIM CA User 1', u.department = 'Finance',
            u.title = 'Director', u.risk_score = 0.3, u.is_privileged = true
    """)
    await neo4j_client.run_query("""
        MERGE (u:User {id: 'sim-ca-user2@company.com'})
        SET u.name = 'SIM CA User 2', u.department = 'Legal',
            u.title = 'Counsel', u.risk_score = 0.25, u.is_privileged = false
    """)
    await neo4j_client.run_query("""
        MERGE (u:User {id: 'sim-ti-user@company.com'})
        SET u.name = 'SIM TI User', u.department = 'Engineering',
            u.title = 'Developer', u.risk_score = 0.35, u.is_privileged = false
    """)
    await neo4j_client.run_query("""
        MERGE (u:User {id: 'sim-lm-svc@internal'})
        SET u.name = 'SIM LM Service Account', u.department = 'IT',
            u.title = 'Service Account', u.risk_score = 0.6, u.is_privileged = true
    """)
    await neo4j_client.run_query("""
        MERGE (u:User {id: 'sim-de-user@company.com'})
        SET u.name = 'SIM DE User', u.department = 'Data Science',
            u.title = 'Analyst', u.risk_score = 0.45, u.is_privileged = false
    """)
    await neo4j_client.run_query("""
        MERGE (u:User {id: 'sim-it-user@company.com'})
        SET u.name = 'SIM IT User', u.department = 'HR',
            u.title = 'Manager', u.risk_score = 0.5, u.is_privileged = false
    """)
    print("  [SIM-3a] Users created (6)")

    # -----------------------------------------------------------------------
    # Assets
    # -----------------------------------------------------------------------
    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'SIM-ASSET-CA-01'})
        SET a.hostname = 'SIM-ASSET-CA-01', a.type = 'endpoint',
            a.criticality = 'high', a.business_unit = 'Finance',
            a.os = 'Windows 11', a.owner_id = 'sim-ca-user1@company.com'
    """)
    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'SIM-ASSET-TI-01'})
        SET a.hostname = 'SIM-ASSET-TI-01', a.type = 'server',
            a.criticality = 'critical', a.business_unit = 'Engineering',
            a.os = 'Ubuntu 22.04', a.owner_id = 'sim-ti-user@company.com'
    """)
    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'SIM-ASSET-LM-01'})
        SET a.hostname = 'SIM-ASSET-LM-01', a.type = 'server',
            a.criticality = 'critical', a.business_unit = 'IT',
            a.os = 'Ubuntu 22.04', a.owner_id = 'sim-lm-svc@internal'
    """)
    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'SIM-ASSET-DE-01'})
        SET a.hostname = 'SIM-ASSET-DE-01', a.type = 'server',
            a.criticality = 'critical', a.business_unit = 'Data Science',
            a.os = 'Ubuntu 22.04', a.owner_id = 'sim-de-user@company.com'
    """)
    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'SIM-ASSET-IT-01'})
        SET a.hostname = 'SIM-ASSET-IT-01', a.type = 'server',
            a.criticality = 'high', a.business_unit = 'HR',
            a.os = 'Windows Server 2022', a.owner_id = 'sim-it-user@company.com'
    """)
    print("  [SIM-3a] Assets created (5)")

    # -----------------------------------------------------------------------
    # Alert nodes — credential_access (SIM-CA-001..004)
    # alert_type = 'anomalous_login' (existing AlertType node)
    # -----------------------------------------------------------------------
    ca_alerts = [
        ("SIM-CA-001", "sim-ca-user1@company.com", "SIM-ASSET-CA-01",
         "103.20.50.11", "Tokyo",   False, False, False, "T1078"),
        ("SIM-CA-002", "sim-ca-user2@company.com", "SIM-ASSET-CA-01",
         "195.144.20.77", "Berlin", False, True,  False, "T1078"),
        ("SIM-CA-003", "sim-ca-user1@company.com", "SIM-ASSET-CA-01",
         "103.20.50.12", "Tokyo",   False, False, True,  "T1078"),
        ("SIM-CA-004", "sim-ca-user2@company.com", "SIM-ASSET-CA-01",
         "195.144.20.78", "Berlin", False, True,  False, "T1078"),
    ]
    for (aid, uid, asset_id, src_ip, location,
         mfa, fingerprint, weekend, technique) in ca_alerts:
        await neo4j_client.run_query("""
            MERGE (alert:Alert {id: $id})
            SET alert.alert_type             = 'anomalous_login',
                alert.severity               = 'high',
                alert.source_ip              = $source_ip,
                alert.source_location        = $location,
                alert.timestamp              = datetime(),
                alert.description            = 'Login from travel destination at unusual time',
                alert.asset_id               = $asset_id,
                alert.user_id                = $uid,
                alert.status                 = 'pending',
                alert.mfa_completed          = $mfa,
                alert.device_fingerprint_match = $fingerprint,
                alert.business_hours_login   = false,
                alert.weekend_login          = $weekend,
                alert.mitre_technique        = $technique,
                alert.mitre_tactic           = 'Initial Access',
                alert.demo_priority          = 3
            WITH alert
            MATCH (asset:Asset {id: $asset_id})
            MATCH (user:User  {id: $uid})
            MERGE (alert)-[:DETECTED_ON]->(asset)
            MERGE (alert)-[:INVOLVES]->(user)
        """, {
            "id": aid, "uid": uid, "asset_id": asset_id,
            "source_ip": src_ip, "location": location,
            "mfa": mfa, "fingerprint": fingerprint,
            "weekend": weekend, "technique": technique,
        })
    print("  [SIM-3a] credential_access alerts created (SIM-CA-001..004)")

    # -----------------------------------------------------------------------
    # Alert nodes — threat_intel_match (SIM-TI-001..004)
    # -----------------------------------------------------------------------
    ti_alerts = [
        ("SIM-TI-001", True,  True,  False),
        ("SIM-TI-002", False, True,  False),
        ("SIM-TI-003", True,  True,  False),
        ("SIM-TI-004", True,  True,  True),
    ]
    for (aid, mfa, fingerprint, weekend) in ti_alerts:
        await neo4j_client.run_query("""
            MERGE (alert:Alert {id: $id})
            SET alert.alert_type             = 'threat_intel_match',
                alert.severity               = 'critical',
                alert.source_ip              = '198.51.100.77',
                alert.source_location        = 'External',
                alert.timestamp              = datetime(),
                alert.description            = 'Indicator matches active APT threat feed',
                alert.asset_id               = 'SIM-ASSET-TI-01',
                alert.user_id                = 'sim-ti-user@company.com',
                alert.status                 = 'pending',
                alert.mfa_completed          = $mfa,
                alert.device_fingerprint_match = $fingerprint,
                alert.business_hours_login   = true,
                alert.weekend_login          = $weekend,
                alert.mitre_technique        = 'T1566',
                alert.mitre_tactic           = 'Initial Access',
                alert.demo_priority          = 3
            WITH alert
            MATCH (asset:Asset {id: 'SIM-ASSET-TI-01'})
            MATCH (user:User   {id: 'sim-ti-user@company.com'})
            MERGE (alert)-[:DETECTED_ON]->(asset)
            MERGE (alert)-[:INVOLVES]->(user)
        """, {"id": aid, "mfa": mfa, "fingerprint": fingerprint, "weekend": weekend})
    print("  [SIM-3a] threat_intel_match alerts created (SIM-TI-001..004)")

    # -----------------------------------------------------------------------
    # Alert nodes — lateral_movement (SIM-LM-001..004)
    # -----------------------------------------------------------------------
    lm_alerts = [
        ("SIM-LM-001", False, False, False),
        ("SIM-LM-002", False, False, True),
        ("SIM-LM-003", False, True,  False),
        ("SIM-LM-004", False, False, False),
    ]
    for (aid, mfa, fingerprint, weekend) in lm_alerts:
        await neo4j_client.run_query("""
            MERGE (alert:Alert {id: $id})
            SET alert.alert_type             = 'privilege_escalation',
                alert.severity               = 'critical',
                alert.source_ip              = '10.0.5.99',
                alert.source_location        = 'Internal',
                alert.timestamp              = datetime(),
                alert.description            = 'Service account lateral movement on critical server',
                alert.asset_id               = 'SIM-ASSET-LM-01',
                alert.user_id                = 'sim-lm-svc@internal',
                alert.status                 = 'pending',
                alert.mfa_completed          = $mfa,
                alert.device_fingerprint_match = $fingerprint,
                alert.business_hours_login   = false,
                alert.weekend_login          = $weekend,
                alert.mitre_technique        = 'T1021',
                alert.mitre_tactic           = 'Lateral Movement',
                alert.demo_priority          = 3
            WITH alert
            MATCH (asset:Asset {id: 'SIM-ASSET-LM-01'})
            MATCH (user:User   {id: 'sim-lm-svc@internal'})
            MERGE (alert)-[:DETECTED_ON]->(asset)
            MERGE (alert)-[:INVOLVES]->(user)
        """, {"id": aid, "mfa": mfa, "fingerprint": fingerprint, "weekend": weekend})
    print("  [SIM-3a] lateral_movement alerts created (SIM-LM-001..004)")

    # -----------------------------------------------------------------------
    # Alert nodes — data_exfiltration (SIM-DE-001..004)
    # -----------------------------------------------------------------------
    de_alerts = [
        ("SIM-DE-001", False, False, True),
        ("SIM-DE-002", False, False, False),
        ("SIM-DE-003", True,  False, True),
        ("SIM-DE-004", False, True,  False),
    ]
    for (aid, mfa, fingerprint, weekend) in de_alerts:
        await neo4j_client.run_query("""
            MERGE (alert:Alert {id: $id})
            SET alert.alert_type             = 'data_exfil',
                alert.severity               = 'critical',
                alert.source_ip              = '10.0.4.33',
                alert.source_location        = 'External',
                alert.timestamp              = datetime(),
                alert.description            = 'Large data upload to external destination after hours',
                alert.asset_id               = 'SIM-ASSET-DE-01',
                alert.user_id                = 'sim-de-user@company.com',
                alert.status                 = 'pending',
                alert.mfa_completed          = $mfa,
                alert.device_fingerprint_match = $fingerprint,
                alert.business_hours_login   = false,
                alert.weekend_login          = $weekend,
                alert.mitre_technique        = 'T1048',
                alert.mitre_tactic           = 'Exfiltration',
                alert.demo_priority          = 3
            WITH alert
            MATCH (asset:Asset {id: 'SIM-ASSET-DE-01'})
            MATCH (user:User   {id: 'sim-de-user@company.com'})
            MERGE (alert)-[:DETECTED_ON]->(asset)
            MERGE (alert)-[:INVOLVES]->(user)
        """, {"id": aid, "mfa": mfa, "fingerprint": fingerprint, "weekend": weekend})
    print("  [SIM-3a] data_exfiltration alerts created (SIM-DE-001..004)")

    # -----------------------------------------------------------------------
    # Alert nodes — insider_threat (SIM-IT-001..004)
    # All signals look benign (trusted insider paradox)
    # -----------------------------------------------------------------------
    for i in range(1, 5):
        await neo4j_client.run_query("""
            MERGE (alert:Alert {id: $id})
            SET alert.alert_type             = 'insider_threat',
                alert.severity               = 'high',
                alert.source_ip              = '10.0.2.55',
                alert.source_location        = 'Office',
                alert.timestamp              = datetime(),
                alert.description            = 'Bulk data collection by trusted employee',
                alert.asset_id               = 'SIM-ASSET-IT-01',
                alert.user_id                = 'sim-it-user@company.com',
                alert.status                 = 'pending',
                alert.mfa_completed          = true,
                alert.device_fingerprint_match = true,
                alert.business_hours_login   = true,
                alert.weekend_login          = false,
                alert.mitre_technique        = 'T1078.004',
                alert.mitre_tactic           = 'Persistence',
                alert.demo_priority          = 3
            WITH alert
            MATCH (asset:Asset {id: 'SIM-ASSET-IT-01'})
            MATCH (user:User   {id: 'sim-it-user@company.com'})
            MERGE (alert)-[:DETECTED_ON]->(asset)
            MERGE (alert)-[:INVOLVES]->(user)
        """, {"id": f"SIM-IT-00{i}"})
    print("  [SIM-3a] insider_threat alerts created (SIM-IT-001..004)")

    # -----------------------------------------------------------------------
    # TravelRecord nodes — required by TravelMatchFactor [:HAS_TRAVEL]
    # (credential_access category)
    # -----------------------------------------------------------------------
    await neo4j_client.run_query("""
        MERGE (u:User {id: 'sim-ca-user1@company.com'})
        MERGE (t:TravelRecord {id: 'TR-SIM-CA-USER1-TYO'})
        SET t.destination  = 'Tokyo',
            t.start_date   = date('2026-02-20'),
            t.end_date     = date('2026-03-05'),
            t.vpn_expected = ['NTT', 'hotel-vpn']
        MERGE (u)-[:HAS_TRAVEL]->(t)
    """)
    await neo4j_client.run_query("""
        MERGE (u:User {id: 'sim-ca-user2@company.com'})
        MERGE (t:TravelRecord {id: 'TR-SIM-CA-USER2-BER'})
        SET t.destination  = 'Berlin',
            t.start_date   = date('2026-02-22'),
            t.end_date     = date('2026-03-02'),
            t.vpn_expected = ['hotel-vpn']
        MERGE (u)-[:HAS_TRAVEL]->(t)
    """)
    print("  [SIM-3a] TravelRecord nodes: sim-ca-user1(Tokyo), sim-ca-user2(Berlin)")

    # -----------------------------------------------------------------------
    # ThreatIntel nodes — required by ThreatIntelEnrichmentFactor [:ASSOCIATED_WITH]
    # Each TI alert gets 2 corroborating sources for a strong factor signal.
    # -----------------------------------------------------------------------
    ti_iocs = [
        ("SIM-TI-001", "TI-SIM-APT-001", "TI-SIM-APT-002"),
        ("SIM-TI-002", "TI-SIM-APT-003", "TI-SIM-APT-004"),
        ("SIM-TI-003", "TI-SIM-APT-005", "TI-SIM-APT-006"),
        ("SIM-TI-004", "TI-SIM-APT-007", "TI-SIM-APT-008"),
    ]
    for (alert_id, ti1_id, ti2_id) in ti_iocs:
        await neo4j_client.run_query("""
            MERGE (ti:ThreatIntel {id: $ti1_id})
            SET ti.name      = 'SIM APT Campaign Indicator',
                ti.severity  = 'critical',
                ti.source    = 'cisa_kev',
                ti.ioc_type  = 'domain',
                ti.ioc_value = 'sim-apt-domain.evil'
            WITH ti
            MATCH (a:Alert {id: $alert_id})
            MERGE (ti)-[:ASSOCIATED_WITH]->(a)
        """, {"ti1_id": ti1_id, "alert_id": alert_id})
        await neo4j_client.run_query("""
            MERGE (ti:ThreatIntel {id: $ti2_id})
            SET ti.name      = 'SIM APT IP Indicator',
                ti.severity  = 'high',
                ti.source    = 'greynoise',
                ti.ioc_type  = 'ip',
                ti.ioc_value = '198.51.100.77'
            WITH ti
            MATCH (a:Alert {id: $alert_id})
            MERGE (ti)-[:ASSOCIATED_WITH]->(a)
        """, {"ti2_id": ti2_id, "alert_id": alert_id})
    print("  [SIM-3a] ThreatIntel nodes + [:ASSOCIATED_WITH]: SIM-TI-001..004 (2 sources each)")

    # -----------------------------------------------------------------------
    # DataClass nodes — required by AssetCriticalityFactor [:STORES]
    # data_exfiltration → PII (adds +0.1 sensitivity bonus on top of CRITICAL)
    # insider_threat    → RESTRICTED (adds sensitivity bonus on top of HIGH)
    # -----------------------------------------------------------------------
    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'SIM-ASSET-DE-01'})
        MERGE (dc:DataClass {id: 'DC-SIM-DE-PII'})
        SET dc.name           = 'Customer PII — SIM',
            dc.sensitivity    = 'PII',
            dc.classification = 'RESTRICTED'
        MERGE (a)-[:STORES]->(dc)
    """)
    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'SIM-ASSET-IT-01'})
        MERGE (dc:DataClass {id: 'DC-SIM-IT-HR'})
        SET dc.name           = 'HR Records — SIM',
            dc.sensitivity    = 'RESTRICTED',
            dc.classification = 'CONFIDENTIAL'
        MERGE (a)-[:STORES]->(dc)
    """)
    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'SIM-ASSET-CA-01'})
        MERGE (dc:DataClass {id: 'DC-SIM-CA-FINANCE'})
        SET dc.name           = 'Financial Reports — SIM',
            dc.sensitivity    = 'RESTRICTED',
            dc.classification = 'CONFIDENTIAL'
        MERGE (a)-[:STORES]->(dc)
    """)
    print("  [SIM-3a] DataClass nodes + [:STORES]: SIM-ASSET-DE-01(PII), SIM-ASSET-IT-01(RESTRICTED), SIM-ASSET-CA-01(RESTRICTED)")

    # -----------------------------------------------------------------------
    # SIM-FIX-2: AlertType nodes — required by get_security_context()
    #
    # anomalous_login, threat_intel_match, and privilege_escalation are
    # already created by the main seed_neo4j.py corpus.  Only data_exfil
    # and insider_threat are new; the others use MERGE for safety.
    # -----------------------------------------------------------------------
    for at_id, at_name, at_desc, at_severity, at_mitre in [
        ('anomalous_login',   'Anomalous Login',
         'Login from unusual location or device',           'medium',   'T1078'),
        ('threat_intel_match','Threat Intel Match',
         'Indicator matches active threat intelligence feed','high',    'T1566'),
        ('privilege_escalation','Privilege Escalation',
         'Unauthorized elevation of user privileges',       'critical', 'T1098'),
        ('data_exfil',        'Data Exfiltration',
         'Unauthorized data transfer to external destination','critical','T1048'),
        ('insider_threat',    'Insider Threat',
         'Suspicious bulk data access by trusted internal user','high',  'T1078.004'),
    ]:
        await neo4j_client.run_query("""
            MERGE (at:AlertType {id: $id})
            SET at.name            = $name,
                at.description     = $desc,
                at.severity        = $severity,
                at.mitre_technique = $mitre
        """, {"id": at_id, "name": at_name, "desc": at_desc,
              "severity": at_severity, "mitre": at_mitre})
    print("  [SIM-FIX-2] AlertType nodes merged (5 types)")

    # Playbooks for the two new AlertTypes (optional — enriches graph viz)
    await neo4j_client.run_query("""
        MERGE (pb:Playbook {id: 'PB-EXFIL-001'})
        SET pb.name        = 'Data Exfiltration Response',
            pb.description = 'Block egress, preserve evidence, escalate to IR',
            pb.steps       = ['Block egress', 'Preserve logs', 'Escalate to IR', 'Notify DPO'],
            pb.auto_actions = ['block_egress'],
            pb.sla_minutes  = 10
        WITH pb
        MATCH (at:AlertType {id: 'data_exfil'})
        MERGE (at)-[:HANDLED_BY]->(pb)
    """)
    await neo4j_client.run_query("""
        MERGE (pb:Playbook {id: 'PB-INSIDER-001'})
        SET pb.name        = 'Insider Threat Investigation',
            pb.description = 'Covert monitoring, collect evidence, escalate to HR and Legal',
            pb.steps       = ['Enable covert monitoring', 'Collect evidence', 'Escalate to HR', 'Brief Legal'],
            pb.auto_actions = [],
            pb.sla_minutes  = 60
        WITH pb
        MATCH (at:AlertType {id: 'insider_threat'})
        MERGE (at)-[:HANDLED_BY]->(pb)
    """)
    print("  [SIM-FIX-2] Playbooks merged: PB-EXFIL-001, PB-INSIDER-001")

    # -----------------------------------------------------------------------
    # SIM-FIX-2: [:CLASSIFIED_AS] edges — the missing link
    #
    # get_security_context() uses a mandatory MATCH on this relationship.
    # MERGE is idempotent; re-running seed_neo4j.py will not create duplicates.
    # -----------------------------------------------------------------------
    for ids, type_id in [
        (['SIM-CA-001', 'SIM-CA-002', 'SIM-CA-003', 'SIM-CA-004'], 'anomalous_login'),
        (['SIM-TI-001', 'SIM-TI-002', 'SIM-TI-003', 'SIM-TI-004'], 'threat_intel_match'),
        (['SIM-LM-001', 'SIM-LM-002', 'SIM-LM-003', 'SIM-LM-004'], 'privilege_escalation'),
        (['SIM-DE-001', 'SIM-DE-002', 'SIM-DE-003', 'SIM-DE-004'], 'data_exfil'),
        (['SIM-IT-001', 'SIM-IT-002', 'SIM-IT-003', 'SIM-IT-004'], 'insider_threat'),
    ]:
        await neo4j_client.run_query("""
            MATCH (at:AlertType {id: $type_id})
            WITH at
            UNWIND $ids AS aid
            MATCH (alert:Alert {id: aid})
            MERGE (alert)-[:CLASSIFIED_AS]->(at)
        """, {"type_id": type_id, "ids": ids})
    print("  [SIM-FIX-2] [:CLASSIFIED_AS] edges merged for all 20 SIM alerts")

    print("[SIM-3a] Simulation alert seeding complete — 20 alerts across 5 categories.")
