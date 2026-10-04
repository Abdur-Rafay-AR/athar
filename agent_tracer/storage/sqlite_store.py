import sqlite3
import json
import threading
from typing import Dict, Any, Optional

class TraceStore:
    """
    SQLite-backed local storage for trace steps.
    Uses WAL mode to allow concurrent read/writes between the running agent and the UI.
    """
    def __init__(self, db_path: str = "agent_traces.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    @property
    def conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.execute("PRAGMA journal_mode=WAL;")
        return self._local.conn

    def _init_db(self):
        c = self.conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS traces (
                trace_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,
                trace_id TEXT,
                parent_node_id TEXT,
                func_name TEXT,
                input_data TEXT,
                output_data TEXT,
                state_snapshot TEXT,
                cost REAL,
                latency REAL,
                step_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(trace_id) REFERENCES traces(trace_id)
            )
        ''')
        self.conn.commit()

    def insert_node(self, node_id: str, trace_id: str, parent_node_id: Optional[str], 
                    func_name: str, input_data: Dict, output_data: Dict, 
                    state_snapshot: Dict, latency: float, step_hash: str):
        c = self.conn.cursor()
        c.execute('''
            INSERT INTO nodes (node_id, trace_id, parent_node_id, func_name, 
                               input_data, output_data, state_snapshot, latency, step_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            node_id, trace_id, parent_node_id, func_name, 
            json.dumps(input_data), json.dumps(output_data), 
            json.dumps(state_snapshot), latency, step_hash
        ))
        self.conn.commit()
