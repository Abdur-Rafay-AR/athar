import asyncio
import inspect
import threading
from typing import Callable, Dict, Any, Optional, Tuple

class FunctionRegistry:
    """
    Thread-safe registry mapping function names to executable callables.
    Enables true dynamic time-travel execution from any trace step.
    """
    def __init__(self):
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def register(self, name: str, func: Callable, is_async: Optional[bool] = None) -> None:
        """Registers a callable by name for dynamic replay."""
        with self._lock:
            # Unwrap any functools.wraps wrappers to find the base callable if needed
            raw_func = inspect.unwrap(func)
            detected_async = asyncio.iscoroutinefunction(func) or asyncio.iscoroutinefunction(raw_func)
            self._registry[name] = {
                "func": func,
                "raw_func": raw_func,
                "is_async": is_async if is_async is not None else detected_async,
                "sig": inspect.signature(raw_func)
            }

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._registry.get(name)

    def is_registered(self, name: str) -> bool:
        with self._lock:
            return name in self._registry

    def list_registered(self) -> Dict[str, bool]:
        with self._lock:
            return {k: v["is_async"] for k, v in self._registry.items()}

    def execute(self, name: str, args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None) -> Any:
        """
        Dynamically executes a registered function synchronously or via an event loop.
        """
        entry = self.get(name)
        if not entry:
            raise KeyError(f"Function '{name}' is not registered for live execution.")

        fn = entry["func"]
        args = args or ()
        kwargs = kwargs or {}

        if entry["is_async"]:
            # Run coroutine in current or new event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # If already in an active loop, schedule or nest
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(lambda: asyncio.run(fn(*args, **kwargs))).result()
            else:
                return asyncio.run(fn(*args, **kwargs))
        else:
            return fn(*args, **kwargs)

    def clear(self):
        with self._lock:
            self._registry.clear()


_global_registry = FunctionRegistry()

def get_registry() -> FunctionRegistry:
    return _global_registry
