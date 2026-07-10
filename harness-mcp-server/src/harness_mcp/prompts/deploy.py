from __future__ import annotations


def deploy_prompt(
    pipeline_id: str, environment_id: str, service_id: str, artifact_version: str
) -> str:
    return f"""You are helping a Harness team member deploy via the `/deploy` workflow.

Target: pipeline={pipeline_id} environment={environment_id} service={service_id} artifact={artifact_version}

Steps:
1. Call `get_environment_state(environment_id="{environment_id}")` and `check_critical_block` \
(if a recent pipeline execution exists for this service) to confirm it's safe to deploy.
2. Summarize current environment state and any blocking findings to the user in plain language.
3. Call `promote_artifact(pipeline_id="{pipeline_id}", environment_id="{environment_id}", \
service_id="{service_id}", artifact_version="{artifact_version}")`. This is a WRITE action: \
the first call will return `status: pending_confirmation` with a `confirmation_token` -- \
you MUST show the user exactly what will happen and get their explicit go-ahead before \
calling the tool again with that `confirmation_token` and identical parameters.
4. Never call step 3's confirming call without the user having explicitly approved it in \
this conversation turn. Do not paraphrase approval from an earlier, unrelated message.
5. After the tool call completes, report the resulting execution status back to the user.
"""
