"""
Novel-OS Pipeline —— 双层 CrewAI 调度主循环。

外层（每 5-10 章）：4 个战略 Agent —— 架构巡检 / 一致性 / 节奏 / 回溯修正
内层（每章）：7 个战术 Agent —— 规划 → 写作 → 润色 → 审计
精度层（每章）：ChapterValidator + StateManager + Expander

替代旧版 orchestrator.py 中分散的写章逻辑。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from core.batch_writer import BatchWriter
from core.config_loader import BookConfig
from core.llm_client import LLMClient
from core.outer_crew_runner import OuterCrewRunner
from core.state_manager import StateManager

logger = logging.getLogger("novel-os.pipeline")


class NovelPipeline:
    """双层调度流水线。"""

    def __init__(self, book_config: BookConfig):
        self.config = book_config
        self.book_dir = Path(book_config.base_path or ".")
        self.state = StateManager(self.book_dir / "world_state.db")

        # 内层写手（内部已含 Validator + Expander，无需外层重复）
        self.inner_writer = BatchWriter(book_config, self.state)

        # 外层巡检运行器（接入真实 LLM）
        self.outer_crew = OuterCrewRunner(book_config, self.state, self.inner_writer.llm)

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

            # ── 写一章（BatchWriter 内部已含 Validator + Expander + 重试）──
            result = self.inner_writer.write_chapter(ch)

            results[ch] = {
                "success": result.success,
                "verdict": result.gate_level,
                "word_count": result.word_count,
                "attempts": result.attempts,
            }
            print(f"  [完成] 第 {ch} 章: success={result.success} | {result.word_count} 字 | {result.attempts} 次尝试")

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
    # 内层（已委托给 BatchWriter，内部含完整 7 阶流水线）
    # ==================================================================

    # ==================================================================
    # 外层
    # ==================================================================
    def _run_outer_check(self, current_chapter: int) -> dict:
        """执行外层 4 Agent 巡检，通过 OuterCrewRunner 调用真实 LLM。"""
        report: dict[str, Any] = {
            "architecture_health": "?",
            "critical_issues": 0,
            "pacing_diagnosis": "?",
            "retcon_plan": None,
        }

        if not self.outer_crew.is_available():
            logger.info("[外层] 配置不可用，跳过巡检")
            return report

        try:
            # Agent 1: 全书架构师
            arch = self.outer_crew.run_architecture_review(current_chapter)
            report["architecture_health"] = arch.health_grade or "?"
            report["next_5_priorities"] = arch.next_5_priorities
            logger.info("[外层] 架构巡检完成，健康度=%s", arch.health_grade)

            # Agent 2: 一致性巡检
            conti = self.outer_crew.run_continuity_check(current_chapter)
            report["critical_issues"] = len([i for i in conti.issues if i.severity == "🔴"])
            report["has_critical"] = conti.has_critical
            logger.info("[外层] 一致性巡检完成，矛盾=%d，致命=%s",
                       len(conti.issues), conti.has_critical)

            # Agent 3: 节奏分析（每 10 章）
            if current_chapter % 10 == 0:
                pacing = self.outer_crew.run_pacing_analysis(current_chapter)
                report["pacing_diagnosis"] = pacing.rhythm_diagnosis or "?"
                logger.info("[外层] 节奏分析完成，诊断=%s", pacing.rhythm_diagnosis)

            # Agent 4: Retcon（致命矛盾时触发）
            if conti.has_critical and conti.issues:
                retcon = self.outer_crew.run_retcon_fix(conti.issues, current_chapter)
                report["retcon_plan"] = [a.fix_text for a in retcon.actions]
                logger.info("[外层] Retcon 完成，修复方案=%d", len(retcon.actions))

        except Exception as exc:
            logger.exception("[外层] 巡检异常（不阻塞写作）: %s", exc)

        return report

    def _apply_outer_feedback(self, report: dict, current_chapter: int):
        """将外层报告应用到状态管理。"""
        # 如果有 Retcon 方案，写入 StateManager 的 pending_retcons
        if report.get("retcon_plan"):
            logger.info("外层 Retcon 方案待应用: %s", report["retcon_plan"])
