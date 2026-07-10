"""Per-tool field allowlists: the primary redaction mechanism.

Harness NG API responses commonly use a `{"status", "data", "metaData",
"correlationId"}` envelope (see `sanitizer.py`). The allowlist below applies
to the *payload* (post-envelope-unwrap) using dotted paths; `*` matches any
single dict key or list index at that position.

These lists are a deliberately conservative starting point built from
well-known Harness NG field names (identifiers, statuses, timestamps). They
are NOT a guarantee of exact field names in every account/module version --
tune them against your account's real responses before production use (see
README "Known limitations"). Anything not listed is dropped, so the failure
mode of an incomplete allowlist is "too little data returned", never
"secret data leaked" -- the regex layer in patterns.py additionally scrubs
whatever does pass through.
"""

from __future__ import annotations

_COMMON = {
    "identifier",
    "name",
    "description",
    "tags",
    "status",
    "createdAt",
    "lastModifiedAt",
    "createdBy",
    "accountId",
    "orgIdentifier",
    "projectIdentifier",
}

_PIPELINE_EXEC_FIELDS = _COMMON | {
    "planExecutionId",
    "pipelineIdentifier",
    "executionStatus",
    "startTs",
    "endTs",
    "triggerType",
    "moduleInfo",
    "stagesExecution",
    "runSequence",
    "successfulStagesCount",
    "failedStagesCount",
}

TOOL_FIELD_ALLOWLIST: dict[str, set[str]] = {
    "list_pipelines": {f"content.*.{f}" for f in _COMMON} | {"totalElements", "pageIndex", "pageSize"},
    "get_pipeline": _COMMON | {"yamlPipeline", "numOfStages", "numOfErrors"},
    "get_pipeline_yaml": _COMMON | {"yamlPipeline"},
    "list_executions": {f"content.*.{f}" for f in _PIPELINE_EXEC_FIELDS} | {"totalElements"},
    "get_execution": _PIPELINE_EXEC_FIELDS,
    "get_execution_logs": {"logLines", "stageIdentifier", "stepIdentifier"},
    "trigger_pipeline": _PIPELINE_EXEC_FIELDS,
    "abort_execution": _PIPELINE_EXEC_FIELDS,
    "get_environment_state": _COMMON
    | {
        "environment.*",
        "activeInstances.*.instanceId",
        "activeInstances.*.artifactVersion",
        "activeInstances.*.deployedAt",
    },
    "promote_artifact": _PIPELINE_EXEC_FIELDS,
    "initiate_rollback": _COMMON | {"rollbackExecutionId", "targetExecutionId"},
    "list_scan_results": _COMMON | {"content.*.severity", "content.*.title", "content.*.issueId"},
    "get_vulnerability": _COMMON
    | {"severity", "title", "cve", "cvss", "remediation", "exemptionStatus"},
    "check_critical_block": _COMMON | {"blocked", "criticalCount", "exemptedCount"},
    "triage_vulnerability": _COMMON | {"issueId", "status", "comment"},
    "list_flags": {f"features.*.{f}" for f in (_COMMON | {"kind", "state"})},
    "get_flag": _COMMON | {"kind", "state", "variations", "defaultOnVariation", "defaultOffVariation"},
    "evaluate_flag": {"identifier", "value", "kind"},
    "update_flag_state": _COMMON | {"state"},
    "get_cost_summary": {"totalCost", "costTrend", "currency", "perspectiveId"},
    "list_cost_anomalies": {"content.*.id", "content.*.actualCost", "content.*.anomalyScore", "content.*.entity"},
    "get_cost_recommendations": {
        "items.*.id",
        "items.*.resourceType",
        "items.*.monthlySavings",
        "items.*.recommendationState",
    },
    "list_chaos_experiments": {f"experiments.*.{f}" for f in _COMMON},
    "get_chaos_experiment": _COMMON | {"experimentType", "lastRunStatus", "faults"},
    "run_chaos_experiment": _COMMON | {"runId", "status"},
    "query_audit_trail": {
        "content.*.action",
        "content.*.timestamp",
        "content.*.actor",
        "content.*.resourceType",
        "content.*.module",
    },
    "get_repo_info": _COMMON | {"repoUrl", "defaultBranch"},
}


def get_allowlist(tool_name: str) -> set[str]:
    return TOOL_FIELD_ALLOWLIST.get(tool_name, _COMMON)
