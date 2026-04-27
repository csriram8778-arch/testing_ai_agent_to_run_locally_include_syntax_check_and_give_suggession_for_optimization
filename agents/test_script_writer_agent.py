import ast
from core.task_model import AgentResponse


class TestScriptWriterAgent:
    """
    Writes a complete, ready-to-run pytest test script from any Python code.
    Unlike UNIT_TEST_AGENT (which generates stubs), this agent produces
    a fully working test file you can run immediately with: pytest tests/
    """
    NAME = "TEST_SCRIPT_WRITER_AGENT"

    # ── Helpers ────────────────────────────────────────────────────────

    def _parse_functions(self, code: str):
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []
        return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]

    def _get_return_type(self, func: ast.FunctionDef) -> str:
        """Best-guess return type from annotation or body."""
        if func.returns:
            return ast.unparse(func.returns)
        for node in ast.walk(func):
            if isinstance(node, ast.Return) and node.value:
                if isinstance(node.value, ast.Constant):
                    return type(node.value.value).__name__
                if isinstance(node.value, (ast.List, ast.ListComp)):
                    return "list"
                if isinstance(node.value, (ast.Dict, ast.DictComp)):
                    return "dict"
                if isinstance(node.value, ast.BinOp):
                    return "number"
        return "object"

    def _sample_args(self, func: ast.FunctionDef) -> dict:
        """
        Generate sample argument values based on annotation hints or names.
        Falls back to safe defaults when no hint is available.
        """
        samples = {}
        annotations = {a.arg: ast.unparse(a.annotation)
                       for a in func.args.args
                       if a.annotation} if func.args.args else {}

        for arg in func.args.args:
            name = arg.arg
            hint = annotations.get(name, "").lower()

            if name == "self":
                continue
            elif "str" in hint or any(k in name for k in ["name", "text", "msg", "path", "key", "label"]):
                samples[name] = '"hello"'
            elif "float" in hint:
                samples[name] = "1.5"
            elif "bool" in hint or name.startswith("is_") or name.startswith("has_"):
                samples[name] = "True"
            elif "list" in hint or name in ["items", "lst", "arr", "data", "values"]:
                samples[name] = "[1, 2, 3]"
            elif "dict" in hint or name in ["config", "options", "params", "mapping"]:
                samples[name] = '{"key": "value"}'
            else:
                samples[name] = "1"   # safe numeric default

        return samples

    def _write_test_class(self, func: ast.FunctionDef, module_name: str) -> str:
        args      = [a.arg for a in func.args.args if a.arg != "self"]
        samples   = self._sample_args(func)
        call_args = ", ".join(samples.get(a, "1") for a in args)
        ret_type  = self._get_return_type(func)
        fn        = func.name
        cls       = fn.replace("_", " ").title().replace(" ", "")

        # Build a sensible assert for the happy path
        if ret_type in ("int", "float", "number"):
            happy_assert = f"assert isinstance(result, (int, float))"
        elif ret_type == "str":
            happy_assert = f"assert isinstance(result, str)"
        elif ret_type == "list":
            happy_assert = f"assert isinstance(result, list)"
        elif ret_type == "dict":
            happy_assert = f"assert isinstance(result, dict)"
        elif ret_type == "bool":
            happy_assert = f"assert isinstance(result, bool)"
        else:
            happy_assert = f"assert result is not None"

        return f'''
class Test{cls}:
    """Tests for {fn}({", ".join(args)})"""

    # ── Happy path ────────────────────────────────────────────
    def test_{fn}_returns_expected_type(self):
        result = {fn}({call_args})
        {happy_assert}

    def test_{fn}_basic_call_succeeds(self):
        """Should not raise any exception on valid input."""
        try:
            {fn}({call_args})
        except Exception as e:
            pytest.fail(f"{fn} raised {{e}} unexpectedly")

    # ── Edge cases ────────────────────────────────────────────
    def test_{fn}_with_zero(self):
        """Zero / falsy values should not crash the function."""
        zero_args = ", ".join(["0"] * len(args)) if {repr(bool(args))} else ""
        try:
            {fn}({{zero_args}})
        except (TypeError, ValueError, ZeroDivisionError):
            pass   # acceptable errors for zero input

    def test_{fn}_with_large_input(self):
        """Large inputs check for overflow or performance issues."""
        large_args = ", ".join(["10**6"] * len(args)) if {repr(bool(args))} else ""
        try:
            {fn}({{large_args}})
        except (TypeError, OverflowError, RecursionError):
            pass   # acceptable for oversized input

    def test_{fn}_with_negative(self):
        """Negative values should be handled or raise a clear error."""
        neg_args = ", ".join(["-1"] * len(args)) if {repr(bool(args))} else ""
        try:
            {fn}({{neg_args}})
        except (TypeError, ValueError):
            pass

    # ── None / type guard ─────────────────────────────────────
    def test_{fn}_none_raises_or_handles(self):
        """Passing None should raise TypeError or handle gracefully."""
        none_args = ", ".join(["None"] * len(args)) if {repr(bool(args))} else ""
        if none_args:
            with pytest.raises((TypeError, AttributeError, ValueError)):
                {fn}({{none_args}})

    def test_{fn}_empty_string(self):
        """Empty string inputs."""
        str_args = ", ".join(['""'] * len(args)) if {repr(bool(args))} else ""
        try:
            {fn}({{str_args}})
        except (TypeError, ValueError):
            pass

    # ── Return value consistency ──────────────────────────────
    def test_{fn}_same_input_same_output(self):
        """Pure functions must return the same result for identical inputs."""
        r1 = {fn}({call_args})
        r2 = {fn}({call_args})
        assert r1 == r2, "Function returned different results for identical inputs"
'''

    # ── Public entry point ─────────────────────────────────────────────

    def run(self, code: str, module_name: str = "your_module") -> AgentResponse:
        functions = self._parse_functions(code)

        if not functions:
            return AgentResponse(
                agent_name=self.NAME,
                result=(
                    "⚠️  No function definitions found.\n"
                    "  Provide Python code containing at least one function."
                )
            )

        test_classes = [self._write_test_class(f, module_name) for f in functions]
        func_names   = [f.name for f in functions]

        script = f'''"""
Auto-generated test script
Generated by: TEST_SCRIPT_WRITER_AGENT
Functions tested: {", ".join(func_names)}

HOW TO RUN:
  1. Copy this file to your tests/ folder
  2. Replace '{module_name}' import with your actual module filename
  3. Run:  pytest tests/test_{module_name}.py -v
"""
import pytest
import sys
import os

# ── Make sure the project root is on the path ─────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from {module_name} import {", ".join(func_names)}


{"".join(test_classes)}

# ── Parametrized tests (data-driven) ─────────────────────────────────
{"".join(self._parametrized_block(f) for f in functions)}
'''

        return AgentResponse(agent_name=self.NAME, result=script)

    def _parametrized_block(self, func: ast.FunctionDef) -> str:
        args = [a.arg for a in func.args.args if a.arg != "self"]
        if not args:
            return ""

        fn = func.name
        first_arg = args[0]

        return f'''
@pytest.mark.parametrize("{first_arg}", [0, 1, -1, 100, "test", None])
def test_{fn}_parametrized_{first_arg}({first_arg}):
    """Data-driven test — runs {fn} with multiple {first_arg} values."""
    try:
        result = {fn}(**{{"{first_arg}": {first_arg}}})
        assert result is not None or result == 0
    except (TypeError, ValueError, AttributeError):
        pass  # acceptable failures for invalid input types
'''