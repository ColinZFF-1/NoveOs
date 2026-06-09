"""Novel-OS 批量写作器 —— 核心写作流水线。

替代 V9.0 的 4413 行 batch_write_v9_direct.py，每章调用 4 个 Agent：
Director → Writer → Polish → Auditor。
"""
from __future__ import annotations

import logging
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from core.config_loader import BookConfig

from core.event_bus import EventBus
from core.chapter_validator import ChapterValidator, ValidationResult, ValidationIssue, TERM_MANDATORY
from core.guard_registry_init import get_registry
from core.iwr_analyzer import analyze_chapter
from core.llm_client import LLMClient, LLMConfig
from core.platform_scorer import score_platform_adaptation, compute_genre_dna_match
from core.state_manager import StateManager
from core.post_write_validator import PostWriteValidator, PostValidationResult
from core.input_governor import InputGovernor
from core.anti_detect_reviser import AntiDetectReviser

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

        # ★ project_id 启动校验：防止 book.yaml 与数据库不一致
        self._validate_project_id()

        # CrewAIConnector 已移除，所有配置直接从 book.yaml 读取
        # DeAIInterceptor 已移除，所有规则扫描统一由 ChapterValidator 执行

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
        agent_cfgs = getattr(book_config, "agent_llm", None)
        if llm_cfg:
            primary = _build_llm_cfg(llm_cfg)
            fallback = _build_llm_cfg(fallback_cfg) if fallback_cfg else None
            self.llm = LLMClient(primary, fallback, agent_configs=agent_cfgs)
        else:
            self.llm = LLMClient(LLMConfig.from_env(), agent_configs=agent_cfgs)

        # ★ InkOS 对标：零成本预检层 + 输入治理 + 反检测改写
        self.post_validator = PostWriteValidator()
        self.input_governor = InputGovernor(book_config, self.state)
        self.anti_detect = AntiDetectReviser()

        # ChapterValidator：统一校验层（替代 QualityGates + Interceptor + 8 Guards）
        # 阈值与 Prompt 保持一致，消除 4000/5000 硬编码与 book_config 的偏差
        validator_thresholds = {
            "min_words": self.cfg.words_per_chapter - self.cfg.words_tolerance,
            "max_words": self.cfg.words_per_chapter + self.cfg.words_tolerance,
        }
        self.validator = ChapterValidator(thresholds=validator_thresholds)

        self.output_dir = book_config.base_path / book_config.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _validate_project_id(self) -> None:
        """校验 book.yaml 与数据库的 project_id 一致性。"""
        try:
            db_info = self.state.get_project_info()
            db_pid = db_info.get("project_id", "")
            cfg_pid = self.state.project_id
            if db_pid and db_pid != cfg_pid:
                logger.error(
                    "project_id 不匹配! 数据库=%s, 配置=%s. "
                    "这将导致 outline/character_states 查询返回空，全书脱离大纲写作。",
                    db_pid, cfg_pid,
                )
                raise ValueError(
                    f"project_id 不匹配: db='{db_pid}' vs cfg='{cfg_pid}'. "
                    f"请统一 book.yaml 的 project 字段与数据库 projects.project_id。"
                )
            if db_pid:
                logger.info("project_id 校验通过: %s", cfg_pid)
            else:
                logger.warning("数据库中无 projects 记录，跳过 project_id 校验")
        except Exception as exc:
            if isinstance(exc, ValueError):
                raise
            logger.warning("project_id 启动校验异常: %s", exc)

    def _call_spot_fix(self, chapter_num: int, content: str, instruction: str) -> str:
        """PostWriteValidator 命中后的 spot-fix 调用。"""
        import re
        original_cn = len(re.findall(r'[\u4e00-\u9fff]', content))
        
        system = (
            "你是 SpotFix Agent。你的任务是根据修正指令对文本做最小改动。\n"
            "规则：\n"
            "- 只修改指令中指出的问题，其他内容一字不动\n"
            "- 不要添加新情节\n"
            "- 绝对只输出修正后的纯正文\n"
        )
        user = f"【修正指令】\n{instruction}\n\n【待修正正文】\n{content}"
        logger.info("第 %d 章 调用 SpotFix", chapter_num)
        result = self.llm.call_for_agent("spot_fix", system, user, temperature=0.3, max_tokens=8000)
        
        # 防御：SpotFix 返回非正文时回退原稿
        result_cn = len(re.findall(r'[\u4e00-\u9fff]', result))
        if original_cn > 500 and result_cn < original_cn * 0.5:
            logger.warning(
                "第 %d 章 SpotFix 返回内容疑似非正文（%d→%d 字），回退原稿",
                chapter_num, original_cn, result_cn
            )
            return content
        # 检测修正指令残留
        if "修正指令" in result[:200] or "指令指出" in result[:200]:
            logger.warning("第 %d 章 SpotFix 返回内容含指令残留，回退原稿", chapter_num)
            return content
        return result

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def write_chapter(self, chapter_num: int) -> WriteResult:
        """写单章入口：完整流水线。"""
        return self._write_full_pipeline(chapter_num)

    def _write_full_pipeline(self, chapter_num: int) -> WriteResult:
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

                # ★ InputGovernor：编译 Writer 输入（对标 InkOS plan → compose）
                compiled = self.input_governor.compile(chapter_num, director_prompt)
                context["compiled"] = compiled
                logger.info("第 %d 章 InputGovernor 编译完成: 意图=%s字, 规则=%d条",
                            chapter_num, len(compiled.intent.core_event),
                            len(compiled.rule_stack.must_rules) + len(compiled.rule_stack.should_rules))

                # 2. BeatPlanner（只在第一次生成，重试时复用）
                if not beat_plan:
                    self._emit_agent_event("agent_call_start", chapter_num, "BeatPlanner", "六段式节拍分配")
                    beat_plan = self._call_beat_planner(chapter_num, director_prompt, context)
                    self._emit_agent_event("agent_call_complete", chapter_num, "BeatPlanner", "节拍分配完成")
                    logger.info("第 %d 章 BeatPlanner 完成", chapter_num)

                # 3. SceneWriter（场景正文，只负责按节拍表创作）
                self._emit_agent_event("agent_call_start", chapter_num, "SceneWriter", "创作场景正文")
                scene_draft = self._call_scene_writer(chapter_num, beat_plan, corrections, compiled)
                self._emit_agent_event("agent_call_complete", chapter_num, "SceneWriter", "正文创作完成")
                logger.info("第 %d 章 SceneWriter 完成", chapter_num)

                # 4. HookEngineer（开头/结尾优化，确保IWR和钩子）
                # ★ 字数保护：SceneWriter 产出已在目标范围内时，HookEngineer 只做最小调整
                scene_cn = len(re.findall(r'[\u4e00-\u9fff]', scene_draft))
                target_min = self.cfg.words_per_chapter - self.cfg.words_tolerance
                target_max = self.cfg.words_per_chapter + self.cfg.words_tolerance
                
                if target_min <= scene_cn <= target_max:
                    logger.info("第 %d 章 SceneWriter 字数已达标(%d)，HookEngineer 最小调整", chapter_num, scene_cn)
                    hook_draft = scene_draft  # 跳过 HookEngineer，避免字数膨胀
                else:
                    self._emit_agent_event("agent_call_start", chapter_num, "HookEngineer", "优化钩子和IWR")
                    hook_draft = self._call_hook_engineer(chapter_num, scene_draft, context, corrections)
                    self._emit_agent_event("agent_call_complete", chapter_num, "HookEngineer", "钩子优化完成")
                    logger.info("第 %d 章 HookEngineer 完成", chapter_num)

                # 5. DialogueTuner（对话优化，确保对话占比和道说比）
                # ★ 字数保护：HookEngineer 后字数仍在范围内时，跳过 DialogueTuner
                hook_cn = len(re.findall(r'[\u4e00-\u9fff]', hook_draft))
                if target_min <= hook_cn <= target_max:
                    logger.info("第 %d 章 HookEngineer 后字数已达标(%d)，跳过 DialogueTuner", chapter_num, hook_cn)
                    content = hook_draft
                else:
                    self._emit_agent_event("agent_call_start", chapter_num, "DialogueTuner", "优化对话和道说比")
                    content = self._call_dialogue_tuner(chapter_num, hook_draft, context, corrections)
                    self._emit_agent_event("agent_call_complete", chapter_num, "DialogueTuner", "对话优化完成")
                    logger.info("第 %d 章 DialogueTuner 完成", chapter_num)

                # ★ PostWriteValidator：零成本预检（对标 InkOS）
                post_result = self.post_validator.validate(content)
                if post_result.verdict == "SPOT_FIX":
                    logger.info("第 %d 章 PostWriteValidator 命中 %d 处",
                                chapter_num, len(post_result.issues))
                    # ★ 临时跳过 SpotFix，避免思考过程污染正文
                    logger.info("第 %d 章 跳过 SpotFix，保留原始内容", chapter_num)
                else:
                    logger.info("第 %d 章 PostWriteValidator PASS", chapter_num)

                # 6. ChapterValidator 快速扫描（替代 DeAI Interceptor）
                quick_check = self.validator.validate(content, {"chapter_num": chapter_num})
                polish_extra = self.validator.build_retry_feedback(quick_check) if quick_check.issues else ""
                if quick_check.issues:
                    content = quick_check.auto_fix_text or content
                    logger.info("第 %d 章 Validator 标红 %d 处", chapter_num, len(quick_check.issues))

                # 7. Polish（每 3 章调 1 次；如有问题则强制润色）
                # ★ 临时禁用 Polish，因为 Kimi-K2.5 对 Polish 任务极不稳定（时而狂删80%时而狂扩200%）
                should_polish = False  # (chapter_num - 1) % 3 == 0 or bool(quick_check.issues)
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

                # ★ AntiDetectReviser：AI 痕迹高时触发反检测改写（对标 InkOS revise --mode anti-detect）
                if validation.verdict != "BLOCK":
                    ai_markers = AntiDetectReviser.compute_ai_marker_score(content)
                    audit_report["ai_markers"] = ai_markers
                    if ai_markers.get("total", 0) > 0.6:
                        logger.warning("第 %d 章 AI 痕迹分数 %.2f，触发反检测改写",
                                       chapter_num, ai_markers["total"])
                        content = self.anti_detect.revise(content, aggressiveness=0.7)
                        # 改写后重新验证
                        validation = self.validator.validate(content, {
                            "chapter_num": chapter_num,
                            "state_manager": self.state,
                            "core_event": context.get("outline", {}).get("core_event", ""),
                        })
                        audit_report["anti_detect_applied"] = True
                        logger.info("第 %d 章 反检测改写后验证: %s", chapter_num, validation.verdict)
                    else:
                        logger.info("第 %d 章 AI 痕迹分数 %.2f，无需改写", chapter_num, ai_markers["total"])

                if validation.verdict == "BLOCK":
                    logger.warning("ChapterValidator BLOCK: %s",
                                   [i.message for i in validation.issues if i.level == "BLOCK"])

                    # 字数超标 → 截断
                    if any("字数超标" in i.message for i in validation.issues if i.level == "BLOCK"):
                        # 截断到中文字数上限
                        max_cn = self.cfg.words_per_chapter + self.cfg.words_tolerance
                        cn_chars = re.findall(r'[\u4e00-\u9fff]', content)
                        if len(cn_chars) > max_cn:
                            # 找到第max_cn个中文字符的位置
                            pos = 0
                            count = 0
                            for m in re.finditer(r'[\u4e00-\u9fff]', content):
                                count += 1
                                if count == max_cn:
                                    pos = m.end()
                                    break
                            content = content[:pos] + "\n\n[本章因超字数截断]"
                            logger.info("第 %d 章 截断到 %d 中文字符", chapter_num, max_cn)
                        validation = self.validator.validate(content, {"chapter_num": chapter_num})
                        if validation.verdict != "BLOCK":
                            break

                    # 字数不足 → Expander（可多次调用）
                    elif any("字数不足" in i.message for i in validation.issues if i.level == "BLOCK"):
                        short_by = self.cfg.words_per_chapter - self.cfg.words_tolerance - validation.metrics.get("word_count", 0)
                        expanded = self._call_expander(chapter_num, content, max(short_by, 200))
                        content = content + "\n\n" + expanded
                        validation = self.validator.validate(content, {"chapter_num": chapter_num})
                        if validation.verdict != "BLOCK":
                            break
                        # 第一次Expander后仍不足，再试一次
                        short_by2 = self.cfg.words_per_chapter - self.cfg.words_tolerance - self._count_chinese_chars(content)
                        if short_by2 > 0:
                            logger.info("第 %d 章 第一次Expander后仍不足%d字，再次调用Expander", chapter_num, short_by2)
                            expanded2 = self._call_expander(chapter_num, content, max(short_by2, 200))
                            content = content + "\n\n" + expanded2
                            validation = self.validator.validate(content, {"chapter_num": chapter_num})
                            if validation.verdict != "BLOCK":
                                break
                            short_by3 = self.cfg.words_per_chapter - self.cfg.words_tolerance - self._count_chinese_chars(content)
                            corrections["scene_writer"] += (
                                f"\n字数仍不足，当前{self._count_chinese_chars(content)}字，"
                                f"需再扩写{max(short_by3, 200)}字。"
                            )
                            logger.info("第 %d 章 第二次Expander后仍不足，回退 SceneWriter", chapter_num)
                        else:
                            break

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
            # ★ BLOCK 也保存草稿，便于调试和人工介入
            if content.strip():
                draft_path = self.save_chapter(chapter_num, content + "\n\n[本章因校验失败保存为草稿]")
                logger.info("第 %d 章 草稿已保存: %s", chapter_num, draft_path)
            return WriteResult(
                chapter_num=chapter_num, success=False, final_content=content,
                word_count=final_word_count, gate_level="BLOCKING",
                attempts=attempt, audit_report=audit_report,
                saved_path=draft_path if content.strip() else None,
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

        # ── 强制术语缺失 → 注入补全指令 ──
        missing_terms = []
        for issue in validation.issues:
            if issue.category == "术语" and issue.level in ("BLOCK", "WARN"):
                # 从 message 中提取术语名
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
                   但如果已有文件含草稿标记，强制重写。
        """
        results: list[WriteResult] = []
        for num in range(start, end + 1):
            if resume and self._chapter_exists(num):
                # ★ 检测草稿标记：含草稿标记的文件需要重写
                existing_content = self._load_existing_chapter(num) or ""
                if "[本章因校验失败保存为草稿]" in existing_content:
                    logger.warning("第 %d 章 已存在但含草稿标记，强制重写", num)
                else:
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

    def _sanitize_content(self, content: str) -> str:
        """清理正文中的元信息、润色说明、字数统计等杂质。"""
        # 1. 删除单行元信息：当前字数、进度统计等
        content = re.sub(r'[（(]当前字数[：:].*?[）)]\n?', '', content)
        content = re.sub(r'[（(]总进度[：:].*?[）)]\n?', '', content)
        content = re.sub(r'[（(]字数[：:].*?[）)]\n?', '', content)
        # 2. 删除 =====...===== 包裹的区块（润色说明、自检表等）
        content = re.sub(r'=+.*?=+\n?[\s\S]*?=+.*?=+\n?', '', content)
        # 3. 删除常见元信息引导语
        content = re.sub(r'请确认是否继续生成.*\n?', '', content)
        content = re.sub(r'【润色说明】.*\n?', '', content)
        content = re.sub(r'【字数统计】.*\n?', '', content)
        content = re.sub(r'【自检表】.*\n?', '', content)
        # 4. 删除 markdown 代码块标记
        content = re.sub(r'```[\s\S]*?```\n?', '', content)
        # ★ 5. 删除 Agent 自检/思考过程残留（DialogueTuner/HookEngineer 等）
        content = re.sub(r'在我的优化版本中：.*\n?', '', content)
        content = re.sub(r'让我重新调整.*\n?', '', content)
        content = re.sub(r'【.*?自检.*?】.*\n?', '', content)
        content = re.sub(r'【优化说明】.*\n?', '', content)
        content = re.sub(r'【思考过程】.*\n?', '', content)
        content = re.sub(r'（优化版本）.*\n?', '', content)
        content = re.sub(r'以下是优化后的.*\n?', '', content)
        # 6. 自动替换过量"突然"（保留前3个，其余替换）
        content = self._limit_sudden(content, max_count=3)
        # 7. 英文缩写替换为中文，避免网文 immersion break
        content = self._replace_english_terms(content)
        # 8. 自动拆分超长段落（>50个中文字符）
        content = self._split_long_paragraphs(content, max_cn_chars=50)
        # ★ 9. 清洗精确数字铺陈（保留剧情必需的楼层/时间/编号）
        content = re.sub(r'(?<![第\d])(?<![\d\-])\d+\.?\d*\s*毫米', '几分厚', content)
        content = re.sub(r'\d+\s*赫兹', '某种频率', content)
        content = re.sub(r'\d+\s*摄氏度', '异常的温', content)
        content = re.sub(r'\d+\s*%\s*湿度', '湿闷的空气', content)
        content = re.sub(r'pH值\s*低于\s*[\d\.]+', '强酸性', content)
        # ★ 10. 清洗概括性时间
        content = re.sub(r'过了一会儿|不久之后|几天后|数秒后|片刻之后|转眼之间|一段时间后', '', content)
        # ★ 11. 清洗情绪标签化（标记为需人工检查）
        emotion_labels = ["恐惧", "绝望", "愤怒", "悲伤", "快乐", "幸福", "焦虑", "紧张", "害怕"]
        for label in emotion_labels:
            content = re.sub(rf'感到{label}|一种{label}感|充斥着{label}', f'[[{label}——改为生理反应]]', content)
        return content

    # 世界观核心术语白名单：这些英文词是本书设定的一部分，禁止替换
    _ENGLISH_WHITELIST = {"KPI", "NULL", "HR", "Hz", "PPT"}

    @classmethod
    def _replace_english_terms(cls, text: str) -> str:
        """将常见英文缩写替换为中文，避免破坏网文沉浸感。"""
        replacements = {
            r'\blogo\b': '标识',
            r'\bERROR\b': '报错',
            r'\bDNA\b': '基因',
            r'\bAI\b': '人工智能',
            r'\bLED\b': '发光二极管',
            r'\bUSB\b': '通用接口',
            r'\bWAV\b': '音频',
            r'\bHR[-_]?(\d+)\b': r'人事\1号',
        }
        for pattern, repl in replacements.items():
            text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
        return text

    @staticmethod
    def _limit_sudden(text: str, max_count: int = 3) -> str:
        """保留前 max_count 个'突然'，其余替换为替代词。"""
        replacements = ["猛地", "骤然", "冷不防地", "毫无征兆地", "刹那间", "陡然"]
        count = 0
        result = []
        idx = 0
        while idx < len(text):
            pos = text.find("突然", idx)
            if pos == -1:
                result.append(text[idx:])
                break
            result.append(text[idx:pos])
            count += 1
            if count > max_count:
                # 选择替代词，尽量均匀分布
                rep = replacements[(count - max_count - 1) % len(replacements)]
                result.append(rep)
            else:
                result.append("突然")
            idx = pos + 2
        return "".join(result)

    @staticmethod
    def _split_long_paragraphs(text: str, max_cn_chars: int = 30) -> str:
        """将超长段落按句末标点拆分为短段落。"""
        lines = text.split('\n')
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                new_lines.append(line)
                continue
            cn_chars = len(re.findall(r'[\u4e00-\u9fff]', stripped))
            if cn_chars <= max_cn_chars:
                new_lines.append(line)
                continue
            # 按句末标点拆分（。！？；），并合并标点到前一句
            raw_parts = re.split(r'([。！？；])', stripped)
            sentences = []
            i = 0
            while i < len(raw_parts):
                s = raw_parts[i]
                if i + 1 < len(raw_parts) and raw_parts[i+1] in '。！？；':
                    s += raw_parts[i+1]
                    i += 2
                else:
                    i += 1
                if not s:
                    continue
                # 修复：如果当前片段以"开头且前一句以标点结尾，
                # 说明这个"是前一句对话的闭合引号，合并到前一句
                if sentences and s.startswith('"') and sentences[-1] and sentences[-1][-1] in '。！？；':
                    sentences[-1] += s
                else:
                    sentences.append(s)
            buf = ""
            buf_cn = 0
            for sent in sentences:
                sent_cn = len(re.findall(r'[\u4e00-\u9fff]', sent))
                # 如果单句本身超长，先在逗号/顿号处强制子分割
                if sent_cn > max_cn_chars:
                    sub_parts = re.split(r'([，、])', sent)
                    sub_sents = []
                    j = 0
                    while j < len(sub_parts):
                        ss = sub_parts[j]
                        if j + 1 < len(sub_parts) and sub_parts[j+1] in '，、':
                            ss += sub_parts[j+1]
                            j += 2
                        else:
                            j += 1
                        if ss:
                            sub_sents.append(ss)
                    for ss in sub_sents:
                        ss_cn = len(re.findall(r'[\u4e00-\u9fff]', ss))
                        if buf_cn + ss_cn > max_cn_chars and buf:
                            new_lines.append(buf)
                            buf = ss
                            buf_cn = ss_cn
                        else:
                            buf += ss
                            buf_cn += ss_cn
                else:
                    if buf_cn + sent_cn > max_cn_chars and buf:
                        new_lines.append(buf)
                        buf = sent
                        buf_cn = sent_cn
                    else:
                        buf += sent
                        buf_cn += sent_cn
            if buf:
                new_lines.append(buf)
        return "\n".join(new_lines)

    def save_chapter(self, chapter_num: int, content: str) -> Path:
        """保存章节正文到 output_dir。

        文件名格式: 第{num:03d}章_标题_正文.txt
        标题优先从 world_state.db 读取，其次从内容中提取。
        """
        content = self._sanitize_content(content)
        # 优先从数据库读取标题
        title = self._get_chapter_title(chapter_num) or self._extract_title(chapter_num, content)
        # 清理文件名非法字符
        safe_title = re.sub(r'[\\/:*?"<>|]', "", title)[:20]
        filename = f"第{chapter_num:03d}章_{safe_title}.txt"
        path = self.output_dir / filename
        path.write_text(content, encoding="utf-8")
        return path

    def _get_chapter_title(self, chapter_num: int) -> str:
        """从 state 数据库读取章节标题。"""
        try:
            return self.state.get_chapter_title(chapter_num)
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
        """保存章节标题到 state 数据库。"""
        try:
            self.state.set_chapter_title(chapter_num, title)
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

    def _log_full_prompt(self, agent_type: str, chapter_num: int, system: str, user: str) -> None:
        """在每次 LLM 调用前，将完整的 system prompt 和 user prompt 写入日志文件。"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = Path("logs/prompts")
        log_dir.mkdir(parents=True, exist_ok=True)
        filename = log_dir / f"ch{chapter_num:03d}_{agent_type}_{ts}.txt"
        content = (
            f"=== Agent: {agent_type} | Chapter: {chapter_num} | Time: {ts} ===\n\n"
            f"----- SYSTEM PROMPT -----\n{system}\n\n"
            f"----- USER PROMPT -----\n{user}\n"
        )
        try:
            filename.write_text(content, encoding="utf-8")
            logger.debug("Prompt 已记录: %s", filename)
        except Exception as exc:
            logger.warning("记录 prompt 失败: %s", exc)

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
            "terms": self.state.get_term_dict(),
            "prev_summary": self._get_prev_summary(chapter_num),
        }
        # 注入外层 CrewAI 反馈
        if getattr(self, "_pending_retcons", None):
            ctx["outer_crew_retcons"] = self._pending_retcons
        if getattr(self, "_emotion_targets", None):
            ctx["emotion_targets"] = self._emotion_targets
        if getattr(self, "_outer_crew_priorities", None):
            ctx["outer_crew_priorities"] = self._outer_crew_priorities
        return ctx

    def _get_prev_summary(self, chapter_num: int) -> str:
        """获取前一章的摘要。"""
        if chapter_num <= 1:
            return ""
        try:
            history = self.state.list_chapters()
            for h in history:
                if h.get("chapter") == chapter_num - 1:
                    return h.get("summary", "") or ""
        except Exception:
            pass
        return ""

    def _get_chapter_outline(self, chapter_num: int) -> dict[str, str]:
        """从 state 数据库读取本章详细规划。"""
        try:
            return self.state.get_chapter_outline(chapter_num)
        except Exception as exc:
            logger.warning("读取 outline 失败: %s", exc)
        return {}

    def _get_character_states(self) -> list[dict]:
        """从 state 数据库读取活跃人物状态。"""
        try:
            return self.state.get_characters_full()
        except Exception as exc:
            logger.warning("读取人物状态失败: %s", exc)
        return []

    def _get_consistency_rules(self) -> list[str]:
        """从 state 数据库读取写作规则。"""
        try:
            return self.state.get_hard_rules()
        except Exception as exc:
            logger.warning("读取规则失败: %s", exc)
        return []

    def _chapter_exists(self, chapter_num: int) -> bool:
        """检查 output_dir 是否已有该章节文件。"""
        pattern = f"第{chapter_num:03d}章_*_正文.txt"
        return any(self.output_dir.glob(pattern))

    def _load_existing_chapter(self, chapter_num: int) -> str:
        """加载 output_dir 中已存在的章节正文。"""
        pattern = f"第{chapter_num:03d}章_*_正文.txt"
        files = list(self.output_dir.glob(pattern))
        if not files:
            return ""
        try:
            return files[0].read_text(encoding="utf-8")
        except Exception:
            return ""

    def _propagate_character_states(self, chapter_num: int) -> None:
        """将上一章的角色状态复制到本章，保持跨章连续性。

        策略：逐章传播，若上一章无记录则回退到 chapter=0 初始态。
        """
        if chapter_num <= 0:
            return
        try:
            # 优先查找上一章的记录
            prev_chars = self.state.get_characters_by_chapter(chapter_num - 1)
            if not prev_chars and chapter_num > 1:
                # 若上一章无记录，继续回退查找最近的有记录章节
                for back in range(chapter_num - 2, -1, -1):
                    prev_chars = self.state.get_characters_by_chapter(back)
                    if prev_chars:
                        break
            if not prev_chars:
                logger.warning("第 %d 章 无可用角色状态可传播", chapter_num)
                return
            for char in prev_chars:
                self.state.update_character_state(
                    chapter=chapter_num,
                    character=char["name"],
                    location=char.get("location", ""),
                    emotional_state=char.get("emotional_state", ""),
                    known_secrets=char.get("known_secrets", ""),
                    unknown_secrets=char.get("unknown_secrets", ""),
                    abilities_active=char.get("abilities", ""),
                    dialog_fingerprint=char.get("dialog_fingerprint", ""),
                    body_language=char.get("body_language", ""),
                    physical_description=char.get("description", ""),
                )
            logger.info("第 %d 章 角色状态已传播: %d 人", chapter_num, len(prev_chars))
        except Exception as exc:
            logger.warning("传播角色状态到第 %d 章失败: %s", chapter_num, exc)

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
        # ★ 传播角色状态：将上一章的角色状态复制到本章，保持连续性
        self._propagate_character_states(chapter_num)
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
        # ★ 降本：禁用LLM情感标注，使用加权词袋回退（比单字计数更准确）
        nue_indicators = {
            "痛": 0.5, "血": 0.3, "死": 0.8, "杀": 0.7, "折": 0.4,
            "窒息": 0.9, "腐蚀": 0.7, "剥离": 0.6, "消退": 0.4,
            "绝望": 0.8, "窒息感": 0.9, "钝痛": 0.6, "撕裂": 0.7,
        }
        tian_indicators = {
            "笑": 0.5, "暖": 0.6, "光": 0.2, "甜": 0.8, "温柔": 0.5,
            "依赖": 0.4, "信任": 0.5, "安慰": 0.4,
        }
        shuang_indicators = {
            "赢": 0.8, "碾压": 0.9, "破": 0.5, "解": 0.3, "反击": 0.7,
            "挣脱": 0.6, "识破": 0.5,
        }
        nue = sum(content.count(w) * weight for w, weight in nue_indicators.items())
        tian = sum(content.count(w) * weight for w, weight in tian_indicators.items())
        shuang = sum(content.count(w) * weight for w, weight in shuang_indicators.items())
        total = nue + tian + shuang + 0.1
        emotion = {
            "nue": nue / total,
            "tian": tian / total,
            "shuang": shuang / total,
            "coord_x": 0.0,
            "coord_y": 0.0,
            "desc": f"IWR={metrics['iwr_score']}, Platform={platform['platform_grade']} (加权词袋回退)",
        }
        self.state.update_emotion_history(
            chapter_num=chapter_num,
            mode="auto",
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
    def _get_agent_llm_params(self, agent_type: str, default_temp: float, default_max_tokens: int) -> tuple[float, int]:
        """从 book.yaml agent_query 读取 agent 的 temperature/max_tokens，未定义则使用默认值。"""
        query = self.cfg.agent_query.get(agent_type, {})
        return query.get("temperature", default_temp), query.get("max_tokens", default_max_tokens)

    def _load_worldview_rules(self) -> str:
        """从 state 数据库读取术语字典和世界观铁律，注入 system prompt。"""
        rules_parts = []
        try:
            # 读取术语字典
            terms = self.state.get_term_dict()
            if not terms:
                # fallback: 使用 chapter_validator 中的硬编码术语
                terms = [
                    {
                        "term": k,
                        "category": v.get("category", ""),
                        "first_chapter": v.get("first_chapter", 1),
                        "description": v.get("description", ""),
                    }
                    for k, v in TERM_MANDATORY.items()
                ]
            if terms:
                rules_parts.append("【世界观铁律——出现任何一条术语错误，整章废弃重写】")
                for t in terms:
                    rules_parts.append(f"- {t['term']}（{t.get('category', '')}，第{t.get('first_chapter', '?')}章首次出现）：{t.get('description', '')}")

            # 读取 chapter_specs 中的 title 和 core_event
            specs = self.state.get_chapter_specs(spec_keys=["title", "core_event"])
            if specs:
                rules_parts.append("\n【章节任务——必须严格呈现以下核心事件】")
                for s in specs:
                    if s.get("spec_key") == "core_event" and s.get("spec_value"):
                        rules_parts.append(f"- 第{s['chapter']}章：{s['spec_value'][:80]}")
        except Exception as exc:
            logger.warning("读取世界观铁律失败: %s", exc)
        return "\n".join(rules_parts)

    def _build_system_prompt(self, agent_type: str) -> str:
        """根据 Agent 类型构造 system prompt，所有书籍配置从数据库动态加载。"""
        query = self.cfg.agent_query.get(agent_type, {})
        role = query.get("role", f"小说{agent_type}")

        cfg = query

        # 世界观铁律注入 system prompt 最前面
        worldview = self._load_worldview_rules()

        parts = []
        if worldview:
            parts.append(worldview)

        # author_persona 注入 system prompt
        persona = self.cfg.author_persona
        if persona:
            parts.append("\n【作者人格——所有正文必须体现以下风格特征】")
            voice = persona.get("voice", "")
            if voice:
                parts.append(f"叙事声音：{voice}")
            wound = persona.get("core_wound", "")
            if wound:
                parts.append(f"核心创伤：{wound}")
            rhythm = persona.get("sentence_rhythm", [])
            if rhythm:
                parts.append("句式节奏：")
                for r in rhythm:
                    parts.append(f"  - {r}")
            sensory = persona.get("sensory_priority", [])
            if sensory:
                parts.append(f"感官优先级：{' > '.join(sensory)}")
            moves = persona.get("signature_moves", [])
            if moves:
                parts.append("标志性动作（必须出现）：")
                for m in moves:
                    parts.append(f"  - {m}")
            forbidden = persona.get("forbidden_rhetoric", [])
            if forbidden:
                parts.append("禁止修辞：")
                for f in forbidden:
                    parts.append(f"  - {f}")

        # 通用网文禁区（非书籍特定）
        parts.append("\n【网文禁区——出现即FAIL】")
        parts.append("- 禁止'不知道为什么/仿佛/似乎/好像/他意识到'")
        parts.append("- 禁止'一些/实际上/在一定程度上/本质上/换句话说'")
        parts.append("- 禁止被动语态：'被拖走/被吞噬'→改成主动描述")
        parts.append("- 禁止概括性时间：'过了一会儿/不久之后'")
        parts.append("- 禁止情绪标签：'恐惧/绝望'→改成生理反应")

        # 人物对话指纹——从数据库动态加载
        chars = self._get_character_states()
        if chars:
            parts.append("\n【人物对话指纹——逐句核对】")
            for c in chars:
                name = c.get("name", "")
                fp = c.get("dialog_fingerprint", "")
                if name and fp:
                    parts.append(f"- {name}：{fp}")

        parts.append(f"你是 {role}。")
        if cfg.get("goal"):
            parts.append(f"你的目标是：{cfg['goal']}")
        if cfg.get("backstory"):
            parts.append(cfg["backstory"])
        return "\n\n".join(parts)

    def _build_task_user_prompt(self, agent_type: str, chapter_num: int, context: str = "") -> str:
        """构造 user prompt。"""
        query = self.cfg.agent_query.get(agent_type, {})
        role = query.get("role", f"小说{agent_type}")

        desc = query.get("description", "")
        expected = query.get("expected_output", "")

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
            # ★ 字数铁律移至末尾，弱化措辞，降低对LLM的压迫感
            word_count_section = (
                f"\n【字数参考——弹性目标】\n"
                f"本章目标中文字数：{target} 字（舒适范围 {min_w}~{max_w}）。\n"
                f"字数不是第一优先级。在保障情节完整、去AI味达标的前提下，尽量接近目标字数即可。\n"
                f" slight under 比 slight over 更好——填充内容是AI味的主要来源。\n"
                f"若写完核心情节后字数不足，优先补充：对话交锋、感官细节、废动作。\n"
                f"禁止为凑字数而添加：精确参数、重复描写、无意义的心理分析、概括性场景概述。\n\n"
                f"【正文格式铁律】\n"
                f"- 禁止出现【节拍X】标签、markdown标记、自检表、字数统计\n"
                f"- 每章开头必须写标题，格式：第{chapter_num}章：标题（标题由任务卡指定，不可自拟，严禁写其他章节的标题）\n"
                f"- 标题后空一行，再开始正文\n\n"
                f"【对话铁律】\n"
                f"1. 本章对话占比控制在 25%-45%。对话是推动情节的核心手段，不是点缀。\n"
                f"2. 每章至少包含 3-5 组人物对话场景，每组对话不少于 3 轮交锋。\n"
                f"3. 对话中禁止用'道/说'以外的同义替换词（不可：低语/呢喃/沉声道/冷声道/缓缓道）。\n"
                f"4. 对话簇长度≤3段，禁止出现'对话块'超过3段的连续对话。\n"
                f"5. 对话口语化：允许打断、重复、半截话、口癖、脏话。禁止书面语台词和完美逻辑链。\n\n"
            )
            parts.append(word_count_section)

        return "\n".join(parts)

    def _get_chapter_title_from_outline_md(self, chapter_num: int) -> str:
        """从 outline.md 解析指定章节的标题。"""
        outline_path = self.cfg.base_path / "outline.md"
        if not outline_path.exists():
            return ""
        try:
            text = outline_path.read_text(encoding="utf-8")
            import re
            # 匹配 ### 第N章：标题名 或 ## 第N章：标题名
            pattern = rf'[#]{{2,4}}\s*第\s*{chapter_num}\s*章[：:]\s*(.+)'
            m = re.search(pattern, text)
            if m:
                return m.group(1).strip()
        except Exception:
            pass
        return ""

    def _call_director(self, chapter_num: int, context: dict[str, Any]) -> str:
        """Director Agent：生成本章任务卡（含标题），严格基于大纲。"""
        system = self._build_system_prompt("director")

        # 从 outline.md 读取标题（最高优先级）
        md_title = self._get_chapter_title_from_outline_md(chapter_num)

        # 构造大纲驱动的上下文
        outline = context.get("outline", {})
        outline_text = ""
        if outline:
            outline_text = (
                f"\n【本章大纲——必须严格遵循，禁止擅自修改核心事件与人物名称】\n"
                f"卷名/篇名：{outline.get('arc', '')}\n"
                f"核心事件：{outline.get('core_event', '')}\n"
                f"打脸对象：{outline.get('face_slap_target', '')}\n"
                f"打脸方式：{outline.get('face_slap_method', '')}\n"
                f"护妻时刻/人性高光：{outline.get('husband_moment', '')}\n"
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
            chars_text = "\n【人物状态——逐句核对对话指纹】\n" + "\n".join(
                f"- {c.get('name','')}（{c.get('location','未知')}）：{c.get('emotional_state','')}。\n"
                f"  对话指纹：{c.get('dialog_fingerprint','')}\n"
                f"  肢体语言：{c.get('body_language','')}"
                for c in chars[:5]
            )

        # 硬规则
        rules = context.get("rules", [])
        rules_text = ""
        if rules:
            rules_text = "\n【必须遵守的写作铁律】\n" + "\n".join(f"{i+1}. {r}" for i, r in enumerate(rules))

        # 术语字典
        terms = context.get("terms", [])
        terms_text = ""
        if terms:
            terms_text = "\n【世界观术语——出现即FAIL】\n" + "\n".join(
                f"- {t['term']}（{t.get('category','')}，第{t.get('first_chapter','?')}章首次出现）：{t.get('description','')}"
                for t in terms
            )

        # 前情摘要
        prev_summary = context.get("prev_summary", "")
        prev_text = f"\n【前情摘要】\n{prev_summary}" if prev_summary else ""

        # 标题约束文本
        title_constraint = ""
        if md_title:
            title_constraint = (
                f"\n【章节标题——绝对不可更改】\n"
                f"本章标题必须为：第{chapter_num}章：{md_title}\n"
                f"严禁使用其他标题，严禁缩写或改写。"
            )

        user = self._build_task_user_prompt(
            "director", chapter_num,
            context=f"活跃债务: {context.get('debts', [])}\n"
                     f"活跃伏笔: {context.get('foreshadowing', [])}"
                     f"{outline_text}{chars_text}{rules_text}{terms_text}{prev_text}{title_constraint}"
        )
        user += (
            f"\n\n【输出格式要求】\n"
            f"任务卡第一行必须是章节标题，格式：【标题】第{chapter_num}章：标题名\n"
        )
        if md_title:
            user += (
                f"【绝对铁律】标题必须严格使用『第{chapter_num}章：{md_title}』，一字不可改。\n"
            )
        else:
            user += (
                f"标题名要求：4-8个字，紧扣本章核心事件，有网文感，不要文艺腔。\n"
            )
        user += (
            f"【绝对铁律】当前是第{chapter_num}章，任务卡中的标题必须写'第{chapter_num}章'，严禁写其他章节的编号。\n"
            f"标题后空一行，再写正文任务卡内容。\n"
            f"任务卡必须严格基于【本章大纲】设计，不能偏离大纲中的核心事件、打脸方式和章末钩子。"
        )
        temp, max_tok = self._get_agent_llm_params("director", 0.1, 4000)
        self._log_full_prompt("director", chapter_num, system, user)
        return self.llm.call_for_agent("director", system, user, temperature=temp, max_tokens=max_tok)

    def _call_beat_planner(self, chapter_num: int, director_prompt: str, context: dict[str, Any]) -> str:
        """BeatPlanner Agent：将 Director 任务卡转换为弹性节拍分配表。"""
        # ★ 引入节拍变异，打破固定六段式铁律
        BEAT_VARIATIONS = {
            0: ("起-承1-承2-转-合1-合2", "标准六段式，适合常规推进章"),
            1: ("起-转-承-转-合1-合2", "快节奏，核心冲突提前爆发，适合转折章"),
            2: ("起-承-承-承-转-合", "慢燃铺垫，适合信息量大的解密章"),
            3: ("起-对话交锋1-对话交锋2-转-合1-合2", "对话主导，适合信息释放和立场对峙章"),
            4: ("起-承-转-转-转-合", "多转折连击，适合高潮章"),
            5: ("悬念-起-承-转-合-钩子", "双重悬念框架，适合钩子章"),
        }
        variation_idx = (chapter_num - 1) % len(BEAT_VARIATIONS)
        beat_structure, beat_desc = BEAT_VARIATIONS[variation_idx]

        system = (
            "你是 BeatPlanner（节拍分配师）。\n"
            "你的任务是将导演任务卡拆解为节拍分配表，精确到每段的字数范围和核心内容。\n"
            "你只做字数分配和内容规划，不输出正文。\n"
            "\n【核心职责 - 绝对不可违背】\n"
            "1. 节拍表中必须包含至少 3-5 个对话场景节点。\n"
            "2. 对话不是点缀，是推动情节的核心手段——没有对话的节拍表是失败的。\n"
            "3. 每个对话节点必须标注：参与人物、核心冲突、预估字数。\n"
            "4. 禁止每章使用完全相同的节拍结构，必须根据本章类型灵活调整。"
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
            f"【任务】为第{chapter_num}章生成节拍分配表。\n"
            f"\n【本章节拍结构——必须遵循，禁止套固定六段式模板】\n"
            f"类型：{beat_desc}\n"
            f"结构：{beat_structure}\n"
            f"请按此结构分配字数和规划内容，不要机械套用起-承1-承2-转-合1-合2。\n\n"
            f"【字数要求】总字数 {min_w}~{max_w} 字（目标 {target} 字）\n"
            f"- 各段字数按结构弹性分配，没有固定比例。核心冲突段可占30-40%，铺垫段可压缩。\n"
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
        temp, max_tok = self._get_agent_llm_params("beat_planner", 0.1, 3000)
        self._log_full_prompt("beat_planner", chapter_num, system, user)
        return self.llm.call_for_agent("beat_planner", system, user, temperature=temp, max_tokens=max_tok)
    def _build_scene_writer_dna(self) -> str:
        """构建 SceneWriter 的 system prompt（风格DNA），基于 book.yaml author_persona 动态注入。"""
        persona = self.cfg.author_persona
        parts = []

        parts.append("【作者人格——你必须以这个人格写作，而非通用网文风格】")

        voice = persona.get("voice", "") if persona else ""
        if voice:
            parts.append(f"你的叙事声音是：{voice}")

        wound = persona.get("core_wound", "") if persona else ""
        if wound:
            parts.append(f"你的核心创伤视角：{wound}")

        rhythm = persona.get("sentence_rhythm", []) if persona else []
        if rhythm:
            parts.append("句式节奏（必须体现）：")
            for r in rhythm:
                parts.append(f"  - {r}")

        sensory = persona.get("sensory_priority", []) if persona else []
        if sensory:
            parts.append(f"感官优先级：{' > '.join(sensory)}")

        moves = persona.get("signature_moves", []) if persona else []
        if moves:
            parts.append("标志性动作（每章至少出现2处）：")
            for m in moves:
                parts.append(f"  - {m}")

        forbidden = persona.get("forbidden_rhetoric", []) if persona else []
        if forbidden:
            parts.append("绝对禁止（出现即失败）：")
            for f in forbidden:
                parts.append(f"  - {f}")

        # 通用去AI味铁律（不绑定特定作品）
        parts.append("\n【去AI味写作铁律——违反即降档】")
        parts.append("1. 禁止精确数字铺陈环境：不写'0.5毫米/47赫兹/22摄氏度/45%湿度/pH值'等参数，改用身体体感（'扎进肉里/震得牙根发酸/闷得像裹了保鲜膜'）。数字只保留剧情必需的（倒计时、楼层编号、工牌编号）")
        parts.append("2. 段落切碎：单段15-50字，紧张场景可一句一段。严禁AI式长段落堆砌")
        parts.append("3. 感官聚焦：一段只写一个主导感官，禁止一段内视觉+听觉+触觉+嗅觉五感全齐式轰炸")
        parts.append("4. 废动作：每章至少1个与主线无关的小动作（摸鼻子、抖腿、走神、废话、拿错东西），暴露角色是活人")
        parts.append("5. 对话口语化：允许打断、重复、半截话、口癖、脏话。禁止书面语台词和完美逻辑链。人说话会磕巴、会跑题")
        parts.append("6. 主角可以犯错：允许慢半拍、错判、走神三秒、做出看似愚蠢的决定。禁止上帝视角般的精确判断和即时正确反应")
        parts.append("7. 比喻≤3处，禁止公共库存比喻（像刀/像蛇/像铁板/像提线木偶/像蜡像/像离弦的箭）")
        parts.append("8. 全文禁止'不是X，是Y'句式")
        parts.append("9. 开头多样性：禁止连续两章用同一类型开头（触感/对话/动作/环境/回忆/悬念轮换）。禁止重复前几章用过的具体意象")
        parts.append("10. 结尾多样性：禁止连续两章用'主角静止+物品特写+悬念'结构。可轮换：动作悬念/对话未竟/认知崩塌/环境突变")
        parts.append("11. 他密度≤6%，情绪必须物化（不写'他感到恐惧'，写'他的手指在抖，指甲掐进了掌心'）")
        parts.append("12. 禁止情绪标签：恐惧/绝望/愤怒/悲伤/焦虑→全部改为生理反应或行为表现")
        parts.append("13. 禁止概括性时间：'过了一会儿''不久之后''几天后'→直接切入下一动作或场景")

        parts.append("\n【格式】")
        parts.append("- 第一行：第N章：标题名")
        parts.append("- 标题后空一行开始正文")
        parts.append("- 段落之间空一行（网文标准排版，适合移动端阅读）")
        parts.append("- 不要出现【节拍X】标签、markdown、自检表、思考过程")

        parts.append("\n【标点与节奏铁律】")
        parts.append("- 每500字至少2个问号（？）或省略号（……），用于悬念和留白。禁止全篇只有句号+逗号的说明书式单调")
        parts.append("- 每章至少3处2-10字的超短段落，制造节奏停顿和情绪落差。例：'酸。' / '她没动。' / '然后呢？'")
        parts.append("- 关键对话单独成段，不要淹没在叙述中。对话段可用2-15字制造冲击感")

        return "\n".join(parts)

    def _call_scene_writer_half(self, chapter_num: int, beat_plan: str, corrections: dict[str, str], half: str, word_target: int, compiled_context: str = "") -> str:
        """SceneWriter 半章写作（内部方法，供并行调用）。"""
        dna = self._build_scene_writer_dna()
        target = self.cfg.words_per_chapter
        tol = self.cfg.words_tolerance
        min_w = target - tol

        # 构建当前章节必须包含的强制术语列表
        required_terms = [
            term for term, cfg in TERM_MANDATORY.items()
            if chapter_num >= cfg.get("first_chapter", 1)
        ]
        terms_section = ""
        if required_terms:
            term_lines = [f"{', '.join(required_terms)}"]
            # 注入正反示例
            for term in required_terms:
                cfg = TERM_MANDATORY.get(term, {})
                good = cfg.get("good_example", "")
                bad = cfg.get("bad_example", "")
                if good or bad:
                    term_lines.append(f"\n■ {term}：")
                    if good:
                        term_lines.append(f"  正确写法：{good}")
                    if bad:
                        term_lines.append(f"  错误写法（禁止）：{bad}")
            terms_section = (
                f"\n【强制术语——必须在正文中自然出现，禁止意译或替换】\n"
                f"本章必须包含以下世界观核心术语（共{len(required_terms)}个）：\n"
                f"\n".join(term_lines) + "\n"
                f"术语必须自然嵌入叙述或对话中，禁止生硬插入或整段解释。禁止百科式说明。\n"
            )

        # 开头多样性：动态注入本章推荐的开头类型
        OPENING_ROTATION = {
            0: "触感/身体感受开场（主角身体的某个感受直接切入，但禁止用工牌/指腹意象）",
            1: "对话/声音开场（一句对话或一个声音直接切入）",
            2: "动作/突发事件开场（一个动作或意外直接切入）",
            3: "环境/氛围开场（一个环境细节或氛围变化直接切入）",
            4: "内心独白/回忆开场（主角的一个念头或闪回直接切入）",
            5: "悬念/疑问开场（一个未解之谜或反常现象直接切入）",
        }
        opening_idx = (chapter_num - 1) % 6
        opening_type = OPENING_ROTATION[opening_idx]
        prev_idx = (chapter_num - 2) % 6 if chapter_num > 1 else -1
        prev_type = OPENING_ROTATION.get(prev_idx, "")
        opening_section = (
            f"\n【开场类型要求——禁止与上一章重复】\n"
            f"本章必须使用以下方式开场：{opening_type}\n"
        )
        if prev_type:
            opening_section += f"上一章（第{chapter_num-1}章）已使用：{prev_type}，本章严禁重复。\n"
        opening_section += "前100字必须有动作+感官细节，禁止概述。\n"

        if half == "first":
            user = (
                f"【任务】创作第{chapter_num}章的前半部分（起-承1-承2）\n\n"
                f"【字数铁律——绝对不可违背】\n"
                f"1. 这部分必须写满 {word_target} 字。绝对不能少于 {word_target - 200} 字。\n"
                f"2. 全章总目标 {target}±{tol} 字，前半部分占一半，必须达到 {word_target} 字。\n"
                f"3. 句长铁律：单句不超过40字，超过必须在逗号或顿号处断句。这是硬性排版要求。\n"
                f"4. 写完后立即估算中文字数。如果不足 {word_target} 字，立即补充：\n"
                f"   - 更详细的场景描写和环境氛围渲染\n"
                f"   - 人物对话和心理活动\n"
                f"   - 动作细节和感官体验\n"
                f"   - 不要草草结束，不要留空白\n"
                f"{terms_section}"
                f"{opening_section}\n"
                f"【分工说明】\n"
                f"你只负责前三段（起、承1、承2）。写到【承2】结束即可。\n"
                f"结尾处停在情节即将升级的瞬间，为后半部分（转-合1-合2）留下张力。\n"
                f"绝对不要写后半部分的情节，也不要写本章结局。\n\n"
                f"{compiled_context}\n"
                f"【节拍分配表】\n{beat_plan}\n"
            )
        elif half == "second":
            user = (
                f"【任务】创作第{chapter_num}章的后半部分（转-合1-合2）\n\n"
                f"【字数铁律——绝对不可违背】\n"
                f"1. 这部分必须写满 {word_target} 字。绝对不能少于 {word_target - 200} 字。\n"
                f"2. 全章总目标 {target}±{tol} 字，后半部分占一半，必须达到 {word_target} 字。\n"
                f"3. 句长铁律：单句不超过40字，超过必须在逗号或顿号处断句。这是硬性排版要求。\n"
                f"4. 后半部分和前半部分同等重要，同样需要大量细节描写。\n"
                f"5. 写完后立即估算中文字数。如果不足 {word_target} 字，立即补充：\n"
                f"   - 更详细的场景描写和环境氛围渲染\n"
                f"   - 人物对话和心理活动\n"
                f"   - 动作细节和感官体验\n"
                f"   - 不要草草结束，不要留空白\n"
                f"{terms_section}"
                f"{opening_section}\n"
                f"【分工说明】\n"
                f"你只负责后三段（转、合1、合2）。\n"
                f"前半部分（起-承1-承2）已经写好了，情节发展到【承2】结束时的紧张状态。\n"
                f"请从这里继续写：核心冲突爆发、情绪对峙、章末钩子。\n"
                f"不要重复前半部分已写的情节。\n\n"
                f"{compiled_context}\n"
                f"【节拍分配表】\n{beat_plan}\n"
            )
        elif half == "full":
            user = (
                f"【任务】一次性创作第{chapter_num}章的完整正文\n\n"
                f"【本章核心任务——必须优先于字数和格式】\n"
                f"{compiled_context}\n\n"
                f"【字数铁律——绝对不可违背】\n"
                f"1. 本章必须写满 {word_target} 字。绝对不能少于 {word_target - 400} 字，绝对不能超过 {word_target + 400} 字。\n"
                f"2. 目标字数 {target}±{tol} 字，写完后立即估算中文字数，严格控制在范围内。\n"
                f"3. 句长铁律：单句不超过40字，超过必须在逗号或顿号处断句。这是硬性排版要求。\n"
                f"4. 写完后立即估算中文字数。如果不足 {word_target} 字，立即补充细节描写和对话。\n"
                f"   如果超过 {word_target + 400} 字，立即精简冗余描写，保留核心情节。\n"
                f"{terms_section}"
                f"{opening_section}\n"
                f"【结构要求】\n"
                f"完整包含六段式结构：起-承1-承2-转-合1-合2。\n"
                f"起：直接切入场景，前100字必须有动作+感官细节。\n"
                f"承1-承2：情节推进，伏笔铺设，细节描写。\n"
                f"转：核心冲突爆发，情绪升级。\n"
                f"合1-合2：对峙/解决，章末钩子（不要回答悬念）。\n\n"
                f"【节拍分配表】\n{beat_plan}\n"
            )

        if corrections.get("scene_writer"):
            user += f"\n【修正指令】\n{corrections['scene_writer']}\n"

        # ★ SceneWriter 需要更多输出额度（3200中文字≈6000 tokens），其他Agent保持8000
        temp, max_tok = self._get_agent_llm_params("scene_writer", 0.75, 12000)
        self._log_full_prompt(f"scene_writer_{half}", chapter_num, dna, user)
        return self.llm.call_for_agent("scene_writer", dna, user, temperature=temp, max_tokens=max_tok)

    def _call_merger(self, chapter_num: int, draft_first: str, draft_second: str) -> str:
        """Merger：检查接缝，消除断裂和重复。"""
        system = (
            "你是 Merger（章节合并师）。\n"
            "你接收两篇小说片段（前半章 + 后半章），任务是检查接缝并消除问题。\n"
            "\n检查清单：\n"
            "1. 接缝处是否有逻辑断裂（前半结尾和后半开头不连贯）\n"
            "2. 是否有重复内容（后半开头重复了前半结尾的情节）\n"
            "3. 人称/视角是否一致\n"
            "4. 情绪节奏是否自然过渡\n"
            "\n处理规则：\n"
            "- 只修改接缝处±200字，保留其他内容一字不动\n"
            "- 删除重复内容，保留更精彩的版本\n"
            "- 如有断裂，用1-2句过渡句衔接\n"
            "- 绝对不要添加新的情节或改变故事走向\n"
            "- 绝对不要输出任何说明、标记、字数统计\n"
        )
        # 只传入接缝附近的内容，减少token消耗
        first_tail = draft_first[-500:] if len(draft_first) > 500 else draft_first
        second_head = draft_second[:500] if len(draft_second) > 500 else draft_second
        user = (
            f"【任务】合并第{chapter_num}章的两个片段\n\n"
            f"【前半章结尾】\n{first_tail}\n\n"
            f"【后半章开头】\n{second_head}\n\n"
            f"【输出要求】\n"
            f"1. 输出修正后的完整合并正文（前半章 + 后半章，接缝已修复）\n"
            f"2. 不要任何说明、润色总结、字数统计或标记\n"
            f"3. 第一行必须是章节标题：第{chapter_num}章：标题名"
        )
        temp, max_tok = self._get_agent_llm_params("merger", 0.3, 12000)
        self._log_full_prompt("merger", chapter_num, system, user)
        return self.llm.call_for_agent("merger", system, user, temperature=temp, max_tokens=max_tok)

    def _call_scene_writer(self, chapter_num: int, beat_plan: str, corrections: dict[str, str], compiled=None) -> str:
        """SceneWriter：单次写作完整章。（降本：A/B合并为单次调用）"""
        target = self.cfg.words_per_chapter
        tol = self.cfg.words_tolerance

        # 提取 InputGovernor 编译的上下文
        compiled_context = ""
        if compiled is not None:
            compiled_context = compiled.format_writer_prompt()

        logger.info("第 %d 章 启动 SceneWriter 单次写作（目标%d字）", chapter_num, target)

        draft = self._call_scene_writer_half(
            chapter_num, beat_plan, corrections, "full", target, compiled_context
        )

        words = self._count_chinese_chars(draft)
        logger.info("第 %d 章 SceneWriter 完成: %d字", chapter_num, words)
        return draft.strip()

    def _build_persona_injection(self) -> str:
        """生成 author_persona 注入文本，供后处理 Agent 使用。"""
        persona = self.cfg.author_persona
        if not persona:
            return ""
        parts = ["\n【作者人格——修改时必须保持此风格】"]
        voice = persona.get("voice", "")
        if voice:
            parts.append(f"叙事声音：{voice}")
        forbidden = persona.get("forbidden_rhetoric", [])
        if forbidden:
            parts.append(f"绝对禁止引入：{ '、'.join(forbidden) }")
        return "\n".join(parts)

    def _call_hook_engineer(self, chapter_num: int, scene_draft: str, context: dict[str, Any], corrections: dict[str, str]) -> str:
        """HookEngineer Agent：优化开头和结尾，确保 IWR 和钩子密度。"""
        import re
        original_cn = len(re.findall(r'[\u4e00-\u9fff]', scene_draft))
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
            + self._build_persona_injection()
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
        temp, max_tok = self._get_agent_llm_params("hook_engineer", 0.1, 8000)
        self._log_full_prompt("hook_engineer", chapter_num, system, user)
        hook_result = self.llm.call_for_agent("hook_engineer", system, user, temperature=temp, max_tokens=max_tok)
        result_cn = len(re.findall(r'[\u4e00-\u9fff]', hook_result))
        if original_cn > 0 and result_cn < original_cn * 0.85:
            logger.warning("第 %d 章 HookEngineer 字数损失 %.1f%% (%d→%d)，回退原稿", chapter_num, (1 - result_cn/original_cn) * 100, original_cn, result_cn)
            return scene_draft
        return hook_result

    def _call_dialogue_tuner(self, chapter_num: int, hook_draft: str, context: dict[str, Any], corrections: dict[str, str]) -> str:
        """DialogueTuner Agent：优化对话密度和道说比，确保符合品类 DNA。"""
        # 字数保护：如果输入已超标，直接返回，不调用LLM（避免膨胀）
        import re
        input_cn = len(re.findall(r'[\u4e00-\u9fff]', hook_draft))
        target = self.cfg.words_per_chapter
        tol = self.cfg.words_tolerance
        max_w = target + tol
        if input_cn > max_w:
            logger.warning("第 %d 章 DialogueTuner 输入已超标(%d > %d)，跳过", chapter_num, input_cn, max_w)
            return hook_draft
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
            "- 如果对话占比过低，适当添加对话；如果过高，转为叙述\n"
            "\n【对话去AI味铁律——违反即回退】\n"
            "- 禁止书面语台词：'既然如此''那么''综上所述''首先''其次'\n"
            "- 禁止完美逻辑链：人说话会跑题、会自相矛盾、会只说半句\n"
            "- 禁止连续3句以上用'道/说'以外的提示词（低语/呢喃/沉声道/冷声道/缓缓道）\n"
            "- 允许：口癖、脏话、打断、重复、反问、不回答对方问题\n"
            "- 每个角色的对话必须体现其对话指纹，禁止千人一面"
            + self._build_persona_injection()
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
        temp, max_tok = self._get_agent_llm_params("dialogue_tuner", 0.1, 8000)
        self._log_full_prompt("dialogue_tuner", chapter_num, system, user)
        tuned = self.llm.call_for_agent("dialogue_tuner", system, user, temperature=temp, max_tokens=max_tok)
        tuned_cn = len(re.findall(r'[\u4e00-\u9fff]', tuned))
        if input_cn > 0 and tuned_cn < input_cn * 0.85:
            logger.warning("第 %d 章 DialogueTuner 字数损失 %.1f%% (%d→%d)，回退原稿", chapter_num, (1 - tuned_cn/input_cn) * 100, input_cn, tuned_cn)
            return hook_draft
        return tuned

    def _call_polish(self, chapter_num: int, draft: str, extra_instruction: str = "") -> str:
        """Polish：基于纸人婚风格质检，不合格重写。
        
        ★ 字数保护：Polish 后字数损失超过 15% 则回退到原稿。
        """
        import re
        original_cn = len(re.findall(r'[\u4e00-\u9fff]', draft))
        
        system = (
            "你是 Polish（终审润色师）。\n"
            "质检清单（逐项检查，不合格必须修正）：\n"
            f"1. 字数：是否{self.cfg.words_per_chapter}±{self.cfg.words_tolerance}字？\n"
            "2. 开头：是否直接切入场景（不是概述）？前100字是否有动作+感官？\n"
            "3. 结尾：是否画面定格或疑问悬念？\n"
            "4. 对话：是否自然嵌入叙述（不是引号单独成段）？\n"
            "5. 术语：是否自然嵌入，不生硬？\n"
            "6. 去AI味：是否有首先…其次…最后/综上所述/值得注意的是/过了一会儿？\n"
            "7. 思考过程：是否有模型思考内容？有则删除\n"
            "8. 精确数字：是否有'0.5毫米/47赫兹/pH值'等参数？改为身体体感\n"
            "9. 情绪标签：是否有'恐惧/绝望/愤怒'等标签？改为生理反应\n"
            "\n【绝对铁律——违反任何一条，润色结果作废】\n"
            "- 保留所有情节和场景，禁止删减任何段落\n"
            "- 润色后的中文字数必须与原文字数相差不超过 5%\n"
            "- 只微调措辞、节奏和对话格式，不要重写\n"
            "- 绝对只输出纯正文，不要输出任何说明、润色总结、字数统计、自检表、思考过程或元信息\n"
            + self._build_persona_injection()
        )
        user = f"【任务】润色第{chapter_num}章\n\n【正文】\n{draft}"
        if extra_instruction:
            user += f"\n\n【额外指令】\n{extra_instruction}"
        temp, max_tok = self._get_agent_llm_params("polish", 0.3, 8000)
        self._log_full_prompt("polish", chapter_num, system, user)
        polished = self.llm.call_for_agent("polish", system, user, temperature=temp, max_tokens=max_tok)
        
        # 字数保护：损失超过 15% 回退原稿
        polished_cn = len(re.findall(r'[\u4e00-\u9fff]', polished))
        if original_cn > 0 and polished_cn < original_cn * 0.85:
            logger.warning(
                "第 %d 章 Polish 后字数损失 %.1f%% (%d→%d)，回退到原稿",
                chapter_num, (1 - polished_cn/original_cn) * 100, original_cn, polished_cn
            )
            return draft
        return polished

    def _call_auditor(self, chapter_num: int, content: str) -> dict[str, Any]:
        """Auditor Agent：结构审计 + LLM 深度审计（可配置开关）。"""
        report = self._structural_audit(content, chapter_num)

        # LLM 深度审计（默认启用，可通过 book.yaml llm.auditor_enabled=false 关闭）
        if self.cfg.llm.get("auditor_enabled", True):
            try:
                system = self._build_auditor_system_prompt()
                user = self._build_auditor_user_prompt(chapter_num, content, report)
                temp, max_tok = self._get_agent_llm_params("auditor", 0.0, 2000)
                self._log_full_prompt("auditor", chapter_num, system, user)
                llm_report = self.llm.call_for_agent("auditor", system, user, temperature=temp, max_tokens=max_tok)
                if isinstance(llm_report, str):
                    import json
                    llm_report = json.loads(llm_report)
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
            self._log_full_prompt("emotion_llm", chapter_num, system, user)
            result = self.llm.call_for_agent("emotion_analyzer", system, user, temperature=0.0, max_tokens=500)
            if isinstance(result, str):
                import json
                result = json.loads(result)
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
            "\n3. 直接输出补充的正文段落。"
            "\n4. 绝对不要输出任何说明、润色总结、字数统计、自检表、思考过程或元信息。"
            "\n5. 只输出中文正文。"
        )
        user = (
            f"以下是第 {chapter_num} 章的已有内容（当前字数不足，需要补充约 {short_by} 字）：\n\n"
            f"{content[:3000]}\n\n"
            f"【任务】请基于以上内容，补充至少 {short_by} 字的新内容。"
            f"这是硬性要求——你必须写满 {short_by} 字，只多不少。\n\n"
            f"【补充策略——按优先级】\n"
            f"1. 优先补充叙述性细节：环境氛围、感官描写、动作细节、心理活动\n"
            f"2. 次要补充对话：只在必要时添加，避免对话块超过3段\n"
            f"3. 不要重复已有情节，而是深化已有场景\n"
            f"4. 补充内容必须自然衔接，保持风格一致\n\n"
            f"直接输出补充的正文段落，不要任何说明。"
        )
        default_max_tok = min(12000, self.cfg.llm.get("max_tokens", 12000))
        temp, max_tok = self._get_agent_llm_params("expander", 0.5, default_max_tok)
        self._log_full_prompt("expander", chapter_num, system, user)
        return self.llm.call_for_agent("expander", system, user, temperature=temp, max_tokens=max_tok)

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