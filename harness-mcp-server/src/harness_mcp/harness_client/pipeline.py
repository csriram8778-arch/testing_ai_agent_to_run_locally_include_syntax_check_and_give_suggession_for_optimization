"""CI/CD pipeline client: list, inspect, trigger, and abort executions.

Endpoint shapes follow the well-known Harness NG Pipeline module conventions.
Verify against your account's live OpenAPI docs -- see endpoints.py.
"""

from __future__ import annotations

from typing import Any

from harness_mcp.harness_client.base import HarnessHTTPClient


class PipelineClient:
    def __init__(self, http: HarnessHTTPClient) -> None:
        self._http = http
        self._base = http.paths.pipeline

    async def list_pipelines(self, token: str, *, page: int = 0, size: int = 25) -> dict[str, Any]:
        return await self._http.request(
            "POST",
            f"{self._base}/pipelines/list",
            token=token,
            params={"page": page, "size": size},
            json_body={"filterType": "PipelineSetup"},
        )

    async def get_pipeline(self, token: str, pipeline_id: str) -> dict[str, Any]:
        return await self._http.request("GET", f"{self._base}/pipelines/{pipeline_id}", token=token)

    async def get_pipeline_yaml(self, token: str, pipeline_id: str) -> dict[str, Any]:
        return await self._http.request(
            "GET", f"{self._base}/pipelines/{pipeline_id}", token=token, params={"getYaml": "true"}
        )

    async def list_executions(
        self, token: str, *, pipeline_id: str | None = None, page: int = 0, size: int = 25
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if pipeline_id:
            body["pipelineIdentifier"] = pipeline_id
        return await self._http.request(
            "POST",
            f"{self._base}/pipelines/execution/summary",
            token=token,
            params={"page": page, "size": size},
            json_body=body,
        )

    async def get_execution(self, token: str, plan_execution_id: str) -> dict[str, Any]:
        return await self._http.request(
            "GET", f"{self._base}/pipelines/execution/v2/{plan_execution_id}", token=token
        )

    async def get_execution_logs(self, token: str, plan_execution_id: str) -> dict[str, Any]:
        return await self._http.request(
            "GET",
            f"{self._base}/pipelines/execution/{plan_execution_id}/logs",
            token=token,
        )

    async def trigger_pipeline(
        self, token: str, pipeline_id: str, *, inputs_yaml: str | None = None
    ) -> dict[str, Any]:
        return await self._http.request(
            "POST",
            f"{self._base}/pipeline/execute/{pipeline_id}",
            token=token,
            json_body={"runtimeInputYaml": inputs_yaml} if inputs_yaml else None,
        )

    async def abort_execution(self, token: str, plan_execution_id: str) -> dict[str, Any]:
        return await self._http.request(
            "POST",
            f"{self._base}/pipeline/execute/interrupt/{plan_execution_id}",
            token=token,
            params={"interruptType": "AbortAll"},
        )
