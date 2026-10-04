# Agent Tracer System Design

## 1. High-Level Architecture

Agent Tracer is designed as a localized, offline-first debugging framework for Large Language Model (LLM) agents. The system utilizes a three-tier architecture:

1.  **Instrumentation Layer (SDK):** A lightweight Python package that wraps execution contexts, capturing LLM queries, tool invocations, and state mutations.
2.  **Storage Layer (SQLite):** A highly concurrent local database leveraging Write-Ahead Logging (WAL) to persist tracing trees and node hashes.
3.  **Presentation Layer (Web UI):** A FastAPI backend paired with a React frontend to visualize directed acyclic graphs (DAGs) of execution paths and facilitate the "fork and replay" mechanism.

## 2. Core Components

### 2.1 The Trace SDK

The SDK provides both a decorator (`@traced`) and a context manager (`TracerContext`) for flexible integration. 

*   **Node Hashing:** Each step in the trace generates a SHA-256 hash based on its inputs, parent state, and function signature. This guarantees idempotent replays.
*   **Asynchronous Logging:** Employs a non-blocking queue (`asyncio.Queue`) for background database writes, ensuring that agent performance is not bottlenecked by I/O.
*   **Adapter Pattern:** Pluggable adapters allow seamless integration with frameworks like LangChain, AutoGen, and Crucible.

### 2.2 Storage Engine

The database schema models execution as a tree:

*   `Traces`: Represents a full agent session.
*   `Nodes`: Represents an individual step (LLM call, tool execution). Contains `node_id`, `trace_id`, `parent_node_id`, `input_data`, `output_data`, `state_snapshot`, `cost`, `latency`.
*   `Branches`: Tracks divergence points when a user initiates a "fork and replay".

WAL mode is strictly enforced to handle simultaneous reads from the Web UI and writes from the running agent.

### 2.3 Execution Engine (Fork & Replay)

When a user edits state at a specific node and initiates a replay, the system performs the following:
1.  Retrieves the complete state up to the fork point.
2.  Injects the modified state.
3.  Spawns a new isolated branch.
4.  Re-executes the agent loop from the modified node onward.

### 2.4 Web Interface

*   **Backend (FastAPI):** Serves RESTful endpoints for trace retrieval, diff calculation, and replay invocation.
*   **Frontend (React):** Features a timeline scrubber, side-by-side branch diff viewer, and a Monaco-based JSON editor for state modification.

## 3. Data Flow Diagram

1.  **Agent Execution:** User agent code calls a wrapped function.
2.  **Capture:** The SDK serializes the input and takes a shallow copy of the state.
3.  **Execution:** The original function executes.
4.  **Completion:** Output and latency are recorded. The result is dispatched to the async write queue.
5.  **Persistence:** The worker thread writes the node to SQLite.
6.  **Visualization:** The UI polls the local API (or uses WebSockets) to update the timeline.

## 4. Future Extensibility

*   **Custom Storage Backends:** Interface segregation allows swapping SQLite for Postgres in team environments.
*   **Automated Anomaly Detection:** Potential integration of local embeddings to automatically flag divergent or failing branches.
