"""Builds and emits the structured audit event for one tool call.

`tools/registry.py` is the only caller: it wraps every tool invocation in a
try/finally that always calls `emit()` on the way out, regardless of
success, denial, or exception -- so no tool, prompt, or Claude-supplied
instruction can suppress an audit event by, say, raising early or returning
before "the logging code".

Known limitation (documented in README "Known limitations" too): because the
Harness API call happens before this function is invoked, `AUDIT_FAIL_CLOSED`
can only fail the *response back to the caller* if every sink is down -- it
cannot retroactively undo a Harness action that already completed. For
WRITE-tier tools, `tools/registry.py` additionally emits a best-effort
"pending" pre-call audit event (see `emit_preflight`) before contacting
Harness, so a gap between "action taken" and "audit recorded" still leaves a
trail showing intent, even in the rare case where the post-call write fails.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

from harness_mcp.audit_logging.event import AuditEvent, Outcome
from harness_mcp.audit_logging.sink_factory import write_audit_event
from harness_mcp.observability.logging_config import get_logger
from harness_mcp.observability.metrics import TOOL_CALLS_TOTAL

logger = get_logger(__name__)


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def build_event(
    *,
    request_id: str,
    user_id: str,
    harness_account_id: str,
    tool_name: str,
    risk_tier: str,
    params: dict[str, Any],
    outcome: Outcome,
    error_message: str | None = None,
    reasoning_context: str | None = None,
    redaction_kinds: list[str] | None = None,
) -> AuditEvent:
    return AuditEvent(
        timestamp=_now_iso(),
        request_id=request_id,
        user_id=user_id,
        harness_account_id=harness_account_id,
        tool_name=tool_name,
        risk_tier=risk_tier,
        params=params,
        outcome=outcome,
        error_message=error_message,
        reasoning_context=reasoning_context,
        redaction_kinds=redaction_kinds or [],
    )


async def emit(event: AuditEvent) -> None:
    TOOL_CALLS_TOTAL.labels(tool=event.tool_name, tier=event.risk_tier, outcome=event.outcome).inc()
    logger.info(
        "audit_event",
        request_id=event.request_id,
        user_id=event.user_id,
        tool=event.tool_name,
        tier=event.risk_tier,
        outcome=event.outcome,
    )
    await write_audit_event(event)


async def emit_preflight(
    *, request_id: str, user_id: str, harness_account_id: str, tool_name: str, risk_tier: str,
    params: dict[str, Any], reasoning_context: str | None,
) -> None:
    """Best-effort record of intent before a WRITE-tier tool calls Harness,
    written outside the main try/finally so its own failure never blocks the
    tool call -- see module docstring for why this exists."""
    try:
        await emit(
            build_event(
                request_id=request_id,
                user_id=user_id,
                harness_account_id=harness_account_id,
                tool_name=tool_name,
                risk_tier=risk_tier,
                params=params,
                outcome="pending_confirmation",
                reasoning_context=reasoning_context,
            )
        )
    except Exception as exc:  # pragma: no cover - best-effort only
        logger.warning("preflight_audit_failed", tool=tool_name, request_id=request_id, error=str(exc))
