"""MITRE ATT&CK STIX bundle client for SOC threat intelligence."""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path
from typing import Any, cast


class MITREClient:
    """MITRE ATT&CK STIX bundle reader.

    Source: GitHub-hosted STIX bundles (CC-BY-4.0).
    No API key needed. Cache refreshes weekly.
    """

    ENTERPRISE_URL = (
        "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/"
        "enterprise-attack/enterprise-attack.json"
    )

    def __init__(self, *, cache_dir: Path | None = None):
        self._cache_dir = Path(cache_dir) if cache_dir else None
        self._cache_ttl_seconds = 7 * 24 * 60 * 60

    def techniques(self) -> list[dict]:
        """All enterprise ATT&CK techniques."""

        return [self._parse_technique(obj) for obj in self._objects("attack-pattern")]

    def tactics(self) -> list[dict]:
        """All enterprise ATT&CK tactics."""

        return [self._parse_tactic(obj) for obj in self._objects("x-mitre-tactic")]

    def groups(self) -> list[dict]:
        """All enterprise ATT&CK intrusion sets."""

        return [self._parse_group(obj) for obj in self._objects("intrusion-set")]

    def techniques_for_tactic(self, tactic_name: str) -> list[dict]:
        """Techniques whose kill-chain phase matches a tactic name."""

        wanted = self._normalize(tactic_name)
        return [
            technique
            for technique in self.techniques()
            if any(self._normalize(tactic) == wanted for tactic in technique["tactics"])
        ]

    def _objects(self, object_type: str) -> list[dict]:
        bundle = self._load_bundle()
        return [
            obj
            for obj in bundle.get("objects", [])
            if obj.get("type") == object_type and not obj.get("revoked", False)
        ]

    def _load_bundle(self) -> dict:
        cache_path = self._cache_path()
        if cache_path and self._cache_fresh(cache_path):
            return cast(dict, json.loads(cache_path.read_text(encoding="utf-8")))

        data = self._fetch_json()
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data

    def _fetch_json(self) -> dict:
        with urllib.request.urlopen(self.ENTERPRISE_URL, timeout=30) as response:
            return cast(dict, json.loads(response.read().decode("utf-8")))

    def _cache_path(self) -> Path | None:
        if not self._cache_dir:
            return None
        return self._cache_dir / "mitre_enterprise_attack.json"

    def _cache_fresh(self, path: Path) -> bool:
        if not path.is_file():
            return False
        return (time.time() - path.stat().st_mtime) <= self._cache_ttl_seconds

    @classmethod
    def _parse_technique(cls, obj: dict) -> dict:
        return {
            "id": cls._external_id(obj) or obj.get("id"),
            "stix_id": obj.get("id"),
            "external_id": cls._external_id(obj),
            "name": obj.get("name"),
            "description": obj.get("description", ""),
            "tactics": [
                phase.get("phase_name")
                for phase in obj.get("kill_chain_phases", [])
                if phase.get("phase_name")
            ],
            "source_url": cls._external_url(obj),
            "provenance_tier": "scraped_external",
        }

    @classmethod
    def _parse_tactic(cls, obj: dict) -> dict:
        return {
            "id": cls._external_id(obj) or obj.get("id"),
            "stix_id": obj.get("id"),
            "external_id": cls._external_id(obj),
            "name": obj.get("name"),
            "shortname": obj.get("x_mitre_shortname"),
            "description": obj.get("description", ""),
            "source_url": cls._external_url(obj),
            "provenance_tier": "scraped_external",
        }

    @classmethod
    def _parse_group(cls, obj: dict) -> dict:
        return {
            "id": cls._external_id(obj) or obj.get("id"),
            "stix_id": obj.get("id"),
            "external_id": cls._external_id(obj),
            "name": obj.get("name"),
            "aliases": obj.get("aliases", []),
            "description": obj.get("description", ""),
            "source_url": cls._external_url(obj),
            "provenance_tier": "scraped_external",
        }

    @staticmethod
    def _external_id(obj: dict) -> str | None:
        for ref in obj.get("external_references", []):
            external_id = ref.get("external_id")
            if external_id:
                return cast(str, external_id)
        return None

    @staticmethod
    def _external_url(obj: dict) -> str | None:
        for ref in obj.get("external_references", []):
            url = ref.get("url")
            if url:
                return cast(str, url)
        return None

    @staticmethod
    def _normalize(value: Any) -> str:
        return str(value or "").strip().lower().replace("_", "-").replace(" ", "-")
