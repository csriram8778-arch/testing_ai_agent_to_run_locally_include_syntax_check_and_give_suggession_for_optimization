"""Grounding-context client for Claude's own code generation / review /
documentation. These are read-only calls that fetch real pipeline and repo
state so Claude isn't guessing -- there is no separate LLM call here."""

from __future__ import annotations

from typing import Any

from harness_mcp.harness_client.base import HarnessHTTPClient


class ContextClient:
    def __init__(self, http: HarnessHTTPClient) -> None:
        self._http = http
        self._ng = http.paths.ng

    async def get_repo_info(self, token: str, connector_id: str, repo_name: str) -> dict[str, Any]:
        return await self._http.request(
            "GET",
            f"{self._ng}/connectors/{connector_id}/repos/{repo_name}",
            token=token,
        )
