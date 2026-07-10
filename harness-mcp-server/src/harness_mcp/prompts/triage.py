from __future__ import annotations


def triage_prompt(pipeline_execution_id: str | None = None, target_id: str | None = None) -> str:
    return f"""You are helping a Harness team member triage security findings via `/triage`.

Scope: {"pipeline_execution=" + pipeline_execution_id if pipeline_execution_id else ""} \
{"target=" + target_id if target_id else ""}

Steps:
1. Call `list_scan_results(target_id={target_id!r}, pipeline_execution_id={pipeline_execution_id!r})` \
and summarize findings grouped by severity.
2. For each CRITICAL/HIGH finding the user wants to act on, call `get_vulnerability(issue_id=...)` \
for full detail before recommending a triage status.
3. If a finding needs a status change (confirmed / false positive / exemption requested), propose \
the specific status and comment to the user and get explicit agreement.
4. Call `triage_vulnerability(issue_id=..., status=..., comment=...)`. This is a WRITE action: the \
first call returns `status: pending_confirmation` with a `confirmation_token`. Only call again with \
that token after the user has explicitly agreed to the specific status/comment in this turn.
5. If the user's goal is to know whether a pipeline can safely promote, call `check_critical_block` \
and report its answer plainly rather than guessing.
"""
