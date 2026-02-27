"""
UCL Connector Base — Abstract base class for all Universal Context Layer connectors.

Every data source (Pulsedive, GreyNoise, CrowdStrike, ...) implements UCLConnector
and returns ConnectorResult / HealthStatus from its two required async methods.

Design: keep this file small. No Neo4j or HTTP imports here — those belong
in the concrete connector implementations.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List


# ---------------------------------------------------------------------------
# Return-value dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ConnectorResult:
    """Summary returned by UCLConnector.refresh()."""
    source: str                          # e.g. "pulsedive_live", "greynoise_fallback"
    indicators_ingested: int             # IOC / detection nodes written to Neo4j
    relationships_created: int           # Edges created / updated in Neo4j
    enrichment_summary: List[Dict]       # Per-indicator detail rows (for logs / UI)
    timestamp: str = field(             # ISO-8601 UTC
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict:
        return {
            "source": self.source,
            "indicators_ingested": self.indicators_ingested,
            "relationships_created": self.relationships_created,
            "enrichment_summary": self.enrichment_summary,
            "timestamp": self.timestamp,
        }


@dataclass
class HealthStatus:
    """Summary returned by UCLConnector.health_check()."""
    healthy: bool
    source: str                          # connector name, e.g. "pulsedive"
    message: str                         # "OK", "Rate limited", "API key missing"
    last_checked: str = field(          # ISO-8601 UTC
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict:
        return {
            "healthy": self.healthy,
            "source": self.source,
            "message": self.message,
            "last_checked": self.last_checked,
        }


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class UCLConnector(ABC):
    """
    Abstract base class for all UCL data source connectors.

    Subclasses MUST:
    - Set `name` (unique slug, e.g. "pulsedive")
    - Set `source_type` (one of: "threat_intel", "enrichment", "alert_source")
    - Implement refresh(), health_check(), get_config_schema()

    Subclasses MAY:
    - Set `description` (shown in /api/graph/connectors listing)
    """

    # Concrete subclasses must set these as class attributes
    name: str
    source_type: str
    description: str = ""

    @abstractmethod
    async def refresh(self) -> ConnectorResult:
        """
        Pull fresh data from the source, write to Neo4j, return a summary.

        Must be idempotent: running refresh() twice should not create duplicates
        (use MERGE in Cypher queries, not CREATE).
        """

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """
        Verify the source is reachable and credentials are valid.

        Should be fast (< 2 seconds). Do NOT write any data.
        """

    @abstractmethod
    def get_config_schema(self) -> Dict:
        """
        Describe the environment variables this connector requires.

        Example return value:
            {
                "PULSEDIVE_API_KEY": {
                    "required": True,
                    "description": "Pulsedive community API key",
                    "docs": "https://pulsedive.com/api/"
                }
            }
        """
