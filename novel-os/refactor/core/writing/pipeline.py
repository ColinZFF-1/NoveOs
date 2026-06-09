"""写作流水线编排 —— 替代 batch_writer.py 的核心逻辑。"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.content.metrics import count_chinese_chars
from core.validation.models import ValidationContext, ValidationResult
from core.validation.chain import ValidationChain
from core.writing.context import ChapterContext
from core.writing.output import WriteResult
from core.writing.steps.base import PipelineStep, StepFailure, StepResult
from core.writing.steps.auditor import AuditorStep
from core.writing.steps.beat_planner import BeatPlannerStep
from core.writing.steps.dialogue_tuner import DialogueTunerStep
from core.writing.steps.director import DirectorStep
from core.writing.steps.hook_engineer import HookEngineerStep
from core.writing.steps.polish import PolishStep
from core.writing.steps.scene_writer import SceneWriterStep

logger = logging.getLogger("novel-os.pipeline")


@dataclass
class PipelineConfig:
    """流水线行为配置。"""

    max_retries: int = 3
    enable_polish: bool = False  # Kimi-K2.5 对 Polish 不稳定，默认关闭
    polish_interval: int = 3  # 每 N 章润色一次
    skip_hook_if_in_range: bool = True  # SceneWriter 字数达标时跳过 HookEngineer
    skip_dialogue_if_in_range: bool = True  # HookEngineer 后字数达标时跳过 DialogueTuner


class WritingPipeline:
    """10 阶写作流水线编排器。

    职责：
    1. 按顺序执行 Steps
    2. 管理重试逻辑（字数不足 → Expander，结构问题 → 修正回退）
    3. 协调条件跳过（字数达标时跳过 Hook/Dialogue）
    4. 触发校验链和反检测改写
    5. 产出最终的 WriteResult

    不直接操作：
    - 文件保存（委托 ContentService）
    - 数据库更新（委托 StateService）
    - LLM 调用细节（委托各 Step）
    """

    def __init__(
        self,
        steps: list[PipelineStep] | None = None,
        validator: ValidationChain | None = None,
        config: PipelineConfig | None = None,
    ) -> None:
        self._steps = steps or self._default_steps()
        self._validator = validator
        self._cfg = config or PipelineConfig()
        self._step_map: dict[str, PipelineStep] = {s.name: s for s in self._steps}

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def execute(self, ctx: ChapterContext) -> WriteResult:
        """执行完整流水线，返回 WriteResult。"""
        logger.info("=" * 60)
        logger.info("[Pipeline] 开始写作 第 %d 章", ctx.chapter_num)

        attempt = 0
        content = ""
        validation = ValidationResult(verdict="BLOCK", issues=[])
        audit_report: dict[str, Any] = {}

        while attempt < self._cfg.max_retries:
            attempt += 1
            logger.info("[Pipeline] 第 %d 章 第 %d 次尝试", ctx.chapter_num, attempt)

            try:
                content = self._run_steps(ctx)
            except StepFailure as exc:
                logger.warning("[Pipeline] StepFailure: %s - %s", exc.step_name, exc.reason)
                hint = self._step_map.get(exc.step_name, exc).fallback(ctx, exc)
                if hint:
                    ctx.corrections[exc.step_name] = hint
                    continue
                # 不可恢复，直接失败
                break
            except Exception as exc:
                logger.exception("[Pipeline] 未处理异常: %s", exc)
                break

            # 校验
            if self._validator:
                validation = self._validator.validate(
                    content,
                    ValidationContext(
                        chapter_num=ctx.chapter_num,
                        word_count=count_chinese_chars(content),
                        outline=ctx.outline,
                    ),
                )
                audit_report = {"validation": validation.to_dict()}

            if validation.verdict != "BLOCK":
                break

            # BLOCK → 生成修正指令继续重试
            ctx.corrections = self._build_corrections(validation)
            logger.info("[Pipeline] 校验 BLOCK，生成修正指令继续重试")

        # 最终判定
        final_wc = count_chinese_chars(content)
        if validation.verdict == "BLOCK":
            logger.error("[Pipeline] 第 %d 章 最终失败，已用尽 %d 次重试", ctx.chapter_num, attempt)
            return WriteResult(
                chapter_num=ctx.chapter_num,
                success=False,
                final_content=content,
                word_count=final_wc,
                gate_level="BLOCKING",
                attempts=attempt,
                audit_report=audit_report,
            )

        logger.info("[Pipeline] 第 %d 章 完成，字数=%d", ctx.chapter_num, final_wc)
        return WriteResult(
            chapter_num=ctx.chapter_num,
            success=True,
            final_content=content,
            word_count=final_wc,
            gate_level=validation.verdict,
            attempts=attempt,
            audit_report=audit_report,
        )

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    def _run_steps(self, ctx: ChapterContext) -> str:
        """按顺序执行 Steps，返回最终正文。"""
        content = ""
        skip_remaining = False

        for step in self._steps:
            if skip_remaining:
                logger.info("[Pipeline] 跳过 %s（前置步骤要求跳过后续）", step.name)
                continue

            logger.info("[Pipeline] 执行 %s", step.name)
            result: StepResult = step.execute(ctx)
            content = result.content
            skip_remaining = result.skip_subsequent

            # 字数保护：SceneWriter 后达标 → 跳过 Hook
            if step.name == "SceneWriter" and self._cfg.skip_hook_if_in_range:
                wc = count_chinese_chars(content)
                if ctx.word_min <= wc <= ctx.word_max:
                    logger.info("[Pipeline] SceneWriter 字数达标(%d)，跳过 HookEngineer", wc)
                    # 找到 HookEngineer 并标记跳过（通过修正逻辑）
                    # 更简洁的做法：在 _default_steps 中 HookEngineer 自己检查

        return content

    def _build_corrections(self, validation: ValidationResult) -> dict[str, str]:
        """根据校验结果生成各 Step 的修正指令。"""
        corrections: dict[str, str] = {}
        for issue in validation.issues:
            if "钩子" in issue.message or "IWR" in issue.message:
                corrections["HookEngineer"] = issue.message
            elif "对话" in issue.message or "道说" in issue.message:
                corrections["DialogueTuner"] = issue.message
            elif "句长" in issue.message or "他密度" in issue.message:
                corrections["SceneWriter"] = issue.message
            else:
                corrections["global"] = issue.message
        return corrections

    @classmethod
    def _default_steps(cls) -> list[PipelineStep]:
        """默认 10 阶 Steps。"""
        return [
            DirectorStep(),
            BeatPlannerStep(),
            SceneWriterStep(),
            HookEngineerStep(),
            DialogueTunerStep(),
            PolishStep(),
            AuditorStep(),
        ]
