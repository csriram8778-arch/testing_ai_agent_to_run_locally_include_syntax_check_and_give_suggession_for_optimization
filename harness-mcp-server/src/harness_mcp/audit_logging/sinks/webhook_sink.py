"""Generic SIEM/webhook sink (Splunk HEC-compatible JSON body, or any
webhook that accepts a signed JSON POST). Requests are HMAC-signed with a
secret pulled from the configured secrets backend so the receiving SIEM can
verify authenticity.
"""

from __future__ import annotations

import hashlib
import hmac
import json

import httpx

from harness_mcp.audit_logging.event import AuditEvent


class WebhookAuditSink:
    name = "webhook"

    def __init__(self, url: str, signing_secret: str) -> None:
        self._url = url
        self._signing_secret = signing_secret.encode("utf-8")
        self._client = httpx.AsyncClient(timeout=10.0)

    def _sign(self, body: bytes) -> str:
        return hmac.new(self._signing_secret, body, hashlib.sha256).hexdigest()

    async def write(self, event: AuditEvent) -> None:
        body = json.dumps({"event": event.to_json_dict()}, sort_keys=True).encode("utf-8")
        signature = self._sign(body)
        resp = await self._client.post(
            self._url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature-SHA256": signature,
            },
        )
        resp.raise_for_status()

    async def healthy(self) -> bool:
        try:
            resp = await self._client.head(self._url, timeout=5.0)
            return resp.status_code < 500
        except httpx.HTTPError:
            return False
