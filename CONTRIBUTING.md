# Contributing to Athar (أثر)

Thank you for your interest in contributing to **Athar**! We are building a local-first, time-travel debugger and observability engine for multi-agent LLM systems.

Whether you are fixing a bug, adding an adapter for an agent framework, improving the web UI, or writing documentation, your contributions are welcome.

---

## 🛠️ Development Environment Setup

### 1. Prerequisites
- **Python**: `>=3.9` (Python 3.9, 3.10, 3.11, or 3.12).
- **Git**: Installed and configured.

### 2. Clone the Repository & Create a Virtual Environment

```bash
# Clone your fork
git clone https://github.com/Abdur-Rafay-AR/athar.git
cd athar

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Linux / macOS:
source venv/bin/activate
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Windows (Command Prompt):
.\venv\Scripts\activate.bat
```

### 3. Install Editable Package with Dev Dependencies

```bash
pip install -e ".[dev]"
```

This installs:
- Core dependencies: `fastapi`, `uvicorn`, `pydantic`.
- Development & test dependencies: `pytest`, `httpx`, `build`, `twine`.

---

## 🧪 Running Tests

Athar maintains a clean, dependency-light automated test suite under `tests/`.

Run the test suite using Python's standard `unittest`:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

Or run with `pytest`:
```bash
pytest
```

Ensure all tests pass before submitting a pull request.

---

## 🚀 Running the Local UI Server

To start the local UI and API server during development:

```bash
# Start server on default port 4173
athar

# Or with custom port, host, and database file
athar --port 4173 --host 127.0.0.1 --db ./dev_traces.db
```

Then visit **[http://localhost:4173](http://localhost:4173)** in your browser.

---

## 🎯 Curated Good First Issues

If you're looking for an actionable way to contribute, these well-scoped issues are ideal starting points:

### Issue #1: CLI Trace Export (`athar export`)
- **Description**: Add a subcommand `athar export --trace-id <id> --format <json|otel>` to dump recorded traces from SQLite into standard JSON or OpenTelemetry-compatible span hierarchies.
- **Key files**: `src/athar/ui/app.py`, `src/athar/storage/sqlite_store.py`.
- **Difficulty**: Beginner-Friendly.

### Issue #2: Dedicated AutoGen Adapter
- **Description**: Implement `AtharAutoGenAdapter` in `src/athar/adapters/autogen.py` that hooks into Microsoft AutoGen's `ConversableAgent.register_reply` or message hook system to automatically trace multi-agent dialogues.
- **Key files**: `src/athar/adapters/`, `tests/test_autogen_adapter.py`.
- **Difficulty**: Intermediate.

### Issue #3: UI Timeline Search & Filter Bar
- **Description**: In `src/athar/ui/static/index.html`, add a search input above the timeline cards that filters nodes by function name, branch name, or execution errors in real-time.
- **Key files**: `src/athar/ui/static/index.html`.
- **Difficulty**: Beginner-Friendly.

### Issue #4: Side-Effect Dry-Run Warning for Replay
- **Description**: Add an `is_idempotent=False` flag to `@traced` to identify functions that cause external side effects (e.g., sending emails, database mutations). Display a confirmation prompt in the UI Step Inspector before replaying non-idempotent nodes.
- **Key files**: `src/athar/core/tracer.py`, `src/athar/core/replayer.py`, `src/athar/ui/static/index.html`.
- **Difficulty**: Intermediate.

---

## 📋 Pull Request & Code Guidelines

1. **Branch Naming**:
   - `feat/feature-name` for new capabilities.
   - `fix/bug-description` for bug fixes.
   - `adapter/framework-name` for new agent adapters.
   - `docs/topic` for documentation improvements.
2. **Core Decorator Lightness**:
   - Keep `@traced` lightweight and non-blocking. Never add synchronous network calls inside `@traced`.
3. **Storage Engine Integrity**:
   - Ensure SQLite WAL mode (`PRAGMA journal_mode=WAL;`) is preserved. Never add hard external database dependencies.
4. **Commit Messages**:
   - Write clear, imperative commit messages (e.g., `feat: add autogen adapter callback handler`, `fix: handle None parent_run_id in langchain adapter`).
