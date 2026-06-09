"""共享 Prompt 构建工具 —— 从 batch_writer.py 迁移。

原 _build_system_prompt、_build_task_user_prompt、_build_scene_writer_dna 等
方法提取为模块级函数，供各 Step 复用。
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from core.chapter_validator import TERM_MANDATORY
from core.config_loader import BookConfig
from core.state_manager import StateManager

logger = logging.getLogger("novel-os.writing.prompts")


# ------------------------------------------------------------------
# Agent LLM 参数
# ------------------------------------------------------------------
def get_agent_llm_params(
    book_config: BookConfig, agent_type: str, default_temp: float, default_max_tokens: int
) -> tuple[float, int]:
    """从 book.yaml agent_query 读取 agent 的 temperature/max_tokens。"""
    query = book_config.agent_query.get(agent_type, {})
    return query.get("temperature", default_temp), query.get("max_tokens", default_max_tokens)


# ------------------------------------------------------------------
# Prompt 日志
# ------------------------------------------------------------------
def log_full_prompt(agent_type: str, chapter_num: int, system: str, user: str) -> None:
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


# ------------------------------------------------------------------
# 世界观 / 规则加载
# ------------------------------------------------------------------
def load_worldview_rules(state: StateManager) -> str:
    """从 state 数据库读取术语字典和世界观铁律，注入 system prompt。"""
    rules_parts = []
    try:
        terms = state.get_term_dict()
        if not terms:
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
                rules_parts.append(
                    f"- {t['term']}（{t.get('category', '')}，第{t.get('first_chapter', '?')}章首次出现）：{t.get('description', '')}"
                )

        specs = state.get_chapter_specs(spec_keys=["title", "core_event"])
        if specs:
            rules_parts.append("\n【章节任务——必须严格呈现以下核心事件】")
            for s in specs:
                if s.get("spec_key") == "core_event" and s.get("spec_value"):
                    rules_parts.append(f"- 第{s['chapter']}章：{s['spec_value'][:80]}")
    except Exception as exc:
        logger.warning("读取世界观铁律失败: %s", exc)
    return "\n".join(rules_parts)


def get_character_states(state: StateManager) -> list[dict[str, Any]]:
    """从 state 数据库读取活跃人物状态。"""
    try:
        return state.get_characters_full()
    except Exception as exc:
        logger.warning("读取人物状态失败: %s", exc)
    return []


def get_consistency_rules(state: StateManager) -> list[str]:
    """从 state 数据库读取写作规则。"""
    try:
        return state.get_hard_rules()
    except Exception as exc:
        logger.warning("读取规则失败: %s", exc)
    return []


# ------------------------------------------------------------------
# System Prompt 构建
# ------------------------------------------------------------------
def build_system_prompt(book_config: BookConfig, state: StateManager, agent_type: str) -> str:
    """根据 Agent 类型构造 system prompt，所有书籍配置从数据库动态加载。"""
    query = book_config.agent_query.get(agent_type, {})
    role = query.get("role", f"小说{agent_type}")
    cfg = query

    worldview = load_worldview_rules(state)
    parts = []
    if worldview:
        parts.append(worldview)

    persona = book_config.author_persona
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

    parts.append("\n【网文禁区——出现即FAIL】")
    parts.append("- 禁止'不知道为什么/仿佛/似乎/好像/他意识到'")
    parts.append("- 禁止'一些/实际上/在一定程度上/本质上/换句话说'")
    parts.append("- 禁止被动语态：'被拖走/被吞噬'→改成主动描述")
    parts.append("- 禁止概括性时间：'过了一会儿/不久之后'")
    parts.append("- 禁止情绪标签：'恐惧/绝望'→改成生理反应")

    chars = get_character_states(state)
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


def build_task_user_prompt(book_config: BookConfig, agent_type: str, chapter_num: int, context: str = "") -> str:
    """构造 user prompt。"""
    query = book_config.agent_query.get(agent_type, {})
    role = query.get("role", f"小说{agent_type}")
    desc = query.get("description", "")
    expected = query.get("expected_output", "")

    for placeholder in ["{chapter_number}", "{chapter}"]:
        desc = desc.replace(placeholder, str(chapter_num))
        expected = expected.replace(placeholder, str(chapter_num))

    parts = [desc] if desc else []
    if context:
        parts.append(f"\n[上文/输入]\n{context[:5000]}")
    if expected:
        parts.append(f"\n[预期输出]\n{expected}")

    if agent_type == "writer":
        target = book_config.words_per_chapter
        tol = book_config.words_tolerance
        min_w = target - tol
        max_w = target + tol
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


# ------------------------------------------------------------------
# 作者人格注入
# ------------------------------------------------------------------
def build_persona_injection(book_config: BookConfig) -> str:
    """生成 author_persona 注入文本，供后处理 Agent 使用。"""
    persona = book_config.author_persona
    if not persona:
        return ""
    parts = ["\n【作者人格——修改时必须保持此风格】"]
    voice = persona.get("voice", "")
    if voice:
        parts.append(f"叙事声音：{voice}")
    forbidden = persona.get("forbidden_rhetoric", [])
    if forbidden:
        parts.append(f"绝对禁止引入：{'、'.join(forbidden)}")
    return "\n".join(parts)


# ------------------------------------------------------------------
# SceneWriter DNA
# ------------------------------------------------------------------
def build_scene_writer_dna(book_config: BookConfig) -> str:
    """构建 SceneWriter 的 system prompt（风格DNA），基于 book.yaml author_persona 动态注入。"""
    persona = book_config.author_persona
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


# ------------------------------------------------------------------
# 辅助：从 outline.md 读取标题
# ------------------------------------------------------------------
def get_chapter_title_from_outline_md(book_config: BookConfig, chapter_num: int) -> str:
    """从 outline.md 解析指定章节的标题。"""
    outline_path = book_config.base_path / "outline.md"
    if not outline_path.exists():
        return ""
    try:
        text = outline_path.read_text(encoding="utf-8")
        pattern = rf'[#]{{2,4}}\s*第\s*{chapter_num}\s*章[：:]\s*(.+)'
        m = re.search(pattern, text)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return ""
