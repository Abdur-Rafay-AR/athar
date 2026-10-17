import unittest
import os
import tempfile
from athar.core.diff import compare_branches
from athar.storage.sqlite_store import TraceStore

class TestBranchDiff(unittest.TestCase):
    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        self.store = TraceStore(db_path=self.temp_db_path)
        self.trace_id = "diff_test_trace"
        self.store.ensure_trace(self.trace_id, name="Diff Testing Run")

    def tearDown(self):
        if hasattr(self.store._local, "conn"):
            self.store._local.conn.close()
            delattr(self.store._local, "conn")
        os.close(self.temp_db_fd)
        try:
            os.remove(self.temp_db_path)
        except PermissionError:
            pass

    def test_compare_branches_metrics_and_diff(self):
        # Step 1 on main
        n1 = self.store.insert_node(
            node_id="n1",
            trace_id=self.trace_id,
            parent_node_id=None,
            func_name="search_tool",
            input_data={"query": "AI benchmarks"},
            output_data={"result": "Version 1.0 details"},
            cost=0.002,
            latency=0.5,
            branch_id="main",
            step_hash="hash_a1"
        )

        # Step 2 on main
        self.store.insert_node(
            node_id="n2",
            trace_id=self.trace_id,
            parent_node_id=n1,
            func_name="synthesizer",
            input_data={"context": "Version 1.0 details"},
            output_data={"summary": "Summary 1"},
            cost=0.005,
            latency=1.2,
            branch_id="main",
            step_hash="hash_a2"
        )

        # Forked Step 2 on fork_branch
        self.store.insert_node(
            node_id="n2_fork",
            trace_id=self.trace_id,
            parent_node_id=n1,
            func_name="synthesizer (forked)",
            input_data={"context": "Version 2.0 details", "forked_from": "n1"},
            output_data={"summary": "Summary 2 (optimized)"},
            cost=0.003, # Cost is lower!
            latency=0.8, # Faster!
            branch_id="fork_branch",
            step_hash="hash_b2"
        )

        diff = compare_branches(
            store=self.store,
            trace_id=self.trace_id,
            branch_a="main",
            branch_b="fork_branch"
        )

        summary = diff["summary"]
        self.assertEqual(summary["steps_branch_a"], 2)
        self.assertEqual(summary["steps_branch_b"], 1)
        self.assertAlmostEqual(summary["delta_cost"], 0.003 - (0.002 + 0.005))
        self.assertAlmostEqual(summary["delta_latency"], 0.8 - (0.5 + 1.2))
        self.assertIsNotNone(summary["fork_point"])
        self.assertEqual(summary["fork_point"]["node_id"], "n1")

        # Verify unified diff is present for compared steps
        step_diffs = diff["step_diffs"]
        self.assertGreater(len(step_diffs), 0)
        self.assertIn("output_diff", step_diffs[0])

    def test_invalid_branch_raises_value_error(self):
        with self.assertRaises(ValueError):
            compare_branches(self.store, self.trace_id, branch_a="main", branch_b="non_existent")

if __name__ == "__main__":
    unittest.main()
