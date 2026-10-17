import unittest
import asyncio
import os
import tempfile
from athar.core.tracer import traced, TracerContext, set_trace_store
from athar.storage.sqlite_store import TraceStore

class TestTracer(unittest.TestCase):
    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        self.store = TraceStore(db_path=self.temp_db_path)
        set_trace_store(self.store)

    def tearDown(self):
        if hasattr(self.store._local, "conn"):
            self.store._local.conn.close()
            delattr(self.store._local, "conn")
        os.close(self.temp_db_fd)
        try:
            os.remove(self.temp_db_path)
        except PermissionError:
            pass

    def test_sync_traced_execution(self):
        @traced
        def add(a: int, b: int) -> int:
            return a + b

        result = add(2, 3)
        self.assertEqual(result, 5)

        traces = self.store.list_traces()
        self.assertEqual(len(traces), 1)
        nodes = self.store.get_nodes(traces[0]["trace_id"])
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["func_name"], "add")
        self.assertEqual(nodes[0]["output_data"]["result"], 5)
        self.assertTrue(nodes[0]["step_hash"])

    def test_async_traced_execution(self):
        @traced
        async def fetch_data(key: str):
            await asyncio.sleep(0.01)
            return {"key": key, "val": 42}

        res = asyncio.run(fetch_data("alpha"))
        self.assertEqual(res["val"], 42)

        traces = self.store.list_traces()
        self.assertEqual(len(traces), 1)
        nodes = self.store.get_nodes(traces[0]["trace_id"])
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["func_name"], "fetch_data")
        self.assertEqual(nodes[0]["output_data"]["result"]["val"], 42)

    def test_traced_error_capture(self):
        @traced
        def failing_tool():
            raise ValueError("Something went wrong in the tool")

        with self.assertRaises(ValueError):
            failing_tool()

        traces = self.store.list_traces()
        nodes = self.store.get_nodes(traces[0]["trace_id"])
        self.assertEqual(len(nodes), 1)
        self.assertIn("Something went wrong", nodes[0]["output_data"]["error"])

    def test_nested_agent_hierarchy(self):
        @traced
        def tool_call(q: str):
            return f"Answer for {q}"

        @traced
        def agent_orchestrator(task: str):
            ans = tool_call(task)
            return f"Final: {ans}"

        with TracerContext(trace_id="session_hierarchical", name="Hierarchy Test"):
            res = agent_orchestrator("What is the meaning?")
            self.assertIn("Final: Answer", res)

        nodes = self.store.get_nodes("session_hierarchical")
        self.assertEqual(len(nodes), 2)

        # Child node (tool_call) should have parent_node_id equal to orchestrator's node_id
        parent_node = [n for n in nodes if n["func_name"] == "agent_orchestrator"][0]
        child_node = [n for n in nodes if n["func_name"] == "tool_call"][0]

        self.assertIsNone(parent_node["parent_node_id"])
        self.assertEqual(child_node["parent_node_id"], parent_node["node_id"])

if __name__ == "__main__":
    unittest.main()
