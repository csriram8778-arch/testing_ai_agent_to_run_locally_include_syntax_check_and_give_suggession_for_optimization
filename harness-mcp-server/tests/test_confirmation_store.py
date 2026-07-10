from __future__ import annotations

import pytest

from harness_mcp.guardrails.confirmation_store import InMemoryConfirmationStore


@pytest.mark.asyncio
async def test_create_then_consume_matching_params_succeeds():
    store = InMemoryConfirmationStore()
    params = {"pipeline_id": "p1"}
    token = await store.create("trigger_pipeline", "user-1", params, ttl_seconds=60)
    assert await store.consume(token, "trigger_pipeline", "user-1", params) is True


@pytest.mark.asyncio
async def test_token_is_single_use():
    store = InMemoryConfirmationStore()
    params = {"pipeline_id": "p1"}
    token = await store.create("trigger_pipeline", "user-1", params, ttl_seconds=60)
    assert await store.consume(token, "trigger_pipeline", "user-1", params) is True
    assert await store.consume(token, "trigger_pipeline", "user-1", params) is False


@pytest.mark.asyncio
async def test_mismatched_params_rejected():
    store = InMemoryConfirmationStore()
    token = await store.create("trigger_pipeline", "user-1", {"pipeline_id": "p1"}, ttl_seconds=60)
    assert await store.consume(token, "trigger_pipeline", "user-1", {"pipeline_id": "p2"}) is False


@pytest.mark.asyncio
async def test_different_user_cannot_consume_another_users_token():
    store = InMemoryConfirmationStore()
    params = {"pipeline_id": "p1"}
    token = await store.create("trigger_pipeline", "user-1", params, ttl_seconds=60)
    assert await store.consume(token, "trigger_pipeline", "user-2", params) is False


@pytest.mark.asyncio
async def test_expired_token_rejected():
    store = InMemoryConfirmationStore()
    params = {"pipeline_id": "p1"}
    token = await store.create("trigger_pipeline", "user-1", params, ttl_seconds=-1)
    assert await store.consume(token, "trigger_pipeline", "user-1", params) is False


@pytest.mark.asyncio
async def test_unknown_token_rejected():
    store = InMemoryConfirmationStore()
    assert await store.consume("not-a-real-token", "trigger_pipeline", "user-1", {}) is False
