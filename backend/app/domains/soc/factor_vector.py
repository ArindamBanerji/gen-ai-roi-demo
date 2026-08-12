"""Validation boundary for SOC Decision.factor_vector values."""

from __future__ import annotations

import math
from typing import Any

from app.domains.soc.config import N_FACTORS


def validated_factor_vector(value: Any, *, field: str = "factor_vector") -> list[float]:
    """Return a canonical SOC factor vector or fail before an AGE write."""
    if hasattr(value, "tolist"):
        value = value.tolist()
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be a list or tuple")
    if len(value) != N_FACTORS:
        raise ValueError(f"{field} must contain exactly {N_FACTORS} values")
    result: list[float] = []
    for index, raw in enumerate(value):
        if isinstance(raw, bool):
            raise ValueError(f"{field}[{index}] must be numeric")
        try:
            number = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field}[{index}] must be numeric") from exc
        if not math.isfinite(number) or not 0.0 <= number <= 1.0:
            raise ValueError(f"{field}[{index}] must be finite and within [0, 1]")
        result.append(number)
    return result
