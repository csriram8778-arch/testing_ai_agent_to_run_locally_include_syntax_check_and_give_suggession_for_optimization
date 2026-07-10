"""CI/CD pipeline tools: list, inspect, trigger, abort executions."""

from __future__ import annotations

from harness_mcp.harness_client.factory import get_pipeline_client
from harness_mcp.server.session_context import SessionPrincipal
from harness_mcp.tools.registry import register_tool


@register_tool("list_pipelines", description="List CI/CD pipelines in the configured Harness project.")
async def list_pipelines(session: SessionPrincipal, page: int = 0, size: int = 25) -> dict:
    return await get_pipeline_client().list_pipelines(session.harness_token, page=page, size=size)


@register_tool("get_pipeline", description="Get details for one CI/CD pipeline by identifier.")
async def get_pipeline(session: SessionPrincipal, pipeline_id: str) -> dict:
    return await get_pipeline_client().get_pipeline(session.harness_token, pipeline_id)


@register_tool("get_pipeline_yaml", description="Get the YAML definition of one pipeline, for grounding Claude's code/doc generation.")
async def get_pipeline_yaml(session: SessionPrincipal, pipeline_id: str) -> dict:
    return await get_pipeline_client().get_pipeline_yaml(session.harness_token, pipeline_id)


@register_tool("list_executions", description="List recent pipeline executions, optionally filtered to one pipeline.")
async def list_executions(
    session: SessionPrincipal, pipeline_id: str | None = None, page: int = 0, size: int = 25
) -> dict:
    return await get_pipeline_client().list_executions(
        session.harness_token, pipeline_id=pipeline_id, page=page, size=size
    )


@register_tool("get_execution", description="Get the status and details of one pipeline execution.")
async def get_execution(session: SessionPrincipal, plan_execution_id: str) -> dict:
    return await get_pipeline_client().get_execution(session.harness_token, plan_execution_id)


@register_tool("get_execution_logs", description="Get logs for one pipeline execution, for triage/debugging.")
async def get_execution_logs(session: SessionPrincipal, plan_execution_id: str) -> dict:
    return await get_pipeline_client().get_execution_logs(session.harness_token, plan_execution_id)


@register_tool(
    "trigger_pipeline",
    description=(
        "Trigger a new run of a CI/CD pipeline. This is a WRITE action and "
        "requires explicit human confirmation before it executes."
    ),
)
async def trigger_pipeline(
    session: SessionPrincipal, pipeline_id: str, inputs_yaml: str | None = None
) -> dict:
    return await get_pipeline_client().trigger_pipeline(
        session.harness_token, pipeline_id, inputs_yaml=inputs_yaml
    )


@register_tool(
    "abort_execution",
    description=(
        "Abort a running pipeline execution. This is a WRITE action and "
        "requires explicit human confirmation before it executes."
    ),
)
async def abort_execution(session: SessionPrincipal, plan_execution_id: str) -> dict:
    return await get_pipeline_client().abort_execution(session.harness_token, plan_execution_id)
