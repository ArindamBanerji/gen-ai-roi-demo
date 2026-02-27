"""
PulsediveConnector — UCL connector for Pulsedive threat intelligence.

Wraps the logic that was previously in services/threat_intel.py.
threat_intel.py is now a thin backward-compat wrapper that delegates here.

Behaviour:
  a. If PULSEDIVE_API_KEY is set: call the Pulsedive live API for each IOC
     (0.5 s between requests for rate limiting). Per-IOC failures fall back
     to the hardcoded entry for that specific indicator.
  b. If no key, or all calls fail: use the full hardcoded fallback set.

After enrichment:
  c. MERGE :ThreatIntel nodes into Neo4j (idempotent — updates timestamp if
     the node already exists).
  d. MERGE :ASSOCIATED_WITH relationships to relevant :Alert nodes.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.connectors.base import ConnectorResult, HealthStatus, UCLConnector
from app.db.neo4j import neo4j_client


logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

PULSEDIVE_BASE_URL = "https://pulsedive.com/api/info.php"


# ============================================================================
# Curated IOC list
# ============================================================================

DEMO_IOCS: List[Dict[str, str]] = [
    {"value": "103.15.42.17",                 "context": "Singapore IP range — ties to ALERT-7823"},
    {"value": "185.220.101.34",               "context": "Known Tor exit node"},
    {"value": "cobaltstrike.github.io",       "context": "C2 framework domain"},
    {"value": "45.33.32.156",                 "context": "Scanning source — reconnaissance"},
    {"value": "malware-traffic-analysis.net", "context": "Malware distribution tracker"},
]


# ============================================================================
# Hardcoded fallback data (used when API key absent or per-IOC call fails)
# ============================================================================

HARDCODED_FALLBACK: Dict[str, Dict[str, Any]] = {
    "103.15.42.17": {
        "value":        "103.15.42.17",
        "type":         "ip",
        "severity":     "high",
        "source":       "hardcoded_fallback",
        "risk_factors": [
            "Singapore exit node",
            "associated with anomalous login pattern",
            "seen in 12 incidents",
        ],
        "first_seen":   "2024-08-15",
        "last_updated": "2025-11-20",
        "context":      "Singapore IP range — ties to ALERT-7823",
    },
    "185.220.101.34": {
        "value":        "185.220.101.34",
        "type":         "ip",
        "severity":     "critical",
        "source":       "hardcoded_fallback",
        "risk_factors": [
            "Tor exit node",
            "used in 47 malicious campaigns",
            "abuse DB listed",
        ],
        "first_seen":   "2023-03-10",
        "last_updated": "2025-12-01",
        "context":      "Known Tor exit node",
    },
    "cobaltstrike.github.io": {
        "value":        "cobaltstrike.github.io",
        "type":         "domain",
        "severity":     "critical",
        "source":       "hardcoded_fallback",
        "risk_factors": [
            "C2 framework indicator",
            "active in nation-state campaigns",
            "Cobalt Strike beacon",
        ],
        "first_seen":   "2024-01-05",
        "last_updated": "2025-11-28",
        "context":      "C2 framework domain",
    },
    "45.33.32.156": {
        "value":        "45.33.32.156",
        "type":         "ip",
        "severity":     "medium",
        "source":       "hardcoded_fallback",
        "risk_factors": [
            "reconnaissance scanning",
            "port sweep activity",
            "shodan listed",
        ],
        "first_seen":   "2024-06-22",
        "last_updated": "2025-10-15",
        "context":      "Scanning source — reconnaissance",
    },
    "malware-traffic-analysis.net": {
        "value":        "malware-traffic-analysis.net",
        "type":         "domain",
        "severity":     "medium",
        "source":       "hardcoded_fallback",
        "risk_factors": [
            "malware sample distribution",
            "PCAP repository",
            "threat research indicator",
        ],
        "first_seen":   "2022-11-01",
        "last_updated": "2025-12-01",
        "context":      "Malware distribution tracker",
    },
}

# Pulsedive risk string → internal severity
_RISK_TO_SEVERITY: Dict[str, str] = {
    "none":     "low",
    "low":      "low",
    "medium":   "medium",
    "high":     "high",
    "critical": "critical",
    "unknown":  "medium",
}

# Alert nodes with a known direct IOC association (for :ASSOCIATED_WITH edges)
ALERT_IOC_MAP: Dict[str, List[str]] = {
    "ALERT-7823": ["103.15.42.17"],  # Singapore IP ties directly to travel login alert
}


# ============================================================================
# Private helper — fetch one indicator from Pulsedive live API
# ============================================================================

async def _fetch_pulsedive(
    value: str,
    key: str,
    client: httpx.AsyncClient,
) -> Optional[Dict[str, Any]]:
    """
    Fetch one indicator from the Pulsedive API.
    Returns a normalized dict on success, None on any failure.
    """
    try:
        resp = await client.get(
            PULSEDIVE_BASE_URL,
            params={"indicator": value, "key": key},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()

        # Pulsedive returns {"error": "..."} for unknown indicators or bad keys
        if "error" in data:
            logger.warning(
                "[PULSEDIVE] API error for %s: %s", value, data["error"]
            )
            return None

        # Normalize type to ip / domain
        raw_type = data.get("type", "unknown").lower()
        if raw_type in ("ip", "ipv4", "ipv6"):
            ioc_type = "ip"
        elif raw_type in ("domain", "url", "fqdn"):
            ioc_type = "domain"
        else:
            ioc_type = raw_type

        # Extract risk factors from threats array (cap at 3)
        risk_factors: List[str] = []
        for threat in data.get("threats", [])[:3]:
            name = threat.get("name") or threat.get("category")
            if name:
                risk_factors.append(name)

        # Supplement with geo if available
        geo = data.get("properties", {}).get("geo", {})
        if geo.get("country"):
            risk_factors.append(f"Country: {geo['country']}")

        risk = data.get("risk", "unknown")
        if not risk_factors:
            risk_factors = [f"Risk level: {risk}"]

        stamp_seen    = data.get("stamp_seen", "") or ""
        stamp_updated = data.get("stamp_updated", "") or stamp_seen

        return {
            "value":        value,
            "type":         ioc_type,
            "severity":     _RISK_TO_SEVERITY.get(risk.lower(), "medium"),
            "source":       "pulsedive_live",
            "risk_factors": risk_factors,
            "first_seen":   stamp_seen[:10],
            "last_updated": stamp_updated[:10],
        }

    except httpx.RequestError as exc:
        logger.warning("[PULSEDIVE] HTTP error fetching %s: %s", value, exc)
        return None
    except Exception as exc:
        logger.warning("[PULSEDIVE] Unexpected error parsing %s: %s", value, exc)
        return None


# ============================================================================
# PulsediveConnector
# ============================================================================

class PulsediveConnector(UCLConnector):
    """
    UCL connector for Pulsedive community threat intelligence.

    Live API if PULSEDIVE_API_KEY is set; hardcoded fallback otherwise.
    Writes :ThreatIntel nodes and :ASSOCIATED_WITH edges to Neo4j.
    """

    name        = "pulsedive"
    source_type = "threat_intel"
    description = "Pulsedive community threat intelligence — live API with hardcoded fallback"

    def __init__(self) -> None:
        # Populated by refresh() so the backward-compat wrapper can read them
        self._last_live_attempted: int = 0
        self._last_live_succeeded: int = 0

    # ------------------------------------------------------------------
    # UCLConnector.refresh()
    # ------------------------------------------------------------------

    async def refresh(self) -> ConnectorResult:
        """
        Refresh threat intel for all curated IOCs.

        Steps:
          1. Fetch from Pulsedive live API (if key present), fallback per-IOC.
          2. MERGE :ThreatIntel nodes into Neo4j.
          3. MERGE :ASSOCIATED_WITH relationships to :Alert nodes.
          4. Return ConnectorResult summary.
        """
        api_key = os.environ.get("PULSEDIVE_API_KEY")
        enriched: List[Dict[str, Any]] = []
        live_attempted = 0
        live_succeeded = 0
        source = "hardcoded_fallback"

        # ---------------------------------------------------------------
        # Step 1 — Live API or hardcoded fallback
        # ---------------------------------------------------------------
        if api_key:
            print("[PULSEDIVE] API key present — attempting live enrichment")
            async with httpx.AsyncClient() as client:
                for ioc in DEMO_IOCS:
                    live_attempted += 1
                    result = await _fetch_pulsedive(ioc["value"], api_key, client)
                    if result:
                        result["context"] = ioc["context"]
                        enriched.append(result)
                        live_succeeded += 1
                        print(f"[PULSEDIVE] Live data fetched for {ioc['value']}")
                    else:
                        # Per-IOC fallback when Pulsedive errors or times out
                        fallback = HARDCODED_FALLBACK.get(ioc["value"])
                        if fallback:
                            enriched.append(dict(fallback))
                            print(f"[PULSEDIVE] Fallback used for {ioc['value']}")
                    # Rate limit: 0.5 s between requests
                    await asyncio.sleep(0.5)

            source = "pulsedive_live" if live_succeeded > 0 else "hardcoded_fallback"

        # Full fallback when no key or every call failed
        if not enriched:
            print("[PULSEDIVE] No live data — using full hardcoded fallback set")
            enriched = [dict(v) for v in HARDCODED_FALLBACK.values()]
            source = "hardcoded_fallback"

        print(
            f"[PULSEDIVE] {len(enriched)} indicators ready "
            f"(source={source}, live_ok={live_succeeded}/{live_attempted})"
        )

        # Expose for backward-compat wrapper
        self._last_live_attempted = live_attempted
        self._last_live_succeeded = live_succeeded

        # ---------------------------------------------------------------
        # Step 2 — MERGE :ThreatIntel nodes (idempotent)
        # ---------------------------------------------------------------
        indicators_ingested = 0
        merge_query = """
        MERGE (ti:ThreatIntel {value: $value})
        SET ti.type         = $type,
            ti.severity     = $severity,
            ti.source       = $source,
            ti.risk_factors = $risk_factors,
            ti.first_seen   = $first_seen,
            ti.last_updated = $last_updated,
            ti.context      = $context,
            ti.refreshed_at = datetime()
        RETURN ti.value AS value
        """

        for ioc in enriched:
            try:
                await neo4j_client.run_query(merge_query, {
                    "value":        ioc["value"],
                    "type":         ioc.get("type", "unknown"),
                    "severity":     ioc.get("severity", "medium"),
                    "source":       ioc.get("source", source),
                    "risk_factors": ioc.get("risk_factors", []),
                    "first_seen":   ioc.get("first_seen", ""),
                    "last_updated": ioc.get("last_updated", ""),
                    "context":      ioc.get("context", ""),
                })
                indicators_ingested += 1
            except Exception as exc:
                print(f"[PULSEDIVE] Failed to write {ioc['value']} to Neo4j: {exc}")

        # ---------------------------------------------------------------
        # Step 3 — MERGE :ASSOCIATED_WITH relationships to :Alert nodes
        # ---------------------------------------------------------------
        relationships_created = 0
        assoc_query = """
        MATCH (ti:ThreatIntel {value: $ioc_value})
        MATCH (alert:Alert {id: $alert_id})
        MERGE (ti)-[r:ASSOCIATED_WITH]->(alert)
        SET r.linked_at = datetime()
        RETURN ti.value AS ioc, alert.id AS alert_id
        """

        for alert_id, ioc_values in ALERT_IOC_MAP.items():
            for ioc_value in ioc_values:
                try:
                    result = await neo4j_client.run_query(assoc_query, {
                        "ioc_value": ioc_value,
                        "alert_id":  alert_id,
                    })
                    if result:
                        relationships_created += 1
                        print(f"[PULSEDIVE] Linked {ioc_value} → {alert_id}")
                except Exception as exc:
                    print(f"[PULSEDIVE] Failed to link {ioc_value} → {alert_id}: {exc}")

        # ---------------------------------------------------------------
        # Step 4 — Build ConnectorResult
        # ---------------------------------------------------------------
        enrichment_summary = [
            {
                "value":    ioc["value"],
                "type":     ioc.get("type"),
                "severity": ioc.get("severity"),
                "source":   ioc.get("source", source),
                "context":  ioc.get("context", ""),
            }
            for ioc in enriched
        ]

        return ConnectorResult(
            source=source,
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
        Check whether the Pulsedive API key is configured.

        Avoids pinging the live API to conserve the free-tier rate limit.
        Reports healthy=True when the key is present; False when absent
        (connector will produce data via hardcoded fallback, but the LIVE
        source is not reachable).
        """
        api_key = os.environ.get("PULSEDIVE_API_KEY")
        if api_key:
            return HealthStatus(
                healthy=True,
                source=self.name,
                message="API key present",
            )
        return HealthStatus(
            healthy=False,
            source=self.name,
            message="PULSEDIVE_API_KEY not set — using hardcoded fallback",
        )

    # ------------------------------------------------------------------
    # UCLConnector.get_config_schema()
    # ------------------------------------------------------------------

    def get_config_schema(self) -> Dict:
        return {
            "PULSEDIVE_API_KEY": {
                "required":    True,
                "description": "Pulsedive community API key (free tier available)",
                "docs":        "https://pulsedive.com/api/",
            }
        }
