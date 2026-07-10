"""Named slash-command-style prompts. Each returns a templated instruction
message for Claude -- none of them call `harness_client` directly, so
enforcement of the confirmation step stays entirely in
`tools/registry.py`/`guardrails/approval_hook.py` regardless of what a
prompt's text says. A client that ignores a prompt's instructions still
cannot push a WRITE-tier tool through without a valid confirmation token.
"""

from harness_mcp.prompts.chaos_run import chaos_run_prompt
from harness_mcp.prompts.cost_check import cost_check_prompt
from harness_mcp.prompts.deploy import deploy_prompt
from harness_mcp.prompts.document import document_prompt
from harness_mcp.prompts.review_pr import review_pr_prompt
from harness_mcp.prompts.rollback import rollback_prompt
from harness_mcp.prompts.triage import triage_prompt

ALL_PROMPTS = {
    "deploy": deploy_prompt,
    "rollback": rollback_prompt,
    "triage": triage_prompt,
    "review-pr": review_pr_prompt,
    "document": document_prompt,
    "cost-check": cost_check_prompt,
    "chaos-run": chaos_run_prompt,
}

__all__ = ["ALL_PROMPTS"]
