from __future__ import annotations

import pytest

from harness_mcp.guardrails import approval_hook
from harness_mcp.guardrails.risk import RiskTier, TOOL_RISK
from harness_mcp.server.session_context import (
    SessionPrincipal,
    new_request_id,
    reset_current_session,
    set_current_session,
)
from harness_mcp.tools import registry


@pytest.fixture(autouse=True)
def _reset_state():
    approval_hook._store.cache_clear()
    yield
    approval_hook._store.cache_clear()


@pytest.fixture()
def session_ctx():
    principal = SessionPrincipal(
        user_id="user-1",
        harness_account_id="acct-1",
        harness_token="fake-token",
        token_expires_at=None,
        request_id=new_request_id(),
    )
    token = set_current_session(principal)
    yield principal
    reset_current_session(token)


def test_register_tool_rejects_unclassified_name():
    with pytest.raises(RuntimeError):

        @registry.register_tool("__not_in_risk_table__", description="x")
        async def _handler(session):  # pragma: no cover
            return {}


def test_register_tool_rejects_destructive_tier(monkeypatch):
    monkeypatch.setitem(TOOL_RISK, "__destructive_probe__", RiskTier.DESTRUCTIVE_EXCLUDED)
    with pytest.raises(RuntimeError):

        @registry.register_tool("__destructive_probe__", description="x")
        async def _handler(session):  # pragma: no cover
            return {}
    del TOOL_RISK["__destructive_probe__"]


@pytest.mark.asyncio
async def test_read_only_tool_end_to_end(monkeypatch, tmp_path, session_ctx):
    monkeypatch.setenv("AUDIT_LOCAL_FILE_PATH", str(tmp_path / "audit.jsonl"))
    from harness_mcp.settings import get_settings
    from harness_mcp.audit_logging.sink_factory import get_audit_sinks

    get_settings.cache_clear()
    get_audit_sinks.cache_clear()

    monkeypatch.setitem(TOOL_RISK, "__read_probe__", RiskTier.READ_ONLY)

    @registry.register_tool("__read_probe__", description="probe")
    async def _handler(session, value: int) -> dict:
        assert session.user_id == "user-1"
        return {"identifier": "ok", "name": str(value)}

    result = await _handler(value=42)
    assert result["identifier"] == "ok"

    del TOOL_RISK["__read_probe__"]
    del registry._REGISTERED["__read_probe__"]


@pytest.mark.asyncio
async def test_write_tool_end_to_end_requires_confirmation(monkeypatch, tmp_path, session_ctx):
    monkeypatch.setenv("AUDIT_LOCAL_FILE_PATH", str(tmp_path / "audit.jsonl"))
    from harness_mcp.settings import get_settings
    from harness_mcp.audit_logging.sink_factory import get_audit_sinks

    get_settings.cache_clear()
    get_audit_sinks.cache_clear()

    monkeypatch.setitem(TOOL_RISK, "__write_probe__", RiskTier.WRITE)

    calls = []

    @registry.register_tool("__write_probe__", description="probe")
    async def _handler(session, value: int) -> dict:
        calls.append(value)
        return {"identifier": "done"}

    first = await _handler(value=7)
    assert first["status"] == "pending_confirmation"
    assert calls == []  # handler must NOT have executed yet

    second = await _handler(value=7, confirmation_token=first["confirmation_token"])
    assert second["identifier"] == "done"
    assert calls == [7]

    del TOOL_RISK["__write_probe__"]
    del registry._REGISTERED["__write_probe__"]
