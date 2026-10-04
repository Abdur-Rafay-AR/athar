import functools
import hashlib
import json
import time
import asyncio
from typing import Callable, Any

def traced(func: Callable) -> Callable:
    """
    Decorator to wrap an agent or tool function to record inputs, outputs, and latency.
    Hashes the step for fork-and-replay functionality.
    """
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        
        # Serialize input for hashing
        input_data = {"args": args, "kwargs": kwargs}
        input_json = json.dumps(input_data, default=str)
        
        result = None
        error = None
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            error = str(e)
            raise e
        finally:
            latency = time.time() - start_time
            output_json = json.dumps({"result": result, "error": error}, default=str)
            
            # Create content hash
            hasher = hashlib.sha256()
            hasher.update(input_json.encode('utf-8'))
            hasher.update(output_json.encode('utf-8'))
            step_hash = hasher.hexdigest()
            
            # Dispatch to storage queue (pseudo-code logic)
            _dispatch_to_storage(
                func_name=func.__name__,
                inputs=input_json,
                outputs=output_json,
                step_hash=step_hash,
                latency=latency
            )

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        
        input_data = {"args": args, "kwargs": kwargs}
        input_json = json.dumps(input_data, default=str)
        
        result = None
        error = None
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            error = str(e)
            raise e
        finally:
            latency = time.time() - start_time
            output_json = json.dumps({"result": result, "error": error}, default=str)
            
            hasher = hashlib.sha256()
            hasher.update(input_json.encode('utf-8'))
            hasher.update(output_json.encode('utf-8'))
            step_hash = hasher.hexdigest()
            
            _dispatch_to_storage(
                func_name=func.__name__,
                inputs=input_json,
                outputs=output_json,
                step_hash=step_hash,
                latency=latency
            )
            
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

def _dispatch_to_storage(func_name: str, inputs: str, outputs: str, step_hash: str, latency: float):
    # This would push to a thread-safe queue consumed by the SQLite WAL writer
    pass
