"""Chaos Engineering client: view + trigger experiments.

Harness Chaos has historically leaned on a GraphQL API internally for some
operations; this client presents a plain REST-shaped interface and isolates
that detail here so tool code doesn't need to know. Verify the exact
transport (REST vs GraphQL passthrough) against your account before
production use.
"""

from __future__ import annotations

from typing import Any

from harness_mcp.harness_client.base import HarnessHTTPClient


class ChaosClient:
    def __init__(self, http: HarnessHTTPClient) -> None:
        self._http = http
        self._base = http.paths.chaos

    async def list_experiments(self, token: str, *, project_id: str | None = None) -> dict[str, Any]:
        params = {"projectIdentifier": project_id} if project_id else {}
        return await self._http.request("GET", f"{self._base}/experiments", token=token, params=params)

    async def get_experiment(self, token: str, experiment_id: str) -> dict[str, Any]:
        return await self._http.request(
            "GET", f"{self._base}/experiments/{experiment_id}", token=token
        )

    async def run_experiment(self, token: str, experiment_id: str) -> dict[str, Any]:
        """Callers must have already passed the approval-hook confirmation gate
        (RiskTier.WRITE) before this is ever invoked -- see guardrails.approval_hook."""
        return await self._http.request(
            "POST", f"{self._base}/experiments/{experiment_id}/run", token=token
        )
