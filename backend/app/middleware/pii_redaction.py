"""
PB-01 response middleware for optional PII redaction.

When PII_REDACTION_ENABLED is truthy, JSON API responses are redacted with the
ci-platform PIIRedactor after endpoint business logic has produced a response.
The middleware is fail-open: parsing or redaction errors return the original
response body rather than failing the API call.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Callable, cast

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

EXEMPT_PREFIXES = (
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/admin",
)

_redactor = None


def _is_enabled() -> bool:
    value = os.environ.get("PII_REDACTION_ENABLED", "false")
    return value.strip().lower() in {"true", "1", "yes"}


def _get_redactor():
    global _redactor
    if _redactor is None:
        from ci_platform.redaction.pii_redactor import PIIRedactor

        _redactor = PIIRedactor()
        logger.info("PII response redactor initialized")
    return _redactor


def _should_skip(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in EXEMPT_PREFIXES)


def _filtered_headers(headers) -> dict[str, str]:
    return {
        key: value
        for key, value in headers.items()
        if key.lower() not in {"content-length", "content-encoding"}
    }


def _json_media_type(content_type: str) -> str:
    return content_type.split(";", 1)[0] if content_type else "application/json"


async def _read_body(response) -> bytes:
    chunks = [chunk async for chunk in response.body_iterator]
    return b"".join(chunks)


class PIIRedactionMiddleware(BaseHTTPMiddleware):
    """Redact PII from JSON responses when pilot redaction is enabled."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not _is_enabled() or _should_skip(request.url.path):
            return cast(Response, await call_next(request))

        response = await call_next(request)
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            return cast(Response, response)
        if response.headers.get("content-encoding"):
            return cast(Response, response)

        started_at = time.perf_counter()
        body_bytes = await _read_body(response)
        headers = _filtered_headers(response.headers)
        media_type = _json_media_type(content_type)

        try:
            data = json.loads(body_bytes)
            redacted_data, report = _get_redactor().redact_dict(data)
            redacted_content = json.dumps(redacted_data, ensure_ascii=False)
            if getattr(report, "total_redactions", 0) > 0:
                elapsed_ms = (time.perf_counter() - started_at) * 1000
                logger.debug(
                    "PII response redaction applied path=%s redactions=%s elapsed_ms=%.2f",
                    request.url.path,
                    report.total_redactions,
                    elapsed_ms,
                )
            return Response(
                content=redacted_content,
                status_code=response.status_code,
                headers=headers,
                media_type=media_type,
            )
        except Exception as exc:
            logger.warning(
                "PII response redaction failed open path=%s error=%s",
                request.url.path,
                type(exc).__name__,
            )
            return Response(
                content=body_bytes,
                status_code=response.status_code,
                headers=headers,
                media_type=media_type,
            )
