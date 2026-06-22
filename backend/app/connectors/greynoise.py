"""
GreyNoiseConnector -- UCL connector for GreyNoise IP enrichment.

GreyNoise Community API classifies IPs as malicious, benign, or unknown and
flags whether they are background internet noise or part of a riot (known
safe) service.

Behaviour:
  a. If GREYNOISE_API_KEY is set: call the GreyNoise community API for each
     demo IP (0.5 s between requests; free tier = 50 req/day).
     Per-IP failures fall back to the hardcoded entry for that IP.
  b. If no key, or all calls fail: use the full hardcoded fallback set.

NOTE: GreyNoise Community only supports IPs, not domains. Domain IOCs in the
Pulsedive curated list are silently skipped.

After enrichment:
  c. MERGE :GreyNoiseEnrichment nodes into Neo4j (idempotent -- updates
     refreshed_at if the node already exists).
  d. MERGE :ENRICHED_BY relationships from :ThreatIntel to :GreyNoiseEnrichment.
"""
import asyncio
import json as _json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.connectors.base import ConnectorResult, HealthStatus, UCLConnector
from app.db.neo4j import neo4j_client


logger = logging.getLogger(__name__)


def _S(val) -> str:
    """Serialize a Python value to an AGE-safe inline Cypher literal."""
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, (list, tuple)):
        return "'" + _json.dumps(val).replace("'", "\\'") + "'"
    return "'" + str(val).replace("\\", "\\\\").replace("'", "\\'") + "'"


# ============================================================================
# Configuration
# ============================================================================

GREYNOISE_BASE_URL = "https://api.greynoise.io/v3/community"


# ============================================================================
# Demo IPs to enrich (IPs only — GreyNoise Community does not support domains)
# ============================================================================

DEMO_IPS: List[str] = [
    "103.15.42.17",    # Singapore IP -- ties to ALERT-7823 travel login
    "185.220.101.34",  # Known Tor exit node
    "45.33.32.156",    # Scanning / reconnaissance source
]


# ============================================================================
# Hardcoded fallback data (used when API key absent or per-IP call fails)
# ============================================================================

HARDCODED_FALLBACK: Dict[str, Dict[str, Any]] = {
    "103.15.42.17": {
        "ip":             "103.15.42.17",
        "classification": "malicious",
        "noise":          True,
        "riot":           False,
        "name":           "Unknown",
        "link":           "https://viz.greynoise.io/ip/103.15.42.17",
        "last_seen":      "2025-11-20",
        "source":         "hardcoded_fallback",
    },
    "185.220.101.34": {
        "ip":             "185.220.101.34",
        "classification": "benign",
        "noise":          True,
        "riot":           True,
        "name":           "Tor Project",
        "link":           "https://viz.greynoise.io/ip/185.220.101.34",
        "last_seen":      "2025-12-01",
        "source":         "hardcoded_fallback",
    },
    "45.33.32.156": {
        "ip":             "45.33.32.156",
        "classification": "unknown",
        "noise":          True,
        "riot":           False,
        "name":           "Unknown",
        "link":           "https://viz.greynoise.io/ip/45.33.32.156",
        "last_seen":      "2025-10-15",
        "source":         "hardcoded_fallback",
    },
}


# ============================================================================
# Private helper — fetch one IP from GreyNoise Community API
# ============================================================================

async def _fetch_greynoise(
    ip: str,
    key: str,
    client: httpx.AsyncClient,
) -> Optional[Dict[str, Any]]:
    """
    Fetch one IP from the GreyNoise Community API.
    Returns a normalized dict on success, None on any failure.

    GreyNoise Community response shape:
        {
          "ip": "1.2.3.4",
          "noise": true,
          "riot": false,
          "classification": "malicious",
          "name": "Unknown",
          "link": "https://viz.greynoise.io/ip/1.2.3.4",
          "last_seen": "2025-01-15",
          "message": "Success"
        }
    """
    try:
        resp = await client.get(
            f"{GREYNOISE_BASE_URL}/{ip}",
            headers={"key": key},
            timeout=10.0,
        )

        # 404 means GreyNoise has no data for this IP (not malicious = unlisted)
        if resp.status_code == 404:
            logger.info("[GREYNOISE] No data for %s (404 -- unlisted)", ip)
            return None

        resp.raise_for_status()
        data = resp.json()

        if data.get("message") == "This IP is commonly seen scanning the internet.":
            # Sometimes returned instead of a full record
            logger.info("[GREYNOISE] Minimal record for %s: scanning IP", ip)

        return {
            "ip":             ip,
            "classification": data.get("classification", "unknown"),
            "noise":          bool(data.get("noise", False)),
            "riot":           bool(data.get("riot", False)),
            "name":           data.get("name", "Unknown"),
            "link":           data.get("link", f"https://viz.greynoise.io/ip/{ip}"),
            "last_seen":      data.get("last_seen", "")[:10],
            "source":         "greynoise_live",
        }

    except httpx.RequestError as exc:
        logger.warning("[GREYNOISE] HTTP error fetching %s: %s", ip, exc)
        return None
    except Exception as exc:
        logger.warning("[GREYNOISE] Unexpected error parsing %s: %s", ip, exc)
        return None


# ============================================================================
# GreyNoiseConnector
# ============================================================================

class GreyNoiseConnector(UCLConnector):
    """
    UCL connector for GreyNoise community IP enrichment.

    Live API if GREYNOISE_API_KEY is set; hardcoded fallback otherwise.
    Writes :GreyNoiseEnrichment nodes and :ENRICHED_BY edges to Neo4j,
    cross-referencing existing :ThreatIntel nodes seeded by Pulsedive.
    """

    name        = "greynoise"
    source_type = "enrichment"
    description = "GreyNoise community IP enrichment -- classification, noise, riot flags"

    # ------------------------------------------------------------------
    # UCLConnector.refresh()
    # ------------------------------------------------------------------

    async def refresh(self) -> ConnectorResult:
        """
        Refresh GreyNoise enrichment for all demo IPs.

        Steps:
          1. Fetch from GreyNoise live API (if key present), fallback per-IP.
          2. MERGE :GreyNoiseEnrichment nodes into Neo4j.
          3. MERGE :ENRICHED_BY relationships from :ThreatIntel to :GreyNoiseEnrichment.
          4. Return ConnectorResult summary.
        """
        api_key = os.environ.get("GREYNOISE_API_KEY")
        enriched: List[Dict[str, Any]] = []
        live_attempted = 0
        live_succeeded = 0
        source = "hardcoded_fallback"

        # -------------------------------------------------------------------
        # Step 1 — Live API or hardcoded fallback
        # -------------------------------------------------------------------
        if api_key:
            print("[GREYNOISE] API key present -- attempting live enrichment")
            async with httpx.AsyncClient() as client:
                for ip in DEMO_IPS:
                    live_attempted += 1
                    result = await _fetch_greynoise(ip, api_key, client)
                    if result:
                        enriched.append(result)
                        live_succeeded += 1
                        print(f"[GREYNOISE] Live data fetched for {ip}")
                    else:
                        fallback = HARDCODED_FALLBACK.get(ip)
                        if fallback:
                            enriched.append(dict(fallback))
                            print(f"[GREYNOISE] Fallback used for {ip}")
                    # Rate limit: 50 req/day — space requests to be safe
                    await asyncio.sleep(0.5)

            source = "greynoise_live" if live_succeeded > 0 else "hardcoded_fallback"

        # Full fallback when no key or every call failed
        if not enriched:
            print("[GREYNOISE] No live data -- using full hardcoded fallback set")
            enriched = [dict(v) for v in HARDCODED_FALLBACK.values()]
            source = "hardcoded_fallback"

        print(
            f"[GREYNOISE] {len(enriched)} IPs ready "
            f"(source={source}, live_ok={live_succeeded}/{live_attempted})"
        )

        # -------------------------------------------------------------------
        # Step 2 — Write :GreyNoiseEnrichment nodes (idempotent)
        # AGE has no MERGE — MATCH first, SET if found, CREATE if absent.
        # -------------------------------------------------------------------
        indicators_ingested = 0
        _now_epoch = int(time.time() * 1000)

        for entry in enriched:
            try:
                _ip = _S(entry["ip"])
                existing = await neo4j_client.run_query(
                    f"MATCH (gn:GreyNoiseEnrichment {{ip: {_ip}}}) RETURN gn"
                )
                if existing:
                    await neo4j_client.run_query(
                        f"MATCH (gn:GreyNoiseEnrichment {{ip: {_ip}}})"
                        f" SET gn.classification = {_S(entry.get('classification', 'unknown'))},"
                        f"     gn.noise = {_S(entry.get('noise', False))},"
                        f"     gn.riot = {_S(entry.get('riot', False))},"
                        f"     gn.name = {_S(entry.get('name', 'Unknown'))},"
                        f"     gn.link = {_S(entry.get('link', ''))},"
                        f"     gn.last_seen = {_S(entry.get('last_seen', ''))},"
                        f"     gn.source = {_S(entry.get('source', source))},"
                        f"     gn.refreshed_at = {_S(_now_epoch)}"
                    )
                else:
                    await neo4j_client.run_query(
                        f"CREATE (gn:GreyNoiseEnrichment {{"
                        f" ip: {_ip},"
                        f" classification: {_S(entry.get('classification', 'unknown'))},"
                        f" noise: {_S(entry.get('noise', False))},"
                        f" riot: {_S(entry.get('riot', False))},"
                        f" name: {_S(entry.get('name', 'Unknown'))},"
                        f" link: {_S(entry.get('link', ''))},"
                        f" last_seen: {_S(entry.get('last_seen', ''))},"
                        f" source: {_S(entry.get('source', source))},"
                        f" refreshed_at: {_S(_now_epoch)}"
                        f"}})"
                    )
                indicators_ingested += 1
            except Exception as exc:
                print(f"[GREYNOISE] Failed to write {entry['ip']} to AGE: {exc}")

        # -------------------------------------------------------------------
        # Step 3 — Write :ENRICHED_BY from :ThreatIntel to :GreyNoiseEnrichment
        # AGE has no MERGE — check edge existence then CREATE if absent.
        # -------------------------------------------------------------------
        relationships_created = 0
        for entry in enriched:
            try:
                _ip = _S(entry["ip"])
                edge_check = await neo4j_client.run_query(
                    f"MATCH (ti:ThreatIntel {{value: {_ip}}})"
                    f"-[:ENRICHED_BY]->(gn:GreyNoiseEnrichment {{ip: {_ip}}}) RETURN ti"
                )
                if not edge_check:
                    await neo4j_client.run_query(
                        f"MATCH (ti:ThreatIntel {{value: {_ip}}})"
                        f" MATCH (gn:GreyNoiseEnrichment {{ip: {_ip}}})"
                        f" CREATE (ti)-[:ENRICHED_BY {{linked_at: {_S(_now_epoch)}}}]->(gn)"
                    )
                relationships_created += 1
                print(f"[GREYNOISE] Linked ThreatIntel({entry['ip']}) -[:ENRICHED_BY]-> GreyNoiseEnrichment")
            except Exception as exc:
                print(f"[GREYNOISE] Failed to link {entry['ip']}: {exc}")

        # -------------------------------------------------------------------
        # Step 4 — Build ConnectorResult
        # -------------------------------------------------------------------
        enrichment_summary = [
            {
                "ip":             entry["ip"],
                "classification": entry.get("classification"),
                "noise":          entry.get("noise"),
                "riot":           entry.get("riot"),
                "name":           entry.get("name"),
                "source":         entry.get("source", source),
            }
            for entry in enriched
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
        Check whether the GreyNoise API key is configured.

        Avoids pinging the live API to conserve the 50 req/day free-tier quota.
        Reports healthy=True when the key is present; False when absent
        (connector will produce data via hardcoded fallback, but the live
        source is not reachable).
        """
        api_key = os.environ.get("GREYNOISE_API_KEY")
        if api_key:
            return HealthStatus(
                healthy=True,
                source=self.name,
                message="API key present",
            )
        return HealthStatus(
            healthy=False,
            source=self.name,
            message="GREYNOISE_API_KEY not set -- using hardcoded fallback",
        )

    # ------------------------------------------------------------------
    # UCLConnector.get_config_schema()
    # ------------------------------------------------------------------

    def get_config_schema(self) -> Dict:
        return {
            "GREYNOISE_API_KEY": {
                "required":    True,
                "description": "GreyNoise community API key (free tier available)",
                "docs":        "https://docs.greynoise.io/docs/using-the-greynoise-community-api",
            }
        }
