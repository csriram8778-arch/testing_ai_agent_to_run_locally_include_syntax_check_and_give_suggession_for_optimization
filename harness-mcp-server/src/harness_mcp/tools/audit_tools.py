"""Harness-side audit log tools -- read-only access for compliance review.
Distinct from this server's own compliance audit trail in `audit_logging/`."""

from __future__ import annotations

from harness_mcp.harness_client.factory import get_audit_client
from harness_mcp.server.session_context import SessionPrincipal
from harness_mcp.tools.registry import register_tool


@register_tool("query_audit_trail", description="Query the Harness platform audit trail (read-only).")
async def query_audit_trail(
    session: SessionPrincipal,
    start_time: str | None = None,
    end_time: str | None = None,
    actions: list[str] | None = None,
    page: int = 0,
    size: int = 25,
) -> dict:
    return await get_audit_client().query_audit_trail(
        session.harness_token,
        start_time=start_time,
        end_time=end_time,
        actions=actions,
        page=page,
        size=size,
    )
