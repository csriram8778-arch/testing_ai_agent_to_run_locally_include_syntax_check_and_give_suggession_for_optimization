"""Opportunistic use of MCP's `elicitation/create` capability for a nicer
confirm UX, layered on top of the two-step propose/confirm state machine in
approval_hook.py (which remains the source of truth and the portable
default -- elicitation support varies by client, and this module degrades
silently to "not available" rather than failing a call).
"""

from __future__ import annotations

from typing import Any


class ElicitationUnavailable(Exception):
    """Raised (and caught by approval_hook) when the connected client does not
    support elicitation or the call otherwise fails -- callers must fall back
    to the two-step propose/confirm tool pattern."""


async def try_elicit_confirmation(ctx: Any, *, tool_name: str, summary: str) -> bool | None:
    """Attempt to ask the human, via the MCP client, to confirm this action.

    Returns True/False if the client answered, or None if elicitation is not
    supported/available -- callers must treat None as "use the fallback
    two-step confirm pattern", never as an implicit yes.
    """

    elicit = getattr(ctx, "elicit", None)
    if elicit is None:
        return None

    schema = {
        "type": "object",
        "properties": {
            "confirm": {
                "type": "boolean",
                "description": f"Confirm: {summary}",
            }
        },
        "required": ["confirm"],
    }

    try:
        result = await elicit(
            message=f"Harness MCP server requests confirmation for '{tool_name}': {summary}",
            requestedSchema=schema,
        )
    except Exception:
        return None

    action = getattr(result, "action", None)
    if action != "accept":
        return False

    content = getattr(result, "content", None) or {}
    return bool(content.get("confirm", False))
