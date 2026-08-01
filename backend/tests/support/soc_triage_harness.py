"""Stateful test infrastructure for post-unification SOC triage tests.

The InMemoryGraphStore is the only authority for Decision records and
outcomes.  ``SOCNonDecisionClient`` supplies the legacy client surface only
for non-Decision reads and side effects that the router still needs.
"""

from __future__ import annotations

import re
import uuid
from copy import deepcopy
from typing import Any, cast

from app.domains.soc.scorer_adapter import SOCCompoundingScorerAdapter
from copilot_sdk.graph.memory_store import InMemoryGraphStore
from copilot_sdk.scoring.scorer import CompoundingScorer


_UNSET = object()


class SOCNonDecisionClient:
    """Stateful client for SOC graph operations other than Decisions.

    Decision creation, lookup, and outcome writes intentionally are not
    implemented here.  The stored projection exists only for legacy route
    context reads and is populated from the same harness input as the real
    Decision store.
    """

    def __init__(self) -> None:
        self._alerts: dict[str, dict[str, Any]] = {}
        self._campaigns: dict[str, dict[str, Any]] = {}
        self._entities: dict[str, dict[str, Any]] = {}
        self._sequence_count = 0
        self._cross_category_count = 0
        self._evolution_events: list[dict[str, Any]] = []
        self._queries: list[tuple[str, dict[str, Any] | None]] = []
        self._decision_projections: dict[str, dict[str, Any]] = {}
        self._health_rows: list[dict[str, Any]] = [{"red_days": 0}]
        self._decision_summary_rows: list[dict[str, Any]] = []
        self.fail_triggered_evolution = False

    def add_decision_projection(self, decision_id: str, projection: dict[str, Any]) -> None:
        """Register the non-Decision context projection for a Decision."""
        self._decision_projections[decision_id] = deepcopy(projection)

    def set_health_rows(self, rows: list[dict[str, Any]]) -> None:
        self._health_rows = deepcopy(rows)

    def set_decision_summary_rows(self, rows: list[dict[str, Any]]) -> None:
        self._decision_summary_rows = deepcopy(rows)

    async def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        return deepcopy(self._alerts.get(alert_id))

    async def get_security_context(self, alert_id: str) -> dict[str, Any]:
        alert = self._alerts.get(alert_id, {})
        return deepcopy(alert.get("security_context", {}))

    async def get_sequence_count(self, _source_id: str) -> int:
        return self._sequence_count

    async def get_cross_category_count(self, _user_id: str) -> int:
        return self._cross_category_count

    async def run_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Answer supported non-Decision queries from this client's state."""
        self._queries.append((query, deepcopy(params)))

        if self.fail_triggered_evolution and "TRIGGERED_EVOLUTION" in query:
            raise RuntimeError("evolution write failed")

        if "RETURN d.factor_vector AS factor_vector" in query:
            match = re.search(r"decision_id\s*:\s*['\"]([^'\"]+)['\"]", query)
            decision_id = match.group(1) if match else None
            projection = self._decision_projections.get(decision_id or "")
            return [deepcopy(projection)] if projection is not None else []

        if "MATCH (h:HealthLog)" in query:
            return deepcopy(self._health_rows)

        if "MATCH (d:Decision)" in query and "RETURN d.category AS category" in query:
            return deepcopy(self._decision_summary_rows)

        if "TRIGGERED_EVOLUTION" in query or "EvolutionEvent" in query:
            property_names = (
                "timestamp_epoch",
                "decision_id",
                "category",
                "correct",
                "action",
                "verified_correct",
                "action_index",
                "factor_snapshot",
                "decision_number",
            )
            properties = {
                name: True
                for name in property_names
                if name in query
            }
            self._evolution_events.append(
                {
                    "query": query,
                    "params": deepcopy(params),
                    "properties": properties,
                }
            )
        return []


class SOCTriageHarness:
    """Shared harness with a real stateful Decision authority."""

    def __init__(self) -> None:
        self.store = InMemoryGraphStore(domain="soc")
        compound = CompoundingScorer.from_preset(
            "soc",
            graph_store=self.store,
            profile="test",
            enable_rl=False,
        )
        self.scorer = object.__new__(SOCCompoundingScorerAdapter)
        object.__setattr__(self.scorer, "_compound", compound)
        object.__setattr__(self.scorer, "_scorer", compound._scorer)
        self.graph_client = SOCNonDecisionClient()

    def add_decision(
        self,
        *,
        decision_id: str | None = None,
        category: str,
        action: str,
        factors: dict[str, Any],
        confidence: float = 0.85,
        status: str = "pending",
        campaign_id: str | None = None,
        exploration_flags: dict[str, Any] | None = None,
        factor_vector: Any = _UNSET,
        **extra: Any,
    ) -> str:
        """Create one Decision through the GraphStore contract."""
        actual_id = decision_id or f"SOC-TEST-{uuid.uuid4().hex[:12]}"
        metadata: dict[str, Any] = {
            "decision_id": actual_id,
            "recommended_index": int(extra.pop("recommended_index", 0)),
            "category_index": int(extra.pop("category_index", 0)),
        }
        if factor_vector is not _UNSET:
            metadata["factor_vector"] = deepcopy(factor_vector)
        if campaign_id is not None:
            metadata["campaign_id"] = campaign_id
        if "probabilities" in extra:
            metadata["probabilities"] = deepcopy(extra.pop("probabilities"))
        metadata.update(deepcopy(extra))
        self.store.write_decision(
            domain="soc",
            category=category,
            action=action,
            confidence=confidence,
            factors=deepcopy(factors),
            metadata=metadata,
        )
        flags = dict(exploration_flags or {})
        self.graph_client.add_decision_projection(
            actual_id,
            {
                "factor_vector": deepcopy(
                    None if factor_vector is _UNSET else factor_vector
                ),
                "action": action,
                "confidence": confidence,
                "category": category,
                "alert_type": extra.get("alert_type", category),
                "campaign_id": campaign_id,
                "explored": bool(flags.get("explored", extra.get("explored", False))),
                "explored_but_referred": bool(
                    flags.get("explored_but_referred", extra.get("explored_but_referred", False))
                ),
                "exploration_executed": bool(
                    flags.get("exploration_executed", extra.get("exploration_executed", False))
                ),
                "explored_action": flags.get("explored_action", extra.get("explored_action")),
            },
        )
        if status != "pending":
            raise ValueError("SOCTriageHarness.add_decision only creates pending Decisions")
        return actual_id

    def get_decision(self, decision_id: str) -> dict[str, Any] | None:
        """Read a Decision from the authoritative store."""
        return cast(dict[str, Any] | None, self.store.get_decision(decision_id, domain="soc"))

    def get_scorer(self) -> SOCCompoundingScorerAdapter:
        """Return the real scorer adapter for route dependency injection."""
        return self.scorer
