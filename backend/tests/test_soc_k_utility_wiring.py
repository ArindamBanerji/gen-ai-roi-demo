"""SOC routing weights use the configured graph and explicit SOC domain."""
from __future__ import annotations

import numpy as np
import pytest

from app.main import _create_vld_k_store
from copilot_sdk.config import GraphConfig
from copilot_sdk.graph import InMemoryGraphStore
from copilot_sdk.graph import factory
from copilot_sdk.graph.protocol import GraphStore
from copilot_sdk.scoring.investigation import InvestigationStep, InvestigationTrace

pytestmark = pytest.mark.no_data_guard


def test_k_utility_reads_and_updates_soc_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    store = InMemoryGraphStore(domain="soc")
    configs: list[GraphConfig] = []

    def configured_store(*, config: GraphConfig) -> GraphStore:
        configs.append(config)
        return store

    monkeypatch.setattr(factory, "create_graph_store", configured_store)
    store.save_k_utility("soc", "credential_access", 2, 0.9)
    store.save_k_utility("other", "credential_access", 2, 2.0)
    weights = _create_vld_k_store(6)
    assert configs == [GraphConfig.load("soc")]
    assert weights.domain == "soc"
    assert weights.graph_store is store
    np.testing.assert_allclose(weights.get_weights("credential_access"), [0.5, 0.5, 0.9, 0.5, 0.5, 0.5])
    trace = InvestigationTrace(
        decision_id="soc-k-test", category="credential_access", budget=1,
        steps=[InvestigationStep(
            step=0, dimension=2, factor_name="threat_intel_enrichment",
            evidence_value=0.9, evidence_confidence=1.0, evidence_source="test",
            v_before=[0.5] * 6, v_after=[0.5, 0.5, 0.9, 0.5, 0.5, 0.5],
            action_before=0, action_after=1, margin_before=0.1, margin_after=0.4,
            flipped=True,
        )],
        surface_action=0, surface_margin=0.1, final_action=1, final_margin=0.4,
    )
    weights.update_weights("credential_access", trace, correct=True)
    rebuilt = _create_vld_k_store(6)
    assert rebuilt.get_weights("credential_access")[2] == pytest.approx(0.94)
    assert store.get_k_utilities("other", "credential_access")[0]["utility"] == 2.0


def test_k_utility_does_not_fall_back_when_graph_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(*, config: GraphConfig) -> GraphStore:
        raise RuntimeError("configured graph unavailable")

    monkeypatch.setattr(factory, "create_graph_store", unavailable)
    with pytest.raises(RuntimeError, match="configured graph unavailable"):
        _create_vld_k_store(6)
