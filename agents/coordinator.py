from agents.syntax_check_agent import SyntaxCheckAgent
from agents.optimization_agent import OptimizationAgent
from agents.unit_test_agent import UnitTestAgent
from agents.merge_conflict_agent import MergeConflictAgent
from core.task_model import FinalOutput
from core.output_formatter import format_task_assignment


class Coordinator:
    """
    Central controller.
    Analyses user input → dispatches tasks → aggregates results.
    """

    def __init__(self):
        self.syntax_agent      = SyntaxCheckAgent()
        self.optimization_agent = OptimizationAgent()
        self.unit_test_agent   = UnitTestAgent()
        self.merge_agent       = MergeConflictAgent()

    # ── Internal helpers ───────────────────────────────────────────────

    def _is_merge_conflict(self, code: str) -> bool:
        return "<<<<<<<" in code and "=======" in code

    def _has_syntax_error(self, result_text: str) -> bool:
        return "SyntaxError" in result_text

    def _print_assignment(self, agent: str, task: str, code: str):
        print(format_task_assignment(agent, task, code))

    # ── Main entry point ───────────────────────────────────────────────

    def analyze(self, user_input: str) -> str:
        output_lines = []
        final = FinalOutput()

        print("\n[COORDINATOR] Analysing input...\n")

        # ── Step 1: Merge Conflict ─────────────────────────────────────
        if self._is_merge_conflict(user_input):
            self._print_assignment(
                MergeConflictAgent.NAME,
                "Detect and resolve all merge conflict blocks",
                user_input
            )
            r = self.merge_agent.run(user_input)
            output_lines.append(str(r))
            final.changes.append("Merge conflicts resolved")
            final.next_steps.append("Review resolved code, then commit")

        # ── Step 2: Syntax Check ───────────────────────────────────────
        self._print_assignment(
            SyntaxCheckAgent.NAME,
            "Check for syntax errors and code warnings",
            user_input
        )
        syntax_result = self.syntax_agent.run(user_input)
        output_lines.append(str(syntax_result))
        final.changes.append("Syntax analysis complete")

        has_errors = self._has_syntax_error(syntax_result.result)
        if has_errors:
            final.next_steps.append("⚠️  Fix syntax errors before running other agents")

        # ── Step 3: Optimization (only if syntax is clean) ────────────
        if not has_errors:
            self._print_assignment(
                OptimizationAgent.NAME,
                "Identify performance and readability improvements",
                user_input
            )
            opt_result = self.optimization_agent.run(user_input)
            output_lines.append(str(opt_result))
            final.changes.append("Optimization analysis complete")
            final.next_steps.append("Apply optimization suggestions where applicable")
        else:
            output_lines.append(
                "\n[SKIPPED] OPTIMIZATION_AGENT — syntax errors must be fixed first.\n"
                + "-" * 50
            )

        # ── Step 4: Unit Tests (only if syntax is clean) ──────────────
        if not has_errors:
            self._print_assignment(
                UnitTestAgent.NAME,
                "Generate pytest test stubs covering edge cases",
                user_input
            )
            test_result = self.unit_test_agent.run(user_input)
            output_lines.append(str(test_result))
            final.changes.append("Unit test stubs generated")
            final.next_steps.append("Copy generated tests to tests/ and run: pytest tests/ -v")
        else:
            output_lines.append(
                "\n[SKIPPED] UNIT_TEST_AGENT — syntax errors must be fixed first.\n"
                + "-" * 50
            )

        # ── Step 5: Aggregate ──────────────────────────────────────────
        output_lines.append(str(final))

        return "\n".join(output_lines)
