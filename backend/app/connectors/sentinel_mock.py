"""
SentinelMockConnector — test harness for the real Microsoft Sentinel connector.

Accepts synthetic_pilot_alerts.json (Sentinel normalized schema) and streams
alerts as normalized dicts ready for ingestion into the SOC graph.

Input schema (per alert in JSON file):
  alert_id, day, category, shift, severity, timestamp,
  alert_type, source_location, asset_id, user_id

Output schema (normalized for SOC graph):
  id, alert_type, severity, category, source_location,
  asset_id, user_id, timestamp_epoch, status, day, shift, source
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Iterator


def _iso_to_epoch_ms(iso_str: str) -> int:
    """Convert ISO-8601 string to milliseconds since Unix epoch."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except ValueError:
        # Fallback: treat as UTC naive
        dt = datetime.strptime(iso_str[:19], "%Y-%m-%dT%H:%M:%S").replace(
            tzinfo=timezone.utc
        )
    return int(dt.timestamp() * 1000)


class SentinelMockConnector:
    """
    Mock connector that replays synthetic Sentinel alerts.

    Usage:
        connector = SentinelMockConnector()
        connector.load("path/to/synthetic_pilot_alerts.json")
        for alert in connector.stream(day_filter=(0, 30)):
            ingest(alert)
    """

    def __init__(self) -> None:
        self._alerts: list[dict] = []

    def load(self, filepath: str | Path) -> int:
        """
        Load alerts from JSON file.
        Returns the number of alerts loaded.
        Accepts either a top-level list or {"alerts": [...]} wrapper.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Alert file not found: {path}")
        with open(path) as f:
            raw = json.load(f)
        self._alerts = raw if isinstance(raw, list) else raw.get("alerts", [])
        return len(self._alerts)

    def normalize(self, alert: dict) -> dict:
        """
        Map Sentinel field names to SOC graph schema.

        Sentinel field    -> SOC field
        ---------------------------------
        alert_id          -> id
        alert_type        -> alert_type   (keep as-is — real Sentinel name)
        severity          -> severity
        timestamp         -> timestamp_epoch  (ISO -> epoch ms int)
        category          -> category
        source_location   -> source_location
        asset_id          -> asset_id
        user_id           -> user_id
        day               -> day          (passthrough for filtering)
        shift             -> shift        (passthrough)
        """
        ts_raw = alert.get("timestamp", "")
        if ts_raw:
            timestamp_epoch = _iso_to_epoch_ms(ts_raw)
        else:
            timestamp_epoch = int(datetime.utcnow().timestamp() * 1000)

        return {
            "id":               alert["alert_id"],
            "alert_type":       alert.get("alert_type", "unknown"),
            "severity":         alert.get("severity", "medium"),
            "category":         alert.get("category", "unknown"),
            "source_location":  alert.get("source_location", ""),
            "asset_id":         alert.get("asset_id", ""),
            "user_id":          alert.get("user_id", ""),
            "timestamp_epoch":  timestamp_epoch,
            "day":              alert.get("day", 0),
            "shift":            alert.get("shift", ""),
            "status":           "pending",
            "source":           "sentinel_mock_v1",
        }

    def stream(
        self,
        day_filter: tuple[int, int] | None = None,
    ) -> Generator[dict, None, None]:
        """
        Yield normalized alert dicts one at a time.

        Args:
            day_filter: optional (min_day, max_day) tuple inclusive.
                        If None, all alerts are streamed.
        """
        for raw in self._alerts:
            day = raw.get("day", 0)
            if day_filter is not None:
                lo, hi = day_filter
                if not (lo <= day <= hi):
                    continue
            yield self.normalize(raw)
