import asyncio
import contextvars
import functools
import hashlib
import json
import time
import uuid
from typing import Callable, Any, Optional, Dict

from ..storage.sqlite_store import TraceStore
from .registry import get_registry

# Context variables for tracking active trace execution context across async/threads
_active_trace_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("active_trace_id", default=None)
_active_parent_node_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("active_parent_node_id", default=None)
_global_store: Optional[TraceStore] = None

def get_trace_store() -> TraceStore:
    """Returns the singleton or newly initialized default TraceStore."""
    global _global_store
    if _global_store is None:
        _global_store = TraceStore()
    return _global_store

def set_trace_store(store: TraceStore):
    """Overrides the global trace store (useful for testing or custom paths)."""
    global _global_store
    _global_store = store

def get_active_trace_id() -> Optional[str]:
    """Returns the currently active trace ID if running inside a trace context."""
    return _active_trace_id.get()

def set_active_trace_id(trace_id: Optional[str]):
    """Manually sets the active trace ID for the current context."""
    _active_trace_id.set(trace_id)


class TracerContext:
    """
    Context manager to scope a sequence of agent calls under a single trace session.
    Supports both synchronous ('with') and asynchronous ('async with') execution.
    """
    def __init__(self, trace_id: Optional[str] = None, name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        self.trace_id = trace_id or f"trace_{uuid.uuid4().hex[:12]}"
        self.name = name
        self.metadata = metadata or {}
        self._token_trace: Optional[contextvars.Token] = None
        self._token_parent: Optional[contextvars.Token] = None

    def __enter__(self):
        store = get_trace_store()
        store.ensure_trace(self.trace_id, name=self.name, metadata=self.metadata)
        self._token_trace = _active_trace_id.set(self.trace_id)
        self._token_parent = _active_parent_node_id.set(None)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._token_trace:
            _active_trace_id.reset(self._token_trace)
        if self._token_parent:
            _active_parent_node_id.reset(self._token_parent)

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)


def _compute_hash(inputs_json: str, outputs_json: str) -> str:
    """Computes a deterministic SHA-256 content hash of inputs and outputs."""
    hasher = hashlib.sha256()
    hasher.update(inputs_json.encode("utf-8"))
    hasher.update(outputs_json.encode("utf-8"))
    return hasher.hexdigest()


def traced(func: Optional[Callable] = None, *, name: Optional[str] = None, cost: float = 0.0) -> Callable:
    """
    Decorator to wrap an agent or tool function to record inputs, outputs, state snapshots,
    latency, and content hashes into Athar's local trace store.

    Usage:
        @traced
        def my_agent(prompt: str):
            ...

        @traced(name="SummarizerTool", cost=0.002)
        async def call_llm(messages):
            ...
    """
    def decorator(fn: Callable) -> Callable:
        func_display_name = name or fn.__name__
        get_registry().register(func_display_name, fn)

        if asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                store = get_trace_store()
                
                # Active or new trace session
                trace_id = _active_trace_id.get()
                if not trace_id:
                    trace_id = f"trace_{uuid.uuid4().hex[:12]}"
                    store.ensure_trace(trace_id, name=f"Run: {func_display_name}")

                parent_id = _active_parent_node_id.get()
                node_id = f"node_{uuid.uuid4().hex[:12]}"

                # Serialize inputs
                input_payload = {"args": args, "kwargs": kwargs}
                input_json = json.dumps(input_payload, default=str)

                start_time = time.time()
                result = None
                error = None

                # Push this node as parent for subsequent nested calls
                parent_token = _active_parent_node_id.set(node_id)
                trace_token = _active_trace_id.set(trace_id)

                try:
                    result = await fn(*args, **kwargs)
                    return result
                except Exception as e:
                    error = str(e)
                    raise
                finally:
                    latency = round(time.time() - start_time, 4)
                    _active_parent_node_id.reset(parent_token)
                    _active_trace_id.reset(trace_token)

                    output_payload = {"result": result, "error": error}
                    output_json = json.dumps(output_payload, default=str)
                    step_hash = _compute_hash(input_json, output_json)

                    # Store execution step
                    store.insert_node(
                        node_id=node_id,
                        trace_id=trace_id,
                        parent_node_id=parent_id,
                        func_name=func_display_name,
                        input_data=input_payload,
                        output_data=output_payload,
                        state_snapshot={"args": repr(args), "kwargs": repr(kwargs)},
                        latency=latency,
                        cost=cost,
                        step_hash=step_hash
                    )
            return async_wrapper
        else:
            @functools.wraps(fn)
            def sync_wrapper(*args, **kwargs):
                store = get_trace_store()
                
                trace_id = _active_trace_id.get()
                if not trace_id:
                    trace_id = f"trace_{uuid.uuid4().hex[:12]}"
                    store.ensure_trace(trace_id, name=f"Run: {func_display_name}")

                parent_id = _active_parent_node_id.get()
                node_id = f"node_{uuid.uuid4().hex[:12]}"

                input_payload = {"args": args, "kwargs": kwargs}
                input_json = json.dumps(input_payload, default=str)

                start_time = time.time()
                result = None
                error = None

                parent_token = _active_parent_node_id.set(node_id)
                trace_token = _active_trace_id.set(trace_id)

                try:
                    result = fn(*args, **kwargs)
                    return result
                except Exception as e:
                    error = str(e)
                    raise
                finally:
                    latency = round(time.time() - start_time, 4)
                    _active_parent_node_id.reset(parent_token)
                    _active_trace_id.reset(trace_token)

                    output_payload = {"result": result, "error": error}
                    output_json = json.dumps(output_payload, default=str)
                    step_hash = _compute_hash(input_json, output_json)

                    store.insert_node(
                        node_id=node_id,
                        trace_id=trace_id,
                        parent_node_id=parent_id,
                        func_name=func_display_name,
                        input_data=input_payload,
                        output_data=output_payload,
                        state_snapshot={"args": repr(args), "kwargs": repr(kwargs)},
                        latency=latency,
                        cost=cost,
                        step_hash=step_hash
                    )
            return sync_wrapper

    if func is not None:
        return decorator(func)
    return decorator
