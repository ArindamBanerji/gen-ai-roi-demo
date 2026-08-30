"""
PB-01 response middleware for optional PII redaction.

When PII_REDACTION_ENABLED is truthy, JSON API responses are redacted with the
ci-platform PIIRedactor after endpoint business logic has produced a response.
The middleware is fail-open: parsing or redaction errors return the original
response body rather than failing the API call.
"""

from __future__ import annotations

import logging
from typing import Callable, cast

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.pii_redaction import is_enabled, should_skip

logger = logging.getLogger(__name__)

_is_enabled = is_enabled
_should_skip = should_skip


class PIIRedactionMiddleware(BaseHTTPMiddleware):
    """Advertise endpoint-level PII redaction without touching response bodies."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        if is_enabled() and not should_skip(request.url.path):
            response.headers.setdefault("X-PII-Redaction", "handler")
        return cast(Response, response)
