"""Always-active crash-safety-net sink: append-only JSONL on local disk.

In the reference Kubernetes deployment this path lives on a small scoped
emptyDir (the container root filesystem is read-only) and is expected to be
shipped off-box by a log-forwarder sidecar/daemonset in addition to whichever
of the S3-Object-Lock / webhook sinks are configured as the durable,
immutable record.
"""

from __future__ import annotations

import asyncio
import json
import os

from harness_mcp.audit_logging.event import AuditEvent


class LocalFileAuditSink:
    name = "local_file"

    def __init__(self, path: str) -> None:
        self._path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._lock = asyncio.Lock()

    async def write(self, event: AuditEvent) -> None:
        line = json.dumps(event.to_json_dict(), sort_keys=True) + "\n"
        async with self._lock:
            # Append-only open mode; never truncates, never rewrites prior lines.
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(line)

    async def healthy(self) -> bool:
        try:
            os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
            return os.access(os.path.dirname(self._path) or ".", os.W_OK)
        except OSError:
            return False
