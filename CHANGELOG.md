# Changelog

All notable changes to **Athar** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] - (v0.2.0-dev on GitHub `main`)

### Added
- **Structured Branch Diff Engine (`compare_branches`)**:
  - Computes exact fork points between execution branches.
  - Measures cost differential ($\Delta\text{cost}$) and latency differential ($\Delta\text{latency}$).
  - Unified output diffing for JSON and text payloads across corresponding steps.
  - Interactive Branch Comparison Modal in the Web UI.
- **Universal LangChain & LangGraph Callback Adapter (`AtharCallbackHandler`)**:
  - Automatically captures chain invocations, tool calls, and LLM completions.
  - Extracts token usage statistics and cost estimations.
  - Tracks nested parent-child hierarchies via LangChain `parent_run_id`.
- **Trace & Branch Deletion Management**:
  - Added REST API endpoints `DELETE /api/traces/{trace_id}` and `DELETE /api/traces/{trace_id}/branches/{branch_id}`.
  - Added visual trash icon buttons to trace cards in sidebar and forked branches in inspector/diff modal.
- **Time-Travel Fork & Replay Runtime (`execute_replay`)**:
  - `FunctionRegistry` for mapping function names to executable Python callables.
  - Live re-execution with mutated inputs for active processes.
  - State snapshot mutation fallback for offline traces.
- **Enhanced CLI**:
  - Added CLI options `--port`, `--host`, and `--db` for custom database routing.

### Planned
- **Trace Export Subcommand (`athar export`)**: Export recorded traces to formatted JSON or OpenTelemetry trace format (Issue #2).
- **Native AutoGen Adapter (`athar.adapters.autogen`)**: Automatic wrapping of AutoGen conversational agents (Issue #3).
- **Timeline Search & Filter**: Filter timeline cards by function name, branch name, or execution error (Issue #4).
- **Side-Effect Dry-Run Guard**: Warn users before replaying non-idempotent functions (Issue #5).
- **Live Trace Streaming**: Server-Sent Events (SSE) / WebSockets for real-time trace streaming.
- **Cascading Multi-Step Replay**: Automated forward execution across multi-step agent graph dependencies.

---

## [0.1.0] - 2026-10-17

### Added
- **Core Instrumentation SDK (`@traced`, `TracerContext`)**:
  - Non-intrusive wrapping of synchronous and asynchronous Python functions.
  - Automatic call-tree tracking via Python `contextvars`.
  - Deterministic SHA-256 step content hashing over normalized JSON payloads.
- **Local Storage Layer (`TraceStore`)**:
  - SQLite backend configured with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) and `PRAGMA synchronous=NORMAL;`.
  - Thread-safe connection handling and structured schema for traces, nodes, and branches.
- **Framework Adapters**:
  - Crucible multi-agent adapter (`CrucibleAdapter`).
- **Web UI & REST API (`athar.ui.app`)**:
  - FastAPI server serving responsive dark-mode Single Page Application.
  - Interactive timeline cards, step inspector, and "Seed Sample Trace" demo generator.
  - CLI entrypoint (`athar`).
