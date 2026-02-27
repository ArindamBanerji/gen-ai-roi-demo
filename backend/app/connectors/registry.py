"""
ConnectorRegistry — Central registry for all UCL data source connectors.

Usage pattern:
    # 1. In service module (or main.py at startup):
    from app.connectors.registry import registry
    registry.register(PulsediveConnector())

    # 2. In a router endpoint:
    from app.connectors.registry import registry
    results = await registry.refresh_all()

The module-level `registry` singleton is the single source of truth.
Adding a new connector only requires registering it in main.py startup_event.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.connectors.base import ConnectorResult, HealthStatus, UCLConnector


class ConnectorRegistry:
    """
    Holds all registered UCLConnector instances and provides
    bulk refresh / health-check operations.
    """

    def __init__(self) -> None:
        self._connectors: Dict[str, UCLConnector] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, connector: UCLConnector) -> None:
        """
        Add a connector to the registry (idempotent — last registration wins
        if the same name is registered twice, which is intentional for testing).
        """
        self._connectors[connector.name] = connector
        print(
            f"[CONNECTOR] Registered: {connector.name!r} "
            f"(type={connector.source_type})"
        )

    # ------------------------------------------------------------------
    # Single-connector access
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[UCLConnector]:
        """Return the named connector or None if not registered."""
        return self._connectors.get(name)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_all(self) -> List[Dict]:
        """
        Return a lightweight summary of every registered connector.
        Does NOT call health_check (that would require async).
        """
        return [
            {
                "name": c.name,
                "type": c.source_type,
                "description": getattr(c, "description", ""),
            }
            for c in self._connectors.values()
        ]

    def count(self) -> int:
        return len(self._connectors)

    # ------------------------------------------------------------------
    # Bulk async operations
    # ------------------------------------------------------------------

    async def refresh_all(self) -> List[ConnectorResult]:
        """
        Call refresh() on every registered connector.
        Failures are caught and represented as error-result entries so that
        one broken connector does not abort the others.
        """
        results: List[ConnectorResult] = []
        for connector in self._connectors.values():
            try:
                result = await connector.refresh()
                results.append(result)
                print(
                    f"[CONNECTOR] {connector.name} refresh OK — "
                    f"ingested={result.indicators_ingested}, "
                    f"relationships={result.relationships_created}"
                )
            except Exception as exc:
                error_result = ConnectorResult(
                    source=f"{connector.name}_error",
                    indicators_ingested=0,
                    relationships_created=0,
                    enrichment_summary=[{"error": str(exc)}],
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                results.append(error_result)
                print(f"[CONNECTOR] {connector.name} refresh FAILED: {exc}")
        return results

    async def health_check_all(self) -> List[HealthStatus]:
        """
        Call health_check() on every registered connector.
        Failures are caught and represented as unhealthy status entries.
        """
        statuses: List[HealthStatus] = []
        for connector in self._connectors.values():
            try:
                status = await connector.health_check()
            except Exception as exc:
                status = HealthStatus(
                    healthy=False,
                    source=connector.name,
                    message=f"Health check raised exception: {exc}",
                    last_checked=datetime.now(timezone.utc).isoformat(),
                )
                print(f"[CONNECTOR] {connector.name} health_check FAILED: {exc}")
            statuses.append(status)
        return statuses


# ---------------------------------------------------------------------------
# Module-level singleton — import this everywhere
# ---------------------------------------------------------------------------
registry = ConnectorRegistry()
