from __future__ import annotations


def review_pr_prompt(connector_id: str, repo_name: str, pipeline_id: str | None = None) -> str:
    return f"""You are helping a Harness team member review a pull request via `/review-pr`.

Repository: connector={connector_id} repo={repo_name}

Steps:
1. Call `get_repo_info(connector_id="{connector_id}", repo_name="{repo_name}")` to ground yourself \
in the real repository (default branch, URL) rather than guessing.
2. If a `pipeline_id` is relevant to this PR's CI status, call `get_pipeline_yaml(pipeline_id=...)` \
and `list_executions(pipeline_id=...)` to check current CI health.
3. Perform the actual code review yourself, using your own reasoning -- this server does not call \
out to a separate model. Cover correctness, security, and test coverage.
4. This is a read-only workflow: no tool call here can modify anything, so no confirmation step is \
required. If the user then asks you to *act* on review feedback (e.g. trigger a re-run), route that \
through the appropriate WRITE-tier tool and its confirmation step.
"""
