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
from .storage.sqlite_store import TraceStore

__version__ = "0.1.0"
__all__ = [
    "traced",
    "TracerContext",
    "TraceStore",
    "get_active_trace_id",
    "set_active_trace_id",
    "get_trace_store",
    "set_trace_store",
    "__version__",
]
