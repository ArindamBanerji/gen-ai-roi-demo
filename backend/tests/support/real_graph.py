"""Seed production stores and legacy entity schemas in a disposable AGE graph.

No query evaluation or programmed result rows: all clients execute real Cypher.
"""
from __future__ import annotations

import re
import time
from typing import Any
from uuid import uuid4

from ci_platform.graph.age_client import AGEClient
from ci_platform.graph.age_sdk_adapter import AGEGraphStoreAdapter


class SOCGraphFixture:
    def __init__(self, dsn: str, graph_name: str) -> None:
        self.dsn = dsn
        self.graph_name = graph_name
        self.store = AGEGraphStoreAdapter(dsn=dsn, graph_name=graph_name, domain="soc")
        self.client = AGEClient(dsn=dsn, graph_name=graph_name)
        self.resources: list[Any] = [self.store, self.client]

    def __repr__(self) -> str:
        return f"SOCGraphFixture(graph={self.graph_name!r})"

    def reopen_store(self) -> Any:
        store = AGEGraphStoreAdapter(dsn=self.dsn, graph_name=self.graph_name, domain="soc")
        self.resources.append(store)
        return store

    def reopen_client(self) -> Any:
        client = AGEClient(dsn=self.dsn, graph_name=self.graph_name)
        self.resources.append(client)
        return client

    def query(self, cypher: str) -> list[dict[str, Any]]:
        return list(self.store._store._run_query(cypher))

    @staticmethod
    def _identifier(value: str) -> str:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            raise ValueError(f"invalid fixture identifier: {value}")
        return value

    def node(self, label: str, **properties: Any) -> None:
        """Seed legacy entity/checkpoint data with the production AGE serializer."""
        fields = ", ".join(
            f"{self._identifier(key)}: {AGEClient.serialize_for_age(value)}"
            for key, value in properties.items()
        )
        self.query(f"CREATE (n:{self._identifier(label)} {{{fields}}}) RETURN n")

    def set_properties(self, label: str, key: str, value: Any, *, _domain: str | None = None, **properties: Any) -> None:
        fields = ", ".join(
            f"n.{self._identifier(name)} = {AGEClient.serialize_for_age(item)}"
            for name, item in properties.items()
        )
        domain_filter = "" if _domain is None else f" WHERE n.domain = {AGEClient.serialize_for_age(_domain)}"
        self.query(
            f"MATCH (n:{self._identifier(label)} {{{self._identifier(key)}: "
            f"{AGEClient.serialize_for_age(value)}}}){domain_filter} SET {fields} RETURN n"
        )

    def decision(
        self, *, decision_id: str | None = None, domain: str = "soc",
        category: str = "credential_access", correct: bool | None = None,
        action: str = "investigate", created_at: float | None = None,
        factors: dict[str, float] | None = None, **properties: Any,
    ) -> str:
        identifier = decision_id or "SOC-TEST-" + uuid4().hex[:12]
        created_at = time.time() if created_at is None else created_at
        self.store.write_decision(
            domain, category, action, float(properties.pop("confidence", 0.8)),
            factors or {"threat_intel_enrichment": 0.5},
            metadata={"decision_id": identifier, "created_at": created_at},
        )
        if correct is not None:
            self.store.write_outcome(identifier, action, correct, domain=domain)
        # Historical SOC readers consume these additional, persisted properties.
        extra = {"action": action, "timestamp_epoch": int(created_at * 1000)}
        if correct is not None:
            extra.update(outcome="correct" if correct else "incorrect", verified_at_epoch=int(created_at * 1000))
        self.set_properties("Decision", "decision_id", identifier, _domain=domain, **{**extra, **properties})
        return identifier

    def alert(self, *, alert_id: str | None = None, domain: str = "soc", **properties: Any) -> str:
        identifier = alert_id or "ALERT-TEST-" + uuid4().hex[:12]
        self.node("Alert", id=identifier, alert_id=identifier, domain=domain,
                  **{"timestamp_epoch": int(time.time() * 1000), "status": "new", **properties})
        return identifier

    def close(self) -> None:
        for resource in reversed(self.resources):
            if isinstance(resource, AGEGraphStoreAdapter):
                resource.close()
            else:
                resource._sync_close()
