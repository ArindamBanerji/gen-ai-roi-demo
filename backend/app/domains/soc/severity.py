"""SOC severity weight loading for RL reward shaping."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict

log = logging.getLogger(__name__)

DEFAULT_SEVERITY = 0.50
_SEVERITY_CACHE: Dict[str, Dict[str, float]] | None = None


def _severity_path() -> Path:
    """Return repo-root support/setup severity lookup path."""
    return Path(__file__).resolve().parents[4] / "support" / "setup" / "soc_severity_weights.json"


def get_severity_weights() -> Dict[str, Dict[str, float]]:
    """Load category severity weights, failing open to an empty mapping."""
    global _SEVERITY_CACHE
    if _SEVERITY_CACHE is not None:
        return dict(_SEVERITY_CACHE)

    path = _severity_path()
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
        _SEVERITY_CACHE = {
            str(category): {"base": float(values.get("base", DEFAULT_SEVERITY))}
            for category, values in raw.items()
            if isinstance(values, dict)
        }
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        log.warning("[RL] Failed to load SOC severity weights from %s: %s", path, exc)
        _SEVERITY_CACHE = {}

    return dict(_SEVERITY_CACHE)


def get_category_severity(category: str) -> float:
    """Return category base severity or the fail-open default."""
    weights = get_severity_weights()
    return float(weights.get(category, {}).get("base", DEFAULT_SEVERITY))


def reset_severity_cache() -> None:
    """Clear cached severity weights for tests."""
    global _SEVERITY_CACHE
    _SEVERITY_CACHE = None
