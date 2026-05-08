"""
PB-03 lightweight Sentinel poller.

The poller is disabled by default and only fetches/deduplicates Sentinel alerts.
It does not write to AGE because no safe reusable ingestion path was discovered
that satisfies the current AGE Cypher rules.
"""

import asyncio
import inspect
import logging
import os
from typing import Any, Awaitable, Callable, Dict, Optional

log = logging.getLogger(__name__)

_TRUE_VALUES = {"true", "1", "yes"}
_DEFAULT_INTERVAL_SECONDS = 300.0
_poller: Optional["SentinelPoller"] = None


def _is_polling_enabled() -> bool:
    return os.environ.get("SENTINEL_POLLING_ENABLED", "false").strip().lower() in _TRUE_VALUES


def _get_poll_interval_seconds() -> float:
    raw = os.environ.get("SENTINEL_POLL_INTERVAL_SECONDS", str(_DEFAULT_INTERVAL_SECONDS))
    try:
        interval = float(raw)
    except (TypeError, ValueError):
        return _DEFAULT_INTERVAL_SECONDS
    return interval if interval > 0 else _DEFAULT_INTERVAL_SECONDS


def _alert_id(alert: Dict[str, Any]) -> str:
    for key in ("alert_id", "id", "systemAlertId", "incident_id"):
        value = alert.get(key)
        if value:
            return str(value)
    return ""


IngestFunc = Callable[[Dict[str, Any]], Optional[Awaitable[Any]]]


class SentinelPoller:
    """Fetch Sentinel alerts on an interval and deduplicate by alert_id."""

    def __init__(
        self,
        connector: Any = None,
        interval_seconds: Optional[float] = None,
        ingest_func: Optional[IngestFunc] = None,
    ):
        self.connector = connector
        self.interval_seconds = (
            interval_seconds if interval_seconds is not None else _get_poll_interval_seconds()
        )
        self.ingest_func = ingest_func
        self._seen_alert_ids: set[str] = set()
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def _get_connector(self) -> Any:
        if self.connector is None:
            from app.connectors.sentinel_real import get_sentinel_connector

            self.connector = get_sentinel_connector()
        return self.connector

    async def start(self) -> bool:
        if self.is_running:
            return True

        connector = self._get_connector()
        if not connector.is_configured():
            log.info("Sentinel poller skipped: connector not configured")
            return False

        self._stop_event.clear()
        self._task = asyncio.create_task(self.run_forever())
        return True

    async def stop(self) -> None:
        if not self._task:
            return
        self._stop_event.set()
        try:
            await asyncio.wait_for(self._task, timeout=max(self.interval_seconds, 1.0))
        except asyncio.TimeoutError:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def run_forever(self) -> None:
        while not self._stop_event.is_set():
            await self.poll_once()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.interval_seconds,
                )
            except asyncio.TimeoutError:
                continue

    async def poll_once(self) -> Dict[str, Any]:
        connector = self._get_connector()
        if not connector.is_configured():
            return {
                "fetched": 0,
                "new": 0,
                "duplicates": 0,
                "ingested": 0,
                "ingestion_blocked": 0,
                "errors": 0,
                "skipped": "not_configured",
            }

        try:
            alerts = await connector.fetch_alerts()
        except Exception as exc:
            log.warning("Sentinel poll failed: %s", exc)
            return {
                "fetched": 0,
                "new": 0,
                "duplicates": 0,
                "ingested": 0,
                "ingestion_blocked": 0,
                "errors": 1,
            }

        new_alerts = []
        duplicates = 0
        for alert in alerts:
            alert_key = _alert_id(alert)
            if not alert_key:
                continue
            if alert_key in self._seen_alert_ids:
                duplicates += 1
                continue
            self._seen_alert_ids.add(alert_key)
            new_alerts.append(alert)

        ingested = 0
        errors = 0
        if self.ingest_func is not None:
            for alert in new_alerts:
                try:
                    result = self.ingest_func(alert)
                    if inspect.isawaitable(result):
                        await result
                    ingested += 1
                except Exception as exc:
                    errors += 1
                    log.warning("Sentinel alert ingestion failed: %s", exc)

        ingestion_blocked = 0 if self.ingest_func is not None else len(new_alerts)
        log.info(
            "Sentinel poll cycle fetched=%d new=%d duplicates=%d ingested=%d blocked=%d errors=%d",
            len(alerts),
            len(new_alerts),
            duplicates,
            ingested,
            ingestion_blocked,
            errors,
        )
        return {
            "fetched": len(alerts),
            "new": len(new_alerts),
            "duplicates": duplicates,
            "ingested": ingested,
            "ingestion_blocked": ingestion_blocked,
            "errors": errors,
        }


async def start_sentinel_poller() -> Dict[str, Any]:
    global _poller
    if not _is_polling_enabled():
        return {"started": False, "reason": "disabled"}

    if _poller is not None and _poller.is_running:
        return {"started": True, "reason": "already_running"}

    if _poller is None:
        _poller = SentinelPoller()

    started = await _poller.start()
    if not started:
        _poller = None
    return {
        "started": started,
        "reason": "started" if started else "not_configured",
    }


async def stop_sentinel_poller() -> None:
    global _poller
    if _poller is not None:
        await _poller.stop()
        _poller = None
