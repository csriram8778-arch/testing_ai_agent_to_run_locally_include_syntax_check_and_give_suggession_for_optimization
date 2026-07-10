"""Server-side storage for pending confirmations in the two-step
propose->confirm pattern (guardrails.approval_hook).

A WRITE-tier tool's first call (confirm=False) computes a hash of the
user + tool + params, stores a short-lived single-use record keyed by a
random token, and returns that token to the caller instead of executing
anything. The second call must supply that token AND the same params --
if either is missing/mismatched/expired/already-used, execution is denied.

Default backend is in-memory, which is correct for stdio mode and a
single-replica HTTP deployment. A multi-replica HTTP deployment (behind a
Service/HPA) MUST set CONFIRMATION_STORE_BACKEND=redis so a confirmation
proposed on one pod can be confirmed on another.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any, Protocol


def params_hash(tool_name: str, user_id: str, params: dict[str, Any]) -> str:
    canonical = json.dumps({"tool": tool_name, "user": user_id, "params": params}, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PendingConfirmation:
    token: str
    params_digest: str
    expires_at: float


class ConfirmationStore(Protocol):
    async def create(self, tool_name: str, user_id: str, params: dict[str, Any], ttl_seconds: int) -> str: ...

    async def consume(self, token: str, tool_name: str, user_id: str, params: dict[str, Any]) -> bool:
        """Atomically validate + invalidate. Returns True iff the token exists,
        is unexpired, unused, and matches this exact tool/user/params."""
        ...


class InMemoryConfirmationStore:
    def __init__(self) -> None:
        self._pending: dict[str, PendingConfirmation] = {}

    async def create(self, tool_name: str, user_id: str, params: dict[str, Any], ttl_seconds: int) -> str:
        self._evict_expired()
        token = secrets.token_urlsafe(32)
        self._pending[token] = PendingConfirmation(
            token=token,
            params_digest=params_hash(tool_name, user_id, params),
            expires_at=time.time() + ttl_seconds,
        )
        return token

    async def consume(self, token: str, tool_name: str, user_id: str, params: dict[str, Any]) -> bool:
        record = self._pending.pop(token, None)
        if record is None:
            return False
        if record.expires_at < time.time():
            return False
        return record.params_digest == params_hash(tool_name, user_id, params)

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [t for t, r in self._pending.items() if r.expires_at < now]
        for t in expired:
            self._pending.pop(t, None)


class RedisConfirmationStore:
    """Required for multi-replica HTTP deployments. Lazily imports redis.asyncio
    so it's not a hard dependency for stdio/single-replica installs."""

    def __init__(self, redis_url: str) -> None:
        import redis.asyncio as redis  # type: ignore[import-not-found]

        self._redis = redis.from_url(redis_url)

    def _key(self, token: str) -> str:
        return f"harness-mcp:confirmation:{token}"

    async def create(self, tool_name: str, user_id: str, params: dict[str, Any], ttl_seconds: int) -> str:
        token = secrets.token_urlsafe(32)
        digest = params_hash(tool_name, user_id, params)
        await self._redis.set(self._key(token), digest, ex=ttl_seconds, nx=True)
        return token

    async def consume(self, token: str, tool_name: str, user_id: str, params: dict[str, Any]) -> bool:
        key = self._key(token)
        stored = await self._redis.get(key)
        if stored is None:
            return False
        await self._redis.delete(key)
        expected = params_hash(tool_name, user_id, params)
        stored_str = stored.decode("utf-8") if isinstance(stored, bytes) else stored
        return stored_str == expected


def build_confirmation_store(backend: str, redis_url: str | None) -> ConfirmationStore:
    if backend == "redis":
        if not redis_url:
            raise ValueError("REDIS_URL is required when CONFIRMATION_STORE_BACKEND=redis")
        return RedisConfirmationStore(redis_url)
    return InMemoryConfirmationStore()
