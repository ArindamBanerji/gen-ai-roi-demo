"""
SOC Factor Provenance Classification (from P-FIXTURE-AUDIT-SOC):

ALL 6 factors are K3 when running on seed/demo data.

The computation MECHANISM is real (factors compute from graph
context). When real alerts arrive, factors become K4 automatically.
This is the same SUBTLE_K3 classification as Purchasing
conservation -- mechanism real, inputs seeded.

threat_intel_enrichment: HIGH risk -- reads seeded
ThreatIndicator/Campaign nodes, not Pulsedive live data.

pattern_history: SUBTLE_K3 -- learned from prior decisions.

privileged_identity_context, asset_criticality,
time_anomaly, device_trust: Medium -- seed alert properties.

F-26 exposure: demo/seed alert scoring produces K3-quality
factors. Label seed data, document the transition path.
When real feeds arrive: provenance becomes "scraped_external".
"""

from __future__ import annotations

import json
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
SEED_V5_PATH = BACKEND_ROOT / "support" / "setup" / "zero_day_decisions_v5.json"
SEED_ORIGINAL_PATH = BACKEND_ROOT / "support" / "setup" / "zero_day_decisions.json"
DATA_DIR = BACKEND_ROOT / "app" / "data"


def test_seed_v5_has_provenance() -> None:
    payload = _load_json(SEED_V5_PATH)

    assert payload["metadata"]["provenance"] == "sample"


def test_seed_v5_all_alerts_have_provenance() -> None:
    payload = _load_json(SEED_V5_PATH)

    assert payload["alerts"]
    assert payload["demo_alerts"]
    assert all(alert.get("provenance") == "sample" for alert in payload["alerts"])
    assert all(alert.get("provenance") == "sample" for alert in payload["demo_alerts"])


def test_seed_v5_all_decisions_have_provenance() -> None:
    payload = _load_json(SEED_V5_PATH)

    assert payload["decisions"]
    assert all(decision.get("provenance") == "sample" for decision in payload["decisions"])


def test_seed_original_has_provenance() -> None:
    payload = _load_json(SEED_ORIGINAL_PATH)

    assert payload["metadata"]["provenance"] == "sample"
    assert all(record.get("provenance") == "sample" for record in payload["alerts"])
    assert all(record.get("provenance") == "sample" for record in payload["decisions"])


def test_eval_scenarios_have_provenance() -> None:
    scenarios = _load_json(DATA_DIR / "soc_eval_scenarios.json")

    assert scenarios
    assert all(scenario.get("provenance") == "sample" for scenario in scenarios)


def test_data_files_have_provenance() -> None:
    for path in DATA_DIR.glob("*.json"):
        payload = _load_json(path)
        if isinstance(payload, list):
            assert payload, path
            assert all(isinstance(record, dict) and record.get("provenance") == "sample" for record in payload), path
        else:
            assert isinstance(payload, dict), path
            if payload.get("provenance") == "sample":
                continue
            assert payload, path
            assert all(
                isinstance(record, dict) and record.get("provenance") == "sample"
                for record in payload.values()
            ), path


def test_existing_origin_fields_preserved() -> None:
    seed_v5 = _load_json(SEED_V5_PATH)
    original = _load_json(SEED_ORIGINAL_PATH)

    assert {alert["origin"] for alert in seed_v5["alerts"]} == {"zero_day_synthetic"}
    assert {alert["origin"] for alert in seed_v5["demo_alerts"]} == {"zero_day_demo"}
    assert {decision["origin"] for decision in seed_v5["decisions"]} == {"zero_day_synthetic"}
    assert {alert["origin"] for alert in original["alerts"]} == {"zero_day_synthetic"}
    assert {decision["origin"] for decision in original["decisions"]} == {"zero_day_synthetic"}
    assert all(alert["provenance"] == "sample" for alert in seed_v5["alerts"])


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
