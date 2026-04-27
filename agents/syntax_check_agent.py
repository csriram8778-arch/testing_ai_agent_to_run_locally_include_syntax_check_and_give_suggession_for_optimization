import ast
from io import StringIO
from core.task_model import AgentResponse


class SyntaxCheckAgent:
    NAME = "SYNTAX_CHECK_AGENT"

    def run(self, code: str) -> AgentResponse:
        errors = []

        # ── 1. AST parse: catches hard syntax errors ──────────────────
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(
                f"  [SyntaxError] Line {e.lineno}: {e.msg}\n"
                f"  Fix → Check for missing ':', ')', or ',' near that line."
            )
            # If AST fails, skip deeper checks — code won't parse
            return AgentResponse(
                agent_name=self.NAME,
                result="\n".join(errors)
            )

        # ── 2. Pyflakes: catches undefined names, unused imports ───────
        try:
            import pyflakes.api
            import pyflakes.reporter

            warning_lines = []

            class _Collector(pyflakes.reporter.Reporter):
                def unexpectedError(self, filename, msg):
                    warning_lines.append(f"  [Unexpected] {msg}")

                def syntaxError(self, filename, msg, lineno, offset, text):
                    warning_lines.append(
                        f"  [SyntaxError] Line {lineno}: {msg}"
                    )

                def flake(self, message):
                    warning_lines.append(f"  [Warning] {message}")

            reporter = _Collector(StringIO(), StringIO())
            pyflakes.api.check(code, "<string>", reporter=reporter)
            errors.extend(warning_lines)

        except ImportError:
            errors.append(
                "  [Info] pyflakes not installed. "
                "Run: pip install pyflakes"
            )

        # ── 3. Extra manual checks ─────────────────────────────────────
        tree = ast.parse(code)
        for node in ast.walk(tree):
            # Bare except
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                errors.append(
                    "  [Warning] Bare `except:` found — "
                    "catch a specific exception (e.g. Exception as e)"
                )
            # Print used instead of logging
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "print":
                    errors.append(
                        f"  [Info] `print()` detected at line "
                        f"{node.lineno} — consider using logging module"
                    )

        if not errors:
            return AgentResponse(
                agent_name=self.NAME,
                result="✅ No syntax errors or warnings detected."
            )

        return AgentResponse(
            agent_name=self.NAME,
            result="\n".join(errors)
        )
