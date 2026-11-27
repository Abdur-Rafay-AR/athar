# Changelog

All notable changes to **Athar** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.0] - 2026-03-15

### Added
- **Universal LangChain & LangGraph Adapter (`AtharCallbackHandler`)**:
  - Automatically captures chain start/end/error, tool calls, and LLM completions.
  - Extracts token usage statistics and cost estimations.
  - Tracks nested parent-child hierarchies via LangChain `parent_run_id`.
- **Crucible Multi-Agent Adapter (`CrucibleAdapter`)**:
  - Automatically wraps agent `act()` and `run()` execution loops.
- **Enhanced CLI**:
  - Added CLI options `--port`, `--host`, and `--db` for custom database routing.

---

## [0.2.0] - 2026-02-01

### Added
- **Semantic Branch Diff Engine (`compare_branches`)**:
  - Computes exact fork points between execution branches.
  - Measures cost differential ($\Delta\text{cost}$) and latency differential ($\Delta\text{latency}$).
  - Unified output diffing for JSON and text payloads across corresponding steps.
- **Branch Comparison Modal in Web UI**:
  - Interactive side-by-side diff view triggered when multiple branches exist in a trace.

---

## [0.1.0] - 2026-01-10

### Added
- **Core Instrumentation SDK (`@traced`, `TracerContext`)**:
  - Non-intrusive wrapping of synchronous and asynchronous Python functions.
  - Automatic call-tree tracking via Python `contextvars`.
  - Deterministic SHA-256 step content hashing over normalized JSON payloads.
- **Local Storage Layer (`TraceStore`)**:
  - SQLite backend configured with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`).
  - Thread-safe connection handling and structured schema for traces, nodes, and branches.
- **Time-Travel Fork & Replay Runtime (`execute_replay`)**:
  - `FunctionRegistry` for mapping function names to executable Python callables.
  - Live re-execution with mutated inputs for active processes.
  - State snapshot mutation fallback for offline traces.
- **Web UI & REST API (`athar.ui.app`)**:
  - FastAPI server serving responsive dark-mode Single Page Application.
  - Interactive timeline cards, step inspector, and "Seed Sample Trace" demo generator.
