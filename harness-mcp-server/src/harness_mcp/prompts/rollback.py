from __future__ import annotations


def rollback_prompt(
    environment_id: str, service_id: str, target_execution_id: str | None = None
) -> str:
    return f"""You are helping a Harness team member roll back via the `/rollback` workflow.

Target: environment={environment_id} service={service_id} \
{"target_execution=" + target_execution_id if target_execution_id else "(roll back to previous deployment)"}

Steps:
1. Call `get_environment_state(environment_id="{environment_id}")` and summarize the currently \
deployed version and recent execution history for this service to the user.
2. Clearly state what rolling back will change (from which version to which version).
3. Call `initiate_rollback(environment_id="{environment_id}", service_id="{service_id}", \
target_execution_id={target_execution_id!r})`. This is a WRITE action: the first call returns \
`status: pending_confirmation` with a `confirmation_token`. Get explicit user approval in this \
conversation turn before calling again with that token and identical parameters.
4. Report the resulting rollback execution status back to the user.
"""
