"""NIST NVD API v2.0 client for CVE intelligence."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping, cast


class NVDClient:
    """NIST NVD API v2.0 client.

    Public, rate-limited (5 req/30s without API key).
    Env var NVD_API_KEY enables higher rate limits when available.
    """

    BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    def __init__(self, *, api_key: str | None = None, cache_dir: Path | None = None):
        self._api_key = api_key or os.environ.get("NVD_API_KEY")
        self._cache_dir = Path(cache_dir) if cache_dir else None

    def recent_cves(self, *, days: int = 30, keyword: str | None = None) -> list[dict]:
        """Recent CVEs from NVD."""

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=days)
        params = {
            "pubStartDate": self._nvd_datetime(start),
            "pubEndDate": self._nvd_datetime(now),
            "resultsPerPage": "50",
        }
        if keyword:
            params["keywordSearch"] = keyword
        return self.parse_response(self._fetch_json(params))

    def _fetch_json(self, params: Mapping[str, str]) -> dict:
        query = urllib.parse.urlencode(params)
        request = urllib.request.Request(f"{self.BASE_URL}?{query}")
        if self._api_key:
            request.add_header("apiKey", self._api_key)

        with urllib.request.urlopen(request, timeout=30) as response:
            payload = cast(dict, json.loads(response.read().decode("utf-8")))
            delay = self.rate_limit_delay(response.headers)
            if delay > 0:
                time.sleep(min(delay, 30))
            return payload

    @classmethod
    def parse_response(cls, payload: dict) -> list[dict]:
        """Parse NVD v2.0 CVE payloads into compact CVE records."""

        parsed = []
        for item in payload.get("vulnerabilities", []):
            cve = item.get("cve", {})
            metrics = cve.get("metrics", {})
            parsed.append(
                {
                    "id": cve.get("id"),
                    "published": cve.get("published"),
                    "last_modified": cve.get("lastModified"),
                    "description": cls._english_description(cve),
                    "cvss": cls._cvss(metrics),
                    "weaknesses": cls._weaknesses(cve),
                    "references": [
                        ref.get("url")
                        for ref in cve.get("references", {}).get("referenceData", [])
                        if ref.get("url")
                    ],
                    "provenance_tier": "scraped_external",
                }
            )
        return parsed

    @staticmethod
    def rate_limit_delay(headers: Mapping[str, str]) -> float:
        """Return the requested delay from common NVD rate-limit headers."""

        retry_after = headers.get("Retry-After") or headers.get("retry-after")
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                return 0.0

        remaining = headers.get("X-RateLimit-Remaining") or headers.get(
            "x-ratelimit-remaining"
        )
        reset = headers.get("X-RateLimit-Reset") or headers.get("x-ratelimit-reset")
        if remaining == "0" and reset:
            try:
                return max(0.0, float(reset) - time.time())
            except ValueError:
                return 0.0
        return 0.0

    @staticmethod
    def _nvd_datetime(value: datetime) -> str:
        return value.strftime("%Y-%m-%dT%H:%M:%S.000")

    @staticmethod
    def _english_description(cve: dict) -> str:
        for desc in cve.get("descriptions", []):
            if desc.get("lang") == "en":
                return cast(str, desc.get("value", ""))
        return ""

    @staticmethod
    def _weaknesses(cve: dict) -> list[str]:
        values = []
        for weakness in cve.get("weaknesses", []):
            for desc in weakness.get("description", []):
                value = desc.get("value")
                if value:
                    values.append(value)
        return values

    @staticmethod
    def _cvss(metrics: dict) -> dict | None:
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            entries = metrics.get(key) or []
            if not entries:
                continue
            data = entries[0].get("cvssData", {})
            return {
                "version": data.get("version"),
                "base_score": data.get("baseScore"),
                "base_severity": entries[0].get("baseSeverity"),
                "vector": data.get("vectorString"),
            }
        return None
