"""Immutable, append-only audit sink using S3 Object Lock (COMPLIANCE mode).

Each event is written as its own object (one PUT per event, keyed by
timestamp + request id) rather than appended to a shared object, because S3
has no native append -- and because per-object immutability is exactly what
Object Lock protects. The bucket must be created with Object Lock enabled
and a default COMPLIANCE-mode retention policy; this client does not (and
cannot) alter or shorten a retention period once set.
"""

from __future__ import annotations

import json

import boto3
from botocore.exceptions import ClientError

from harness_mcp.audit_logging.event import AuditEvent


class S3ObjectLockAuditSink:
    name = "s3_object_lock"

    def __init__(self, bucket: str, region: str, prefix: str) -> None:
        self._bucket = bucket
        self._prefix = prefix.rstrip("/") + "/"
        self._client = boto3.client("s3", region_name=region)

    def _key(self, event: AuditEvent) -> str:
        date_part = event.timestamp[:10]
        return f"{self._prefix}{date_part}/{event.request_id}-{event.tool_name}.json"

    async def write(self, event: AuditEvent) -> None:
        import asyncio

        body = json.dumps(event.to_json_dict(), sort_keys=True).encode("utf-8")
        key = self._key(event)

        def _put() -> None:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=body,
                ContentType="application/json",
                # Server-side confirmation that Object Lock is engaged for this
                # object; the bucket-level default retention still governs the
                # actual retain-until date.
                ObjectLockLegalHoldStatus="ON",
            )

        await asyncio.get_running_loop().run_in_executor(None, _put)

    async def healthy(self) -> bool:
        import asyncio

        def _check() -> bool:
            try:
                self._client.head_bucket(Bucket=self._bucket)
                return True
            except ClientError:
                return False

        return await asyncio.get_running_loop().run_in_executor(None, _check)
