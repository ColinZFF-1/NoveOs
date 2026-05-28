"""Novel-OS 类型插件基类。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BasePlugin(ABC):
    """所有类型插件（genre plugin）必须继承的抽象基类。

    插件负责提供：
    - 节拍默认值（beat defaults）
    - 审计规则扩展
    - 感官词库
    - 红线词列表
    - 配置注入段
    """

    @property
    @abstractmethod
    def plugin_id(self) -> str:
        """插件唯一标识，如 'era_biz'。"""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """插件人类可读名称。"""
        ...

    @abstractmethod
    def load_beat_defaults(self) -> dict[str, Any]:
        """加载该类型默认的节拍配置。"""
        ...

    @abstractmethod
    def load_audit_rules(self) -> list[dict[str, Any]]:
        """加载该类型专属的审计规则列表。"""
        ...

    @abstractmethod
    def load_sensory_arsenal(self) -> dict[str, list[str]]:
        """加载感官词库。

        返回如:
        {
          "tactile": ["粗粝", "冰凉"],
          "olfactory": ["霉味", "煤油味"],
          ...
        }
        """
        ...

    @abstractmethod
    def load_redline_words(self) -> list[str]:
        """加载红线词列表（出现即 BLOCKING）。"""
        ...

    @abstractmethod
    def inject_config_sections(self) -> dict[str, Any]:
        """返回要注入全局配置模板的额外模块字典。

        键为模块名，值为模块内容（会被渲染到 config_base.md 的 {{plugin_modules}} 槽位）。
        """
        ...

    def load_forbidden_words(self) -> list[str]:
        """加载禁用词列表（出现即计数，超限 BLOCKING）。

        默认空列表；子类可覆盖。
        """
        return []
