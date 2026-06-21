from __future__ import annotations

import time

from app.connectors.mitre_client import MITREClient
from app.connectors.nvd_client import NVDClient
from app.connectors.threat_intel_provider import (
    MockThreatIntelProvider,
    ThreatIntelProvider,
)


TECHNIQUES = [
    {
        "id": "T1110",
        "external_id": "T1110",
        "name": "Brute Force",
        "tactics": ["credential-access"],
        "provenance_tier": "scraped_external",
    }
]

CVES = [
    {
        "id": "CVE-2025-1234",
        "description": "Test CVE",
        "provenance_tier": "scraped_external",
    }
]

GROUPS = [
    {
        "id": "G1000",
        "external_id": "G1000",
        "name": "Credential Harvesting Wave",
        "aliases": ["Credential Harvesting Wave"],
        "provenance_tier": "scraped_external",
    }
]


class FakeMITREClient:
    def __init__(self, *, fail: bool = False):
        self.fail = fail

    def techniques(self) -> list[dict]:
        if self.fail:
            raise RuntimeError("MITRE unavailable")
        return TECHNIQUES

    def techniques_for_tactic(self, tactic_name: str) -> list[dict]:
        if self.fail:
            raise RuntimeError("MITRE unavailable")
        return [
            technique
            for technique in TECHNIQUES
            if tactic_name in technique.get("tactics", [])
        ]

    def groups(self) -> list[dict]:
        if self.fail:
            raise RuntimeError("MITRE unavailable")
        return GROUPS


class FakeNVDClient:
    def __init__(self, *, fail: bool = False):
        self.fail = fail

    def recent_cves(self, *, days: int = 30, keyword: str | None = None) -> list[dict]:
        if self.fail:
            raise RuntimeError("NVD unavailable")
        return CVES


def test_provider_provenance_tier():
    assert ThreatIntelProvider.provenance_tier == "scraped_external"


def test_mock_provenance_tier():
    assert MockThreatIntelProvider.provenance_tier == "sample"


def test_cascade_live_to_cached(tmp_path):
    provider = ThreatIntelProvider(
        mitre_client=FakeMITREClient(),
        nvd_client=FakeNVDClient(),
        cache_dir=tmp_path,
    )

    result = provider.get_techniques_for_alert({"tactic": "credential-access"})

    assert result.source == "live"
    assert result.provenance_tier == "scraped_external"
    assert result.value == TECHNIQUES
    assert (tmp_path / "techniques_credential_access.json").is_file()


def test_cascade_cached_to_fixture(tmp_path):
    live_provider = ThreatIntelProvider(
        mitre_client=FakeMITREClient(),
        nvd_client=FakeNVDClient(),
        cache_dir=tmp_path,
    )
    live_provider.get_techniques_for_alert({"tactic": "credential-access"})
    failing_provider = ThreatIntelProvider(
        mitre_client=FakeMITREClient(fail=True),
        nvd_client=FakeNVDClient(fail=True),
        cache_dir=tmp_path,
    )

    result = failing_provider.get_techniques_for_alert({"tactic": "credential-access"})

    assert result.source == "cached"
    assert result.provenance_tier == "scraped_external"
    assert result.value == TECHNIQUES


def test_cascade_fixture_fallback(tmp_path):
    provider = ThreatIntelProvider(
        mitre_client=FakeMITREClient(fail=True),
        nvd_client=FakeNVDClient(fail=True),
        cache_dir=tmp_path,
    )

    result = provider.get_techniques_for_alert({"tactic": "credential-access"})

    assert result.source == "sample"
    assert result.provenance_tier == "sample"
    assert result.value[0]["provenance"] == "sample"


def test_techniques_for_alert(tmp_path):
    provider = ThreatIntelProvider(
        mitre_client=FakeMITREClient(),
        nvd_client=FakeNVDClient(),
        cache_dir=tmp_path,
    )

    result = provider.get_techniques_for_alert({"tactic": "credential-access"})

    assert result.value[0]["external_id"] == "T1110"


def test_recent_cves(tmp_path):
    provider = ThreatIntelProvider(
        mitre_client=FakeMITREClient(),
        nvd_client=FakeNVDClient(),
        cache_dir=tmp_path,
    )

    result = provider.get_recent_cves(days=7, keyword="openssl")

    assert result.source == "live"
    assert result.value[0]["id"] == "CVE-2025-1234"


def test_campaign_context(tmp_path):
    provider = ThreatIntelProvider(
        mitre_client=FakeMITREClient(),
        nvd_client=FakeNVDClient(),
        cache_dir=tmp_path,
    )

    result = provider.get_campaign_context("Credential Harvesting Wave")

    assert result.source == "live"
    assert result.value["id"] == "G1000"


def test_mitre_parse_stix(monkeypatch, tmp_path):
    bundle = {
        "type": "bundle",
        "objects": [
            {
                "type": "attack-pattern",
                "id": "attack-pattern--1",
                "name": "Brute Force",
                "description": "Credential guessing",
                "kill_chain_phases": [{"phase_name": "credential-access"}],
                "external_references": [
                    {"external_id": "T1110", "url": "https://attack.mitre.org/T1110"}
                ],
            },
            {
                "type": "x-mitre-tactic",
                "id": "x-mitre-tactic--1",
                "name": "Credential Access",
                "x_mitre_shortname": "credential-access",
                "external_references": [{"external_id": "TA0006"}],
            },
            {
                "type": "intrusion-set",
                "id": "intrusion-set--1",
                "name": "APT Test",
                "aliases": ["APT Test"],
                "external_references": [{"external_id": "G0001"}],
            },
        ],
    }
    client = MITREClient(cache_dir=tmp_path)
    monkeypatch.setattr(client, "_fetch_json", lambda: bundle)

    assert client.techniques()[0]["external_id"] == "T1110"
    assert client.tactics()[0]["shortname"] == "credential-access"
    assert client.groups()[0]["external_id"] == "G0001"
    assert client.techniques_for_tactic("credential-access")[0]["name"] == "Brute Force"


def test_nvd_parse_response():
    payload = {
        "vulnerabilities": [
            {
                "cve": {
                    "id": "CVE-2025-1234",
                    "published": "2025-01-01T00:00:00.000",
                    "lastModified": "2025-01-02T00:00:00.000",
                    "descriptions": [{"lang": "en", "value": "Example issue"}],
                    "metrics": {
                        "cvssMetricV31": [
                            {
                                "baseSeverity": "HIGH",
                                "cvssData": {
                                    "version": "3.1",
                                    "baseScore": 8.8,
                                    "vectorString": "CVSS:3.1/AV:N/AC:L",
                                },
                            }
                        ]
                    },
                    "weaknesses": [{"description": [{"value": "CWE-79"}]}],
                    "references": {"referenceData": [{"url": "https://example.test"}]},
                }
            }
        ]
    }

    parsed = NVDClient.parse_response(payload)

    assert parsed[0]["id"] == "CVE-2025-1234"
    assert parsed[0]["description"] == "Example issue"
    assert parsed[0]["cvss"]["base_score"] == 8.8
    assert parsed[0]["weaknesses"] == ["CWE-79"]


def test_nvd_rate_limit_header():
    assert NVDClient.rate_limit_delay({"Retry-After": "6"}) == 6.0

    delay = NVDClient.rate_limit_delay(
        {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(time.time() + 10),
        }
    )
    assert 0 < delay <= 10


def test_mock_not_labeled_live():
    result = MockThreatIntelProvider().get_recent_cves()

    assert MockThreatIntelProvider.provenance_tier != "scraped_external"
    assert result.provenance_tier == "sample"
    assert result.source == "sample"


def test_provider_source_declares_tier(tmp_path):
    provider = ThreatIntelProvider(
        mitre_client=FakeMITREClient(),
        nvd_client=FakeNVDClient(),
        cache_dir=tmp_path,
    )

    results = [
        provider.get_techniques_for_alert({"tactic": "credential-access"}),
        provider.get_recent_cves(),
        provider.get_campaign_context("Credential Harvesting Wave"),
    ]

    assert all(result.provenance_tier == "scraped_external" for result in results)
    assert all(result.source == "live" for result in results)
