import ast
from core.task_model import AgentResponse

_STDLIB = {
    "os", "sys", "re", "ast", "io", "json", "math", "time", "datetime",
    "collections", "itertools", "functools", "pathlib", "typing",
    "dataclasses", "abc", "copy", "string", "random", "hashlib",
    "threading", "subprocess", "logging", "unittest", "contextlib",
    "inspect", "importlib", "warnings", "traceback", "struct", "enum",
    "signal", "socket", "http", "urllib", "email", "html", "xml",
    "csv", "sqlite3", "shutil", "tempfile", "glob", "fnmatch",
    "argparse", "configparser", "pprint", "textwrap", "base64",
}


class CICDPipelineAgent:
    NAME = "CICD_PIPELINE_AGENT"

    def _detect_third_party_imports(self, tree: ast.AST) -> list[str]:
        seen = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    seen.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    seen.add(node.module.split(".")[0])
        return sorted(i for i in seen if i not in _STDLIB and not i.startswith("_"))

    def _detect_test_functions(self, tree: ast.AST) -> list[str]:
        return [
            n.name for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
        ]

    def _has_entry_point(self, tree: ast.AST) -> bool:
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test = node.test
                if (
                    isinstance(test, ast.Compare)
                    and isinstance(test.left, ast.Name)
                    and test.left.id == "__name__"
                ):
                    return True
        return False

    def _readiness_checklist(
        self,
        third_party: list[str],
        has_tests: bool,
        has_entry: bool,
    ) -> str:
        lines = [
            f"  {'✅' if has_tests  else '❌'} Test functions detected"
            + ("" if has_tests else " — add tests in tests/ folder"),
            f"  {'✅' if has_entry  else '⚠️ '} Entry point (if __name__ == '__main__')"
            + ("" if has_entry else " — not found"),
            f"  {'✅' if not third_party else '⚠️ '} Third-party dependencies: "
            + (", ".join(third_party) if third_party else "none detected"),
        ]
        if third_party:
            lines.append(
                f"  ⚠️  Ensure requirements.txt lists: {', '.join(third_party)}"
            )
        lines.append("  ℹ️  Save generated YAML to .github/workflows/ci.yml")
        return "\n".join(lines)

    def _generate_workflow(self, third_party: list[str], has_tests: bool) -> str:
        if third_party:
            install = (
                "      - name: Install dependencies\n"
                "        run: |\n"
                "          python -m pip install --upgrade pip\n"
                "          pip install -r requirements.txt"
            )
        else:
            install = (
                "      - name: Install base tools\n"
                "        run: |\n"
                "          python -m pip install --upgrade pip\n"
                "          pip install pyflakes pycodestyle pytest"
            )

        test_step = (
            "\n"
            "      - name: Run tests\n"
            "        run: pytest tests/ -v --tb=short"
            if has_tests else ""
        )

        return (
            "# Save as: .github/workflows/ci.yml\n"
            "name: CI Pipeline\n\n"
            "on:\n"
            "  push:\n"
            "    branches: [main, develop]\n"
            "  pull_request:\n"
            "    branches: [main]\n\n"
            "jobs:\n"
            "  ci:\n"
            "    runs-on: ubuntu-latest\n"
            "    strategy:\n"
            "      matrix:\n"
            '        python-version: ["3.11"]\n\n'
            "    steps:\n"
            "      - name: Checkout\n"
            "        uses: actions/checkout@v4\n\n"
            "      - name: Set up Python\n"
            "        uses: actions/setup-python@v5\n"
            "        with:\n"
            "          python-version: ${{ matrix.python-version }}\n\n"
            f"{install}\n\n"
            "      - name: Syntax check\n"
            "        run: python -m py_compile *.py\n\n"
            "      - name: Lint\n"
            "        run: python -m pyflakes .\n\n"
            "      - name: Style check\n"
            "        run: pycodestyle --max-line-length=120 ."
            f"{test_step}\n"
        )

    def run(self, code: str) -> AgentResponse:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return AgentResponse(
                agent_name=self.NAME,
                result="⚠️  Cannot generate pipeline — fix syntax errors first.",
            )

        third_party = self._detect_third_party_imports(tree)
        test_funcs  = self._detect_test_functions(tree)
        has_tests   = bool(test_funcs)
        has_entry   = self._has_entry_point(tree)

        checklist = self._readiness_checklist(third_party, has_tests, has_entry)
        workflow  = self._generate_workflow(third_party, has_tests)

        result = (
            "CI/CD Readiness Checklist:\n"
            f"{checklist}\n\n"
            "── Generated GitHub Actions Workflow ──────────────────\n"
            f"{workflow}"
        )
        return AgentResponse(agent_name=self.NAME, result=result)
