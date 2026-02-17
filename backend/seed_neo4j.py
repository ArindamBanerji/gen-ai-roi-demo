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
            device_fingerprint_match: true
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
            device_fingerprint_match: true
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
            device_fingerprint_match: true
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
            device_fingerprint_match: true
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
            device_fingerprint_match: true
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
            malicious_url: 'hxxp://evil-phishing-site[.]com/login'
        })

        CREATE (alert)-[:DETECTED_ON]->(asset)
        CREATE (alert)-[:INVOLVES]->(user)
        CREATE (alert)-[:CLASSIFIED_AS]->(alertType)
        CREATE (alert)-[:MATCHES]->(pattern)
        CREATE (alert)-[:PART_OF]->(campaign)
    """)

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
    print("\nReady for demo!")
    print("  - Tab 2: Try processing ALERT-7823")
    print("  - Tab 3: View alert queue - now has 6 alerts")
    print("  - ALERT-7823 -> FALSE_POSITIVE_CLOSE (travel scenario)")
    print("  - ALERT-7824 -> AUTO_REMEDIATE (known phishing campaign)")

    await neo4j_client.close()


if __name__ == "__main__":
    asyncio.run(seed_data())
