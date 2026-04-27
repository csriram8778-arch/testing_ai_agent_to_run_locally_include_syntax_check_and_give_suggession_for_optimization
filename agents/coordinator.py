from agents.syntax_check_agent import SyntaxCheckAgent
from agents.optimization_agent import OptimizationAgent
from agents.unit_test_agent import UnitTestAgent
from agents.merge_conflict_agent import MergeConflictAgent
from agents.test_script_writer_agent import TestScriptWriterAgent   # ← NEW
from core.task_model import FinalOutput
from core.output_formatter import format_task_assignment


class Coordinator:
    """
    Central controller.
    Analyses user input → dispatches tasks → aggregates results.

    Agent execution order:
      1. MERGE_CONFLICT_AGENT     (if <<< markers found)
      2. SYNTAX_CHECK_AGENT       (always)
      3. OPTIMIZATION_AGENT       (only if syntax clean)
      4. UNIT_TEST_AGENT          (only if syntax clean)
      5. TEST_SCRIPT_WRITER_AGENT (only if syntax clean)
    """

    def __init__(self):
        self.syntax_agent       = SyntaxCheckAgent()
        self.optimization_agent = OptimizationAgent()
        self.unit_test_agent    = UnitTestAgent()
        self.merge_agent        = MergeConflictAgent()
        self.test_writer_agent  = TestScriptWriterAgent()

    def _is_merge_conflict(self, code: str) -> bool:
        return "<<<<<<<" in code and "=======" in code

    def _has_syntax_error(self, result_text: str) -> bool:
        return "SyntaxError" in result_text

    def _print_assignment(self, agent: str, task: str, code: str):
        print(format_task_assignment(agent, task, code))

    def _skipped(self, agent_name: str) -> str:
        return (
            f"\n[SKIPPED] {agent_name} "
            f"— syntax errors must be fixed first.\n"
            + "-" * 50
        )

    def analyze(self, user_input: str, module_name: str = "your_module") -> str:
        output_lines = []
        final = FinalOutput()

        print("\n[COORDINATOR] Analysing input...\n")

        # Step 1: Merge Conflict
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

        # Step 2: Syntax Check
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
            final.next_steps.append("Fix syntax errors before running other agents")

        # Step 3: Optimization
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
            output_lines.append(self._skipped(OptimizationAgent.NAME))

        # Step 4: Unit Test Stubs
        if not has_errors:
            self._print_assignment(
                UnitTestAgent.NAME,
                "Generate pytest test stubs covering edge cases",
                user_input
            )
            test_result = self.unit_test_agent.run(user_input)
            output_lines.append(str(test_result))
            final.changes.append("Unit test stubs generated")
            final.next_steps.append("Copy test stubs to tests/ and update assertions")
        else:
            output_lines.append(self._skipped(UnitTestAgent.NAME))

        # Step 5: Full Test Script (NEW)
        if not has_errors:
            self._print_assignment(
                TestScriptWriterAgent.NAME,
                "Write a complete ready-to-run pytest test script",
                user_input
            )
            script_result = self.test_writer_agent.run(user_input, module_name)
            output_lines.append(str(script_result))
            final.changes.append("Full test script generated")
            final.next_steps.append(
                f"Save generated script to tests/test_{module_name}.py "
                f"then run: pytest tests/ -v"
            )
        else:
            output_lines.append(self._skipped(TestScriptWriterAgent.NAME))

        output_lines.append(str(final))
        return "\n".join(output_lines)
