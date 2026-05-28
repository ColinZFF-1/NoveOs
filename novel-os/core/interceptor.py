"""Novel-OS DeAI 拦截器 —— 第 5 个隐形 Agent。

职责：在 Writer → Polish 之间执行零成本规则扫描，
      识别并标红 AI 模板词、高频副词、英文残留、闭环结尾等。

设计约束：
    - 零 LLM 调用（纯正则 + 统计，毫秒级）
    - 可配置（通过 world_state.interceptor_rules）
    - 状态持久化（命中次数写入 frequency_tracker）
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("novel-os.interceptor")

# ------------------------------------------------------------------
# 默认黑名单词库（21 类）
# ------------------------------------------------------------------
DEFAULT_BLACKLIST: dict[str, list[str]] = {
    "英文残留": ["harness", "navigate", "cultivate", "leverage", "resonate"],
    "标志性表情": [
        "嘴角微微上扬",
        "眼眸中闪过一丝复杂的光",
        "眼底浮现",
        "眸色幽深",
    ],
    "氛围模板": [
        "空气中弥漫着一种说不清的",
        "仿佛有什么东西在暗处涌动",
    ],
    "过渡废词": [
        "就在这时",
        "殊不知",
        "然而",
        "与此同时",
        "果不其然",
    ],
    "心理描写套壳": [
        "心中一凛",
        "心头一震",
        "莫名有种预感",
        "下意识觉得",
    ],
    "AI高频副词": [
        "缓缓",
        "微微",
        "轻轻",
        "默默",
        "悄然",
        "下意识",
    ],
    "排比诱导词": [
        "不仅",
        "而且",
        "一边",
        "有的",
    ],
}

# 单章闭环检测词（结尾 200 字内出现即标红）
CLOSURE_WORDS = ["终于", "总算", "尘埃落定", "一切归于平静", "到此为止"]


@dataclass
class InterceptorResult:
    """单章扫描结果。"""

    chapter_num: int
    issues: list[str] = field(default_factory=list)
    modified_text: str = ""
    stats: dict[str, Any] = field(default_factory=dict)
    blocking: bool = False
    repair_instruction: str = ""


class DeAIInterceptor:
    """去 AI 味拦截器。"""

    def __init__(
        self,
        rules: dict[str, Any] | None = None,
        blacklist: dict[str, list[str]] | None = None,
    ) -> None:
        self.rules = rules or {}
        self.blacklist = blacklist or DEFAULT_BLACKLIST
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """预编译正则，加速扫描。"""
        self._patterns: dict[str, re.Pattern] = {}
        for category, words in self.blacklist.items():
            # 按长度降序，避免短词先匹配导致长词漏匹配
            sorted_words = sorted(words, key=len, reverse=True)
            escaped = [re.escape(w) for w in sorted_words]
            self._patterns[category] = re.compile("|".join(escaped))

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def scan(self, text: str, chapter_num: int) -> InterceptorResult:
        """扫描正文，返回标红结果与修复指令。"""
        issues: list[str] = []
        modified = text
        stats: dict[str, Any] = {"chapter_num": chapter_num}

        # 1. 黑名单命中（自动替换为占位符，强制 Polish 重写）
        total_hits = 0
        for category, pattern in self._patterns.items():
            hits = pattern.findall(text)
            if hits:
                count = len(hits)
                total_hits += count
                issues.append(f"[{category}] 命中 {count} 次: {list(set(hits))}")
                # 自动替换为占位符
                for word in set(hits):
                    modified = modified.replace(word, f"[[待改写:{word}]]")

        stats["blacklist_hits"] = total_hits

        # 2. 他字密度
        he_count = len(re.findall(r"[他她它]", text))
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        he_density = he_count / max(chinese_chars, 1)
        max_he = self.rules.get("max_he_density", 0.10)
        stats["he_density"] = round(he_density, 4)
        stats["he_count"] = he_count
        if he_density > max_he:
            issues.append(f"[他字密度] {he_density:.2%}（上限 {max_he:.0%}）")

        # 3. 破折号计数
        dash_count = text.count("——")
        max_dash = self.rules.get("max_dash_per_chapter", 3)
        stats["dash_count"] = dash_count
        if dash_count > max_dash:
            issues.append(f"[破折号] {dash_count} 个（上限 {max_dash}）")

        # 4. 省略号计数
        ellipsis_count = text.count("……")
        max_ellipsis = self.rules.get("max_ellipsis_per_chapter", 2)
        stats["ellipsis_count"] = ellipsis_count
        if ellipsis_count > max_ellipsis:
            issues.append(f"[省略号] {ellipsis_count} 个（上限 {max_ellipsis}）")

        # 5. 英文词检测（简单：连续英文字母）
        english_words = re.findall(r"[a-zA-Z]{2,}", text)
        max_eng = self.rules.get("max_english_words", 0)
        stats["english_words"] = english_words
        if len(english_words) > max_eng:
            issues.append(f"[英文残留] {len(english_words)} 个: {english_words[:5]}")

        # 6. 排比句检测（三连及以上结构相似句，简化版：连续3句以同一词开头）
        para_count = self._detect_parallels(text)
        stats["parallel_count"] = para_count
        if para_count > 0:
            issues.append(f"[排比句] 发现 {para_count} 处三连及以上结构")

        # 7. 单章闭环检测（结尾 200 字内）
        tail = text[-200:] if len(text) >= 200 else text
        closure_hits = [w for w in CLOSURE_WORDS if w in tail]
        if closure_hits:
            issues.append(f"[闭环结尾] 结尾 200 字内出现: {closure_hits}")

        # 8. 构建修复指令
        repair_instruction = ""
        if issues:
            repair_instruction = (
                "【DeAI 拦截器修复指令 - 必须执行】\n"
                "以下内容为规则引擎标红的 AI 痕迹，请在润色时彻底消除：\n"
                + "\n".join(f"- {issue}" for issue in issues)
                + "\n\n特别注意：\n"
                "1. 所有 [[待改写:xxx]] 占位符必须替换为自然中文表达，禁止保留占位符。\n"
                "2. 他字密度超标时，用角色名、身份、器物指代替代连续的人称代词。\n"
                "3. 禁止用破折号和省略号营造氛围，改用动作或感官描写。\n"
                "4. 结尾必须留悬念或钩子，禁止自我圆满。\n"
            )

        blocking = bool(issues) and self.rules.get("strict_mode", True)

        logger.info(
            "Interceptor 第 %d 章扫描完成: %d issues, 他字密度 %.2f%%",
            chapter_num,
            len(issues),
            he_density * 100,
        )

        return InterceptorResult(
            chapter_num=chapter_num,
            issues=issues,
            modified_text=modified,
            stats=stats,
            blocking=blocking,
            repair_instruction=repair_instruction,
        )

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_parallels(text: str) -> int:
        """简化排比检测：检测连续 3 句以上以同一字/词开头。"""
        sentences = re.split(r"[。！？\n]", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        count = 0
        i = 0
        while i < len(sentences) - 2:
            first_word = sentences[i][:2]
            if first_word and sentences[i + 1].startswith(first_word) and sentences[i + 2].startswith(first_word):
                count += 1
                # 跳过已检测的句子
                j = i + 3
                while j < len(sentences) and sentences[j].startswith(first_word):
                    j += 1
                i = j
            else:
                i += 1
        return count

    def load_blacklist_from_json(self, path: Path) -> None:
        """从外部 JSON 加载黑名单（支持用户自定义扩展）。"""
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            self.blacklist.update(data)
            self._compile_patterns()
            logger.info("加载外部黑名单: %s, 共 %d 类", path, len(data))
