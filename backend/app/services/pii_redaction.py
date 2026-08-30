"""Application-level PII redaction for endpoint response payloads."""

from __future__ import annotations

import logging
import os
import importlib
from typing import Any

logger = logging.getLogger(__name__)

EXEMPT_PREFIXES = (
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/admin",
)

_redactor: Any = None


def is_enabled() -> bool:
    value = os.environ.get("PII_REDACTION_ENABLED", "false")
    return value.strip().lower() in {"true", "1", "yes"}


def should_skip(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in EXEMPT_PREFIXES)


def _get_redactor() -> Any:
    global _redactor
    if _redactor is None:
        module = importlib.import_module("ci_platform.redaction.pii_redactor")
        _redactor = module.PIIRedactor()
        logger.info("PII response redactor initialized")
    return _redactor


def redact_payload(payload: Any, path: str = "") -> Any:
    """Redact a JSON-compatible endpoint payload, preserving fail-open behavior."""
    if not is_enabled() or should_skip(path):
        return payload
    try:
        redacted, report = _get_redactor().redact_dict(payload)
        total_redactions = getattr(report, "total_redactions", 0)
        if total_redactions > 0:
            logger.debug(
                "PII response redaction applied path=%s redactions=%s",
                path,
                total_redactions,
            )
        return redacted
    except Exception as exc:
        logger.warning(
            "PII response redaction failed open path=%s error=%s",
            path,
            type(exc).__name__,
        )
        return payload
