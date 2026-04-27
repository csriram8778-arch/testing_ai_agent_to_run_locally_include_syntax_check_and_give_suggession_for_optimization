def format_task_assignment(agent: str, task: str, input_code: str) -> str:
    preview = input_code.strip()[:120].replace("\n", " ")
    return (
        f"\n[TASK_ASSIGNMENT]\n"
        f"Agent: {agent}\n"
        f"Task:  {task}\n"
        f"Input: {preview}...\n"
        f"{'-' * 50}"
    )
