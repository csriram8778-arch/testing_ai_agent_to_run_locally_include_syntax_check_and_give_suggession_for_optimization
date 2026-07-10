"""Chaos engineering tools: view experiments, trigger with an approval gate."""

from __future__ import annotations

from harness_mcp.harness_client.factory import get_chaos_client
from harness_mcp.server.session_context import SessionPrincipal
from harness_mcp.tools.registry import register_tool


@register_tool("list_chaos_experiments", description="List configured chaos experiments in the project.")
async def list_chaos_experiments(session: SessionPrincipal, project_id: str | None = None) -> dict:
    return await get_chaos_client().list_experiments(session.harness_token, project_id=project_id)


@register_tool("get_chaos_experiment", description="Get details of one chaos experiment by identifier.")
async def get_chaos_experiment(session: SessionPrincipal, experiment_id: str) -> dict:
    return await get_chaos_client().get_experiment(session.harness_token, experiment_id)


@register_tool(
    "run_chaos_experiment",
    description=(
        "Run a chaos experiment against a target environment. This is a "
        "WRITE action with an explicit approval gate per the spec, and "
        "requires human confirmation before it executes."
    ),
)
async def run_chaos_experiment(session: SessionPrincipal, experiment_id: str) -> dict:
    return await get_chaos_client().run_experiment(session.harness_token, experiment_id)
