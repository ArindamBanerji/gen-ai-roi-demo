"""Celonis Developer Portal REST connector with cache/fixture fallback."""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


class CelonisConnector:
    """Read process-model metadata from a Celonis developer demo endpoint."""

    name = "celonis"
    source = "Celonis"

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.url = os.environ.get(
            "CELONIS_KNOWLEDGE_MODELS_URL",
            "https://16abf815-remockly.com/intelligence/api/knowledge-models",
        )
        self.token = os.environ.get("CELONIS_API_TOKEN")
        self.cache_path = cache_dir or Path(__file__).resolve().parents[1] / "data"
        self.cache_file = self.cache_path / "celonis.json"
        self.fixture_file = self.cache_path / "celonis_fixture.json"

    async def health_check(self) -> dict[str, Any]:
        started = time.perf_counter()
        if not self.token:
            return self._status(False, "Bearer token not configured; using cached fixture", started)
        try:
            await asyncio.to_thread(self._request)
            return self._status(True, "API reachable", started)
        except requests.RequestException as exc:
            return self._status(False, f"API unavailable: {type(exc).__name__}", started)

    async def fetch(self) -> dict[str, Any]:
        try:
            if self.token:
                payload = await asyncio.to_thread(self._request)
                normalized = self._normalize(payload)
                self._write_cache(normalized)
                return self._envelope(normalized, "live")
        except requests.RequestException:
            pass
        cached = self._read_json(self.cache_file) or self._read_json(self.fixture_file) or {"models": []}
        return self._envelope(cached, "cached" if self.cache_file.is_file() else "fixture")

    def _request(self) -> dict[str, Any]:
        response = requests.get(
            self.url,
            headers={"Authorization": f"Bearer {self.token or ''}", "Accept": "application/json"},
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {"value": payload}

    def _normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        raw = payload.get("data", payload.get("knowledge_models", payload))
        models = raw if isinstance(raw, list) else raw.get("items", []) if isinstance(raw, dict) else []
        return {"models": models[:5] if isinstance(models, list) else []}

    def _envelope(self, payload: dict[str, Any], mode: str) -> dict[str, Any]:
        return {
            "source": self.name,
            "label": self.source,
            "mode": mode,
            "models": payload.get("models", []),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    def _status(self, healthy: bool, message: str, started: float) -> dict[str, Any]:
        return {
            "source": self.name,
            "label": self.source,
            "healthy": healthy,
            "message": message,
            "mode": "live" if healthy else "fallback",
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any] | None:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def _write_cache(self, payload: dict[str, Any]) -> None:
        self.cache_path.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
