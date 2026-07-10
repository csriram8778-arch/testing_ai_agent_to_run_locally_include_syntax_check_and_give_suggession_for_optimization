"""Validates a caller-supplied Harness token by calling Harness's own identity
endpoint -- this server never mints, stores, or trusts a token without
checking liveness against Harness itself.

Results are cached briefly, keyed by a SHA-256 hash of the token (never the
raw token), to avoid hammering the identity endpoint on every tool call
within the same short-lived MCP session.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

import httpx

from harness_mcp.settings import Settings

_CACHE_TTL_SECONDS = 30


@dataclass(frozen=True, slots=True)
class Identity:
    user_id: str
    harness_account_id: str
    expires_at: float | None


class TokenValidationError(Exception):
    pass


class TokenValidator:
    """Calls Harness's user-info/token-introspection endpoint to resolve identity.

    NOTE: the exact introspection path (``/ng/api/user/currentUser`` below is
    the well-known NG "who am I" endpoint) should be verified against the
    team's Harness edition/OpenAPI docs -- see harness_client/endpoints.py.
    """

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http = http_client
        self._cache: dict[str, tuple[float, Identity]] = {}

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def validate(self, token: str) -> Identity:
        if not token or not token.strip():
            raise TokenValidationError("empty token")

        key = self._hash(token)
        cached = self._cache.get(key)
        now = time.monotonic()
        if cached and cached[0] > now:
            return cached[1]

        try:
            resp = await self._http.get(
                f"{self._settings.harness_base_url}ng/api/user/currentUser",
                params={"accountIdentifier": self._settings.harness_account_id},
                headers={"x-api-key": token},
                timeout=10.0,
            )
        except httpx.HTTPError as exc:
            raise TokenValidationError(f"could not reach Harness identity endpoint: {exc}") from exc

        if resp.status_code == 401 or resp.status_code == 403:
            raise TokenValidationError("Harness rejected this token (401/403)")
        if resp.status_code >= 400:
            raise TokenValidationError(
                f"unexpected response validating token: HTTP {resp.status_code}"
            )

        body = resp.json()
        data = body.get("data") or body
        user_id = data.get("uuid") or data.get("email") or data.get("name")
        if not user_id:
            raise TokenValidationError("Harness identity response missing a user identifier")

        identity = Identity(
            user_id=str(user_id),
            harness_account_id=self._settings.harness_account_id,
            expires_at=None,
        )
        self._cache[key] = (now + _CACHE_TTL_SECONDS, identity)
        return identity
