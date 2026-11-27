import unittest
import os
import tempfile
from athar.ui.app import (
    health,
    list_traces,
    create_trace,
    get_trace,
    get_trace_nodes,
    replay_from_node,
    delete_trace,
    delete_branch,
    seed_sample_trace,
    CreateTraceRequest,
    ReplayRequest,
)
from athar.storage.sqlite_store import TraceStore
from fastapi import HTTPException

class TestAtharAPI(unittest.TestCase):
    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.environ["ATHAR_DB_PATH"] = self.temp_db_path

    def tearDown(self):
        os.close(self.temp_db_fd)
        try:
            os.remove(self.temp_db_path)
        except PermissionError:
            pass

    def test_health_endpoint(self):
        res = health()
        self.assertEqual(res["status"], "healthy")
        self.assertEqual(res["service"], "athar")

    def test_create_and_list_traces(self):
        req = CreateTraceRequest(name="API Test Run", trace_id="api_tr_1")
        create_res = create_trace(req)
        self.assertEqual(create_res["status"], "created")
        self.assertEqual(create_res["trace_id"], "api_tr_1")

        list_res = list_traces()
        self.assertEqual(list_res["count"], 1)
        self.assertEqual(list_res["traces"][0]["name"], "API Test Run")

    def test_seed_sample_and_query_nodes(self):
        seed_res = seed_sample_trace()
        self.assertEqual(seed_res["status"], "seeded")
        trace_id = seed_res["trace_id"]

        nodes_res = get_trace_nodes(trace_id)
        self.assertEqual(nodes_res["count"], 3)
        self.assertEqual(nodes_res["nodes"][0]["func_name"], "orchestrator_agent")

    def test_replay_from_node(self):
        seed_res = seed_sample_trace()
        nodes_res = get_trace_nodes(seed_res["trace_id"])
        target_node = nodes_res["nodes"][0]

        replay_req = ReplayRequest(
            new_state={"user_prompt": "Mutated prompt for replay"},
            branch_name="test_branch"
        )
        replay_res = replay_from_node(target_node["node_id"], replay_req)
        self.assertEqual(replay_res["status"], "success")
        self.assertEqual(replay_res["data"]["branch_id"], "test_branch")

    def test_delete_trace_endpoint(self):
        create_trace(CreateTraceRequest(trace_id="del_api_trace"))
        del_res = delete_trace("del_api_trace")
        self.assertEqual(del_res["status"], "deleted")

        with self.assertRaises(HTTPException):
            get_trace("del_api_trace")

    def test_delete_branch_endpoint(self):
        store = TraceStore(db_path=self.temp_db_path)
        store.ensure_trace("del_branch_trace")
        store.insert_node("n_main", "del_branch_trace", None, "step1", {}, {}, branch_id="main")
        store.insert_node("n_fork", "del_branch_trace", "n_main", "step2", {}, {}, branch_id="fork_to_delete")

        # Deleting main branch should raise 400
        with self.assertRaises(HTTPException) as cm:
            delete_branch("del_branch_trace", "main")
        self.assertEqual(cm.exception.status_code, 400)

        # Deleting valid non-main branch should succeed
        res = delete_branch("del_branch_trace", "fork_to_delete")
        self.assertEqual(res["status"], "deleted")
        self.assertEqual(res["branch_id"], "fork_to_delete")

        # Deleting again should raise 404
        with self.assertRaises(HTTPException) as cm:
            delete_branch("del_branch_trace", "fork_to_delete")
        self.assertEqual(cm.exception.status_code, 404)

if __name__ == "__main__":
    unittest.main()
