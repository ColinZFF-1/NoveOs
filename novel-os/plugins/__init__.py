"""Novel-OS 插件系统。"""
from plugins.base import BasePlugin
from plugins.plugin_loader import list_available_plugins, load_plugin

__all__ = ["BasePlugin", "load_plugin", "list_available_plugins"]
