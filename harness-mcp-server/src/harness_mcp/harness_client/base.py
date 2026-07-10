"""Shared async HTTP client for all Harness NG API modules.

- TLS is enforced (Settings validates HARNESS_BASE_URL is https:// at
  startup; this client also refuses to send a request to a non-https URL as
  a second check).
- Every call takes an explicit `token` argument sourced from
  `session_context.get_current_session()` by the caller -- there is no
  module-level or cached credential here, which structurally prevents one
  user's token from ever being used for another user's request.
- Every call is checked against `guardrails.deny_list` before being sent.
"""

from __future__ import annotations

from typing import Any

import httpx

from harness_mcp.guardrails.deny_list import check_allowed
from harness_mcp.harness_client.endpoints import get_module_paths
from harness_mcp.harness_client.errors import (
    HarnessAPIError,
    HarnessAuthError,
    HarnessNotFoundError,
)
from harness_mcp.settings import Settings


class HarnessHTTPClient:
    def __init__(self, settings: Settings, *, timeout: float = 30.0) -> None:
        base_url = str(settings.harness_base_url)
        if not base_url.startswith("https://"):
            raise ValueError("Harness base URL must be HTTPS")
        self._settings = settings
        self._base_url = base_url.rstrip("/") + "/"
        self._paths = get_module_paths(settings.harness_edition)
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=timeout)

    @property
    def paths(self):
        return self._paths

    async def ping(self) -> bool:
        try:
            resp = await self._client.get("ng/api/health", timeout=5.0)
            return resp.status_code < 500
        except httpx.HTTPError:
            return False

    def _scope_params(self) -> dict[str, str]:
        params = {"accountIdentifier": self._settings.harness_account_id}
        if self._settings.harness_org_id:
            params["orgIdentifier"] = self._settings.harness_org_id
        if self._settings.harness_project_id:
            params["projectIdentifier"] = self._settings.harness_project_id
        return params

    async def request(
        self,
        method: str,
        path: str,
        *,
        token: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        include_scope: bool = True,
    ) -> dict[str, Any]:
        check_allowed(method, path)

        merged_params = {**self._scope_params(), **(params or {})} if include_scope else (params or {})
        resp = await self._client.request(
            method,
            path,
            params=merged_params,
            json=json_body,
            headers={"x-api-key": token, "Content-Type": "application/json"},
        )

        if resp.status_code in (401, 403):
            raise HarnessAuthError(
                f"Harness rejected this request ({resp.status_code})", status_code=resp.status_code
            )
        if resp.status_code == 404:
            raise HarnessNotFoundError("resource not found", status_code=404)
        if resp.status_code >= 400:
            raise HarnessAPIError(
                f"Harness API error {resp.status_code}: {resp.text[:500]}",
                status_code=resp.status_code,
            )

        if not resp.content:
            return {}
        return resp.json()

    async def aclose(self) -> None:
        await self._client.aclose()
