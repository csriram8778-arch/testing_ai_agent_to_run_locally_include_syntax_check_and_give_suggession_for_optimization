from __future__ import annotations


def document_prompt(pipeline_id: str) -> str:
    return f"""You are helping a Harness team member document a pipeline via `/document`.

Target: pipeline={pipeline_id}

Steps:
1. Call `get_pipeline(pipeline_id="{pipeline_id}")` and `get_pipeline_yaml(pipeline_id="{pipeline_id}")` \
to ground yourself in the pipeline's real structure and stages.
2. Write clear documentation yourself (purpose, stages, triggers, required approvals) using your own \
reasoning -- this server does not call out to a separate model.
3. This is a read-only workflow: no confirmation step is required.
"""
