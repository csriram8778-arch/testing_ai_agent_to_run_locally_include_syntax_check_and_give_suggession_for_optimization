"""Feature Flags (module `cf`) client: list, evaluate, update with rollout controls."""

from __future__ import annotations

from typing import Any

from harness_mcp.harness_client.base import HarnessHTTPClient


class FeatureFlagClient:
    def __init__(self, http: HarnessHTTPClient) -> None:
        self._http = http
        self._base = http.paths.feature_flags

    async def list_flags(self, token: str, *, environment_id: str | None = None) -> dict[str, Any]:
        params = {"environmentIdentifier": environment_id} if environment_id else {}
        return await self._http.request("GET", f"{self._base}/features", token=token, params=params)

    async def get_flag(self, token: str, identifier: str) -> dict[str, Any]:
        return await self._http.request("GET", f"{self._base}/features/{identifier}", token=token)

    async def evaluate_flag(
        self, token: str, identifier: str, *, environment_id: str, target_id: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"environmentIdentifier": environment_id}
        if target_id:
            params["target"] = target_id
        return await self._http.request(
            "GET", f"{self._base}/features/{identifier}/evaluate", token=token, params=params
        )

    async def update_flag_state(
        self,
        token: str,
        identifier: str,
        *,
        environment_id: str,
        enabled: bool,
        rollout_percentage: int | None = None,
    ) -> dict[str, Any]:
        patch_instructions: list[dict[str, Any]] = [
            {"kind": "setFeatureFlagState", "parameters": {"state": "on" if enabled else "off"}}
        ]
        if rollout_percentage is not None:
            patch_instructions.append(
                {
                    "kind": "setDefaultServeRule",
                    "parameters": {"distribution": {"percentageRollout": rollout_percentage}},
                }
            )
        return await self._http.request(
            "PATCH",
            f"{self._base}/features/{identifier}",
            token=token,
            params={"environmentIdentifier": environment_id},
            json_body={"instructions": patch_instructions},
        )
