"""
Multi-Agent AI Code Analyzer
==============================
Run:  python main.py
      python main.py --file path/to/yourcode.py
"""

import sys
import os
import argparse
#from dotenv import load_dotenv
from agents.coordinator import Coordinator

#load_dotenv()


BANNER = """
╔════════════════════════════════════════════════════════════════════════════════╗
║                   🤖  Multi-Agent AI Code Analyzer                             ║
║  Agents: Syntax · Optimization · Tests · Conflicts · TestWriter · CI/CD        ║
╚════════════════════════════════════════════════════════════════════════════════╝
Commands:  paste code → type END    |    exit / quit
"""


def read_code_from_stdin() -> str:
    """Interactive multi-line input. User types END to submit."""
    print("\n📋 Paste your code below (type END on a new line to submit):\n")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip().upper() == "END":
            break
        if line.strip().lower() in ("exit", "quit"):
            print("\n👋 Goodbye!\n")
            sys.exit(0)
        lines.append(line)
    return "\n".join(lines)


def read_code_from_file(path: str) -> str:
    """Read code directly from a .py file."""
    if not os.path.exists(path):
        print(f"❌ File not found: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Agent AI Code Analyzer"
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        default=None,
        help="Path to a Python file to analyze (optional)"
    )
    args = parser.parse_args()

    print(BANNER)

    coordinator = Coordinator()

    if args.file:
        # ── File mode ─────────────────────────────────────────────────
        print(f"📂 Analyzing file: {args.file}\n")
        code = read_code_from_file(args.file)
        print(f"{'─' * 54}")
        result = coordinator.analyze(code)
        print(result)
    else:
        # ── Interactive loop ───────────────────────────────────────────
        while True:
            code = read_code_from_stdin()
            if not code.strip():
                print("⚠️  No code entered. Try again.\n")
                continue
            print(f"\n{'─' * 54}")
            result = coordinator.analyze(code)
            print(result)
            print("\n" + "═" * 54)
            print("Ready for next input. (type 'exit' to quit)")


if __name__ == "__main__":
    main()
