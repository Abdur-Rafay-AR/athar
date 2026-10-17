import difflib
import json
from typing import Dict, Any, List, Optional
from ..storage.sqlite_store import TraceStore

def _compute_json_diff(obj_a: Any, obj_b: Any) -> str:
    """Generates a unified text diff between two JSON-serializable payloads."""
    str_a = json.dumps(obj_a, indent=2, sort_keys=True, default=str).splitlines(keepends=True)
    str_b = json.dumps(obj_b, indent=2, sort_keys=True, default=str).splitlines(keepends=True)
    diff = difflib.unified_diff(str_a, str_b, fromfile="branch_a", tofile="branch_b", lineterm="")
    return "".join(diff)

def compare_branches(
    store: TraceStore,
    trace_id: str,
    branch_a: str = "main",
    branch_b: str = ""
) -> Dict[str, Any]:
    """
    Compares two execution branches in a trace.
    Computes:
      - Fork point & divergence step
      - Cost delta (delta_cost = cost_b - cost_a)
      - Latency delta (delta_latency = latency_b - latency_a)
      - Step count comparison
      - Per-step output diffs
    """
    all_nodes = store.get_nodes(trace_id)
    if not all_nodes:
        raise ValueError(f"Trace '{trace_id}' contains no nodes.")

    # Group nodes by branch_id
    nodes_a = [n for n in all_nodes if (n.get("branch_id") or "main") == branch_a]
    nodes_b = [n for n in all_nodes if (n.get("branch_id") or "main") == branch_b]

    if not nodes_a:
        raise ValueError(f"Branch '{branch_a}' not found in trace '{trace_id}'.")
    if not nodes_b:
        raise ValueError(f"Branch '{branch_b}' not found in trace '{trace_id}'.")

    # Aggregate metrics
    cost_a = sum(n.get("cost", 0.0) or 0.0 for n in nodes_a)
    cost_b = sum(n.get("cost", 0.0) or 0.0 for n in nodes_b)
    latency_a = sum(n.get("latency", 0.0) or 0.0 for n in nodes_a)
    latency_b = sum(n.get("latency", 0.0) or 0.0 for n in nodes_b)

    delta_cost = round(cost_b - cost_a, 6)
    delta_latency = round(latency_b - latency_a, 4)

    # Detect divergence / fork point
    fork_point = None
    first_b_node = nodes_b[0]
    
    # Check if branch_b specifies forked_from in input_data
    forked_from_id = None
    if isinstance(first_b_node.get("input_data"), dict):
        forked_from_id = first_b_node["input_data"].get("forked_from")

    if forked_from_id:
        ancestor = next((n for n in nodes_a if n["node_id"] == forked_from_id), None)
        if ancestor:
            fork_point = {
                "node_id": ancestor["node_id"],
                "func_name": ancestor["func_name"],
                "step_hash": ancestor.get("step_hash")
            }
    elif first_b_node.get("parent_node_id"):
        ancestor = next((n for n in nodes_a if n["node_id"] == first_b_node["parent_node_id"]), None)
        if ancestor:
            fork_point = {
                "node_id": ancestor["node_id"],
                "func_name": ancestor["func_name"],
                "step_hash": ancestor.get("step_hash")
            }

    # Step-by-step diff
    step_diffs = []
    max_steps = max(len(nodes_a), len(nodes_b))
    for i in range(max_steps):
        step_a = nodes_a[i] if i < len(nodes_a) else None
        step_b = nodes_b[i] if i < len(nodes_b) else None

        diff_item = {
            "index": i + 1,
            "step_a": {
                "node_id": step_a["node_id"] if step_a else None,
                "func_name": step_a["func_name"] if step_a else None,
                "latency": step_a.get("latency", 0.0) if step_a else None,
                "cost": step_a.get("cost", 0.0) if step_a else None,
                "output_data": step_a.get("output_data") if step_a else None,
            } if step_a else None,
            "step_b": {
                "node_id": step_b["node_id"] if step_b else None,
                "func_name": step_b["func_name"] if step_b else None,
                "latency": step_b.get("latency", 0.0) if step_b else None,
                "cost": step_b.get("cost", 0.0) if step_b else None,
                "output_data": step_b.get("output_data") if step_b else None,
            } if step_b else None,
        }

        if step_a and step_b:
            diff_item["output_diff"] = _compute_json_diff(
                step_a.get("output_data"),
                step_b.get("output_data")
            )
            diff_item["is_identical"] = step_a.get("step_hash") == step_b.get("step_hash")
        else:
            diff_item["output_diff"] = None
            diff_item["is_identical"] = False

        step_diffs.append(diff_item)

    return {
        "trace_id": trace_id,
        "branch_a": branch_a,
        "branch_b": branch_b,
        "summary": {
            "steps_branch_a": len(nodes_a),
            "steps_branch_b": len(nodes_b),
            "cost_branch_a": cost_a,
            "cost_branch_b": cost_b,
            "delta_cost": delta_cost,
            "latency_branch_a": latency_a,
            "latency_branch_b": latency_b,
            "delta_latency": delta_latency,
            "fork_point": fork_point
        },
        "step_diffs": step_diffs
    }
