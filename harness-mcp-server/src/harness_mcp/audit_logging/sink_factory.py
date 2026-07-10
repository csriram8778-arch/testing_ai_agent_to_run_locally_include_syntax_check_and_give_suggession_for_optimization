"""Builds and fans out to every configured audit sink.

The local append-only file sink is always active as a crash-safety net. S3
Object Lock and/or a webhook/SIEM sink are added on top when configured.
`write_audit_event` writes to all sinks concurrently; if `AUDIT_FAIL_CLOSED`
(default true) and *every* sink failed, it raises -- the caller
(`audit_logging.middleware`) treats that as reason to fail the tool call
rather than let an unaudited action proceed silently.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache

from harness_mcp.audit_logging.event import AuditEvent
from harness_mcp.audit_logging.sinks.base import AuditSink
from harness_mcp.audit_logging.sinks.local_file_sink import LocalFileAuditSink
from harness_mcp.observability.logging_config import get_logger
from harness_mcp.observability.metrics import AUDIT_SINK_FAILURES_TOTAL
from harness_mcp.settings import Settings, get_settings

logger = get_logger(__name__)


class AllAuditSinksFailedError(Exception):
    pass


def _build_sinks(settings: Settings) -> list[AuditSink]:
    sinks: list[AuditSink] = [LocalFileAuditSink(settings.audit_local_file_path)]

    if settings.audit_s3_bucket and settings.audit_s3_region:
        from harness_mcp.audit_logging.sinks.s3_object_lock_sink import S3ObjectLockAuditSink

        sinks.append(
            S3ObjectLockAuditSink(
                bucket=settings.audit_s3_bucket,
                region=settings.audit_s3_region,
                prefix=settings.audit_s3_prefix,
            )
        )

    if settings.audit_webhook_url and settings.audit_webhook_signing_secret_ref:
        from harness_mcp.audit_logging.sinks.webhook_sink import WebhookAuditSink
        from harness_mcp.secrets.factory import get_secrets_provider

        secret = get_secrets_provider().get_secret(settings.audit_webhook_signing_secret_ref)
        sinks.append(WebhookAuditSink(url=str(settings.audit_webhook_url), signing_secret=secret))

    return sinks


@lru_cache(maxsize=1)
def get_audit_sinks() -> list[AuditSink]:
    return _build_sinks(get_settings())


async def write_audit_event(event: AuditEvent) -> None:
    settings = get_settings()
    sinks = get_audit_sinks()

    results = await asyncio.gather(
        *(sink.write(event) for sink in sinks), return_exceptions=True
    )

    any_success = False
    for sink, result in zip(sinks, results):
        if isinstance(result, Exception):
            AUDIT_SINK_FAILURES_TOTAL.labels(sink=sink.name).inc()
            logger.error("audit_sink_write_failed", sink=sink.name, error=str(result))
        else:
            any_success = True

    if not any_success and settings.audit_fail_closed:
        raise AllAuditSinksFailedError(
            "Every configured audit sink failed to write this event; refusing "
            "to let the action proceed unaudited (AUDIT_FAIL_CLOSED=true)."
        )
