"""Liveness vs readiness handlers, mounted unauthenticated (see auth.middleware)."""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse

from harness_mcp.audit_logging.sink_factory import get_audit_sinks
from harness_mcp.harness_client.base import HarnessHTTPClient
from harness_mcp.secrets.factory import get_secrets_provider
from harness_mcp.settings import get_settings


async def liveness(request: Request) -> JSONResponse:
    """Process-only check. Must never depend on Harness reachability, or a
    transient Harness outage would crash-loop every pod."""
    return JSONResponse({"status": "alive"})


async def readiness(request: Request) -> JSONResponse:
    settings = get_settings()
    checks: dict[str, bool] = {}

    try:
        get_secrets_provider()
        checks["secrets_backend"] = True
    except Exception:
        checks["secrets_backend"] = False

    try:
        sinks = get_audit_sinks()
        checks["audit_sink"] = any(await sink.healthy() for sink in sinks)
    except Exception:
        checks["audit_sink"] = False

    try:
        client = HarnessHTTPClient(settings)
        checks["harness_reachable"] = await client.ping()
    except Exception:
        checks["harness_reachable"] = False

    ready = all(checks.values())
    return JSONResponse({"status": "ready" if ready else "not_ready", "checks": checks},
                         status_code=200 if ready else 503)
