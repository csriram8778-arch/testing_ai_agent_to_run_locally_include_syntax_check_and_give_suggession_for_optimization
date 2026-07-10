"""Security Testing Orchestration (STO) tools: triage vulnerabilities, view
scan results, block on critical findings."""

from __future__ import annotations

from harness_mcp.harness_client.factory import get_sto_client
from harness_mcp.server.session_context import SessionPrincipal
from harness_mcp.tools.registry import register_tool


@register_tool("list_scan_results", description="List security scan findings for a target or pipeline execution.")
async def list_scan_results(
    session: SessionPrincipal, target_id: str | None = None, pipeline_execution_id: str | None = None
) -> dict:
    return await get_sto_client().list_scan_results(
        session.harness_token, target_id=target_id, pipeline_execution_id=pipeline_execution_id
    )


@register_tool("get_vulnerability", description="Get details of one vulnerability/finding by issue id.")
async def get_vulnerability(session: SessionPrincipal, issue_id: str) -> dict:
    return await get_sto_client().get_vulnerability(session.harness_token, issue_id)


@register_tool(
    "check_critical_block",
    description="Check whether a pipeline execution has unresolved CRITICAL findings that block promotion.",
)
async def check_critical_block(session: SessionPrincipal, pipeline_execution_id: str) -> dict:
    return await get_sto_client().check_critical_block(session.harness_token, pipeline_execution_id)


@register_tool(
    "triage_vulnerability",
    description=(
        "Set the triage status (e.g. confirmed, false positive, exemption "
        "requested) on a vulnerability finding. This is a WRITE action and "
        "requires explicit human confirmation before it executes."
    ),
)
async def triage_vulnerability(session: SessionPrincipal, issue_id: str, status: str, comment: str) -> dict:
    return await get_sto_client().triage_vulnerability(
        session.harness_token, issue_id, status=status, comment=comment
    )
