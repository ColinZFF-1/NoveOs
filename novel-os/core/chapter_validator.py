"""
Novel-OS ChapterValidator —— 统一校验层。

合并了旧版 interceptor.py (230行) + quality_gates.py (157行) + 8 guards (~900行)。
总计 ~1300 行 → ~350 行。

设计原则：
  - 所有阈值在一个 dict 中定义，消除 10% vs 15% 这种冲突。
  - 所有规则扫描只跑一次。
  - 输出简洁：PASS / WARN / BLOCK + 具体问题 + 可操作建议。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ============================================================================
# ★ 唯一阈值源 —— 所有硬指标在这里定义，不散落各处
# ============================================================================
THRESHOLDS = {
    # P0 阻塞级
    "min_words": 4000,
    "max_words": 5000,
    "max_ta_density": 0.10,        # 统一用 10%，消除旧版 interceptor(10%) vs QualityGates(15%) 冲突
    "max_redline": 0,              # 红线词 = 0 容忍
    # P1 警告级
    "max_forbidden_patterns": 3,    # 禁用模式命中 > 3 个
    "dialogue_ratio": (0.25, 0.45),
    "max_dash_count": 3,
    "max_ellipsis_count": 2,
    "max_english_words": 0,
    # P2 信息级
    "sensory_min_per_500": 1,      # 每 500 字至少 1 处非视觉感官
}

# ============================================================================
# ★ 唯一禁用词库 —— interceptor 的黑名单合并于此
# ============================================================================
BANNED_PATTERNS: dict[str, list[str]] = {
    "红线词": [
        # 政治敏感词及平台违禁词（此处留空，由外部 JSON 注入）
    ],
    "禁用词": [
        "缓缓", "微微", "淡淡", "轻轻", "默默", "悄然",
        "莫名", "忽然", "竟然", "突然", "殊不知",
        "与此同时", "果不其然", "不得不说", "众所周知",
        "就在这时", "心中一凛", "心头一震", "下意识觉得",
    ],
    "AI万能结尾": [
        "他不知道的是", "然而事情并没有那么简单",
        "一切归于平静", "尘埃落定",
    ],
    "模板比喻": [
        "像一把刀", "像一条蛇", "像铁板", "像灯泡", "像离水的鱼",
    ],
    "标志性AI表情": [
        "嘴角微微上扬", "眼眸中闪过一丝", "眼底浮现", "眸色幽深",
    ],
    "X秒凝视模式": [
        # 用正则匹配：看了(\d+)秒
    ],
}


@dataclass
class ValidationIssue:
    """单个校验问题。"""
    level: str          # "BLOCK" | "WARN" | "INFO"
    category: str       # "字数" | "他字密度" | "禁用词" | "对话" | "连续性" | "幻觉"
    message: str        # 人类可读描述
    detail: Any = None  # 额外数据（命中词列表、坐标等）


@dataclass
class ValidationResult:
    """统一校验结果。"""
    verdict: str                        # "PASS" | "WARN" | "BLOCK"
    issues: list[ValidationIssue] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    auto_fix_text: str = ""             # 自动修复后的文本（禁用词替换等）
    repair_instruction: str = ""        # 如果需要人工介入，具体的修改指引


class ChapterValidator:
    """统一校验层。"""

    def __init__(self, extra_blacklist: dict[str, list[str]] | None = None):
        self.thresholds = THRESHOLDS.copy()
        self.banned = {k: v.copy() for k, v in BANNED_PATTERNS.items()}
        if extra_blacklist:
            for k, v in extra_blacklist.items():
                self.banned.setdefault(k, []).extend(v)
        self._compile_regexes()

    def _compile_regexes(self):
        """预编译所有正则。"""
        self._re_banned: dict[str, re.Pattern] = {}
        for cat, words in self.banned.items():
            if words:
                escaped = [re.escape(w) for w in sorted(words, key=len, reverse=True)]
                self._re_banned[cat] = re.compile("|".join(escaped))

        # 特殊模式
        self._re_x_second = re.compile(r"看了(\d+)秒|沉默了(\d+)秒|等了(\d+)秒")
        self._re_parallel = re.compile(r"(.{3,15})。\1。\1。")
        self._re_english = re.compile(r"[a-zA-Z]{2,}")
        # 英文允许列表（品类特定术语，不视为 AI 残留）
        self._english_allowlist = {
            "HR", "KPI", "NULL", "PPT", "PC", "ID", "OK", "NO",
            "BGM", "CEO", "CTO", "VIP", "PDF", "OKR", "AI",
            "REVIEW", "Hz", "PS", "ERR", "LV", "XM", "SW",
            "GMT", "UTC", "AM", "PM", "DNA", "RNA", "API",
            "URL", "HTTP", "HTTPS", "SQL", "CPU", "GPU", "RAM",
            "APP", "iOS", "Android", "Java", "Python", "C++",
        }
        self._re_sensory = re.compile(
            r"(闻到|听见|触到|摸到|冰凉|温热|粗糙|滑腻|刺痛|麻木"
            r"|气味|声音|温度|触感|舌尖|鼻腔|耳膜|皮肤|指尖传来)"
        )
        self._re_chinese = re.compile(r"[一-鿿]")
        self._re_ta = re.compile(r"[他她它]")

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def validate(self, text: str, context: dict | None = None) -> ValidationResult:
        """执行全部校验，返回统一结果。

        Args:
            text: 章节正文
            context: 可选上下文，含 chapter_num / state_manager / core_event
        """
        ctx = context or {}
        issues: list[ValidationIssue] = []
        metrics: dict[str, Any] = {}

        # ── P0: 字数 ──
        metrics["word_count"] = self._count_chinese(text)
        wc = metrics["word_count"]
        if wc < self.thresholds["min_words"]:
            issues.append(ValidationIssue("BLOCK", "字数", f"字数不足: {wc} < {self.thresholds['min_words']}", wc))
        elif wc > self.thresholds["max_words"]:
            issues.append(ValidationIssue("BLOCK", "字数", f"字数超标: {wc} > {self.thresholds['max_words']}", wc))

        # ── P0: 他字密度 ──
        ta_count = len(self._re_ta.findall(text))
        metrics["ta_density"] = ta_count / max(wc, 1)
        if metrics["ta_density"] > self.thresholds["max_ta_density"]:
            issues.append(ValidationIssue("BLOCK", "他字密度",
                f"他字密度超标: {metrics['ta_density']:.1%} > {self.thresholds['max_ta_density']:.0%}",
                ta_count))

        # ── P0: 红线词 ──
        redline_hits = self._scan_category(text, "红线词")
        metrics["redline_hits"] = len(redline_hits)
        if metrics["redline_hits"] > self.thresholds["max_redline"]:
            issues.append(ValidationIssue("BLOCK", "红线词", f"红线词命中: {redline_hits}"))

        # ── P1: 禁用词 ──
        banned_hits: dict[str, list[str]] = {}
        for cat in ["禁用词", "AI万能结尾", "模板比喻", "标志性AI表情"]:
            hits = self._scan_category(text, cat)
            if hits:
                banned_hits[cat] = hits
        total_banned = sum(len(v) for v in banned_hits.values())
        metrics["banned_hits"] = total_banned
        metrics["banned_detail"] = banned_hits
        if total_banned > self.thresholds["max_forbidden_patterns"]:
            issues.append(ValidationIssue("WARN", "禁用词",
                f"禁用模式命中 {total_banned} 次（阈值 {self.thresholds['max_forbidden_patterns']}）",
                banned_hits))

        # ── P1: X秒凝视 ──
        xsec_hits = self._re_x_second.findall(text)
        metrics["x_second_count"] = len(xsec_hits)
        if xsec_hits:
            issues.append(ValidationIssue("WARN", "AI模式", f"X秒凝视模式命中 {len(xsec_hits)} 次: {xsec_hits[:3]}"))

        # ── P1: 三连句式 ──
        parallel_hits = self._re_parallel.findall(text)
        metrics["parallel_count"] = len(parallel_hits)
        if parallel_hits:
            issues.append(ValidationIssue("WARN", "AI模式", f"三连句式命中 {len(parallel_hits)} 处"))

        # ── P1: 对话占比 ──
        dialogue_ratio = self._calc_dialogue_ratio(text)
        metrics["dialogue_ratio"] = dialogue_ratio
        lo, hi = self.thresholds["dialogue_ratio"]
        if not (lo <= dialogue_ratio <= hi):
            issues.append(ValidationIssue("WARN", "对话", f"对话占比 {dialogue_ratio:.1%} 不在 [{lo:.0%}, {hi:.0%}] 范围"))

        # ── P1: 英文残留 ──
        eng_words = self._re_english.findall(text)
        eng_filtered = [w for w in eng_words if w not in self._english_allowlist]
        metrics["english_count"] = len(eng_filtered)
        if len(eng_filtered) > self.thresholds["max_english_words"]:
            issues.append(ValidationIssue("WARN", "英文残留",
                f"发现 {len(eng_filtered)} 个非术语英文词: {eng_filtered[:5]}"))

        # ── P1: 大纲遵循度 ──
        core_event = ctx.get("core_event", "")
        if core_event and not self._verify_core_event(text, core_event):
            issues.append(ValidationIssue("WARN", "大纲遵循", f"疑似遗漏核心事件: {core_event[:80]}"))

        # ── P1: 连续性（如果 StateManager 可用）─
        sm = ctx.get("state_manager")
        ch = ctx.get("chapter_num", 0)
        if sm and ch > 1:
            continuity = self._check_continuity(text, sm, ch)
            issues.extend(continuity)

        # ── P2: 感官密度 ─
        sensory_count = len(self._re_sensory.findall(text))
        metrics["sensory_count"] = sensory_count
        expected_sensory = max(1, wc // 500)
        if sensory_count < expected_sensory:
            issues.append(ValidationIssue("INFO", "感官密度",
                f"感官描写 {sensory_count} 处 < 预期 {expected_sensory} 处"))

        # ── 判定 ──
        blocks = [i for i in issues if i.level == "BLOCK"]
        warns = [i for i in issues if i.level == "WARN"]
        info = [i for i in issues if i.level == "INFO"]

        if blocks:
            verdict = "BLOCK"
        elif warns:
            verdict = "WARN"
        else:
            verdict = "PASS"

        # ── 构建修复指令 ──
        repair = self._build_repair(blocks, warns, metrics)

        # ── 自动修复（禁用词替换） ──
        auto_fixed = self._auto_replace(text, banned_hits)

        return ValidationResult(
            verdict=verdict,
            issues=blocks + warns + info,
            metrics=metrics,
            auto_fix_text=auto_fixed,
            repair_instruction=repair,
        )

    def should_retry(self, result: ValidationResult, attempt: int, max_retries: int = 3) -> bool:
        """是否需要重试。"""
        return result.verdict == "BLOCK" and attempt < max_retries

    def build_retry_feedback(self, result: ValidationResult) -> str:
        """将校验失败转为注入 Writer 的修正指令。"""
        if result.verdict == "PASS":
            return ""
        lines = ["\n===== 质量校验反馈（请针对以下问题修改） ====="]
        for issue in result.issues:
            marker = "[阻塞]" if issue.level == "BLOCK" else "[警告]" if issue.level == "WARN" else "[提示]"
            lines.append(f"{marker} [{issue.category}] {issue.message}")
        if result.metrics.get("word_count"):
            lines.append(f"当前字数: {result.metrics['word_count']}")
        lines.append("请修改后重新输出完整章节。")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------
    @staticmethod
    def _count_chinese(text: str) -> int:
        return len(re.findall(r"[一-鿿]", text))

    def _scan_category(self, text: str, category: str) -> list[str]:
        pat = self._re_banned.get(category)
        if not pat:
            return []
        return list(set(pat.findall(text)))

    @staticmethod
    def _calc_dialogue_ratio(text: str) -> float:
        """估算对话占比：中文引号内容 / 总字数。"""
        # 匹配多种中文引号：“...” 或 "..." 或 「...」
        contents = (
            re.findall(r'“([^”]*)”', text) +  # "..."
            re.findall(r'「([^」]*)」', text) +  # 「...」
            re.findall(r'『([^』]*)』', text)      # 『...』
        )
        chinese = len(re.findall(r'[一-鿿]', text))
        if chinese == 0:
            return 0.0
        dialogue_chars = sum(len(re.findall(r'[一-鿿]', q)) for q in contents)
        return min(dialogue_chars / chinese, 1.0)

    @staticmethod
    def _verify_core_event(text: str, core_event: str) -> bool:
        """检查核心事件关键词是否在正文中出现。"""
        keywords = re.findall(r"[一-鿿]{2,}", core_event)
        if not keywords:
            return True
        match_count = sum(1 for kw in keywords if kw in text)
        return match_count >= len(keywords) * 0.5

    @staticmethod
    def _check_continuity(text: str, state_manager, chapter_num: int) -> list[ValidationIssue]:
        """跨章连续性检查（精简版）。"""
        issues: list[ValidationIssue] = []
        try:
            prev_chars = state_manager.list_characters(chapter_num - 1)
            curr_chars = state_manager.list_characters(chapter_num)
            for name, prev in prev_chars.items():
                curr = curr_chars.get(name)
                if not curr:
                    continue
                prev_loc = prev.get("location", "")
                curr_loc = curr.get("location", "")
                if prev_loc and curr_loc and prev_loc != curr_loc:
                    if curr_loc not in text and prev_loc not in text:
                        issues.append(ValidationIssue("WARN", "连续性",
                            f"人物'{name}'位置从'{prev_loc}'跳变到'{curr_loc}'，正文未提及"))
        except Exception:
            pass
        return issues

    def _auto_replace(self, text: str, banned_hits: dict[str, list[str]]) -> str:
        """自动替换禁用词为合适的替代词。"""
        # 禁用词 → 替代词映射
        replacement_map = {
            "缓缓": "慢慢",
            "微微": "稍",
            "淡淡": "轻",
            "轻轻": "轻",
            "默默": "无声",
            "悄然": "无声",
            "莫名": "不知为何",
            "忽然": "猛地",
            "竟然": "竟",
            "突然": "猛地",
            "与此同时": "同时",
            "果不其然": "果然",
            "不得不说": "必须说",
            "众所周知": "人人皆知",
            "就在这时": "此刻",
            "心中一凛": "心头一紧",
            "心头一震": "心头一紧",
            "下意识觉得": "直觉感到",
        }
        modified = text
        for cat, words in banned_hits.items():
            for word in words:
                if word in modified:
                    repl = replacement_map.get(word, f"[[{word}]]")
                    modified = modified.replace(word, repl)
        return modified

    def _build_repair(self, blocks: list, warns: list, metrics: dict) -> str:
        """构建修复指令。"""
        if not blocks and not warns:
            return ""
        lines = ["【ChapterValidator 修复指引】"]
        for b in blocks:
            lines.append(f"  🔴 {b.category}: {b.message}")
        for w in warns:
            lines.append(f"  🟡 {w.category}: {w.message}")
        if metrics.get("word_count", 0) < self.thresholds["min_words"]:
            lines.append("\n→ 字数不足：扩充场景描写或对话细节，而非重复已有内容。")
        if metrics.get("word_count", 0) > self.thresholds["max_words"]:
            lines.append("\n→ 字数超标：精简冗余叙述，合并重复信息。")
        return "\n".join(lines)
