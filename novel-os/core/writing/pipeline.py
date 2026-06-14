"""写作流水线编排 —— 替代 batch_writer.py 的核心逻辑。"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from core.chapter_validator import ChapterValidator, ValidationIssue, ValidationResult
from core.content.metrics import count_chinese_chars
from core.post_write_validator import PostWriteValidator
from core.writing.context import ChapterContext
from core.writing.output import WriteResult
from core.writing.steps.base import PipelineStep, StepFailure, StepResult
from core.writing.steps.auditor import AuditorStep
from core.writing.steps.beat_planner import BeatPlannerStep
from core.writing.steps.dialogue_tuner import DialogueTunerStep
from core.writing.steps.director import DirectorStep
from core.writing.steps.expander import ExpanderStep
from core.writing.steps.hook_engineer import HookEngineerStep
from core.writing.steps.polish import PolishStep
from core.writing.steps.scene_writer import SceneWriterStep
from core.writing.steps.spot_fix import SpotFixStep

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
    4. 触发校验和反检测改写
    5. 产出最终的 WriteResult

    不直接操作：
    - 文件保存（委托 BatchWriter）
    - 数据库更新（委托 BatchWriter）
    - LLM 调用细节（委托各 Step）
    """

    def __init__(
        self,
        steps: list[PipelineStep] | None = None,
        validator: ChapterValidator | None = None,
        config: PipelineConfig | None = None,
    ) -> None:
        self._steps = steps or self._default_steps()
        self._validator = validator
        self._cfg = config or PipelineConfig()
        self._step_map: dict[str, PipelineStep] = {s.name: s for s in self._steps}
        self._post_validator = PostWriteValidator()
        self._expander = ExpanderStep()
        self._spot_fix = SpotFixStep()

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
        chapter_title = ""

        corrections: dict[str, str] = {
            "scene_writer": "",
            "hook_engineer": "",
            "dialogue_tuner": "",
            "global": "",
        }

        while self._should_retry(validation, attempt):
            attempt += 1
            logger.info("[Pipeline] 第 %d 章 第 %d 次尝试", ctx.chapter_num, attempt)

            try:
                content = self._run_steps(ctx, corrections)
            except StepFailure as exc:
                logger.warning("[Pipeline] StepFailure: %s - %s", exc.step_name, exc.reason)
                hint = self._step_map.get(exc.step_name, exc).fallback(ctx, exc)
                if hint:
                    corrections[exc.step_name] = hint
                    continue
                break
            except Exception as exc:
                logger.exception("[Pipeline] 未处理异常: %s", exc)
                validation = ValidationResult(
                    verdict="BLOCK",
                    issues=[ValidationIssue("BLOCK", "异常", str(exc))],
                )
                break

            # PostWriteValidator 零成本预检
            post_result = self._post_validator.validate(content)
            if post_result.verdict == "SPOT_FIX":
                logger.info("[Pipeline] 第 %d 章 PostWriteValidator 命中 %d 处", ctx.chapter_num, len(post_result.issues))
                logger.info("[Pipeline] 第 %d 章 跳过 SpotFix，保留原始内容", ctx.chapter_num)

            # ChapterValidator 快速扫描
            quick_check = self._validator.validate(content, {"chapter_num": ctx.chapter_num}) if self._validator else ValidationResult(verdict="PASS", issues=[])
            polish_extra = self._validator.build_retry_feedback(quick_check) if (self._validator and quick_check.issues) else ""
            if quick_check.issues:
                content = quick_check.auto_fix_text or content
                logger.info("[Pipeline] 第 %d 章 Validator 标红 %d 处", ctx.chapter_num, len(quick_check.issues))

            # Polish（当前默认禁用）
            should_polish = self._cfg.enable_polish and ((ctx.chapter_num - 1) % self._cfg.polish_interval == 0 or bool(quick_check.issues))
            if should_polish:
                polish_step = self._step_map.get("Polish")
                if polish_step:
                    logger.info("[Pipeline] 第 %d 章 调用 Polish", ctx.chapter_num)
                    try:
                        ctx.corrections["__previous_content__"] = content
                        ctx.corrections["polish"] = polish_extra
                        result = polish_step.execute(ctx)
                        content = result.content
                    except StepFailure as exc:
                        logger.warning("Polish 失败: %s", exc.reason)

            # Auditor + ChapterValidator
            auditor_step = self._step_map.get("Auditor")
            if auditor_step:
                try:
                    ctx.corrections["__previous_content__"] = content
                    audit_result = auditor_step.execute(ctx)
                    audit_report = audit_result.metadata.get("audit_report", {})
                except Exception as exc:
                    logger.warning("Auditor 失败: %s", exc)

            if self._validator:
                validation = self._validator.validate(content, {
                    "chapter_num": ctx.chapter_num,
                    "state_manager": ctx.state,
                    "core_event": ctx.outline.get("core_event", ""),
                })
            else:
                validation = ValidationResult(verdict="PASS", issues=[])

            # 反检测改写
            if validation.verdict != "BLOCK":
                from core.anti_detect_reviser import AntiDetectReviser
                ai_markers = AntiDetectReviser.compute_ai_marker_score(content)
                audit_report["ai_markers"] = ai_markers
                if ai_markers.get("total", 0) > 0.6:
                    logger.warning("第 %d 章 AI 痕迹分数 %.2f，触发反检测改写", ctx.chapter_num, ai_markers["total"])
                    anti_detect = AntiDetectReviser()
                    content = anti_detect.revise(content, aggressiveness=0.7)
                    if self._validator:
                        validation = self._validator.validate(content, {
                            "chapter_num": ctx.chapter_num,
                            "state_manager": ctx.state,
                            "core_event": ctx.outline.get("core_event", ""),
                        })
                    audit_report["anti_detect_applied"] = True
                    logger.info("第 %d 章 反检测改写后验证: %s", ctx.chapter_num, validation.verdict)
                else:
                    logger.info("第 %d 章 AI 痕迹分数 %.2f，无需改写", ctx.chapter_num, ai_markers["total"])

            if validation.verdict == "BLOCK":
                block_issues = [i for i in validation.issues if i.level == "BLOCK"]
                logger.warning("ChapterValidator BLOCK: %s",
                               [i.message for i in block_issues])

                has_overlength = any("字数超标" in i.message for i in block_issues)
                has_shortage = any("字数不足" in i.message for i in block_issues)

                # 字数超标 → 截断
                if has_overlength:
                    content = self._truncate_if_overlength(ctx, content)
                    if self._validator:
                        validation = self._validator.validate(content, {"chapter_num": ctx.chapter_num})
                    if validation.verdict != "BLOCK":
                        break
                    # 截断后仍有其他阻塞问题，合并修正指令继续重试
                    corrections = self._merge_corrections(
                        corrections, self._generate_corrections(validation, audit_report)
                    )
                    logger.info(
                        "[Pipeline] 第 %d 章 截断后仍有 %d 处阻塞问题，继续重试",
                        ctx.chapter_num,
                        len([i for i in validation.issues if i.level == "BLOCK"]),
                    )
                    continue

                # 字数不足 → Expander
                if has_shortage:
                    content = self._try_expand(ctx, content, validation)
                    if self._validator:
                        validation = self._validator.validate(content, {"chapter_num": ctx.chapter_num})
                    if validation.verdict != "BLOCK":
                        break
                    # 第二次
                    short_by2 = ctx.word_min - count_chinese_chars(content)
                    if short_by2 > 0:
                        content = self._try_expand(ctx, content, None, short_by2)
                        if self._validator:
                            validation = self._validator.validate(content, {"chapter_num": ctx.chapter_num})
                        if validation.verdict != "BLOCK":
                            break
                        # 若二次扩写后字数达标但仍有其他阻塞问题，合并修正指令
                        if not any("字数不足" in i.message for i in validation.issues if i.level == "BLOCK"):
                            corrections = self._merge_corrections(
                                corrections, self._generate_corrections(validation, audit_report)
                            )
                            logger.info(
                                "[Pipeline] 第 %d 章 扩写后字数达标但仍有 %d 处阻塞问题，继续重试",
                                ctx.chapter_num,
                                len([i for i in validation.issues if i.level == "BLOCK"]),
                            )
                            continue
                        short_by3 = ctx.word_min - count_chinese_chars(content)
                        corrections = self._merge_corrections(corrections, {
                            "scene_writer": (
                                f"\n字数仍不足，当前{count_chinese_chars(content)}字，"
                                f"需再扩写{max(short_by3, 200)}字。"
                            ),
                            "hook_engineer": "",
                            "dialogue_tuner": "",
                            "global": "",
                        })
                        logger.info("[Pipeline] 第 %d 章 第二次Expander后仍不足，回退 SceneWriter", ctx.chapter_num)
                    else:
                        # 扩写后字数达标但仍有其他阻塞问题，合并修正指令继续重试
                        corrections = self._merge_corrections(
                            corrections, self._generate_corrections(validation, audit_report)
                        )
                        logger.info(
                            "[Pipeline] 第 %d 章 扩写后字数达标但仍有 %d 处阻塞问题，继续重试",
                            ctx.chapter_num,
                            len([i for i in validation.issues if i.level == "BLOCK"]),
                        )
                        continue
                else:
                    corrections = self._merge_corrections(
                        corrections, self._generate_corrections(validation, audit_report)
                    )
                    logger.info("[Pipeline] 第 %d 章 结构问题，回退修正", ctx.chapter_num)
            else:
                break

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

        if validation.verdict == "WARN":
            logger.warning("[Pipeline] 第 %d 章 WARN: %s", ctx.chapter_num,
                           [i.message for i in validation.issues])

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
    def _should_retry(self, validation: ValidationResult, attempt: int) -> bool:
        return validation.verdict == "BLOCK" and attempt < self._cfg.max_retries

    @staticmethod
    def _merge_corrections(
        old: dict[str, str], new: dict[str, str]
    ) -> dict[str, str]:
        """合并修正指令，避免覆盖已累积的反馈。"""
        merged = dict(old)
        for key, value in new.items():
            if value:
                merged[key] = (merged.get(key, "") + "\n" + value).strip()
        return merged

    def _run_steps(self, ctx: ChapterContext, corrections: dict[str, str]) -> str:
        """按顺序执行 Steps，返回最终正文。"""
        content = ""
        ctx.corrections = corrections.copy()

        for step in self._steps:
            logger.info("[Pipeline] 执行 %s", step.name)

            # 字数保护：SceneWriter 后达标 → 跳过 HookEngineer
            if step.name == "HookEngineer" and self._cfg.skip_hook_if_in_range:
                wc = count_chinese_chars(content)
                if ctx.word_min <= wc <= ctx.word_max:
                    logger.info("[Pipeline] SceneWriter 字数达标(%d)，跳过 HookEngineer", wc)
                    continue

            # 字数保护：HookEngineer 后达标 → 跳过 DialogueTuner
            if step.name == "DialogueTuner" and self._cfg.skip_dialogue_if_in_range:
                wc = count_chinese_chars(content)
                if ctx.word_min <= wc <= ctx.word_max:
                    logger.info("[Pipeline] HookEngineer 后字数达标(%d)，跳过 DialogueTuner", wc)
                    continue

            # 时间保护：跳过 Polish 和 Auditor，直接保存 SceneWriter 原始输出
            if step.name in ("Polish", "Auditor"):
                logger.info("[Pipeline] 跳过 %s，直接保存 SceneWriter 输出", step.name)
                continue

            # 传递当前内容给需要前置内容的 Steps
            if step.name in ("HookEngineer", "DialogueTuner", "Polish", "Auditor"):
                ctx.corrections["__previous_content__"] = content

            result: StepResult = step.execute(ctx)
            content = result.content

        return content

    def _truncate_if_overlength(self, ctx: ChapterContext, content: str) -> str:
        """字数超标时截断到中文字数上限。"""
        max_cn = ctx.word_max
        cn_chars = re.findall(r'[\u4e00-\u9fff]', content)
        if len(cn_chars) > max_cn:
            pos = 0
            count = 0
            for m in re.finditer(r'[\u4e00-\u9fff]', content):
                count += 1
                if count == max_cn:
                    pos = m.end()
                    break
            content = content[:pos] + "\n\n[本章因超字数截断]"
            logger.info("[Pipeline] 第 %d 章 截断到 %d 中文字符", ctx.chapter_num, max_cn)
        return content

    def _try_expand(self, ctx: ChapterContext, content: str, validation: ValidationResult | None = None, short_by: int | None = None) -> str:
        """调用 Expander 补充字数。"""
        if short_by is None:
            short_by = ctx.word_min - (validation.metrics.get("word_count", 0) if validation else count_chinese_chars(content))
        short_by = max(short_by, 200)
        logger.info("[Pipeline] 第 %d 章 调用 Expander，缺口 %d 字", ctx.chapter_num, short_by)
        try:
            expanded = self._expander.expand(ctx, content, short_by)
            return content + "\n\n" + expanded
        except StepFailure:
            return content

    def _generate_corrections(self, validation: ValidationResult, audit_report: dict[str, Any]) -> dict[str, str]:
        """根据 ChapterValidator 结果生成各 Agent 的修正指令。"""
        corrections: dict[str, str] = {
            "scene_writer": "",
            "hook_engineer": "",
            "dialogue_tuner": "",
            "global": "",
        }
        extra = audit_report.get("extra", {})

        reasons = [i.message for i in validation.issues] if hasattr(validation, 'issues') else []
        for reason in reasons:
            if any(k in reason for k in ["IWR", "钩子", "悬念", "结尾", "开头"]):
                iwr = extra.get("iwr_score", 0)
                q_count = extra.get("questions_count", 0)
                corrections["hook_engineer"] += (
                    f"\n【钩子修正】当前IWR={iwr}（要求≥2.0），问题数={q_count}（要求≥3）。"
                    f"请在开头增加1个情境悬念，在结尾增加1-2个未解之谜。"
                )
            if any(k in reason for k in ["对话", "道说比", "对白"]):
                dial = extra.get("dialogue_ratio", 0)
                corrections["dialogue_tuner"] += (
                    f"\n【对话修正】当前对话占比={dial:.0%}。请调整对话密度和'道/说'比率。"
                )
            if any(k in reason for k in ["句长", "句子", "过长"]):
                sent = extra.get("sentence_length", 0)
                corrections["scene_writer"] += (
                    f"\n【句长修正】当前平均句长={sent}字。请将过长句子拆分为短句。"
                )
            if any(k in reason for k in ["他密度", "人称", "他字"]):
                ta = extra.get("ta_density", 0)
                corrections["scene_writer"] += (
                    f"\n【人称修正】当前他密度={ta:.2%}。请减少'他/她/它'的使用。"
                )
            if any(k in reason for k in ["平台", "适配", "DNA"]):
                grade = extra.get("platform_grade", "C")
                corrections["global"] += (
                    f"\n【平台适配修正】当前等级{grade}。请整体调整结构。"
                )

        # 强制术语缺失 → 注入补全指令
        missing_terms = []
        for issue in validation.issues:
            if issue.category == "术语" and issue.level in ("BLOCK", "WARN"):
                m = re.search(r"'(.+?)'", issue.message)
                if m:
                    missing_terms.append(m.group(1))
        if missing_terms:
            corrections["scene_writer"] += (
                f"\n【术语补全——绝对优先】当前正文缺失以下世界观核心术语，"
                f"必须在正文中准确出现（禁止意译或替换）：{', '.join(missing_terms)}。"
                f"请在合适场景自然嵌入这些术语，确保读者能看到准确的专有名词。"
            )
            corrections["global"] += (
                f"\n【术语铁律】本章必须包含：{', '.join(missing_terms)}。"
            )

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
