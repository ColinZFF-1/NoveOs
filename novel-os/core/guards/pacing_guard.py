"""PacingGuard —— 节奏检测。

检测连续多章同模式（爽→爽→爽无起伏）、情绪曲线单调。
"""
from __future__ import annotations

from core.guards.base import BaseGuard, GuardResult


class PacingGuard(BaseGuard):
    """检测节奏：连续多章同模式、情绪曲线单调。"""

    guard_id = "pacing"
    description = "节奏检测：检测连续多章同模式、情绪曲线单调"
    default_level = "INFO"

    def run(self, content: str, context: dict) -> GuardResult:
        state = context.get("state_manager")
        chapter_num = context.get("chapter_num", 0)
        if not state or chapter_num < 3:
            return GuardResult(
                guard_id=self.guard_id, level="PASS",
                message="章节数不足，跳过节奏检测", metadata={},
            )

        issues: list[str] = []
        metadata: dict = {}

        # 1. 检测连续3章同一主导情绪
        history = state.get_emotion_history()
        if len(history) >= 3:
            recent = history[-3:]
            # 找出每章主导情绪
            dominant_emotions = []
            for h in recent:
                nue = h.get("nue", 0)
                tian = h.get("tian", 0)
                shuang = h.get("shuang", 0)
                if shuang > nue and shuang > tian:
                    dominant_emotions.append("爽")
                elif nue > tian and nue > shuang:
                    dominant_emotions.append("虐")
                elif tian > nue and tian > shuang:
                    dominant_emotions.append("甜")
                else:
                    dominant_emotions.append("平")

            if len(set(dominant_emotions)) == 1 and dominant_emotions[0] != "平":
                issues.append(
                    f"[情绪单调] 最近3章均为'{dominant_emotions[0]}'模式，缺少情绪起伏"
                )
            metadata["recent_dominant"] = dominant_emotions

        # 2. 检测本章内部节奏：高潮位置
        # 简化：检测高潮词在文中的分布
        climax_words = ["终于", "果然", "果然如此", "果然不出所料", "反转", "逆转",
                        "爆发", "爆发出来", "炸裂", "震惊", "震撼", "不可思议"]
        climax_positions = []
        for word in climax_words:
            idx = content.find(word)
            if idx >= 0:
                climax_positions.append(idx / max(len(content), 1))
        if climax_positions:
            avg_pos = sum(climax_positions) / len(climax_positions)
            metadata["climax_avg_position"] = round(avg_pos, 3)
            if avg_pos < 0.3:
                issues.append("[高潮前置] 高潮/反转集中在文章前30%，后文可能乏力")
            elif avg_pos > 0.85:
                issues.append("[高潮后置] 高潮/反转集中在文章末尾85%后，前文可能拖沓")

        # 3. 检测节奏单一：本章缺乏情绪转折
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        if len(paragraphs) >= 5:
            # 检测是否有明显的情绪转折标记
            turn_markers = ["但", "却", "然而", "没想到", "突然", "反转", "原来",
                           "不料", "谁知", "岂料", "岂知"]
            turn_count = sum(content.count(m) for m in turn_markers)
            metadata["turn_count"] = turn_count
            if turn_count == 0:
                issues.append("[无转折] 本章缺少情绪/情节转折，平铺直叙")
            elif turn_count >= 8:
                issues.append(f"[转折过多] 本章有{turn_count}处转折，节奏可能过于跳跃")

        if issues:
            # PacingGuard 默认 INFO 级别，但如果问题严重则升级为 WARN
            level = "WARN" if len(issues) >= 2 else "INFO"
            return GuardResult(
                guard_id=self.guard_id,
                level=level,
                message=f"发现 {len(issues)} 处节奏问题",
                metadata={"issues": issues, **metadata},
            )
        return GuardResult(
            guard_id=self.guard_id,
            level="PASS",
            message="节奏检测通过",
            metadata=metadata,
        )
