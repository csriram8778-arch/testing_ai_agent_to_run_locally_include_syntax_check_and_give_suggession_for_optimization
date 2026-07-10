"""Per-request identity propagation.

In HTTP mode the official MCP Python SDK's Streamable HTTP transport does not
hand tool handlers a reference to the originating HTTP request, so headers
(``x-harness-api-key``) have to be captured by ASGI-level middleware and
threaded through via a ``contextvars.ContextVar``. This works because
contextvars propagate through the *same* in-process async call stack --
middleware -> ASGI app -> MCP dispatch -> tool handler -- as long as nothing
along that path spawns a detached task or thread. ``auth.middleware`` sets
this var fresh on *every* HTTP request (never cached across a session), so a
rotated or expired token is re-checked on each call.
"""

from __future__ import annotations

import contextvars
import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SessionPrincipal:
    """The authenticated identity + scoped Harness token for one in-flight call.

    Deliberately holds the raw token so it can be used for exactly one
    Harness API call and then discarded -- it must never be copied into a
    tool's return value, audit params, or logged. ``__repr__`` is overridden
    so an accidental ``print(principal)`` / log call never leaks it.
    """

    user_id: str
    harness_account_id: str
    harness_token: str
    token_expires_at: float | None
    request_id: str

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            f"SessionPrincipal(user_id={self.user_id!r}, "
            f"harness_account_id={self.harness_account_id!r}, "
            f"harness_token=<redacted>, request_id={self.request_id!r})"
        )


_current_session: contextvars.ContextVar[SessionPrincipal | None] = contextvars.ContextVar(
    "current_session", default=None
)


def set_current_session(principal: SessionPrincipal) -> contextvars.Token:
    return _current_session.set(principal)


def reset_current_session(token: contextvars.Token) -> None:
    _current_session.reset(token)


def get_current_session() -> SessionPrincipal:
    """Return the authenticated principal for the in-flight call.

    Raises if called outside of an authenticated request context -- there is
    no "unauthenticated fallback" value. Every tool handler must go through
    this accessor rather than receiving the token as an argument, so it can
    never appear in a tool's input parameters (and therefore never in audit
    logs or model context).
    """

    principal = _current_session.get()
    if principal is None:
        raise RuntimeError(
            "No authenticated session in context. This should be impossible: "
            "auth middleware must set a SessionPrincipal before any tool "
            "handler runs. Refusing to proceed rather than falling back to "
            "an unauthenticated call."
        )
    return principal


def new_request_id() -> str:
    return uuid.uuid4().hex
