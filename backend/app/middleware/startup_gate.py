"""Lifespan-driven startup fence without per-request graph probes."""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class StartupGateMiddleware:
    """Reject business requests while lifespan initialization is in progress.

    The lifespan arms the flag before initializing and releases it on success.
    ASGI harnesses that do not run lifespan retain their existing behavior.
    Once ready, the only steady-state work is a boolean lookup and delegation.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] == "http"
            and getattr(scope["app"].state, "startup_complete", True) is False
            and scope["path"] not in {"/api/health", "/health", "/"}
        ):
            response = JSONResponse(
                {"detail": "Backend initializing", "retry_after_seconds": 2},
                status_code=503,
                headers={"Retry-After": "2"},
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
