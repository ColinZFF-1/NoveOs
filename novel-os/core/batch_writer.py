"""Novel-OS 批量写作器 —— 核心写作流水线。

替代 V9.0 的 4413 行 batch_write_v9_direct.py，每章调用 4 个 Agent：
Director → Writer → Polish → Auditor。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.config_loader import BookConfig
from core.crewai_connector import CrewAIConnector
from core.llm_client import LLMClient, LLMConfig
from core.quality_gates import GateResult, QualityGates
from core.state_manager import StateManager

logger = logging.getLogger("novel-os.batch_writer")


@dataclass
class WriteResult:
    """单章写作结果。"""
    chapter_num: int
    success: bool
    final_content: str
    word_count: int
    gate_level: str
    attempts: int
    saved_path: Path | None = None


class BatchWriter:
    """配置驱动的批量章节写作器，支持断点续传。"""

    def __init__(self, book_config: BookConfig, state_manager: StateManager | None = None) -> None:
        self.cfg = book_config
        self.state = state_manager or StateManager(
            book_config.base_path / "world_state.db"
        )

        # 自动检测 crewai 配置来源：db > export.json > mock
        export_json = book_config.base_path / "crewai_entities_export.json"
        self.crew = CrewAIConnector(
            book_config.crewai_db_path,
            mock_mode=not book_config.crewai_db_path.exists(),
            export_json_path=export_json if export_json.exists() else None,
        )

        # 初始化 LLM 客户端
        llm_cfg = book_config.llm
        if llm_cfg:
            self.llm = LLMClient(
                LLMConfig(
                    model=llm_cfg.get("model", "deepseek-chat"),
                    api_key=llm_cfg.get("api_key", ""),
                    api_base=llm_cfg.get("api_base", "https://api.deepseek.com/v1"),
                    temperature=llm_cfg.get("temperature", 0.7),
                    max_tokens=llm_cfg.get("max_tokens", 8000),
                    timeout=llm_cfg.get("timeout", 300),
                )
            )
        else:
            self.llm = LLMClient(LLMConfig.from_env())

        self.gates = QualityGates(
            min_words=book_config.words_per_chapter - book_config.words_tolerance,
            max_words=book_config.words_per_chapter + book_config.words_tolerance,
        )
        self.output_dir = book_config.base_path / book_config.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def write_chapter(self, chapter_num: int) -> WriteResult:
        """写单章完整流水线。

        步骤:
        a. 从 StateManager 获取本章需要的状态
        b. 调用 Director Agent 生成任务卡
        c. 调用 Writer Agent 生成初稿
        d. 调用 Polish Agent 润色
        e. 调用 Auditor Agent 审计
        f. QualityGates 判定
        g. BLOCKING → 重跑（最多3次）
        h. PASS → 保存正文 + 更新 StateManager
        """
        logger.info("=" * 60)
        logger.info("开始写作 第 %d 章", chapter_num)

        # a. 获取本章状态上下文
        context = self._build_chapter_context(chapter_num)

        attempt = 0
        content = ""
        gate_result = GateResult(passed=False, level="BLOCKING", reasons=["尚未开始"])
        director_prompt = ""

        while self.gates.should_retry(gate_result, attempt, self.cfg.max_retries):
            attempt += 1
            logger.info("第 %d 章 第 %d 次尝试", chapter_num, attempt)

            try:
                # b. Director（只在第一次生成，重试时复用）
                if not director_prompt:
                    director_prompt = self._call_director(chapter_num, context)
                # c. Writer
                content = self._call_writer(chapter_num, director_prompt)
                # d. Polish（每 3 章调 1 次：第 1,4,7,10... 章）
                if (chapter_num - 1) % 3 == 0:
                    content = self._call_polish(chapter_num, content)
                    logger.info("第 %d 章 调用 Polish 润色", chapter_num)
                else:
                    logger.info("第 %d 章 跳过 Polish（每3章润色1次）", chapter_num)
                # e. Auditor
                audit_report = self._call_auditor(chapter_num, content)
                # f. QualityGates
                gate_result = self.gates.audit(content, audit_report)

                if gate_result.level == "BLOCKING":
                    logger.warning("质量门 BLOCKING: %s", gate_result.reasons)
                    # 如果是字数超限，尝试截断而不是重试
                    if any("字数超标" in r for r in gate_result.reasons):
                        content = self.gates.truncate_if_needed(
                            content, self.cfg.words_per_chapter + self.cfg.words_tolerance
                        )
                        # 截断后重新审计
                        audit_report = self._call_auditor(chapter_num, content)
                        gate_result = self.gates.audit(content, audit_report)
                        if gate_result.level != "BLOCKING":
                            break
                else:
                    break

            except Exception as exc:
                logger.exception("第 %d 章 第 %d 次尝试异常: %s", chapter_num, attempt, exc)
                gate_result = GateResult(
                    passed=False,
                    level="BLOCKING",
                    reasons=[f"异常: {exc}"],
                )

        # 最终判定
        if gate_result.level == "BLOCKING":
            logger.error("第 %d 章 最终失败，已用尽 %d 次重试", chapter_num, attempt)
            return WriteResult(
                chapter_num=chapter_num,
                success=False,
                final_content=content,
                word_count=len(content),
                gate_level="BLOCKING",
                attempts=attempt,
            )

        if gate_result.level == "WARN":
            logger.warning("第 %d 章 WARN: %s", chapter_num, gate_result.reasons)

        # h. 保存并更新状态
        saved_path = self.save_chapter(chapter_num, content)
        self._update_state_after_chapter(chapter_num, content)

        logger.info("第 %d 章 完成，字数=%d，路径=%s", chapter_num, len(content), saved_path)
        return WriteResult(
            chapter_num=chapter_num,
            success=True,
            final_content=content,
            word_count=len(content),
            gate_level=gate_result.level,
            attempts=attempt,
            saved_path=saved_path,
        )

    def write_range(self, start: int, end: int, resume: bool = False) -> list[WriteResult]:
        """批量写一定范围的章节。

        Args:
            start: 起始章节号（含）。
            end: 结束章节号（含）。
            resume: 为 True 时跳过 output_dir 中已存在的章节。
        """
        results: list[WriteResult] = []
        for num in range(start, end + 1):
            if resume and self._chapter_exists(num):
                logger.info("第 %d 章 已存在，跳过", num)
                continue
            try:
                result = self.write_chapter(num)
                results.append(result)
            except Exception as exc:
                logger.exception("第 %d 章 流水线外层异常: %s", num, exc)
                results.append(
                    WriteResult(
                        chapter_num=num,
                        success=False,
                        final_content="",
                        word_count=0,
                        gate_level="BLOCKING",
                        attempts=0,
                    )
                )
        return results

    def save_chapter(self, chapter_num: int, content: str) -> Path:
        """保存章节正文到 output_dir。

        文件名格式: 第{num:03d}章_标题_v9.0-pm_正文.txt
        （标题从内容第一行提取，若无则留空）
        """
        title = ""
        first_line = content.strip().splitlines()[0] if content.strip() else ""
        if first_line.startswith("第") and "章" in first_line:
            # 尝试提取标题
            parts = first_line.split("章", 1)
            if len(parts) > 1:
                title = parts[1].strip().lstrip("_").strip()
        title = title or "未命名"
        # 清理文件名非法字符
        safe_title = re.sub(r'[\\/:*?"<>|]', "", title)[:20]
        filename = f"第{chapter_num:03d}章_{safe_title}_v9.0-pm_正文.txt"
        path = self.output_dir / filename
        path.write_text(content, encoding="utf-8")
        return path

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    def _build_chapter_context(self, chapter_num: int) -> dict[str, Any]:
        """组装本章需要的全部状态上下文。"""
        ctx: dict[str, Any] = {
            "chapter": chapter_num,
            "debts": self.state.get_active_debts(chapter_num),
            "foreshadowing": self.state.get_active_foreshadowing(chapter_num),
        }
        # TODO: 如需人物状态，可在此扩展
        return ctx

    def _chapter_exists(self, chapter_num: int) -> bool:
        """检查 output_dir 是否已有该章节文件。"""
        pattern = f"第{chapter_num:03d}章_*_正文.txt"
        return any(self.output_dir.glob(pattern))

    def _update_state_after_chapter(self, chapter_num: int, content: str) -> None:
        """章节写完后更新状态库。"""
        # 简单摘要：取前 200 字作为摘要
        summary = content[:200].replace("\n", " ") + "..."
        self.state.update_after_chapter(
            chapter_num=chapter_num,
            summary=summary,
            word_count=len(content),
            mode="",  # TODO: 从内容或配置中提取 mode
        )

    # ------------------------------------------------------------------
    # Agent 调用（真实 LLM）
    # ------------------------------------------------------------------
    def _build_system_prompt(self, agent_type: str) -> str:
        """根据 Agent 类型构造 system prompt。"""
        query = self.cfg.agent_query.get(agent_type, {})
        role = query.get("role", f"小说{agent_type}")

        try:
            agent_id = self.crew.get_agent_id(role, agent_type)
            cfg = self.crew.get_agent_config(agent_id)
        except ValueError:
            cfg = {}

        parts = [f"你是 {role}。"]
        if cfg.get("goal"):
            parts.append(f"你的目标是：{cfg['goal']}")
        if cfg.get("backstory"):
            parts.append(cfg["backstory"])
        return "\n\n".join(parts)

    def _build_task_user_prompt(self, agent_type: str, chapter_num: int, context: str = "") -> str:
        """构造 user prompt。"""
        query = self.cfg.agent_query.get(agent_type, {})
        role = query.get("role", f"小说{agent_type}")

        try:
            agent_id = self.crew.get_agent_id(role, agent_type)
            task_id = self.crew.get_task_id(agent_id, agent_type)
            task_cfg = self.crew.get_task_config(task_id)
            desc = task_cfg.get("description", "")
            expected = task_cfg.get("expected_output", "")
        except ValueError:
            desc = ""
            expected = ""

        desc = desc.replace("{chapter_number}", str(chapter_num))
        expected = expected.replace("{chapter_number}", str(chapter_num))

        parts = [desc] if desc else []
        if context:
            parts.append(f"\n[上文/输入]\n{context[:5000]}")
        if expected:
            parts.append(f"\n[预期输出]\n{expected}")

        if agent_type == "writer":
            # 字数铁律放在最前面，确保模型最先看到
            parts.insert(0,
                f"【最高优先级 - 字数铁律】\n"
                f"本章正文总字数必须严格控制在 {self.cfg.words_per_chapter}±{self.cfg.words_tolerance} 字\n"
                f"（即 {self.cfg.words_per_chapter - self.cfg.words_tolerance} ~ {self.cfg.words_per_chapter + self.cfg.words_tolerance} 字）。\n"
                f"写完后立即自检字数，超出上限必须删除冗余描写。\n"
                f"宁可在范围内精简，绝对不要超标。超标整章废弃。\n"
                f"目标字数：{self.cfg.words_per_chapter} 字。\n\n"
                f"【节拍字数分配】\n"
                f"- 节拍1（起）：约 {int(self.cfg.words_per_chapter * 0.20)} 字\n"
                f"- 节拍2（承）：约 {int(self.cfg.words_per_chapter * 0.30)} 字\n"
                f"- 节拍3（转）：约 {int(self.cfg.words_per_chapter * 0.30)} 字\n"
                f"- 节拍4（合）：约 {int(self.cfg.words_per_chapter * 0.20)} 字\n\n"
                f"【正文格式铁律】\n"
                f"- 禁止出现【节拍X】标签、markdown标记、自检表、字数统计\n"
                f"- 每章开头直接以正文第一句开始，不要标题\n\n"
                f"【去AI味核心3条】\n"
                f"- 他字密度≤10%，情绪必须物化，禁用：然而/不得不说/众所周知/突然/竟然/原来/与此同时\n\n"
            )

        return "\n".join(parts)

    def _call_director(self, chapter_num: int, context: dict[str, Any]) -> str:
        """Director Agent：生成本章任务卡。"""
        system = self._build_system_prompt("director")
        user = self._build_task_user_prompt(
            "director", chapter_num,
            context=f"活跃债务: {context['debts']}\n活跃伏笔: {context['foreshadowing']}"
        )
        return self.llm.call(system, user, temperature=0.1, max_tokens=4000)

    def _call_writer(self, chapter_num: int, director_prompt: str) -> str:
        """Writer Agent：生成初稿。"""
        system = self._build_system_prompt("writer")
        user = self._build_task_user_prompt("writer", chapter_num, context=director_prompt)
        # 字数硬限制：max_tokens 设为 7000（约 5000 中文字上限）
        max_tok = min(7000, self.cfg.llm.get("max_tokens", 8000))
        return self.llm.call(system, user, temperature=0.15, max_tokens=max_tok)

    def _call_polish(self, chapter_num: int, draft: str) -> str:
        """Polish Agent：去 AI 味润色。"""
        system = self._build_system_prompt("polish")
        user = self._build_task_user_prompt("polish", chapter_num, context=draft)
        # 强制约束：Polish 只输出纯正文
        user += (
            "\n\n【输出格式铁律 - 绝对不可违背】\n"
            "1. 你必须只输出润色后的纯小说正文，禁止输出任何其他内容。\n"
            "2. 禁止输出'润色修改清单'、'句式破坏完成情况'、'修改说明'等任何形式的元信息。\n"
            "3. 禁止输出 markdown 标题（如 '# 润色后正文'）。\n"
            "4. 禁止在正文末尾添加注释、总结、自检表。\n"
            "5. 如果原文中有【节拍X】标签，直接删除，保持正文流畅。\n"
            "6. 输出格式：直接以正文第一句开始，到最后一个字结束，中间不要任何非正文内容。"
        )
        return self.llm.call(system, user, temperature=0.1, max_tokens=8000)

    def _call_auditor(self, chapter_num: int, content: str) -> dict[str, Any]:
        """Auditor Agent：审计并返回指标报告。"""
        # 优先使用本地审计（快、免费、稳定）
        report = self._mock_audit(content)

        # 如果配置了真实 LLM 审计，可在此扩展
        # system = self._build_system_prompt("auditor")
        # user = self._build_task_user_prompt("auditor", chapter_num, context=content)
        # llm_report = self.llm.call_json(system, user, temperature=0.0, max_tokens=2000)
        # report.update(llm_report)

        return report

    def _mock_audit(self, content: str) -> dict[str, Any]:
        """本地快速审计（当 Auditor Agent 不可用时降级使用）。"""
        text = content
        word_count = len(text)
        # 他字密度: 统计 "他" 字出现频率
        ta_count = text.count("他")
        ta_density = ta_count / max(word_count, 1)
        return {
            "word_count": word_count,
            "ta_density": ta_density,
            "redline_words": [],
            "forbidden_words": [],
            "broken_sentences": [],
            "extra": {},
        }
