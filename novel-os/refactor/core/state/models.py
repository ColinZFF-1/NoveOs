"""状态域领域模型 —— 纯数据结构，无业务逻辑。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ProjectInfo:
    project_id: str
    name: str
    genre: str
    platform: str
    base_path: str
    total_chapters: int
    status: str = "pending"
    current_chapter: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ChapterOutline:
    """单章大纲。"""

    chapter: int
    core_event: str = ""
    face_slap: str = ""  # 打脸方式
    protect_wife: str = ""  # 护妻时刻
    hook: str = ""  # 章末钩子
    emotion_target: str = ""  # 情绪目标
    must_terms: list[str] = field(default_factory=list)  # 必须出现的世界观术语


@dataclass
class CharacterState:
    """人物状态。"""

    name: str
    chapter: int
    location: str = ""
    emotional_state: str = ""
    known_secrets: str = ""
    unknown_secrets: str = ""
    abilities_active: str = ""
    abilities_locked: str = ""
    dialog_fingerprint: str = ""
    body_language: str = ""
    physical_description: str = ""


@dataclass
class Debt:
    """悬念债务。"""

    debt_id: str
    type: str
    content: str
    bury_chapter: int
    collect_chapter: int | None = None
    status: str = "active"  # active / collected / abandoned


@dataclass
class Foreshadowing:
    """伏笔。"""

    fs_id: str
    content: str
    bury_chapter: int
    collect_chapter: int | None = None
    type: str = ""
    status: str = "active"


@dataclass
class ChapterHistory:
    """已写章节记录。"""

    chapter: int
    title: str = ""
    summary: str = ""
    word_count: int = 0
    agent_version: str = ""
    status: str = "draft"  # draft / published / rollback


@dataclass
class ItemState:
    """道具/关键物品状态。"""

    item_name: str
    chapter: int
    location: str = ""
    state: str = ""
    rule: str = ""


@dataclass
class CastSchedule:
    """配角出场调度。"""

    character_name: str
    chapter: int
    must_appear: bool = False
    scene_purpose: str = ""
