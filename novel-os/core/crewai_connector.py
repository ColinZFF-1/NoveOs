"""Novel-OS CrewAI 连接器 —— 运行时从 crewai.db 动态查询 Agent / Task ID。"""
from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

logger = logging.getLogger("novel-os.crew")


class CrewAIConnector:
    """封装对 CrewAI Studio SQLite 数据库的只读查询。

    V9.0 的痛点是 Agent ID 硬编码在 Python 源码中；Novel-OS 改为运行时查询，
    支持用户增删 Agent 后无需改代码。

    降级策略：
    1. 如果 crewai.db 存在，优先从 SQLite 查询；
    2. 否则尝试从 crewai_entities_export.json 加载；
    3. 最后回退到 MOCK 模式。
    """

    def __init__(
        self,
        db_path: Path,
        mock_mode: bool = False,
        export_json_path: Path | None = None,
    ) -> None:
        self.db_path = db_path
        self._agents: dict[str, dict[str, Any]] = {}
        self._tasks: dict[str, dict[str, Any]] = {}

        if db_path.exists():
            self.mock_mode = False
            logger.info("使用 crewai.db: %s", db_path)
        elif export_json_path and export_json_path.exists():
            self.mock_mode = False
            self._load_from_export(export_json_path)
            logger.info("从 JSON 导出加载 Agent/Task: %s", export_json_path)
        else:
            self.mock_mode = True
            logger.warning("crewai.db 不存在且无导出文件，启用 MOCK 模式")

    def _load_from_export(self, path: Path) -> None:
        """从 crewai_entities_export.json 加载 Agent 和 Task。"""
        data = json.loads(path.read_text(encoding="utf-8"))
        for entity_id, entity in data.items():
            if entity.get("type") == "agent":
                self._agents[entity_id] = entity.get("data", {})
            elif entity.get("type") == "task":
                self._tasks[entity_id] = entity.get("data", {})

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Agent 查询
    # ------------------------------------------------------------------
    def get_agent_id(self, role: str, agent_type: str) -> str:
        """根据 role 和 agent_type 模糊匹配，返回最新创建的 Agent ID。"""
        if self.mock_mode:
            return f"mock-agent-{agent_type}"

        if self._agents:
            for aid, data in self._agents.items():
                if data.get("role") == role or agent_type in data.get("role", ""):
                    return aid
            raise ValueError(f"未找到 Agent: role={role!r}")

        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT id, role, backstory, goal, created_at
                FROM agent
                WHERE role = ?
                   OR backstory LIKE ?
                   OR goal LIKE ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (role, f"%{agent_type}%", f"%{agent_type}%"),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError(
                    f"未找到 Agent: role={role!r}, agent_type={agent_type!r}"
                )
            return str(row["id"])

    def get_agent_config(self, agent_id: str) -> dict[str, Any]:
        """获取 Agent 完整配置（role, goal, backstory, temperature 等）。"""
        if self.mock_mode:
            return {}
        if agent_id in self._agents:
            return self._agents[agent_id]
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM agent WHERE id = ?", (agent_id,)
            ).fetchone()
            return dict(row) if row else {}

    # ------------------------------------------------------------------
    # Task 查询
    # ------------------------------------------------------------------
    def get_task_id(self, agent_id: str, task_type: str) -> str:
        """根据 agent_id 和 task_type 模糊匹配，返回最新创建的 Task ID。"""
        if self.mock_mode:
            return f"mock-task-{task_type}"

        if self._tasks:
            for tid, data in self._tasks.items():
                if data.get("agent_id") == agent_id and task_type in data.get("description", ""):
                    return tid
            for tid, data in self._tasks.items():
                if data.get("agent_id") == agent_id:
                    return tid
            raise ValueError(f"未找到 Task: agent_id={agent_id!r}")

        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT id, description, created_at
                FROM task
                WHERE agent_id = ?
                  AND description LIKE ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (agent_id, f"%{task_type}%"),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError(
                    f"未找到 Task: agent_id={agent_id!r}, task_type={task_type!r}"
                )
            return str(row["id"])

    def get_task_config(self, task_id: str) -> dict[str, Any]:
        """获取 Task 完整配置（description, expected_output 等）。"""
        if self.mock_mode:
            return {}
        if task_id in self._tasks:
            return self._tasks[task_id]
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM task WHERE id = ?", (task_id,)
            ).fetchone()
            return dict(row) if row else {}

    # ------------------------------------------------------------------
    # 列表
    # ------------------------------------------------------------------
    def list_agents(self) -> list[dict]:
        """列出所有 Agent，用于调试。"""
        if self.mock_mode:
            return []
        if self._agents:
            return [{"id": k, **v} for k, v in self._agents.items()]
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT id, role, goal, created_at FROM agent ORDER BY created_at DESC"
            )
            return [dict(row) for row in cursor.fetchall()]

    def list_tasks(self, agent_id: str | None = None) -> list[dict]:
        """列出所有 Task；可过滤 agent_id。"""
        if self.mock_mode:
            return []
        if self._tasks:
            tasks = [{"id": k, **v} for k, v in self._tasks.items()]
            if agent_id:
                tasks = [t for t in tasks if t.get("agent_id") == agent_id]
            return tasks
        with self._connect() as conn:
            if agent_id:
                cursor = conn.execute(
                    "SELECT id, description, agent_id, created_at FROM task WHERE agent_id = ? ORDER BY created_at DESC",
                    (agent_id,),
                )
            else:
                cursor = conn.execute(
                    "SELECT id, description, agent_id, created_at FROM task ORDER BY created_at DESC"
                )
            return [dict(row) for row in cursor.fetchall()]
