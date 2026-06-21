from __future__ import annotations

import json
from pathlib import Path

from app.connectors.mitre_client import MITREClient
from app.connectors.nvd_client import NVDClient
from app.connectors.threat_intel_provider import (
    MockThreatIntelProvider,
    ThreatIntelProvider,
)


class FailingMITREClient:
    def __init__(self, error: Exception):
        self._error = error

    def techniques(self) -> list[dict]:
        raise self._error

    def techniques_for_tactic(self, tactic_name: str) -> list[dict]:
        raise self._error

    def groups(self) -> list[dict]:
        raise self._error


class FailingNVDClient:
    def __init__(self, error: Exception):
        self._error = error

    def recent_cves(self, *, days: int = 30, keyword: str | None = None) -> list[dict]:
        raise self._error


def test_provider_live_provenance():
    assert ThreatIntelProvider.provenance_tier == "scraped_external"


def test_mock_provenance():
    assert MockThreatIntelProvider.provenance_tier == "sample"


def test_cascade_network_error(tmp_path):
    provider = ThreatIntelProvider(
        mitre_client=FailingMITREClient(ConnectionError("network down")),
        nvd_client=FailingNVDClient(ConnectionError("network down")),
        cache_dir=tmp_path,
    )

    result = provider.get_techniques_for_alert({"tactic": "credential-access"})

    assert result.source in {"cached", "sample"}
    assert result.provenance_tier in {"scraped_external", "sample"}


def test_cascade_timeout(tmp_path):
    provider = ThreatIntelProvider(
        mitre_client=FailingMITREClient(TimeoutError("timeout")),
        nvd_client=FailingNVDClient(TimeoutError("timeout")),
        cache_dir=tmp_path,
    )

    result = provider.get_recent_cves(keyword="openssl")

    assert result.source in {"cached", "sample"}
    assert result.provenance_tier in {"scraped_external", "sample"}


def test_cascade_malformed_stix(tmp_path):
    provider = ThreatIntelProvider(
        mitre_client=FailingMITREClient(AttributeError("bad STIX")),
        nvd_client=FailingNVDClient(ConnectionError("unused")),
        cache_dir=tmp_path,
    )

    result = provider.get_techniques_for_alert({"tactic": "credential-access"})

    assert result.source == "sample"
    assert result.value[0]["provenance"] == "sample"


def test_mitre_technique_parse(monkeypatch, tmp_path):
    bundle = {
        "objects": [
            {
                "type": "attack-pattern",
                "id": "attack-pattern--1",
                "name": "Brute Force",
                "description": "Credential guessing",
                "kill_chain_phases": [{"phase_name": "credential-access"}],
                "external_references": [{"external_id": "T1110"}],
            }
        ]
    }
    client = MITREClient(cache_dir=tmp_path)
    monkeypatch.setattr(client, "_fetch_json", lambda: bundle)

    techniques = client.techniques()

    assert techniques[0]["external_id"] == "T1110"
    assert techniques[0]["tactics"] == ["credential-access"]


def test_nvd_cve_parse():
    parsed = NVDClient.parse_response(
        {
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2025-1234",
                        "published": "2025-01-01T00:00:00.000",
                        "descriptions": [{"lang": "en", "value": "Example CVE"}],
                        "metrics": {
                            "cvssMetricV31": [
                                {
                                    "baseSeverity": "HIGH",
                                    "cvssData": {"version": "3.1", "baseScore": 8.8},
                                }
                            ]
                        },
                    }
                }
            ]
        }
    )

    assert parsed[0]["id"] == "CVE-2025-1234"
    assert parsed[0]["cvss"]["base_score"] == 8.8
    assert parsed[0]["provenance_tier"] == "scraped_external"


def test_nvd_rate_limit_respected():
    assert NVDClient.rate_limit_delay({"Retry-After": "2"}) == 2.0


def test_f25_mock_not_live():
    assert MockThreatIntelProvider.provenance_tier != "scraped_external"


def test_provenance_labels_on_seed():
    path = Path(__file__).resolve().parents[1] / "support" / "setup" / "zero_day_decisions_v5.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    assert all(alert.get("provenance") == "sample" for alert in data["alerts"])
    assert all(decision.get("provenance") == "sample" for decision in data["decisions"])
    assert all("origin" in alert for alert in data["alerts"])
    assert all("origin" in decision for decision in data["decisions"])
