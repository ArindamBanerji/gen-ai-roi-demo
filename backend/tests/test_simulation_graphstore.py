from __future__ import annotations

from app.services.simulation import _write_simulation_decision


class _GraphStore:
    def __init__(self) -> None:
        self.payload = None

    def write_decision(self, **payload):
        self.payload = payload
        return "soc-decision-1"


def test_simulation_decision_uses_domain_scoped_graphstore() -> None:
    store = _GraphStore()

    decision_id = _write_simulation_decision(
        store,
        alert_id="alert-1",
        category="malware_execution",
        action="investigate",
        confidence=0.9,
        factor_names=["threat_intel_enrichment"],
        factor_values=[0.8],
    )

    assert decision_id == "soc-decision-1"
    assert store.payload is not None
    assert store.payload["domain"] == "soc"
    assert store.payload["metadata"]["entity_id"] == "alert-1"
    assert store.payload["factors"]["factor_values"] == [0.8]
