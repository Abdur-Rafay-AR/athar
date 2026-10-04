# Agent Tracer

**A local-first, time-travel debugger for multi-agent LLM systems.**

Agent Tracer records every step a multi-agent system takes (prompts, tool calls, tool results, intermediate reasoning) into a local trace store, and gives you a UI to scrub through that history, fork execution from any point, edit the state at that point, and replay forward without re-running everything that came before it.

No account. No cloud. No vendor lock-in. SQLite on disk, a local web UI, done.

---

## The problem

If you've built anything beyond a single-agent toy, you've hit this: an agent does something wrong four steps into a run, and your only tools to figure out why are `print()` statements and re-running the whole thing from scratch, hoping it fails the same way twice (it often doesn't, because LLMs aren't deterministic).

Existing observability tools (LangSmith, Helicone, Langfuse) solve *logging* - you can see what happened. None of them solve *debugging* - going back to step 3, changing what the tool returned, and seeing what the agent does differently from there, without burning tokens re-running steps 1 and 2. They're also largely cloud/SaaS-first, which is a non-starter if you're running agents locally against Ollama or similar for cost, privacy, or latency reasons.

Agent Tracer is built around one core mechanic that doesn't really exist elsewhere in an accessible form: **fork and replay**.

## Core mechanic: fork and replay

1. Every agent run is recorded as a trace: a tree of steps (LLM calls, tool calls, tool results, state mutations), each with full input/output and a content hash.
2. Open any trace in the UI and scrub through it like a video timeline.
3. Pick any step. Edit the prompt, the tool result, or the agent's state at that point.
4. Hit replay. Execution resumes from that step forward using your edited state - steps before the fork point are never re-executed, so you're not re-paying for or re-waiting on work you already did.
5. The result is a new branch in the trace tree, so you can compare the original run against your "what if" run side by side.

This turns debugging a bad agent decision from "re-run the whole pipeline and hope" into "fix the one thing you think is wrong and see what happens next" - the same mental model as `git rebase -i` or a real debugger's "set next statement."

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Your Agent Code                     │
│         (Crucible, LangChain, AutoGen, raw loop...)      │
└───────────────────────────┬────────────────────────────┘
                             │ instrumentation (decorator / context manager)
┌────────────────────────────▼────────────────────────────┐
│                      Tracer SDK (Python)                 │
│   - captures LLM calls, tool calls, state snapshots       │
│   - content-hashes each step for dedup/caching             │
│   - async, non-blocking write path                         │
└───────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│              Local Trace Store (SQLite + WAL)             │
│   trace_id -> tree of steps, each with:                   │
│   input, output, timestamp, cost, parent_step_id           │
└───────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│                  Local Web UI (FastAPI + React)           │
│   - timeline scrubber per trace                            │
│   - step inspector (full I/O, diff view between branches)  │
│   - fork-and-replay controls                                │
│   - cost/latency breakdown per step and per branch          │
└───────────────────────────────────────────────────────────┘
```

Replay execution re-invokes your actual agent/tool code starting at the fork point - Agent Tracer doesn't simulate anything, it calls your real functions with the edited state, so behavior after the fork is exactly as real as the original run.

## Key features (v1 scope)

- **Zero-config instrumentation**: one decorator (`@traced`) or context manager around your agent loop; no changes to agent logic required.
- **Framework-agnostic capture**: works with raw Python agent loops, LangChain, AutoGen, and Crucible out of the box via thin adapters.
- **Fork and replay**: the core mechanic described above.
- **Branch diffing**: side-by-side comparison of two branches from the same fork point: what changed in output, cost, latency, tool calls made.
- **Cost and latency breakdown**: per-step and per-branch, so you can see exactly which step in a 20-step trace is expensive or slow.
- **Local-first**: SQLite trace store, no external service, no API key required to use the core tool.
- **Export/import traces**: share a trace file with a teammate or attach one to a bug report.

## Explicitly out of scope for v1

- Multi-user / team collaboration features (single-user local tool first)
- Cloud sync (may come later as opt-in, not required)
- Automatic root-cause analysis via LLM (tempting, but it's a gimmick until the core mechanic is solid)

## Tech stack

- **SDK**: Python, async-first, minimal dependencies
- **Storage**: SQLite (WAL mode for concurrent read/write during live tracing)
- **Backend**: FastAPI serving the trace store over a local HTTP API
- **Frontend**: React + a lightweight state-diff viewer
- **Reference integration**: [Crucible](https://github.com/abdur-rafay-ar/crucible) (hybrid BM25 + embedding multi-agent framework, local via Ollama)

## Quickstart (planned)

```bash
pip install agent-tracer

from agent_tracer import traced

@traced
def run_agent(task: str):
    ...

# then
agent-tracer ui
# opens http://localhost:4173 with your traces
```

## Roadmap

- [ ] v0.1: SDK with decorator-based capture + SQLite store
- [ ] v0.2: Local web UI timeline view, step inspector
- [ ] v0.3: Fork and replay
- [ ] v0.4: Branch diffing + cost/latency breakdown
- [ ] v0.5: Crucible adapter, LangChain adapter
- [ ] v1.0: Stable SDK API, documented extension points for custom adapters

## Why this exists

Built as the debugging layer I wanted while working on [Crucible](https://github.com/abdur-rafay-ar/crucible). Multi-agent systems are hard enough to reason about when everything works - they're nearly impossible to debug with print statements when something goes wrong three agents deep. This is the tool I kept wishing existed.

## License

MIT
