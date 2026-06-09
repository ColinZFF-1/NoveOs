"""章节上下文 —— 写作流水线的数据载体。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from core.state.models import (
    ChapterOutline,
    CharacterState,
    Debt,
    Foreshadowing,
)
from infrastructure.config import BookConfig

if TYPE_CHECKING:
    from infrastructure.llm import LLMService
    from core.state.unit_of_work import UnitOfWork


@dataclass
class ChapterContext:
    """单章写作所需的全部上下文数据。

    由 ChapterContextBuilder 在流水线启动前组装，
    Step 只读不写，保证数据流单向透明。
    """

    # --- 标识 ---
    chapter_num: int
    project_id: str
    book_config: BookConfig

    # --- 来自状态库的查询结果（ContextBuilder 填充） ---
    outline: ChapterOutline
    """本章大纲：核心事件、打脸方式、护妻时刻、章末钩子。"""

    prev_summary: str = ""
    """前 3 章摘要，用于 continuity。"""

    character_states: list[CharacterState] = field(default_factory=list)
    """本章涉及的人物状态。"""

    consistency_rules: list[str] = field(default_factory=list)
    """跨章一致性约束。"""

    debts: list[Debt] = field(default_factory=list)
    """本章需要埋/收的债务。"""

    foreshadowing: list[Foreshadowing] = field(default_factory=list)
    """本章需要埋/收的伏笔。"""

    # --- 流水线中间状态（Steps 填充，后续 Steps 读取） ---
    director_prompt: str = ""
    """Director 生成的任务卡。重试时复用。"""

    beat_plan: str = ""
    """BeatPlanner 生成的六段式节拍。重试时复用。"""

    corrections: dict[str, str] = field(default_factory=dict)
    """各 Agent 的修正指令，key 为 step_name。"""

    # --- 运行时依赖（依赖注入，不直接实例化） ---
    llm: LLMService = field(repr=False)
    """LLM 调用服务。"""

    uow: UnitOfWork = field(repr=False)
    """数据库工作单元。"""

    @property
    def word_target(self) -> int:
        """本章目标字数。"""
        return self.book_config.words_per_chapter

    @property
    def word_tolerance(self) -> int:
        """本章字数容差。"""
        return getattr(self.book_config, "words_tolerance", 450)

    @property
    def word_min(self) -> int:
        return self.word_target - self.word_tolerance

    @property
    def word_max(self) -> int:
        return self.word_target + self.word_tolerance

    def get_correction(self, step_name: str) -> str:
        """获取指定 Step 的修正指令。"""
        return self.corrections.get(step_name, "")
