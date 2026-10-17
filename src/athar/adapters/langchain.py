import time
import uuid
import json
import hashlib
from typing import Any, Dict, List, Optional
from ..storage.sqlite_store import TraceStore
from ..core.tracer import get_trace_store

try:
    from langchain_core.callbacks.base import BaseCallbackHandler
except ImportError:
    # Graceful fallback: class can operate standalone without hard langchain dependency
    class BaseCallbackHandler:
        pass

def _compute_hash(inputs_json: str, outputs_json: str) -> str:
    hasher = hashlib.sha256()
    hasher.update(inputs_json.encode("utf-8"))
    hasher.update(outputs_json.encode("utf-8"))
    return hasher.hexdigest()

class AtharCallbackHandler(BaseCallbackHandler):
    """
    Universal LangChain & LangGraph callback handler for Athar.
    Captures LLM calls, chain invocations, and tool executions directly into
    Athar's local SQLite trace store.

    Usage:
        from athar.adapters import AtharCallbackHandler

        handler = AtharCallbackHandler(trace_name="Research Agent Run")
        chain.invoke({"topic": "AI"}, config={"callbacks": [handler]})
    """
    def __init__(self, trace_id: Optional[str] = None, trace_name: Optional[str] = None, store: Optional[TraceStore] = None):
        super().__init__()
        self.store = store or get_trace_store()
        self.trace_id = trace_id or f"trace_{uuid.uuid4().hex[:12]}"
        self.trace_name = trace_name or f"LangChain Run: {self.trace_id[:8]}"
        self.store.ensure_trace(self.trace_id, name=self.trace_name)

        # Map run_id -> active step metadata
        self._runs: Dict[str, Dict[str, Any]] = {}

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        run_key = str(run_id)
        name = serialized.get("name") or serialized.get("id", ["Chain"])[-1]
        parent_key = str(parent_run_id) if parent_run_id else None
        parent_node_id = self._runs[parent_key]["node_id"] if parent_key in self._runs else None

        self._runs[run_key] = {
            "node_id": f"node_{uuid.uuid4().hex[:12]}",
            "parent_node_id": parent_node_id,
            "func_name": f"chain:{name}",
            "input_data": inputs,
            "start_time": time.time()
        }

    def on_chain_end(self, outputs: Dict[str, Any], *, run_id: Any, **kwargs: Any) -> None:
        run_key = str(run_id)
        run_info = self._runs.pop(run_key, None)
        if not run_info:
            return

        latency = round(time.time() - run_info["start_time"], 4)
        input_json = json.dumps(run_info["input_data"], default=str)
        output_json = json.dumps(outputs, default=str)
        step_hash = _compute_hash(input_json, output_json)

        self.store.insert_node(
            node_id=run_info["node_id"],
            trace_id=self.trace_id,
            parent_node_id=run_info["parent_node_id"],
            func_name=run_info["func_name"],
            input_data=run_info["input_data"],
            output_data={"result": outputs, "error": None},
            state_snapshot={},
            latency=latency,
            cost=0.0,
            step_hash=step_hash
        )

    def on_chain_error(self, error: BaseException, *, run_id: Any, **kwargs: Any) -> None:
        run_key = str(run_id)
        run_info = self._runs.pop(run_key, None)
        if not run_info:
            return

        latency = round(time.time() - run_info["start_time"], 4)
        input_json = json.dumps(run_info["input_data"], default=str)
        output_payload = {"result": None, "error": str(error)}
        step_hash = _compute_hash(input_json, json.dumps(output_payload, default=str))

        self.store.insert_node(
            node_id=run_info["node_id"],
            trace_id=self.trace_id,
            parent_node_id=run_info["parent_node_id"],
            func_name=run_info["func_name"],
            input_data=run_info["input_data"],
            output_data=output_payload,
            state_snapshot={},
            latency=latency,
            cost=0.0,
            step_hash=step_hash
        )

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        run_key = str(run_id)
        name = serialized.get("name") or "Tool"
        parent_key = str(parent_run_id) if parent_run_id else None
        parent_node_id = self._runs[parent_key]["node_id"] if parent_key in self._runs else None

        self._runs[run_key] = {
            "node_id": f"node_{uuid.uuid4().hex[:12]}",
            "parent_node_id": parent_node_id,
            "func_name": f"tool:{name}",
            "input_data": {"input": input_str},
            "start_time": time.time()
        }

    def on_tool_end(self, output: Any, *, run_id: Any, **kwargs: Any) -> None:
        run_key = str(run_id)
        run_info = self._runs.pop(run_key, None)
        if not run_info:
            return

        latency = round(time.time() - run_info["start_time"], 4)
        input_json = json.dumps(run_info["input_data"], default=str)
        output_payload = {"result": output, "error": None}
        output_json = json.dumps(output_payload, default=str)
        step_hash = _compute_hash(input_json, output_json)

        self.store.insert_node(
            node_id=run_info["node_id"],
            trace_id=self.trace_id,
            parent_node_id=run_info["parent_node_id"],
            func_name=run_info["func_name"],
            input_data=run_info["input_data"],
            output_data=output_payload,
            state_snapshot={},
            latency=latency,
            cost=0.0,
            step_hash=step_hash
        )

    def on_tool_error(self, error: BaseException, *, run_id: Any, **kwargs: Any) -> None:
        run_key = str(run_id)
        run_info = self._runs.pop(run_key, None)
        if not run_info:
            return

        latency = round(time.time() - run_info["start_time"], 4)
        input_json = json.dumps(run_info["input_data"], default=str)
        output_payload = {"result": None, "error": str(error)}
        step_hash = _compute_hash(input_json, json.dumps(output_payload, default=str))

        self.store.insert_node(
            node_id=run_info["node_id"],
            trace_id=self.trace_id,
            parent_node_id=run_info["parent_node_id"],
            func_name=run_info["func_name"],
            input_data=run_info["input_data"],
            output_data=output_payload,
            state_snapshot={},
            latency=latency,
            cost=0.0,
            step_hash=step_hash
        )

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        run_key = str(run_id)
        name = serialized.get("name") or "LLM"
        parent_key = str(parent_run_id) if parent_run_id else None
        parent_node_id = self._runs[parent_key]["node_id"] if parent_key in self._runs else None

        self._runs[run_key] = {
            "node_id": f"node_{uuid.uuid4().hex[:12]}",
            "parent_node_id": parent_node_id,
            "func_name": f"llm:{name}",
            "input_data": {"prompts": prompts},
            "start_time": time.time()
        }

    def on_llm_end(self, response: Any, *, run_id: Any, **kwargs: Any) -> None:
        run_key = str(run_id)
        run_info = self._runs.pop(run_key, None)
        if not run_info:
            return

        latency = round(time.time() - run_info["start_time"], 4)
        
        # Extract generations and token usage if available
        generations = []
        if hasattr(response, "generations"):
            for gen_list in response.generations:
                for gen in gen_list:
                    generations.append(getattr(gen, "text", str(gen)))
        else:
            generations = [str(response)]

        llm_output = getattr(response, "llm_output", {}) or {}
        token_usage = llm_output.get("token_usage", {})
        cost = token_usage.get("total_tokens", 0) * 0.000002 # Rough estimation

        output_payload = {
            "generations": generations,
            "token_usage": token_usage,
            "error": None
        }

        input_json = json.dumps(run_info["input_data"], default=str)
        output_json = json.dumps(output_payload, default=str)
        step_hash = _compute_hash(input_json, output_json)

        self.store.insert_node(
            node_id=run_info["node_id"],
            trace_id=self.trace_id,
            parent_node_id=run_info["parent_node_id"],
            func_name=run_info["func_name"],
            input_data=run_info["input_data"],
            output_data=output_payload,
            state_snapshot=token_usage,
            latency=latency,
            cost=cost,
            step_hash=step_hash
        )
