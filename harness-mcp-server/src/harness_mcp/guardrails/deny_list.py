"""Second, independent enforcement layer at the HTTP-call boundary.

Even if a bug in `tools/registry.py` or a future tool accidentally tried to
call one of these operations, `harness_client.base.HarnessHTTPClient` checks
every outbound request against this deny-list first and refuses to send it.
This is deliberately redundant with "the tool doesn't exist" -- defense in
depth for the explicitly excluded categories: secret values, deletes, and
RBAC/token mutation.

Patterns are matched against the request path (after the module base path)
using simple substring/prefix rules -- intentionally conservative and easy to
audit by a human, not a general-purpose rules engine.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DenyRule:
    method: str  # "*" matches any method
    path_contains: str
    reason: str


DENY_RULES: tuple[DenyRule, ...] = (
    DenyRule("GET", "/secrets/", "reading secret values is never permitted"),
    DenyRule("GET", "/secret-text", "reading secret values is never permitted"),
    DenyRule("DELETE", "", "delete operations are never permitted"),
    DenyRule("*", "/rbac/", "RBAC/role modification is never permitted"),
    DenyRule("*", "/role-assignments", "RBAC/role modification is never permitted"),
    DenyRule("*", "/user-groups", "RBAC/role modification is never permitted"),
    DenyRule("*", "/api-key", "API token/key management is never permitted"),
    DenyRule("*", "/token", "API token/key management is never permitted"),
    DenyRule("POST", "/projects", "project deletion/creation is never permitted", ),
)


class DeniedByGuardrailError(Exception):
    def __init__(self, method: str, path: str, reason: str) -> None:
        super().__init__(f"Blocked {method} {path}: {reason}")
        self.method = method
        self.path = path
        self.reason = reason


def check_allowed(method: str, path: str) -> None:
    """Raise DeniedByGuardrailError if this call matches a deny rule.

    DELETE is blocked unconditionally regardless of path. Everything else is
    substring-matched against `path_contains`.
    """

    method_upper = method.upper()
    for rule in DENY_RULES:
        if rule.method not in ("*", method_upper):
            continue
        if rule.path_contains and rule.path_contains not in path:
            continue
        if rule.method == "DELETE" and method_upper != "DELETE":
            continue
        raise DeniedByGuardrailError(method_upper, path, rule.reason)
