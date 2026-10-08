"""SQLite persistence. All writes use transactions and parameterized SQL."""
import sqlite3
from pathlib import Path

from .models import Task, TaskError


class TaskStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, timeout=5)
        self.connection.row_factory = sqlite3.Row
        try:
            with self.connection:
                self.connection.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL CHECK(length(trim(title)) > 0),
                        priority INTEGER NOT NULL CHECK(priority BETWEEN 1 AND 3),
                        due TEXT,
                        status TEXT NOT NULL DEFAULT 'todo'
                            CHECK(status IN ('todo', 'done')),
                        created_at TEXT NOT NULL
                    )
                """)
        except Exception:
            self.close()
            raise

    def close(self):
        self.connection.close()

    def get(self, task_id: int) -> Task:
        row = self.connection.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise TaskError(f"任务 {task_id} 不存在")
        return Task(**dict(row))

    def add(self, title: str, priority: int, due: str | None, created_at: str) -> Task:
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO tasks(title, priority, due, created_at) VALUES (?, ?, ?, ?)",
                (title, priority, due, created_at),
            )
        return self.get(cursor.lastrowid)

    def list(self, status: str = "all", search: str = "") -> list[Task]:
        # instr treats '%' and '_' literally instead of as LIKE wildcards.
        rows = self.connection.execute("""
            SELECT * FROM tasks
            WHERE (? = 'all' OR status = ?) AND instr(lower(title), lower(?)) > 0
            ORDER BY priority DESC, due IS NULL, due, id
        """, (status, status, search)).fetchall()
        return [Task(**dict(row)) for row in rows]

    def update(self, task_id: int, changes: dict) -> Task:
        self.get(task_id)
        allowed = {"title", "priority", "due", "status"}
        if not changes or not set(changes) <= allowed:
            raise TaskError("没有可更新的字段")
        assignments = ", ".join(f"{key} = ?" for key in changes)
        with self.connection:
            self.connection.execute(
                f"UPDATE tasks SET {assignments} WHERE id = ?",
                (*changes.values(), task_id),
            )
        return self.get(task_id)

    def delete(self, task_id: int):
        with self.connection:
            cursor = self.connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            if cursor.rowcount == 0:
                raise TaskError(f"任务 {task_id} 不存在")
