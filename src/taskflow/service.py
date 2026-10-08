"""Business rules, independent of terminal formatting."""
from datetime import date, datetime, timezone

from .models import TaskError
from .storage import TaskStore


def validate_title(title: str) -> str:
    title = title.strip()
    if not title or len(title) > 200:
        raise TaskError("标题应为 1～200 个字符")
    return title


def validate_due(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise TaskError("截止日期应为有效的 YYYY-MM-DD") from None
    if parsed.isoformat() != value:
        raise TaskError("截止日期应为有效的 YYYY-MM-DD")
    return value


def validate_priority(value: int) -> int:
    if value not in (1, 2, 3):
        raise TaskError("优先级应为 1、2 或 3")
    return value


class TaskService:
    def __init__(self, store: TaskStore):
        self.store = store

    def add(self, title: str, priority: int = 2, due: str | None = None):
        return self.store.add(
            validate_title(title), validate_priority(priority), validate_due(due),
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

    def update(self, task_id: int, **changes):
        if "title" in changes:
            changes["title"] = validate_title(changes["title"])
        if "priority" in changes:
            changes["priority"] = validate_priority(changes["priority"])
        if "due" in changes:
            changes["due"] = validate_due(changes["due"])
        return self.store.update(task_id, changes)

    def set_status(self, task_id: int, status: str):
        if status not in ("todo", "done"):
            raise TaskError("状态应为 todo 或 done")
        return self.store.update(task_id, {"status": status})
