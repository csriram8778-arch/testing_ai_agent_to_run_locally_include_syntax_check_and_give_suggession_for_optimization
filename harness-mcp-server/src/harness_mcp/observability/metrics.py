"""Prometheus metrics for the tool-call pipeline."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

TOOL_CALLS_TOTAL = Counter(
    "tool_calls_total",
    "MCP tool invocations",
    labelnames=("tool", "tier", "outcome"),
)

APPROVAL_DENIALS_TOTAL = Counter(
    "approval_denials_total",
    "Tool calls denied or requiring confirmation by the approval hook",
    labelnames=("tool", "reason"),
)

REDACTION_HITS_TOTAL = Counter(
    "redaction_hits_total",
    "Fields/values redacted from tool output before returning to the client",
    labelnames=("tool", "kind"),
)

AUDIT_SINK_FAILURES_TOTAL = Counter(
    "audit_sink_failures_total",
    "Failures writing an audit event to a given sink",
    labelnames=("sink",),
)

TOOL_CALL_DURATION_SECONDS = Histogram(
    "tool_call_duration_seconds",
    "Wall-clock duration of a tool call including guardrail overhead",
    labelnames=("tool",),
)
