import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from taskflow.cli import main
from taskflow.models import TaskError
from taskflow.service import TaskService
from taskflow.storage import TaskStore


@pytest.fixture
def store(tmp_path):
    database = TaskStore(tmp_path / "tasks.db")
    yield database
    database.close()


def test_crud_and_status(store):
    service = TaskService(store)
    task = service.add("  学习 Python  ", 3, "2026-10-10")
    assert task.title == "学习 Python"
    assert task.status == "todo"
    assert task.created_at.endswith("+00:00")
    edited = service.update(task.id, title="写测试", due=None, priority=1)
    assert (edited.title, edited.due, edited.priority) == ("写测试", None, 1)
    assert service.set_status(task.id, "done").status == "done"
    assert service.set_status(task.id, "todo").status == "todo"
    store.delete(task.id)
    with pytest.raises(TaskError, match="不存在"):
        store.get(task.id)


@pytest.mark.parametrize("title", ["", "   ", "x" * 201])
def test_invalid_title_does_not_write(store, title):
    with pytest.raises(TaskError):
        TaskService(store).add(title)
    assert store.list() == []


@pytest.mark.parametrize("due", ["2026-02-30", "20261008", "2026-1-01", "abc", ""])
def test_invalid_date(store, due):
    with pytest.raises(TaskError):
        TaskService(store).add("task", due=due)
    assert store.list() == []


@pytest.mark.parametrize("priority", [0, 4, -1])
def test_invalid_priority(store, priority):
    with pytest.raises(TaskError):
        TaskService(store).add("task", priority=priority)


def test_filters_and_order(store):
    service = TaskService(store)
    a = service.add("Python 100%", 3)
    b = service.add("python tests", 3, "2026-10-10")
    service.add("Japanese", 1)
    service.set_status(a.id, "done")
    assert [t.id for t in store.list(search="PYTHON")] == [b.id, a.id]
    assert [t.id for t in store.list("done")] == [a.id]
    assert [t.id for t in store.list(search="%")] == [a.id]


def test_persistence_and_id_not_reused(tmp_path):
    path = tmp_path / "nested" / "tasks.db"
    first = TaskStore(path)
    task = TaskService(first).add("持久保存")
    first.close()
    second = TaskStore(path)
    try:
        assert second.get(task.id).title == "持久保存"
        second.delete(task.id)
        assert TaskService(second).add("new").id > task.id
    finally:
        second.close()


def test_failed_edit_preserves_data(store):
    service = TaskService(store)
    task = service.add("original")
    with pytest.raises(TaskError):
        service.update(task.id, title="changed", due="bad")
    assert store.get(task.id).title == "original"
    with pytest.raises(TaskError):
        service.update(task.id)
    with pytest.raises(TaskError):
        service.set_status(task.id, "invalid")
    with pytest.raises(TaskError):
        store.delete(999)


def test_sql_input_is_data(store):
    title = "'); DROP TABLE tasks; --"
    task = TaskService(store).add(title)
    assert store.get(task.id).title == title
    assert len(store.list()) == 1


def test_cli_lifecycle(tmp_path, capsys):
    prefix = ["--db", str(tmp_path / "tasks.db")]
    assert main(prefix + ["add", "做项目", "--due", "2026-10-10"]) == 0
    assert main(prefix + ["edit", "1", "--title", "完善项目", "--clear-due"]) == 0
    assert main(prefix + ["done", "1"]) == 0
    assert main(prefix + ["reopen", "1"]) == 0
    assert main(prefix + ["show", "1"]) == 0
    capsys.readouterr()
    assert main(prefix + ["list", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["title"] == "完善项目"
    assert main(prefix + ["delete", "1"]) == 1
    assert "--yes" in capsys.readouterr().err
    assert main(prefix + ["delete", "1", "--yes"]) == 0
    assert main(prefix + ["show", "1"]) == 1
    assert "不存在" in capsys.readouterr().err


def test_bad_database_is_reported(tmp_path, capsys):
    path = tmp_path / "broken.db"
    path.write_text("not sqlite")
    assert main(["--db", str(path), "list"]) == 1
    assert "错误" in capsys.readouterr().err
    assert path.read_text() == "not sqlite"


def test_subprocess_entry_and_env(tmp_path):
    env = dict(os.environ, TASKFLOW_DB=str(tmp_path / "tasks.db"))
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    def run(*args):
        return subprocess.run([sys.executable, "-m", "taskflow", *args],
                              env=env, text=True, capture_output=True)
    assert run("add", "跨进程保存").returncode == 0
    result = run("list", "--json")
    assert result.returncode == 0
    assert json.loads(result.stdout)[0]["title"] == "跨进程保存"
    assert run("add", "bad", "--priority", "9").returncode == 2
    assert run("--help").returncode == 0
