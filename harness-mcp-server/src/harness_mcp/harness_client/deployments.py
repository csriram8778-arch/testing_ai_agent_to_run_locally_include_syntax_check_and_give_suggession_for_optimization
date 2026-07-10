"""Deployment client: environment state, artifact promotion, rollback.

Harness NG expresses promotion/rollback largely through pipeline stage
triggers against CD environments/services; this client wraps that behind a
deployment-shaped interface. Verify exact stage/trigger identifiers with
your pipeline authors -- see endpoints.py and README "Known limitations".
"""

from __future__ import annotations

from typing import Any

from harness_mcp.harness_client.base import HarnessHTTPClient


class DeploymentClient:
    def __init__(self, http: HarnessHTTPClient) -> None:
        self._http = http
        self._ng = http.paths.ng
        self._pipeline = http.paths.pipeline

    async def get_environment_state(self, token: str, environment_id: str) -> dict[str, Any]:
        env = await self._http.request(
            "GET", f"{self._ng}/environmentsV2/{environment_id}", token=token
        )
        instances = await self._http.request(
            "GET",
            f"{self._ng}/instances/list",
            token=token,
            params={"environmentIdentifier": environment_id},
        )
        return {"environment": env, "activeInstances": instances}

    async def promote_artifact(
        self,
        token: str,
        *,
        pipeline_id: str,
        environment_id: str,
        service_id: str,
        artifact_version: str,
    ) -> dict[str, Any]:
        inputs_yaml = (
            f"pipeline:\n"
            f"  identifier: {pipeline_id}\n"
            f"  variables:\n"
            f"    - name: environment\n      value: {environment_id}\n"
            f"    - name: service\n      value: {service_id}\n"
            f"    - name: artifactVersion\n      value: {artifact_version}\n"
        )
        return await self._http.request(
            "POST",
            f"{self._pipeline}/pipeline/execute/{pipeline_id}",
            token=token,
            json_body={"runtimeInputYaml": inputs_yaml},
        )

    async def initiate_rollback(
        self, token: str, *, environment_id: str, service_id: str, target_execution_id: str | None = None
    ) -> dict[str, Any]:
        return await self._http.request(
            "POST",
            f"{self._ng}/deployments/rollback",
            token=token,
            json_body={
                "environmentIdentifier": environment_id,
                "serviceIdentifier": service_id,
                "targetExecutionId": target_execution_id,
            },
        )
