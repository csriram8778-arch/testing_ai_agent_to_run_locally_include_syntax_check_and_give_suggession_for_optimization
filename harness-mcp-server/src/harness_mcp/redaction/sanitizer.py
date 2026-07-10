"""Applies allowlist projection (primary) then regex scrubbing (defense in
depth) to every tool's response before it can reach the MCP client / Claude's
context. This is the only function `tools/registry.py` calls -- individual
tool modules never decide what's safe to return.
"""

from __future__ import annotations

from typing import Any

from harness_mcp.redaction.allowlists import get_allowlist
from harness_mcp.redaction.patterns import scrub_string

_MISSING = object()

# Harness NG's common response envelope. These wrapper keys carry no
# sensitive payload themselves and are always safe to pass through as-is;
# only `data` is subject to allowlist projection.
_ENVELOPE_KEYS = {"status", "metaData", "correlationId"}


def _segment_matches(key: str, segment: str) -> bool:
    return segment == "*" or segment == key


def _project(obj: Any, paths: list[tuple[str, ...]]) -> Any:
    if any(len(p) == 0 for p in paths):
        return obj

    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            remaining = [p[1:] for p in paths if len(p) > 0 and _segment_matches(key, p[0])]
            if not remaining:
                continue
            projected = _project(value, remaining)
            if projected is not _MISSING:
                out[key] = projected
        return out

    if isinstance(obj, list):
        remaining_for_items = [p[1:] for p in paths if len(p) > 0 and p[0] == "*"]
        if not remaining_for_items:
            return _MISSING
        out_list = []
        for item in obj:
            projected = _project(item, remaining_for_items)
            if projected is not _MISSING:
                out_list.append(projected)
        return out_list

    # Scalar reached but the allowlist still expects a deeper path -> nothing
    # to match against, so drop it (fail closed, never fail open).
    return _MISSING


def _apply_allowlist(payload: Any, allowed_paths: set[str]) -> Any:
    if not isinstance(payload, (dict, list)):
        return payload
    paths = [tuple(p.split(".")) for p in allowed_paths]
    result = _project(payload, paths)
    return {} if result is _MISSING else result


def _scrub_recursive(obj: Any, hits: list[str]) -> Any:
    if isinstance(obj, str):
        cleaned, kinds = scrub_string(obj)
        hits.extend(kinds)
        return cleaned
    if isinstance(obj, dict):
        return {k: _scrub_recursive(v, hits) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub_recursive(v, hits) for v in obj]
    return obj


def apply_redaction(tool_name: str, payload: Any) -> tuple[Any, list[str]]:
    """Returns (sanitized_payload, redaction_kinds_hit) for metrics/audit."""

    allowlist = get_allowlist(tool_name)

    if isinstance(payload, dict) and (set(payload.keys()) & _ENVELOPE_KEYS):
        envelope = {k: v for k, v in payload.items() if k in _ENVELOPE_KEYS}
        data = payload.get("data")
        projected_data = _apply_allowlist(data, allowlist) if data is not None else None
        result: Any = {**envelope, "data": projected_data}
    else:
        result = _apply_allowlist(payload, allowlist)

    hits: list[str] = []
    scrubbed = _scrub_recursive(result, hits)
    return scrubbed, hits
