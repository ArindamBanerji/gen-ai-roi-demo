"""
Neo4j Database Seeding Service
Seeds the SOC Copilot Demo with canonical test data
"""
from typing import Dict, Any, List
from app.db.neo4j import neo4j_client


# =============================================================================
# CANONICAL SEED DATA (from support/setup/neo4j_seed_data.py)
# =============================================================================

ASSETS = [
    {"asset_id": "LAPTOP-JSMITH", "hostname": "LAPTOP-JSMITH", "type": "endpoint", "os": "Windows 11 Enterprise", "criticality": "high", "business_unit": "Finance", "owner_id": "jsmith@company.com"},
    {"asset_id": "SRV-DB-PROD-01", "hostname": "SRV-DB-PROD-01", "type": "server", "os": "RHEL 8.6", "criticality": "critical", "business_unit": "IT", "owner_id": "db_admin@company.com"},
    {"asset_id": "LAPTOP-MCHEN", "hostname": "LAPTOP-MCHEN", "type": "endpoint", "os": "macOS Sonoma", "criticality": "high", "business_unit": "Engineering", "owner_id": "mchen@company.com"},
    {"asset_id": "LAPTOP-AGARCIA", "hostname": "LAPTOP-AGARCIA", "type": "endpoint", "os": "macOS Sonoma", "criticality": "medium", "business_unit": "Engineering", "owner_id": "agarcia@company.com"},
    {"asset_id": "MAIL-GW-01", "hostname": "MAIL-GW-01", "type": "network", "os": "Proofpoint Appliance", "criticality": "critical", "business_unit": "IT", "owner_id": "mail_admin@company.com"},
]

USERS = [
    {"user_id": "jsmith@company.com", "name": "John Smith", "title": "VP Finance", "department": "Finance", "risk_score": 0.85, "is_privileged": True},
    {"user_id": "mchen@company.com", "name": "Mary Chen", "title": "Director Engineering", "department": "Engineering", "risk_score": 0.72, "is_privileged": True},
    {"user_id": "agarcia@company.com", "name": "Ana Garcia", "title": "Senior Developer", "department": "Engineering", "risk_score": 0.35, "is_privileged": False},
    {"user_id": "cjohnson@company.com", "name": "Chris Johnson", "title": "CEO", "department": "Executive", "risk_score": 0.95, "is_privileged": True},
    {"user_id": "blee@company.com", "name": "Bob Lee", "title": "SOC Analyst", "department": "Security", "risk_score": 0.25, "is_privileged": False},
]

ALERT_TYPES = [
    {"id": "anomalous_login", "name": "Anomalous Login", "severity": "medium", "mitre": "T1078"},
    {"id": "phishing", "name": "Phishing", "severity": "high", "mitre": "T1566"},
    {"id": "malware_detection", "name": "Malware Detection", "severity": "critical", "mitre": "T1204"},
    {"id": "data_exfiltration", "name": "Data Exfiltration", "severity": "high", "mitre": "T1048"},
]

PATTERNS = [
    {"pattern_id": "PAT-TRAVEL-001", "name": "Travel Login False Positive", "fp_rate": 0.94, "occurrence_count": 127, "confidence": 0.91},
    {"pattern_id": "PAT-PHISH-KNOWN", "name": "Known Phishing Campaign", "fp_rate": 0.02, "occurrence_count": 89, "confidence": 0.96},
    {"pattern_id": "PAT-MALWARE-ISOLATE", "name": "Standard Malware Isolation", "fp_rate": 0.08, "occurrence_count": 34, "confidence": 0.91},
    {"pattern_id": "PAT-VPN-KNOWN", "name": "Known VPN Provider", "fp_rate": 0.96, "occurrence_count": 245, "confidence": 0.94},
    {"pattern_id": "PAT-LOGIN-NORMAL", "name": "Normal Location Login", "fp_rate": 0.98, "occurrence_count": 2847, "confidence": 0.97},
]

PLAYBOOKS = [
    {"playbook_id": "PB-LOGIN-001", "name": "Anomalous Login Response", "sla_minutes": 15},
    {"playbook_id": "PB-PHISH-001", "name": "Phishing Response", "sla_minutes": 30},
    {"playbook_id": "PB-MALWARE-001", "name": "Malware Response", "sla_minutes": 10},
    {"playbook_id": "PB-DLP-001", "name": "Data Exfiltration Response", "sla_minutes": 5},
]

SLAS = [
    {"id": "SLA-CRITICAL", "name": "Critical SLA", "response_time_minutes": 10, "severity": "critical"},
    {"id": "SLA-HIGH", "name": "High SLA", "response_time_minutes": 30, "severity": "high"},
    {"id": "SLA-MEDIUM", "name": "Medium SLA", "response_time_minutes": 60, "severity": "medium"},
]

TRAVEL_RECORDS = [
    {"travel_id": "TRAVEL-001", "user_id": "jsmith@company.com", "destination": "Singapore", "start_date": "2026-01-28", "end_date": "2026-02-05"},
    {"travel_id": "TRAVEL-002", "user_id": "agarcia@company.com", "destination": "Denver", "start_date": "2026-01-30", "end_date": "2026-02-01"},
]

ALERTS = [
    {"alert_id": "ALERT-7823", "alert_type": "anomalous_login", "severity": "medium", "source": "Splunk", "asset_id": "LAPTOP-JSMITH", "user_id": "jsmith@company.com", "source_location": "Singapore", "status": "pending", "description": "Login from unusual location: Singapore at 3:47 AM local time"},
    {"alert_id": "ALERT-7822", "alert_type": "phishing", "severity": "high", "source": "Proofpoint", "asset_id": "MAIL-GW-01", "user_id": "finance_team@company.com", "source_location": "External", "status": "pending", "description": "Phishing email detected targeting Finance team"},
    {"alert_id": "ALERT-7821", "alert_type": "malware_detection", "severity": "critical", "source": "CrowdStrike", "asset_id": "SRV-DB-PROD-01", "user_id": "system", "source_location": "Internal", "status": "pending", "description": "Known malware hash detected on production database server"},
    {"alert_id": "ALERT-7820", "alert_type": "data_exfiltration", "severity": "high", "source": "DLP", "asset_id": "LAPTOP-MCHEN", "user_id": "mchen@company.com", "source_location": "Internal", "status": "pending", "description": "Large data transfer to external cloud storage"},
    {"alert_id": "ALERT-7819", "alert_type": "anomalous_login", "severity": "low", "source": "Splunk", "asset_id": "LAPTOP-AGARCIA", "user_id": "agarcia@company.com", "source_location": "Denver", "status": "pending", "description": "Login from Denver (user normally in San Francisco)"},
]

DECISIONS = [
    {"id": "DEC-7823", "type": "alert_triage", "reasoning": "User has active travel to Singapore. VPN from Marriott Hotels matches known provider. Pattern PAT-TRAVEL-001 matched with 127 similar cases.", "confidence": 0.92, "timestamp": "2026-01-31T03:48:00Z", "alert_id": "ALERT-7823", "action_taken": "false_positive_close"},
    {"id": "DEC-7822", "type": "alert_triage", "reasoning": "Email matches known Q4 phishing campaign. Auto-quarantine executed.", "confidence": 0.96, "timestamp": "2026-01-31T08:16:00Z", "alert_id": "ALERT-7822", "action_taken": "auto_remediate"},
    {"id": "DEC-7821", "type": "alert_triage", "reasoning": "Malware detected on CRITICAL production database server. Immediate IR escalation required.", "confidence": 0.96, "timestamp": "2026-01-31T09:31:00Z", "alert_id": "ALERT-7821", "action_taken": "escalate_incident"},
    {"id": "DEC-7820", "type": "alert_triage", "reasoning": "Potential data exfiltration from privileged user. Escalating to IR per policy.", "confidence": 0.97, "timestamp": "2026-01-31T10:16:00Z", "alert_id": "ALERT-7820", "action_taken": "escalate_incident"},
    {"id": "DEC-7819", "type": "alert_triage", "reasoning": "User Ana Garcia has active travel to Denver. Login location matches travel destination.", "confidence": 0.91, "timestamp": "2026-01-31T07:31:00Z", "alert_id": "ALERT-7819", "action_taken": "false_positive_close"},
]

CONTEXTS = [
    {"id": "CTX-7823", "decision_id": "DEC-7823", "patterns_matched": ["PAT-TRAVEL-001"], "nodes_consulted": 47},
    {"id": "CTX-7822", "decision_id": "DEC-7822", "patterns_matched": ["PAT-PHISH-KNOWN"], "nodes_consulted": 23},
    {"id": "CTX-7821", "decision_id": "DEC-7821", "patterns_matched": [], "nodes_consulted": 31},
    {"id": "CTX-7820", "decision_id": "DEC-7820", "patterns_matched": [], "nodes_consulted": 28},
    {"id": "CTX-7819", "decision_id": "DEC-7819", "patterns_matched": ["PAT-TRAVEL-001"], "nodes_consulted": 35},
]

EVOLUTIONS = [
    {"id": "EVO-0891", "event_type": "pattern_confidence", "triggered_by": "DEC-7823", "before_state": '{"confidence": 0.91, "occurrence_count": 126}', "after_state": '{"confidence": 0.94, "occurrence_count": 127}', "description": "Pattern PAT-TRAVEL-001 confidence increased based on successful false positive close", "timestamp": "2026-01-31T03:48:30Z"},
    {"id": "EVO-0890", "event_type": "threshold_adjustment", "triggered_by": "DEC-7819", "before_state": '{"auto_close_threshold": 0.88}', "after_state": '{"auto_close_threshold": 0.90}', "description": "Auto-close threshold for travel alerts adjusted based on sustained accuracy", "timestamp": "2026-01-31T07:32:00Z"},
    {"id": "EVO-0889", "event_type": "new_pattern", "triggered_by": "DEC-7822", "before_state": '{}', "after_state": '{"pattern_id": "PAT-PHISH-Q1-2026", "confidence": 0.94}', "description": "New phishing campaign pattern identified from Q1 2026 campaign", "timestamp": "2026-01-31T08:17:00Z"},
]

# Relationships
USER_ASSET_MAPPINGS = [("jsmith@company.com", "LAPTOP-JSMITH"), ("mchen@company.com", "LAPTOP-MCHEN"), ("agarcia@company.com", "LAPTOP-AGARCIA")]
ALERT_PLAYBOOK_MAPPINGS = [("anomalous_login", "PB-LOGIN-001"), ("phishing", "PB-PHISH-001"), ("malware_detection", "PB-MALWARE-001"), ("data_exfiltration", "PB-DLP-001")]
ASSET_SLA_MAPPINGS = [("LAPTOP-JSMITH", "SLA-HIGH"), ("SRV-DB-PROD-01", "SLA-CRITICAL"), ("LAPTOP-MCHEN", "SLA-HIGH"), ("LAPTOP-AGARCIA", "SLA-MEDIUM"), ("MAIL-GW-01", "SLA-CRITICAL")]
ALERT_PATTERN_MAPPINGS = [("ALERT-7823", "PAT-TRAVEL-001"), ("ALERT-7822", "PAT-PHISH-KNOWN"), ("ALERT-7821", "PAT-MALWARE-ISOLATE"), ("ALERT-7820", "PAT-VPN-KNOWN"), ("ALERT-7819", "PAT-LOGIN-NORMAL")]
TRIGGERED_EVOLUTIONS = [
    {"decision_id": "DEC-7823", "evolution_id": "EVO-0891", "impact": "pattern_confidence_increase", "magnitude": 0.03},
    {"decision_id": "DEC-7819", "evolution_id": "EVO-0890", "impact": "threshold_adjustment", "magnitude": 0.02},
    {"decision_id": "DEC-7822", "evolution_id": "EVO-0889", "impact": "new_pattern_created", "magnitude": 1.0},
]


# =============================================================================
# SEEDING FUNCTIONS
# =============================================================================

async def seed_neo4j_database() -> Dict[str, Any]:
    """
    Seed Neo4j database with canonical test data.
    Clears existing data and creates all nodes and relationships.
    """
    print("[SEED] Starting Neo4j database seeding...")
    summary = {}

    try:
        # Step 1: Clear existing data
        print("[SEED] Step 1: Clearing existing data...")
        await neo4j_client.run_query("MATCH (n) DETACH DELETE n")
        print("[SEED] ✓ Database cleared")

        # Step 2: Create Assets
        print("[SEED] Step 2: Creating Assets...")
        for asset in ASSETS:
            await neo4j_client.run_query(
                "CREATE (:Asset {id: $asset_id, hostname: $hostname, type: $type, os: $os, criticality: $criticality, business_unit: $business_unit, owner_id: $owner_id})",
                asset
            )
        summary["assets"] = len(ASSETS)
        print(f"[SEED] ✓ Created {len(ASSETS)} assets")

        # Step 3: Create Users
        print("[SEED] Step 3: Creating Users...")
        for user in USERS:
            await neo4j_client.run_query(
                "CREATE (:User {id: $user_id, name: $name, title: $title, department: $department, risk_score: $risk_score, is_privileged: $is_privileged})",
                user
            )
        summary["users"] = len(USERS)
        print(f"[SEED] ✓ Created {len(USERS)} users")

        # Step 4: Create AlertTypes
        print("[SEED] Step 4: Creating AlertTypes...")
        for alert_type in ALERT_TYPES:
            await neo4j_client.run_query(
                "CREATE (:AlertType {id: $id, name: $name, severity: $severity, mitre_technique: $mitre})",
                alert_type
            )
        summary["alert_types"] = len(ALERT_TYPES)
        print(f"[SEED] ✓ Created {len(ALERT_TYPES)} alert types")

        # Step 5: Create AttackPatterns
        print("[SEED] Step 5: Creating AttackPatterns...")
        for pattern in PATTERNS:
            await neo4j_client.run_query(
                "CREATE (:AttackPattern {id: $pattern_id, name: $name, fp_rate: $fp_rate, occurrence_count: $occurrence_count, confidence: $confidence})",
                pattern
            )
        summary["patterns"] = len(PATTERNS)
        print(f"[SEED] ✓ Created {len(PATTERNS)} attack patterns")

        # Step 6: Create Playbooks
        print("[SEED] Step 6: Creating Playbooks...")
        for playbook in PLAYBOOKS:
            await neo4j_client.run_query(
                "CREATE (:Playbook {id: $playbook_id, name: $name, sla_minutes: $sla_minutes})",
                playbook
            )
        summary["playbooks"] = len(PLAYBOOKS)
        print(f"[SEED] ✓ Created {len(PLAYBOOKS)} playbooks")

        # Step 7: Create SLAs
        print("[SEED] Step 7: Creating SLAs...")
        for sla in SLAS:
            await neo4j_client.run_query(
                "CREATE (:SLA {id: $id, name: $name, response_time_minutes: $response_time_minutes, severity: $severity})",
                sla
            )
        summary["slas"] = len(SLAS)
        print(f"[SEED] ✓ Created {len(SLAS)} SLAs")

        # Step 8: Create TravelContext
        print("[SEED] Step 8: Creating TravelContext...")
        for travel in TRAVEL_RECORDS:
            await neo4j_client.run_query(
                "CREATE (:TravelContext {id: $travel_id, user_id: $user_id, destination: $destination, start_date: $start_date, end_date: $end_date})",
                travel
            )
        summary["travel_contexts"] = len(TRAVEL_RECORDS)
        print(f"[SEED] ✓ Created {len(TRAVEL_RECORDS)} travel contexts")

        # Step 9: Create Alerts
        print("[SEED] Step 9: Creating Alerts...")
        for alert in ALERTS:
            await neo4j_client.run_query(
                "CREATE (:Alert {id: $alert_id, alert_type: $alert_type, severity: $severity, source: $source, source_location: $source_location, status: $status, description: $description, timestamp: datetime()})",
                alert
            )
        summary["alerts"] = len(ALERTS)
        print(f"[SEED] ✓ Created {len(ALERTS)} alerts")

        # Step 10: Create Decisions
        print("[SEED] Step 10: Creating Decisions...")
        for decision in DECISIONS:
            await neo4j_client.run_query(
                "CREATE (:Decision {id: $id, type: $type, reasoning: $reasoning, confidence: $confidence, timestamp: datetime($timestamp), alert_id: $alert_id, action_taken: $action_taken})",
                decision
            )
        summary["decisions"] = len(DECISIONS)
        print(f"[SEED] ✓ Created {len(DECISIONS)} decisions")

        # Step 11: Create DecisionContexts
        print("[SEED] Step 11: Creating DecisionContexts...")
        for context in CONTEXTS:
            await neo4j_client.run_query(
                "CREATE (:DecisionContext {id: $id, decision_id: $decision_id, patterns_matched: $patterns_matched, nodes_consulted: $nodes_consulted})",
                context
            )
        summary["decision_contexts"] = len(CONTEXTS)
        print(f"[SEED] ✓ Created {len(CONTEXTS)} decision contexts")

        # Step 12: Create EvolutionEvents
        print("[SEED] Step 12: Creating EvolutionEvents...")
        for evolution in EVOLUTIONS:
            await neo4j_client.run_query(
                "CREATE (:EvolutionEvent {id: $id, event_type: $event_type, triggered_by: $triggered_by, before_state: $before_state, after_state: $after_state, description: $description, timestamp: datetime($timestamp)})",
                evolution
            )
        summary["evolution_events"] = len(EVOLUTIONS)
        print(f"[SEED] ✓ Created {len(EVOLUTIONS)} evolution events")

        # Step 13: Create relationships
        print("[SEED] Step 13: Creating relationships...")

        # User -[:ASSIGNED_TO]-> Asset
        for user_id, asset_id in USER_ASSET_MAPPINGS:
            await neo4j_client.run_query(
                "MATCH (u:User {id: $user_id}), (a:Asset {id: $asset_id}) CREATE (u)-[:ASSIGNED_TO]->(a)",
                {"user_id": user_id, "asset_id": asset_id}
            )

        # User -[:HAS_TRAVEL]-> TravelContext
        for travel in TRAVEL_RECORDS:
            await neo4j_client.run_query(
                "MATCH (u:User {id: $user_id}), (t:TravelContext {id: $travel_id}) CREATE (u)-[:HAS_TRAVEL]->(t)",
                {"user_id": travel["user_id"], "travel_id": travel["travel_id"]}
            )

        # AlertType -[:HANDLED_BY]-> Playbook
        for alert_type, playbook_id in ALERT_PLAYBOOK_MAPPINGS:
            await neo4j_client.run_query(
                "MATCH (at:AlertType {id: $alert_type}), (pb:Playbook {id: $playbook_id}) CREATE (at)-[:HANDLED_BY]->(pb)",
                {"alert_type": alert_type, "playbook_id": playbook_id}
            )

        # Asset -[:SUBJECT_TO]-> SLA
        for asset_id, sla_id in ASSET_SLA_MAPPINGS:
            await neo4j_client.run_query(
                "MATCH (a:Asset {id: $asset_id}), (s:SLA {id: $sla_id}) CREATE (a)-[:SUBJECT_TO]->(s)",
                {"asset_id": asset_id, "sla_id": sla_id}
            )

        # Alert relationships (DETECTED_ON, INVOLVES, CLASSIFIED_AS)
        for alert in ALERTS:
            # Alert -[:DETECTED_ON]-> Asset
            await neo4j_client.run_query(
                "MATCH (alert:Alert {id: $alert_id}), (asset:Asset {id: $asset_id}) CREATE (alert)-[:DETECTED_ON]->(asset)",
                {"alert_id": alert["alert_id"], "asset_id": alert["asset_id"]}
            )
            # Alert -[:INVOLVES]-> User (only if user exists in User nodes)
            if alert["user_id"] in [u["user_id"] for u in USERS]:
                await neo4j_client.run_query(
                    "MATCH (alert:Alert {id: $alert_id}), (user:User {id: $user_id}) CREATE (alert)-[:INVOLVES]->(user)",
                    {"alert_id": alert["alert_id"], "user_id": alert["user_id"]}
                )
            # Alert -[:CLASSIFIED_AS]-> AlertType
            await neo4j_client.run_query(
                "MATCH (alert:Alert {id: $alert_id}), (type:AlertType {id: $alert_type}) CREATE (alert)-[:CLASSIFIED_AS]->(type)",
                {"alert_id": alert["alert_id"], "alert_type": alert["alert_type"]}
            )

        # Alert -[:MATCHES]-> AttackPattern
        for alert_id, pattern_id in ALERT_PATTERN_MAPPINGS:
            await neo4j_client.run_query(
                "MATCH (alert:Alert {id: $alert_id}), (pattern:AttackPattern {id: $pattern_id}) CREATE (alert)-[:MATCHES]->(pattern)",
                {"alert_id": alert_id, "pattern_id": pattern_id}
            )

        # Decision -[:FOR_ALERT]-> Alert
        for decision in DECISIONS:
            await neo4j_client.run_query(
                "MATCH (d:Decision {id: $decision_id}), (a:Alert {id: $alert_id}) CREATE (d)-[:FOR_ALERT]->(a)",
                {"decision_id": decision["id"], "alert_id": decision["alert_id"]}
            )

        # Decision -[:HAD_CONTEXT]-> DecisionContext
        for context in CONTEXTS:
            await neo4j_client.run_query(
                "MATCH (d:Decision {id: $decision_id}), (ctx:DecisionContext {id: $context_id}) CREATE (d)-[:HAD_CONTEXT]->(ctx)",
                {"decision_id": context["decision_id"], "context_id": context["id"]}
            )

        # Decision -[:TRIGGERED_EVOLUTION]-> EvolutionEvent (THE KEY!)
        for te in TRIGGERED_EVOLUTIONS:
            await neo4j_client.run_query(
                "MATCH (d:Decision {id: $decision_id}), (e:EvolutionEvent {id: $evolution_id}) CREATE (d)-[:TRIGGERED_EVOLUTION {impact: $impact, magnitude: $magnitude, timestamp: datetime()}]->(e)",
                te
            )

        print(f"[SEED] ✓ Created all relationships")

        print("[SEED] ✓ Database seeding completed successfully!")
        return summary

    except Exception as e:
        print(f"[SEED ERROR] Failed to seed database: {e}")
        import traceback
        traceback.print_exc()
        raise


async def verify_neo4j_seed() -> Dict[str, Any]:
    """
    Verify Neo4j database seeding by counting nodes and relationships.
    """
    print("[VERIFY] Verifying Neo4j seed data...")

    verification = {}

    try:
        # Count nodes by label
        node_counts_query = """
        MATCH (n)
        RETURN labels(n)[0] as label, count(n) as count
        ORDER BY label
        """
        results = await neo4j_client.run_query(node_counts_query)
        node_counts = {r["label"]: r["count"] for r in results}
        verification["node_counts"] = node_counts

        # Count TRIGGERED_EVOLUTION relationships
        te_query = """
        MATCH ()-[r:TRIGGERED_EVOLUTION]->()
        RETURN count(r) as count
        """
        te_result = await neo4j_client.run_query(te_query)
        verification["triggered_evolution_count"] = te_result[0]["count"] if te_result else 0

        # Total counts
        total_nodes = sum(node_counts.values())
        verification["total_nodes"] = total_nodes

        print(f"[VERIFY] Total nodes: {total_nodes}")
        print(f"[VERIFY] TRIGGERED_EVOLUTION relationships: {verification['triggered_evolution_count']}")

        return verification

    except Exception as e:
        print(f"[VERIFY ERROR] Failed to verify seed: {e}")
        raise
