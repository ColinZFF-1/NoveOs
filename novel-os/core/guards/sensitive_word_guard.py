"""敏感词检查 Guard —— 检测正文中的禁用词汇。"""
from __future__ import annotations

import re

from core.guards.base import BaseGuard, GuardResult


# 默认敏感词列表（可扩展）
DEFAULT_FORBIDDEN: list[str] = []


class SensitiveWordGuard(BaseGuard):
    """检查正文是否包含敏感/禁用词汇。"""

    guard_id = "sensitive_word"
    description = "敏感词检查：检测正文中的禁用词汇"
    default_level = "BLOCKING"

    def __init__(self, forbidden_words: list[str] | None = None) -> None:
        self.forbidden_words = forbidden_words or DEFAULT_FORBIDDEN

    def run(self, content: str, context: dict) -> GuardResult:
        found: list[str] = []
        for word in self.forbidden_words:
            if word in content:
                found.append(word)
        if found:
            return GuardResult(
                guard_id=self.guard_id,
                level="BLOCKING",
                message=f"发现敏感词 {len(found)} 个: {', '.join(found[:5])}",
                metadata={"found": found, "count": len(found)},
            )
        return GuardResult(
            guard_id=self.guard_id,
            level="PASS",
            message="未发现敏感词",
            metadata={},
        )

    def calibrate(self, hits: int, total: int) -> dict:
        """如果敏感词命中率过高，可能需要扩充词库或调整匹配策略。"""
        if total == 0:
            return {}
        hit_rate = hits / total
        if hit_rate > 0.5:
            return {"suggestion": "敏感词库可能过于严格，建议审查词库"}
        return {}
