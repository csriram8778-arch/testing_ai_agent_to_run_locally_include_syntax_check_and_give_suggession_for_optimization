"""Feature flag tools: list, evaluate, update flag states with rollout controls."""

from __future__ import annotations

from harness_mcp.harness_client.factory import get_feature_flag_client
from harness_mcp.server.session_context import SessionPrincipal
from harness_mcp.tools.registry import register_tool


@register_tool("list_flags", description="List feature flags, optionally scoped to one environment.")
async def list_flags(session: SessionPrincipal, environment_id: str | None = None) -> dict:
    return await get_feature_flag_client().list_flags(session.harness_token, environment_id=environment_id)


@register_tool("get_flag", description="Get details of one feature flag by identifier.")
async def get_flag(session: SessionPrincipal, identifier: str) -> dict:
    return await get_feature_flag_client().get_flag(session.harness_token, identifier)


@register_tool("evaluate_flag", description="Evaluate a feature flag's current value for an environment/target.")
async def evaluate_flag(
    session: SessionPrincipal, identifier: str, environment_id: str, target_id: str | None = None
) -> dict:
    return await get_feature_flag_client().evaluate_flag(
        session.harness_token, identifier, environment_id=environment_id, target_id=target_id
    )


@register_tool(
    "update_flag_state",
    description=(
        "Enable/disable a feature flag and optionally set a rollout "
        "percentage in an environment. This is a WRITE action and requires "
        "explicit human confirmation before it executes."
    ),
)
async def update_flag_state(
    session: SessionPrincipal,
    identifier: str,
    environment_id: str,
    enabled: bool,
    rollout_percentage: int | None = None,
) -> dict:
    return await get_feature_flag_client().update_flag_state(
        session.harness_token,
        identifier,
        environment_id=environment_id,
        enabled=enabled,
        rollout_percentage=rollout_percentage,
    )
