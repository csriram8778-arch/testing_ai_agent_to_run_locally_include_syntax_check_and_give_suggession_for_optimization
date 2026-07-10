from __future__ import annotations


def cost_check_prompt(perspective_id: str, start_time: str, end_time: str) -> str:
    return f"""You are helping a Harness team member check cloud cost via `/cost-check`.

Scope: perspective={perspective_id} window={start_time}..{end_time}

Steps:
1. Call `get_cost_summary(perspective_id="{perspective_id}", start_time="{start_time}", \
end_time="{end_time}")` and summarize the trend to the user.
2. Call `list_cost_anomalies(start_time="{start_time}", end_time="{end_time}")` and flag anything \
notable.
3. Optionally call `get_cost_recommendations()` if the user wants savings suggestions.
4. This entire module is read-only in this server (no write tools exist for cost management), so no \
confirmation step is ever required here.
"""
