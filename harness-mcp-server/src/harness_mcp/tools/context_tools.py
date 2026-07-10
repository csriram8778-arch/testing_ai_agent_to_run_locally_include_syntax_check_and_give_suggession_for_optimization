"""Grounding-context tools for Claude's own code generation, review, and
documentation. Claude does the generation/review itself -- these tools only
fetch real pipeline/repo state so it isn't guessing; there is no separate
LLM call in this server."""

from __future__ import annotations

from harness_mcp.harness_client.factory import get_context_client
from harness_mcp.server.session_context import SessionPrincipal
from harness_mcp.tools.registry import register_tool


@register_tool(
    "get_repo_info",
    description="Get repository metadata (URL, default branch) via a configured Harness connector, to ground code review/generation.",
)
async def get_repo_info(session: SessionPrincipal, connector_id: str, repo_name: str) -> dict:
    return await get_context_client().get_repo_info(session.harness_token, connector_id, repo_name)
