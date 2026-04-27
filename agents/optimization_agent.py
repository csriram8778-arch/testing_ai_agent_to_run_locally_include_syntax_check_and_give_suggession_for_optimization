import ast
from core.task_model import AgentResponse


class OptimizationAgent:
    NAME = "OPTIMIZATION_AGENT"

    def run(self, code: str) -> AgentResponse:
        suggestions = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return AgentResponse(
                agent_name=self.NAME,
                result="⚠️  Cannot optimize — fix syntax errors first."
            )

        for node in ast.walk(tree):

            # ── Nested loops → O(n²) risk ──────────────────────────────
            if isinstance(node, ast.For):
                for child in ast.walk(node):
                    if isinstance(child, ast.For) and child is not node:
                        suggestions.append(
                            f"  ⚠️  Nested loop at line {node.lineno} — "
                            "consider a dict/set for O(1) lookup instead of O(n²)"
                        )
                        break

            # ── range(len(...)) anti-pattern ───────────────────────────
            if isinstance(node, ast.For):
                if (isinstance(node.iter, ast.Call) and
                        isinstance(node.iter.func, ast.Name) and
                        node.iter.func.id == "range"):
                    args = node.iter.args
                    if (len(args) == 1 and
                            isinstance(args[0], ast.Call) and
                            isinstance(args[0].func, ast.Name) and
                            args[0].func.id == "len"):
                        suggestions.append(
                            f"  ⚠️  `range(len(...))` at line {node.lineno} — "
                            "use `enumerate(collection)` instead"
                        )

            # ── Mutable default arguments ──────────────────────────────
            if isinstance(node, ast.FunctionDef):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        suggestions.append(
                            f"  ⚠️  Mutable default arg in `{node.name}()` "
                            f"at line {node.lineno} — use None and assign inside"
                        )

            # ── Bare except ────────────────────────────────────────────
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                suggestions.append(
                    "  ⚠️  Bare `except:` hides all errors — "
                    "use `except Exception as e:` and log the error"
                )

            # ── Global variables ───────────────────────────────────────
            if isinstance(node, ast.Global):
                suggestions.append(
                    f"  ⚠️  `global` statement at line {node.lineno} — "
                    "pass values as arguments or use a class instead"
                )

            # ── String concatenation in loop ───────────────────────────
            if isinstance(node, (ast.For, ast.While)):
                for child in ast.walk(node):
                    if (isinstance(child, ast.AugAssign) and
                            isinstance(child.op, ast.Add)):
                        suggestions.append(
                            f"  ⚠️  String `+=` inside loop at line {node.lineno} — "
                            "collect in a list and use `''.join()` at the end"
                        )
                        break

            # ── Long functions (> 30 lines) ────────────────────────────
            if isinstance(node, ast.FunctionDef):
                start = node.lineno
                end = max(
                    (getattr(n, "lineno", start) for n in ast.walk(node)),
                    default=start
                )
                if (end - start) > 30:
                    suggestions.append(
                        f"  ℹ️  Function `{node.name}` spans ~{end - start} lines — "
                        "consider splitting into smaller functions"
                    )

        if not suggestions:
            return AgentResponse(
                agent_name=self.NAME,
                result="✅ No optimization issues found."
            )

        return AgentResponse(
            agent_name=self.NAME,
            result="\n".join(suggestions)
        )
