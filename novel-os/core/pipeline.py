"""
Novel-OS Pipeline —— 双层 CrewAI 调度主循环。

外层（每 5-10 章）：4 个战略 Agent —— 架构巡检 / 一致性 / 节奏 / 回溯修正
内层（每章）：7 个战术 Agent —— 规划 → 写作 → 润色 → 审计
精度层（每章）：ChapterValidator + StateManager + Expander

替代旧版 orchestrator.py 中分散的写章逻辑。
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from core.batch_writer import BatchWriter
from core.chapter_validator import ChapterValidator, ValidationResult
from core.config_loader import BookConfig
from core.context_builder import ChapterContext
from core.expander import ChapterExpander
from core.state_manager import StateManager

logger = logging.getLogger("novel-os.pipeline")


class NovelPipeline:
    """双层调度流水线。"""

    def __init__(self, book_config: BookConfig):
        self.config = book_config
        self.book_dir = Path(book_config.base_path or ".")
        self.state = StateManager(self.book_dir / "world_state.db")
        self.validator = ChapterValidator()
        self.expander = ChapterExpander()

        # 内层写手
        self.inner_writer = BatchWriter(book_config, self.state)

    # ==================================================================
    # 公共接口
    # ==================================================================
    def write_chapters(
        self,
        start_chapter: int,
        count: int = 1,
        outer_check_interval: int = 5,
    ) -> dict[str, Any]:
        """写多章，自动触发外层巡检。

        Args:
            start_chapter: 起始章节号
            count: 写几章
            outer_check_interval: 外层巡检间隔（默认每 5 章）

        Returns:
            {chapter_num: result_dict, ...}
        """
        results = {}
        total = start_chapter + count

        for ch in range(start_chapter, total):
            print(f"\n{'='*60}")
            print(f"  [内层] 写第 {ch} 章...")
            print(f"{'='*60}")

            # ── 写一章 ──
            chapter_result = self._write_one_chapter(ch)

            # ── 精度校验 ──
            ctx = ChapterContext(str(self.book_dir), ch, self.state)
            context = ctx.build()
            context["chapter_num"] = ch
            context["state_manager"] = self.state
            context["core_event"] = context.get("core_event", "")

            validation = self.validator.validate(
                chapter_result.get("content", ""), context
            )

            # ── 字数不足 → 扩写 ──
            if validation.metrics.get("word_count", 0) < 4000:
                print(f"  [Expander] 字数不足，尝试扩写...")
                expanded = self.expander.expand(
                    chapter_result.get("content", ""), target_min=4000
                )
                if expanded.success:
                    chapter_result["content"] = expanded.text
                    validation = self.validator.validate(expanded.text, context)
                    print(f"  [Expander] 扩写完成: {expanded.words_before} → {expanded.words_after}")

            # ── 阻塞 → 重试 ──
            retry = 0
            while validation.verdict == "BLOCK" and retry < 3:
                retry += 1
                print(f"  [重试 {retry}/3] {len([i for i in validation.issues if i.level=='BLOCK'])} 个阻塞问题")
                feedback = self.validator.build_retry_feedback(validation)
                chapter_result = self._write_one_chapter(ch, feedback)
                validation = self.validator.validate(
                    chapter_result.get("content", ""), context
                )

            # ── 保存 ──
            self._save_chapter(ch, chapter_result, validation)

            # ── 更新状态 ──
            self._update_state(ch, chapter_result.get("content", ""))

            results[ch] = {
                "verdict": validation.verdict,
                "word_count": validation.metrics.get("word_count", 0),
                "issues": len(validation.issues),
            }
            print(f"  [完成] 第 {ch} 章: {validation.verdict} | {validation.metrics.get('word_count', 0)} 字 | {len(validation.issues)} 个问题")

            # ── 外层巡检（每 N 章）─
            if ch > 1 and ch % outer_check_interval == 0:
                print(f"\n{'='*60}")
                print(f"  [外层] 第 {ch-outer_check_interval+1}-{ch} 章巡检...")
                print(f"{'='*60}")
                outer_report = self._run_outer_check(ch)
                self._apply_outer_feedback(outer_report, ch)
                print(f"  [外层完成] 架构:{outer_report.get('architecture_health','?')} | 矛盾:{outer_report.get('critical_issues',0)}个")

        return results

    # ==================================================================
    # 内层
    # ==================================================================
    def _write_one_chapter(self, ch: int, feedback: str = "") -> dict:
        """写一章（委托给 BatchWriter）。"""
        try:
            return self.inner_writer.write_single_chapter(ch, feedback)
        except Exception as e:
            logger.error(f"第 {ch} 章写作失败: {e}")
            return {"content": f"[写作失败: {e}]", "audit_report": {}}

    # ==================================================================
    # 外层
    # ==================================================================
    def _run_outer_check(self, current_chapter: int) -> dict:
        """执行外层 4 Agent 巡检。

        注意：外层 Agent 不使用 CrewAI 框架（避免依赖），
        而是使用 LLMClient 进行结构化调用。
        将来可以替换为 CrewAI 原生调用。
        """
        ctx = ChapterContext(str(self.book_dir), current_chapter, self.state)
        minimal = ctx.build_minimal()
        report: dict[str, Any] = {
            "architecture_health": "?",
            "critical_issues": 0,
            "pacing_diagnosis": "?",
            "retcon_plan": None,
        }

        # Agent 1: 全书架构师
        arch_prompt = self._build_architect_prompt(minimal)
        # arch_result = self.llm.chat(arch_prompt)  # 需要 LLM 客户端
        report["architecture_health"] = "B+（占位，需接入 LLM）"

        # Agent 2: 一致性巡检
        report["critical_issues"] = 0  # ChapterValidator 已做基础检查

        # Agent 3: 节奏分析（每 10 章）
        if current_chapter % 10 == 0:
            report["pacing_diagnosis"] = "正常（占位，需接入 LLM）"

        # Agent 4: Retcon（发现致命矛盾时）
        # 由 Continuity Inspector 的输出触发

        return report

    def _build_architect_prompt(self, ctx: dict) -> str:
        """构建全书架构师 prompt。"""
        return f"""你是一位经验丰富的长篇小说架构师。请对照大纲和最近 5 章的产出，输出以下报告：

## 全书大纲
{ctx.get('outline_summary', '(无)')}

## 最近 5 章摘要
{ctx.get('chapter_history', '(无)')}

## 人物状态
{ctx.get('character_states', '(无)')}

## 未回收伏笔
{ctx.get('pending_foreshadowing', '(无)')}

请输出：
1. 偏离分析（实际产出 vs 大纲）
2. 角色活跃度（谁被遗忘了？）
3. 伏笔健康度（哪个埋太久了？）
4. 下 5 章优先级建议"""

    def _apply_outer_feedback(self, report: dict, current_chapter: int):
        """将外层报告应用到状态管理。"""
        # 如果有 Retcon 方案，写入 StateManager 的 pending_retcons
        if report.get("retcon_plan"):
            logger.info("外层 Retcon 方案待应用: %s", report["retcon_plan"])

    # ==================================================================
    # 保存与状态
    # ==================================================================
    def _save_chapter(self, ch: int, result: dict, validation: ValidationResult):
        """保存章节到文件。"""
        chapters_dir = self.book_dir / "chapters"
        chapters_dir.mkdir(parents=True, exist_ok=True)

        content = result.get("content", "")
        if not content or content.startswith("[写作失败"):
            return

        # 优先用自动修复后的文本
        if validation.auto_fix_text:
            content = validation.auto_fix_text

        filename = f"第{ch:03d}章_正文.txt"
        filepath = chapters_dir / filename
        filepath.write_text(content, encoding="utf-8")

    def _update_state(self, ch: int, content: str):
        """更新 StateManager（自动提取人物/伏笔变化）。"""
        try:
            self.state.record_chapter(
                chapter_num=ch,
                content=content,
            )
        except Exception as e:
            logger.warning(f"状态更新失败（非致命）: {e}")
