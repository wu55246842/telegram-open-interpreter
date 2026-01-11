from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class Task:
    task_id: str
    chat_id: int
    user_id: int
    command: str
    plan_json: str
    status: str
    created_at: float
    updated_at: float
    timeout_seconds: int
    result_json: str | None


class TaskQueue:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    command TEXT NOT NULL,
                    plan_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    timeout_seconds INTEGER NOT NULL,
                    result_json TEXT
                )
                """
            )

    def create_task(self, chat_id: int, user_id: int, command: str, plan_json: str, timeout_seconds: int) -> str:
        task_id = str(uuid.uuid4())
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tasks (task_id, chat_id, user_id, command, plan_json, status, created_at, updated_at, timeout_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (task_id, chat_id, user_id, command, plan_json, "pending_approval", now, now, timeout_seconds),
            )
        return task_id

    def approve_task(self, task_id: str) -> bool:
        return self._update_status(task_id, "queued", expected="pending_approval")

    def cancel_task(self, task_id: str) -> bool:
        return self._update_status(task_id, "cancelled")

    def mark_running(self, task_id: str) -> bool:
        return self._update_status(task_id, "running", expected="queued")

    def mark_done(self, task_id: str, result: dict[str, Any]) -> None:
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status = ?, updated_at = ?, result_json = ?
                WHERE task_id = ?
                """,
                ("completed", now, json.dumps(result, ensure_ascii=False), task_id),
            )

    def mark_failed(self, task_id: str, message: str) -> None:
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status = ?, updated_at = ?, result_json = ?
                WHERE task_id = ?
                """,
                ("failed", now, json.dumps({"error": message}, ensure_ascii=False), task_id),
            )

    def get_task(self, task_id: str) -> Task | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT task_id, chat_id, user_id, command, plan_json, status, created_at, updated_at, timeout_seconds, result_json FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        return Task(*row)

    def list_recent(self, limit: int = 5) -> list[Task]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT task_id, chat_id, user_id, command, plan_json, status, created_at, updated_at, timeout_seconds, result_json
                FROM tasks
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [Task(*row) for row in rows]

    def next_queued(self) -> Task | None:
        if self.has_running():
            return None
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT task_id, chat_id, user_id, command, plan_json, status, created_at, updated_at, timeout_seconds, result_json
                FROM tasks
                WHERE status = 'queued'
                ORDER BY created_at ASC
                LIMIT 1
                """,
            ).fetchone()
        if row is None:
            return None
        return Task(*row)

    def has_running(self) -> bool:
        with self._connect() as conn:
            row = conn.execute(\"SELECT 1 FROM tasks WHERE status = 'running' LIMIT 1\").fetchone()
        return row is not None

    def _update_status(self, task_id: str, status: str, expected: str | None = None) -> bool:
        now = time.time()
        with self._connect() as conn:
            if expected:
                cursor = conn.execute(
                    """
                    UPDATE tasks
                    SET status = ?, updated_at = ?
                    WHERE task_id = ? AND status = ?
                    """,
                    (status, now, task_id, expected),
                )
            else:
                cursor = conn.execute(
                    """
                    UPDATE tasks
                    SET status = ?, updated_at = ?
                    WHERE task_id = ?
                    """,
                    (status, now, task_id),
                )
        return cursor.rowcount > 0
