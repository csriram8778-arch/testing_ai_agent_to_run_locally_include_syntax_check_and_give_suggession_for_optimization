"""Security Testing Orchestration (STO) client: scan results, vulnerability
triage, and critical-finding gating. STO API versioning (v1 vs v2) has
shifted across Harness releases -- verify the pinned version against your
account's docs; see endpoints.py.
"""

from __future__ import annotations

from typing import Any

from harness_mcp.harness_client.base import HarnessHTTPClient


class StoClient:
    def __init__(self, http: HarnessHTTPClient) -> None:
        self._http = http
        self._base = http.paths.sto

    async def list_scan_results(
        self, token: str, *, target_id: str | None = None, pipeline_execution_id: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if target_id:
            params["targetId"] = target_id
        if pipeline_execution_id:
            params["pipelineExecutionId"] = pipeline_execution_id
        return await self._http.request("GET", f"{self._base}/issues", token=token, params=params)

    async def get_vulnerability(self, token: str, issue_id: str) -> dict[str, Any]:
        return await self._http.request("GET", f"{self._base}/issues/{issue_id}", token=token)

    async def check_critical_block(self, token: str, pipeline_execution_id: str) -> dict[str, Any]:
        """Read-only check: does this execution have unresolved CRITICAL findings
        that a governing STO policy would block on?"""
        return await self._http.request(
            "GET",
            f"{self._base}/pipeline-execution/{pipeline_execution_id}/exemptions",
            token=token,
            params={"severity": "CRITICAL"},
        )

    async def triage_vulnerability(
        self, token: str, issue_id: str, *, status: str, comment: str
    ) -> dict[str, Any]:
        """`status` is one of Harness's STO triage states, e.g. 'ExemptionRequested',
        'Confirmed', 'FalsePositive' -- validate against your org's configured set."""
        return await self._http.request(
            "PATCH",
            f"{self._base}/issues/{issue_id}/triage",
            token=token,
            json_body={"status": status, "comment": comment},
        )
