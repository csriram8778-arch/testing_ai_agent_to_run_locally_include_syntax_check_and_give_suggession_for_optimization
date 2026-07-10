"""Deployment tools: promote artifacts, initiate rollback, check environment state."""

from __future__ import annotations

from harness_mcp.harness_client.factory import get_deployment_client
from harness_mcp.server.session_context import SessionPrincipal
from harness_mcp.tools.registry import register_tool


@register_tool(
    "get_environment_state", description="Get the current state and active instances of a deployment environment."
)
async def get_environment_state(session: SessionPrincipal, environment_id: str) -> dict:
    return await get_deployment_client().get_environment_state(session.harness_token, environment_id)


@register_tool(
    "promote_artifact",
    description=(
        "Promote an artifact version to an environment via its deployment "
        "pipeline. This is a WRITE action and requires explicit human "
        "confirmation before it executes."
    ),
)
async def promote_artifact(
    session: SessionPrincipal,
    pipeline_id: str,
    environment_id: str,
    service_id: str,
    artifact_version: str,
) -> dict:
    return await get_deployment_client().promote_artifact(
        session.harness_token,
        pipeline_id=pipeline_id,
        environment_id=environment_id,
        service_id=service_id,
        artifact_version=artifact_version,
    )


@register_tool(
    "initiate_rollback",
    description=(
        "Roll a service in an environment back to its previous (or a "
        "specified) deployment. This is a WRITE action and requires explicit "
        "human confirmation before it executes."
    ),
)
async def initiate_rollback(
    session: SessionPrincipal,
    environment_id: str,
    service_id: str,
    target_execution_id: str | None = None,
) -> dict:
    return await get_deployment_client().initiate_rollback(
        session.harness_token,
        environment_id=environment_id,
        service_id=service_id,
        target_execution_id=target_execution_id,
    )
