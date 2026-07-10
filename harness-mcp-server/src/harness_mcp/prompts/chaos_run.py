from __future__ import annotations


def chaos_run_prompt(experiment_id: str) -> str:
    return f"""You are helping a Harness team member run a chaos experiment via `/chaos-run`.

Target: experiment={experiment_id}

Steps:
1. Call `get_chaos_experiment(experiment_id="{experiment_id}")` and summarize exactly what this \
experiment will do (blast radius, fault type, target) to the user BEFORE proposing to run it.
2. Explicitly ask the user to confirm they understand the impact and want to proceed -- chaos \
experiments affect live systems.
3. Call `run_chaos_experiment(experiment_id="{experiment_id}")`. This is a WRITE action with an \
explicit approval gate: the first call returns `status: pending_confirmation` with a \
`confirmation_token`. Only call again with that token after the user has explicitly approved \
running THIS experiment in this conversation turn.
4. Report the resulting run status back to the user, and mention how to check on/abort it if the \
platform surfaces that capability later.
"""
