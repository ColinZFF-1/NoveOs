"""Novel-OS 插件加载器 —— 动态发现与加载类型插件。"""
from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any

import yaml

from plugins.base import BasePlugin

logger = logging.getLogger("novel-os.plugin_loader")


def load_plugin(plugin_id: str, plugins_dir: Path | None = None) -> BasePlugin | dict[str, Any]:
    """加载指定插件。

    优先尝试加载 Python 插件类（plugins/{plugin_id}/plugin.py），
    回退到纯 YAML 配置模式（plugins/{plugin_id}/plugin.yaml）。

    Args:
        plugin_id: 如 "era_biz"。
        plugins_dir: 插件根目录，默认为本文件所在目录。

    Returns:
        BasePlugin 实例，或纯 dict（YAML 模式）。
    """
    if plugins_dir is None:
        plugins_dir = Path(__file__).parent

    plugin_dir = plugins_dir / plugin_id
    if not plugin_dir.exists():
        raise ValueError(f"插件目录不存在: {plugin_dir}")

    # 1. 尝试 Python 类插件
    py_file = plugin_dir / "plugin.py"
    if py_file.exists():
        return _load_python_plugin(plugin_id, py_file)

    # 2. 回退到 YAML 模式
    yaml_file = plugin_dir / "plugin.yaml"
    if yaml_file.exists():
        data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
        logger.info("已加载 YAML 插件: %s", plugin_id)
        return data

    raise ValueError(f"插件 {plugin_id} 缺少 plugin.py 或 plugin.yaml")


def _load_python_plugin(plugin_id: str, py_file: Path) -> BasePlugin:
    """动态导入 Python 插件模块并实例化。"""
    spec = importlib.util.spec_from_file_location(f"novelos_plugin_{plugin_id}", py_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载插件模块: {py_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # 查找 BasePlugin 的子类
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr is not BasePlugin:
            instance = attr()
            logger.info("已加载 Python 插件: %s (%s)", plugin_id, instance.name)
            return instance

    raise ValueError(f"插件 {plugin_id} 的 plugin.py 中未找到 BasePlugin 子类")


def list_available_plugins(plugins_dir: Path | None = None) -> list[str]:
    """列出所有可用插件 ID。"""
    if plugins_dir is None:
        plugins_dir = Path(__file__).parent
    return [
        d.name for d in plugins_dir.iterdir()
        if d.is_dir() and not d.name.startswith("__")
        and (d / "plugin.yaml").exists() or (d / "plugin.py").exists()
    ]
