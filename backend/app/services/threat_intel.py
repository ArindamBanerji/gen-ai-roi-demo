"""
Threat Intel Service — backward-compat wrapper (C3 refactor)

All Pulsedive logic (constants, IOC list, fallback data, Neo4j writes) now
lives in backend/app/connectors/pulsedive.py.

This module exists solely so that existing callers (routers/graph.py) can
continue to call refresh_threat_intel() without modification.

The return dict preserves the original seven-key shape:
    source, indicators_ingested, relationships_created,
    enrichment_summary, live_attempted, live_succeeded, timestamp
"""
from typing import Any, Dict


async def refresh_threat_intel() -> Dict[str, Any]:
    """
    Refresh Pulsedive threat intelligence.

    Delegates to PulsediveConnector.refresh() and reconstructs the original
    dict format (including Pulsedive-specific live_attempted / live_succeeded
    fields that are not part of the generic ConnectorResult).
    """
    # Deferred imports avoid any circular-import risk at module load time.
    from app.connectors.registry import registry as connector_registry
    from app.connectors.pulsedive import PulsediveConnector

    # Prefer the registered singleton so stats stay consistent across callers;
    # fall back to a fresh instance if the registry isn't populated yet
    # (e.g. during unit tests or early startup).
    connector: PulsediveConnector = (
        connector_registry.get("pulsedive") or PulsediveConnector()
    )

    result = await connector.refresh()

    return {
        "source":                result.source,
        "indicators_ingested":   result.indicators_ingested,
        "relationships_created": result.relationships_created,
        "enrichment_summary":    result.enrichment_summary,
        "live_attempted":        connector._last_live_attempted,
        "live_succeeded":        connector._last_live_succeeded,
        "timestamp":             result.timestamp,
    }
