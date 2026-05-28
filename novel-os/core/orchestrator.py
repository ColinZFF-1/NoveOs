"""Novel-OS 全局编排器 —— 多项目调度中心。"""
from __future__ import annotations

import logging
import sqlite3
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from core.batch_writer import BatchWriter
from core.config_loader import BookConfig
from core.crewai_connector import CrewAIConnector
from core.event_bus import (
    CHAPTER_COMPLETE,
    CHAPTER_ERROR,
    CHAPTER_START,
    EVENT_TYPES,
    EventBus,
    PIPELINE_COMPLETE,
    PIPELINE_PAUSE,
    PIPELINE_START,
)
from core.state_manager import StateManager

logger = logging.getLogger("novel-os.orchestrator")


@dataclass
class ProjectRuntime:
    """项目运行时上下文。"""

    project_id: str
    book_config: BookConfig
    state_manager: StateManager
    batch_writer: BatchWriter
    status: str = "pending"  # pending / outlining / configuring / writing / auditing / completed / paused / error
    current_chapter: int = 0
    pipeline_id: str | None = None
    future: Future | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class Orchestrator:
    """管理多个项目的生命周期与流水线调度。

    设计约束:
    - 单项目串行: 同一项目章节必须串行
    - 跨项目并行: 不同项目可并发 Worker
    - 失败隔离: Worker 崩溃只影响当前章节，Orchestrator 自动标记 error
    - 可观测: 每个状态变更通过 EventBus 推送
    """

    def __init__(self, max_workers: int = 10) -> None:
        self.max_workers = max_workers
        self._projects: dict[str, ProjectRuntime] = {}
        self._lock = threading.RLock()
        self._paused: set[str] = set()
        self._stopped: set[str] = set()
        self._event_bus = EventBus()
        self._event_handlers: list[Callable[[str, dict[str, Any]], None]] = []
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="novelos_worker"
        )
        self._global_db_path = Path("D:/noveos/books/orchestrator.db")
        self._global_db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_global_db()
        self._load_projects_from_db()

    # ------------------------------------------------------------------
    # 全局数据库
    # ------------------------------------------------------------------
    def _init_global_db(self) -> None:
        with sqlite3.connect(str(self._global_db_path)) as conn:
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
                """
            )

    def _persist_project(self, project_id: str, info: ProjectRuntime) -> None:
        with sqlite3.connect(str(self._global_db_path)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO projects
                (project_id, name, genre, platform, base_path, status, current_chapter, total_chapters, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    info.book_config.project,
                    info.book_config.genre,
                    info.book_config.platform,
                    str(info.book_config.base_path),
                    info.status,
                    info.current_chapter,
                    info.book_config.chapters_target,
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()

    def _load_projects_from_db(self) -> None:
        """启动时从全局注册表恢复项目列表（仅恢复元数据，不恢复运行时）。"""
        try:
            with sqlite3.connect(str(self._global_db_path)) as conn:
                cur = conn.execute("SELECT * FROM projects")
                for row in cur.fetchall():
                    logger.info("从注册表恢复项目: %s", row[0])
        except Exception:
            logger.exception("恢复项目列表失败")

    # ------------------------------------------------------------------
    # 项目注册 / 注销
    # ------------------------------------------------------------------
    def register_project(self, project_id: str, book_config: BookConfig) -> None:
        """注册新项目并初始化状态库与 BatchWriter。"""
        with self._lock:
            db_path = book_config.base_path / "world_state.db"
            state = StateManager(db_path, project_id)
            state.init_project(
                project_id=project_id,
                name=book_config.project,
                genre=book_config.genre,
                platform=book_config.platform,
                base_path=str(book_config.base_path),
                total_chapters=book_config.chapters_target,
            )
            writer = BatchWriter(book_config, state_manager=state, event_bus=self._event_bus)
            runtime = ProjectRuntime(
                project_id=project_id,
                book_config=book_config,
                state_manager=state,
                batch_writer=writer,
                status="pending",
            )
            self._projects[project_id] = runtime
            self._persist_project(project_id, runtime)
            logger.info("项目 %s 已注册", project_id)

    def unregister_project(self, project_id: str) -> None:
        """从调度器中注销项目（不删除文件）。"""
        with self._lock:
            info = self._projects.pop(project_id, None)
            if info and info.future and not info.future.done():
                info.future.cancel()
            logger.info("项目 %s 已注销", project_id)

    # ------------------------------------------------------------------
    # 流水线控制
    # ------------------------------------------------------------------
    def start_pipeline(
        self, project_id: str, chapter_range: tuple[int, int], resume: bool = False
    ) -> str:
        """启动项目流水线，提交到 Worker Pool。"""
        with self._lock:
            if project_id not in self._projects:
                raise ValueError(f"项目不存在: {project_id}")
            runtime = self._projects[project_id]
            if runtime.status in ("writing", "auditing"):
                raise ValueError("项目正在运行中，请先暂停或停止当前流水线")

            pipeline_id = f"pipe_{datetime.utcnow():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"
            runtime.pipeline_id = pipeline_id
            runtime.status = "writing"
            runtime.current_chapter = chapter_range[0]
            self._paused.discard(project_id)
            self._stopped.discard(project_id)

            future = self._executor.submit(
                self._run_pipeline, project_id, chapter_range, resume, pipeline_id
            )
            runtime.future = future
            self._persist_project(project_id, runtime)

            logger.info(
                "项目 %s 流水线 %s 启动，章节范围 %s",
                project_id,
                pipeline_id,
                chapter_range,
            )
            return pipeline_id

    def pause_pipeline(self, project_id: str) -> None:
        """暂停流水线（当前章节完成后停止）。"""
        with self._lock:
            runtime = self._projects.get(project_id)
            if not runtime:
                raise ValueError(f"项目不存在: {project_id}")
            if runtime.status in ("writing", "auditing"):
                self._paused.add(project_id)
                runtime.status = "paused"
                self._persist_project(project_id, runtime)
                logger.info("项目 %s 流水线暂停", project_id)

    def stop_pipeline(self, project_id: str) -> None:
        """停止流水线（立即取消）。"""
        with self._lock:
            runtime = self._projects.get(project_id)
            if not runtime:
                raise ValueError(f"项目不存在: {project_id}")
            self._stopped.add(project_id)
            if runtime.future and not runtime.future.done():
                runtime.future.cancel()
            runtime.status = "pending"
            runtime.pipeline_id = None
            self._persist_project(project_id, runtime)
            logger.info("项目 %s 流水线停止", project_id)

    # ------------------------------------------------------------------
    # Worker 线程中的实际执行逻辑
    # ------------------------------------------------------------------
    def _run_pipeline(
        self,
        project_id: str,
        chapter_range: tuple[int, int],
        resume: bool,
        pipeline_id: str,
    ) -> None:
        """在 Worker 线程中执行的实际流水线。"""
        try:
            self._event_bus.emit(
                PIPELINE_START,
                {
                    "project_id": project_id,
                    "pipeline_id": pipeline_id,
                    "chapter_range": chapter_range,
                },
            )

            with self._lock:
                runtime = self._projects.get(project_id)
                if not runtime:
                    return
                writer = runtime.batch_writer

            start, end = chapter_range
            for num in range(start, end + 1):
                # 检查暂停/停止
                if project_id in self._stopped:
                    logger.info("项目 %s 被停止", project_id)
                    break
                if project_id in self._paused:
                    logger.info("项目 %s 被暂停", project_id)
                    self._event_bus.emit(
                        PIPELINE_PAUSE,
                        {"project_id": project_id, "pipeline_id": pipeline_id, "paused_at": num},
                    )
                    break

                self._event_bus.emit(
                    CHAPTER_START,
                    {
                        "project_id": project_id,
                        "pipeline_id": pipeline_id,
                        "chapter_num": num,
                    },
                )

                try:
                    result = writer.write_chapter(num)
                    with self._lock:
                        runtime.current_chapter = num
                        if result.success:
                            runtime.status = "writing"
                        else:
                            runtime.status = "error"
                        self._persist_project(project_id, runtime)

                    self._event_bus.emit(
                        CHAPTER_COMPLETE,
                        {
                            "project_id": project_id,
                            "pipeline_id": pipeline_id,
                            "chapter_num": num,
                            "word_count": result.word_count,
                            "gate_level": result.gate_level,
                            "success": result.success,
                        },
                    )
                except Exception as exc:
                    logger.exception("项目 %s 第 %d 章写作失败", project_id, num)
                    self._event_bus.emit(
                        CHAPTER_ERROR,
                        {
                            "project_id": project_id,
                            "pipeline_id": pipeline_id,
                            "chapter_num": num,
                            "error": str(exc),
                        },
                    )
                    with self._lock:
                        runtime.status = "error"
                        self._persist_project(project_id, runtime)
                    break

            # 全部完成
            with self._lock:
                if runtime.status not in ("paused", "error"):
                    runtime.status = "completed"
                runtime.pipeline_id = None
                runtime.future = None
                self._persist_project(project_id, runtime)

            self._event_bus.emit(
                PIPELINE_COMPLETE,
                {
                    "project_id": project_id,
                    "pipeline_id": pipeline_id,
                    "final_status": runtime.status,
                    "last_chapter": runtime.current_chapter,
                },
            )

        except Exception:
            logger.exception("项目 %s 流水线异常终止", project_id)
            with self._lock:
                runtime = self._projects.get(project_id)
                if runtime:
                    # 保护已完成的流水线不被 event handler 或 persist 异常覆盖
                    if runtime.status not in ("completed", "paused"):
                        runtime.status = "error"
                    runtime.pipeline_id = None
                    runtime.future = None
                    self._persist_project(project_id, runtime)

    # ------------------------------------------------------------------
    # 状态查询
    # ------------------------------------------------------------------
    def get_project_status(self, project_id: str) -> dict[str, Any] | None:
        """获取单个项目状态。"""
        with self._lock:
            runtime = self._projects.get(project_id)
            if not runtime:
                return None
            return {
                "project_id": runtime.project_id,
                "name": runtime.book_config.project,
                "genre": runtime.book_config.genre,
                "platform": runtime.book_config.platform,
                "status": runtime.status,
                "current_chapter": runtime.current_chapter,
                "total_chapters": runtime.book_config.chapters_target,
                "pipeline_id": runtime.pipeline_id,
                "base_path": str(runtime.book_config.base_path),
                "llm": runtime.book_config.llm,
            }

    def get_all_projects(self) -> list[dict[str, Any]]:
        """获取所有项目列表。"""
        with self._lock:
            return [
                {
                    "project_id": p.project_id,
                    "name": p.book_config.project,
                    "genre": p.book_config.genre,
                    "platform": p.book_config.platform,
                    "status": p.status,
                    "current_chapter": p.current_chapter,
                    "total_chapters": p.book_config.chapters_target,
                }
                for p in self._projects.values()
            ]

    def get_global_stats(self) -> dict[str, Any]:
        """获取全局统计。"""
        with self._lock:
            active = sum(
                1 for p in self._projects.values() if p.status in ("writing", "auditing")
            )
            return {
                "total_projects": len(self._projects),
                "active_projects": active,
                "max_workers": self.max_workers,
                "pending_projects": sum(
                    1 for p in self._projects.values() if p.status == "pending"
                ),
                "completed_projects": sum(
                    1 for p in self._projects.values() if p.status == "completed"
                ),
            }

    def get_state_manager(self, project_id: str) -> StateManager | None:
        """获取项目的 StateManager 实例。"""
        with self._lock:
            runtime = self._projects.get(project_id)
            return runtime.state_manager if runtime else None

    # ------------------------------------------------------------------
    # 事件总线封装
    # ------------------------------------------------------------------
    def on_event(self, handler: Callable[[str, dict[str, Any]], None]) -> None:
        """注册全局事件处理器（供 WebSocket 等使用）。"""
        for event_type in EVENT_TYPES:
            self._event_bus.on(event_type, handler)
        self._event_handlers.append(handler)

    def remove_event_handler(self, handler: Callable[[str, dict[str, Any]], None]) -> None:
        """注销全局事件处理器。"""
        for event_type in EVENT_TYPES:
            self._event_bus.off(event_type, handler)
        if handler in self._event_handlers:
            self._event_handlers.remove(handler)

    def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        """直接发布事件（供外部模块使用）。"""
        self._event_bus.emit(event_type, payload)
