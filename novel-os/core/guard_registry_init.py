"""Guard Registry 初始化 —— 加载所有内置 Guard。"""
from __future__ import annotations

from core.guards.registry import GuardRegistry
from core.guards.word_count_guard import WordCountGuard
from core.guards.sensitive_word_guard import SensitiveWordGuard

# 全局 Guard Registry 单例
_registry: GuardRegistry | None = None


def get_registry() -> GuardRegistry:
    """获取全局 Guard Registry 单例（懒加载）。"""
    global _registry
    if _registry is None:
        _registry = GuardRegistry()
        # 注册内置 Guard
        _registry.register(WordCountGuard())
        _registry.register(SensitiveWordGuard())
    return _registry


def reset_registry() -> None:
    """重置 Registry（主要用于测试）。"""
    global _registry
    _registry = None
