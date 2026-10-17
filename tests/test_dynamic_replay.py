import unittest
import asyncio
import os
import tempfile
from athar.core.tracer import traced, set_trace_store
from athar.core.registry import get_registry
from athar.core.replayer import execute_replay
from athar.storage.sqlite_store import TraceStore

class TestDynamicReplay(unittest.TestCase):
    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        self.store = TraceStore(db_path=self.temp_db_path)
        set_trace_store(self.store)
        get_registry().clear()

    def tearDown(self):
        if hasattr(self.store._local, "conn"):
            self.store._local.conn.close()
            delattr(self.store._local, "conn")
        os.close(self.temp_db_fd)
        try:
            os.remove(self.temp_db_path)
        except PermissionError:
            pass
        get_registry().clear()

    def test_live_sync_replay(self):
        call_count = 0

        @traced
        def multiply(x: int, y: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * y

        # Run 1: initial run
        res = multiply(3, 4)
        self.assertEqual(res, 12)
        self.assertEqual(call_count, 1)

        traces = self.store.list_traces()
        nodes = self.store.get_nodes(traces[0]["trace_id"])
        original_node_id = nodes[0]["node_id"]

        # Run 2: Replay with mutated inputs (x=5, y=10)
        replay_res = execute_replay(
            store=self.store,
            node_id=original_node_id,
            mutated_input={"kwargs": {"x": 5, "y": 10}},
            branch_name="experiment_5x10"
        )

        self.assertEqual(call_count, 2)  # Real Python function executed again!
        self.assertEqual(replay_res["execution_mode"], "live_executed")
        self.assertEqual(replay_res["result"], 50)
        self.assertEqual(replay_res["branch_id"], "experiment_5x10")

        # Verify new branch node in database
        updated_nodes = self.store.get_nodes(traces[0]["trace_id"])
        self.assertEqual(len(updated_nodes), 2)
        forked_node = [n for n in updated_nodes if n["branch_id"] == "experiment_5x10"][0]
        self.assertEqual(forked_node["output_data"]["result"], 50)

    def test_live_async_replay(self):
        @traced
        async def async_summarize(text: str) -> str:
            await asyncio.sleep(0.01)
            return f"Summary: {text.upper()}"

        asyncio.run(async_summarize("original text"))
        traces = self.store.list_traces()
        original_node = self.store.get_nodes(traces[0]["trace_id"])[0]

        # Replay with mutated text
        replay_res = execute_replay(
            store=self.store,
            node_id=original_node["node_id"],
            mutated_input={"kwargs": {"text": "mutated prompt"}},
            branch_name="async_branch"
        )

        self.assertEqual(replay_res["execution_mode"], "live_executed")
        self.assertEqual(replay_res["result"], "Summary: MUTATED PROMPT")

    def test_live_replay_exception_capture(self):
        @traced
        def divide(a: int, b: int) -> float:
            return a / b

        divide(10, 2)
        traces = self.store.list_traces()
        orig_node = self.store.get_nodes(traces[0]["trace_id"])[0]

        # Mutate b to 0 to trigger ZeroDivisionError on replay
        replay_res = execute_replay(
            store=self.store,
            node_id=orig_node["node_id"],
            mutated_input={"kwargs": {"a": 10, "b": 0}}
        )

        self.assertEqual(replay_res["execution_mode"], "live_error")
        self.assertIn("division by zero", replay_res["error"])

    def test_fallback_simulation_when_not_registered(self):
        # Insert a raw node not in FunctionRegistry
        node_id = self.store.insert_node(
            node_id="unregistered_node",
            trace_id="tr_sim",
            parent_node_id=None,
            func_name="legacy_external_tool",
            input_data={"data": 1},
            output_data={"data": 2}
        )

        replay_res = execute_replay(
            store=self.store,
            node_id=node_id,
            mutated_input={"data": 99}
        )

        self.assertEqual(replay_res["execution_mode"], "state_mutation")
        self.assertIn("logged without active runtime callable", replay_res["result"]["message"])

if __name__ == "__main__":
    unittest.main()
