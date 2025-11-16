"""
TaskDB Tool - local SQLite-backed task storage with ADK wrapper.
"""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import threading

_DB_LOCK = threading.Lock()


class TaskDB:
    """
    Simple task database using SQLite.
    """

    def __init__(self, db_path: str = "data/tasks.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ----------------------------------------------------------
    # Internal: DB initialization
    # ----------------------------------------------------------
    def _init_db(self) -> None:
        with _DB_LOCK:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    duration_minutes INTEGER,
                    priority TEXT,
                    preferred_time_block TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            conn.commit()
            conn.close()

    # ----------------------------------------------------------
    # Add new task
    # ----------------------------------------------------------
    def add_task(
        self,
        title: str,
        description: str = "",
        duration_minutes: int = 60,
        priority: str = "medium",
        preferred_time_block: str = "morning"
    ) -> int:
        now = datetime.utcnow().isoformat()
        with _DB_LOCK:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO tasks (title, description, duration_minutes, priority,
                                   preferred_time_block, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (title, description, int(duration_minutes or 0), priority, preferred_time_block, now, now))

            task_id = cursor.lastrowid
            conn.commit()
            conn.close()

        return int(task_id)

    # ----------------------------------------------------------
    # Update an existing task
    # ----------------------------------------------------------
    def update_task(self, task_id: int, updates: Dict[str, Any]) -> bool:
        if not updates:
            return False

        allowed_fields = {
            "title", "description", "duration_minutes",
            "priority", "preferred_time_block", "status"
        }

        update_pairs = []
        values = []

        for key, val in updates.items():
            if key in allowed_fields:
                update_pairs.append(f"{key} = ?")
                values.append(val)

        if not update_pairs:
            return False

        # always update timestamp
        update_pairs.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())

        values.append(int(task_id))

        query = f"UPDATE tasks SET {', '.join(update_pairs)} WHERE id = ?"

        with _DB_LOCK:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute(query, values)
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()

        return bool(success)

    # ----------------------------------------------------------
    # Query tasks
    # ----------------------------------------------------------
    def query_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        with _DB_LOCK:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM tasks WHERE 1=1"
            params = []

            if status:
                query += " AND status = ?"
                params.append(status)

            if priority:
                query += " AND priority = ?"
                params.append(priority)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(int(limit or 100))

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

    # ----------------------------------------------------------
    # Get single task
    # ----------------------------------------------------------
    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        with _DB_LOCK:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM tasks WHERE id = ?", (int(task_id),))
            row = cursor.fetchone()
            conn.close()

            return dict(row) if row else None


# ============================================================
# Tool wrapper (ADK compliant)
# ============================================================
class TaskDBTool:
    """ADK-compliant tool wrapper for TaskDB."""

    def __init__(self):
        self.db = TaskDB()

    def execute(self, action: str, **kwargs) -> Any:
        action = (action or "").strip()
        if action == "add_task":
            return self.db.add_task(
                title=kwargs.get("title", "Task"),
                description=kwargs.get("description", ""),
                duration_minutes=int(kwargs.get("duration_minutes", 60) or 0),
                priority=kwargs.get("priority", "medium"),
                preferred_time_block=kwargs.get("preferred_time_block", "morning")
            )

        elif action == "update_task":
            task_id = kwargs.get("task_id") or kwargs.get("id")
            if task_id is None:
                raise ValueError("update_task requires task_id")
            updates = kwargs.copy()
            updates.pop("task_id", None)
            updates.pop("id", None)
            return self.db.update_task(int(task_id), updates)

        elif action == "query_tasks":
            return self.db.query_tasks(status=kwargs.get("status"), priority=kwargs.get("priority"), limit=int(kwargs.get("limit", 100)))

        elif action == "get_task":
            task_id = kwargs.get("task_id") or kwargs.get("id")
            if task_id is None:
                return None
            return self.db.get_task(int(task_id))

        else:
            raise ValueError(f"Unknown task_db action: {action}")

    @property
    def name(self) -> str:
        return "task_db_tool"

    @property
    def description(self) -> str:
        return "Database tool for managing tasks (add, update, query, get)"


# Global instance
task_db_tool = TaskDBTool()
