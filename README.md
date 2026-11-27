<div align="center">

  <img src="assets/logo-banner.svg" alt="Athar Banner" width="720" />

  <br /><br />

  <h1>Athar (أثر)</h1>

  <p><b>A local-first, time-travel debugger for multi-agent LLM systems.</b></p>
  <p>Record an agent execution. Inspect what happened. Change a state. Replay from that point.</p>

  [![PyPI version](https://img.shields.io/pypi/v/athar.svg?color=00D6A3)](https://pypi.org/project/athar/)
  [![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
  [![Tests](https://img.shields.io/badge/tests-23%20passed-00D6A3.svg)](tests/)
  [![Storage: SQLite WAL](https://img.shields.io/badge/storage-SQLite%20WAL-101820.svg)](#architecture)
  [![License: MIT](https://img.shields.io/badge/license-MIT-00D6A3.svg)](LICENSE)
  [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

  <br />

  <pre><code>pip install athar</code></pre>

  <p align="center">
    <a href="#10-second-summary">Summary</a> &bull;
    <a href="#the-problem-cascading-multi-agent-failures">The Problem</a> &bull;
    <a href="#how-athar-works">How It Works</a> &bull;
    <a href="#quick-start">Quick Start</a> &bull;
    <a href="#real-world-example-debugging-a-multi-agent-loop">Real-World Example</a> &bull;
    <a href="#architecture">Architecture</a> &bull;
    <a href="#supported-integrations">Integrations</a> &bull;
    <a href="#comparison-with-existing-tools">Comparison</a> &bull;
    <a href="#contributing-and-good-first-issues">Contributing</a>
  </p>

  <br />

  <img src="assets/demo.gif" alt="Athar Time-Travel Debugger Demo" width="100%" />

</div>

---

## 10-Second Summary

Debugging multi-agent systems is difficult because **errors compound**. When an agent loop fails on step 12 of 30, re-running from scratch burns API tokens, wastes minutes waiting for prior steps to complete, and often fails to reproduce the issue due to LLM stochasticity.

**Athar** solves this with local-first **time-travel debugging**:

- **Record**: Captures prompts, tool calls, return values, state snapshots, latency, and SHA-256 step hashes to a local SQLite database using Write-Ahead Logging (WAL).
- **Inspect**: Scrub through the execution timeline in a dark-mode web UI with zero frontend build dependencies (no npm, no node_modules, zero browser-side libraries).
- **Modify**: Edit prompts, mock tool outputs, or tweak agent state at any step.
- **Fork & Replay**: Fork execution at any step to re-execute with mutated arguments or state. **Prior steps are never re-executed**, saving their execution time and token costs.
- **Diff**: Compare branches side-by-side with delta cost, delta latency, and unified output diffs.

> **Local-first telemetry.** Athar transmits zero telemetry, requires no accounts, and connects to no external database servers. All trace data remains on your local machine in SQLite. (Note: Network calls made directly by your own agent or LLM providers still communicate with their respective API endpoints).

---

## The Problem: Cascading Multi-Agent Failures

Consider a real-world multi-agent workflow: an orchestrator agent delegates tasks to a web search tool, a code interpreter, and a report synthesizer across 30 sequential steps.

```
Step 1 (Plan) ──> Step 2 (Search) ──> ... ──> Step 12 (Tool Call) ──> Step 13 (Corrupted) ──> Step 30 (Failure)
```

At **Step 12**, the search tool returns a malformed schema or an ambiguous fact. Steps 13 through 30 proceed to hallucinate and compound the error.

```mermaid
flowchart TD
    subgraph Traditional["Traditional Debugging: Re-running From Scratch"]
        A1["Step 1: Planning"] --> A2["Step 2: Search Tool"]
        A2 --> A3["Step 12: Tool Malfunction"]
        A3 --> A4["Steps 13-30: Compounded Hallucinations"]
        A4 -.->|"Add print statements & rerun"| R1["Step 1: Re-executed (High Cost)"]
        R1 --> R2["Step 2: Re-executed (High Cost)"]
        R2 --> R3["Step 12: Stochastic LLM behaves differently"]
    end

    subgraph Athar["Athar: Time-Travel Fork & Replay"]
        B1["Step 1: Planning"] --> B2["Step 2: Search Tool"]
        B2 --> B3["Step 12: Tool Malfunction"]
        B3 --> B4["Steps 13-30: Preserved in History"]
        B3 ==>|"1. Mutate Input / State"| F1["Step 12 (Forked): Corrected Query"]
        F1 ==>|"2. Replay Forward Only"| F2["Step 13 (Replay): Clean Context"]
    end
```

### The Traditional Debugging Experience
1. **Wasted Cost & Latency**: To test a fix at Step 12, you must re-run Steps 1 through 11 every single time. In multi-step agent pipelines, re-running from scratch burns compounding API tokens and minutes of waiting on each iteration.
2. **LLM Stochasticity**: Even at `temperature=0`, non-deterministic provider routing and concurrent tool outputs mean re-running from scratch often fails to reproduce the exact state that caused the bug.
3. **Observability vs. Local Debugging**: Most LLM observability platforms (such as LangSmith, Langfuse, and Arize Phoenix) are designed primarily for cloud-scale tracing, evaluation datasets, and production monitoring. During active local development, however, developers need immediate time-travel debugging: click a step, edit inputs, and re-execute callables directly in the local development environment without spinning up external infrastructure.

---

## How Athar Works

Athar establishes a 5-stage lifecycle for agent execution:

```mermaid
flowchart LR
    R["1. RECORD<br/>(@traced / Callbacks)"] --> I["2. INSPECT<br/>(Timeline & Inspector)"]
    I --> M["3. MODIFY<br/>(JSON State Editor)"]
    M --> F["4. FORK<br/>(Branch in DAG)"]
    F --> P["5. REPLAY<br/>(Re-execute Step)"]
```

1. **RECORD**: Wrap Python functions with `@traced` or pass `AtharCallbackHandler` to LangChain or LangGraph. Execution steps, inputs, outputs, errors, latency, and SHA-256 content hashes are written to local SQLite via thread-safe WAL mode.
2. **INSPECT**: Start `athar` and open `http://localhost:4173`. Scrub through chronological execution cards or examine the parent-child DAG hierarchy.
3. **MODIFY**: Click the problematic step. In the Step Inspector, edit the input arguments, tool payload, or state snapshot in the JSON editor.
4. **FORK**: Athar creates a new execution branch (for example, `branch_replay_1`) linked to the fork point. Historical traces remain immutable and intact.
5. **REPLAY**:
   - **Live Callable Replay**: If the step function is registered in the active Python session, Athar re-invokes the real callable with mutated arguments, measuring true output and latency.
   - **State Mutation Mode**: If inspecting offline or across process restarts, Athar records a state mutation snapshot branch for downstream inspection.
   - **Structured Branch Diff**: Compare the original and forked branches side-by-side with delta cost, delta latency, and unified text and JSON diffs.
   *(Note: Current releases re-execute the selected step; automated cascading replay across downstream steps is planned for v0.4).*

---

## Quick Start

### Requirements
- **Python**: `>=3.9` (tested on 3.9, 3.10, 3.11, and 3.12).
- **Operating System**: macOS, Linux, or Windows.

### 1. Installation

**Stable Release (PyPI)**:
```bash
pip install athar
```
*Installs the core tracing SDK (`@traced`, `TracerContext`), SQLite WAL store, and local debugger UI.*

**Latest Development Build (GitHub `main`)**:
To install the latest features (Structured Branch Diff, universal LangChain/LangGraph adapter, and trace/branch deletion):
```bash
pip install git+https://github.com/Abdur-Rafay-AR/athar.git
```

Or clone for local development:
```bash
git clone https://github.com/Abdur-Rafay-AR/athar.git
cd athar
pip install -e ".[dev]"
```

### 2. Minimal Working Example

Wrap your agent or tool functions with `@traced`. The decorator works seamlessly on both **async** and **sync** functions:

```python
import asyncio
from athar import traced, TracerContext

@traced
async def search_tool(query: str):
    # Simulates an external API or retrieval step
    await asyncio.sleep(0.1)
    return {"results": f"Latest data for: {query}"}

@traced
async def research_agent(topic: str):
    data = await search_tool(topic)
    res = data["results"]
    return f"Synthesized report based on {res}"

async def main():
    # Bundle execution inside a named trace session
    async with TracerContext(name="Market Intelligence Run"):
        report = await research_agent("Autonomous Coding Agents")
        print("Done:", report)

if __name__ == "__main__":
    asyncio.run(main())
```

Run the script:
```bash
python my_agent.py
```

### 3. Open the Athar Debugger UI

Start the local server:
```bash
athar
```
*(Or specify custom options: `athar --port 4173 --host 127.0.0.1 --db ./my_traces.db`).*

Visit **[http://localhost:4173](http://localhost:4173)** in your browser.

> **Tip**: If you haven't run any code yet, click the **"Seed Sample Trace"** button in the top navigation bar to populate a realistic multi-agent research workflow.

---

## Real-World Example: Debugging a Multi-Agent Loop

Here is how you debug an autonomous research workflow when an intermediate tool returns insufficient data:

```python
from athar import traced, TracerContext

@traced(cost=0.0005)
def market_search(query: str):
    # Suppose this initially returns an unhelpful generic response
    return {"status": "ok", "summary": "Generic market overview (no quantitative data)"}

@traced(cost=0.0020)
def synthesis_agent(context: dict):
    # Fails or warns if quantitative metrics are missing
    if "metrics" not in context.get("summary", ""):
        return "Warning: Insufficient data to synthesize definitive report."
    return "Final report: Enterprise velocity increased by 38%."

def run_pipeline():
    with TracerContext(name="Quarterly Velocity Analysis"):
        search_output = market_search("Developer productivity benchmarks")
        report = synthesis_agent(context=search_output)
        print("Pipeline Result:", report)

if __name__ == "__main__":
    run_pipeline()
```

### What Happens in Athar:
1. Run the script. The synthesizer outputs: `Warning: Insufficient data to synthesize definitive report.`
2. Launch `athar` and open `http://localhost:4173`.
3. Select `synthesis_agent` (the step that generated the warning) in the timeline.
4. In the Step Inspector, edit the input `context` to test the synthesizer logic with corrected data:
   ```json
   {
     "context": {
       "summary": "Empirical study: metrics demonstrate 38% velocity increase across 45 teams"
     }
   }
   ```
5. Click **"Execute Fork & Replay"**.
6. Because `synthesis_agent` is registered in memory, Athar re-runs `synthesis_agent (forked)` with the corrected input, immediately producing `"Final report: Enterprise velocity increased by 38%."` without re-running `market_search`.
7. Click **"Compare Branches"** to view the structured diff between the warning output on `main` and the successful report on the forked branch, along with delta latency and cost.

*Table: Debugging workflow comparison (Illustrative scenario).*

| Dimension | Without Athar | With Athar |
| :--- | :--- | :--- |
| **Token Cost** | Re-spends tokens for all steps 1..N | **0 tokens** on prior steps (only replayed step runs) |
| **Iteration Latency** | Full pipeline re-run duration | Immediate execution of forked step |
| **Reproducibility** | Stochastic (LLM outputs drift on re-runs) | Deterministic state injection for target step |
| **Execution History** | Overwrites console logs | Immutable DAG branches in SQLite |

---

## Architecture

Athar is engineered as an offline-first system structured into three tiers:

```mermaid
flowchart TD
    subgraph HostApp["Host Agent Application"]
        Agent["Agent Orchestrator / Tools"]
    end

    subgraph AtharSDK["Athar Core SDK"]
        T["@traced / TracerContext"]
        H["SHA-256 Hasher"]
        CTX["ContextVar Call Tree Tracker"]
        REG["FunctionRegistry"]
    end

    subgraph Storage["Local Storage Layer"]
        DB[("SQLite WAL Store<br/>agent_traces.db")]
    end

    subgraph Presentation["Presentation Tier (FastAPI & Web UI)"]
        API["FastAPI REST API"]
        UI["Interactive Timeline & Step Inspector"]
        REP["execute_replay Runtime"]
        DIFF["compare_branches Engine"]
    end

    HostApp -->|wraps calls| AtharSDK
    AtharSDK -->|non-blocking WAL writes| Storage
    Storage <-->|reads & branches| API
    API --> UI
    UI -->|triggers replay| REP
    REP -.->|re-executes live callable| REG
    REP -->|stores branch node| Storage
    UI -->|requests diff| DIFF
```

### Subsystem Details

- **Instrumentation Engine (`athar.core.tracer`)**:
  - Transparently intercepts sync and async functions without modifying signatures or return types.
  - Automatically registers callables in `FunctionRegistry` for live re-execution.
  - Uses Python `contextvars` (`_active_trace_id`, `_active_parent_node_id`) to track parent-child call trees across nested agent calls and async task boundaries without manual span propagation.
- **Deterministic Step Fingerprinting**:
  - Computes a canonical SHA-256 hash over normalized inputs and outputs:
    $$\text{step\_hash} = \text{SHA256}(\text{canonical\_json}(\text{inputs}) \parallel \text{canonical\_json}(\text{outputs}))$$
  - Provides an immutable content hash per step to detect payload divergence between baseline and replayed branches.
- **Concurrent SQLite Storage (`athar.storage.sqlite_store`)**:
  - `PRAGMA journal_mode=WAL;`: Allows concurrent readers (such as the Web UI) to operate simultaneously without blocking or being blocked by writing operations. While SQLite serializes writes (one writer at a time), concurrent write requests are managed via a 10-second busy timeout.
  - `PRAGMA synchronous=NORMAL;`: Avoids costly fsync calls on every commit in WAL mode, significantly improving write throughput while ensuring structural database integrity across application crashes.
  - Thread-local connection management: Isolates SQLite connection objects per thread to prevent cross-thread handle sharing.
- **Dynamic Replay Engine (`athar.core.replayer`, `athar.core.registry`)**:
  - Distinguishes between **Live Callable Replay** (active in-memory Python function re-invoked with mutated inputs) and **State Snapshot Forking** (offline inspection and annotation).
- **Structured Branch Diffing (`athar.core.diff`)**:
  - Traverses the execution graph to detect fork points.
  - Computes exact cost differentials ($\Delta\text{cost} = \text{cost}_B - \text{cost}_A$) and latency differentials ($\Delta\text{latency} = \text{latency}_B - \text{latency}_A$).
  - Produces unified diffs of input and output payloads using standard `difflib`.

---

## Supported Integrations

### 1. Raw Python & Async Functions
Works with any custom agent loop, LangChain component, AutoGen step, or CrewAI task:

```python
from athar import traced, TracerContext

@traced(name="Summarizer", cost=0.001)
def summarize(text: str):
    return f"Summary of {len(text)} chars"

with TracerContext(name="Custom Loop"):
    summarize("Hello world")
```

### 2. LangChain & LangGraph Universal Callback Handler
Athar provides a first-class `AtharCallbackHandler` (inheriting from `BaseCallbackHandler`):

```python
from athar import AtharCallbackHandler

handler = AtharCallbackHandler(trace_name="LangChain Agent Run")

# Pass to any chain, graph, or agent run:
chain.invoke({"input": "Analyze market trends"}, config={"callbacks": [handler]})
```

The callback handler automatically captures:
- Chain invocations (`on_chain_start`, `on_chain_end`, `on_chain_error`)
- Tool calls and outputs (`on_tool_start`, `on_tool_end`, `on_tool_error`)
- LLM prompts, token usages, and costs (`on_llm_start`, `on_llm_end`)
- Hierarchical parent-child relationship tracking via LangChain `parent_run_id`

### 3. Crucible Multi-Agent Engine
Athar includes dedicated support for the [Crucible](https://github.com/Abdur-Rafay-AR/crucible) multi-agent framework:

```python
from athar import CrucibleAdapter

agent = CrucibleAdapter.wrap_agent(my_crucible_agent)
agent.run()
```

---

## Design Decisions

| Decision | Why Athar Does It | Trade-Off |
| :--- | :--- | :--- |
| **Local-First Storage (SQLite WAL)** | Zero SaaS dependencies, no telemetry, no external database setup (Docker/PostgreSQL). | Traces reside on your local machine; team collaboration requires sharing or exporting the `.db` file. |
| **Deterministic SHA-256 Hashes** | Verifies whether a replayed step altered inputs or outputs compared to baseline execution. | Requires JSON serialization and hash calculation for each traced step. |
| **Immutability of History** | Replaying never overwrites historical execution nodes; it creates new branch records referencing the parent. | Database file grows with each branch until cleaned or deleted. |
| **Dual Replay Modes** | Enables live Python execution during active sessions, while gracefully supporting offline trace inspection. | Re-executing live code across process restarts requires the host process to maintain registered callables. |

---

## Comparison With Existing Tools

| Capability | Athar | LangSmith | Langfuse | Arize Phoenix | LangGraph Studio |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Primary Focus** | **Local time-travel debugging & step replay** | Production tracing & evaluation | Open-source observability & metrics | LLM evaluation & trace analysis | Visual graph IDE & checkpoint time travel |
| **Deployment Model** | **Local-first (embedded SQLite file)** | SaaS (Cloud) / Enterprise | Self-hosted (Docker) or Cloud | Local (`pip`) or Cloud | Desktop app (Docker / LangGraph CLI) |
| **Debugger Telemetry** | **Zero telemetry from Athar** | Sends trace data to cloud | Stored in self-hosted or cloud DB | Stored locally in Phoenix DB or cloud | Local LangGraph server or cloud |
| **State Mutation & Replay** | **UI step mutation + live Python re-execution** | Prompt playground testing | Prompt playground testing | Experiment evaluation runs | Checkpoint state editing & node re-runs |
| **Execution Target** | **Replays selected step (skips prior steps)** | Isolated prompt re-run | Isolated prompt re-run | Evaluation dataset run | Graph resumption from checkpoint |
| **Structured Branch Diff** | **Built-in ($\Delta\text{cost}$, $\Delta\text{latency}$, step diffs)** | Run-to-run comparison | Trace-to-trace comparison | Experiment comparison | Per-checkpoint state inspection |
| **Infrastructure Overhead** | **Python package (`fastapi`, `uvicorn`, `pydantic`); zero frontend build tools** | API key & network | Docker (PostgreSQL + ClickHouse) | Local Python package (`arize-phoenix`) | Desktop App + Docker + LangGraph CLI |

---

## Current Limitations

To maintain technical credibility, we document our current constraints honestly:

1. **Single-Node Replay vs. Cascading Pipeline Execution**:
   Athar currently re-executes the selected step and logs the resulting branch node. In custom Python agent loops, automatic multi-step cascading replay requires orchestrator re-invocation. Full multi-step graph cascade replay is actively being implemented for v0.4.
2. **In-Memory Registry Scope**:
   Live Python callable re-execution requires the host process to have registered the function via `@traced` or `get_registry().register()`. If you restart your machine and inspect historical traces using standalone `athar`, Athar operates in **State Mutation Mode** (recording mutated state snapshots rather than executing arbitrary Python code in the server process).
3. **LLM Stochasticity**:
   Re-running an LLM step without setting `temperature=0` or enabling response caching will produce a stochastic completion. Athar records both the original and new outputs so you can compare differences directly.
4. **Side-Effecting Tools**:
   If an agent step performs destructive real-world side effects (for example, executing a financial transaction or sending an email), replaying that step will trigger the side effect again unless the tool is guarded or mocked.

---

## Roadmap

- [x] **v0.1.0 (PyPI Stable)**:
  - Local-first tracer SDK (`@traced`, `TracerContext`, contextvars call tree).
  - SQLite WAL persistence with concurrent reader support.
  - Baseline Web UI debugger with interactive timeline and "Seed Sample Trace" generator.
  - Crucible multi-agent adapter (`CrucibleAdapter`).
- [x] **v0.2.0-dev (Current GitHub `main` / Upcoming PyPI Release)**:
  - Side-by-side Structured Branch Diff visualizer ($\Delta\text{cost}$, $\Delta\text{latency}$, and unified text/JSON diffs).
  - Universal LangChain & LangGraph callback adapter (`AtharCallbackHandler`).
  - Time-travel fork & replay runtime (`execute_replay`) with in-memory `FunctionRegistry`.
  - Full trace and individual branch deletion controls in the Web UI and REST API.
- [ ] **v0.3.0 (Planned)**:
  - CLI trace export utilities (`athar export` for formatted JSON and OpenTelemetry).
  - Timeline search and tag filtering in the Web UI.
- [ ] **v0.4.0 (Planned)**:
  - Live trace streaming via Server-Sent Events (SSE) / WebSockets.
  - Automated multi-step cascading replay engine across downstream dependencies.
  - Side-effect dry-run guard (`@traced(is_idempotent=False)`).

---

## Contributing and Good First Issues

We welcome contributions from the community. Whether you want to add adapters for new frameworks, improve the web UI, or optimize SQLite storage, your help is appreciated.

### Quick Setup

```bash
# 1. Clone the repository
git clone https://github.com/Abdur-Rafay-AR/athar.git
cd athar

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install in editable mode with dev dependencies
pip install -e ".[dev]"

# 4. Run the test suite
python -m unittest discover -s tests -p "test_*.py"
```

### Curated Good First Issues

Looking for a place to start? Here are four high-impact, well-scoped tasks ready for contributors:

1. **[Issue #2: Add CLI Trace Export (`athar export`)](https://github.com/Abdur-Rafay-AR/athar/issues/2)**
   - *Goal*: Add a CLI flag to export recorded traces from SQLite to formatted JSON or OpenTelemetry trace format.
   - *Relevant files*: `src/athar/ui/app.py`, `src/athar/storage/sqlite_store.py`.
2. **[Issue #3: Native AutoGen Adapter](https://github.com/Abdur-Rafay-AR/athar/issues/3)**
   - *Goal*: Create `athar.adapters.autogen` to automatically wrap AutoGen's `ConversableAgent` message exchange loops.
   - *Relevant files*: `src/athar/adapters/`.
3. **[Issue #4: Timeline Text Search & Tag Filter in Web UI](https://github.com/Abdur-Rafay-AR/athar/issues/4)**
   - *Goal*: Add a search bar to the center timeline in `index.html` to filter cards by function name, branch name, or execution error.
   - *Relevant files*: `src/athar/ui/static/index.html`.
4. **[Issue #5: Side-Effect Dry-Run Guard for Replay](https://github.com/Abdur-Rafay-AR/athar/issues/5)**
   - *Goal*: Add a `@traced(is_idempotent=False)` parameter to warn users in the UI before replaying functions that perform destructive side effects.
   - *Relevant files*: `src/athar/core/tracer.py`, `src/athar/core/replayer.py`.

See [CONTRIBUTING.md](CONTRIBUTING.md) for full style guidelines, branch naming conventions, and testing practices.

---

## Meaning of "Athar"

**Athar** (أثر) is an Arabic word meaning **trace**, **imprint**, or **footprint**. In multi-agent AI systems, understanding the exact trace left behind by an agent's reasoning process is the key to deterministic reliability and time-travel interpretability.

---

## License and Community

Distributed under the [MIT License](LICENSE). Copyright © 2026 Abdur Rafay.

- **Found a bug?** Open an issue on [GitHub Issues](https://github.com/Abdur-Rafay-AR/athar/issues).
- **Have an idea?** Start a discussion or submit a Pull Request.
- **Enjoying Athar?** Consider [starring the repository](https://github.com/Abdur-Rafay-AR/athar) to support local-first developer tooling!
