from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
BACKEND = Path(__file__).resolve().parents[1]
SDK = ROOT.parent / "copilot-sdk"
for path in (str(BACKEND), str(SDK)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.services.soc_situation_pattern import SocAlertTraversalPattern
from copilot_sdk.situation import SituationAnalyzer, TypedIntent


class FakeSocClient:
    def __init__(self, context: dict[str, Any] | None) -> None:
        self.context = context
        self.read_calls: list[str] = []
        self.mutation_calls: list[str] = []

    def get_security_context(self, alert_id: str) -> dict[str, Any] | None:
        self.read_calls.append(alert_id)
        return self.context

    def run_query(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        self.mutation_calls.append("run_query")
        return []


class MissingContextClient:
    pass


class AsyncFakeSocClient(FakeSocClient):
    async def get_security_context(self, alert_id: str) -> dict[str, Any] | None:
        self.read_calls.append(alert_id)
        return self.context


def _intent(domain: str = "soc", alert_id: str = "ALERT-1") -> TypedIntent:
    return TypedIntent(
        domain=domain,
        intent_type="alert_context",
        verb="explain",
        subject="alert",
        scope={"alert_id": alert_id},
        source_event_id=alert_id,
        decision_id="DEC-1",
        trace_id="TRACE-1",
    )


def _context() -> dict[str, Any]:
    return {
        "alert_id": "ALERT-1",
        "alert_type": "anomalous_login",
        "user_id": "USER-1",
        "user_name": "Analyst User",
        "user_title": "VP Finance",
        "user_risk_score": 0.7,
        "asset_id": "ASSET-1",
        "asset_hostname": "workstation-1",
        "asset_criticality": "high",
        "user_traveling": True,
        "travel_destination": "Singapore",
        "vpn_matches_location": True,
        "vpn_provider": "corp-vpn",
        "playbook_id": "PB-1",
        "known_campaign_signature": True,
        "pattern_id": "PAT-1",
        "pattern_count": 4,
        "fp_rate": 0.05,
        "campaign_id": "CAMP-1",
        "nodes_consulted": 47,
    }


def test_supports_accepts_soc_alert_intent() -> None:
    pattern = SocAlertTraversalPattern()

    assert pattern.supports(_intent()) is True


def test_supports_rejects_non_soc_domain() -> None:
    pattern = SocAlertTraversalPattern()

    assert pattern.supports(_intent(domain="dataops")) is False


def test_maps_security_context_to_generic_nodes() -> None:
    pattern = SocAlertTraversalPattern(FakeSocClient(_context()))
    analyzer = SituationAnalyzer([pattern])

    context = analyzer.analyze_intent(_intent())
    by_type = {node.type: node for node in context.nodes}

    assert by_type["Alert"].id == "ALERT-1"
    assert by_type["User"].properties["user_id"] == "USER-1"
    assert by_type["Asset"].properties["asset_id"] == "ASSET-1"
    assert by_type["Playbook"].id == "PB-1"
    assert by_type["AttackPattern"].id == "PAT-1"
    assert by_type["Campaign"].id == "CAMP-1"
    assert context.metadata["nodes_consulted"] == 47


def test_edges_connect_alert_to_context_nodes() -> None:
    pattern = SocAlertTraversalPattern(FakeSocClient(_context()))

    context = pattern.traverse(_intent())
    edge_types = {edge.type for edge in context.edges}
    edge_targets = {edge.target_id for edge in context.edges}

    assert {"INVOLVES", "DETECTED_ON", "HAS_TRAVEL", "HANDLED_BY", "MATCHES", "MEMBER_OF"} <= edge_types
    assert {"USER-1", "ASSET-1", "travel:Singapore", "PB-1", "PAT-1", "CAMP-1"} <= edge_targets


def test_missing_context_returns_warning_context() -> None:
    pattern = SocAlertTraversalPattern(FakeSocClient(None))

    context = pattern.traverse(_intent())

    assert context.nodes[0].id == "ALERT-1"
    assert context.edges == []
    assert context.warnings == ["no SOC security context found"]


def test_missing_client_method_returns_warning_context() -> None:
    pattern = SocAlertTraversalPattern(MissingContextClient())

    context = pattern.traverse(_intent())

    assert context.nodes[0].id == "ALERT-1"
    assert context.warnings == ["graph client does not provide get_security_context"]


def test_bounded_depth_zero_only_returns_alert_node() -> None:
    pattern = SocAlertTraversalPattern(FakeSocClient(_context()))

    context = pattern.traverse(_intent(), max_depth=0)

    assert [node.type for node in context.nodes] == ["Alert"]
    assert context.edges == []
    assert context.truncated is True


def test_no_mutation_calls() -> None:
    client = FakeSocClient(_context())
    pattern = SocAlertTraversalPattern(client)

    context = pattern.traverse(_intent())

    assert context.nodes
    assert client.read_calls == ["ALERT-1"]
    assert client.mutation_calls == []


@pytest.mark.asyncio
async def test_async_fake_client_supported_without_live_backend() -> None:
    client = AsyncFakeSocClient(_context())
    pattern = SocAlertTraversalPattern(client)

    context = await pattern.traverse_async(_intent())

    assert {node.type for node in context.nodes} >= {"Alert", "User", "Asset"}
    assert client.read_calls == ["ALERT-1"]
