"""Re-exports the session principal type for convenient importing from `auth.*`."""

from harness_mcp.server.session_context import (
    SessionPrincipal,
    get_current_session,
    set_current_session,
)

__all__ = ["SessionPrincipal", "get_current_session", "set_current_session"]
