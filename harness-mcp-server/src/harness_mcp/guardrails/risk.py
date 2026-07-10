"""Risk classification: the table that decides which tools require human
confirmation and which are structurally impossible to register at all.

`tools/registry.py` refuses to register any tool whose name is absent from
`TOOL_RISK` -- classification is a startup-time hard failure, not something
a reviewer has to remember to check.
"""

from __future__ import annotations

from enum import Enum


class RiskTier(str, Enum):
    READ_ONLY = "read_only"
    WRITE = "write"
    # Tools at this tier are never implemented/registered. Listing the
    # *names* here is documentation of intent, not an enforcement mechanism --
    # enforcement is "the function doesn't exist" plus the independent
    # deny_list check inside harness_client.base.
    DESTRUCTIVE_EXCLUDED = "destructive_excluded"


TOOL_RISK: dict[str, RiskTier] = {
    # -- CI/CD pipelines --------------------------------------------------
    "list_pipelines": RiskTier.READ_ONLY,
    "get_pipeline": RiskTier.READ_ONLY,
    "list_executions": RiskTier.READ_ONLY,
    "get_execution": RiskTier.READ_ONLY,
    "trigger_pipeline": RiskTier.WRITE,
    "abort_execution": RiskTier.WRITE,
    # -- Deployments --------------------------------------------------------
    "get_environment_state": RiskTier.READ_ONLY,
    "promote_artifact": RiskTier.WRITE,
    "initiate_rollback": RiskTier.WRITE,
    # -- STO ------------------------------------------------------------
    "list_scan_results": RiskTier.READ_ONLY,
    "get_vulnerability": RiskTier.READ_ONLY,
    "check_critical_block": RiskTier.READ_ONLY,
    "triage_vulnerability": RiskTier.WRITE,
    # -- Feature flags --------------------------------------------------
    "list_flags": RiskTier.READ_ONLY,
    "get_flag": RiskTier.READ_ONLY,
    "evaluate_flag": RiskTier.READ_ONLY,
    "update_flag_state": RiskTier.WRITE,
    # -- Cloud cost management (read-only module, no write tools exist) --
    "get_cost_summary": RiskTier.READ_ONLY,
    "list_cost_anomalies": RiskTier.READ_ONLY,
    "get_cost_recommendations": RiskTier.READ_ONLY,
    # -- Chaos engineering ------------------------------------------------
    "list_chaos_experiments": RiskTier.READ_ONLY,
    "get_chaos_experiment": RiskTier.READ_ONLY,
    "run_chaos_experiment": RiskTier.WRITE,
    # -- Audit logs (read-only) -------------------------------------------
    "query_audit_trail": RiskTier.READ_ONLY,
    # -- Code/doc grounding context ---------------------------------------
    "get_pipeline_yaml": RiskTier.READ_ONLY,
    "get_repo_info": RiskTier.READ_ONLY,
    "get_execution_logs": RiskTier.READ_ONLY,
}

# Tools that must NEVER be implemented, for documentation purposes only.
# harness_client.base independently enforces this at the HTTP layer via
# guardrails.deny_list, so this being "just a list" is not the only control.
DESTRUCTIVE_EXCLUDED_INTENT: tuple[str, ...] = (
    "get_secret_value",
    "delete_pipeline",
    "delete_service",
    "delete_environment",
    "delete_project",
    "update_rbac_role",
    "create_api_token",
    "revoke_api_token",
)


def requires_confirmation(tool_name: str) -> bool:
    tier = TOOL_RISK.get(tool_name)
    if tier is None:
        raise KeyError(
            f"Tool '{tool_name}' has no risk classification in guardrails.risk.TOOL_RISK. "
            "Refusing to treat an unclassified tool as safe."
        )
    return tier == RiskTier.WRITE
