from __future__ import annotations

from typing import Protocol

from harness_mcp.audit_logging.event import AuditEvent


class AuditSink(Protocol):
    name: str

    async def write(self, event: AuditEvent) -> None:
        """Persist one event. Must raise on failure -- never swallow errors,
        so sink_factory can decide whether to fail-closed."""
        ...

    async def healthy(self) -> bool:
        ...
