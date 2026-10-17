# Contributing to Athar (أثر)

Thank you for your interest in contributing to Athar! We welcome issues, PRs, adapters for new agent frameworks, UI improvements, and documentation enhancements.

---

## 🛠️ Local Development Setup

### 1. Clone Repository & Setup Virtual Environment

```bash
git clone https://github.com/Abdur-Rafay-AR/athar.git
cd athar

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 2. Install Editable Package with Dev Dependencies

```bash
pip install -e ".[dev]"
```

---

## 🧪 Running Tests

Athar uses Python's standard `unittest` and `pytest`.

```bash
# Run using standard library unittest:
python -m unittest discover -s tests

# Or run with pytest:
pytest
```

---

## 🚀 Running the Local UI Server

To start the local UI and API server during development:

```bash
# Run Athar server
athar --port 4173

# Or on Windows using helper:
run-local.cmd
```

Then visit [http://localhost:4173](http://localhost:4173) in your browser.

---

## 📋 Pull Request Guidelines

1. **Branch Naming**: Use descriptive prefixes like `feat/`, `fix/`, `docs/`, `adapter/`.
2. **Tests**: Ensure any new features or bug fixes include corresponding unit tests under `tests/`.
3. **No Breaking Changes to Core Decorator**: Keep `@traced` lightweight and non-intrusive.
4. **Clean Commits**: Write clear, concise commit messages.
