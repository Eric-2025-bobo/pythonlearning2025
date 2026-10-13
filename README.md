# TaskFlow · Python 工程实践

一个可以真正用于管理学习、求职和日常任务的本地命令行工具。
支持新增、查询、修改、完成、重新打开、删除、优先级、截止日期、关键词检索和 JSON 输出。
运行时仅依赖 Python 标准库；数据保存在 SQLite，不需要账号、网络或云服务。

## 安装与运行

需要 Python 3.11 或更新版本。

```bash
git clone https://github.com/Eric-2025-bobo/pythonlearning2025.git
cd pythonlearning2025
python -m venv .venv
```

Windows PowerShell 激活：`.venv\Scripts\Activate.ps1`；
macOS/Linux 激活：`source .venv/bin/activate`。
如果 Windows 的脚本策略阻止激活，可以直接使用 `.venv\Scripts\python.exe` 替代下面的 python，并使用 `python -m taskflow` 替代 taskflow。

```bash
python -m pip install -e ".[dev]"
taskflow --help
taskflow add "完成第一个 Python 项目" --priority 3 --due 2026-10-15
taskflow list
taskflow show 1
taskflow edit 1 --title "补充项目文档" --priority 2
taskflow done 1
taskflow list --status done
taskflow reopen 1
taskflow edit 1 --clear-due
taskflow list --search "项目" --json
taskflow delete 1 --yes
python -m pytest -q
```

上面的 ID 1 假设数据库初始为空；实际操作请使用 add 或 list 返回的 ID。
也可通过 `python -m taskflow` 运行同一个入口。

## 数据与命令约定

- 默认数据库：用户主目录下的 `.taskflow/tasks.db`，与当前工作目录无关。
- 自定义数据库：`taskflow --db ./demo.db add "测试任务"`。全局参数 --db 放在子命令前。
- 环境变量 TASKFLOW_DB 可以设置默认路径；显式 --db 优先。
- P1 低、P2 中、P3 高；查询按优先级降序、截止日期升序、ID 升序排列，无截止日期排在同优先级的有日期任务后。
- 状态：todo / done。日期必须严格为 YYYY-MM-DD，允许过去日期和闰日。
- 标题自动去除首尾空白，长度限制为 1～200 个字符。
- 查询中的 % 和 _ 按普通字符处理；英文检索不区分大小写，中文按子串匹配。
- 成功退出码 0，业务或存储错误 1，命令参数错误 2。错误输出到 stderr。
- 重定向到文件或管道时，stdout / stderr 统一使用 UTF-8（优先于 PYTHONIOENCODING），保留完整中文；交互终端保持原有编码。Python 调用方应在 subprocess.run 中指定 encoding="utf-8" 解码输出。
- 删除必须明确加 --yes，不可撤销。数据不会上传 GitHub，.gitignore 已忽略数据库。
- 备份：关闭所有 TaskFlow 进程后复制 tasks.db；恢复时用备份替换原文件。不要在数据库写入时直接复制。
- SQLite 事务保护单次写入。当前定位为单用户本地工具，不提供多人协作、提醒、加密或云同步。

## 代码结构与设计

| 文件 | 职责 |
| --- | --- |
| src/taskflow/models.py | 不可变 Task 数据对象和可解释的业务错误 |
| src/taskflow/storage.py | SQLite 表结构、参数化 SQL、事务、持久化 |
| src/taskflow/service.py | 标题、日期、优先级校验以及业务操作 |
| src/taskflow/cli.py | argparse 参数、命令分发、输出、退出码、错误处理 |
| tests/test_tasks.py | 真实临时数据库测试和跨进程 CLI 测试 |
| .github/workflows/tests.yml | Linux/Windows、Python 3.11～3.13 测试矩阵 |
| docs/LEARNING.md | 阅读顺序、练习和作品演进路线 |

采用 src 布局和 pyproject.toml，确保导入、安装和 CLI 入口一致。
不引入 ORM 或复杂框架，方便逐行理解 SQL 与 Python 的关系。
新增时先完成所有业务校验，再写数据库；失败的修改不会写入半成品。
SQL 值全部绑定参数；动态更新字段由白名单限制。数据库主键不复用，避免旧 ID 指向新任务。
datetime 使用 UTC 保存创建时间；截止日期是没有时区的日历日期。
数据库连接由 CLI 在 finally 中关闭，错误不会留下未关闭的连接。

## 自动化测试

```bash
python -m pytest -q
```

测试使用 pytest 的 tmp_path 创建隔离数据库，不碰个人任务。
覆盖 CRUD、持久化、状态切换、非法输入、更新失败不改数据、SQL 特殊字符、过滤排序、
删除确认、损坏数据库、JSON 输出、环境变量以及真实子进程入口。
编码回归测试还覆盖平台默认编码、ASCII / Windows cp1252、文件重定向、中文帮助和错误信息。
GitHub Actions 配置会在 push / PR 时自动测试；本地通过不代表远程矩阵已通过。

运行依赖为空；开发依赖 pytest 固定为 8.3.5。
目前没有完整传递依赖锁文件，后续可使用 uv 锁定整个开发环境。

## 手动提交（无法直接写入时）

在解压得到的项目根目录执行；仅适用于目标仓库仍为空：
```bash
git init -b main
git add .
git commit -m "feat: add SQLite task manager with tests and Chinese docs"
git remote add origin https://github.com/Eric-2025-bobo/pythonlearning2025.git
git push -u origin main
```

提交前设置自己的 git user.name / user.email。若远程已有提交，请先 clone 后将项目文件复制到克隆目录，
创建功能分支提交并开 PR，不要强制覆盖 main。

## 下一步

先每天用它记录自己的学习任务，再按 [学习路线](docs/LEARNING.md) 独立实现一项扩展并补测试。
当前版本由助手协助搭建；简历中应诚实说明自己的贡献，完成独立扩展和实际使用后再描述为个人项目。
