from __future__ import annotations

import json

import pytest

from harness_mcp.audit_logging.event import AuditEvent
from harness_mcp.audit_logging.middleware import build_event, emit
from harness_mcp.audit_logging.sink_factory import AllAuditSinksFailedError, get_audit_sinks


@pytest.fixture(autouse=True)
def _reset_sinks():
    get_audit_sinks.cache_clear()
    yield
    get_audit_sinks.cache_clear()


def _make_event(**overrides) -> AuditEvent:
    base = dict(
        request_id="req-1",
        user_id="user-1",
        harness_account_id="acct-1",
        tool_name="list_pipelines",
        risk_tier="read_only",
        params={},
        outcome="allowed",
    )
    base.update(overrides)
    return build_event(**base)


@pytest.mark.asyncio
async def test_local_file_sink_receives_event(tmp_path, monkeypatch):
    log_path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("AUDIT_LOCAL_FILE_PATH", str(log_path))
    from harness_mcp.settings import get_settings

    get_settings.cache_clear()

    event = _make_event()
    await emit(event)

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    recorded = json.loads(lines[0])
    assert recorded["tool_name"] == "list_pipelines"
    assert recorded["outcome"] == "allowed"
    assert recorded["user_id"] == "user-1"


@pytest.mark.asyncio
async def test_event_recorded_for_denied_outcome_too(tmp_path, monkeypatch):
    log_path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("AUDIT_LOCAL_FILE_PATH", str(log_path))
    from harness_mcp.settings import get_settings

    get_settings.cache_clear()

    event = _make_event(outcome="denied", error_message=None)
    await emit(event)

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert json.loads(lines[0])["outcome"] == "denied"


@pytest.mark.asyncio
async def test_fail_closed_raises_when_all_sinks_fail(monkeypatch):
    class AlwaysFailsSink:
        name = "always_fails"

        async def write(self, event):
            raise RuntimeError("sink is down")

        async def healthy(self):
            return False

    monkeypatch.setattr(
        "harness_mcp.audit_logging.sink_factory.get_audit_sinks", lambda: [AlwaysFailsSink()]
    )

    with pytest.raises(AllAuditSinksFailedError):
        await emit(_make_event())
