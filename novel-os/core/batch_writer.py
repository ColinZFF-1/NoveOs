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
from core.event_bus import EventBus
from core.chapter_validator import ChapterValidator, ValidationResult, ValidationIssue
from core.guard_registry_init import get_registry
from core.interceptor import DeAIInterceptor
from core.iwr_analyzer import analyze_chapter
from core.llm_client import LLMClient, LLMConfig
from core.platform_scorer import score_platform_adaptation, compute_genre_dna_match
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
            book_config.base_path / "world_state.db",
            project_id=book_config.base_path.name,
        )
        self._event_bus = event_bus

        # 初始化 DeAI 拦截器（从 world_state 读取规则配置）
        try:
            interceptor_rules = self.state.get_interceptor_rules()
        except Exception:
            interceptor_rules = {}
        self.interceptor = DeAIInterceptor(rules=interceptor_rules)

        # 自动检测 crewai 配置来源：db > yaml > export.json > mock
        export_json = book_config.base_path / "crewai_entities_export.json"
        yaml_dir = book_config.base_path.parent / "crewai"
        self.crew = CrewAIConnector(
            book_config.crewai_db_path,
            mock_mode=not book_config.crewai_db_path.exists(),
            export_json_path=export_json if export_json.exists() else None,
            yaml_dir=yaml_dir if yaml_dir.exists() else None,
        )

        # 初始化 LLM 客户端（支持主 Provider + Fallback）
        def _build_llm_cfg(cfg_dict: dict[str, Any]) -> LLMConfig:
            return LLMConfig(
                model=cfg_dict.get("model", "deepseek-v4-pro"),
                api_key=cfg_dict.get("api_key", ""),
                api_base=cfg_dict.get("api_base", "https://api.deepseek.com/v1"),
                temperature=cfg_dict.get("temperature", 0.7),
                max_tokens=cfg_dict.get("max_tokens", 8000),
                timeout=cfg_dict.get("timeout", 300),
                reasoning_effort=cfg_dict.get("reasoning_effort", "high"),
                thinking_enabled=cfg_dict.get("thinking_enabled", True),
            )

        llm_cfg = book_config.llm
        fallback_cfg = book_config.llm_fallback
        if llm_cfg:
            primary = _build_llm_cfg(llm_cfg)
            fallback = _build_llm_cfg(fallback_cfg) if fallback_cfg else None
            self.llm = LLMClient(primary, fallback)
        else:
            self.llm = LLMClient(LLMConfig.from_env())

        # ChapterValidator：统一校验层（替代 QualityGates + Interceptor + 8 Guards）
        self.validator = ChapterValidator()

        self.output_dir = book_config.base_path / book_config.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def write_chapter(self, chapter_num: int) -> WriteResult:
        """写单章完整流水线（7阶Agent）。

        步骤:
        1. Director      → 生成任务卡
        2. BeatPlanner   → 六段式节拍分配
        3. SceneWriter   → 场景正文（自由创作）
        4. HookEngineer  → 开头/结尾优化（IWR+钩子）
        5. DialogueTuner → 对话优化（占比+道说比）
        6. Interceptor   → AI味扫描
        7. Polish        → 全文润色
        8. Auditor       → 结构审计
        9. BLOCKING      → 智能回退（对应Agent修正）
        10. PASS         → 保存正文 + 更新 StateManager
        """
        logger.info("=" * 60)
        logger.info("开始写作 第 %d 章", chapter_num)

        context = self._build_chapter_context(chapter_num)

        attempt = 0
        content = ""
        validation = ValidationResult(verdict="BLOCK", issues=[])
        director_prompt = ""
        beat_plan = ""
        chapter_title = ""
        audit_report: dict[str, Any] = {}

        # 结构化修正指令，按 Agent 分类
        corrections: dict[str, str] = {
            "scene_writer": "",
            "hook_engineer": "",
            "dialogue_tuner": "",
            "global": "",
        }

        while self.validator.should_retry(validation, attempt, self.cfg.max_retries):
            attempt += 1
            logger.info("第 %d 章 第 %d 次尝试", chapter_num, attempt)

            try:
                # 1. Director（只在第一次生成，重试时复用）
                if not director_prompt:
                    self._emit_agent_event("agent_call_start", chapter_num, "Director", "生成任务卡")
                    director_prompt = self._call_director(chapter_num, context)
                    self._emit_agent_event("agent_call_complete", chapter_num, "Director", "任务卡已生成")
                    chapter_title = self._extract_title_from_director(director_prompt, chapter_num)
                    if chapter_title:
                        self._save_chapter_title(chapter_num, chapter_title)
                        logger.info("第 %d 章 标题: %s", chapter_num, chapter_title)

                # 2. BeatPlanner（只在第一次生成，重试时复用）
                if not beat_plan:
                    self._emit_agent_event("agent_call_start", chapter_num, "BeatPlanner", "六段式节拍分配")
                    beat_plan = self._call_beat_planner(chapter_num, director_prompt, context)
                    self._emit_agent_event("agent_call_complete", chapter_num, "BeatPlanner", "节拍分配完成")
                    logger.info("第 %d 章 BeatPlanner 完成", chapter_num)

                # 3. SceneWriter（场景正文，只负责按节拍表创作）
                self._emit_agent_event("agent_call_start", chapter_num, "SceneWriter", "创作场景正文")
                scene_draft = self._call_scene_writer(chapter_num, beat_plan, corrections)
                self._emit_agent_event("agent_call_complete", chapter_num, "SceneWriter", "正文创作完成")
                logger.info("第 %d 章 SceneWriter 完成", chapter_num)

                # 4. HookEngineer（开头/结尾优化，确保IWR和钩子）
                self._emit_agent_event("agent_call_start", chapter_num, "HookEngineer", "优化钩子和IWR")
                hook_draft = self._call_hook_engineer(chapter_num, scene_draft, context, corrections)
                self._emit_agent_event("agent_call_complete", chapter_num, "HookEngineer", "钩子优化完成")
                logger.info("第 %d 章 HookEngineer 完成", chapter_num)

                # 5. DialogueTuner（对话优化，确保对话占比和道说比）
                self._emit_agent_event("agent_call_start", chapter_num, "DialogueTuner", "优化对话和道说比")
                content = self._call_dialogue_tuner(chapter_num, hook_draft, context, corrections)
                self._emit_agent_event("agent_call_complete", chapter_num, "DialogueTuner", "对话优化完成")
                logger.info("第 %d 章 DialogueTuner 完成", chapter_num)

                # 6. ChapterValidator 快速扫描（替代 DeAI Interceptor）
                quick_check = self.validator.validate(content, {"chapter_num": chapter_num})
                polish_extra = self.validator.build_retry_feedback(quick_check) if quick_check.issues else ""
                if quick_check.issues:
                    content = quick_check.auto_fix_text or content
                    logger.info("第 %d 章 Validator 标红 %d 处", chapter_num, len(quick_check.issues))

                # 7. Polish（每 3 章调 1 次；如有问题则强制润色）
                should_polish = (chapter_num - 1) % 3 == 0 or bool(quick_check.issues)
                if should_polish:
                    self._emit_agent_event("agent_call_start", chapter_num, "Polish", "去AI味润色")
                    content = self._call_polish(chapter_num, content, extra_instruction=polish_extra)
                    self._emit_agent_event("agent_call_complete", chapter_num, "Polish", "润色完成")
                    logger.info("第 %d 章 调用 Polish 润色", chapter_num)
                else:
                    logger.info("第 %d 章 跳过 Polish", chapter_num)

                # 8. Auditor + ChapterValidator（审计+校验合并）
                audit_report = self._call_auditor(chapter_num, content)
                validation = self.validator.validate(content, {
                    "chapter_num": chapter_num,
                    "state_manager": self.state,
                    "core_event": context.get("outline", {}).get("core_event", ""),
                })

                if validation.verdict == "BLOCK":
                    logger.warning("ChapterValidator BLOCK: %s",
                                   [i.message for i in validation.issues if i.level == "BLOCK"])

                    # 字数超标 → 截断
                    if any("字数超标" in i.message for i in validation.issues if i.level == "BLOCK"):
                        # 简单截断到最大字数
                        max_chars = self.cfg.words_per_chapter + self.cfg.words_tolerance
                        if len(content) > max_chars:
                            content = content[:max_chars] + "\n\n[本章因超字数截断]"
                        validation = self.validator.validate(content, {"chapter_num": chapter_num})
                        if validation.verdict != "BLOCK":
                            break

                    # 字数不足 → Expander
                    elif any("字数不足" in i.message for i in validation.issues if i.level == "BLOCK"):
                        short_by = self.cfg.words_per_chapter - self.cfg.words_tolerance - validation.metrics.get("word_count", 0)
                        expanded = self._call_expander(chapter_num, content, max(short_by, 200))
                        content = content + "\n\n" + expanded
                        validation = self.validator.validate(content, {"chapter_num": chapter_num})
                        if validation.verdict != "BLOCK":
                            break
                        short_by2 = self.cfg.words_per_chapter - self.cfg.words_tolerance - self._count_chinese_chars(content)
                        corrections["scene_writer"] += (
                            f"\n字数仍不足，当前{self._count_chinese_chars(content)}字，"
                            f"需再扩写{max(short_by2, 200)}字。"
                        )
                        logger.info("第 %d 章 Expander 后仍不足，回退 SceneWriter", chapter_num)

                    # 结构问题 → 智能回退
                    else:
                        corrections = self._generate_corrections(validation, audit_report)
                        logger.info("第 %d 章 结构问题，回退修正", chapter_num)
                else:
                    break

            except Exception as exc:
                logger.exception("第 %d 章 第 %d 次尝试异常: %s", chapter_num, attempt, exc)
                validation = ValidationResult(verdict="BLOCK", issues=[ValidationIssue("BLOCK", "异常", str(exc))])

        # 最终判定
        final_word_count = self._count_chinese_chars(content)
        if validation.verdict == "BLOCK":
            logger.error("第 %d 章 最终失败，已用尽 %d 次重试", chapter_num, attempt)
            return WriteResult(
                chapter_num=chapter_num, success=False, final_content=content,
                word_count=final_word_count, gate_level="BLOCKING",
                attempts=attempt, audit_report=audit_report,
            )

        if validation.verdict == "WARN":
            logger.warning("第 %d 章 WARN: %s", chapter_num,
                           [i.message for i in validation.issues])

        # 9. ChapterValidator 已统一处理所有检查，无需额外的 Guard 遍历
        logger.info("ChapterValidator 检查完成: %s, %d issues",
                     validation.verdict, len(validation.issues))

        # ★ 标题兜底：检查正文首行是否为标题格式，如果不是则从 Director 任务卡提取并插入
        content = self._ensure_title_prefix(chapter_num, content, director_prompt)

        saved_path = self.save_chapter(chapter_num, content)
        self._update_state_after_chapter(chapter_num, content, title=chapter_title)

        logger.info("第 %d 章 完成，中文字数=%d，路径=%s", chapter_num, final_word_count, saved_path)
        return WriteResult(
            chapter_num=chapter_num, success=True, final_content=content,
            word_count=final_word_count, gate_level=validation.verdict,
            attempts=attempt, saved_path=saved_path, audit_report=audit_report,
        )

    def _generate_corrections(
        self, validation, audit_report: dict[str, Any]
    ) -> dict[str, str]:
        """根据 ChapterValidator 结果生成各 Agent 的修正指令。"""
        corrections: dict[str, str] = {
            "scene_writer": "", "hook_engineer": "", "dialogue_tuner": "", "global": ""
        }
        extra = audit_report.get("extra", {})

        # 从 ValidationResult 提取 block/warn 原因
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

        return corrections

    def set_outer_crew_feedback(
        self,
        retcons: list[str] | None = None,
        emotion_targets: list[dict[str, Any]] | None = None,
        priorities: list[str] | None = None,
    ) -> None:
        """从 Orchestrator 接收外层 CrewAI 反馈，注入后续章节上下文。"""
        if retcons is not None:
            self._pending_retcons = retcons
        if emotion_targets is not None:
            self._emotion_targets = emotion_targets
        if priorities is not None:
            self._outer_crew_priorities = priorities
        logger.info(
            "BatchWriter 已接收外层反馈: retcons=%d, emotions=%d, priorities=%d",
            len(self._pending_retcons) if hasattr(self, "_pending_retcons") else 0,
            len(self._emotion_targets) if hasattr(self, "_emotion_targets") else 0,
            len(self._outer_crew_priorities) if hasattr(self, "_outer_crew_priorities") else 0,
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
        标题优先从 world_state.db 读取，其次从内容中提取。
        """
        # 优先从数据库读取标题
        title = self._get_chapter_title(chapter_num) or self._extract_title(chapter_num, content)
        # 清理文件名非法字符
        safe_title = re.sub(r'[\\/:*?"<>|]', "", title)[:20]
        filename = f"第{chapter_num:03d}章_{safe_title}_正文.txt"
        path = self.output_dir / filename
        path.write_text(content, encoding="utf-8")
        return path

    def _get_chapter_title(self, chapter_num: int) -> str:
        """从 world_state.db 读取章节标题。"""
        try:
            import sqlite3
            db_path = self.cfg.base_path / "world_state.db"
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.execute(
                    "SELECT title FROM chapter_history WHERE project_id = ? AND chapter = ?",
                    (self.state.project_id, chapter_num),
                )
                row = cursor.fetchone()
                return row[0] if row and row[0] else ""
        except Exception:
            return ""

    @staticmethod
    def _extract_title_from_director(director_prompt: str, chapter_num: int) -> str:
        """从 Director 任务卡中提取章节标题，并验证章节号匹配。"""
        lines = director_prompt.strip().splitlines()
        for line in lines[:8]:
            line = line.strip()
            # 匹配 【标题】第X章：标题名
            if line.startswith("【标题】"):
                inner = line[4:].strip()
                m = re.match(r'第\s*(\d+)\s*章\s*[：:\s_]*(.+)', inner)
                if m:
                    declared_num = int(m.group(1))
                    title = m.group(2).strip()
                    if declared_num == chapter_num:
                        return title[:20]
                    else:
                        # 章节号不匹配，返回空让后续 fallback 处理
                        return ""
            # 匹配 第X章：标题名（无【标题】前缀）
            m = re.match(r'第\s*(\d+)\s*章\s*[：:\s_]*(.+)', line)
            if m:
                declared_num = int(m.group(1))
                title = m.group(2).strip()
                if declared_num == chapter_num:
                    return title[:20]
                else:
                    return ""
        return ""

    def _save_chapter_title(self, chapter_num: int, title: str) -> None:
        """保存章节标题到 world_state.db。"""
        try:
            import sqlite3
            db_path = self.cfg.base_path / "world_state.db"
            with sqlite3.connect(str(db_path)) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO chapter_history (project_id, chapter, title, created_at) VALUES (?, ?, ?, datetime('now'))",
                    (self.state.project_id, chapter_num, title),
                )
                conn.commit()
        except Exception:
            pass

    def _ensure_title_prefix(self, chapter_num: int, content: str, director_prompt: str) -> str:
        """标题兜底：检查正文首行是否为标题格式，如果不是则从 Director 任务卡提取并插入。"""
        if not content.strip():
            return content
        lines = content.strip().splitlines()
        if not lines:
            return content
        # 检查首行是否已经是正确的标题格式
        first_line = lines[0].strip()
        title_pattern = re.compile(r'^第\s*' + str(chapter_num) + r'\s*章\s*[：:\s_]*.+$')
        if title_pattern.match(first_line):
            return content
        # 首行不是标题，尝试从 Director 任务卡提取
        title = self._extract_title_from_director(director_prompt, chapter_num)
        if not title:
            # Director 任务卡也没有，尝试从首行内容推断一个简短标题
            title = self._extract_title(chapter_num, content)
            if title == "未命名":
                title = ""
        if title:
            # 在正文开头插入标题
            new_content = f"第{chapter_num}章：{title}\n\n{content.strip()}"
            logger.info("第 %d 章 标题兜底：插入标题 '%s'", chapter_num, title)
            return new_content
        return content

    @staticmethod
    def _extract_title(chapter_num: int, content: str) -> str:
        """从正文内容中提取章节标题，支持多种格式，严格校验章节号。"""
        if not content.strip():
            return "未命名"

        lines = content.strip().splitlines()

        # 策略1: 匹配 markdown 格式 # 第X章 标题
        md_pattern = re.compile(r'^#\s*第\s*(\d+)\s*章\s*[：:\s_]*(.+)$')
        for line in lines[:5]:
            m = md_pattern.match(line.strip())
            if m:
                declared_num = int(m.group(1))
                title = m.group(2).strip()
                if declared_num == chapter_num:
                    return title

        # 策略2: 匹配 第X章 标题（无 markdown，支持中文数字）
        plain_pattern = re.compile(r'^第\s*(\d+|一|二|三|四|五|六|七|八|九|十)\s*章\s*[：:\s_]*(.+)$')
        for line in lines[:5]:
            m = plain_pattern.match(line.strip())
            if m:
                num_str = m.group(1)
                title = m.group(2).strip()
                # 中文数字转阿拉伯数字
                cn_to_num = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}
                declared_num = cn_to_num.get(num_str, int(num_str) if num_str.isdigit() else -1)
                if declared_num == chapter_num:
                    return title

        # 策略3: 在全文搜索 "第N章" 附近是否有标题提示
        search_pattern = re.compile(r'第\s*' + str(chapter_num) + r'\s*章\s*[：:\s_]*([^\n]{1,30})')
        m = search_pattern.search(content)
        if m:
            return m.group(1).strip()

        return "未命名"

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    def _emit_agent_event(self, event: str, chapter_num: int, agent: str, detail: str = "") -> None:
        """通过 EventBus 发布 Agent 级别事件，前端实时展示进度。"""
        if self._event_bus:
            self._event_bus.emit(
                event,
                {
                    "chapter_num": chapter_num,
                    "agent": agent,
                    "detail": detail,
                    "project_id": getattr(self.cfg, "base_path", Path(".")).name,
                },
            )

    def _build_chapter_context(self, chapter_num: int) -> dict[str, Any]:
        """组装本章需要的全部状态上下文（含品类 DNA）。"""
        ctx: dict[str, Any] = {
            "chapter": chapter_num,
            "debts": self.state.get_active_debts(chapter_num),
            "foreshadowing": self.state.get_active_foreshadowing(chapter_num),
            "outline": self._get_chapter_outline(chapter_num),
            "characters": self._get_character_states(),
            "rules": self._get_consistency_rules(),
            "genre_dna": self.state.get_genre_dna(),
        }
        # ★ 注入外层 CrewAI 反馈
        if getattr(self, "_pending_retcons", None):
            ctx["outer_crew_retcons"] = self._pending_retcons
        if getattr(self, "_emotion_targets", None):
            ctx["emotion_targets"] = self._emotion_targets
        if getattr(self, "_outer_crew_priorities", None):
            ctx["outer_crew_priorities"] = self._outer_crew_priorities
        return ctx

    def _get_chapter_outline(self, chapter_num: int) -> dict[str, str]:
        """从 world_state.db outline 表读取本章详细规划。"""
        try:
            import sqlite3
            db_path = self.cfg.base_path / "world_state.db"
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.execute(
                    "SELECT arc, core_event, face_slap_target, face_slap_method, husband_moment, chapter_hook, emotion_ratio, skill_unlocked FROM outline WHERE project_id = ? AND chapter = ?",
                    (self.state.project_id, chapter_num),
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "arc": row[0] or "",
                        "core_event": row[1] or "",
                        "face_slap_target": row[2] or "",
                        "face_slap_method": row[3] or "",
                        "husband_moment": row[4] or "",
                        "chapter_hook": row[5] or "",
                        "emotion_ratio": row[6] or "",
                        "skill_unlocked": row[7] or "",
                    }
        except Exception as exc:
            logger.warning("读取 outline 失败: %s", exc)
        return {}

    def _get_character_states(self) -> list[dict]:
        """从 world_state.db 读取活跃人物状态。"""
        try:
            import sqlite3
            db_path = self.cfg.base_path / "world_state.db"
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.execute(
                    "SELECT character_name, location, emotional_state, known_secrets, unknown_secrets, abilities_active, dialog_fingerprint, body_language, physical_description FROM character_states WHERE project_id = ?",
                    (self.state.project_id,),
                )
                rows = cursor.fetchall()
                return [
                    {
                        "name": r[0], "location": r[1], "emotional_state": r[2],
                        "known_secrets": r[3], "unknown_secrets": r[4], "abilities": r[5],
                        "dialog_fingerprint": r[6], "body_language": r[7], "description": r[8],
                    }
                    for r in rows
                ]
        except Exception as exc:
            logger.warning("读取人物状态失败: %s", exc)
        return []

    def _get_consistency_rules(self) -> list[str]:
        """从 world_state.db 读取写作规则。"""
        try:
            import sqlite3
            db_path = self.cfg.base_path / "world_state.db"
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.execute(
                    "SELECT rule_type, rule_content FROM consistency_rules WHERE project_id = ? AND enforcement_level = 'hard'",
                    (self.state.project_id,),
                )
                rows = cursor.fetchall()
                return [f"[{r[0]}] {r[1]}" for r in rows]
        except Exception as exc:
            logger.warning("读取规则失败: %s", exc)
        return []

    def _chapter_exists(self, chapter_num: int) -> bool:
        """检查 output_dir 是否已有该章节文件。"""
        pattern = f"第{chapter_num:03d}章_*_正文.txt"
        return any(self.output_dir.glob(pattern))

    def _count_chinese_chars(self, text: str) -> int:
        """统计中文字符数（CJK 统一表意文字）。"""
        import re
        return len(re.findall(r'[\u4e00-\u9fff]', text))

    def _update_state_after_chapter(self, chapter_num: int, content: str, title: str = "") -> None:
        """章节写完后更新状态库（含 RAG 结构指标）。"""
        summary = content[:200].replace("\n", " ") + "..."
        word_count = self._count_chinese_chars(content)
        self.state.update_after_chapter(
            chapter_num=chapter_num,
            summary=summary,
            word_count=word_count,
            mode="",
            title=title,
        )
        self.state.update_project_status(
            current_chapter=chapter_num,
            status="writing",
        )
        # 写入结构指标（RAG 分析驱动）
        metrics = analyze_chapter(content)
        history = self.state.list_chapters()
        hist_word_counts = [h.get("word_count", 0) or 0 for h in history if h.get("word_count")]
        platform = score_platform_adaptation(metrics, hist_word_counts)
        genre_dna = self.state.get_genre_dna()
        dna_match = compute_genre_dna_match(metrics, genre_dna)
        # 确保 metrics 中所有值为 SQLite 支持的类型
        metrics.update({
            "platform_score": platform.get("platform_score", 0),
            "platform_grade": platform.get("platform_grade", "C"),
            "genre_dna_match": dna_match if isinstance(dna_match, (int, float)) else dna_match.get("dna_match", 0.5),
        })
        # 清理不可序列化的字段
        clean_metrics = {}
        for k, v in metrics.items():
            if isinstance(v, (int, float, str, bool, type(None))):
                clean_metrics[k] = v
            elif isinstance(v, dict):
                # 嵌套 dict 只保留简单值
                for sub_k, sub_v in v.items():
                    if isinstance(sub_v, (int, float, str, bool, type(None))):
                        clean_metrics[f"{k}_{sub_k}"] = sub_v
        self.state.update_chapter_metrics(chapter_num, clean_metrics)
        # 写入情感坐标：优先LLM标注，失败回退到字符计数
        emotion = self._analyze_emotion_llm(chapter_num, content)
        if emotion is None:
            # 回退：字符计数
            nue = content.count("怒") + content.count("恨") + content.count("杀")
            tian = content.count("甜") + content.count("笑") + content.count("爱")
            shuang = content.count("爽") + content.count("赢") + content.count("碾压")
            total = nue + tian + shuang + 1
            emotion = {
                "nue": nue / total,
                "tian": tian / total,
                "shuang": shuang / total,
                "coord_x": 0.0,
                "coord_y": 0.0,
                "desc": f"IWR={metrics['iwr_score']}, Platform={platform['platform_grade']} (字符计数回退)",
            }
        self.state.update_emotion_history(
            chapter_num=chapter_num,
            mode="llm" if emotion.get("source") == "llm" else "auto",
            nue=emotion["nue"],
            tian=emotion["tian"],
            shuang=emotion["shuang"],
            coord_x=emotion.get("coord_x", 0.0),
            coord_y=emotion.get("coord_y", 0.0),
            desc=emotion.get("desc", ""),
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

        # 同时替换两种占位符（YAML 中可能用 {chapter} 或 {chapter_number}）
        for placeholder in ["{chapter_number}", "{chapter}"]:
            desc = desc.replace(placeholder, str(chapter_num))
            expected = expected.replace(placeholder, str(chapter_num))

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
                f"- 每章开头必须写标题，格式：第{chapter_num}章：标题（标题由任务卡指定，不可自拟，严禁写其他章节的标题）\n"
                f"- 标题后空一行，再开始正文\n\n"
                f"【对话铁律 - 绝对不可违背】\n"
                f"1. 本章对话占比必须控制在 25%-45%。对话是推动情节的核心手段，不是点缀。\n"
                f"2. 每章至少包含 3-5 组人物对话场景，每组对话不少于 3 轮交锋。\n"
                f"3. 对话中禁止用'道/说'以外的同义替换词（不可：低语/呢喃/沉声道/冷声道/缓缓道）。\n"
                f"4. 对话簇长度≤3段，禁止出现'对话块'超过3段的连续对话。\n\n"
                f"【去AI味核心6条】\n"
                f"1. 他字密度≤10%，情绪必须物化\n"
                f"2. 绝对禁用词（出现即FAIL）：突然、竟然、原来、与此同时、然而、不得不说、众所周知、微微、淡淡、缓缓、轻轻、忽然\n"
                f"3. 禁止'不是X，是Y'句式。全文最多允许1处\n"
                f"4. 极端情绪下感知必须模糊化，禁止精确测量式描写\n"
                f"5. 环境描写必须做减法，只保留带叙事功能的锚点\n"
                f"6. 比喻必须私有化，禁止公共库存比喻\n\n"
            )

        return "\n".join(parts)

    def _call_director(self, chapter_num: int, context: dict[str, Any]) -> str:
        """Director Agent：生成本章任务卡（含标题）。"""
        system = self._build_system_prompt("director")

        # 构造大纲驱动的上下文
        outline = context.get("outline", {})
        outline_text = ""
        if outline:
            outline_text = (
                f"\n【本章大纲】\n"
                f"卷名/篇名：{outline.get('arc', '')}\n"
                f"核心事件：{outline.get('core_event', '')}\n"
                f"打脸对象：{outline.get('face_slap_target', '')}\n"
                f"打脸方式：{outline.get('face_slap_method', '')}\n"
                f"护妻时刻：{outline.get('husband_moment', '')}\n"
                f"章末钩子：{outline.get('chapter_hook', '')}\n"
                f"情绪配比：{outline.get('emotion_ratio', '')}\n"
                f"技能解锁：{outline.get('skill_unlocked', '')}\n"
            )
        else:
            outline_text = "\n【注意】本章暂无大纲，请基于上下文合理设计。\n"

        # 人物状态
        chars = context.get("characters", [])
        chars_text = ""
        if chars:
            chars_text = "\n【人物状态】\n" + "\n".join(
                f"- {c['name']}（{c['location']}）：{c['emotional_state']}。\n  已知秘密：{c['known_secrets']}\n  对话指纹：{c['dialog_fingerprint']}\n  肢体语言：{c['body_language']}"
                for c in chars[:5]
            )

        # 硬规则
        rules = context.get("rules", [])
        rules_text = ""
        if rules:
            rules_text = "\n【必须遵守的写作铁律】\n" + "\n".join(f"{i+1}. {r}" for i, r in enumerate(rules))

        # ★ 外层 CrewAI 反馈注入
        outer_feedback_text = ""
        if context.get("outer_crew_retcons"):
            outer_feedback_text += "\n【外层 CrewAI 修正指令（必须遵守）】\n"
            for i, retcon in enumerate(context["outer_crew_retcons"], 1):
                outer_feedback_text += f"{i}. {retcon[:300]}\n"
        if context.get("emotion_targets"):
            outer_feedback_text += "\n【情绪目标指引】\n"
            for et in context["emotion_targets"]:
                outer_feedback_text += f"- {et.get('suggestion', '')[:200]}\n"
        if context.get("outer_crew_priorities"):
            outer_feedback_text += "\n【架构优先级指引】\n"
            for p in context["outer_crew_priorities"]:
                outer_feedback_text += f"- {p[:200]}\n"

        user = self._build_task_user_prompt(
            "director", chapter_num,
            context=f"活跃债务: {context['debts']}\n活跃伏笔: {context['foreshadowing']}{outline_text}{chars_text}{rules_text}{outer_feedback_text}"
        )
        user += (
            f"\n\n【输出格式要求】\n"
            f"任务卡第一行必须是章节标题，格式：【标题】第{chapter_num}章：标题名\n"
            f"标题名要求：4-8个字，紧扣本章核心事件，有网文感，不要文艺腔。\n"
            f"【绝对铁律】当前是第{chapter_num}章，任务卡中的标题必须写'第{chapter_num}章'，严禁写其他章节的编号。\n"
            f"标题后空一行，再写正文任务卡内容。\n"
            f"任务卡必须严格基于【本章大纲】设计，不能偏离大纲中的核心事件、打脸方式和章末钩子。"
        )
        return self.llm.call(system, user, temperature=0.1, max_tokens=4000)

    def _call_beat_planner(self, chapter_num: int, director_prompt: str, context: dict[str, Any]) -> str:
        """BeatPlanner Agent：将 Director 任务卡转换为六段式节拍分配表。"""
        system = (
            "你是 BeatPlanner（节拍分配师）。\n"
            "你的任务是将导演任务卡拆解为六段式节拍分配表，精确到每段的字数范围和核心内容。\n"
            "你只做字数分配和内容规划，不输出正文。\n"
            "\n【核心职责 - 绝对不可违背】\n"
            "1. 六段式节拍表中必须包含至少 3-5 个对话场景节点。\n"
            "2. 对话不是点缀，是推动情节的核心手段——没有对话的节拍表是失败的。\n"
            "3. 每个对话节点必须标注：参与人物、核心冲突、预估字数。"
        )
        target = self.cfg.words_per_chapter
        tol = self.cfg.words_tolerance
        min_w = target - tol
        max_w = target + tol
        # 品类 DNA
        genre_dna = context.get("genre_dna", {})
        dna_text = ""
        if genre_dna:
            dna_text = (
                f"\n【品类DNA基准】\n"
                f"- 平均句长: {genre_dna.get('avg_sentence_length', 'N/A')} 字\n"
                f"- 道说比: {genre_dna.get('dao_shuo_ratio', 'N/A')}\n"
                f"- 对话占比: {genre_dna.get('dialogue_ratio', 'N/A')}%"
            )
        user = (
            f"【任务】为第{chapter_num}章生成六段式节拍分配表。\n"
            f"\n【字数要求】总字数 {min_w}~{max_w} 字（目标 {target} 字）\n"
            f"- 起（钩子引入）: {int(target * 0.15)}±{tol//4} 字\n"
            f"- 承1（铺垫展开）: {int(target * 0.15)}±{tol//4} 字\n"
            f"- 承2（矛盾升级）: {int(target * 0.15)}±{tol//4} 字\n"
            f"- 转（核心冲突）: {int(target * 0.25)}±{tol//3} 字\n"
            f"- 合1（情绪释放）: {int(target * 0.15)}±{tol//4} 字\n"
            f"- 合2（章末钩子）: {int(target * 0.15)}±{tol//4} 字\n"
            f"{dna_text}\n"
            f"\n【导演任务卡】\n{director_prompt}\n"
            f"\n【对话场景规划 - 绝对不可违背】\n"
            f"六段式节拍表中必须包含至少 3-5 个对话场景节点。\n"
            f"每个对话节点必须标注：\n"
            f"1. 段名标记：在对应段名后标注【对话场景】\n"
            f"2. 参与人物（2-3人）\n"
            f"3. 核心冲突（不是闲聊，必须推进情节或揭示秘密）\n"
            f"4. 预估对话字数（确保总对话字数 ≥ {int(target * 0.25)} 字，即总字数的25%）\n"
            f"\n对话节点分布建议：\n"
            f"- 起：1个对话（引出悬念或人物关系）\n"
            f"- 承1-2：1-2个对话（铺垫升级，信息交换）\n"
            f"- 转：1个对话（核心冲突爆发，情绪对峙）\n"
            f"- 合1-2：1个对话（情绪释放或钩子铺垫）\n"
            f"\n【输出格式】\n"
            f"按六段输出，每段包含：\n"
            f"1. 段名（起/承1/承2/转/合1/合2）【对话场景】（如该段包含对话）\n"
            f"2. 字数范围\n"
            f"3. 核心内容简述（2-3句）\n"
            f"4. 对话场景规划（如有）：人物+冲突+预估字数\n"
            f"5. 必须包含的伏笔/债务/钩子（如有）\n"
            f"\n【对话字数自检】\n"
            f"输出完成后，统计所有对话节点的预估字数总和，确保 ≥ {int(target * 0.25)} 字。\n"
            f"如果不足，调整对话节点数量或单节点字数，直到达标。\n"
            f"\n禁止输出任何正文内容。"
        )
        return self.llm.call(system, user, temperature=0.1, max_tokens=3000)

    def _call_scene_writer(self, chapter_num: int, beat_plan: str, corrections: dict[str, str]) -> str:
        """SceneWriter Agent：根据节拍分配表创作场景正文。\n\n        职责：自由创作高质量场景正文，只受字数铁律和修正指令约束。\n        不控制 IWR、对话占比、DNA 等——这些由下游 Agent 负责。\n        """
        system = (
            "你是 SceneWriter（场景写作师）。\n"
            "你的职责：根据节拍分配表，创作高质量的小说场景正文。\n"
            "你在情节推进、人物塑造、场景描写、情绪渲染层面拥有创作自由。\n"
            "但以下铁律属于绝对约束，不属于创作自由范畴，必须严格遵守。\n"
            "\n【格式铁律 - 绝对不可违背】\n"
            "1. 每章正文第一行必须是标题，格式：第N章：标题名。标题后必须空一行再开始正文。\n"
            "2. 禁止出现【节拍X】标签、markdown标记、自检表、字数统计。\n"
            "\n【对话铁律 - 绝对不可违背】\n"
            "1. 本章对话占比必须控制在 25%-45%。对话是推动情节的核心手段，不是点缀。\n"
            "2. 每章至少包含 3-5 组人物对话场景，每组对话不少于 3 轮交锋。\n"
            "3. 对话中禁止用'道/说'以外的同义替换词（不可：低语/呢喃/沉声道/冷声道/缓缓道）。\n"
            "4. 对话簇长度≤3段，禁止出现'对话块'超过3段的连续对话。\n"
            "\n【反AI味铁律 - 绝对不可违背】\n"
            "1. 禁止在相邻两段中使用'不是X，是Y'或'不是……是那种……'句式。全文最多允许1处。用具体感受替代：'肌肉记忆'替代'那种听到关键词的条件反射'。\n"
            "2. 当角色处于恐惧/紧张/痛苦状态时，感知必须模糊化。'照片好像动了一下'比'照片往左移动三毫米'好一万倍。人类在极端情绪下的感知是失焦的、变形的、不可靠的。\n"
            "3. 环境描写必须做减法：删掉50%无叙事功能的环境细节，只保留一个核心锚点，并赋予它叙事功能。'椅子间距一米五'→暗示曾被绑缚；'抽屉深处的胶质'→暗示前一个受害者。没有叙事功能的环境描写是AI味的源头。\n"
            "4. 比喻必须私有化：禁止用公共库存比喻（如'细线吊着嘴角''溺水者看浮木''磁带被水浸过'）。林默的比喻必须带着HR视角的绩效评估冷酷感，苏晚的比喻必须带着规则执行者的精确感。比喻的杀伤力在于不可复制。\n"
            "5. 金手指的呈现必须是认知错位，不是游戏UI。禁止'黑色背景绿色字'的赛博朋克式代码流。改用肉体层面的不适：融化、粘连、高温、失焦、耳鸣、反胃。\n"
            "6. 描写痛苦的极限是3个感官细节。第4个必须是留白、沉默、或主角的意识中断。过度描写会杀死恐怖感。\n"
            "7. 每章必须给主角至少一个'废动作'——与主线无关、暴露他是活人的细节（走神、肚子叫、注意到主管的鼻毛、想起早餐的味道）。这些是AI最难生成的东西，也是最有价值的东西。\n"
            "8. 系统的规则漏洞不得被主角'轻松破解'。破解过程必须伴随犹豫、恐惧、身体代价、和系统的反扑。完美闭合的逻辑回路是程序员的自我满足，不是文学。"
        )
        user = (
            f"【任务】根据以下节拍分配表，创作第{chapter_num}章的完整正文。\n\n"
            f"【节拍分配表】\n{beat_plan}\n"
        )
        # 注入修正指令
        if corrections.get("scene_writer"):
            user += f"\n【修正指令 - 必须执行】\n{corrections['scene_writer']}\n"
        target = self.cfg.words_per_chapter
        tol = self.cfg.words_tolerance
        min_w = target - tol
        max_w = target + tol
        user += (
            f"\n【字数铁律 - 绝对不可违背】\n"
            f"本章正文总字数（仅统计中文字符）必须严格控制在 {min_w} ~ {max_w} 字。\n"
            f"每完成一个节拍，估算已写中文字数。\n"
            f"最终输出必须满足字数要求。\n\n"
            f"【格式铁律 - 绝对不可违背】\n"
            f"- 每章开头必须写标题，格式：第{chapter_num}章：标题名（标题来自导演任务卡，严禁自拟或写其他章节的标题）\n"
            f"- 正文内容必须严格对应第{chapter_num}章的节拍分配表，严禁写其他章节的内容\n"
            f"- 标题后空一行，再开始正文\n"
            f"- 禁止出现【节拍X】标签、markdown标记、自检表"
        )
        max_tok = self.cfg.llm.get("max_tokens", 8000) * 2  # double for Chinese chars
        return self.llm.call(system, user, temperature=0.15, max_tokens=max_tok)

    def _call_hook_engineer(self, chapter_num: int, scene_draft: str, context: dict[str, Any], corrections: dict[str, str]) -> str:
        """HookEngineer Agent：优化开头和结尾，确保 IWR 和钩子密度。"""
        system = (
            "你是 HookEngineer（钩子工程师）。\n"
            "你的职责：优化章节的开头和结尾，确保信息扣留比（IWR）≥2.0 且钩子密度足够。\n"
            "你只做三件事：\n"
            "1. 检查开头是否在前50字内抛出情境悬念（不是概述，而是让读者想知道'发生了什么'）。\n"
            "2. 检查结尾是否留下未解之谜（不立刻揭示答案，答案留到后续章节）。\n"
            "3. 如果开头/结尾不满足要求，只修改这两处，保留中间正文不变。\n"
            "\n规则：\n"
            "- 开头前50字必须有未解之谜（可用：难道/莫非/究竟/为何/怎么/会不会/是否）\n"
            "- 结尾最后100字必须留下至少1个未解之谜（不要回答！让读者好奇）\n"
            "- 不要在结尾揭示本章悬念的答案\n"
            "- 保留中间所有正文内容，只改开头和结尾\n"
            "\n【结尾多样性铁律 - 绝对不可违背】\n"
            "- 禁止使用'主角静止动作 + 物品特写 + 悬念信息'作为连续两章的结尾结构。\n"
            "- 三章内，结尾必须轮换至少两种不同的收束方式。\n"
            "- 推荐的结尾节奏（轮换使用）：\n"
            "  1. 对话戛然而止（某人说出半句话被打断/沉默）\n"
            "  2. 环境突变（灯灭/声音消失/温度骤降）\n"
            "  3. 主角做出反直觉动作（放弃抵抗/主动走向危险/对不该笑的人笑）\n"
            "  4. 第三方突然介入（一个不该出现的人/声音/物品闯入画面）\n"
            "  5. 视角强制抽离（主角失去意识/被拽走/画面突然切断）"
        )
        # 品类 DNA 和 IWR 目标
        genre_dna = context.get("genre_dna", {})
        user = (
            f"【任务】优化第{chapter_num}章的开头（前50字）和结尾（最后100字），确保钩子密度。\n\n"
            f"【当前正文】\n{scene_draft}\n"
        )
        if corrections.get("hook_engineer"):
            user += f"\n【修正指令 - 必须执行】\n{corrections['hook_engineer']}\n"
        user += (
            f"\n【输出要求】\n"
            f"1. 如果开头/结尾已满足要求，原样输出全文。\n"
            f"2. 如果需要修改，只改开头和结尾，中间正文一字不动。\n"
            f"3. 只输出纯正文，不要任何说明、标记或元信息。"
        )
        return self.llm.call(system, user, temperature=0.1, max_tokens=8000)

    def _call_dialogue_tuner(self, chapter_num: int, hook_draft: str, context: dict[str, Any], corrections: dict[str, str]) -> str:
        """DialogueTuner Agent：优化对话密度和道说比，确保符合品类 DNA。"""
        system = (
            "你是 DialogueTuner（对话调优师）。\n"
            "你的职责：优化全章对话，确保对话占比和'道/说'比率符合品类 DNA。\n"
            "你只做两件事：\n"
            "1. 调整对话密度（目标占比依品类而定，言情通常 40-55%）。\n"
            "2. 优化'道/说'比（目标依品类而定，言情通常 0.6-0.8，即'道'是'说'的60-80%）。\n"
            "\n规则：\n"
            "- 对话段落（以引号开头）应占全章的 25%-45%（言情 40-55%）\n"
            "- '道'字出现次数与'说'字出现次数的比值应接近品类 DNA\n"
            "- 对话簇≤3段（连续对话不超过3个来回）\n"
            "- 对话内容体现角色差异，避免千人一面\n"
            "- 优先保留核心对话，精简冗余对白\n"
            "- 如果对话占比过低，适当添加对话；如果过高，转为叙述"
        )
        # 品类 DNA
        genre_dna = context.get("genre_dna", {})
        target_dialogue = genre_dna.get("dialogue_ratio", 40)
        target_daoshuo = genre_dna.get("dao_shuo_ratio", 0.7)
        user = (
            f"【任务】优化第{chapter_num}章的对话，确保品类DNA匹配。\n\n"
            f"【当前正文】\n{hook_draft}\n"
        )
        if corrections.get("dialogue_tuner"):
            user += f"\n【修正指令 - 必须执行】\n{corrections['dialogue_tuner']}\n"
        user += (
            f"\n【品类DNA目标】\n"
            f"- 对话占比目标: {target_dialogue}%\n"
            f"- 道说比目标: {target_daoshuo}（'道'次数 / '说'次数）\n"
            f"\n【输出要求】\n"
            f"1. 输出优化后的完整正文。\n"
            f"2. 只改对话部分，叙述和描写尽量不动。\n"
            f"3. 只输出纯正文，不要任何说明、标记或元信息。"
        )
        return self.llm.call(system, user, temperature=0.1, max_tokens=8000)

    def _call_writer(self, chapter_num: int, director_prompt: str, extra_instruction: str = "") -> str:
        """Writer Agent：已废弃，保留兼容（现由 SceneWriter 替代）。"""
        logger.warning("Writer Agent 已废弃，请使用 SceneWriter")
        return self._call_scene_writer(chapter_num, director_prompt, {})

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
        """Auditor Agent：结构审计 + LLM 深度审计（可配置开关）。"""
        report = self._structural_audit(content, chapter_num)

        # LLM 深度审计（默认启用，可通过 book.yaml llm.auditor_enabled=false 关闭）
        if self.cfg.llm.get("auditor_enabled", True):
            try:
                system = self._build_auditor_system_prompt()
                user = self._build_auditor_user_prompt(chapter_num, content, report)
                llm_report = self.llm.call_json(system, user, temperature=0.0, max_tokens=2000)
                if isinstance(llm_report, dict):
                    report["llm_audit"] = llm_report
                    # 如果LLM发现严重问题，升级审计级别
                    if any(
                        v.get("score", 10) < 5
                        for v in llm_report.values()
                        if isinstance(v, dict) and "score" in v
                    ):
                        report["llm_flagged"] = True
                logger.info("第 %d 章 LLM深度审计完成", chapter_num)
            except Exception as exc:
                logger.warning("第 %d 章 LLM深度审计失败（回退到结构审计）: %s", chapter_num, exc)

        return report

    def _build_auditor_system_prompt(self) -> str:
        """构建 Auditor Agent 的 system prompt。"""
        query = self.cfg.agent_query.get("auditor", {})
        role = query.get("role", "小说审计师")
        goal = query.get("goal", "审计字数、他字密度、禁用词、年代一致性、IWR、平台适配度")
        return (
            f"你是 {role}。你的目标是：{goal}。\n\n"
            "你需要从以下5个维度对章节进行深度审计，每个维度给出1-10分的评分和具体点评。\n"
            "如果发现问题，必须指出具体位置和修改建议。\n\n"
            "返回严格JSON格式，不要有任何额外文字：\n"
            "{\n"
            '  "dialogue_rhythm": {"score": 1-10, "comment": "对话节奏点评", "issues": ["具体问题1", ...]},\n'
            '  "scene_causality": {"score": 1-10, "comment": "场景因果自洽性", "issues": []},\n'
            '  "character_arc": {"score": 1-10, "comment": "角色弧光进展", "issues": []},\n'
            '  "info_density": {"score": 1-10, "comment": "信息密度评估", "issues": []},\n'
            '  "hook_strength": {"score": 1-10, "comment": "钩子强度", "issues": []},\n'
            '  "overall_comment": "总体评价和优先修改建议"\n'
            "}"
        )

    def _build_auditor_user_prompt(self, chapter_num: int, content: str, report: dict) -> str:
        """构建 Auditor Agent 的 user prompt。"""
        target = self.cfg.words_per_chapter
        tol = self.cfg.words_tolerance
        parts = [
            f"【任务】深度审计第{chapter_num}章。",
            f"【字数标准】目标 {target}±{tol} 字。",
            f"【结构审计结果】",
            f"- 字数: {report.get('word_count', 0)}",
            f"- IWR: {report.get('extra', {}).get('iwr_score', 0)}",
            f"- 平台分: {report.get('extra', {}).get('platform_score', 0)} ({report.get('extra', {}).get('platform_grade', '')})",
            f"- DNA匹配: {report.get('extra', {}).get('genre_dna_match', 0)}",
            f"- 他字密度: {report.get('ta_density', 0):.2%}",
            f"- 对话占比: {report.get('extra', {}).get('dialogue_ratio', 0):.1%}",
            f"- 句长: {report.get('extra', {}).get('sentence_length', 0)}",
            "",
            "【待审计正文（前8000字）】",
            content[:8000],
        ]
        return "\n".join(parts)

    def _analyze_emotion_llm(self, chapter_num: int, content: str) -> dict[str, Any] | None:
        """LLM情感标注：分析本章虐/甜/爽三轴情感坐标。"""
        try:
            system = (
                "你是情感分析专家。分析小说章节的情感成分占比。\n"
                "只返回严格JSON，不要任何额外文字。\n"
                "JSON格式：\n"
                "{\n"
                '  "nue": 0.0-1.0,  // 虐（痛苦/压抑/悲伤/愤怒）占比\n'
                '  "tian": 0.0-1.0,  // 甜（温馨/浪漫/喜悦）占比\n'
                '  "shuang": 0.0-1.0, // 爽（逆袭/胜利/碾压/畅快）占比\n'
                '  "coord_x": -1.0-1.0, // 横轴：压抑(-1)到释放(+1)\n'
                '  "coord_y": -1.0-1.0, // 纵轴：悲伤(-1)到喜悦(+1)\n'
                '  "desc": "情感特征一句话描述，如：先抑后扬，虐转爽"\n'
                "}\n"
                "注意：nue + tian + shuang 不需要等于1，各自独立评分。"
            )
            user = f"【第{chapter_num}章正文（前3000字）】\n{content[:3000]}\n\n请分析情感成分，返回JSON。"
            result = self.llm.call_json(system, user, temperature=0.0, max_tokens=500)
            if isinstance(result, dict) and "nue" in result and "tian" in result and "shuang" in result:
                result["source"] = "llm"
                logger.info("第 %d 章 LLM情感标注: 虐%.2f 甜%.2f 爽%.2f (%s)",
                            chapter_num, result["nue"], result["tian"], result["shuang"], result.get("desc", ""))
                return result
        except Exception as exc:
            logger.warning("第 %d 章 LLM情感标注失败: %s", chapter_num, exc)
        return None

    def _call_expander(self, chapter_num: int, content: str, short_by: int) -> str:
        """Expander Agent：接收现有正文和字数缺口，输出补充内容。

        策略：不推翻已有内容，而是基于已有情节补充细节、对话、心理、环境描写。
        """
        system = (
            "你是一位专业的小说扩写师。你的任务是根据已有的章节内容，"
            "补充更多细节描写，使总字数达到要求。"
            "\n\n规则："
            "\n1. 不要重复已有内容，而是补充新的场景细节、人物对话、心理活动或环境氛围。"
            "\n2. 补充内容必须自然衔接原文，保持情节连贯。"
            "\n3. 直接输出补充的正文段落，不要任何标题、标记或说明。"
            "\n4. 只输出中文正文。"
        )
        user = (
            f"以下是第 {chapter_num} 章的已有内容（当前字数不足，需要补充约 {short_by} 字）：\n\n"
            f"{content[:3000]}\n\n"
            f"【任务】请基于以上内容，补充约 {short_by} 字的新内容。"
            f"可以添加：更详细的场景描写、人物对话、内心独白、环境氛围渲染等。"
            f"不要重复已有内容，直接输出补充的正文段落。"
        )
        max_tok = min(4000, self.cfg.llm.get("max_tokens", 8000))
        return self.llm.call(system, user, temperature=0.2, max_tokens=max_tok)

    def _structural_audit(self, content: str, chapter_num: int) -> dict[str, Any]:
        """结构审计（RAG 分析驱动）：IWR、平台适配度、品类 DNA 匹配度。"""
        import re
        text = content
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        word_count = len(chinese_chars)
        ta_count = text.count("他") + text.count("她") + text.count("它")
        ta_density = ta_count / max(word_count, 1)
        forbidden_words = ["然而", "不得不说", "众所周知", "突然", "竟然", "原来",
                           "与此同时", "紧接着", "果不其然"]
        found_forbidden = [w for w in forbidden_words if w in text]

        # RAG 驱动的结构分析
        metrics = analyze_chapter(text)
        history = self.state.list_chapters()
        hist_word_counts = [h.get("word_count", 0) or 0 for h in history if h.get("word_count")]
        platform = score_platform_adaptation(metrics, hist_word_counts)
        genre_dna = self.state.get_genre_dna()
        dna_match = compute_genre_dna_match(metrics, genre_dna)

        return {
            "word_count": word_count,
            "ta_density": ta_density,
            "redline_words": [],
            "forbidden_words": found_forbidden,
            "broken_sentences": [],
            "extra": {
                "iwr_score": metrics["iwr_score"],
                "questions_count": metrics["questions_count"],
                "answers_count": metrics["answers_count"],
                "hook_ending": metrics["hook_ending"],
                "sentence_length": metrics["sentence_length"],
                "dialogue_ratio": metrics["dialogue_ratio"],
                "oscillations": metrics["oscillations"],
                "platform_score": platform.get("platform_score", 0),
                "platform_grade": platform.get("platform_grade", "C"),
                "platform_breakdown": platform.get("breakdown", {}),
                "genre_dna_match": dna_match,
            },
        }
