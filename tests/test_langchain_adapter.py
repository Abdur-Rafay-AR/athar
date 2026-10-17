import unittest
import os
import tempfile
import uuid
from athar.adapters.langchain import AtharCallbackHandler
from athar.storage.sqlite_store import TraceStore

class DummyLLMResult:
    def __init__(self, text: str, total_tokens: int = 250):
        self.generations = [[type("Gen", (), {"text": text})()]]
        self.llm_output = {"token_usage": {"total_tokens": total_tokens}}

class TestLangChainAdapter(unittest.TestCase):
    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        self.store = TraceStore(db_path=self.temp_db_path)
        self.trace_id = "lc_test_trace"
        self.handler = AtharCallbackHandler(trace_id=self.trace_id, store=self.store)

    def tearDown(self):
        if hasattr(self.store._local, "conn"):
            self.store._local.conn.close()
            delattr(self.store._local, "conn")
        os.close(self.temp_db_fd)
        try:
            os.remove(self.temp_db_path)
        except PermissionError:
            pass

    def test_chain_llm_and_tool_hierarchy(self):
        chain_run_id = uuid.uuid4()
        llm_run_id = uuid.uuid4()
        tool_run_id = uuid.uuid4()

        # 1. Chain starts
        self.handler.on_chain_start(
            serialized={"name": "ResearchChain"},
            inputs={"topic": "Quantum Computing"},
            run_id=chain_run_id
        )

        # 2. Nested LLM call starts & ends
        self.handler.on_llm_start(
            serialized={"name": "ChatOpenAI"},
            prompts=["What is quantum supremacy?"],
            run_id=llm_run_id,
            parent_run_id=chain_run_id
        )
        self.handler.on_llm_end(
            response=DummyLLMResult("Quantum supremacy achieved.", total_tokens=400),
            run_id=llm_run_id
        )

        # 3. Nested Tool call starts & ends
        self.handler.on_tool_start(
            serialized={"name": "ArxivSearch"},
            input_str="quantum computing papers",
            run_id=tool_run_id,
            parent_run_id=chain_run_id
        )
        self.handler.on_tool_end(
            output="3 papers found",
            run_id=tool_run_id
        )

        # 4. Chain ends
        self.handler.on_chain_end(
            outputs={"final_output": "Summary of 3 papers"},
            run_id=chain_run_id
        )

        nodes = self.store.get_nodes(self.trace_id)
        self.assertEqual(len(nodes), 3)

        chain_node = next(n for n in nodes if "chain:" in n["func_name"])
        llm_node = next(n for n in nodes if "llm:" in n["func_name"])
        tool_node = next(n for n in nodes if "tool:" in n["func_name"])

        # Hierarchy assertion
        self.assertIsNone(chain_node["parent_node_id"])
        self.assertEqual(llm_node["parent_node_id"], chain_node["node_id"])
        self.assertEqual(tool_node["parent_node_id"], chain_node["node_id"])

        # Tokens & output assertion
        self.assertGreater(llm_node["cost"], 0.0)
        self.assertIn("Quantum supremacy", str(llm_node["output_data"]))

    def test_error_handling_in_callbacks(self):
        tool_run_id = uuid.uuid4()
        self.handler.on_tool_start(
            serialized={"name": "FaultyTool"},
            input_str="bad input",
            run_id=tool_run_id
        )
        self.handler.on_tool_error(
            error=RuntimeError("API rate limit exceeded"),
            run_id=tool_run_id
        )

        nodes = self.store.get_nodes(self.trace_id)
        self.assertEqual(len(nodes), 1)
        self.assertIn("API rate limit exceeded", nodes[0]["output_data"]["error"])

if __name__ == "__main__":
    unittest.main()
