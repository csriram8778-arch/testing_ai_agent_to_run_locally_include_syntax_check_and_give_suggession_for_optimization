# 🤖 Multi-Agent AI Code Analyzer

A local AI-powered code review system with 5 specialized agents for syntax checking, optimization, unit test generation, and merge conflict resolution.

---

## 🧠 Agents

| Agent | Responsibility |
|-------|---------------|
| `COORDINATOR` | Analyzes input, assigns tasks to agents |
| `SYNTAX_CHECK_AGENT` | Detects syntax errors, suggests minimal fixes |
| `OPTIMIZATION_AGENT` | Flags performance and readability issues |
| `UNIT_TEST_AGENT` | Generates `pytest` test cases from functions |
| `MERGE_CONFLICT_AGENT` | Detects and resolves Git merge conflicts |

---

## 🚀 Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/csriram8778-arch/testing_ai_agent_to_run_locally_include_syntax_check_and_give_suggession_for_optimization.git
cd testing_ai_agent_to_run_locally_include_syntax_check_and_give_suggession_for_optimization
```

### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Add your API key
```bash
cp .env.example .env
# Edit .env and add: ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 5. Run
```bash
python main.py
```

---

## 📁 Project Structure

```
├── agents/
│   ├── coordinator.py
│   ├── syntax_check_agent.py
│   ├── optimization_agent.py
│   ├── unit_test_agent.py
│   └── merge_conflict_agent.py
├── core/
│   ├── task_model.py
│   └── output_formatter.py
├── tests/
│   └── sample_code/
├── main.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 🧪 Run Tests

```bash
pytest tests/ -v
```

---

## 📝 Example Usage

Paste any Python code when prompted, type `END` to submit:

```
Paste your code (type END on a new line when done):
def add(a, b)
    return a + b
END
```

**Output:**
```
[AGENT_RESPONSE]
Agent: SYNTAX_CHECK_AGENT
Result: Line 1: SyntaxError — expected ':'

[FINAL_OUTPUT]
Suggested Next Steps:
  1. Fix syntax errors before proceeding
  2. Run: pytest tests/
```

---

## 🤝 Contributing

1. Fork this repo
2. Create a branch: `git checkout -b feature/your-feature`
3. Commit: `git commit -m "feat: describe your change"`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

See [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) for the full step-by-step guide.

---

## 🔑 Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key — get one at https://console.anthropic.com |

---

## 📦 Requirements

- Python 3.9+
- See `requirements.txt` for full package list

---

## 📄 License

MIT — feel free to use, modify, and distribute.
