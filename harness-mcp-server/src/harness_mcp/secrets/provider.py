"""Secrets backend abstraction.

Used only for the server's own operational credentials: the local-dev/stdio
Harness service-account token, S3 credentials for the audit sink, and the
webhook signing secret. In multi-user HTTP mode, per-user Harness tokens flow
straight from the ``x-harness-api-key`` request header through
``session_context`` and never touch this subsystem -- the server holds zero
Harness credentials of its own in that mode.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SecretsProvider(Protocol):
    """Minimal interface every secrets backend adapter implements."""

    def get_secret(self, key: str) -> str:
        """Return a single secret string by logical key. Raises KeyError if absent."""
        ...

    def get_secret_json(self, key: str) -> dict:
        """Return a secret stored as a JSON object by logical key."""
        ...
