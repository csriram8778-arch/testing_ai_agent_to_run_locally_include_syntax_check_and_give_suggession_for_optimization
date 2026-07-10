"""Harness-side audit trail client -- read-only, distinct from this server's
own compliance audit log in `audit_logging/` (which records MCP tool calls,
not Harness platform actions)."""

from __future__ import annotations

from typing import Any

from harness_mcp.harness_client.base import HarnessHTTPClient


class HarnessAuditClient:
    def __init__(self, http: HarnessHTTPClient) -> None:
        self._http = http
        self._base = http.paths.audit

    async def query_audit_trail(
        self,
        token: str,
        *,
        start_time: str | None = None,
        end_time: str | None = None,
        actions: list[str] | None = None,
        page: int = 0,
        size: int = 25,
    ) -> dict[str, Any]:
        filter_body: dict[str, Any] = {}
        if start_time:
            filter_body["startTime"] = start_time
        if end_time:
            filter_body["endTime"] = end_time
        if actions:
            filter_body["actions"] = actions
        return await self._http.request(
            "POST",
            f"{self._base}/audits/list",
            token=token,
            params={"page": page, "size": size},
            json_body=filter_body,
        )
