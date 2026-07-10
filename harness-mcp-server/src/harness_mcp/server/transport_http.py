"""Multi-user HTTP mode: the server holds zero Harness credentials. Every
request must carry its own scoped token via the `x-harness-api-key` header,
validated and turned into a `SessionPrincipal` by `auth.middleware` before
any MCP method runs. See `server/session_context.py` for why this has to be
ASGI-level middleware rather than something inside a tool handler.
"""

from __future__ import annotations

import httpx
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route

from harness_mcp.auth.middleware import HarnessSessionAuthMiddleware
from harness_mcp.auth.token_validator import TokenValidator
from harness_mcp.observability.healthcheck import liveness, readiness
from harness_mcp.observability.logging_config import configure_logging, get_logger
from harness_mcp.server.app import build_mcp_server
from harness_mcp.settings import get_settings

logger = get_logger(__name__)


async def metrics(request: Request) -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def build_http_app() -> Starlette:
    settings = get_settings()
    configure_logging(settings.log_level)

    mcp = build_mcp_server()
    mcp_asgi_app = mcp.streamable_http_app()

    validator = TokenValidator(settings, httpx.AsyncClient())

    app = Starlette(
        routes=[
            Route("/healthz", liveness),
            Route("/readyz", readiness),
            Route("/metrics", metrics),
            Mount("/", app=mcp_asgi_app),
        ]
    )
    app.add_middleware(HarnessSessionAuthMiddleware, token_validator=validator)

    logger.info(
        "starting_http_server",
        host=settings.http_host,
        port=settings.http_port,
        tls_terminated_upstream=settings.tls_terminated_upstream,
    )
    return app


def run_http() -> None:
    import uvicorn

    settings = get_settings()
    app = build_http_app()

    uvicorn_kwargs: dict = {"host": settings.http_host, "port": settings.http_port}
    if not settings.tls_terminated_upstream:
        uvicorn_kwargs["ssl_certfile"] = settings.tls_cert_path
        uvicorn_kwargs["ssl_keyfile"] = settings.tls_key_path

    uvicorn.run(app, **uvicorn_kwargs)
