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
from .core.diff import compare_branches
from .storage.sqlite_store import TraceStore
from .adapters.crucible_adapter import CrucibleAdapter
from .adapters.langchain import AtharCallbackHandler

__version__ = "0.1.0"
__all__ = [
    "traced",
    "TracerContext",
    "TraceStore",
    "FunctionRegistry",
    "get_registry",
    "execute_replay",
    "compare_branches",
    "CrucibleAdapter",
    "AtharCallbackHandler",
    "get_active_trace_id",
    "set_active_trace_id",
    "get_trace_store",
    "set_trace_store",
    "__version__",
]
