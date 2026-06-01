"""
Novel-OS Context Builder —— 上下文加载与裁剪引擎。

职责：为每一章构建恰好需要的上下文，确保写第 97 章时 prompt 不会因为
装下前 96 章而爆炸。只注入最近 3 章全文 + 当前人物状态 + 未回收伏笔。

替代旧版 batch_writer 中散落的 4 个 _build_chapter_context 函数。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class ChapterContext:
    """单章写作的完整上下文包。"""

    def __init__(
        self,
        book_dir: str,
        chapter_number: int,
        state_manager=None,
    ):
        self.book_dir = Path(book_dir)
        self.chapter_number = chapter_number
        self.state = state_manager

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def build(self) -> dict[str, Any]:
        """构建完整上下文包，供 Skills 层的 Agent 使用。"""
        return {
            "chapter_number": self.chapter_number,
            "chapter_title": self._get_title(),
            "outline": self._load_outline(),
            "core_event": self._get_core_event(),
            "previous_chapters": self._load_previous_chapters(count=3),
            "previous_ending": self._load_previous_ending(),
            "character_states": self._get_character_states(),
            "pending_foreshadowing": self._get_pending_foreshadowing(),
            "consistency_rules": self._get_consistency_rules(),
            "chapter_history": self._get_chapter_history(count=5),  # 最近 5 章摘要
        }

    def build_minimal(self) -> dict[str, Any]:
        """最简上下文（用于外层 CrewAI 巡检）。"""
        return {
            "chapter_number": self.chapter_number,
            "outline_summary": self._load_outline()[:2000],  # 只取前 2000 字
            "chapter_history": self._get_chapter_history(count=10),
            "character_states": self._get_character_states(),
            "pending_foreshadowing": self._get_pending_foreshadowing(),
        }

    # ------------------------------------------------------------------
    # 私有方法
    # ------------------------------------------------------------------
    def _load_outline(self) -> str:
        """加载大纲。优先从文件，否则从 book.yaml 的 outline 字段。"""
        outline_path = self.book_dir / "outline.md"
        if outline_path.exists():
            return outline_path.read_text(encoding="utf-8")
        # fallback
        return "(无大纲文件，请在 book_dir 下放置 outline.md)"

    def _get_title(self) -> str:
        """从大纲中尝试提取本章标题。"""
        outline = self._load_outline()
        import re
        m = re.search(rf"第\s*{self.chapter_number}\s*章[：:]\s*(.+)", outline)
        if m:
            title = m.group(1).strip()
            if len(title) <= 30:
                return title
            return title[:25]
        return f"第{self.chapter_number}章"

    def _get_core_event(self) -> str:
        """提取大纲中本章的核心事件描述。"""
        outline = self._load_outline()
        import re
        m = re.search(
            rf"第\s*{self.chapter_number}\s*章[：:]*\s*\n?(.*?)(?=###\s*第|$)",
            outline,
        )
        if m:
            return m.group(1).strip()[:300]
        return ""

    def _load_previous_chapters(self, count: int = 3) -> str:
        """加载最近 N 章的摘要（每章前 300 + 后 200 字）。"""
        chapters_dir = self.book_dir / "chapters"
        if not chapters_dir.exists():
            return "(无前文章节)"

        chapter_files = sorted(chapters_dir.glob("*.txt"))
        if not chapter_files:
            return "(无前文章节)"

        recent = chapter_files[-count:]
        summaries = []
        for cf in recent:
            text = cf.read_text(encoding="utf-8")
            if len(text) > 600:
                preview = text[:300] + "\n...\n" + text[-200:]
            else:
                preview = text
            summaries.append(f"### {cf.stem}\n{preview}")

        return "\n\n".join(summaries)

    def _load_previous_ending(self) -> str:
        """前一章最后 500 字（用于文风衔接）。"""
        chapters_dir = self.book_dir / "chapters"
        if not chapters_dir.exists():
            return ""

        files = sorted(chapters_dir.glob("*.txt"))
        if not files:
            return ""

        text = files[-1].read_text(encoding="utf-8")
        return text[-500:] if len(text) > 500 else text

    def _get_character_states(self) -> str:
        """从 StateManager 获取当前人物状态。"""
        if not self.state:
            return self._fallback_char_states()

        try:
            chars = self.state.list_characters(self.chapter_number)
            if not chars:
                return "(无已记录的人物状态)"

            lines = ["## 人物状态"]
            for name, info in chars.items():
                loc = info.get("location", "未知")
                emo = info.get("emotional_state", "未知")
                notes = info.get("notes", "")
                lines.append(f"- **{name}**：位置={loc}，情绪={emo}。{notes}")
            return "\n".join(lines)
        except Exception:
            return self._fallback_char_states()

    def _fallback_char_states(self) -> str:
        """回退：从 book.yaml 或 state.md 读取。"""
        state_md = self.book_dir / "state.md"
        if state_md.exists():
            return state_md.read_text(encoding="utf-8")
        return "(无人物状态信息)"

    def _get_pending_foreshadowing(self) -> str:
        """获取未回收的伏笔列表。"""
        if self.state:
            try:
                pending = self.state.list_pending_foreshadowing()
                if pending:
                    return "\n".join(f"- {f}" for f in pending)
            except Exception:
                pass
        return "(无待回收伏笔)"

    def _get_consistency_rules(self) -> str:
        """获取世界观一致性规则。"""
        if self.state:
            try:
                rules = self.state.list_rules()
                if rules:
                    return "\n".join(
                        f"- {r.get('description', '')} (章节范围: {r.get('unlock_chapter', 0)}-{r.get('expire_chapter', 999)})"
                        for r in rules
                    )
            except Exception:
                pass
        return "(无一致性规则)"

    def _get_chapter_history(self, count: int = 5) -> str:
        """获取最近 N 章的摘要（用于外层巡检）。"""
        if self.state:
            try:
                history = self.state.get_chapter_history(self.chapter_number, count)
                if history:
                    return "\n".join(
                        f"- 第{h['chapter_num']}章 [{h.get('emotion', '')}]: {h.get('summary', '')[:100]}"
                        for h in history
                    )
            except Exception:
                pass
        return "(无章节历史)"
