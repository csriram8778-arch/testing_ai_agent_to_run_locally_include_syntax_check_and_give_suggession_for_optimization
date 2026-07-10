"""Entrypoint: `python -m harness_mcp`. Mode is selected via MCP_MODE
(stdio|http), never via a CLI flag, so a container's declared command can't
accidentally start the wrong mode independent of its environment config."""

from __future__ import annotations

import sys

from harness_mcp.settings import get_settings


def cli() -> None:
    settings = get_settings()
    if settings.mcp_mode == "stdio":
        from harness_mcp.server.transport_stdio import run_stdio

        run_stdio()
    elif settings.mcp_mode == "http":
        from harness_mcp.server.transport_http import run_http

        run_http()
    else:  # pragma: no cover - guarded by Settings Literal
        print(f"Unknown MCP_MODE: {settings.mcp_mode}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli()
