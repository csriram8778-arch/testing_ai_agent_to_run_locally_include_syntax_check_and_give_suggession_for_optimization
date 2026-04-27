"""
Run with:  pytest tests/test_agents.py -v
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from agents.syntax_check_agent import SyntaxCheckAgent
from agents.optimization_agent import OptimizationAgent
from agents.unit_test_agent import UnitTestAgent
from agents.merge_conflict_agent import MergeConflictAgent
from agents.coordinator import Coordinator


# ══════════════════════════════════════════════
#  SYNTAX CHECK AGENT
# ══════════════════════════════════════════════

class TestSyntaxCheckAgent:
    agent = SyntaxCheckAgent()

    def test_valid_code(self):
        code = "def add(a, b):\n    return a + b"
        r = self.agent.run(code)
        assert "No syntax errors" in r.result

    def test_missing_colon(self):
        code = "def add(a, b)\n    return a + b"
        r = self.agent.run(code)
        assert "SyntaxError" in r.result

    def test_empty_input(self):
        r = self.agent.run("")
        assert r.result is not None

    def test_bare_except_warning(self):
        code = (
            "def risky():\n"
            "    try:\n"
            "        pass\n"
            "    except:\n"
            "        pass"
        )
        r = self.agent.run(code)
        assert "Bare" in r.result or "except" in r.result


# ══════════════════════════════════════════════
#  OPTIMIZATION AGENT
# ══════════════════════════════════════════════

class TestOptimizationAgent:
    agent = OptimizationAgent()

    def test_clean_code(self):
        code = "def greet(name):\n    return f'Hello {name}'"
        r = self.agent.run(code)
        assert "No optimization" in r.result

    def test_nested_loop_detected(self):
        code = (
            "def search(lst):\n"
            "    for i in lst:\n"
            "        for j in lst:\n"
            "            pass"
        )
        r = self.agent.run(code)
        assert "Nested loop" in r.result or "nested" in r.result.lower()

    def test_range_len_detected(self):
        code = (
            "def process(items):\n"
            "    for i in range(len(items)):\n"
            "        print(items[i])"
        )
        r = self.agent.run(code)
        assert "range(len" in r.result or "enumerate" in r.result

    def test_mutable_default_arg(self):
        code = "def append_item(item, lst=[]):\n    lst.append(item)\n    return lst"
        r = self.agent.run(code)
        assert "Mutable" in r.result or "mutable" in r.result.lower()

    def test_syntax_error_skips_optimization(self):
        code = "def bad(a, b)\n    return a"
        r = self.agent.run(code)
        assert "syntax" in r.result.lower() or "Cannot optimize" in r.result


# ══════════════════════════════════════════════
#  UNIT TEST AGENT
# ══════════════════════════════════════════════

class TestUnitTestAgent:
    agent = UnitTestAgent()

    def test_generates_tests_for_function(self):
        code = "def multiply(a, b):\n    return a * b"
        r = self.agent.run(code)
        assert "multiply" in r.result
        assert "pytest" in r.result

    def test_no_functions_returns_warning(self):
        code = "x = 1 + 1"
        r = self.agent.run(code)
        assert "No function" in r.result or "no function" in r.result.lower()

    def test_edge_cases_included(self):
        code = "def divide(a, b):\n    return a / b"
        r = self.agent.run(code)
        assert "None" in r.result or "zero" in r.result.lower() or "edge" in r.result.lower()


# ══════════════════════════════════════════════
#  MERGE CONFLICT AGENT
# ══════════════════════════════════════════════

class TestMergeConflictAgent:
    agent = MergeConflictAgent()

    def test_no_conflict(self):
        code = "def greet():\n    return 'hello'"
        r = self.agent.run(code)
        assert "No merge conflict" in r.result

    def test_detects_conflict(self):
        code = (
            "<<<<<<< HEAD\n"
            "def greet():\n    return 'Hello'\n"
            "=======\n"
            "def greet():\n    return 'Hi'\n"
            ">>>>>>> feature\n"
        )
        r = self.agent.run(code)
        assert "Block 1" in r.result or "conflict" in r.result.lower()

    def test_identical_blocks_resolved(self):
        code = (
            "<<<<<<< HEAD\n"
            "x = 1\n"
            "=======\n"
            "x = 1\n"
            ">>>>>>> feature\n"
        )
        r = self.agent.run(code)
        assert "identical" in r.result.lower() or "x = 1" in r.result


# ══════════════════════════════════════════════
#  COORDINATOR (integration)
# ══════════════════════════════════════════════

class TestCoordinator:
    coord = Coordinator()

    def test_runs_without_crash(self):
        code = "def add(a, b):\n    return a + b"
        result = self.coord.analyze(code)
        assert "[AGENT_RESPONSE]" in result
        assert "[FINAL_OUTPUT]" in result

    def test_skips_optimization_on_syntax_error(self):
        code = "def bad(a, b)\n    return a"
        result = self.coord.analyze(code)
        assert "SKIPPED" in result

    def test_merge_conflict_triggers_merge_agent(self):
        code = (
            "<<<<<<< HEAD\n"
            "def greet(): return 'Hello'\n"
            "=======\n"
            "def greet(): return 'Hi'\n"
            ">>>>>>> feature\n"
        )
        result = self.coord.analyze(code)
        assert "MERGE_CONFLICT_AGENT" in result
