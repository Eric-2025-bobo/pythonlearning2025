"""Domain types shared by the service and storage layers."""
from dataclasses import dataclass


class TaskError(ValueError):
    """An invalid operation that can be explained to the user."""


@dataclass(frozen=True)
class Task:
    id: int
    title: str
    priority: int
    due: str | None
    status: str
    created_at: str
