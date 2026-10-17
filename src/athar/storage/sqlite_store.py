import sqlite3
import json
import os
import threading
import uuid
from typing import Dict, Any, Optional, List

DEFAULT_DB_PATH = os.environ.get("ATHAR_DB_PATH", "agent_traces.db")

class TraceStore:
    """
    SQLite-backed local storage for trace steps and execution branches.
    Uses WAL mode for high-concurrency non-blocking writes from agents
    and reads from the UI.
    """
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    @property
    def conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self.db_path, timeout=10.0)
            self._local.conn.row_factory = sqlite3.Row
            # Enforce WAL mode for concurrent multi-process / multi-thread access
            self._local.conn.execute("PRAGMA journal_mode=WAL;")
            self._local.conn.execute("PRAGMA synchronous=NORMAL;")
        return self._local.conn

    def _init_db(self):
        c = self.conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS traces (
                trace_id TEXT PRIMARY KEY,
                name TEXT,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL,
                parent_node_id TEXT,
                branch_id TEXT DEFAULT 'main',
                func_name TEXT NOT NULL,
                input_data TEXT,
                output_data TEXT,
                state_snapshot TEXT,
                cost REAL DEFAULT 0.0,
                latency REAL DEFAULT 0.0,
                step_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(trace_id) REFERENCES traces(trace_id) ON DELETE CASCADE
            )
        ''')
        # Indexes for fast querying
        c.execute('CREATE INDEX IF NOT EXISTS idx_nodes_trace_id ON nodes(trace_id);')
        c.execute('CREATE INDEX IF NOT EXISTS idx_nodes_parent_id ON nodes(parent_node_id);')
        self.conn.commit()

    def ensure_trace(self, trace_id: str, name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Ensures a trace record exists in the traces table."""
        c = self.conn.cursor()
        c.execute("SELECT trace_id FROM traces WHERE trace_id = ?", (trace_id,))
        if not c.fetchone():
            meta_json = json.dumps(metadata or {})
            trace_name = name or f"Trace {trace_id[:8]}"
            c.execute(
                "INSERT INTO traces (trace_id, name, metadata) VALUES (?, ?, ?)",
                (trace_id, trace_name, meta_json)
            )
            self.conn.commit()

    def insert_node(
        self,
        node_id: str,
        trace_id: str,
        parent_node_id: Optional[str],
        func_name: str,
        input_data: Any,
        output_data: Any,
        state_snapshot: Optional[Any] = None,
        latency: float = 0.0,
        cost: float = 0.0,
        step_hash: Optional[str] = None,
        branch_id: str = "main"
    ) -> str:
        """Inserts a trace node, auto-registering the trace if missing."""
        self.ensure_trace(trace_id)
        c = self.conn.cursor()
        
        input_json = json.dumps(input_data, default=str) if not isinstance(input_data, str) else input_data
        output_json = json.dumps(output_data, default=str) if not isinstance(output_data, str) else output_data
        state_json = json.dumps(state_snapshot or {}, default=str) if not isinstance(state_snapshot, str) else state_snapshot

        c.execute('''
            INSERT INTO nodes (
                node_id, trace_id, parent_node_id, branch_id, func_name,
                input_data, output_data, state_snapshot, cost, latency, step_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            node_id, trace_id, parent_node_id, branch_id, func_name,
            input_json, output_json, state_json, cost, latency, step_hash
        ))
        
        # Update trace timestamp
        c.execute("UPDATE traces SET updated_at = CURRENT_TIMESTAMP WHERE trace_id = ?", (trace_id,))
        self.conn.commit()
        return node_id

    def list_traces(self) -> List[Dict[str, Any]]:
        """Returns all traces with aggregated stats (node count, duration)."""
        c = self.conn.cursor()
        c.execute('''
            SELECT 
                t.trace_id,
                t.name,
                t.status,
                t.created_at,
                t.updated_at,
                t.metadata,
                COUNT(n.node_id) as node_count,
                COALESCE(SUM(n.latency), 0.0) as total_latency,
                COALESCE(SUM(n.cost), 0.0) as total_cost
            FROM traces t
            LEFT JOIN nodes n ON t.trace_id = n.trace_id
            GROUP BY t.trace_id
            ORDER BY t.created_at DESC
        ''')
        rows = c.fetchall()
        result = []
        for row in rows:
            item = dict(row)
            try:
                item["metadata"] = json.loads(item["metadata"]) if item["metadata"] else {}
            except Exception:
                item["metadata"] = {}
            result.append(item)
        return result

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM traces WHERE trace_id = ?", (trace_id,))
        row = c.fetchone()
        if not row:
            return None
        item = dict(row)
        try:
            item["metadata"] = json.loads(item["metadata"]) if item["metadata"] else {}
        except Exception:
            item["metadata"] = {}
        return item

    def get_nodes(self, trace_id: str) -> List[Dict[str, Any]]:
        """Returns all nodes for a given trace sorted chronologically."""
        c = self.conn.cursor()
        c.execute("SELECT * FROM nodes WHERE trace_id = ? ORDER BY created_at ASC", (trace_id,))
        rows = c.fetchall()
        nodes = []
        for row in rows:
            node = dict(row)
            try:
                node["input_data"] = json.loads(node["input_data"]) if node["input_data"] else None
            except Exception:
                pass
            try:
                node["output_data"] = json.loads(node["output_data"]) if node["output_data"] else None
            except Exception:
                pass
            try:
                node["state_snapshot"] = json.loads(node["state_snapshot"]) if node["state_snapshot"] else {}
            except Exception:
                pass
            nodes.append(node)
        return nodes

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM nodes WHERE node_id = ?", (node_id,))
        row = c.fetchone()
        if not row:
            return None
        node = dict(row)
        try:
            node["input_data"] = json.loads(node["input_data"]) if node["input_data"] else None
        except Exception:
            pass
        try:
            node["output_data"] = json.loads(node["output_data"]) if node["output_data"] else None
        except Exception:
            pass
        try:
            node["state_snapshot"] = json.loads(node["state_snapshot"]) if node["state_snapshot"] else {}
        except Exception:
            pass
        return node

    def delete_trace(self, trace_id: str) -> bool:
        c = self.conn.cursor()
        c.execute("DELETE FROM nodes WHERE trace_id = ?", (trace_id,))
        c.execute("DELETE FROM traces WHERE trace_id = ?", (trace_id,))
        self.conn.commit()
        return c.rowcount > 0

    def fork_node(self, node_id: str, new_state: Dict[str, Any], branch_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Creates a branched execution node from an existing step with mutated state.
        """
        original = self.get_node(node_id)
        if not original:
            raise ValueError(f"Node {node_id} not found.")

        new_node_id = f"node_{uuid.uuid4().hex[:12]}"
        branch_id = branch_name or f"branch_{uuid.uuid4().hex[:6]}"

        # Record the forked replay node
        self.insert_node(
            node_id=new_node_id,
            trace_id=original["trace_id"],
            parent_node_id=original["parent_node_id"],
            func_name=f"{original['func_name']} (forked)",
            input_data={"mutated_state": new_state, "forked_from": node_id},
            output_data={"status": "replayed", "message": "Replay execution initialized from mutated state"},
            state_snapshot=new_state,
            latency=0.001,
            cost=0.0,
            step_hash=f"fork_{uuid.uuid4().hex[:8]}",
            branch_id=branch_id
        )

        return {
            "original_node_id": node_id,
            "new_node_id": new_node_id,
            "branch_id": branch_id,
            "trace_id": original["trace_id"]
        }
