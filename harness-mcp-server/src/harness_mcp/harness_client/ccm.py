"""Cloud Cost Management (CCM) client -- strictly read-only in this server.
No write methods exist in this class at all (not merely gated) since the
spec scopes CCM to "query cost data and anomaly alerts (read-only)".
"""

from __future__ import annotations

from typing import Any

from harness_mcp.harness_client.base import HarnessHTTPClient


class CcmClient:
    def __init__(self, http: HarnessHTTPClient) -> None:
        self._http = http
        self._base = http.paths.ccm

    async def get_cost_summary(
        self, token: str, *, perspective_id: str, start_time: str, end_time: str
    ) -> dict[str, Any]:
        return await self._http.request(
            "POST",
            f"{self._base}/perspective/summary",
            token=token,
            json_body={
                "perspectiveId": perspective_id,
                "startTime": start_time,
                "endTime": end_time,
            },
        )

    async def list_cost_anomalies(
        self, token: str, *, start_time: str | None = None, end_time: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._http.request("GET", f"{self._base}/anomaly/list", token=token, params=params)

    async def get_cost_recommendations(self, token: str, *, limit: int = 25) -> dict[str, Any]:
        return await self._http.request(
            "GET", f"{self._base}/recommendation/list", token=token, params={"limit": limit}
        )
