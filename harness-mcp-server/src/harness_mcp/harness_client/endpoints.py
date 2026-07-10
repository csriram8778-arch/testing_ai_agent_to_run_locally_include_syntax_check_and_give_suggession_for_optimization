"""Per-module Harness NG API base paths.

Exact paths drift between Harness releases and differ SaaS vs Self-Managed
Enterprise Edition. This module is the single seam to update when they do --
none of the per-module client files below should hardcode a base path.

IMPORTANT: the paths below are best-effort, built from well-known/public
Harness NextGen API conventions. Verify each against your account's live
OpenAPI docs (Account Settings -> API docs, or https://apidocs.harness.io)
before relying on them in production -- see README "Known limitations".
"""

from __future__ import annotations

from dataclasses import dataclass

from harness_mcp.settings import HarnessEdition


@dataclass(frozen=True, slots=True)
class ModulePaths:
    pipeline: str = "pipeline/api"
    ng: str = "ng/api"
    feature_flags: str = "cf/admin"
    sto: str = "sto/api/v2"
    ccm: str = "ccm/api"
    chaos: str = "chaos/manager/api"
    audit: str = "audit/api"


# Self-Managed Enterprise Edition installs commonly proxy the same module
# prefixes through a single gateway too, but some deployments front them
# behind an extra `/api/` segment or module-specific subdomains. Confirm with
# the team's platform admin and adjust here if needed.
_PATHS_BY_EDITION: dict[HarnessEdition, ModulePaths] = {
    "saas": ModulePaths(),
    "self_managed_ee": ModulePaths(),
}


def get_module_paths(edition: HarnessEdition) -> ModulePaths:
    return _PATHS_BY_EDITION[edition]
