"""The single choke point every tool must be registered through.

`register_tool` composes, in fixed order, for every call:

    resolve SessionPrincipal -> approval_hook.evaluate() -> handler ->
    redaction.sanitizer.apply_redaction() -> audit_logging emit (finally)

No tool module calls `harness_client` directly from an `@mcp.tool()`
decorator -- every tool function is defined plainly (see `tools/cicd_tools.py`
etc. for the pattern) and registered here, which is the *only* exported way
to turn a plain async function into something `server/app.py` hands to
FastMCP. `assert_all_registered_are_wrapped` lets `server/app.py` fail
startup instead of silently serving an unwrapped tool.

Every registered tool transparently gains three extra keyword-only
parameters on top of its own declared parameters: `confirm` (unused
placeholder for client UX -- the actual gate is `confirmation_token`),
`confirmation_token` (required on the second call of a WRITE-tier tool's
propose->confirm flow), and `reasoning` (best-effort free text the client may
attach describing why it's calling this tool; flows into the audit event).
"""

from __future__ import annotations

import inspect
import time
from typing import Any, Awaitable, Callable, TypeVar

from harness_mcp.audit_logging.middleware import build_event, emit, emit_preflight
from harness_mcp.guardrails.approval_hook import ApprovalOutcome, evaluate
from harness_mcp.guardrails.risk import RiskTier, TOOL_RISK
from harness_mcp.observability.logging_config import get_logger
from harness_mcp.observability.metrics import TOOL_CALL_DURATION_SECONDS
from harness_mcp.redaction.sanitizer import apply_redaction
from harness_mcp.server.session_context import get_current_session

logger = get_logger(__name__)

_HANDLER = TypeVar("_HANDLER", bound=Callable[..., Awaitable[Any]])

_REGISTERED: dict[str, Callable[..., Awaitable[Any]]] = {}

_GUARDRAIL_PARAM_NAMES = ("confirm", "confirmation_token", "reasoning")


def registered_tools() -> dict[str, Callable[..., Awaitable[Any]]]:
    return dict(_REGISTERED)


def register_tool(name: str, *, description: str) -> Callable[[_HANDLER], _HANDLER]:
    if name not in TOOL_RISK:
        raise RuntimeError(
            f"Tool '{name}' is missing from guardrails.risk.TOOL_RISK; refusing to "
            "register an unclassified tool. Add it to TOOL_RISK first."
        )
    tier = TOOL_RISK[name]
    if tier == RiskTier.DESTRUCTIVE_EXCLUDED:
        raise RuntimeError(
            f"Tool '{name}' is classified DESTRUCTIVE_EXCLUDED and must never be "
            "registered as a callable tool."
        )

    def decorator(handler: _HANDLER) -> _HANDLER:
        original_sig = inspect.signature(handler)
        for reserved in _GUARDRAIL_PARAM_NAMES:
            if reserved in original_sig.parameters:
                raise RuntimeError(
                    f"Tool handler '{name}' declares reserved parameter name "
                    f"'{reserved}', which is injected by the guardrail wrapper."
                )

        handler_params = [
            p for pname, p in original_sig.parameters.items() if pname != "session"
        ]
        guardrail_params = [
            inspect.Parameter(
                "confirm", kind=inspect.Parameter.KEYWORD_ONLY, default=False, annotation=bool
            ),
            inspect.Parameter(
                "confirmation_token",
                kind=inspect.Parameter.KEYWORD_ONLY,
                default=None,
                annotation=str | None,
            ),
            inspect.Parameter(
                "reasoning", kind=inspect.Parameter.KEYWORD_ONLY, default=None, annotation=str | None
            ),
        ]

        async def wrapped(**kwargs: Any) -> Any:
            kwargs.pop("confirm", False)
            confirmation_token = kwargs.pop("confirmation_token", None)
            reasoning = kwargs.pop("reasoning", None)
            ctx = kwargs.get("ctx")
            params = {k: v for k, v in kwargs.items() if k != "ctx"}

            session = get_current_session()
            start = time.monotonic()
            outcome = "error"
            error_message: str | None = None
            redaction_kinds: list[str] = []

            try:
                if tier == RiskTier.WRITE:
                    await emit_preflight(
                        request_id=session.request_id,
                        user_id=session.user_id,
                        harness_account_id=session.harness_account_id,
                        tool_name=name,
                        risk_tier=tier.value,
                        params=params,
                        reasoning_context=reasoning,
                    )

                approval = await evaluate(
                    name,
                    params,
                    user_id=session.user_id,
                    ctx=ctx,
                    confirmation_token=confirmation_token,
                    summary=description,
                )

                if approval.outcome == ApprovalOutcome.DENIED:
                    outcome = "denied"
                    return {"status": "denied", "message": approval.message}

                if approval.outcome == ApprovalOutcome.PENDING_CONFIRMATION:
                    outcome = "pending_confirmation"
                    return {
                        "status": "pending_confirmation",
                        "confirmation_token": approval.confirmation_token,
                        "message": approval.message,
                    }

                call_kwargs = dict(kwargs)
                if "session" in original_sig.parameters:
                    call_kwargs["session"] = session
                raw_result = await handler(**call_kwargs)
                sanitized, redaction_kinds = apply_redaction(name, raw_result)
                outcome = "allowed"
                return sanitized
            except Exception as exc:
                error_message = str(exc)
                outcome = "error"
                raise
            finally:
                TOOL_CALL_DURATION_SECONDS.labels(tool=name).observe(time.monotonic() - start)
                await emit(
                    build_event(
                        request_id=session.request_id,
                        user_id=session.user_id,
                        harness_account_id=session.harness_account_id,
                        tool_name=name,
                        risk_tier=tier.value,
                        params=params,
                        outcome=outcome,  # type: ignore[arg-type]
                        error_message=error_message,
                        reasoning_context=reasoning,
                        redaction_kinds=redaction_kinds,
                    )
                )

        wrapped.__name__ = handler.__name__
        wrapped.__doc__ = description
        merged_params = handler_params + guardrail_params
        wrapped.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
            parameters=merged_params, return_annotation=original_sig.return_annotation
        )
        setattr(wrapped, "__harness_mcp_guardrail_wrapped__", True)
        setattr(wrapped, "__harness_mcp_tool_name__", name)
        setattr(wrapped, "__harness_mcp_risk_tier__", tier)

        if name in _REGISTERED:
            raise RuntimeError(f"Tool '{name}' is already registered")
        _REGISTERED[name] = wrapped
        return wrapped  # type: ignore[return-value]

    return decorator


def assert_registry_complete() -> None:
    """Startup check: every non-excluded tool in TOOL_RISK has actually been
    registered (a module failing to import silently would otherwise just
    mean a missing tool, not a caught error)."""
    expected = {n for n, tier in TOOL_RISK.items() if tier != RiskTier.DESTRUCTIVE_EXCLUDED}
    missing = expected - set(_REGISTERED.keys())
    if missing:
        raise RuntimeError(f"Tools classified in TOOL_RISK but never registered: {sorted(missing)}")
