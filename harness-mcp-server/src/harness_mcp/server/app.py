"""Builds the FastMCP server instance: imports every tool module (which
registers tools via `tools/registry.py` as an import side effect), attaches
each registered tool and named prompt to FastMCP, and runs the startup
assertions that make guardrail coverage a hard failure rather than a review
convention.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

import harness_mcp.tools as _tools_package  # noqa: F401  (import registers every tool)
from harness_mcp.observability.logging_config import get_logger
from harness_mcp.prompts import ALL_PROMPTS
from harness_mcp.tools.registry import assert_registry_complete, registered_tools

logger = get_logger(__name__)


def build_mcp_server() -> FastMCP:
    mcp = FastMCP(
        name="harness-mcp-server",
        instructions=(
            "Self-hosted bridge between Claude and the Harness platform. Every "
            "write/deploy/destructive action requires explicit human confirmation "
            "via a two-step confirm flow -- never assume approval from earlier "
            "context. Read-only tools are always safe to call. See the /deploy, "
            "/rollback, /triage, /review-pr, /document, /cost-check, and "
            "/chaos-run prompts for the team's standard workflows."
        ),
    )

    assert_registry_complete()

    for name, fn in registered_tools().items():
        mcp.add_tool(fn, name=name, description=fn.__doc__ or "")
        logger.info("tool_registered", tool=name)

    for name, prompt_fn in ALL_PROMPTS.items():
        mcp.prompt(name=name)(prompt_fn)
        logger.info("prompt_registered", prompt=name)

    _assert_no_unwrapped_tools(mcp)
    return mcp


def _assert_no_unwrapped_tools(mcp: FastMCP) -> None:
    """Startup guard: every tool FastMCP knows about must carry the
    guardrail-wrapped marker set by `tools.registry.register_tool`. This
    catches a future bug where a tool gets attached to `mcp` some other way,
    bypassing approval/audit/redaction."""

    tool_manager = getattr(mcp, "_tool_manager", None)
    if tool_manager is None:  # pragma: no cover - SDK internals shifted
        logger.warning("tool_manager_introspection_unavailable")
        return

    tools = getattr(tool_manager, "_tools", None) or getattr(tool_manager, "tools", {})
    for tool_name, tool in (tools.items() if hasattr(tools, "items") else []):
        fn = getattr(tool, "fn", None)
        if fn is not None and not getattr(fn, "__harness_mcp_guardrail_wrapped__", False):
            raise RuntimeError(
                f"Tool '{tool_name}' is registered with FastMCP but was not wrapped "
                "by tools.registry.register_tool -- refusing to start."
            )
