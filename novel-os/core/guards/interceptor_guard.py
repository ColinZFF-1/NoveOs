"""Interceptor Guard —— 将现有 DeAIInterceptor 接入 Guard Registry。"""
from __future__ import annotations

from typing import Any

from core.guards.base import BaseGuard, GuardResult
from core.interceptor import DeAIInterceptor


class InterceptorGuard(BaseGuard):
    """包装 DeAIInterceptor，提供 Guard Registry 统一接口。"""

    guard_id = "deai_interceptor"
    description = "DeAI 拦截器：识别 AI 模板词、高频副词、英文残留等"
    default_level = "WARN"

    def __init__(self, interceptor: DeAIInterceptor) -> None:
        self._interceptor = interceptor

    def run(self, content: str, context: dict[str, Any]) -> GuardResult:
        chapter_num = context.get("chapter_num", 0)
        result = self._interceptor.scan(content, chapter_num)
        level = "BLOCKING" if result.blocking else ("WARN" if result.issues else "PASS")
        return GuardResult(
            guard_id=self.guard_id,
            level=level,
            message=f"发现 {len(result.issues)} 处问题" if result.issues else "未发现 AI 痕迹",
            metadata={
                "issues": result.issues,
                "stats": result.stats,
                "blocking": result.blocking,
            },
        )

    def calibrate(self, hits: int, total: int) -> dict[str, Any]:
        if total == 0:
            return {}
        hit_rate = hits / total
        if hit_rate > 0.5:
            return {"suggestion": "拦截器命中过高，建议审查黑名单词库"}
        return {}
