"""Director Step —— 生成本章任务卡。"""
from __future__ import annotations

import logging

from core.writing.context import ChapterContext
from core.writing.steps.base import PipelineStep, StepFailure, StepResult

logger = logging.getLogger("novel-os.steps.director")


class DirectorStep(PipelineStep):
    """小说导演：读取大纲和状态库，生成本章任务卡（含标题）。

    原 batch_writer._call_director 的迁移版本。
    """

    name = "Director"

    def execute(self, ctx: ChapterContext) -> StepResult:
        system = self._build_system_prompt(ctx)
        user = self._build_user_prompt(ctx)

        try:
            result = ctx.llm.complete(system, user)
        except Exception as exc:
            raise StepFailure(
                step_name=self.name,
                reason=f"LLM 调用失败: {exc}",
                retryable=True,
            )

        if not result or len(result) < 50:
            raise StepFailure(
                step_name=self.name,
                reason="Director 返回内容过短，疑似无效",
                retryable=True,
            )

        # 保存到上下文，后续 Steps 和重试时复用
        ctx.director_prompt = result
        logger.info("[Director] 第 %d 章 任务卡已生成 (%d 字)", ctx.chapter_num, len(result))

        return StepResult(content=result, metadata={"agent": "Director"})

    def _build_system_prompt(self, ctx: ChapterContext) -> str:
        return (
            "你是小说导演。根据大纲和人物状态，生成本章的详细任务卡。\n"
            "任务卡必须包含：\n"
            "1. 【标题】第X章：标题名\n"
            "2. 【核心事件】本章必须完成的主线事件\n"
            "3. 【节拍分配】六段式：起→承→转→转→合→钩子\n"
            "4. 【人物调度】谁出场、情绪变化、对话指纹\n"
            "5. 【必须术语】世界观核心术语（禁止意译）\n"
            "6. 【字数目标】严格控制在目标范围内"
        )

    def _build_user_prompt(self, ctx: ChapterContext) -> str:
        lines = [
            f"# 第 {ctx.chapter_num} 章 任务卡请求",
            "",
            "## 大纲",
            f"核心事件：{ctx.outline.core_event}",
            f"打脸方式：{ctx.outline.face_slap}",
            f"护妻时刻：{ctx.outline.protect_wife}",
            f"章末钩子：{ctx.outline.hook}",
            "",
            "## 前情摘要",
            ctx.prev_summary[:500],
            "",
            "## 人物状态",
        ]
        for ch in ctx.character_states[:5]:
            lines.append(f"- {ch.name}：{ch.location}，{ch.emotional_state}")
        lines.extend([
            "",
            "## 债务与伏笔",
            f"待埋债务：{len([d for d in ctx.debts if d.bury_chapter == ctx.chapter_num])}",
            f"待收伏笔：{len([f for f in ctx.foreshadowing if f.collect_chapter == ctx.chapter_num])}",
            "",
            f"## 字数目标：{ctx.word_target} ± {ctx.word_tolerance} 中文字",
        ])
        return "\n".join(lines)
