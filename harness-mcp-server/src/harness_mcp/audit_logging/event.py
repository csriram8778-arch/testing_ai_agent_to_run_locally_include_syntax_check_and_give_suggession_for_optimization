"""Structured JSON audit event schema. Every field the spec requires --
timestamp, user identity, tool name, input parameters, and outcome -- plus
request correlation and (best-effort) the reasoning context the client
supplied alongside the call.

`reasoning_context` is populated from an MCP request's `_meta` field if the
client sends one. This is NOT a standardized MCP field as of the current
spec, so its presence/shape varies by client -- treat it as best-effort, not
a guarantee that Claude's reasoning is always captured.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Outcome = Literal["allowed", "denied", "pending_confirmation", "error"]


@dataclass(frozen=True, slots=True)
class AuditEvent:
    timestamp: str
    request_id: str
    user_id: str
    harness_account_id: str
    tool_name: str
    risk_tier: str
    params: dict[str, Any]
    outcome: Outcome
    error_message: str | None = None
    reasoning_context: str | None = None
    redaction_kinds: list[str] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)
