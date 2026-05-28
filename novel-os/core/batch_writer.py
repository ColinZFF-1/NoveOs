"""Novel-OS 批量写作器 —— 核心写作流水线。

替代 V9.0 的 4413 行 batch_write_v9_direct.py，每章调用 4 个 Agent：
Director → Writer → Polish → Auditor。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.config_loader import BookConfig
from core.crewai_connector import CrewAIConnector
from core.event_bus import (
    INTERCEPTOR_SCAN_COMPLETE,
    INTERCEPTOR_SCAN_START,
    EventBus,
)
from core.interceptor import DeAIInterceptor
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
    audit_report: dict[str, Any] = field(default_factory=dict)


class BatchWriter:
    """配置驱动的批量章节写作器，支持断点续传。"""

    def __init__(
        self,
        book_config: BookConfig,
        state_manager: StateManager | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self.cfg = book_config
        self.state = state_manager or StateManager(
            book_config.base_path / "world_state.db"
        )
        self._event_bus = event_bus

        # 初始化 DeAI 拦截器（从 world_state 读取规则配置）
        try:
            interceptor_rules = self.state.get_interceptor_rules()
        except Exception:
            interceptor_rules = {}
        self.interceptor = DeAIInterceptor(rules=interceptor_rules)

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
                    model=llm_cfg.get("model", "deepseek-v4-pro"),
                    api_key=llm_cfg.get("api_key", ""),
                    api_base=llm_cfg.get("api_base", "https://api.deepseek.com/v1"),
                    temperature=llm_cfg.get("temperature", 0.7),
                    max_tokens=llm_cfg.get("max_tokens", 8000),
                    timeout=llm_cfg.get("timeout", 300),
                    reasoning_effort=llm_cfg.get("reasoning_effort", "high"),
                    thinking_enabled=llm_cfg.get("thinking_enabled", True),
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
        audit_report: dict[str, Any] = {}

        extra_instruction = ""
        while self.gates.should_retry(gate_result, attempt, self.cfg.max_retries):
            attempt += 1
            logger.info("第 %d 章 第 %d 次尝试", chapter_num, attempt)

            try:
                # b. Director（只在第一次生成，重试时复用）
                if not director_prompt:
                    director_prompt = self._call_director(chapter_num, context)
                # c. Writer（重试时注入修正指令）
                content = self._call_writer(chapter_num, director_prompt, extra_instruction)

                # [新增] DeAI Interceptor 扫描（Writer → Polish 之间）
                if self._event_bus:
                    self._event_bus.emit(
                        INTERCEPTOR_SCAN_START,
                        {"chapter_num": chapter_num, "project_id": getattr(self.cfg, "project_id", "")},
                    )
                scan_result = self.interceptor.scan(content, chapter_num)
                if self._event_bus:
                    self._event_bus.emit(
                        INTERCEPTOR_SCAN_COMPLETE,
                        {
                            "chapter_num": chapter_num,
                            "project_id": getattr(self.cfg, "project_id", ""),
                            "issues_count": len(scan_result.issues),
                            "stats": scan_result.stats,
                            "blocking": scan_result.blocking,
                        },
                    )

                polish_extra = ""
                if scan_result.issues:
                    content = scan_result.modified_text
                    polish_extra = scan_result.repair_instruction
                    logger.info(
                        "第 %d 章 Interceptor 标红 %d 处: %s",
                        chapter_num,
                        len(scan_result.issues),
                        scan_result.issues,
                    )

                # d. Polish（每 3 章调 1 次；如有拦截 issues 则强制润色）
                should_polish = (chapter_num - 1) % 3 == 0 or bool(scan_result.issues)
                if should_polish:
                    content = self._call_polish(chapter_num, content, extra_instruction=polish_extra)
                    logger.info("第 %d 章 调用 Polish 润色", chapter_num)
                else:
                    logger.info("第 %d 章 跳过 Polish（每3章润色1次且无拦截问题）", chapter_num)
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
                    # 如果是字数不足，注入扩写指令
                    elif any("字数不足" in r for r in gate_result.reasons):
                        short_by = self.cfg.words_per_chapter - self.cfg.words_tolerance - audit_report.get("word_count", 0)
                        extra_instruction = (
                            f"上稿字数不足，仅 {audit_report.get('word_count', 0)} 字，"
                            f"距离最低要求还差约 {max(short_by, 200)} 字。\n"
                            f"请扩写：增加场景细节描写、人物心理活动、对话内容或环境氛围渲染。"
                            f"确保最终中文字数 ≥ {self.cfg.words_per_chapter - self.cfg.words_tolerance} 字。"
                        )
                        logger.info("第 %d 章 注入扩写指令: %s", chapter_num, extra_instruction)
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
        final_word_count = self._count_chinese_chars(content)
        if gate_result.level == "BLOCKING":
            logger.error("第 %d 章 最终失败，已用尽 %d 次重试，字数=%d", chapter_num, attempt, final_word_count)
            return WriteResult(
                chapter_num=chapter_num,
                success=False,
                final_content=content,
                word_count=final_word_count,
                gate_level="BLOCKING",
                attempts=attempt,
                audit_report=audit_report,
            )

        if gate_result.level == "WARN":
            logger.warning("第 %d 章 WARN: %s", chapter_num, gate_result.reasons)

        # h. 保存并更新状态
        saved_path = self.save_chapter(chapter_num, content)
        self._update_state_after_chapter(chapter_num, content)

        logger.info("第 %d 章 完成，中文字数=%d，路径=%s", chapter_num, final_word_count, saved_path)
        return WriteResult(
            chapter_num=chapter_num,
            success=True,
            final_content=content,
            word_count=final_word_count,
            gate_level=gate_result.level,
            attempts=attempt,
            saved_path=saved_path,
            audit_report=audit_report,
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

        文件名格式: 第{num:03d}章_标题_正文.txt
        （标题从内容中智能提取，支持多种格式）
        """
        title = self._extract_title(chapter_num, content)
        # 清理文件名非法字符
        safe_title = re.sub(r'[\\/:*?"<>|]', "", title)[:20]
        filename = f"第{chapter_num:03d}章_{safe_title}_正文.txt"
        path = self.output_dir / filename
        path.write_text(content, encoding="utf-8")
        return path

    @staticmethod
    def _extract_title(chapter_num: int, content: str) -> str:
        """从正文内容中提取章节标题，支持多种格式。"""
        if not content.strip():
            return "未命名"

        lines = content.strip().splitlines()

        # 策略1: 匹配 markdown 格式 # 第X章 标题
        md_pattern = re.compile(r'^#\s*第\s*(\d+|一|二|三|四|五|六|七|八|九|十)\s*章\s*[：:\s_]*(.+)$')
        for line in lines[:3]:
            m = md_pattern.match(line.strip())
            if m:
                return m.group(2).strip()

        # 策略2: 匹配 第X章 标题（无 markdown）
        plain_pattern = re.compile(r'^第\s*(\d+|一|二|三|四|五|六|七|八|九|十)\s*章\s*[：:\s_]*(.+)$')
        for line in lines[:3]:
            m = plain_pattern.match(line.strip())
            if m:
                return m.group(2).strip()

        # 策略3: 在全文搜索 "第X章" 附近是否有标题提示
        search_pattern = re.compile(r'第\s*' + str(chapter_num) + r'\s*章\s*[：:\s_]*([^\n]{1,20})')
        m = search_pattern.search(content)
        if m:
            return m.group(1).strip()

        return "未命名"

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

    def _count_chinese_chars(self, text: str) -> int:
        """统计中文字符数（CJK 统一表意文字）。"""
        import re
        return len(re.findall(r'[\u4e00-\u9fff]', text))

    def _update_state_after_chapter(self, chapter_num: int, content: str) -> None:
        """章节写完后更新状态库。"""
        # 简单摘要：取前 200 字作为摘要
        summary = content[:200].replace("\n", " ") + "..."
        self.state.update_after_chapter(
            chapter_num=chapter_num,
            summary=summary,
            word_count=self._count_chinese_chars(content),
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
            target = self.cfg.words_per_chapter
            tol = self.cfg.words_tolerance
            min_w = target - tol
            max_w = target + tol
            # 字数铁律放在最前面，确保模型最先看到
            parts.insert(0,
                f"【系统指令 - 字数铁律 - 绝对不可违背】\n"
                f"1. 本章正文总字数（仅统计中文字符）必须严格控制在 {min_w} ~ {max_w} 字。\n"
                f"2. 目标字数：{target} 字。允许误差 ±{tol} 字，超出即失败。\n"
                f"3. 写作过程中每完成一个节拍，立即估算已写中文字数，确保进度与分配一致。\n"
                f"4. 完成全部正文后，必须再次精确统计中文字数。若不足 {min_w} 字，立即补充细节描写、对话或心理活动；若超过 {max_w} 字，立即删除冗余修辞和重复叙述。\n"
                f"5. 字数统计方法：只计算中文汉字（不计算标点、空格、英文字母、数字）。\n"
                f"6. 最终输出必须满足字数要求，否则整章废弃重写。\n\n"
                f"【节拍字数分配 - 含自检节点】\n"
                f"- 节拍1（起）：约 {int(target * 0.20)} 字 → 自检：应达 {int(target * 0.18)}~{int(target * 0.22)} 字\n"
                f"- 节拍2（承）：约 {int(target * 0.30)} 字 → 自检：累计应达 {int(target * 0.48)}~{int(target * 0.52)} 字\n"
                f"- 节拍3（转）：约 {int(target * 0.30)} 字 → 自检：累计应达 {int(target * 0.78)}~{int(target * 0.82)} 字\n"
                f"- 节拍4（合）：约 {int(target * 0.20)} 字 → 自检：总字数必须 ≥{min_w} 字\n"
                f"注意：每个节拍完成后立即估算中文字数，不足就补充细节，超标就精简。\n\n"
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

    def _call_writer(self, chapter_num: int, director_prompt: str, extra_instruction: str = "") -> str:
        """Writer Agent：生成初稿。支持注入扩写/精简等额外指令。"""
        system = self._build_system_prompt("writer")
        user = self._build_task_user_prompt("writer", chapter_num, context=director_prompt)
        if extra_instruction:
            user += f"\n\n【修正指令 - 本次必须执行】\n{extra_instruction}\n"
        # 字数硬限制：max_tokens 设为 7000（约 5000 中文字上限）
        max_tok = min(7000, self.cfg.llm.get("max_tokens", 8000))
        return self.llm.call(system, user, temperature=0.15, max_tokens=max_tok)

    def _call_polish(self, chapter_num: int, draft: str, extra_instruction: str = "") -> str:
        """Polish Agent：去 AI 味润色。支持注入拦截器修复指令。"""
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
        if extra_instruction:
            user += f"\n\n{extra_instruction}\n"
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
        import re
        text = content
        # 中文字数：统计 CJK 统一表意文字
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        word_count = len(chinese_chars)
        # 他字密度: 统计 "他" 字出现频率（基于中文字数）
        ta_count = text.count("他") + text.count("她") + text.count("它")
        ta_density = ta_count / max(word_count, 1)
        # 禁用词检测
        forbidden_words = ["然而", "不得不说", "众所周知", "突然", "竟然", "原来",
                           "与此同时", "紧接着", "果不其然"]
        found_forbidden = [w for w in forbidden_words if w in text]
        return {
            "word_count": word_count,
            "ta_density": ta_density,
            "redline_words": [],
            "forbidden_words": found_forbidden,
            "broken_sentences": [],
            "extra": {},
        }
