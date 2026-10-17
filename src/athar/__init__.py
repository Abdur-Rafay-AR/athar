"""
Athar (أثر): A local-first, time-travel debugger for multi-agent LLM systems.
"""

from .core.tracer import (
    traced,
    TracerContext,
    get_active_trace_id,
    set_active_trace_id,
    get_trace_store,
    set_trace_store,
)
from .core.registry import FunctionRegistry, get_registry
from .core.replayer import execute_replay
from .storage.sqlite_store import TraceStore

__version__ = "0.1.0"
__all__ = [
    "traced",
    "TracerContext",
    "TraceStore",
    "FunctionRegistry",
    "get_registry",
    "execute_replay",
    "get_active_trace_id",
    "set_active_trace_id",
    "get_trace_store",
    "set_trace_store",
    "__version__",
]
