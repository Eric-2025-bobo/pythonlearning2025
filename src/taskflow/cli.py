"""CLI adapter: arguments in, business operations out."""
import argparse
import json
import os
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path

from .models import TaskError
from .service import TaskService
from .storage import TaskStore


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="TaskFlow 本地任务管理工具")
    root.add_argument("--db", type=Path, default=Path(
        os.environ.get("TASKFLOW_DB", str(Path.home() / ".taskflow" / "tasks.db"))
    ), help="数据库路径（也可设置 TASKFLOW_DB）")
    commands = root.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="新增任务")
    add.add_argument("title")
    add.add_argument("--priority", type=int, choices=(1, 2, 3), default=2)
    add.add_argument("--due")
    listing = commands.add_parser("list", help="查询任务")
    listing.add_argument("--status", choices=("all", "todo", "done"), default="all")
    listing.add_argument("--search", default="")
    listing.add_argument("--json", action="store_true", help="机器可读输出")
    edit = commands.add_parser("edit", help="修改任务")
    edit.add_argument("id", type=int)
    edit.add_argument("--title")
    edit.add_argument("--priority", type=int, choices=(1, 2, 3))
    due = edit.add_mutually_exclusive_group()
    due.add_argument("--due")
    due.add_argument("--clear-due", action="store_true")
    for command, help_text in (
        ("show", "查看任务"), ("done", "完成任务"),
        ("reopen", "重新打开"), ("delete", "删除任务"),
    ):
        sub = commands.add_parser(command, help=help_text)
        sub.add_argument("id", type=int)
        if command == "delete":
            sub.add_argument("--yes", action="store_true", help="明确确认永久删除")
    return root


def print_task(task):
    print(f"{task.id} | {task.status} | P{task.priority} | {task.due or '-'} | {task.title}")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    store = None
    try:
        if args.command == "delete" and not args.yes:
            raise TaskError("删除需要 --yes；此操作不可撤销")
        store = TaskStore(args.db.expanduser())
        service = TaskService(store)
        if args.command == "add":
            print_task(service.add(args.title, args.priority, args.due))
        elif args.command == "list":
            tasks = store.list(args.status, args.search)
            if args.json:
                print(json.dumps([asdict(task) for task in tasks], ensure_ascii=False))
            elif not tasks:
                print("没有符合条件的任务")
            else:
                for task in tasks:
                    print_task(task)
        elif args.command == "show":
            print_task(store.get(args.id))
        elif args.command == "edit":
            changes = {key: getattr(args, key) for key in ("title", "priority", "due")
                       if getattr(args, key) is not None}
            if args.clear_due:
                changes["due"] = None
            print_task(service.update(args.id, **changes))
        elif args.command in ("done", "reopen"):
            print_task(service.set_status(args.id, "done" if args.command == "done" else "todo"))
        elif args.command == "delete":
            store.delete(args.id)
            print(f"已删除任务 {args.id}")
        return 0
    except (TaskError, sqlite3.Error, OSError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1
    finally:
        if store is not None:
            store.close()
