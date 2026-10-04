from typing import Any, Dict
from ..core.tracer import traced

class CrucibleAdapter:
    """
    Adapter for Crucible integration.
    """
    @staticmethod
    def wrap_agent(agent_instance: Any):
        """
        Wraps a Crucible agent's act or run method with our tracer.
        """
        if hasattr(agent_instance, "run"):
            agent_instance.run = traced(agent_instance.run)
        elif hasattr(agent_instance, "act"):
            agent_instance.act = traced(agent_instance.act)
        return agent_instance
