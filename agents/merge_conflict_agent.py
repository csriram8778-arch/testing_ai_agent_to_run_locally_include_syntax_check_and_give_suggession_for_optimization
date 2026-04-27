import re
from core.task_model import AgentResponse


class MergeConflictAgent:
    NAME = "MERGE_CONFLICT_AGENT"

    # Regex to match a full conflict block
    CONFLICT_PATTERN = re.compile(
        r"<{7} (.+?)\n(.*?)={7}\n(.*?)>{7} (.+?)(\n|$)",
        re.DOTALL
    )

    def _has_conflict(self, code: str) -> bool:
        return "<<<<<<<" in code and "=======" in code and ">>>>>>>" in code

    def _resolve(self, match: re.Match) -> tuple:
        """
        Returns (our_branch, our_code, their_branch, their_code, resolved).
        Resolution strategy:
          - If blocks are identical → keep one.
          - If one block is empty   → keep the non-empty one.
          - Otherwise               → keep BOTH with a merge comment.
        """
        our_branch   = match.group(1).strip()
        our_code     = match.group(2).strip()
        their_branch = match.group(4).strip()
        their_code   = match.group(3).strip()

        if our_code == their_code:
            resolved = our_code
            strategy = "identical — kept one copy"
        elif not our_code:
            resolved = their_code
            strategy = f"HEAD was empty — kept `{their_branch}`"
        elif not their_code:
            resolved = our_code
            strategy = f"`{their_branch}` was empty — kept HEAD"
        else:
            # Merge both, safer than auto-dropping either side
            resolved = (
                f"# ── Merged from {our_branch} ──\n"
                f"{our_code}\n"
                f"# ── Merged from {their_branch} ──\n"
                f"{their_code}"
            )
            strategy = f"both sides kept — review manually"

        return our_branch, our_code, their_branch, their_code, resolved, strategy

    def run(self, code: str) -> AgentResponse:
        if not self._has_conflict(code):
            return AgentResponse(
                agent_name=self.NAME,
                result="✅ No merge conflict markers found."
            )

        matches = list(self.CONFLICT_PATTERN.finditer(code))
        if not matches:
            return AgentResponse(
                agent_name=self.NAME,
                result=(
                    "⚠️  Conflict markers detected but could not be parsed.\n"
                    "  Ensure format is:\n"
                    "  <<<<<<< HEAD\n  ...\n  =======\n  ...\n  >>>>>>> branch"
                )
            )

        resolved_code = code
        report_lines = [
            f"Found {len(matches)} conflict block(s):\n"
        ]

        for i, match in enumerate(matches, 1):
            our_branch, our_code, their_branch, their_code, resolved, strategy = \
                self._resolve(match)

            # Replace the full conflict block with the resolved version
            resolved_code = resolved_code.replace(match.group(0), resolved + "\n", 1)

            report_lines.append(
                f"  Block {i}:\n"
                f"    HEAD   ({our_branch}):  {our_code[:60].replace(chr(10),' ')}...\n"
                f"    THEIRS ({their_branch}): {their_code[:60].replace(chr(10),' ')}...\n"
                f"    Strategy: {strategy}\n"
            )

        report_lines.append("── Resolved Code ──────────────────────────")
        report_lines.append(resolved_code)

        return AgentResponse(
            agent_name=self.NAME,
            result="\n".join(report_lines)
        )
