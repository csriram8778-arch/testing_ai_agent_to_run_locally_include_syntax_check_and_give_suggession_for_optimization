from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Task:
    agent_name: str
    instruction: str
    input_code: str
    result: Optional[str] = None

@dataclass
class AgentResponse:
    agent_name: str
    result: str

    def __str__(self):
        return (
            f"\n[AGENT_RESPONSE]\n"
            f"Agent: {self.agent_name}\n"
            f"Result:\n{self.result}\n"
            f"{'-' * 50}"
        )

@dataclass
class FinalOutput:
    changes: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)

    def __str__(self):
        changes_str = "\n".join(f"  • {c}" for c in self.changes) or "  • No changes"
        steps_str = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(self.next_steps))
        return (
            f"\n{'=' * 50}\n"
            f"[FINAL_OUTPUT]\n"
            f"{'=' * 50}\n\n"
            f"Summary of Changes:\n{changes_str}\n\n"
            f"Suggested Next Steps:\n{steps_str}\n"
        )
