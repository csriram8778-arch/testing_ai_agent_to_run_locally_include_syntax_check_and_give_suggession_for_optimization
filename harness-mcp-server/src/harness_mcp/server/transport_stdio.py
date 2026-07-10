"""Single-user local/dev mode: one Harness Service Account Token, read once
from the configured secrets backend (or directly from the environment
variable named by HARNESS_STDIO_TOKEN_ENV_VAR for local dev), set as the
session context once before the stdio loop starts. Intended for a developer
running Claude Desktop/Code locally against their own scoped SAT -- NOT for
shared/team use, which must go through HTTP mode (see transport_http.py) so
each person authenticates with their own identity.
"""

from __future__ import annotations

import os

from harness_mcp.observability.logging_config import configure_logging, get_logger
from harness_mcp.server.app import build_mcp_server
from harness_mcp.server.session_context import SessionPrincipal, new_request_id, set_current_session
from harness_mcp.settings import get_settings

logger = get_logger(__name__)


def _load_stdio_token(settings) -> str:
    env_var = settings.harness_stdio_service_account_token_env
    token = os.environ.get(env_var)
    if token:
        return token
    try:
        from harness_mcp.secrets.factory import get_secrets_provider

        return get_secrets_provider().get_secret("harness-stdio-service-account-token")
    except Exception as exc:  # pragma: no cover - operator misconfiguration
        raise RuntimeError(
            f"No Harness token available for stdio mode: set the {env_var} "
            "environment variable, or store 'harness-stdio-service-account-token' "
            "in the configured secrets backend."
        ) from exc


def run_stdio() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    token = _load_stdio_token(settings)
    principal = SessionPrincipal(
        user_id=f"stdio-local:{os.environ.get('USER') or os.environ.get('USERNAME') or 'unknown'}",
        harness_account_id=settings.harness_account_id,
        harness_token=token,
        token_expires_at=None,
        request_id=new_request_id(),
    )
    # Set once, before the stdio event loop starts creating tasks -- asyncio
    # tasks created after this point inherit the current contextvars context.
    set_current_session(principal)

    logger.info("starting_stdio_server", user_id=principal.user_id)
    mcp = build_mcp_server()
    mcp.run(transport="stdio")
