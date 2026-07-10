from __future__ import annotations


class HarnessAPIError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class HarnessAuthError(HarnessAPIError):
    """Harness rejected the caller's token (401/403)."""


class HarnessNotFoundError(HarnessAPIError):
    """404 from Harness."""


class OperationNotPermittedError(HarnessAPIError):
    """Raised by the guardrail deny-list before any HTTP call is made.

    This is a *structural* block, independent of and in addition to a tool
    simply not existing for delete/RBAC/secrets-value operations.
    """
