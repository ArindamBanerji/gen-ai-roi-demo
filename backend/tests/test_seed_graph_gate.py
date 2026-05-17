from __future__ import annotations

import copy
import json

import pytest

from app.graph_schema import _validate_json, _validate_seed_data, seed_graph
from app.seed.config import SeedConfig
from app.seed.runner import generate_seed


class FakeGraphClient:
    def __init__(self):
        self.ensure_graph_called = False
        self.queries: list[str] = []

    async def ensure_graph(self):
        self.ensure_graph_called = True

    async def run_query(self, query: str):
        self.queries.append(query)
        return []


def test_seed_graph_refuses_invalid_seed(tmp_path):
    data = generate_seed(SeedConfig(n_training_alerts=24, n_demo_alerts=12, n_decisions=48))
    data["alerts"][0]["alert_type"] = "not_mapped"
    seed_path = tmp_path / "invalid_seed.json"
    seed_path.write_text(json.dumps(data), encoding="utf-8")
    client = FakeGraphClient()

    with pytest.raises(ValueError, match="Seed validation failed") as exc:
        import asyncio

        asyncio.run(seed_graph(str(seed_path), clean=True, client=client))

    assert "unmapped alert_type" in str(exc.value)
    assert client.ensure_graph_called is False
    assert client.queries == []


def test_seed_graph_accepts_valid_generated_seed_gate():
    data = generate_seed(SeedConfig(n_training_alerts=24, n_demo_alerts=12, n_decisions=48))

    _validate_seed_data(data)
    _validate_json(data)


def test_seed_graph_gate_reports_first_ten_errors():
    data = generate_seed(SeedConfig(n_training_alerts=24, n_demo_alerts=12, n_decisions=48))
    broken = copy.deepcopy(data)
    for alert in broken["alerts"][:12]:
        alert["alert_type"] = "not_mapped"

    with pytest.raises(ValueError) as exc:
        _validate_seed_data(broken)

    message = str(exc.value)
    assert message.count("unmapped alert_type") == 10
    assert "... and 2 more errors" in message
