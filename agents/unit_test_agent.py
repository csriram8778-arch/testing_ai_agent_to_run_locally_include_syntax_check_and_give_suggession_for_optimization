import ast
from core.task_model import AgentResponse


class UnitTestAgent:
    NAME = "UNIT_TEST_AGENT"

    # ── Helpers ────────────────────────────────────────────────────────

    def _get_functions(self, code: str):
        """Return list of FunctionDef nodes from parsed code."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []
        return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]

    def _arg_names(self, func: ast.FunctionDef):
        return [a.arg for a in func.args.args]

    def _build_tests(self, func_name: str, args: list) -> str:
        """Generate test stubs covering common edge cases."""
        arg_str_normal  = ", ".join(["1"] * len(args)) if args else ""
        arg_str_zero    = ", ".join(["0"] * len(args)) if args else ""
        arg_str_neg     = ", ".join(["-1"] * len(args)) if args else ""
        arg_str_none    = ", ".join(["None"] * len(args)) if args else ""
        arg_str_empty   = ", ".join(['""'] * len(args)) if args else ""
        arg_str_large   = ", ".join(["10**6"] * len(args)) if args else ""

        params = ", ".join(args) if args else ""

        tests = f'''import pytest
from your_module import {func_name}  # ← replace your_module with actual filename


# ── Normal cases ───────────────────────────────────────────
def test_{func_name}_basic():
    """Basic call with typical inputs."""
    result = {func_name}({arg_str_normal})
    assert result is not None


# ── Edge cases ─────────────────────────────────────────────
def test_{func_name}_zero_values():
    """All arguments as zero."""
    result = {func_name}({arg_str_zero})
    assert result is not None


def test_{func_name}_negative_values():
    """Negative inputs should not raise unexpected errors."""
    result = {func_name}({arg_str_neg})
    assert result is not None


def test_{func_name}_large_input():
    """Large values — checks for overflow or timeout."""
    result = {func_name}({arg_str_large})
    assert result is not None


# ── Type / None guards ─────────────────────────────────────
def test_{func_name}_none_input():
    """None inputs should raise TypeError or be handled gracefully."""
    with pytest.raises((TypeError, ValueError, AttributeError)):
        {func_name}({arg_str_none})


def test_{func_name}_empty_string():
    """Empty string inputs."""
    with pytest.raises((TypeError, ValueError)) if {repr(bool(args))} else pytest.warns(None):
        {func_name}({arg_str_empty})


# ── Return type check ──────────────────────────────────────
def test_{func_name}_return_type():
    """Return value should be a known type, not None unexpectedly."""
    result = {func_name}({arg_str_normal})
    # Update the expected type below to match your function
    assert isinstance(result, (int, float, str, list, dict, bool, type(None)))
'''
        return tests

    # ── Public entry point ─────────────────────────────────────────────

    def run(self, code: str) -> AgentResponse:
        functions = self._get_functions(code)

        if not functions:
            return AgentResponse(
                agent_name=self.NAME,
                result=(
                    "⚠️  No function definitions found in the input.\n"
                    "  Provide a Python function to generate tests for."
                )
            )

        all_tests = []
        for func in functions:
            args = self._arg_names(func)
            tests = self._build_tests(func.name, args)
            all_tests.append(
                f"# ════ Tests for `{func.name}({', '.join(args)})` ════\n"
                + tests
            )

        result = (
            "Generated pytest test stubs — "
            "copy into tests/ folder and update assertions:\n\n"
            + "\n\n".join(all_tests)
        )

        return AgentResponse(agent_name=self.NAME, result=result)
