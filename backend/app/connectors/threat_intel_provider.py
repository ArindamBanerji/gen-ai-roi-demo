"""Provenance-tagged threat intelligence provider for SOC scoring."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar

from app.connectors.mitre_client import MITREClient
from app.connectors.nvd_client import NVDClient


T = TypeVar("T")


@dataclass(frozen=True)
class Provenanced(Generic[T]):
    """Value wrapper carrying data source and substantiation tier."""

    value: T
    source: str
    provenance_tier: str
    fetched_at: float | None = None


class ThreatIntelProvider:
    """K4 threat intelligence with provenance-tagged cascade.

    Sources:
      MITRE ATT&CK: techniques, tactics, groups from public STIX bundles
      NVD/CVE: recent vulnerabilities from NIST NVD API v2.0

    Cascade: live -> cached -> fixture("sample").
    """

    provenance_tier = "scraped_external"

    def __init__(
        self,
        *,
        mitre_client: MITREClient | None = None,
        nvd_client: NVDClient | None = None,
        cache_dir: Path | None = None,
        cache_ttl_hours: int = 24,
    ):
        self._cache_dir = Path(cache_dir) if cache_dir else self._default_cache_dir()
        self._cache_ttl_seconds = cache_ttl_hours * 60 * 60
        self._mitre = mitre_client or MITREClient(cache_dir=self._cache_dir)
        self._nvd = nvd_client or NVDClient(cache_dir=self._cache_dir)

    def get_techniques_for_alert(self, alert: dict) -> Provenanced[list[dict]]:
        """MITRE techniques relevant to this alert's pattern."""

        tactic = self._alert_tactic(alert)
        cache_key = f"techniques_{self._slug(tactic or 'generic')}"

        def live() -> list[dict]:
            if tactic:
                techniques = self._mitre.techniques_for_tactic(tactic)
            else:
                techniques = self._filter_techniques(self._mitre.techniques(), alert)
            return techniques or self._mitre.techniques()[:5]

        return self._cascade(
            cache_key=cache_key,
            live=live,
            fixture=lambda: self._fixture_techniques(tactic),
        )

    def get_recent_cves(
        self, *, days: int = 30, keyword: str | None = None
    ) -> Provenanced[list[dict]]:
        """Recent CVEs from NVD."""

        cache_key = f"cves_{days}_{self._slug(keyword or 'all')}"
        return self._cascade(
            cache_key=cache_key,
            live=lambda: self._nvd.recent_cves(days=days, keyword=keyword),
            fixture=self._fixture_cves,
        )

    def get_campaign_context(self, campaign_name: str) -> Provenanced[dict]:
        """Campaign intelligence from MITRE groups."""

        cache_key = f"campaign_{self._slug(campaign_name)}"
        return self._cascade(
            cache_key=cache_key,
            live=lambda: self._campaign_from_mitre(campaign_name),
            fixture=lambda: self._fixture_campaign(campaign_name),
        )

    def _cascade(
        self,
        *,
        cache_key: str,
        live: Callable[[], T],
        fixture: Callable[[], T],
    ) -> Provenanced[T]:
        try:
            value = live()
            self._write_cache(cache_key, value)
            return Provenanced(
                value=value,
                source="live",
                provenance_tier=self.provenance_tier,
                fetched_at=time.time(),
            )
        except Exception:
            cached = self._read_cache(cache_key)
            if cached is not None:
                return Provenanced(
                    value=cached,
                    source="cached",
                    provenance_tier=self.provenance_tier,
                    fetched_at=time.time(),
                )
            return Provenanced(
                value=fixture(),
                source="sample",
                provenance_tier="sample",
                fetched_at=time.time(),
            )

    def _write_cache(self, key: str, value: Any) -> None:
        path = self._cache_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"fetched_at": time.time(), "value": value}, indent=2),
            encoding="utf-8",
        )

    def _read_cache(self, key: str) -> Any | None:
        path = self._cache_path(key)
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        fetched_at = float(payload.get("fetched_at", 0))
        if time.time() - fetched_at > self._cache_ttl_seconds:
            return None
        return payload.get("value")

    def _cache_path(self, key: str) -> Path:
        return self._cache_dir / f"{key}.json"

    @staticmethod
    def _default_cache_dir() -> Path:
        return Path(__file__).resolve().parents[2] / "data" / "threat_intel_cache"

    @classmethod
    def _filter_techniques(cls, techniques: list[dict], alert: dict) -> list[dict]:
        terms = {
            cls._normalize(alert.get(key))
            for key in (
                "attack_pattern",
                "attack_pattern_id",
                "mitre_id",
                "tactic",
                "category",
                "alert_type",
            )
            if alert.get(key)
        }
        if not terms:
            return []
        matches = []
        for technique in techniques:
            fields = {
                cls._normalize(technique.get("id")),
                cls._normalize(technique.get("external_id")),
                cls._normalize(technique.get("name")),
            }
            fields.update(cls._normalize(t) for t in technique.get("tactics", []))
            if terms & fields:
                matches.append(technique)
        return matches

    @staticmethod
    def _alert_tactic(alert: dict) -> str | None:
        for key in ("tactic", "attack_tactic", "category"):
            value = alert.get(key)
            if value:
                return str(value)
        return None

    @staticmethod
    def _campaign_from_groups(groups: list[dict], campaign_name: str) -> dict:
        wanted = ThreatIntelProvider._normalize(campaign_name)
        for group in groups:
            candidates = [group.get("name"), group.get("external_id")]
            candidates.extend(group.get("aliases", []))
            if wanted in {ThreatIntelProvider._normalize(value) for value in candidates}:
                return group
        raise LookupError(f"No MITRE campaign or group match for {campaign_name!r}")

    def _campaign_from_mitre(self, campaign_name: str) -> dict:
        return self._campaign_from_groups(self._mitre.groups(), campaign_name)

    @staticmethod
    def _fixture_techniques(tactic: str | None) -> list[dict]:
        return [
            {
                "id": "T1110",
                "external_id": "T1110",
                "name": "Brute Force",
                "tactics": [tactic or "credential-access"],
                "description": "Sample ATT&CK technique for offline SOC demo mode.",
                "provenance": "sample",
                "provenance_tier": "sample",
            }
        ]

    @staticmethod
    def _fixture_cves() -> list[dict]:
        return [
            {
                "id": "CVE-2025-0001",
                "published": "2025-01-01T00:00:00.000",
                "description": "Sample CVE for offline SOC demo mode.",
                "cvss": {"version": "3.1", "base_score": 8.1, "base_severity": "HIGH"},
                "provenance": "sample",
                "provenance_tier": "sample",
            }
        ]

    @staticmethod
    def _fixture_campaign(campaign_name: str) -> dict:
        return {
            "id": "G0000",
            "name": campaign_name,
            "aliases": [campaign_name],
            "description": "Sample campaign context for offline SOC demo mode.",
            "provenance": "sample",
            "provenance_tier": "sample",
        }

    @staticmethod
    def _slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_") or "all"

    @staticmethod
    def _normalize(value: Any) -> str:
        return str(value or "").strip().lower().replace("_", "-").replace(" ", "-")


class MockThreatIntelProvider:
    """Fixture-backed provider for tests and offline demos."""

    provenance_tier = "sample"

    def get_techniques_for_alert(self, alert: dict) -> Provenanced[list[dict]]:
        tactic = ThreatIntelProvider._alert_tactic(alert)
        return Provenanced(
            value=ThreatIntelProvider._fixture_techniques(tactic),
            source="sample",
            provenance_tier="sample",
            fetched_at=time.time(),
        )

    def get_recent_cves(
        self, *, days: int = 30, keyword: str | None = None
    ) -> Provenanced[list[dict]]:
        return Provenanced(
            value=ThreatIntelProvider._fixture_cves(),
            source="sample",
            provenance_tier="sample",
            fetched_at=time.time(),
        )

    def get_campaign_context(self, campaign_name: str) -> Provenanced[dict]:
        return Provenanced(
            value=ThreatIntelProvider._fixture_campaign(campaign_name),
            source="sample",
            provenance_tier="sample",
            fetched_at=time.time(),
        )
