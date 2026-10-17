import unittest
import os
import tempfile
from athar.storage.sqlite_store import TraceStore

class TestTraceStore(unittest.TestCase):
    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        self.store = TraceStore(db_path=self.temp_db_path)

    def tearDown(self):
        # Close connection before deleting
        if hasattr(self.store._local, "conn"):
            self.store._local.conn.close()
            delattr(self.store._local, "conn")
        os.close(self.temp_db_fd)
        try:
            os.remove(self.temp_db_path)
        except PermissionError:
            pass

    def test_ensure_trace_and_list(self):
        self.store.ensure_trace("trace_001", name="Test Session")
        traces = self.store.list_traces()
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0]["trace_id"], "trace_001")
        self.assertEqual(traces[0]["name"], "Test Session")

    def test_insert_node_and_query(self):
        node_id = self.store.insert_node(
            node_id="node_001",
            trace_id="trace_002",
            parent_node_id=None,
            func_name="orchestrator",
            input_data={"prompt": "hello"},
            output_data={"response": "world"},
            state_snapshot={"status": "ok"},
            latency=0.15,
            cost=0.001,
            step_hash="hash_123"
        )
        self.assertEqual(node_id, "node_001")

        nodes = self.store.get_nodes("trace_002")
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["func_name"], "orchestrator")
        self.assertEqual(nodes[0]["input_data"], {"prompt": "hello"})
        self.assertEqual(nodes[0]["output_data"], {"response": "world"})
        self.assertEqual(nodes[0]["cost"], 0.001)

    def test_fork_node(self):
        self.store.insert_node(
            node_id="root_node",
            trace_id="trace_fork",
            parent_node_id=None,
            func_name="agent_step",
            input_data={"val": 1},
            output_data={"val": 2}
        )

        fork_res = self.store.fork_node(
            node_id="root_node",
            new_state={"val": 99},
            branch_name="experimental_branch"
        )
        self.assertEqual(fork_res["branch_id"], "experimental_branch")
        self.assertEqual(fork_res["trace_id"], "trace_fork")

        nodes = self.store.get_nodes("trace_fork")
        self.assertEqual(len(nodes), 2)
        forked_node = [n for n in nodes if n["node_id"] == fork_res["new_node_id"]][0]
        self.assertEqual(forked_node["branch_id"], "experimental_branch")

    def test_delete_trace(self):
        self.store.ensure_trace("trace_del", name="To Delete")
        self.store.insert_node("node_del", "trace_del", None, "dummy", {}, {})
        self.assertTrue(self.store.delete_trace("trace_del"))
        self.assertIsNone(self.store.get_trace("trace_del"))
        self.assertEqual(len(self.store.get_nodes("trace_del")), 0)

if __name__ == "__main__":
    unittest.main()
