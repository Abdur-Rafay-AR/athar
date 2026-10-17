# Athar (أثر) · System Design & Architecture

**Athar** (Arabic: *أثر*, meaning *trace*, *mark*, or *footprint*) is an open-source, local-first time-travel debugger and observability engine built specifically for multi-agent Large Language Model (LLM) architectures.

---

## 1. High-Level Architecture

Athar operates as an offline-first, zero-vendor-lock-in system structured into three distinct tiers:

```text
+------------------------------------------------------------------------+
|                          Host Agent Application                        |
|        (Raw Python Loops, AutoGen, LangChain, Crucible, CrewAI)        |
+-----------------------------------+------------------------------------+
                                    |
            instrumentation via @traced / TracerContext
                                    v
+------------------------------------------------------------------------+
|                          Athar SDK Engine                              |
|  - Thread-safe & Async ContextVar tracking (parent-child call tree)    |
|  - Deterministic SHA-256 step content hashing (dedup & replay checks)  |
|  - Latency stopwatch and token / cost accounting                       |
+-----------------------------------+------------------------------------+
                                    |
                          non-blocking WAL writes
                                    v
+------------------------------------------------------------------------+
|                      Local Storage Layer (SQLite + WAL)                |
|  - Write-Ahead Logging (WAL) for concurrent agent execution & UI reads |
|  - Structured relational schema: traces, nodes, branches               |
+-----------------------------------+------------------------------------+
                                    |
                           RESTful polling / SSE
                                    v
+------------------------------------------------------------------------+
|                     Athar Presentation Layer (Web UI)                  |
|  - FastAPI asynchronous backend server                                 |
|  - Dark-mode responsive DAG explorer with interactive timeline         |
|  - Step inspector with syntax-highlighted I/O payloads                 |
|  - Interactive "Fork & Replay" state mutation engine                   |
+------------------------------------------------------------------------+
```

---

## 2. Core Subsystems

### 2.1 The Instrumentation SDK (`athar.core.tracer`)

The SDK provides non-invasive hooks for capturing function executions:

*   **Decorator (`@traced`)**: Can wrap both synchronous and asynchronous functions. Captures runtime arguments, keyword parameters, return values, raised exceptions, and wall-clock latency.
*   **Session Scoping (`TracerContext`)**: Allows bundling an entire agent run or loop inside a single trace session with unique metadata and naming.
*   **Context Chaining (`contextvars`)**: Tracks execution hierarchy without modifying agent signatures. Nested tool calls within an orchestrator agent automatically record the caller as `parent_node_id`.
*   **Idempotent Content Hashing**: Computes SHA-256 hashes over normalized JSON inputs and outputs:
    $$\text{step\_hash} = \text{SHA256}(\text{input\_json} \parallel \text{output\_json})$$

### 2.2 Local Storage Engine (`athar.storage.sqlite_store`)

Athar avoids cloud lock-in by using SQLite configured for high-concurrency workloads:

*   `PRAGMA journal_mode=WAL`: Permits concurrent readers (Web UI) and writers (agent processes) without database table locks.
*   `PRAGMA synchronous=NORMAL`: Provides fast write performance while preserving database integrity.

#### Schema

```sql
CREATE TABLE traces (
    trace_id TEXT PRIMARY KEY,
    name TEXT,
    status TEXT DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT
);

CREATE TABLE nodes (
    node_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    parent_node_id TEXT,
    branch_id TEXT DEFAULT 'main',
    func_name TEXT NOT NULL,
    input_data TEXT,
    output_data TEXT,
    state_snapshot TEXT,
    cost REAL DEFAULT 0.0,
    latency REAL DEFAULT 0.0,
    step_hash TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(trace_id) REFERENCES traces(trace_id) ON DELETE CASCADE
);
```

### 2.3 Time-Travel Engine (Fork & Replay)

When an agent deviates from its intended trajectory (e.g., a hallucinated tool response at step 4 in a 10-step chain), Athar allows forking from that specific node:

1. **Snapshot Retrieval**: Fetches the state snapshot and inputs at `node_id`.
2. **State Mutation**: The user injects corrected state or modified outputs in the UI or via API.
3. **Branching**: Athar registers a new `branch_id` linked to the same parent node.
4. **Replay Execution**: The agent continues forward from the fork point with the mutated inputs. Previous steps (1 through 3) are never re-executed, saving tokens, time, and API cost.

---

## 3. UI and Presentation Tier

The Web UI is delivered directly through FastAPI:

*   **Timeline View**: Visual representation of sequential and branched steps.
*   **Node Inspector**: Full inspection of inputs, outputs, errors, latency, and costs.
*   **State Editor**: In-browser JSON editor to trigger fork-and-replay runs.
*   **Sample Seed Engine**: Instant demonstration generator for onboarding and testing.

---

## 4. Extensibility & Integrations

Athar is designed to plug directly into agent frameworks:

*   **Raw Python Agents**: Direct decoration with `@traced`.
*   **Crucible Framework**: Dedicated `CrucibleAdapter` automatically wrapping agent `act()` / `run()` methods.
*   **LangChain / AutoGen / CrewAI**: Wrappable at callback or tool dispatch boundaries.
