"""Novel-OS 状态管理器 —— SQLite 版跨章状态中心（多项目版本）。

替代 V9.0 的 JSON 状态管理，解决并发与版本控制问题，同时保留 JSON 导出视图。
支持 project_id 隔离，所有查询自动带 project_id 过滤。
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator


class StateManager:
    """管理小说跨章状态的 SQLite 后端。

    核心表:
    - projects:           项目注册表
    - runtime_logs:       运行日志
    - character_states:   人物动态（位置、情感、秘密、能力、对话指纹等）
    - item_states:        道具/关键物品状态
    - debts:              债务（伏笔的一种，带回收章节）
    - foreshadowing:      伏笔总表
    - cast_schedule:      配角出场调度
    - emotion_history:    情感坐标历史
    - chapter_snapshots:  章节快照（用于回滚）
    - consistency_rules:  跨章一致性约束
    - chapter_history:    已写章节摘要
    """

    def __init__(self, db_path: Path, project_id: str = "") -> None:
        self.db_path = db_path
        self.project_id = project_id
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """初始化所有表（若不存在）。"""
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    project_id      TEXT PRIMARY KEY,
                    name            TEXT NOT NULL,
                    genre           TEXT NOT NULL,
                    platform        TEXT NOT NULL,
                    base_path       TEXT NOT NULL,
                    status          TEXT DEFAULT 'pending',
                    current_chapter INTEGER DEFAULT 0,
                    total_chapters  INTEGER NOT NULL,
                    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS runtime_logs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id  TEXT NOT NULL,
                    log_id      TEXT NOT NULL,
                    level       TEXT NOT NULL,
                    agent       TEXT NOT NULL,
                    chapter_num INTEGER,
                    message     TEXT NOT NULL,
                    metadata    TEXT,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                );
                CREATE INDEX IF NOT EXISTS idx_logs_project ON runtime_logs(project_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_logs_agent ON runtime_logs(project_id, agent);

                CREATE TABLE IF NOT EXISTS character_states (
                    project_id      TEXT NOT NULL,
                    chapter         INTEGER NOT NULL,
                    character_name  TEXT NOT NULL,
                    location        TEXT,
                    emotional_state TEXT,
                    known_secrets   TEXT,
                    unknown_secrets TEXT,
                    abilities_active TEXT,
                    abilities_locked TEXT,
                    dialog_fingerprint TEXT,
                    body_language   TEXT,
                    physical_description TEXT,
                    PRIMARY KEY (project_id, chapter, character_name),
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                );
                CREATE INDEX IF NOT EXISTS idx_char ON character_states(project_id, character_name, chapter);

                CREATE TABLE IF NOT EXISTS item_states (
                    project_id  TEXT NOT NULL,
                    chapter     INTEGER NOT NULL,
                    item_name   TEXT NOT NULL,
                    location    TEXT,
                    state       TEXT,
                    rule        TEXT,
                    state_history TEXT,
                    PRIMARY KEY (project_id, chapter, item_name),
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                );
                CREATE INDEX IF NOT EXISTS idx_item ON item_states(project_id, item_name, chapter);

                CREATE TABLE IF NOT EXISTS debts (
                    project_id      TEXT NOT NULL,
                    debt_id         TEXT NOT NULL,
                    type            TEXT,
                    content         TEXT NOT NULL,
                    bury_chapter    INTEGER NOT NULL,
                    collect_chapter INTEGER,
                    status          TEXT DEFAULT 'active' CHECK (status IN ('active', 'collected', 'abandoned')),
                    PRIMARY KEY (project_id, debt_id),
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                );
                CREATE INDEX IF NOT EXISTS idx_debt_status ON debts(project_id, status, collect_chapter);
                CREATE INDEX IF NOT EXISTS idx_debt_bury ON debts(project_id, bury_chapter);

                CREATE TABLE IF NOT EXISTS foreshadowing (
                    project_id      TEXT NOT NULL,
                    fs_id           TEXT NOT NULL,
                    bury_chapter    INTEGER NOT NULL,
                    content         TEXT NOT NULL,
                    collect_chapter TEXT,
                    type            TEXT,
                    status          TEXT DEFAULT 'active' CHECK (status IN ('active', 'collected', 'abandoned')),
                    PRIMARY KEY (project_id, fs_id),
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                );
                CREATE INDEX IF NOT EXISTS idx_fs_status ON foreshadowing(project_id, status, collect_chapter);
                CREATE INDEX IF NOT EXISTS idx_fs_bury ON foreshadowing(project_id, bury_chapter);

                CREATE TABLE IF NOT EXISTS cast_schedule (
                    project_id      TEXT NOT NULL,
                    character_name  TEXT NOT NULL,
                    chapter         INTEGER NOT NULL,
                    must_appear     BOOLEAN DEFAULT 0,
                    role_evolution  TEXT,
                    dialog_fingerprint TEXT,
                    physical_description TEXT,
                    PRIMARY KEY (project_id, character_name, chapter),
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                );
                CREATE INDEX IF NOT EXISTS idx_cast_chapter ON cast_schedule(project_id, chapter);

                CREATE TABLE IF NOT EXISTS emotion_history (
                    project_id      TEXT NOT NULL,
                    chapter         INTEGER NOT NULL,
                    mode            TEXT,
                    nue_density     REAL,
                    tian_density    REAL,
                    shuang_density  REAL,
                    coordinate_x    REAL,
                    coordinate_y    REAL,
                    desc            TEXT,
                    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (project_id, chapter),
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                );

                CREATE TABLE IF NOT EXISTS chapter_snapshots (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id      TEXT NOT NULL,
                    chapter         INTEGER NOT NULL,
                    snapshot_type   TEXT NOT NULL,
                    snapshot_data   TEXT NOT NULL,
                    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                );
                CREATE INDEX IF NOT EXISTS idx_snapshot ON chapter_snapshots(project_id, chapter, snapshot_type);

                CREATE TABLE IF NOT EXISTS consistency_rules (
                    project_id          TEXT NOT NULL,
                    rule_type           TEXT NOT NULL,
                    rule_content        TEXT NOT NULL,
                    enforcement_level   TEXT DEFAULT 'hard' CHECK (enforcement_level IN ('hard', 'soft', 'info')),
                    PRIMARY KEY (project_id, rule_type, rule_content),
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                );
                CREATE INDEX IF NOT EXISTS idx_rule_type ON consistency_rules(project_id, rule_type);

                CREATE TABLE IF NOT EXISTS chapter_history (
                    project_id      TEXT NOT NULL,
                    chapter         INTEGER NOT NULL,
                    summary         TEXT,
                    word_count      INTEGER,
                    mode            TEXT,
                    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (project_id, chapter),
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                );
                """
            )

    # ------------------------------------------------------------------
    # 项目级接口
    # ------------------------------------------------------------------
    def init_project(
        self,
        project_id: str,
        name: str,
        genre: str,
        platform: str,
        base_path: str,
        total_chapters: int,
    ) -> None:
        """初始化 projects 表记录。若已存在则替换。"""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO projects
                (project_id, name, genre, platform, base_path, total_chapters, status, current_chapter, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    name,
                    genre,
                    platform,
                    base_path,
                    total_chapters,
                    "pending",
                    0,
                    datetime.now().isoformat(),
                ),
            )

    def get_project_info(self) -> dict[str, Any]:
        """读取当前 project_id 对应的项目信息。"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE project_id = ?",
                (self.project_id,),
            ).fetchone()
            return dict(row) if row else {}

    # ------------------------------------------------------------------
    # 日志接口
    # ------------------------------------------------------------------
    def log_runtime(
        self,
        level: str,
        agent: str,
        chapter_num: int | None,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """写入 runtime_logs 表。"""
        log_id = f"log_{uuid.uuid4().hex[:12]}"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO runtime_logs
                (project_id, log_id, level, agent, chapter_num, message, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.project_id,
                    log_id,
                    level,
                    agent,
                    chapter_num,
                    message,
                    json.dumps(metadata, ensure_ascii=False) if metadata else None,
                ),
            )

    def get_runtime_logs(
        self,
        limit: int = 100,
        level: str | None = None,
        agent: str | None = None,
    ) -> list[dict[str, Any]]:
        """查询当前项目的运行日志。"""
        conditions = ["project_id = ?"]
        params: list[Any] = [self.project_id]
        if level:
            conditions.append("level = ?")
            params.append(level)
        if agent:
            conditions.append("agent = ?")
            params.append(agent)
        where_clause = " AND ".join(conditions)
        with self._connect() as conn:
            cursor = conn.execute(
                f"""
                SELECT * FROM runtime_logs
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (*params, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------
    def init_from_outline(self, outline: dict[str, Any]) -> None:
        """从大纲 JSON 一次性初始化所有表数据。

        outline 结构示例:
        {
          "characters": {"protagonist_female": {"name": "沈若楠", ...}},
          "world": {"key_items": [...], "locks": [...]},
          "plot": {"debts": [...], "foreshadowing": [...], ...}
        }
        """
        characters = outline.get("characters", {})
        world = outline.get("world", {})
        plot = outline.get("plot", {})
        pid = self.project_id

        with self._connect() as conn:
            # 1. 人物初始状态（第 0 章表示"写第 1 章之前"的初始态）
            for role_key, c in characters.items():
                name = c.get("name", role_key)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO character_states (
                        project_id, chapter, character_name, location, emotional_state,
                        known_secrets, unknown_secrets, abilities_active,
                        abilities_locked, dialog_fingerprint, body_language, physical_description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pid, 0, name, None, None,
                        json.dumps(c.get("a_track", {}).get("secrets_known", []), ensure_ascii=False),
                        json.dumps(c.get("b_track", {}).get("secrets_unknown", []), ensure_ascii=False),
                        json.dumps(c.get("a_track", {}).get("ability", []), ensure_ascii=False),
                        json.dumps([], ensure_ascii=False),
                        c.get("dialog_fingerprint", ""),
                        c.get("body_language", ""),
                        c.get("physical_description", ""),
                    ),
                )

            # 2. 道具初始状态
            for item in world.get("key_items", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO item_states
                    (project_id, chapter, item_name, location, state, rule, state_history)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pid,
                        0,
                        item["name"],
                        item.get("initial_location", ""),
                        item.get("initial_state", ""),
                        json.dumps(item.get("rules", []), ensure_ascii=False),
                        json.dumps([{"chapter": 0, "state": item.get("initial_state", "")}], ensure_ascii=False),
                    ),
                )

            # 3. 债务
            for d in plot.get("debts", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO debts
                    (project_id, debt_id, type, content, bury_chapter, collect_chapter, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pid, d["id"], d.get("type", ""), d["content"],
                        d["bury_chapter"], d.get("collect_chapter"), "active",
                    ),
                )

            # 4. 伏笔
            for f in plot.get("foreshadowing", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO foreshadowing
                    (project_id, fs_id, bury_chapter, content, collect_chapter, type, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pid, f["id"], f["bury_chapter"], f["content"],
                        f.get("collect_chapter", ""), f.get("type", ""), "active",
                    ),
                )

            # 5. 一致性约束
            for lock in world.get("locks", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO consistency_rules
                    (project_id, rule_type, rule_content, enforcement_level)
                    VALUES (?, ?, ?, ?)
                    """,
                    (pid, "world_lock", lock, "hard"),
                )

    # ------------------------------------------------------------------
    # 查询接口
    # ------------------------------------------------------------------
    def get_character_state(self, chapter: int, character: str) -> dict[str, Any]:
        """获取某章某人物的完整状态。"""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM character_states
                WHERE project_id = ? AND chapter = ? AND character_name = ?
                """,
                (self.project_id, chapter, character),
            ).fetchone()
            return dict(row) if row else {}

    def update_character_state(self, chapter: int, character: str, **kwargs: Any) -> None:
        """增量更新人物状态；若记录不存在则自动插入。"""
        allowed = {
            "location", "emotional_state", "known_secrets", "unknown_secrets",
            "abilities_active", "abilities_locked", "dialog_fingerprint",
            "body_language", "physical_description",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return

        columns = ", ".join(updates.keys())
        placeholders = ", ".join(["?"] * len(updates))
        pid = self.project_id
        # 使用 INSERT OR REPLACE 简化 upsert 逻辑
        with self._connect() as conn:
            existing = conn.execute(
                """
                SELECT 1 FROM character_states
                WHERE project_id = ? AND chapter = ? AND character_name = ?
                """,
                (pid, chapter, character),
            ).fetchone()
            if existing:
                set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
                conn.execute(
                    f"""
                    UPDATE character_states SET {set_clause}
                    WHERE project_id = ? AND chapter = ? AND character_name = ?
                    """,
                    (*updates.values(), pid, chapter, character),
                )
            else:
                conn.execute(
                    f"""
                    INSERT INTO character_states
                    (project_id, chapter, character_name, {columns})
                    VALUES (?, ?, ?, {placeholders})
                    """,
                    (pid, chapter, character, *updates.values()),
                )

    def get_active_debts(self, current_chapter: int) -> list[dict[str, Any]]:
        """查询在当前章节应该被回收的债务（collect_chapter <= current_chapter 且 status=active）。"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM debts
                WHERE project_id = ?
                  AND status = 'active'
                  AND collect_chapter IS NOT NULL
                  AND collect_chapter <= ?
                ORDER BY collect_chapter
                """,
                (self.project_id, current_chapter),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_active_foreshadowing(self, current_chapter: int) -> list[dict[str, Any]]:
        """查询在当前章节应该被回收的伏笔。"""
        with self._connect() as conn:
            # collect_chapter 可能是 "3/10" 这样的多章回收，简单处理：提取第一个数字
            cursor = conn.execute(
                """
                SELECT * FROM foreshadowing
                WHERE project_id = ?
                  AND status = 'active'
                  AND collect_chapter IS NOT NULL
                  AND collect_chapter != ''
                ORDER BY bury_chapter
                """,
                (self.project_id,),
            )
            rows = []
            for row in cursor.fetchall():
                collect = str(row["collect_chapter"])
                first_num = int("".join(filter(str.isdigit, collect.split("/")[0])) or 9999)
                if first_num <= current_chapter:
                    rows.append(dict(row))
            return rows

    # ------------------------------------------------------------------
    # 快照与回滚
    # ------------------------------------------------------------------
    def create_snapshot(self, chapter: int, snapshot_type: str, data: dict[str, Any]) -> None:
        """为指定章节创建快照。"""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chapter_snapshots
                (project_id, chapter, snapshot_type, snapshot_data)
                VALUES (?, ?, ?, ?)
                """,
                (self.project_id, chapter, snapshot_type, json.dumps(data, ensure_ascii=False)),
            )

    def rollback_to_snapshot(self, chapter: int, snapshot_type: str) -> dict[str, Any]:
        """回滚到指定章节的最新快照，并返回快照数据。"""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT snapshot_data FROM chapter_snapshots
                WHERE project_id = ? AND chapter = ? AND snapshot_type = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (self.project_id, chapter, snapshot_type),
            ).fetchone()
            if row is None:
                raise ValueError(f"未找到快照: chapter={chapter}, type={snapshot_type}")
            return json.loads(row["snapshot_data"])

    # ------------------------------------------------------------------
    # 章节结束更新
    # ------------------------------------------------------------------
    def update_after_chapter(
        self, chapter_num: int, summary: str, word_count: int, mode: str
    ) -> None:
        """每章写完后更新历史与情感坐标。"""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO chapter_history
                (project_id, chapter, summary, word_count, mode, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (self.project_id, chapter_num, summary, word_count, mode, datetime.now().isoformat()),
            )

    # ------------------------------------------------------------------
    # 查询接口（供 API 层使用）
    # ------------------------------------------------------------------
    def list_characters(self) -> list[dict[str, Any]]:
        """列出当前项目的所有角色（去重）。"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT DISTINCT character_name, location, emotional_state
                FROM character_states
                WHERE project_id = ?
                ORDER BY character_name
                """,
                (self.project_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_emotion_history(self) -> list[dict[str, Any]]:
        """查询情感坐标历史。"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT chapter, mode, coordinate_x, coordinate_y, desc
                FROM emotion_history
                WHERE project_id = ?
                ORDER BY chapter
                """,
                (self.project_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def list_chapters(self) -> list[dict[str, Any]]:
        """列出当前项目的章节历史。"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT chapter, summary, word_count, mode, created_at
                FROM chapter_history
                WHERE project_id = ?
                ORDER BY chapter
                """,
                (self.project_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # 导出视图
    # ------------------------------------------------------------------
    def export_json_view(self, output_path: Path) -> None:
        """导出人类可读的 JSON 视图，便于外部审阅。"""
        view: dict[str, Any] = {
            "exported_at": datetime.now().isoformat(),
            "project_id": self.project_id,
            "characters": {},
            "items": {},
            "debts": [],
            "foreshadowing": [],
            "chapter_history": [],
        }
        pid = self.project_id

        with self._connect() as conn:
            # 人物：取每人的最新 chapter 状态
            for row in conn.execute(
                """
                SELECT * FROM character_states
                WHERE project_id = ?
                ORDER BY character_name, chapter DESC
                """,
                (pid,),
            ).fetchall():
                name = row["character_name"]
                if name not in view["characters"]:
                    view["characters"][name] = dict(row)

            # 道具
            for row in conn.execute(
                """
                SELECT * FROM item_states
                WHERE project_id = ?
                ORDER BY item_name, chapter DESC
                """,
                (pid,),
            ).fetchall():
                name = row["item_name"]
                if name not in view["items"]:
                    view["items"][name] = dict(row)

            view["debts"] = [
                dict(r) for r in conn.execute(
                    "SELECT * FROM debts WHERE project_id = ?", (pid,)
                ).fetchall()
            ]
            view["foreshadowing"] = [
                dict(r) for r in conn.execute(
                    "SELECT * FROM foreshadowing WHERE project_id = ?", (pid,)
                ).fetchall()
            ]
            view["chapter_history"] = [
                dict(r) for r in conn.execute(
                    """
                    SELECT * FROM chapter_history
                    WHERE project_id = ?
                    ORDER BY chapter
                    """,
                    (pid,),
                ).fetchall()
            ]

        output_path.write_text(
            json.dumps(view, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
