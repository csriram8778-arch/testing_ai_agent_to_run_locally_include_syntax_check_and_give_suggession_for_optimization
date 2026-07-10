"""ASGI middleware enforcing "no unauthenticated fallback" for HTTP mode.

Mounted around FastMCP's Streamable HTTP app. Runs before ANY MCP method
(including ``initialize``) is dispatched. A request with a missing, empty, or
invalid/expired ``x-harness-api-key`` header is rejected with 401 before it
ever reaches MCP routing -- there is no code path in this server that
services an MCP request without first passing through here.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse

from harness_mcp.auth.token_validator import TokenValidationError, TokenValidator
from harness_mcp.observability.logging_config import get_logger
from harness_mcp.server.session_context import (
    SessionPrincipal,
    new_request_id,
    reset_current_session,
    set_current_session,
)

logger = get_logger(__name__)

HEADER_NAME = "x-harness-api-key"

# Health/readiness probes must be reachable without a Harness token so
# Kubernetes can evaluate them; nothing under these paths touches Harness.
_UNAUTHENTICATED_PATHS = {"/healthz", "/readyz", "/metrics"}


class HarnessSessionAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token_validator: TokenValidator) -> None:
        super().__init__(app)
        self._validator = token_validator

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ):
        if request.url.path in _UNAUTHENTICATED_PATHS:
            return await call_next(request)

        token = request.headers.get(HEADER_NAME)
        if not token:
            logger.warning("rejected_unauthenticated_request", path=request.url.path)
            return JSONResponse(
                {"error": f"missing required '{HEADER_NAME}' header"}, status_code=401
            )

        try:
            identity = await self._validator.validate(token)
        except TokenValidationError as exc:
            logger.warning("rejected_invalid_token", path=request.url.path, reason=str(exc))
            return JSONResponse({"error": "invalid or expired Harness token"}, status_code=401)

        principal = SessionPrincipal(
            user_id=identity.user_id,
            harness_account_id=identity.harness_account_id,
            harness_token=token,
            token_expires_at=identity.expires_at,
            request_id=new_request_id(),
        )
        ctx_token = set_current_session(principal)
        try:
            return await call_next(request)
        finally:
            reset_current_session(ctx_token)
