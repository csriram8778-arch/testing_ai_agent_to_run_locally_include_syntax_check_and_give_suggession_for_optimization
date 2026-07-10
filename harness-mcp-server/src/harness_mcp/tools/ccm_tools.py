"""Cloud cost management tools -- strictly read-only, per spec ("query cost
data and anomaly alerts (read-only)"). No WRITE-tier tool exists in this
module at all."""

from __future__ import annotations

from harness_mcp.harness_client.factory import get_ccm_client
from harness_mcp.server.session_context import SessionPrincipal
from harness_mcp.tools.registry import register_tool


@register_tool("get_cost_summary", description="Get a cost summary for a saved perspective over a time range.")
async def get_cost_summary(
    session: SessionPrincipal, perspective_id: str, start_time: str, end_time: str
) -> dict:
    return await get_ccm_client().get_cost_summary(
        session.harness_token, perspective_id=perspective_id, start_time=start_time, end_time=end_time
    )


@register_tool("list_cost_anomalies", description="List detected cloud cost anomalies, optionally within a time range.")
async def list_cost_anomalies(
    session: SessionPrincipal, start_time: str | None = None, end_time: str | None = None
) -> dict:
    return await get_ccm_client().list_cost_anomalies(
        session.harness_token, start_time=start_time, end_time=end_time
    )


@register_tool("get_cost_recommendations", description="List cost optimization recommendations.")
async def get_cost_recommendations(session: SessionPrincipal, limit: int = 25) -> dict:
    return await get_ccm_client().get_cost_recommendations(session.harness_token, limit=limit)
