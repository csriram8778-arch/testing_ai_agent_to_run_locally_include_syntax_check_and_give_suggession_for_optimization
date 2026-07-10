from __future__ import annotations

import pytest

from harness_mcp.guardrails import approval_hook
from harness_mcp.guardrails.approval_hook import ApprovalOutcome, evaluate
from harness_mcp.guardrails.risk import RiskTier, TOOL_RISK


@pytest.fixture(autouse=True)
def _reset_store():
    approval_hook._store.cache_clear()
    yield
    approval_hook._store.cache_clear()


@pytest.mark.asyncio
async def test_read_only_tool_always_allowed():
    result = await evaluate("list_pipelines", {}, user_id="user-1")
    assert result.outcome == ApprovalOutcome.ALLOWED


@pytest.mark.asyncio
async def test_write_tool_first_call_returns_pending_confirmation():
    result = await evaluate("trigger_pipeline", {"pipeline_id": "p1"}, user_id="user-1")
    assert result.outcome == ApprovalOutcome.PENDING_CONFIRMATION
    assert result.confirmation_token


@pytest.mark.asyncio
async def test_write_tool_second_call_with_valid_token_allowed():
    params = {"pipeline_id": "p1"}
    first = await evaluate("trigger_pipeline", params, user_id="user-1")
    second = await evaluate(
        "trigger_pipeline", params, user_id="user-1", confirmation_token=first.confirmation_token
    )
    assert second.outcome == ApprovalOutcome.ALLOWED


@pytest.mark.asyncio
async def test_write_tool_second_call_with_wrong_params_denied():
    first = await evaluate("trigger_pipeline", {"pipeline_id": "p1"}, user_id="user-1")
    second = await evaluate(
        "trigger_pipeline",
        {"pipeline_id": "p2"},
        user_id="user-1",
        confirmation_token=first.confirmation_token,
    )
    assert second.outcome == ApprovalOutcome.DENIED


@pytest.mark.asyncio
async def test_write_tool_bogus_token_denied():
    result = await evaluate(
        "trigger_pipeline", {"pipeline_id": "p1"}, user_id="user-1", confirmation_token="bogus"
    )
    assert result.outcome == ApprovalOutcome.DENIED


@pytest.mark.asyncio
async def test_unclassified_tool_denied_by_default():
    result = await evaluate("nonexistent_tool", {}, user_id="user-1")
    assert result.outcome == ApprovalOutcome.DENIED


@pytest.mark.asyncio
async def test_destructive_excluded_tool_always_denied(monkeypatch):
    monkeypatch.setitem(TOOL_RISK, "delete_pipeline_TEST_ONLY", RiskTier.DESTRUCTIVE_EXCLUDED)
    result = await evaluate("delete_pipeline_TEST_ONLY", {}, user_id="user-1")
    assert result.outcome == ApprovalOutcome.DENIED
    del TOOL_RISK["delete_pipeline_TEST_ONLY"]


@pytest.mark.asyncio
async def test_confirmation_cannot_be_reused_across_users():
    params = {"pipeline_id": "p1"}
    first = await evaluate("trigger_pipeline", params, user_id="user-1")
    second = await evaluate(
        "trigger_pipeline", params, user_id="user-2", confirmation_token=first.confirmation_token
    )
    assert second.outcome == ApprovalOutcome.DENIED
