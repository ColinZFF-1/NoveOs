"""Guard Registry 初始化 —— 已重构为 ChapterValidator 统一校验层。

旧版 guards/ 下的独立 Guard 文件已归档至 archive/guards/。
新版所有校验逻辑统一在 core/chapter_validator.py 中。
此文件保留兼容性，返回 ChapterValidator 实例。
"""
from __future__ import annotations

from core.chapter_validator import ChapterValidator

# 全局单例
_validator: ChapterValidator | None = None


def get_registry() -> ChapterValidator:
    """获取全局 ChapterValidator 单例（向后兼容旧 API）。"""
    global _validator
    if _validator is None:
        _validator = ChapterValidator()
    return _validator


def reset_registry() -> None:
    """重置单例（主要用于测试）。"""
    global _validator
    _validator = None
