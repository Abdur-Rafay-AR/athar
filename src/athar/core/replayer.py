import hashlib
import json
import time
import uuid
from typing import Dict, Any, Optional

from .registry import get_registry
from ..storage.sqlite_store import TraceStore

def _compute_hash(inputs_json: str, outputs_json: str) -> str:
    hasher = hashlib.sha256()
    hasher.update(inputs_json.encode("utf-8"))
    hasher.update(outputs_json.encode("utf-8"))
    return hasher.hexdigest()

def execute_replay(
    store: TraceStore,
    node_id: str,
    mutated_input: Optional[Dict[str, Any]] = None,
    branch_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes a time-travel fork-and-replay from an existing trace node.
    If the function is registered in FunctionRegistry, it performs a REAL execution
    with the mutated inputs and measures real output & latency.
    Otherwise, it performs a state-snapshot fork.
    """
    node = store.get_node(node_id)
    if not node:
        raise ValueError(f"Trace node '{node_id}' does not exist.")

    trace_id = node["trace_id"]
    func_name = node["func_name"]
    parent_node_id = node["parent_node_id"]
    branch_id = branch_name or f"replay_{uuid.uuid4().hex[:6]}"
    new_node_id = f"node_{uuid.uuid4().hex[:12]}"

    registry = get_registry()
    is_live = registry.is_registered(func_name)

    # Determine execution arguments
    # Look at original inputs
    orig_inputs = node.get("input_data") or {}
    args = orig_inputs.get("args", ())
    kwargs = orig_inputs.get("kwargs", {})

    # If mutated input is provided, parse it
    if mutated_input is not None:
        if isinstance(mutated_input, dict):
            if "args" in mutated_input or "kwargs" in mutated_input:
                args = tuple(mutated_input.get("args", ()))
                kwargs = dict(mutated_input.get("kwargs", {}))
            else:
                # Treat the entire dictionary as updated kwargs
                kwargs = {**kwargs, **mutated_input}
        else:
            args = (mutated_input,)

    start_time = time.time()
    result = None
    error = None
    execution_mode = "simulated"

    if is_live:
        try:
            result = registry.execute(func_name, args=tuple(args), kwargs=dict(kwargs))
            execution_mode = "live_executed"
        except Exception as e:
            error = str(e)
            execution_mode = "live_error"
    else:
        # Fallback simulation
        result = {"status": "replayed", "message": "State mutation logged without active runtime callable"}
        execution_mode = "state_mutation"

    latency = round(time.time() - start_time, 4)
    output_payload = {"result": result, "error": error}
    input_payload = {"args": args, "kwargs": kwargs, "forked_from": node_id}

    input_json = json.dumps(input_payload, default=str)
    output_json = json.dumps(output_payload, default=str)
    step_hash = _compute_hash(input_json, output_json)

    # Insert branched execution node
    store.insert_node(
        node_id=new_node_id,
        trace_id=trace_id,
        parent_node_id=parent_node_id,
        func_name=f"{func_name} (forked)",
        input_data=input_payload,
        output_data=output_payload,
        state_snapshot={"args": repr(args), "kwargs": repr(kwargs), "execution_mode": execution_mode},
        latency=latency,
        cost=node.get("cost", 0.0),
        step_hash=step_hash,
        branch_id=branch_id
    )

    return {
        "status": "success",
        "execution_mode": execution_mode,
        "trace_id": trace_id,
        "original_node_id": node_id,
        "new_node_id": new_node_id,
        "branch_id": branch_id,
        "result": result,
        "error": error,
        "latency": latency
    }
