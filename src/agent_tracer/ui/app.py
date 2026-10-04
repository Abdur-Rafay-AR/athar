from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sqlite3
import json
import os
from typing import List, Dict, Any

app = FastAPI(title="Agent Tracer UI API")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")



def get_db():
    conn = sqlite3.connect("agent_traces.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/traces")
def list_traces():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM traces ORDER BY created_at DESC")
    traces = [dict(row) for row in cursor.fetchall()]
    return {"traces": traces}

@app.get("/api/traces/{trace_id}/nodes")
def get_trace_nodes(trace_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM nodes WHERE trace_id = ? ORDER BY created_at ASC", (trace_id,))
    nodes = []
    for row in cursor.fetchall():
        node = dict(row)
        node["input_data"] = json.loads(node["input_data"]) if node["input_data"] else None
        node["output_data"] = json.loads(node["output_data"]) if node["output_data"] else None
        node["state_snapshot"] = json.loads(node["state_snapshot"]) if node["state_snapshot"] else None
        nodes.append(node)
    return {"nodes": nodes}

@app.post("/api/replay/{node_id}")
def replay_from_node(node_id: str, new_state: Dict[str, Any]):
    """
    Initiates a fork-and-replay from the given node using the new state.
    """
    # Pseudo-code for replay logic
    # 1. Fetch node
    # 2. Extract parent trace
    # 3. Create a branch
    # 4. Invoke agent via subprocess or RPC with new state
    return {"status": "success", "message": f"Replaying from node {node_id} with mutated state."}

def main():
    import uvicorn
    print("Starting Agent Tracer UI on http://localhost:4173/static/index.html")
    uvicorn.run(app, host="127.0.0.1", port=4173)

if __name__ == "__main__":
    main()
