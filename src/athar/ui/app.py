from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import time
from typing import List, Dict, Any, Optional

from ..storage.sqlite_store import TraceStore
from ..core.replayer import execute_replay
from ..core.registry import get_registry
from ..core.diff import compare_branches

app = FastAPI(
    title="Athar UI & API",
    description="Local-first time-travel debugger for multi-agent LLM systems",
    version="0.1.0"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def get_store() -> TraceStore:
    db_path = os.environ.get("ATHAR_DB_PATH", "agent_traces.db")
    return TraceStore(db_path=db_path)

class ReplayRequest(BaseModel):
    new_state: Dict[str, Any]
    branch_name: Optional[str] = None

class CreateTraceRequest(BaseModel):
    name: Optional[str] = None
    trace_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@app.get("/", include_in_schema=False)
def root_redirect():
    return RedirectResponse(url="/static/index.html")

@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "athar",
        "version": "0.1.0",
        "storage": "sqlite-wal"
    }

@app.get("/api/traces")
def list_traces():
    store = get_store()
    traces = store.list_traces()
    return {"traces": traces, "count": len(traces)}

@app.get("/api/traces/{trace_id}")
def get_trace(trace_id: str):
    store = get_store()
    trace = store.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return {"trace": trace}

@app.get("/api/traces/{trace_id}/nodes")
def get_trace_nodes(trace_id: str):
    store = get_store()
    nodes = store.get_nodes(trace_id)
    return {"trace_id": trace_id, "nodes": nodes, "count": len(nodes)}

@app.get("/api/traces/{trace_id}/diff")
def get_trace_diff(trace_id: str, branch_a: str = Query("main"), branch_b: str = Query(...)):
    """
    Computes a structured diff between two execution branches in a trace.
    Returns fork points, delta cost, delta latency, and unified output diffs.
    """
    store = get_store()
    try:
        return compare_branches(store, trace_id, branch_a=branch_a, branch_b=branch_b)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/traces")
def create_trace(payload: CreateTraceRequest):
    store = get_store()
    trace_id = payload.trace_id or f"trace_{int(time.time()*1000)}"
    store.ensure_trace(trace_id, name=payload.name, metadata=payload.metadata)
    return {"status": "created", "trace_id": trace_id}

@app.get("/api/registry")
def list_registry():
    registry = get_registry()
    return {"registered_functions": registry.list_registered()}

@app.post("/api/replay/{node_id}")
def replay_from_node(node_id: str, payload: ReplayRequest):
    """
    Fork-and-replay from the given step.
    If the function has an active registered callable, it runs real Python code!
    Otherwise, creates a state-snapshot fork.
    """
    store = get_store()
    node = store.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

    try:
        replay_result = execute_replay(
            store=store,
            node_id=node_id,
            mutated_input=payload.new_state,
            branch_name=payload.branch_name
        )
        return {
            "status": "success",
            "message": f"Replayed node {node_id} ({replay_result['execution_mode']})",
            "data": replay_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/traces/{trace_id}")
def delete_trace(trace_id: str):
    store = get_store()
    deleted = store.delete_trace(trace_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Trace not found")
    return {"status": "deleted", "trace_id": trace_id}

@app.post("/api/seed-sample")
def seed_sample_trace():
    """Seeds a realistic sample multi-agent research trace for instant demonstration."""
    store = get_store()
    sample_trace_id = f"sample_trace_{int(time.time())}"
    store.ensure_trace(
        sample_trace_id,
        name="Multi-Agent Market Analysis",
        metadata={"author": "Athar Demo", "environment": "local"}
    )

    # Step 1: User prompt
    n1 = store.insert_node(
        node_id=f"node_root_{int(time.time())}",
        trace_id=sample_trace_id,
        parent_node_id=None,
        func_name="orchestrator_agent",
        input_data={"user_prompt": "Analyze impact of AI code assistants on engineering velocity."},
        output_data={"delegations": ["web_search_tool", "data_synthesis_agent"]},
        state_snapshot={"step": 1, "status": "planning"},
        latency=0.32,
        cost=0.0015,
        step_hash="sha256_root_step_sample"
    )

    # Step 2: Tool call
    n2 = store.insert_node(
        node_id=f"node_tool_{int(time.time())}",
        trace_id=sample_trace_id,
        parent_node_id=n1,
        func_name="web_search_tool",
        input_data={"query": "AI coding tools benchmark velocity 2026"},
        output_data={"results": ["Benchmark A: 35% speedup in boilerplate", "Benchmark B: 42% PR cycle time drop"]},
        state_snapshot={"step": 2, "cache_hit": False},
        latency=0.74,
        cost=0.0008,
        step_hash="sha256_search_tool_sample"
    )

    # Step 3: Synthesis
    store.insert_node(
        node_id=f"node_synth_{int(time.time())}",
        trace_id=sample_trace_id,
        parent_node_id=n2,
        func_name="data_synthesis_agent",
        input_data={"raw_metrics": ["35% speedup", "42% PR drop"]},
        output_data={"final_report": "AI assistants show measured 35-42% reduction in cycle times for routine tasks."},
        state_snapshot={"step": 3, "confidence": 0.94},
        latency=1.15,
        cost=0.0042,
        step_hash="sha256_synthesis_sample"
    )

    return {"status": "seeded", "trace_id": sample_trace_id}

def main():
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="Athar: Local-first time-travel debugger for LLM agents")
    parser.add_argument("--port", type=int, default=4173, help="Port to run the UI server on (default: 4173)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--db", type=str, default=None, help="Custom SQLite trace DB path")
    args = parser.parse_args()

    if args.db:
        os.environ["ATHAR_DB_PATH"] = args.db

    print(f"\n=======================================================")
    print(f"  ATHAR (أثر) · Local-First Multi-Agent Debugger")
    print(f"  Web UI: http://{args.host}:{args.port}")
    print(f"=======================================================\n")
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
