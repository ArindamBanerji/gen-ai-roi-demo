"""
CrowdStrikeMockConnector — UCL connector simulating CrowdStrike Falcon EDR.

No real API key required. All device records are hardcoded to match the
canonical demo assets seeded by seed_neo4j.py.

Behaviour:
  refresh()  — writes :CrowdStrikeEnrichment nodes and
               (Asset)-[:EDR_MANAGED_BY]->(CrowdStrikeEnrichment) edges.
               MERGE throughout so calling refresh() twice is idempotent.
  health_check() — always healthy (no external dependency).

AWS-PROD-ACCOUNT is intentionally absent — cloud accounts do not run the
Falcon sensor.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List

from app.connectors.base import ConnectorResult, HealthStatus, UCLConnector
from app.db.neo4j import neo4j_client


logger = logging.getLogger(__name__)


# ============================================================================
# Mock EDR device records (keyed by Asset.hostname)
# ============================================================================

EDR_DEVICES: List[Dict] = [
    {
        "hostname":          "LAPTOP-JSMITH",
        "device_id":         "CS-001",
        "os":                "Windows 11",
        "last_seen":         "2026-02-26",
        "prevention_status": "active",
        "sensor_version":    "7.14.16804",
    },
    {
        "hostname":          "LAPTOP-MCHEN",
        "device_id":         "CS-002",
        "os":                "Windows 11",
        "last_seen":         "2026-02-25",
        "prevention_status": "active",
        "sensor_version":    "7.14.16804",
    },
    {
        "hostname":          "SRV-WEB-03",
        "device_id":         "CS-003",
        "os":                "CentOS 8",
        "last_seen":         "2026-02-20",
        "prevention_status": "reduced",
        "sensor_version":    "7.12.15409",
    },
    # AWS-PROD-ACCOUNT: no EDR — cloud asset, Falcon sensor not applicable
]


# ============================================================================
# CrowdStrikeMockConnector
# ============================================================================

class CrowdStrikeMockConnector(UCLConnector):
    """
    UCL connector for CrowdStrike Falcon EDR (mock/demo mode).

    Writes :CrowdStrikeEnrichment nodes linked to existing :Asset nodes
    via [:EDR_MANAGED_BY] relationships.  All data is hardcoded — no API
    key or network access required.
    """

    name        = "crowdstrike"
    source_type = "edr"
    description = "CrowdStrike Falcon EDR — device inventory, prevention status, sensor version (mock)"

    # ------------------------------------------------------------------
    # UCLConnector.refresh()
    # ------------------------------------------------------------------

    async def refresh(self) -> ConnectorResult:
        """
        Write mock CrowdStrike EDR data to Neo4j.

        Steps:
          1. MERGE :CrowdStrikeEnrichment nodes for each managed device.
          2. MERGE (Asset)-[:EDR_MANAGED_BY]->(CrowdStrikeEnrichment) edges.
          3. Return ConnectorResult summary.
        """

        # -------------------------------------------------------------------
        # Step 1 — MERGE :CrowdStrikeEnrichment nodes (idempotent)
        # -------------------------------------------------------------------
        indicators_ingested = 0
        merge_node_query = """
        MERGE (cs:CrowdStrikeEnrichment {device_id: $device_id})
        SET cs.hostname          = $hostname,
            cs.os                = $os,
            cs.last_seen         = $last_seen,
            cs.prevention_status = $prevention_status,
            cs.sensor_version    = $sensor_version,
            cs.refreshed_at      = datetime()
        RETURN cs.device_id AS device_id
        """

        for device in EDR_DEVICES:
            try:
                await neo4j_client.run_query(merge_node_query, {
                    "device_id":         device["device_id"],
                    "hostname":          device["hostname"],
                    "os":                device["os"],
                    "last_seen":         device["last_seen"],
                    "prevention_status": device["prevention_status"],
                    "sensor_version":    device["sensor_version"],
                })
                indicators_ingested += 1
                print(
                    f"[CROWDSTRIKE] MERGE CrowdStrikeEnrichment "
                    f"device_id={device['device_id']} hostname={device['hostname']}"
                )
            except Exception as exc:
                print(f"[CROWDSTRIKE] Failed to write {device['device_id']} to Neo4j: {exc}")

        # -------------------------------------------------------------------
        # Step 2 — MERGE (Asset)-[:EDR_MANAGED_BY]->(CrowdStrikeEnrichment)
        # -------------------------------------------------------------------
        relationships_created = 0
        link_query = """
        MATCH (asset:Asset {hostname: $hostname})
        MATCH (cs:CrowdStrikeEnrichment {device_id: $device_id})
        MERGE (asset)-[r:EDR_MANAGED_BY]->(cs)
        SET r.linked_at = datetime()
        RETURN asset.hostname AS hostname
        """

        for device in EDR_DEVICES:
            try:
                result = await neo4j_client.run_query(link_query, {
                    "hostname":  device["hostname"],
                    "device_id": device["device_id"],
                })
                if result:
                    relationships_created += 1
                    print(
                        f"[CROWDSTRIKE] Linked Asset({device['hostname']}) "
                        f"-[:EDR_MANAGED_BY]-> CrowdStrikeEnrichment({device['device_id']})"
                    )
                else:
                    print(
                        f"[CROWDSTRIKE] No Asset found for hostname={device['hostname']} "
                        f"— skipping EDR_MANAGED_BY edge"
                    )
            except Exception as exc:
                print(f"[CROWDSTRIKE] Failed to link {device['hostname']}: {exc}")

        # -------------------------------------------------------------------
        # Step 3 — Build ConnectorResult
        # -------------------------------------------------------------------
        enrichment_summary = [
            {
                "device_id":         d["device_id"],
                "hostname":          d["hostname"],
                "os":                d["os"],
                "last_seen":         d["last_seen"],
                "prevention_status": d["prevention_status"],
                "sensor_version":    d["sensor_version"],
            }
            for d in EDR_DEVICES
        ]

        print(
            f"[CROWDSTRIKE] refresh complete — "
            f"{indicators_ingested} devices ingested, "
            f"{relationships_created} EDR_MANAGED_BY edges created"
        )

        return ConnectorResult(
            source="crowdstrike_mock",
            indicators_ingested=indicators_ingested,
            relationships_created=relationships_created,
            enrichment_summary=enrichment_summary,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    # ------------------------------------------------------------------
    # UCLConnector.health_check()
    # ------------------------------------------------------------------

    async def health_check(self) -> HealthStatus:
        """
        Always healthy — mock connector requires no API key or network access.
        """
        return HealthStatus(
            healthy=True,
            source=self.name,
            message="Mock connector — no API key required",
        )

    # ------------------------------------------------------------------
    # UCLConnector.get_config_schema()
    # ------------------------------------------------------------------

    def get_config_schema(self) -> Dict:
        """No environment variables required for the mock connector."""
        return {}
