"""SOC adapter for shared AGE state persistence.

The legacy ``graph_client`` remains available for the many SOC query callers.
State owned by services in this package is exposed through the GraphStore
contract and is backed by the same configured AGE graph.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, cast

from ci_platform.graph.age_sdk_adapter import AGEGraphStoreAdapter
from copilot_sdk.graph.production import GraphStoreWrapper


log = logging.getLogger(__name__)


def _is_transient_age_failure(exc: Exception) -> bool:
    """Classify the bounded AGE failures that are safe to retry."""
    message = str(exc).lower()
    return any(
        marker in message
        for marker in (
            "could not be locked",
            "failed to be updated",
            "invalid attribute number",
            "relation \"soc_graph.",
            "server closed the connection unexpectedly",
            "consuming input failed",
            "connection is closed",
        )
    )


class GraphStoreAdapter(GraphStoreWrapper):
    """Compose the legacy AGE client with the typed GraphStore state API."""

    def __init__(self, graph_client: Any, store: Any) -> None:
        if graph_client is None:
            raise ValueError("graph_client is required")
        if store is None:
            raise ValueError("AGE GraphStore is required")
        self._graph_client = graph_client
        self._store = store
        self._state_lock = threading.RLock()

    @property
    def graph_client(self) -> Any:
        return self._graph_client

    def _run_state_operation(self, operation: Any) -> Any:
        """Serialize state I/O and retry bounded transient AGE failures."""
        with self._state_lock:
            for attempt in range(3):
                try:
                    return operation()
                except Exception as exc:
                    if not _is_transient_age_failure(exc) or attempt == 2:
                        raise
                    delay_seconds = 0.1 * (attempt + 1)
                    log.warning(
                        "Transient AGE state operation failure; retrying in %.1fs "
                        "(attempt %d/3): %s",
                        delay_seconds,
                        attempt + 2,
                        exc,
                    )
                    time.sleep(delay_seconds)
        raise RuntimeError("unreachable state operation retry")

    def save_evolution(self, domain: str, key: str, payload: dict[str, Any]) -> None:
        self._run_state_operation(lambda: self._store.save_evolution(domain, key, payload))

    def get_evolution(self, domain: str, key: str) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, self._run_state_operation(lambda: self._store.get_evolution(domain, key)))

    def list_evolutions(self, domain: str) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], self._run_state_operation(lambda: self._store.list_evolutions(domain)))

    def delete_evolution(self, domain: str, key: str) -> None:
        self._run_state_operation(lambda: self._store.delete_evolution(domain, key))

    def save_posterior(self, domain: str, key: str, payload: dict[str, Any]) -> None:
        self._run_state_operation(lambda: self._store.save_posterior(domain, key, payload))

    def get_posterior(self, domain: str, key: str) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, self._run_state_operation(lambda: self._store.get_posterior(domain, key)))

    def save_promotion(self, domain: str, key: str, payload: dict[str, Any]) -> None:
        self._run_state_operation(lambda: self._store.save_promotion(domain, key, payload))

    def get_promotion(self, domain: str, key: str) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, self._run_state_operation(lambda: self._store.get_promotion(domain, key)))

    def list_promotions(self, domain: str) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], self._run_state_operation(lambda: self._store.list_promotions(domain)))

    def get_decision(
        self,
        decision_id: str,
        domain: str,
        *,
        include_outcome: bool = False,
    ) -> dict[str, Any] | None:
        return cast(
            dict[str, Any] | None,
            self._run_state_operation(
                lambda: self._store.get_decision(
                    decision_id,
                    domain,
                    include_outcome=include_outcome,
                )
            ),
        )

    def get_verified_decisions(
        self,
        domain: str,
        *,
        offset: int = 0,
        limit: int | None = None,
        chronological: bool = False,
        verified_after: tuple[float, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return verified rows with SOC's legacy outcome vocabulary normalized."""
        rows = cast(
            list[dict[str, Any]],
            self._run_state_operation(
                lambda: self._store.get_verified_decisions(
                    domain,
                    offset=offset,
                    limit=limit,
                    chronological=chronological,
                    verified_after=verified_after,
                )
            ),
        )
        if domain != "soc":
            return rows

        normalized_rows: list[dict[str, Any]] = []
        for row in rows:
            outcome_value = row.get("outcome")
            if outcome_value is None:
                normalized_rows.append(row)
                continue

            outcome = str(outcome_value).strip().lower()
            if outcome in {"confirmed", "overridden"}:
                normalized_rows.append(row)
                continue
            if outcome not in {"correct", "incorrect"}:
                log.warning(
                    "Excluding SOC verified decision with unknown outcome "
                    "(decision_id=%s, outcome=%r)",
                    row.get("decision_id"),
                    outcome_value,
                )
                continue

            status_value = row.get("status")
            status = str(status_value).strip().lower()
            is_correct = row.get("is_correct")
            legacy_correct = outcome == "correct"
            status_correct = status == "confirmed"
            consistent = (
                isinstance(is_correct, bool)
                and status in {"confirmed", "overridden"}
                and is_correct == legacy_correct
                and is_correct == status_correct
            )
            if not consistent:
                log.warning(
                    "Excluding inconsistent SOC verified decision "
                    "(decision_id=%s, outcome=%r, status=%r, is_correct=%r)",
                    row.get("decision_id"),
                    outcome_value,
                    status_value,
                    is_correct,
                )
                continue

            normalized = dict(row)
            normalized["outcome"] = status_value
            normalized_rows.append(normalized)
        return normalized_rows

    def write_outcome(
        self,
        decision_id: str,
        actual_action: str,
        is_correct: bool,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self._run_state_operation(
            lambda: self._store.write_outcome(
                decision_id,
                actual_action,
                is_correct,
                metadata,
                **kwargs,
            )
        )

    def save_evolution_event(self, **kwargs: Any) -> None:
        self._store.write_evolution_event(**kwargs)

    def __getattr__(self, name: str) -> Any:
        """Delegate existing GraphStore operations to the AGE adapter."""
        return getattr(self._store, name)


def create_soc_graph_store(graph_client: Any, graph_config: Any) -> GraphStoreAdapter:
    """Build the SOC state adapter from the typed shared-graph config."""
    backend = str(getattr(graph_config, "backend", "")).lower()
    if backend != "age":
        raise ValueError(f"SOC state requires AGE backend, got {backend!r}")
    dsn = str(getattr(graph_config, "dsn", "") or "").strip()
    graph_name = str(getattr(graph_config, "graph", "") or "").strip()
    if not dsn or not graph_name:
        raise ValueError("SOC GraphConfig must provide AGE DSN and graph")
    store = AGEGraphStoreAdapter(dsn=dsn, graph_name=graph_name, domain="soc")
    return GraphStoreAdapter(graph_client, store)
