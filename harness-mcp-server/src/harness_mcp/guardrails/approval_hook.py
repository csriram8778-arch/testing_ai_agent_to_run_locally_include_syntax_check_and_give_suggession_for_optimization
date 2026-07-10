"""The pre-execution approval hook: every tool call passes through
`evaluate()` before it is allowed to reach the Harness API.

`HARNESS_AUTO_APPROVE_RISK=none` is enforced structurally: `Settings`
rejects any other value at process startup (settings.py), and this function
takes no override parameter of any kind -- no tool argument, prompt text, or
client-supplied field can change the outcome for a WRITE-tier tool. A WRITE
call always either (a) returns PENDING_CONFIRMATION and executes nothing, or
(b) is allowed because a valid, single-use, params-matching confirmation was
supplied. There is no third path.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Any

from harness_mcp.guardrails.confirmation_store import ConfirmationStore, build_confirmation_store
from harness_mcp.guardrails.elicitation import try_elicit_confirmation
from harness_mcp.guardrails.risk import RiskTier, TOOL_RISK
from harness_mcp.observability.metrics import APPROVAL_DENIALS_TOTAL
from harness_mcp.settings import Settings, get_settings


class ApprovalOutcome(str, Enum):
    ALLOWED = "allowed"
    PENDING_CONFIRMATION = "pending_confirmation"
    DENIED = "denied"


@dataclass(frozen=True, slots=True)
class ApprovalResult:
    outcome: ApprovalOutcome
    confirmation_token: str | None = None
    message: str | None = None

    @property
    def allowed(self) -> bool:
        return self.outcome == ApprovalOutcome.ALLOWED


@lru_cache(maxsize=1)
def _store() -> ConfirmationStore:
    settings = get_settings()
    return build_confirmation_store(settings.confirmation_store_backend, settings.redis_url)


async def evaluate(
    tool_name: str,
    params: dict[str, Any],
    *,
    user_id: str,
    ctx: Any = None,
    confirmation_token: str | None = None,
    summary: str | None = None,
) -> ApprovalResult:
    settings: Settings = get_settings()
    # Belt-and-suspenders re-assertion of the hard constraint already
    # enforced by Settings validation at process startup.
    if settings.harness_auto_approve_risk != "none":  # pragma: no cover - unreachable
        raise RuntimeError("HARNESS_AUTO_APPROVE_RISK must be 'none'; refusing to evaluate")

    tier = TOOL_RISK.get(tool_name)
    if tier is None:
        APPROVAL_DENIALS_TOTAL.labels(tool=tool_name, reason="unclassified").inc()
        return ApprovalResult(
            ApprovalOutcome.DENIED,
            message=f"Tool '{tool_name}' has no risk classification; denying by default.",
        )

    if tier == RiskTier.DESTRUCTIVE_EXCLUDED:
        APPROVAL_DENIALS_TOTAL.labels(tool=tool_name, reason="destructive_excluded").inc()
        return ApprovalResult(
            ApprovalOutcome.DENIED, message="This action is permanently excluded from this server."
        )

    if tier == RiskTier.READ_ONLY:
        return ApprovalResult(ApprovalOutcome.ALLOWED)

    # -- RiskTier.WRITE: human confirmation is mandatory ---------------------
    store = _store()

    if confirmation_token:
        ok = await store.consume(confirmation_token, tool_name, user_id, params)
        if ok:
            return ApprovalResult(ApprovalOutcome.ALLOWED)
        APPROVAL_DENIALS_TOTAL.labels(tool=tool_name, reason="invalid_confirmation").inc()
        return ApprovalResult(
            ApprovalOutcome.DENIED,
            message=(
                "Confirmation token is invalid, expired, already used, or the "
                "parameters changed since it was issued. Start over."
            ),
        )

    if ctx is not None:
        elicited = await try_elicit_confirmation(
            ctx, tool_name=tool_name, summary=summary or f"execute {tool_name}"
        )
        if elicited is True:
            return ApprovalResult(ApprovalOutcome.ALLOWED)
        if elicited is False:
            APPROVAL_DENIALS_TOTAL.labels(tool=tool_name, reason="user_declined").inc()
            return ApprovalResult(ApprovalOutcome.DENIED, message="Confirmation declined by user.")
        # elicited is None -> client doesn't support elicitation, fall through

    token = await store.create(tool_name, user_id, params, settings.confirmation_ttl_seconds)
    APPROVAL_DENIALS_TOTAL.labels(tool=tool_name, reason="pending_confirmation").inc()
    return ApprovalResult(
        ApprovalOutcome.PENDING_CONFIRMATION,
        confirmation_token=token,
        message=(
            f"This is a write action and requires explicit human approval. "
            f"Call this tool again with confirm=true and confirmation_token="
            f"'{token}' (identical parameters) within "
            f"{settings.confirmation_ttl_seconds}s to proceed."
        ),
    )
