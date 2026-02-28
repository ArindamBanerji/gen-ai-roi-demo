"""
Seed Neo4j with sample data for SOC Copilot Demo
Run this script to populate the graph with test data for ALERT-7823

Usage:
    python seed_neo4j.py
"""
import asyncio
from dotenv import load_dotenv

# Load .env BEFORE importing neo4j_client (it reads os.getenv at import time)
load_dotenv()

from app.db.neo4j import neo4j_client


async def seed_data():
    """Seed Neo4j with sample security graph data"""

    print("[OK] Connecting to Neo4j...")
    await neo4j_client.connect()

    print("[OK] Clearing existing data...")
    await neo4j_client.run_query("MATCH (n) DETACH DELETE n")

    print("[OK] Creating sample data...")

    # Create Asset nodes
    await neo4j_client.run_query("""
        CREATE (:Asset {
            id: 'LAPTOP-JSMITH',
            hostname: 'LAPTOP-JSMITH',
            type: 'endpoint',
            criticality: 'medium',
            business_unit: 'Finance',
            os: 'Windows 11',
            owner_id: 'jsmith@company.com'
        })
    """)

    # Create User nodes (LOW risk score for demo - travel scenario)
    await neo4j_client.run_query("""
        CREATE (:User {
            id: 'jsmith@company.com',
            name: 'John Smith',
            department: 'Finance',
            title: 'VP Finance',
            risk_score: 0.25,
            is_privileged: true
        })
    """)

    print("  [OK] Created user: John Smith (risk_score: 0.25)")

    # Create TravelContext
    await neo4j_client.run_query("""
        MATCH (user:User {id: 'jsmith@company.com'})
        CREATE (travel:TravelContext {
            id: 'TRAVEL-001',
            user_id: 'jsmith@company.com',
            destination: 'Singapore',
            start_date: date('2026-02-05'),
            end_date: date('2026-02-10'),
            vpn_expected: ['SingTel', 'hotel-vpn']
        })
        CREATE (user)-[:HAS_TRAVEL]->(travel)
    """)

    # Create AlertType
    await neo4j_client.run_query("""
        CREATE (:AlertType {
            id: 'anomalous_login',
            name: 'Anomalous Login',
            description: 'Login from unusual location or device',
            severity: 'medium',
            mitre_technique: 'T1078'
        })
    """)

    # Create AttackPattern
    await neo4j_client.run_query("""
        CREATE (:AttackPattern {
            id: 'PAT-TRAVEL-001',
            name: 'Travel False Positive',
            description: 'Login from expected travel location',
            fp_rate: 0.20,
            occurrence_count: 127,
            confidence: 0.91
        })
    """)

    # Create Playbook
    await neo4j_client.run_query("""
        CREATE (:Playbook {
            id: 'PB-LOGIN-FP',
            name: 'Login False Positive Closure',
            description: 'Auto-close travel-related login alerts',
            steps: ['Verify travel', 'Check VPN', 'Validate MFA', 'Close'],
            auto_actions: ['close_alert', 'update_pattern'],
            sla_minutes: 15
        })
    """)

    # Create SLA
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'LAPTOP-JSMITH'})
        CREATE (sla:SLA {
            id: 'SLA-MEDIUM',
            name: 'Medium Severity SLA',
            response_time_minutes: 30,
            severity: 'medium'
        })
        CREATE (asset)-[:SUBJECT_TO]->(sla)
    """)

    # Create Alert ALERT-7823 (THE DEMO ALERT)
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'LAPTOP-JSMITH'})
        MATCH (user:User {id: 'jsmith@company.com'})
        MATCH (alertType:AlertType {id: 'anomalous_login'})
        MATCH (pattern:AttackPattern {id: 'PAT-TRAVEL-001'})

        CREATE (alert:Alert {
            id: 'ALERT-7823',
            alert_type: 'anomalous_login',
            severity: 'medium',
            source_ip: '103.15.42.88',
            source_location: 'Singapore',
            destination_ip: '10.0.1.50',
            timestamp: datetime('2026-02-06T03:47:00Z'),
            description: 'Login from Singapore at unusual time',
            asset_id: 'LAPTOP-JSMITH',
            user_id: 'jsmith@company.com',
            status: 'pending',
            vpn_provider: 'hotel-vpn',
            mfa_completed: true,
            device_fingerprint_match: true,
            mitre_technique: 'T1078',
            mitre_tactic: 'Initial Access',
            demo_priority: 1
        })

        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
        CREATE (alert)-[:MATCHES]->(pattern)
    """)

    # Create Playbook relationship
    await neo4j_client.run_query("""
        MATCH (alertType:AlertType {id: 'anomalous_login'})
        MATCH (playbook:Playbook {id: 'PB-LOGIN-FP'})
        CREATE (alertType)-[:HANDLED_BY]->(playbook)
    """)

    # Create User->Asset assignment
    await neo4j_client.run_query("""
        MATCH (user:User {id: 'jsmith@company.com'})
        MATCH (asset:Asset {id: 'LAPTOP-JSMITH'})
        CREATE (user)-[:ASSIGNED_TO]->(asset)
    """)

    # ========================================================================
    # Add more alerts for Tab 3 Alert Queue
    # ========================================================================

    print("  [OK] Creating additional alerts for queue...")

    # Create additional users and assets for variety
    await neo4j_client.run_query("""
        CREATE (:User {
            id: 'alee@company.com',
            name: 'Alice Lee',
            department: 'Engineering',
            title: 'Senior Engineer',
            risk_score: 0.15,
            is_privileged: false
        })

        CREATE (:Asset {
            id: 'LAPTOP-ALEE',
            hostname: 'LAPTOP-ALEE',
            type: 'endpoint',
            criticality: 'low',
            business_unit: 'Engineering',
            os: 'MacOS',
            owner_id: 'alee@company.com'
        })

        CREATE (:User {
            id: 'mchen@company.com',
            name: 'Mike Chen',
            department: 'IT',
            title: 'IT Admin',
            risk_score: 0.65,
            is_privileged: true
        })

        CREATE (:Asset {
            id: 'SRV-DB-PROD-01',
            hostname: 'SRV-DB-PROD-01',
            type: 'server',
            criticality: 'critical',
            business_unit: 'IT',
            os: 'Ubuntu 22.04',
            owner_id: 'mchen@company.com'
        })

        CREATE (:User {
            id: 'marychen@company.com',
            name: 'Mary Chen',
            department: 'Engineering',
            title: 'Engineering Lead',
            risk_score: 0.45,
            is_privileged: false
        })

        CREATE (:Asset {
            id: 'LAPTOP-MARYCHEN',
            hostname: 'LAPTOP-MARYCHEN',
            type: 'endpoint',
            criticality: 'medium',
            business_unit: 'Engineering',
            os: 'MacOS',
            owner_id: 'marychen@company.com'
        })
    """)

    # Create phishing alert type
    await neo4j_client.run_query("""
        CREATE (:AlertType {
            id: 'phishing',
            name: 'Phishing Attempt',
            description: 'Suspicious email or link click',
            severity: 'high',
            mitre_technique: 'T1566'
        })
    """)

    # Create PAT-PHISH-KNOWN pattern (for ALERT-7824)
    await neo4j_client.run_query("""
        CREATE (:AttackPattern {
            id: 'PAT-PHISH-KNOWN',
            name: 'Known Phishing Campaign',
            description: 'Recognized phishing campaign with known indicators',
            fp_rate: 0.08,
            occurrence_count: 31,
            confidence: 0.94
        })
    """)

    # Create PhishingCampaign node
    await neo4j_client.run_query("""
        CREATE (:PhishingCampaign {
            id: 'CAMP-2024-0142',
            name: 'Operation DarkHook',
            first_seen: date('2024-11-15'),
            indicators: ['suspicious_sender', 'malicious_url', 'spoofed_domain'],
            threat_actor: 'APT-UNKNOWN',
            target_industries: ['Technology', 'Finance']
        })
    """)

    # Create PB-PHISH-AUTO playbook
    await neo4j_client.run_query("""
        MATCH (alertType:AlertType {id: 'phishing'})
        CREATE (playbook:Playbook {
            id: 'PB-PHISH-AUTO',
            name: 'Phishing Auto-Remediate',
            description: 'Automated response for known phishing campaigns',
            steps: ['Quarantine email', 'Block sender', 'Update signatures', 'Notify user'],
            auto_actions: ['quarantine', 'block_sender'],
            sla_minutes: 10
        })
        CREATE (alertType)-[:HANDLED_BY]->(playbook)
    """)

    # ALERT-7822: Phishing (high severity)
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'LAPTOP-ALEE'})
        MATCH (user:User {id: 'alee@company.com'})
        MATCH (alertType:AlertType {id: 'phishing'})

        CREATE (alert:Alert {
            id: 'ALERT-7822',
            alert_type: 'phishing',
            severity: 'high',
            source_ip: '192.168.1.100',
            source_location: 'San Francisco',
            destination_ip: '45.33.32.156',
            timestamp: datetime('2026-02-06T10:15:00Z'),
            description: 'Suspicious email link clicked',
            asset_id: 'LAPTOP-ALEE',
            user_id: 'alee@company.com',
            status: 'pending',
            mfa_completed: false,
            device_fingerprint_match: true,
            mitre_technique: 'T1566',
            mitre_tactic: 'Initial Access',
            demo_priority: 1
        })

        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
    """)

    # Create malware alert type
    await neo4j_client.run_query("""
        CREATE (:AlertType {
            id: 'malware_detection',
            name: 'Malware Detection',
            description: 'Malicious file or process detected',
            severity: 'critical',
            mitre_technique: 'T1204'
        })
    """)

    # ALERT-7821: Malware (critical severity)
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'SRV-DB-PROD-01'})
        MATCH (user:User {id: 'mchen@company.com'})
        MATCH (alertType:AlertType {id: 'malware_detection'})

        CREATE (alert:Alert {
            id: 'ALERT-7821',
            alert_type: 'malware_detection',
            severity: 'critical',
            source_ip: '10.0.2.50',
            source_location: 'Internal Network',
            timestamp: datetime('2026-02-06T09:30:00Z'),
            description: 'Suspicious process detected on production database server',
            asset_id: 'SRV-DB-PROD-01',
            user_id: 'mchen@company.com',
            status: 'pending',
            mfa_completed: true,
            device_fingerprint_match: true,
            mitre_technique: 'T1204',
            mitre_tactic: 'Execution',
            demo_priority: 2
        })

        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
    """)

    # ALERT-7820: Another anomalous login (low severity)
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'LAPTOP-ALEE'})
        MATCH (user:User {id: 'alee@company.com'})
        MATCH (alertType:AlertType {id: 'anomalous_login'})

        CREATE (alert:Alert {
            id: 'ALERT-7820',
            alert_type: 'anomalous_login',
            severity: 'low',
            source_ip: '192.168.1.45',
            source_location: 'San Francisco',
            timestamp: datetime('2026-02-06T08:00:00Z'),
            description: 'Login from usual location at unusual time',
            asset_id: 'LAPTOP-ALEE',
            user_id: 'alee@company.com',
            status: 'pending',
            mfa_completed: true,
            device_fingerprint_match: true,
            mitre_technique: 'T1078',
            mitre_tactic: 'Initial Access',
            demo_priority: 1
        })

        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
    """)

    # ALERT-7819: Another phishing (medium severity)
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'LAPTOP-JSMITH'})
        MATCH (user:User {id: 'jsmith@company.com'})
        MATCH (alertType:AlertType {id: 'phishing'})

        CREATE (alert:Alert {
            id: 'ALERT-7819',
            alert_type: 'phishing',
            severity: 'medium',
            source_ip: '103.15.42.88',
            source_location: 'Singapore',
            timestamp: datetime('2026-02-06T04:20:00Z'),
            description: 'Suspicious attachment opened',
            asset_id: 'LAPTOP-JSMITH',
            user_id: 'jsmith@company.com',
            status: 'pending',
            mfa_completed: true,
            device_fingerprint_match: true,
            mitre_technique: 'T1566',
            mitre_tactic: 'Initial Access',
            demo_priority: 2
        })

        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
    """)

    # ALERT-7824: Known phishing campaign (HIGH severity - for Prompt 5C)
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'LAPTOP-MARYCHEN'})
        MATCH (user:User {id: 'marychen@company.com'})
        MATCH (alertType:AlertType {id: 'phishing'})
        MATCH (pattern:AttackPattern {id: 'PAT-PHISH-KNOWN'})
        MATCH (campaign:PhishingCampaign {id: 'CAMP-2024-0142'})

        CREATE (alert:Alert {
            id: 'ALERT-7824',
            alert_type: 'phishing',
            severity: 'high',
            source_ip: '192.168.1.150',
            source_location: 'Email Gateway',
            destination_ip: '45.33.32.156',
            timestamp: datetime('2026-02-06T11:30:00Z'),
            description: 'Suspicious email with malicious link targeting Mary Chen, Engineering Lead',
            asset_id: 'LAPTOP-MARYCHEN',
            user_id: 'marychen@company.com',
            status: 'pending',
            mfa_completed: true,
            device_fingerprint_match: true,
            email_subject: 'Urgent: Verify Your Account',
            sender_domain: 'microsofft-support.com',
            malicious_url: 'hxxp://evil-phishing-site[.]com/login',
            mitre_technique: 'T1566',
            mitre_tactic: 'Initial Access',
            demo_priority: 1
        })

        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
        CREATE (alert)-[:MATCHES]->(pattern)
        CREATE (alert)-[:PART_OF]->(campaign)
    """)

    # ========================================================================
    # F2a — Category 1: Travel/VPN alerts (4 new alerts)
    # ========================================================================

    print("  [OK] Creating Travel/VPN alerts (F2a Category 1)...")

    # New users
    await neo4j_client.run_query("""
        MERGE (u:User {id: 'rjones@company.com'})
        SET u.name = 'Robert Jones', u.department = 'Sales',
            u.title = 'Sales Director', u.risk_score = 0.45,
            u.is_privileged = false
    """)

    await neo4j_client.run_query("""
        MERGE (u:User {id: 'agarcia@company.com'})
        SET u.name = 'Ana Garcia', u.department = 'Marketing',
            u.title = 'Marketing Manager', u.risk_score = 0.30,
            u.is_privileged = false
    """)

    await neo4j_client.run_query("""
        MERGE (u:User {id: 'kpatel@company.com'})
        SET u.name = 'Kavita Patel', u.department = 'Finance',
            u.title = 'CFO', u.risk_score = 0.90,
            u.is_privileged = true
    """)

    # New assets
    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'LAPTOP-RJONES'})
        SET a.hostname = 'LAPTOP-RJONES', a.type = 'endpoint',
            a.criticality = 'medium', a.business_unit = 'Sales',
            a.os = 'Windows 11', a.owner_id = 'rjones@company.com'
    """)

    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'LAPTOP-AGARCIA'})
        SET a.hostname = 'LAPTOP-AGARCIA', a.type = 'endpoint',
            a.criticality = 'low', a.business_unit = 'Marketing',
            a.os = 'MacOS', a.owner_id = 'agarcia@company.com'
    """)

    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'DESKTOP-KPATEL'})
        SET a.hostname = 'DESKTOP-KPATEL', a.type = 'endpoint',
            a.criticality = 'high', a.business_unit = 'Finance',
            a.os = 'Windows 11', a.owner_id = 'kpatel@company.com'
    """)

    # New attack patterns
    await neo4j_client.run_query("""
        MERGE (p:AttackPattern {id: 'PAT-TRAVEL-002'})
        SET p.name = 'Travel Login After Hours',
            p.description = 'Login from travel location during late hours',
            p.fp_rate = 0.30, p.occurrence_count = 43, p.confidence = 0.78
    """)

    await neo4j_client.run_query("""
        MERGE (p:AttackPattern {id: 'PAT-TRAVEL-003'})
        SET p.name = 'Travel Login Business Hours',
            p.description = 'Login from travel location during business hours',
            p.fp_rate = 0.55, p.occurrence_count = 8, p.confidence = 0.55
    """)

    await neo4j_client.run_query("""
        MERGE (p:AttackPattern {id: 'PAT-TRAVEL-004'})
        SET p.name = 'VIP After Hours Login',
            p.description = 'Executive login from unusual location at late hours',
            p.fp_rate = 0.20, p.occurrence_count = 2, p.confidence = 0.35
    """)

    # ALERT-7830: Tokyo / rjones (medium)
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'LAPTOP-RJONES'})
        MATCH (user:User {id: 'rjones@company.com'})
        MATCH (alertType:AlertType {id: 'anomalous_login'})
        MATCH (pattern:AttackPattern {id: 'PAT-TRAVEL-002'})
        CREATE (alert:Alert {
            id: 'ALERT-7830',
            alert_type: 'anomalous_login',
            severity: 'medium',
            source_ip: '210.135.18.42',
            source_location: 'Tokyo',
            timestamp: datetime('2026-02-26T14:15:00Z'),
            description: 'Login from unusual location: Tokyo at 11:15 PM local time',
            asset_id: 'LAPTOP-RJONES',
            user_id: 'rjones@company.com',
            status: 'pending',
            mfa_completed: true,
            device_fingerprint_match: true,
            mitre_technique: 'T1078',
            mitre_tactic: 'Initial Access',
            demo_priority: 2
        })
        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
        CREATE (alert)-[:MATCHES]->(pattern)
    """)

    # ALERT-7835: London / agarcia (low)
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'LAPTOP-AGARCIA'})
        MATCH (user:User {id: 'agarcia@company.com'})
        MATCH (alertType:AlertType {id: 'anomalous_login'})
        MATCH (pattern:AttackPattern {id: 'PAT-TRAVEL-003'})
        CREATE (alert:Alert {
            id: 'ALERT-7835',
            alert_type: 'anomalous_login',
            severity: 'low',
            source_ip: '81.129.14.77',
            source_location: 'London',
            timestamp: datetime('2026-02-26T10:30:00Z'),
            description: 'Login from unusual location: London during business hours',
            asset_id: 'LAPTOP-AGARCIA',
            user_id: 'agarcia@company.com',
            status: 'pending',
            mfa_completed: true,
            device_fingerprint_match: true,
            mitre_technique: 'T1078',
            mitre_tactic: 'Initial Access',
            demo_priority: 2
        })
        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
        CREATE (alert)-[:MATCHES]->(pattern)
    """)

    # ALERT-7841: Singapore / jsmith (high — no MFA, new device)
    # Reuses existing jsmith User + LAPTOP-JSMITH Asset + PAT-TRAVEL-001
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'LAPTOP-JSMITH'})
        MATCH (user:User {id: 'jsmith@company.com'})
        MATCH (alertType:AlertType {id: 'anomalous_login'})
        MATCH (pattern:AttackPattern {id: 'PAT-TRAVEL-001'})
        CREATE (alert:Alert {
            id: 'ALERT-7841',
            alert_type: 'anomalous_login',
            severity: 'high',
            source_ip: '103.15.42.99',
            source_location: 'Singapore',
            timestamp: datetime('2026-02-26T05:18:00Z'),
            description: 'Second Singapore login from new device — no MFA completion',
            asset_id: 'LAPTOP-JSMITH',
            user_id: 'jsmith@company.com',
            status: 'pending',
            mfa_completed: false,
            device_fingerprint_match: false,
            mitre_technique: 'T1078',
            mitre_tactic: 'Initial Access',
            demo_priority: 2
        })
        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
        CREATE (alert)-[:MATCHES]->(pattern)
    """)

    # ALERT-7845: Dubai / kpatel (medium — CFO, 2 AM)
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'DESKTOP-KPATEL'})
        MATCH (user:User {id: 'kpatel@company.com'})
        MATCH (alertType:AlertType {id: 'anomalous_login'})
        MATCH (pattern:AttackPattern {id: 'PAT-TRAVEL-004'})
        CREATE (alert:Alert {
            id: 'ALERT-7845',
            alert_type: 'anomalous_login',
            severity: 'medium',
            source_ip: '94.200.17.88',
            source_location: 'Dubai',
            timestamp: datetime('2026-02-26T22:30:00Z'),
            description: 'Login from unusual location: Dubai at 2:30 AM local time',
            asset_id: 'DESKTOP-KPATEL',
            user_id: 'kpatel@company.com',
            status: 'pending',
            mfa_completed: true,
            device_fingerprint_match: false,
            mitre_technique: 'T1078',
            mitre_tactic: 'Initial Access',
            demo_priority: 2
        })
        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
        CREATE (alert)-[:MATCHES]->(pattern)
    """)

    print("  [OK] Travel/VPN alerts created: ALERT-7830, ALERT-7835, ALERT-7841, ALERT-7845")

    # ========================================================================
    # F2a — Category 2: Credential/Access alerts (3 new)
    # F2a — Category 3: Threat Intel Match alerts (2 new)
    # ========================================================================

    print("  [OK] Creating Credential/Access + Threat Intel alerts (F2a Categories 2-3)...")

    # --- New AlertTypes ---

    await neo4j_client.run_query("""
        MERGE (at:AlertType {id: 'brute_force'})
        SET at.name = 'Brute Force Attack',
            at.description = 'Repeated failed authentication attempts',
            at.severity = 'high', at.mitre_technique = 'T1110'
    """)

    await neo4j_client.run_query("""
        MERGE (at:AlertType {id: 'privilege_escalation'})
        SET at.name = 'Privilege Escalation',
            at.description = 'Unauthorized elevation of user privileges',
            at.severity = 'critical', at.mitre_technique = 'T1098'
    """)

    await neo4j_client.run_query("""
        MERGE (at:AlertType {id: 'credential_stuffing'})
        SET at.name = 'Credential Stuffing',
            at.description = 'Automated use of breached credentials against a target',
            at.severity = 'high', at.mitre_technique = 'T1110'
    """)

    await neo4j_client.run_query("""
        MERGE (at:AlertType {id: 'c2_beacon'})
        SET at.name = 'C2 Beacon',
            at.description = 'Outbound communication to known command-and-control infrastructure',
            at.severity = 'critical', at.mitre_technique = 'T1071'
    """)

    await neo4j_client.run_query("""
        MERGE (at:AlertType {id: 'threat_intel_match'})
        SET at.name = 'Threat Intel Match',
            at.description = 'Indicator matches active threat intelligence feed',
            at.severity = 'high', at.mitre_technique = 'T1566'
    """)

    # --- New Playbooks + HANDLED_BY ---

    await neo4j_client.run_query("""
        MERGE (pb:Playbook {id: 'PB-BRUTE-001'})
        SET pb.name = 'Brute Force Response',
            pb.description = 'Lock account and escalate repeated auth failures',
            pb.steps = ['Lock account', 'Notify owner', 'Escalate to Tier 2', 'Review logs'],
            pb.auto_actions = ['lock_account'],
            pb.sla_minutes = 20
        WITH pb
        MATCH (at:AlertType {id: 'brute_force'})
        MERGE (at)-[:HANDLED_BY]->(pb)
    """)

    await neo4j_client.run_query("""
        MERGE (pb:Playbook {id: 'PB-ESCALATE-001'})
        SET pb.name = 'Privilege Escalation Incident',
            pb.description = 'Revoke access and open IR ticket for privilege abuse',
            pb.steps = ['Revoke access', 'Audit change', 'Escalate to IR', 'Preserve logs'],
            pb.auto_actions = ['revoke_access'],
            pb.sla_minutes = 15
        WITH pb
        MATCH (at:AlertType {id: 'privilege_escalation'})
        MERGE (at)-[:HANDLED_BY]->(pb)
    """)

    await neo4j_client.run_query("""
        MERGE (pb:Playbook {id: 'PB-CREDSTUFF-001'})
        SET pb.name = 'Credential Stuffing Block',
            pb.description = 'Rate-limit and block sources of credential stuffing',
            pb.steps = ['Block source IPs', 'Enable rate limiting', 'Force resets', 'Notify security'],
            pb.auto_actions = ['block_ips', 'rate_limit'],
            pb.sla_minutes = 15
        WITH pb
        MATCH (at:AlertType {id: 'credential_stuffing'})
        MERGE (at)-[:HANDLED_BY]->(pb)
    """)

    await neo4j_client.run_query("""
        MERGE (pb:Playbook {id: 'PB-INCIDENT-001'})
        SET pb.name = 'C2 Isolation Incident',
            pb.description = 'Isolate host and block C2 domain, open IR ticket',
            pb.steps = ['Isolate host', 'Block C2 domain', 'Escalate to IR', 'Forensic capture'],
            pb.auto_actions = ['isolate_host', 'block_domain'],
            pb.sla_minutes = 10
        WITH pb
        MATCH (at:AlertType {id: 'c2_beacon'})
        MERGE (at)-[:HANDLED_BY]->(pb)
    """)

    await neo4j_client.run_query("""
        MERGE (pb:Playbook {id: 'PB-THREATINTEL-001'})
        SET pb.name = 'Threat Intel Remediation',
            pb.description = 'Quarantine and search for additional exposure',
            pb.steps = ['Quarantine artifact', 'Block indicator', 'Search similar', 'Notify SOC'],
            pb.auto_actions = ['quarantine', 'block_indicator'],
            pb.sla_minutes = 10
        WITH pb
        MATCH (at:AlertType {id: 'threat_intel_match'})
        MERGE (at)-[:HANDLED_BY]->(pb)
    """)

    # --- New AttackPatterns ---

    await neo4j_client.run_query("""
        MERGE (p:AttackPattern {id: 'PAT-BRUTE-001'})
        SET p.name = 'Brute Force Service Account',
            p.description = 'High-volume failed logins against a service account',
            p.fp_rate = 0.05, p.occurrence_count = 47, p.confidence = 0.88
    """)

    await neo4j_client.run_query("""
        MERGE (p:AttackPattern {id: 'PAT-PRIVESC-001'})
        SET p.name = 'Unauthorized Privilege Escalation',
            p.description = 'Group membership change outside approved change window',
            p.fp_rate = 0.03, p.occurrence_count = 3, p.confidence = 0.92
    """)

    await neo4j_client.run_query("""
        MERGE (p:AttackPattern {id: 'PAT-CREDSTUFF-001'})
        SET p.name = 'Credential Stuffing External',
            p.description = 'Large volume of unique credentials tested against a gateway',
            p.fp_rate = 0.02, p.occurrence_count = 312, p.confidence = 0.95
    """)

    await neo4j_client.run_query("""
        MERGE (p:AttackPattern {id: 'PAT-C2-001'})
        SET p.name = 'C2 Beacon Cobaltstrike',
            p.description = 'Periodic outbound beacon matching known C2 profile',
            p.fp_rate = 0.01, p.occurrence_count = 5, p.confidence = 0.97
    """)

    await neo4j_client.run_query("""
        MERGE (p:AttackPattern {id: 'PAT-APT-001'})
        SET p.name = 'APT Campaign Indicator Match',
            p.description = 'Sender or URL matches active APT campaign indicator feed',
            p.fp_rate = 0.06, p.occurrence_count = 12, p.confidence = 0.85
    """)

    # --- New Users ---

    await neo4j_client.run_query("""
        MERGE (u:User {id: 'svc-backup@system'})
        SET u.name = 'svc-backup', u.department = 'IT',
            u.title = 'Service Account', u.risk_score = 0.65,
            u.is_privileged = false
    """)

    await neo4j_client.run_query("""
        MERGE (u:User {id: 'mwilson@company.com'})
        SET u.name = 'Mike Wilson', u.department = 'Engineering',
            u.title = 'Junior Developer', u.risk_score = 0.55,
            u.is_privileged = false
    """)

    await neo4j_client.run_query("""
        MERGE (u:User {id: 'multiple@external'})
        SET u.name = 'multiple', u.department = 'External',
            u.title = 'External Attacker', u.risk_score = 0.75,
            u.is_privileged = false
    """)

    await neo4j_client.run_query("""
        MERGE (u:User {id: 'unknown@external'})
        SET u.name = 'unknown', u.department = 'External',
            u.title = 'Unknown', u.risk_score = 0.95,
            u.is_privileged = false
    """)

    await neo4j_client.run_query("""
        MERGE (u:User {id: 'tjiang@company.com'})
        SET u.name = 'Tom Jiang', u.department = 'Finance',
            u.title = 'Finance Analyst', u.risk_score = 0.60,
            u.is_privileged = false
    """)

    # --- New Assets ---

    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'SRV-BACKUP-01'})
        SET a.hostname = 'SRV-BACKUP-01', a.type = 'server',
            a.criticality = 'high', a.business_unit = 'IT',
            a.os = 'Ubuntu 22.04', a.owner_id = 'svc-backup@system'
    """)

    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'LAPTOP-MWILSON'})
        SET a.hostname = 'LAPTOP-MWILSON', a.type = 'endpoint',
            a.criticality = 'medium', a.business_unit = 'Engineering',
            a.os = 'Windows 11', a.owner_id = 'mwilson@company.com'
    """)

    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'VPN-GATEWAY-01'})
        SET a.hostname = 'VPN-GATEWAY-01', a.type = 'network',
            a.criticality = 'critical', a.business_unit = 'IT',
            a.os = 'Palo Alto PAN-OS', a.owner_id = 'mchen@company.com'
    """)

    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'SRV-WEB-03'})
        SET a.hostname = 'SRV-WEB-03', a.type = 'server',
            a.criticality = 'critical', a.business_unit = 'IT',
            a.os = 'Ubuntu 22.04', a.owner_id = 'mchen@company.com'
    """)

    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'LAPTOP-TJIANG'})
        SET a.hostname = 'LAPTOP-TJIANG', a.type = 'endpoint',
            a.criticality = 'medium', a.business_unit = 'Finance',
            a.os = 'Windows 11', a.owner_id = 'tjiang@company.com'
    """)

    # --- ALERT-7831: Brute Force / svc-backup (high) ---
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'SRV-BACKUP-01'})
        MATCH (user:User {id: 'svc-backup@system'})
        MATCH (alertType:AlertType {id: 'brute_force'})
        MATCH (pattern:AttackPattern {id: 'PAT-BRUTE-001'})
        CREATE (alert:Alert {
            id: 'ALERT-7831',
            alert_type: 'brute_force',
            severity: 'high',
            source_ip: '192.168.1.0',
            source_location: 'Internal',
            timestamp: datetime('2026-02-26T03:22:00Z'),
            description: '47 failed login attempts in 3 minutes on service account',
            asset_id: 'SRV-BACKUP-01',
            user_id: 'svc-backup@system',
            status: 'pending',
            failed_attempts: 47,
            window_minutes: 3,
            mfa_completed: false,
            device_fingerprint_match: false,
            mitre_technique: 'T1110',
            mitre_tactic: 'Credential Access',
            demo_priority: 2
        })
        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
        CREATE (alert)-[:MATCHES]->(pattern)
    """)

    # --- ALERT-7836: Privilege Escalation / mwilson (critical) ---
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'LAPTOP-MWILSON'})
        MATCH (user:User {id: 'mwilson@company.com'})
        MATCH (alertType:AlertType {id: 'privilege_escalation'})
        MATCH (pattern:AttackPattern {id: 'PAT-PRIVESC-001'})
        CREATE (alert:Alert {
            id: 'ALERT-7836',
            alert_type: 'privilege_escalation',
            severity: 'critical',
            source_ip: '10.0.1.77',
            source_location: 'Internal',
            timestamp: datetime('2026-02-26T02:45:00Z'),
            description: 'User added to Domain Admins group outside change window',
            asset_id: 'LAPTOP-MWILSON',
            user_id: 'mwilson@company.com',
            status: 'pending',
            group_modified: 'Domain Admins',
            change_window_violation: true,
            mfa_completed: true,
            device_fingerprint_match: true,
            mitre_technique: 'T1098',
            mitre_tactic: 'Persistence',
            demo_priority: 2
        })
        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
        CREATE (alert)-[:MATCHES]->(pattern)
    """)

    # --- ALERT-7842: Credential Stuffing / multiple / VPN-GATEWAY (high) ---
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'VPN-GATEWAY-01'})
        MATCH (user:User {id: 'multiple@external'})
        MATCH (alertType:AlertType {id: 'credential_stuffing'})
        MATCH (pattern:AttackPattern {id: 'PAT-CREDSTUFF-001'})
        CREATE (alert:Alert {
            id: 'ALERT-7842',
            alert_type: 'credential_stuffing',
            severity: 'high',
            source_ip: '185.220.101.50',
            source_location: 'External',
            timestamp: datetime('2026-02-26T07:08:00Z'),
            description: '312 unique credential pairs tested against VPN gateway in 8 minutes',
            asset_id: 'VPN-GATEWAY-01',
            user_id: 'multiple@external',
            status: 'pending',
            credential_pairs_tested: 312,
            window_minutes: 8,
            mfa_completed: false,
            device_fingerprint_match: false,
            mitre_technique: 'T1110',
            mitre_tactic: 'Credential Access',
            demo_priority: 2
        })
        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
        CREATE (alert)-[:MATCHES]->(pattern)
    """)

    # --- ALERT-7825: C2 Beacon / unknown / SRV-WEB-03 (critical) ---
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'SRV-WEB-03'})
        MATCH (user:User {id: 'unknown@external'})
        MATCH (alertType:AlertType {id: 'c2_beacon'})
        MATCH (pattern:AttackPattern {id: 'PAT-C2-001'})
        CREATE (alert:Alert {
            id: 'ALERT-7825',
            alert_type: 'c2_beacon',
            severity: 'critical',
            source_ip: '10.0.3.15',
            source_location: 'External',
            destination_domain: 'cobaltstrike.github.io',
            timestamp: datetime('2026-02-26T01:12:00Z'),
            description: 'Outbound beacon to known C2 infrastructure — cobaltstrike.github.io',
            asset_id: 'SRV-WEB-03',
            user_id: 'unknown@external',
            status: 'pending',
            beacon_interval_seconds: 60,
            mfa_completed: false,
            device_fingerprint_match: false,
            mitre_technique: 'T1071',
            mitre_tactic: 'Command and Control',
            demo_priority: 2
        })
        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
        CREATE (alert)-[:MATCHES]->(pattern)
    """)

    # --- ALERT-7832: Threat Intel Match / tjiang (high) ---
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'LAPTOP-TJIANG'})
        MATCH (user:User {id: 'tjiang@company.com'})
        MATCH (alertType:AlertType {id: 'threat_intel_match'})
        MATCH (pattern:AttackPattern {id: 'PAT-APT-001'})
        CREATE (alert:Alert {
            id: 'ALERT-7832',
            alert_type: 'threat_intel_match',
            severity: 'high',
            source_ip: '203.0.113.77',
            source_location: 'External',
            timestamp: datetime('2026-02-26T09:55:00Z'),
            description: 'Email from sender matching active APT campaign indicators',
            asset_id: 'LAPTOP-TJIANG',
            user_id: 'tjiang@company.com',
            status: 'pending',
            sender_domain: 'apt-lookalike-finance.com',
            mfa_completed: true,
            device_fingerprint_match: true,
            mitre_technique: 'T1566',
            mitre_tactic: 'Initial Access',
            demo_priority: 2
        })
        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
        CREATE (alert)-[:MATCHES]->(pattern)
    """)

    print("  [OK] Credential/Access alerts created: ALERT-7831, ALERT-7836, ALERT-7842")
    print("  [OK] Threat Intel alerts created: ALERT-7825, ALERT-7832")

    # ========================================================================
    # F2a — Category 4: Behavioral Anomaly alerts (3 new)
    # F2a — Category 5: Cloud/Infrastructure alerts (2 new)
    # ========================================================================

    print("  [OK] Creating Behavioral Anomaly + Cloud alerts (F2a Categories 4-5)...")

    # --- New AlertTypes ---

    await neo4j_client.run_query("""
        MERGE (at:AlertType {id: 'data_exfil'})
        SET at.name = 'Data Exfiltration',
            at.description = 'Unusual volume of data transferred to external destination',
            at.severity = 'critical', at.mitre_technique = 'T1048'
    """)

    await neo4j_client.run_query("""
        MERGE (at:AlertType {id: 'anomalous_behavior'})
        SET at.name = 'Anomalous Behavior',
            at.description = 'Activity deviating significantly from established baseline',
            at.severity = 'medium', at.mitre_technique = 'T1071'
    """)

    await neo4j_client.run_query("""
        MERGE (at:AlertType {id: 'insider_threat'})
        SET at.name = 'Insider Threat',
            at.description = 'Suspicious data collection activity by internal user',
            at.severity = 'high', at.mitre_technique = 'T1048'
    """)

    await neo4j_client.run_query("""
        MERGE (at:AlertType {id: 'cloud_config'})
        SET at.name = 'Cloud Misconfiguration',
            at.description = 'Cloud resource configuration change that introduces risk',
            at.severity = 'high', at.mitre_technique = 'T1098'
    """)

    # --- New Playbooks + HANDLED_BY ---

    await neo4j_client.run_query("""
        MERGE (pb:Playbook {id: 'PB-EXFIL-001'})
        SET pb.name = 'Data Exfiltration Response',
            pb.description = 'Block connection and escalate to IR for data loss',
            pb.steps = ['Block connection', 'Escalate to IR', 'Preserve evidence', 'Notify Legal'],
            pb.auto_actions = ['block_connection'],
            pb.sla_minutes = 10
        WITH pb
        MATCH (at:AlertType {id: 'data_exfil'})
        MERGE (at)-[:HANDLED_BY]->(pb)
    """)

    await neo4j_client.run_query("""
        MERGE (pb:Playbook {id: 'PB-BEHAVIOR-001'})
        SET pb.name = 'Anomalous Behavior Monitor',
            pb.description = 'Enrich with context and escalate if confirmed',
            pb.steps = ['Enrich with context', 'Review baseline', 'Watch for escalation', 'Alert analyst'],
            pb.auto_actions = ['enrich'],
            pb.sla_minutes = 20
        WITH pb
        MATCH (at:AlertType {id: 'anomalous_behavior'})
        MERGE (at)-[:HANDLED_BY]->(pb)
    """)

    await neo4j_client.run_query("""
        MERGE (pb:Playbook {id: 'PB-INSIDER-001'})
        SET pb.name = 'Insider Threat Preservation',
            pb.description = 'Preserve evidence and notify HR/Legal before acting',
            pb.steps = ['Preserve evidence', 'Notify HR and Legal', 'Escalate to IR', 'Revoke access'],
            pb.auto_actions = ['preserve_evidence'],
            pb.sla_minutes = 15
        WITH pb
        MATCH (at:AlertType {id: 'insider_threat'})
        MERGE (at)-[:HANDLED_BY]->(pb)
    """)

    await neo4j_client.run_query("""
        MERGE (pb:Playbook {id: 'PB-CLOUD-001'})
        SET pb.name = 'Cloud Config Remediation',
            pb.description = 'Revert misconfiguration and audit access',
            pb.steps = ['Revert config', 'Notify cloud team', 'Audit access', 'Update policy'],
            pb.auto_actions = ['revert_config'],
            pb.sla_minutes = 15
        WITH pb
        MATCH (at:AlertType {id: 'cloud_config'})
        MERGE (at)-[:HANDLED_BY]->(pb)
    """)

    # --- New AttackPatterns ---

    await neo4j_client.run_query("""
        MERGE (p:AttackPattern {id: 'PAT-EXFIL-001'})
        SET p.name = 'Large Upload After Hours',
            p.description = 'Bulk data upload to external service outside business hours',
            p.fp_rate = 0.05, p.occurrence_count = 7, p.confidence = 0.91
    """)

    await neo4j_client.run_query("""
        MERGE (p:AttackPattern {id: 'PAT-DNS-001'})
        SET p.name = 'Anomalous DNS Query Volume',
            p.description = 'DNS query rate significantly above user baseline',
            p.fp_rate = 0.15, p.occurrence_count = 15, p.confidence = 0.72
    """)

    await neo4j_client.run_query("""
        MERGE (p:AttackPattern {id: 'PAT-INSIDER-001'})
        SET p.name = 'Departing Employee Mass Download',
            p.description = 'High-volume file collection shortly before departure',
            p.fp_rate = 0.08, p.occurrence_count = 4, p.confidence = 0.87
    """)

    await neo4j_client.run_query("""
        MERGE (p:AttackPattern {id: 'PAT-CLOUD-001'})
        SET p.name = 'S3 Public Access Change',
            p.description = 'Cloud storage ACL changed to allow public read',
            p.fp_rate = 0.04, p.occurrence_count = 9, p.confidence = 0.83
    """)

    await neo4j_client.run_query("""
        MERGE (p:AttackPattern {id: 'PAT-CLOUD-002'})
        SET p.name = 'Service Principal Owner Grant',
            p.description = 'Unexpected Owner role assigned to automation principal',
            p.fp_rate = 0.10, p.occurrence_count = 3, p.confidence = 0.65
    """)

    # --- New Users (jsmith reused from existing data) ---

    await neo4j_client.run_query("""
        MERGE (u:User {id: 'lchen@company.com'})
        SET u.name = 'Lisa Chen', u.department = 'Data Science',
            u.title = 'Data Scientist', u.risk_score = 0.40,
            u.is_privileged = false
    """)

    await neo4j_client.run_query("""
        MERGE (u:User {id: 'rwang@company.com'})
        SET u.name = 'Richard Wang', u.department = 'Engineering',
            u.title = 'Departing Employee', u.risk_score = 0.80,
            u.is_privileged = false
    """)

    await neo4j_client.run_query("""
        MERGE (u:User {id: 'system@automated'})
        SET u.name = 'system', u.department = 'IT',
            u.title = 'Automated Process', u.risk_score = 0.70,
            u.is_privileged = false
    """)

    await neo4j_client.run_query("""
        MERGE (u:User {id: 'devops-pipeline@system'})
        SET u.name = 'devops-pipeline', u.department = 'DevOps',
            u.title = 'Service Principal', u.risk_score = 0.50,
            u.is_privileged = false
    """)

    # --- New Assets (LAPTOP-JSMITH reused from existing data) ---

    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'WORKSTATION-LCHEN'})
        SET a.hostname = 'WORKSTATION-LCHEN', a.type = 'endpoint',
            a.criticality = 'medium', a.business_unit = 'Data Science',
            a.os = 'Ubuntu 22.04', a.owner_id = 'lchen@company.com'
    """)

    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'LAPTOP-RWANG'})
        SET a.hostname = 'LAPTOP-RWANG', a.type = 'endpoint',
            a.criticality = 'medium', a.business_unit = 'Engineering',
            a.os = 'Windows 11', a.owner_id = 'rwang@company.com'
    """)

    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'AWS-PROD-ACCOUNT'})
        SET a.hostname = 'AWS-PROD-ACCOUNT', a.type = 'cloud',
            a.criticality = 'critical', a.business_unit = 'IT',
            a.os = 'AWS', a.owner_id = 'system@automated'
    """)

    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'AZURE-SUB-PROD'})
        SET a.hostname = 'AZURE-SUB-PROD', a.type = 'cloud',
            a.criticality = 'high', a.business_unit = 'DevOps',
            a.os = 'Azure', a.owner_id = 'devops-pipeline@system'
    """)

    # --- ALERT-7826: Data Exfil / jsmith / LAPTOP-JSMITH (critical, P1) ---
    # Reuses existing jsmith User + LAPTOP-JSMITH Asset
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'LAPTOP-JSMITH'})
        MATCH (user:User {id: 'jsmith@company.com'})
        MATCH (alertType:AlertType {id: 'data_exfil'})
        MATCH (pattern:AttackPattern {id: 'PAT-EXFIL-001'})
        CREATE (alert:Alert {
            id: 'ALERT-7826',
            alert_type: 'data_exfil',
            severity: 'critical',
            source_ip: '103.15.42.88',
            source_location: 'Internal',
            destination_url: 'dropbox.com',
            timestamp: datetime('2026-02-26T22:15:00Z'),
            description: '4.2 GB uploaded to external cloud storage outside business hours',
            asset_id: 'LAPTOP-JSMITH',
            user_id: 'jsmith@company.com',
            status: 'pending',
            upload_gb: 4.2,
            mfa_completed: true,
            device_fingerprint_match: true,
            mitre_technique: 'T1048',
            mitre_tactic: 'Exfiltration',
            demo_priority: 1
        })
        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
        CREATE (alert)-[:MATCHES]->(pattern)
    """)

    # --- ALERT-7833: Anomalous Behavior / lchen (medium, P2) ---
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'WORKSTATION-LCHEN'})
        MATCH (user:User {id: 'lchen@company.com'})
        MATCH (alertType:AlertType {id: 'anomalous_behavior'})
        MATCH (pattern:AttackPattern {id: 'PAT-DNS-001'})
        CREATE (alert:Alert {
            id: 'ALERT-7833',
            alert_type: 'anomalous_behavior',
            severity: 'medium',
            source_ip: '10.0.1.99',
            source_location: 'Internal',
            timestamp: datetime('2026-02-26T14:40:00Z'),
            description: 'Unusual outbound DNS query volume — 3x normal baseline',
            asset_id: 'WORKSTATION-LCHEN',
            user_id: 'lchen@company.com',
            status: 'pending',
            dns_queries_per_hour: 1847,
            baseline_queries_per_hour: 614,
            mfa_completed: true,
            device_fingerprint_match: true,
            mitre_technique: 'T1071',
            mitre_tactic: 'Command and Control',
            demo_priority: 2
        })
        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
        CREATE (alert)-[:MATCHES]->(pattern)
    """)

    # --- ALERT-7838: Insider Threat / rwang (high, P2) ---
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'LAPTOP-RWANG'})
        MATCH (user:User {id: 'rwang@company.com'})
        MATCH (alertType:AlertType {id: 'insider_threat'})
        MATCH (pattern:AttackPattern {id: 'PAT-INSIDER-001'})
        CREATE (alert:Alert {
            id: 'ALERT-7838',
            alert_type: 'insider_threat',
            severity: 'high',
            source_ip: '10.0.1.112',
            source_location: 'Internal',
            timestamp: datetime('2026-02-26T16:50:00Z'),
            description: 'Mass file download from SharePoint 2 days before resignation effective date',
            asset_id: 'LAPTOP-RWANG',
            user_id: 'rwang@company.com',
            status: 'pending',
            files_downloaded: 847,
            mfa_completed: true,
            device_fingerprint_match: true,
            mitre_technique: 'T1048',
            mitre_tactic: 'Exfiltration',
            demo_priority: 2
        })
        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
        CREATE (alert)-[:MATCHES]->(pattern)
    """)

    # --- ALERT-7827: Cloud Config / system / AWS-PROD-ACCOUNT (high, P1) ---
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'AWS-PROD-ACCOUNT'})
        MATCH (user:User {id: 'system@automated'})
        MATCH (alertType:AlertType {id: 'cloud_config'})
        MATCH (pattern:AttackPattern {id: 'PAT-CLOUD-001'})
        CREATE (alert:Alert {
            id: 'ALERT-7827',
            alert_type: 'cloud_config',
            severity: 'high',
            source_ip: '54.239.28.85',
            source_location: 'AWS',
            timestamp: datetime('2026-02-26T11:22:00Z'),
            description: 'S3 bucket policy changed to public access on production data store',
            asset_id: 'AWS-PROD-ACCOUNT',
            user_id: 'system@automated',
            status: 'pending',
            resource: 's3://prod-data-warehouse',
            change_type: 'ACL_PUBLIC_READ',
            mfa_completed: false,
            device_fingerprint_match: false,
            mitre_technique: 'T1098',
            mitre_tactic: 'Persistence',
            demo_priority: 1
        })
        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
        CREATE (alert)-[:MATCHES]->(pattern)
    """)

    # --- ALERT-7834: Cloud Config / devops-pipeline / AZURE-SUB-PROD (medium, P2) ---
    # Reuses PB-CLOUD-001 playbook (wired to cloud_config AlertType above)
    await neo4j_client.run_query("""
        MATCH (asset:Asset {id: 'AZURE-SUB-PROD'})
        MATCH (user:User {id: 'devops-pipeline@system'})
        MATCH (alertType:AlertType {id: 'cloud_config'})
        MATCH (pattern:AttackPattern {id: 'PAT-CLOUD-002'})
        CREATE (alert:Alert {
            id: 'ALERT-7834',
            alert_type: 'cloud_config',
            severity: 'medium',
            source_ip: '20.190.144.200',
            source_location: 'Azure',
            timestamp: datetime('2026-02-26T13:05:00Z'),
            description: 'New service principal granted Owner role on production subscription',
            asset_id: 'AZURE-SUB-PROD',
            user_id: 'devops-pipeline@system',
            status: 'pending',
            principal_name: 'deploy-automation-sp',
            role_assigned: 'Owner',
            mfa_completed: false,
            device_fingerprint_match: false,
            mitre_technique: 'T1098',
            mitre_tactic: 'Persistence',
            demo_priority: 2
        })
        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
        CREATE (alert)-[:MATCHES]->(pattern)
    """)

    print("  [OK] Behavioral Anomaly alerts created: ALERT-7826, ALERT-7833, ALERT-7838")
    print("  [OK] Cloud/Infrastructure alerts created: ALERT-7827, ALERT-7834")

    # ========================================================================
    # GAE-2a: Factor-specific seed data
    # ========================================================================
    await _seed_gae_factor_data()

    print("[SUCCESS] Sample data created successfully!")
    print("\nCreated:")
    print("  - 4 Users (John Smith, Alice Lee, Mike Chen, Mary Chen)")
    print("  - 4 Assets (3 laptops, 1 database server)")
    print("  - 6 Alerts (ALERT-7824 through ALERT-7819):")
    print("    * ALERT-7824: phishing (HIGH) - Known campaign (DarkHook) [NEW]")
    print("    * ALERT-7823: anomalous_login (medium) - Singapore travel")
    print("    * ALERT-7822: phishing (high) - suspicious link")
    print("    * ALERT-7821: malware_detection (critical) - prod server")
    print("    * ALERT-7820: anomalous_login (low) - unusual time")
    print("    * ALERT-7819: phishing (medium) - suspicious attachment")
    print("  - 1 TravelContext (Singapore, Feb 5-10)")
    print("  - 2 AttackPatterns (PAT-TRAVEL-001, PAT-PHISH-KNOWN)")
    print("  - 1 PhishingCampaign (Operation DarkHook)")
    print("  - 2 Playbooks (PB-LOGIN-FP, PB-PHISH-AUTO)")
    print("  - 3 AlertTypes (anomalous_login, phishing, malware_detection)")
    print("  - 1 SLA (Medium severity, 30 min)")
    print("  GAE factor data:")
    print("  - TravelRecord nodes: jsmith(Singapore), rjones(Tokyo), agarcia(London), kpatel(Dubai)")
    print("  - DataClass nodes + [:STORES] edges: JSMITH, SRV-DB-PROD-01, MARYCHEN, ALEE")
    print("  - ThreatIntel nodes + [:ASSOCIATED_WITH] edges: ALERT-7824, ALERT-7821, ALERT-7825")
    print("  - business_hours_login property set on travel/login alerts")
    print("\nReady for demo!")
    print("  - Tab 2: Try processing ALERT-7823")
    print("  - Tab 3: View alert queue - now has 6 alerts")
    print("  - ALERT-7823 -> FALSE_POSITIVE_CLOSE (travel scenario)")
    print("  - ALERT-7824 -> AUTO_REMEDIATE (known phishing campaign)")

    await neo4j_client.close()


async def _seed_gae_factor_data():
    """
    Add GAE factor-specific nodes: TravelRecord, DataClass, ThreatIntel.
    Also sets business_hours_login property on alerts for TimeAnomalyFactor.

    Called from seed_data() after the main corpus is seeded.
    """
    print("\n[GAE] Seeding factor data (TravelRecord, DataClass, ThreatIntel)...")

    # ========================================================================
    # TravelRecord nodes — required by TravelMatchFactor ([:HAS_TRAVEL])
    # The existing TravelContext nodes remain; TravelRecord is the new label.
    # ========================================================================

    await neo4j_client.run_query("""
        MERGE (u:User {id: 'jsmith@company.com'})
        MERGE (t:TravelRecord {id: 'TR-JSMITH-SGP-001'})
        SET t.destination  = 'Singapore',
            t.start_date   = date('2026-02-05'),
            t.end_date     = date('2026-02-10'),
            t.vpn_expected = ['SingTel', 'hotel-vpn']
        MERGE (u)-[:HAS_TRAVEL]->(t)
    """)

    await neo4j_client.run_query("""
        MERGE (u:User {id: 'rjones@company.com'})
        MERGE (t:TravelRecord {id: 'TR-RJONES-TYO-001'})
        SET t.destination  = 'Tokyo',
            t.start_date   = date('2026-02-24'),
            t.end_date     = date('2026-03-01'),
            t.vpn_expected = ['NTT', 'hotel-vpn']
        MERGE (u)-[:HAS_TRAVEL]->(t)
    """)

    await neo4j_client.run_query("""
        MERGE (u:User {id: 'agarcia@company.com'})
        MERGE (t:TravelRecord {id: 'TR-AGARCIA-LON-001'})
        SET t.destination  = 'London',
            t.start_date   = date('2026-02-25'),
            t.end_date     = date('2026-03-04'),
            t.vpn_expected = ['BT', 'hotel-vpn']
        MERGE (u)-[:HAS_TRAVEL]->(t)
    """)

    await neo4j_client.run_query("""
        MERGE (u:User {id: 'kpatel@company.com'})
        MERGE (t:TravelRecord {id: 'TR-KPATEL-DXB-001'})
        SET t.destination  = 'Dubai',
            t.start_date   = date('2026-02-26'),
            t.end_date     = date('2026-02-28'),
            t.vpn_expected = ['hotel-vpn']
        MERGE (u)-[:HAS_TRAVEL]->(t)
    """)

    print("  [GAE-OK] TravelRecord nodes: jsmith(Singapore), rjones(Tokyo), agarcia(London), kpatel(Dubai)")

    # ========================================================================
    # DataClass nodes — required by AssetCriticalityFactor ([:STORES])
    # ========================================================================

    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'LAPTOP-JSMITH'})
        MERGE (dc:DataClass {id: 'DC-FINANCE-REPORTS'})
        SET dc.name           = 'Finance Reports',
            dc.sensitivity    = 'RESTRICTED',
            dc.classification = 'CONFIDENTIAL'
        MERGE (a)-[:STORES]->(dc)
    """)

    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'SRV-DB-PROD-01'})
        MERGE (dc:DataClass {id: 'DC-CUSTOMER-PII'})
        SET dc.name           = 'Customer PII',
            dc.sensitivity    = 'PII',
            dc.classification = 'RESTRICTED'
        MERGE (a)-[:STORES]->(dc)
    """)

    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'LAPTOP-MARYCHEN'})
        MERGE (dc:DataClass {id: 'DC-ENG-DOCS'})
        SET dc.name           = 'Engineering Documentation',
            dc.sensitivity    = 'INTERNAL',
            dc.classification = 'INTERNAL'
        MERGE (a)-[:STORES]->(dc)
    """)

    await neo4j_client.run_query("""
        MERGE (a:Asset {id: 'LAPTOP-ALEE'})
        MERGE (dc:DataClass {id: 'DC-SOURCE-CODE'})
        SET dc.name           = 'Source Code',
            dc.sensitivity    = 'CONFIDENTIAL',
            dc.classification = 'CONFIDENTIAL'
        MERGE (a)-[:STORES]->(dc)
    """)

    print("  [GAE-OK] DataClass nodes + [:STORES] edges: JSMITH, SRV-DB-PROD-01, MARYCHEN, ALEE")

    # ========================================================================
    # ThreatIntel nodes — required by ThreatIntelEnrichmentFactor ([:ASSOCIATED_WITH])
    # ========================================================================

    # ALERT-7824: DarkHook phishing campaign — 2 corroborating sources
    await neo4j_client.run_query("""
        MERGE (ti:ThreatIntel {id: 'TI-DARKHOOK-001'})
        SET ti.name      = 'DarkHook Phishing Campaign',
            ti.severity  = 'high',
            ti.source    = 'pulsedive',
            ti.ioc_type  = 'domain',
            ti.ioc_value = 'microsofft-support.com'
        WITH ti
        MATCH (a:Alert {id: 'ALERT-7824'})
        MERGE (ti)-[:ASSOCIATED_WITH]->(a)
    """)

    await neo4j_client.run_query("""
        MERGE (ti:ThreatIntel {id: 'TI-DARKHOOK-002'})
        SET ti.name      = 'DarkHook URL Indicator',
            ti.severity  = 'high',
            ti.source    = 'greynoise',
            ti.ioc_type  = 'url',
            ti.ioc_value = 'evil-phishing-site.com'
        WITH ti
        MATCH (a:Alert {id: 'ALERT-7824'})
        MERGE (ti)-[:ASSOCIATED_WITH]->(a)
    """)

    # ALERT-7821: Malware on production server — 1 source
    await neo4j_client.run_query("""
        MERGE (ti:ThreatIntel {id: 'TI-MALWARE-001'})
        SET ti.name      = 'Cobalt Strike Implant Signature',
            ti.severity  = 'critical',
            ti.source    = 'health_isac',
            ti.ioc_type  = 'process',
            ti.ioc_value = 'csagent.exe'
        WITH ti
        MATCH (a:Alert {id: 'ALERT-7821'})
        MERGE (ti)-[:ASSOCIATED_WITH]->(a)
    """)

    # ALERT-7825: C2 beacon — 2 corroborating sources
    await neo4j_client.run_query("""
        MERGE (ti:ThreatIntel {id: 'TI-C2-001'})
        SET ti.name      = 'Cobalt Strike C2 Domain',
            ti.severity  = 'critical',
            ti.source    = 'cisa_kev',
            ti.ioc_type  = 'domain',
            ti.ioc_value = 'cobaltstrike.github.io'
        WITH ti
        MATCH (a:Alert {id: 'ALERT-7825'})
        MERGE (ti)-[:ASSOCIATED_WITH]->(a)
    """)

    await neo4j_client.run_query("""
        MERGE (ti:ThreatIntel {id: 'TI-C2-002'})
        SET ti.name      = 'Known C2 Infrastructure IP',
            ti.severity  = 'critical',
            ti.source    = 'greynoise',
            ti.ioc_type  = 'ip',
            ti.ioc_value = '10.0.3.15'
        WITH ti
        MATCH (a:Alert {id: 'ALERT-7825'})
        MERGE (ti)-[:ASSOCIATED_WITH]->(a)
    """)

    print("  [GAE-OK] ThreatIntel nodes + [:ASSOCIATED_WITH] edges: ALERT-7824, ALERT-7821, ALERT-7825")

    # ========================================================================
    # business_hours_login property — required by TimeAnomalyFactor
    # True = within business hours (08:00-18:00 Mon-Fri)
    # False = after hours or weekend
    # ========================================================================

    bhl_values = [
        ("ALERT-7823", False),   # 3 AM home timezone — after hours
        ("ALERT-7824", True),    # 11:30 — business hours
        ("ALERT-7821", True),    # 09:30 — business hours
        ("ALERT-7820", True),    # 08:00 — business hours
        ("ALERT-7819", False),   # 04:20 — after hours
        ("ALERT-7822", True),    # 10:15 — business hours
        ("ALERT-7830", False),   # 14:15 UTC = 23:15 Tokyo — after hours
        ("ALERT-7835", True),    # 10:30 — business hours
        ("ALERT-7841", False),   # 05:18 — after hours
        ("ALERT-7845", False),   # 22:30 — after hours
    ]
    for alert_id, bhl in bhl_values:
        await neo4j_client.run_query(
            "MATCH (a:Alert {id: $id}) SET a.business_hours_login = $bhl",
            {"id": alert_id, "bhl": bhl},
        )

    print("  [GAE-OK] business_hours_login property set on 10 alerts")
    print("[GAE] Factor data seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed_data())
