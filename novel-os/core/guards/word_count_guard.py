"""字数检查 Guard —— 确保章节字数在目标范围内。"""
from __future__ import annotations

from core.guards.base import BaseGuard, GuardResult


class WordCountGuard(BaseGuard):
    """检查章节字数是否在目标字数 ± 容忍度范围内。"""

    guard_id = "word_count"
    description = "字数检查：确保章节字数在目标范围内"
    default_level = "BLOCKING"

    def __init__(self, target: int = 4500, tolerance: int = 450) -> None:
        self.target = target
        self.tolerance = tolerance

    def run(self, content: str, context: dict) -> GuardResult:
        word_count = len(content)
        min_words = self.target - self.tolerance
        max_words = self.target + self.tolerance

        if word_count < min_words:
            return GuardResult(
                guard_id=self.guard_id,
                level="BLOCKING",
                message=f"字数不足：{word_count} 字（目标 {self.target}±{self.tolerance}）",
                metadata={"word_count": word_count, "target": self.target, "tolerance": self.tolerance},
            )
        if word_count > max_words:
            return GuardResult(
                guard_id=self.guard_id,
                level="WARN",
                message=f"字数超标：{word_count} 字（目标 {self.target}±{self.tolerance}）",
                metadata={"word_count": word_count, "target": self.target, "tolerance": self.tolerance},
            )
        return GuardResult(
            guard_id=self.guard_id,
            level="PASS",
            message=f"字数合格：{word_count} 字",
            metadata={"word_count": word_count},
        )

    def calibrate(self, hits: int, total: int) -> dict:
        """如果字数频繁不足，放宽容忍度；频繁超标，收紧容忍度。"""
        if total == 0:
            return {}
        hit_rate = hits / total
        if hit_rate < 0.05:
            # 几乎不触发，说明目标太松，可以收紧
            return {"tolerance_adjustment": -50}
        if hit_rate > 0.3:
            # 频繁触发，说明目标太紧，可以放宽
            return {"tolerance_adjustment": +100}
        return {}
