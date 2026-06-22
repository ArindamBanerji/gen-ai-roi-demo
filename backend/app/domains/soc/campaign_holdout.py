"""Deterministic campaign-context holdout helpers."""

from __future__ import annotations

import hashlib


def banner_suppressed(alert_id: str, holdout_pct: int = 15) -> bool:
    """Return whether campaign context should be hidden for this alert."""
    pct = max(0, min(100, int(holdout_pct)))
    if pct <= 0:
        return False
    if pct >= 100:
        return True
    digest = hashlib.sha256(str(alert_id or "").encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:8], "big") % 100
    return bucket < pct
