# 全自动选题→写作→发布工作流 设计文档

## 基于 DeepSeek API + Kimi API 的 Python 编排引擎

> **设计日期**: 2026-06-10  
> **目标**: 在仅有 DeepSeek API Key 和 Kimi API Key 的条件下，复刻视频中的全自动内容创作流水线  
> **与原方案的核心差异**: 用 Python 编排引擎替代 Claude Code CLI，用双 API 路由替代单一 Claude 模型

---

## 〇、约束与设计原则

### 0.1 可用资源

| 资源 | 有/无 | 说明 |
|------|-------|------|
| DeepSeek API Key | ✅ 有 | `deepseek-v4-flash` + `deepseek-v4-pro` |
| Kimi API Key | ✅ 有 | `kimi-k2.6` + `kimi-k2.5` |
| Claude Code CLI | ❌ 无 | 需要自己搭建编排层 |
| 飞书机器人 | ❌ 未提及 | 可选扩展，设计预留接口 |
| Windows 环境 | ✅ 有 | Python 3.12 已就绪 |

### 0.2 设计原则

1. **Python 即编排引擎** — 替代 Claude Code 的全部调度能力
2. **双 API 智能路由** — 根据任务特性自动选择最优模型
3. **Obsidian 为唯一存储** — 所有中间产物和最终输出都落在 Vault 内
4. **幂等 + 可恢复** — 每个阶段独立运行，中断后可从断点续跑
5. **人工确认点内置** — 自动化不意味着无人干预，关键节点必须人工过手
6. **渐进式全自动** — 先跑通半自动（有人工确认），再逐步去掉确认点

### 0.3 API 路由策略

```
                    ┌─────────────────────┐
                    │    任务路由器        │
                    │  (APIRouter)        │
                    └─────────┬───────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
    需要结构化推理?       需要长文写作?        需要阅读长文档?
    便宜优先?             中文质量最重要?      超长上下文?
          │                   │                   │
    ┌─────┴─────┐      ┌─────┴─────┐      ┌─────┴─────┐
    │ DeepSeek  │      │   Kimi    │      │   Kimi    │
    │ V4 Flash  │      │  K2.6     │      │  K2.6     │
    │ (think=on)│      │           │      │ (128K ctx)│
    └───────────┘      └───────────┘      └───────────┘
```

**具体任务分配**：

| 流水线阶段 | 主 API | 备选 API | 理由 |
|-----------|--------|---------|------|
| ① 选题扫描 | DeepSeek V4 Flash + thinking | DeepSeek V4 Pro | 结构化分析、评分矩阵、成本低 |
| ② 选题调研 | Kimi K2.6 | DeepSeek V4 Pro | 需要阅读大量知识库笔记，长上下文 |
| ③ 大纲生成 | DeepSeek V4 Flash + thinking | Kimi K2.5 | SCQA 结构需要强推理能力 |
| ④ 正文撰写 | **Kimi K2.6** | DeepSeek V4 Pro | **中文长文写作质量 Kimi 更优** |
| ⑤ 标题生成 | DeepSeek V4 Flash | Kimi K2.5 | 快速迭代任务，成本敏感 |
| ⑥ 去AI味润色 | DeepSeek V4 Flash + thinking | Kimi K2.5 | 规则驱动的结构化润色 |
| ⑦ 知识库搜索 | DeepSeek V4 Flash | — | 本地文件搜索，不需要 API（用 Python 实现） |
| ⑧ 日报/周报 | DeepSeek V4 Flash | Kimi K2.5 | 结构化摘要，便宜优先 |

---

## 一、系统总览

### 1.1 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户交互层                                │
│                                                                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐                 │
│   │  cmd 终端  │    │ Obsidian │    │ 可选: WebUI│                │
│   │ python    │    │ 直接编辑  │    │ (Flask)   │                │
│   │ main.py   │    │          │    │           │                │
│   └─────┬─────┘    └────┬─────┘    └─────┬─────┘                │
│         │               │               │                       │
└─────────┼───────────────┼───────────────┼───────────────────────┘
          │               │               │
          └───────────────┴───────┬───────┘
                                  │
┌─────────────────────────────────┼─────────────────────────────────┐
│                    Python 编排引擎 (content_factory/)               │
│                                  │                                  │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                     Scheduler (调度器)                        │ │
│  │  · 命令行触发: python main.py <command>                      │ │
│  │  · 定时触发: Windows Task Scheduler / schedule 库            │ │
│  │  · 链式触发: 阶段 N 完成后自动调用阶段 N+1                    │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                  │                                  │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐      │
│  │  Stage 1  │→│  Stage 2  │→│  Stage 3  │→│  Stage 4  │      │
│  │ TopicScan │ │ TopicDeep │ │  Outline  │ │   Draft   │      │
│  │  选题扫描  │ │  选题深挖  │ │  大纲生成  │ │  正文撰写  │      │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘      │
│        │              │              │              │              │
│        ↓              ↓              ↓              ↓              │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐      │
│  │  Stage 5  │  │  Stage 6  │  │  Stage 7  │  │  Stage 8  │      │
│  │  Titles   │  │  Polish   │  │  Publish  │  │ Feedback  │      │
│  │  标题生成  │  │ 去AI润色   │  │  发布回流  │  │  数据回收  │      │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘      │
│                                  │                                  │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                    Core Modules (核心模块)                     │ │
│  │                                                               │ │
│  │  APIClient    — DeepSeek & Kimi 统一调用封装                  │ │
│  │  APIRouter    — 智能路由：根据任务类型选择模型                 │ │
│  │  VaultManager — Obsidian Vault 文件读写                       │ │
│  │  PromptLoader — 提示词模板加载与变量注入                       │ │
│  │  StateManager — 流水线状态追踪 (哪个选题在哪个阶段)           │ │
│  │  GitManager   — 自动 git commit                              │ │
│  │  Logger       — 全流程日志                                    │ │
│  └──────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
┌─────────┴─────────┐  ┌─────────┴─────────┐  ┌─────────┴─────────┐
│   DeepSeek API     │  │    Kimi API       │  │   Obsidian Vault  │
│ api.deepseek.com   │  │ api.moonshot.ai   │  │   (本地文件系统)   │
│                    │  │                   │  │                   │
│ · deepseek-v4-flash│  │ · kimi-k2.6       │  │ D:/vault/         │
│ · deepseek-v4-pro  │  │ · kimi-k2.5       │  │                   │
└────────────────────┘  └───────────────────┘  └───────────────────┘
```

### 1.2 项目目录结构

```
D:/vault/                              ← Obsidian Vault 根目录
├── content_factory/                   ← Python 编排引擎 (本项目)
│   │
│   ├── main.py                        ← 主入口: python main.py <command>
│   ├── config.py                      ← 配置文件 (API Key, 路径, 偏好)
│   │
│   ├── core/                          ← 核心模块
│   │   ├── __init__.py
│   │   ├── api_client.py             ← DeepSeek & Kimi 统一调用
│   │   ├── api_router.py             ← 智能路由
│   │   ├── vault_manager.py          ← Obsidian 文件读写
│   │   ├── prompt_loader.py          ← 提示词加载 & 变量渲染
│   │   ├── state_manager.py          ← 流水线状态追踪
│   │   ├── git_manager.py            ← Git 自动提交
│   │   └── logger.py                 ← 日志
│   │
│   ├── stages/                        ← 流水线各阶段
│   │   ├── __init__.py
│   │   ├── stage01_topic_scan.py     ← ① 选题扫描
│   │   ├── stage02_topic_deep.py     ← ② 选题深挖
│   │   ├── stage03_outline.py        ← ③ 大纲生成
│   │   ├── stage04_draft.py          ← ④ 正文撰写
│   │   ├── stage05_titles.py         ← ⑤ 标题生成
│   │   ├── stage06_polish.py         ← ⑥ 去AI润色
│   │   ├── stage07_publish.py        ← ⑦ 发布回流
│   │   └── stage08_feedback.py       ← ⑧ 数据回收
│   │
│   ├── prompts/                       ← 提示词模板 (Jinja2)
│   │   ├── topic_scan.j2
│   │   ├── topic_deep.j2
│   │   ├── outline.j2
│   │   ├── draft.j2
│   │   ├── titles.j2
│   │   ├── polish.j2
│   │   ├── daily_brief.j2
│   │   └── weekly_report.j2
│   │
│   ├── templates/                     ← 输出文件模板
│   │   ├── topic_template.md
│   │   ├── outline_template.md
│   │   ├── draft_template.md
│   │   └── published_template.md
│   │
│   ├── tests/                         ← 测试
│   │   ├── test_api_client.py
│   │   ├── test_router.py
│   │   └── test_stages.py
│   │
│   └── requirements.txt               ← 依赖
│
├── 00_Inbox/                          ← Vault 目录 (同上个方案)
├── 10_Journal/
├── 20_Topics/
│   ├── Pending/
│   ├── Approved/
│   ├── In_Progress/
│   └── Completed/
├── 30_Drafts/
├── 40_Published/
├── 50_Knowledge/
├── 60_Content_Library/
├── 90_System/
│   ├── settings.yaml                 ← 用户偏好配置
│   └── style_guide.md                ← 个人写作风格指南
└── .gitignore
```

---

## 二、核心模块详细设计

### 2.1 config.py — 配置中心

```python
"""
content_factory/config.py
所有配置集中管理。API Key 从环境变量读取，绝不硬编码。
"""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class APIConfig:
    """API 配置"""
    # DeepSeek
    deepseek_api_key: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", "")
    )
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_default_model: str = "deepseek-v4-flash"
    deepseek_pro_model: str = "deepseek-v4-pro"

    # Kimi (Moonshot)
    kimi_api_key: str = field(
        default_factory=lambda: os.getenv("KIMI_API_KEY", "")
    )
    kimi_base_url: str = "https://api.moonshot.ai/v1"
    kimi_default_model: str = "kimi-k2.6"
    kimi_fast_model: str = "kimi-k2.5"

    # 通用
    max_retries: int = 3
    request_timeout: int = 300  # 秒，长文写作需要更久

@dataclass
class VaultConfig:
    """Obsidian Vault 配置"""
    vault_root: Path = Path("D:/vault")  # 默认，可改
    topic_dir: Path = field(init=False)
    draft_dir: Path = field(init=False)
    published_dir: Path = field(init=False)
    knowledge_dir: Path = field(init=False)
    library_dir: Path = field(init=False)
    system_dir: Path = field(init=False)

    def __post_init__(self):
        self.topic_dir = self.vault_root / "20_Topics"
        self.draft_dir = self.vault_root / "30_Drafts"
        self.published_dir = self.vault_root / "40_Published"
        self.knowledge_dir = self.vault_root / "50_Knowledge"
        self.library_dir = self.vault_root / "60_Content_Library"
        self.system_dir = self.vault_root / "90_System"

@dataclass
class PipelineConfig:
    """流水线配置"""
    # 自动化级别: "semi" (半自动，每阶段需确认) | "full" (全自动)
    auto_mode: str = "semi"

    # 默认字数
    default_word_count: int = 3500

    # 写作领域
    content_domain: str = "AI技术 & 产品实践"  # 改成你的领域

    # 发布平台
    platforms: list = field(default_factory=lambda: ["公众号", "知乎"])

    # 定时任务 (Windows Task Scheduler 触发时使用)
    daily_scan_time: str = "08:00"    # 每日选题扫描
    weekly_report_day: str = "friday"  # 周报日

@dataclass
class Config:
    """总配置"""
    api: APIConfig = field(default_factory=APIConfig)
    vault: VaultConfig = field(default_factory=VaultConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)

# 全局单例
config = Config()
```

### 2.2 api_client.py — 统一 API 调用

```python
"""
content_factory/core/api_client.py
统一封装 DeepSeek 和 Kimi 的 API 调用，都走 OpenAI SDK 兼容接口。
"""
import time
from typing import Optional, Generator
from openai import OpenAI
from content_factory.config import config, APIConfig
from content_factory.core.logger import get_logger

logger = get_logger(__name__)

class APIClient:
    """统一的 LLM API 客户端"""

    def __init__(self, provider: str):
        """
        provider: "deepseek" | "kimi"
        """
        self.provider = provider
        cfg = config.api

        if provider == "deepseek":
            self.client = OpenAI(
                api_key=cfg.deepseek_api_key,
                base_url=cfg.deepseek_base_url
            )
            self.default_model = cfg.deepseek_default_model
        elif provider == "kimi":
            self.client = OpenAI(
                api_key=cfg.kimi_api_key,
                base_url=cfg.kimi_base_url
            )
            self.default_model = cfg.kimi_default_model
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        thinking: bool = False,
        stream: bool = False,
    ) -> str:
        """
        发送聊天请求，返回完整响应文本。

        Args:
            messages: 标准 OpenAI 格式消息列表
            model: 模型 ID，None 则用默认
            temperature: 温度参数
            max_tokens: 最大输出 token
            thinking: 是否启用思考模式 (仅 DeepSeek 支持)
            stream: 是否流式输出

        Returns:
            响应文本
        """
        model = model or self.default_model
        extra_body = {}

        if thinking and self.provider == "deepseek":
            extra_body["thinking"] = {"type": "enabled"}

        for attempt in range(config.api.max_retries):
            try:
                logger.info(
                    f"[{self.provider}] Calling {model} | "
                    f"messages={len(messages)} | tokens_max={max_tokens}"
                )

                if stream:
                    # 流式调用，拼接后返回
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        extra_body=extra_body if extra_body else None,
                        stream=True,
                        timeout=config.api.request_timeout,
                    )
                    full_text = []
                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            full_text.append(chunk.choices[0].delta.content)
                    return "".join(full_text)
                else:
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        extra_body=extra_body if extra_body else None,
                        timeout=config.api.request_timeout,
                    )
                    return response.choices[0].message.content

            except Exception as e:
                logger.warning(
                    f"[{self.provider}] Attempt {attempt+1}/{config.api.max_retries} failed: {e}"
                )
                if attempt < config.api.max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    raise

    def chat_with_file(
        self,
        system_prompt: str,
        user_prompt: str,
        file_paths: list[str],
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        带文件上下文的聊天。
        读取指定文件内容，拼接到 user prompt 前面。

        用于：选题调研时加载知识库相关笔记、大纲生成时加载选题报告等。
        """
        file_contents = []
        for fp in file_paths:
            p = Path(fp)
            if p.exists():
                content = p.read_text(encoding="utf-8")
                file_contents.append(f"--- 文件: {p.name} ---\n{content}\n")

        full_user_prompt = (
            "以下是相关参考文件的内容：\n\n"
            + "\n".join(file_contents)
            + "\n--- 以上是参考文件 ---\n\n"
            + user_prompt
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_user_prompt},
        ]

        return self.chat(messages, model=model, **kwargs)
```

### 2.3 api_router.py — 智能路由

```python
"""
content_factory/core/api_router.py
根据任务类型自动选择最优模型。
"""
from enum import Enum
from content_factory.core.api_client import APIClient
from content_factory.config import config

class TaskType(Enum):
    """任务类型枚举"""
    TOPIC_SCAN = "topic_scan"           # 选题扫描 → DeepSeek Flash
    TOPIC_DEEP = "topic_deep"           # 选题深挖 → Kimi (长上下文)
    OUTLINE = "outline"                 # 大纲生成 → DeepSeek Flash + thinking
    DRAFT = "draft"                     # 正文撰写 → Kimi (中文写作质量)
    TITLES = "titles"                   # 标题生成 → DeepSeek Flash
    POLISH = "polish"                   # 去AI润色 → DeepSeek Flash + thinking
    SUMMARY = "summary"                 # 日报/周报 → DeepSeek Flash
    KNOWLEDGE_SEARCH = "knowledge"      # 知识库搜索 → 本地 Python (不调 API)

# 路由表
ROUTE_TABLE = {
    TaskType.TOPIC_SCAN:   ("deepseek", "deepseek-v4-flash", True),   # (provider, model, thinking)
    TaskType.TOPIC_DEEP:   ("kimi",     "kimi-k2.6",         False),
    TaskType.OUTLINE:      ("deepseek", "deepseek-v4-flash", True),
    TaskType.DRAFT:        ("kimi",     "kimi-k2.6",         False),
    TaskType.TITLES:       ("deepseek", "deepseek-v4-flash", False),
    TaskType.POLISH:       ("deepseek", "deepseek-v4-flash", True),
    TaskType.SUMMARY:      ("deepseek", "deepseek-v4-flash", False),
}

# 缓存已创建的 client 实例
_clients: dict[str, APIClient] = {}

def get_client(task_type: TaskType) -> APIClient:
    """根据任务类型获取最优 APIClient"""
    provider, model, thinking = ROUTE_TABLE[task_type]

    if provider not in _clients:
        _clients[provider] = APIClient(provider)

    return _clients[provider]

def get_model(task_type: TaskType) -> str:
    """获取任务类型对应的推荐模型"""
    _, model, _ = ROUTE_TABLE[task_type]
    return model

def get_thinking(task_type: TaskType) -> bool:
    """是否需要启用思考模式"""
    _, _, thinking = ROUTE_TABLE[task_type]
    return thinking

def execute_task(
    task_type: TaskType,
    system_prompt: str,
    user_prompt: str,
    file_paths: list[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    fallback: bool = True,
) -> str:
    """
    执行任务的统一入口。

    Args:
        task_type: 任务类型
        system_prompt: 系统提示词
        user_prompt: 用户提示词
        file_paths: 可选，要加载的参考文件路径列表
        temperature: 温度
        max_tokens: 最大输出
        fallback: 主 API 失败时是否尝试备选

    Returns:
        AI 响应文本
    """
    provider, model, thinking = ROUTE_TABLE[task_type]
    client = get_client(task_type)

    try:
        if file_paths:
            return client.chat_with_file(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                file_paths=file_paths,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                thinking=thinking,
            )
        else:
            return client.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                thinking=thinking,
            )
    except Exception as e:
        if not fallback:
            raise

        # 降级到备选 API
        fallback_provider = "kimi" if provider == "deepseek" else "deepseek"
        logger = __import__("content_factory.core.logger", fromlist=["get_logger"]).get_logger(__name__)
        logger.warning(f"Primary {provider} failed, falling back to {fallback_provider}")

        fb_client = APIClient(fallback_provider)
        return fb_client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
```

### 2.4 vault_manager.py — Vault 文件管理

```python
"""
content_factory/core/vault_manager.py
Obsidian Vault 的文件读写、选题状态管理、知识库搜索。
"""
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from content_factory.config import config
from content_factory.core.logger import get_logger

logger = get_logger(__name__)

class VaultManager:
    """Obsidian Vault 管理器"""

    def __init__(self):
        self.root = config.vault.vault_root

    # ─── 文件读写 ─────────────────────────────────

    def read(self, relative_path: str) -> str:
        """读取 Vault 中的文件"""
        p = self.root / relative_path
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")
        return p.read_text(encoding="utf-8")

    def write(self, relative_path: str, content: str):
        """写入文件到 Vault，自动创建父目录"""
        p = self.root / relative_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        logger.info(f"Written: {p}")

    def exists(self, relative_path: str) -> bool:
        return (self.root / relative_path).exists()

    # ─── 选题状态管理 ─────────────────────────────

    def get_topic_status(self, topic_slug: str) -> str:
        """返回选题当前状态: pending/approved/in_progress/completed"""
        for status_dir in ["Pending", "Approved", "In_Progress", "Completed"]:
            if (self.root / f"20_Topics/{status_dir}/{topic_slug}.md").exists():
                return status_dir.lower()
        return "unknown"

    def move_topic(self, topic_slug: str, from_status: str, to_status: str):
        """移动选题文件到新状态目录（跨目录重命名）"""
        src = self.root / f"20_Topics/{from_status}/{topic_slug}.md"
        dst = self.root / f"20_Topics/{to_status}/{topic_slug}.md"
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        logger.info(f"Topic moved: {from_status} → {to_status} | {topic_slug}")

        # 更新选题索引
        self._update_topic_index()

    def list_topics(self, status: str = "Pending") -> list[dict]:
        """列出指定状态的选题"""
        d = self.root / f"20_Topics/{status}"
        if not d.exists():
            return []
        topics = []
        for f in d.glob("*.md"):
            if f.name.startswith("_"):
                continue
            topics.append({
                "slug": f.stem,
                "path": str(f.relative_to(self.root)),
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
        return sorted(topics, key=lambda x: x["modified"], reverse=True)

    # ─── 知识库搜索 (本地实现，不调 API) ───────────

    def search_knowledge(self, query: str, max_results: int = 10) -> list[dict]:
        """
        在知识库中搜索相关笔记。
        使用简单的关键词匹配 + 文件元数据。后续可升级为向量搜索。
        """
        results = []
        search_dirs = [
            "50_Knowledge",
            "60_Content_Library",
            "40_Published",
        ]

        keywords = query.lower().split()

        for dir_name in search_dirs:
            d = self.root / dir_name
            if not d.exists():
                continue
            for md_file in d.rglob("*.md"):
                if md_file.name.startswith("_"):
                    continue
                try:
                    content = md_file.read_text(encoding="utf-8").lower()
                    # 计算匹配分数
                    score = sum(content.count(kw) for kw in keywords)
                    if score > 0:
                        # 提取相关段落 (含关键词的前后 100 字)
                        snippets = []
                        for kw in keywords:
                            for m in re.finditer(
                                rf".{{0,100}}{re.escape(kw)}.{{0,100}}",
                                content
                            ):
                                snippets.append(m.group().strip()[:200])

                        results.append({
                            "path": str(md_file.relative_to(self.root)),
                            "score": score,
                            "snippets": snippets[:3],  # 最多 3 段
                        })
                except Exception:
                    continue

        return sorted(results, key=lambda x: x["score"], reverse=True)[:max_results]

    # ─── 知识回流 ─────────────────────────────────

    def extract_and_save_concepts(self, article_path: str):
        """
        从已发布文章中提取新概念，存入 50_Knowledge/Concepts/
        这里不做 NLP 提取，而是让后续的 AI Agent 来做。
        本方法只是准备好上下文并触发 AI 提取。
        """
        # 这个留给 stage07_publish 调用 AI 来实现
        pass

    def extract_and_save_quotes(self, article_path: str):
        """从文章中提取金句，存入 60_Content_Library/Quotes/"""
        # 同上，由 AI Agent 实现
        pass

    def _update_topic_index(self):
        """更新选题总索引文件 20_Topics/_Topic_Index.md"""
        # 遍历所有状态目录，生成 Dataview 表格
        lines = [
            "# 选题总索引\n",
            f"更新于: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        ]
        for status in ["Pending", "Approved", "In_Progress", "Completed"]:
            topics = self.list_topics(status)
            lines.append(f"\n## {status} ({len(topics)})\n")
            for t in topics:
                lines.append(f"- [[{t['path']}|{t['slug']}]] ({t['modified'][:10]})")

        index_path = self.root / "20_Topics/_Topic_Index.md"
        index_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Topic index updated")

    def get_state_file(self) -> Path:
        """获取流水线状态文件路径"""
        return self.root / "90_System/pipeline_state.json"

    def save_state(self, state: dict):
        """保存流水线状态"""
        self.get_state_file().write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def load_state(self) -> dict:
        """加载流水线状态"""
        sf = self.get_state_file()
        if sf.exists():
            return json.loads(sf.read_text(encoding="utf-8"))
        return {"topics": {}, "last_scan": None, "last_publish": None}
```

### 2.5 prompt_loader.py — 提示词加载

```python
"""
content_factory/core/prompt_loader.py
从 Jinja2 模板加载提示词，注入变量。
"""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from content_factory.config import config

# Jinja2 环境，模板目录为 content_factory/prompts/
_template_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent.parent / "prompts"),
    trim_blocks=True,
    lstrip_blocks=True,
)

# 模板变量缓存
_style_guide_cache: str | None = None

def _get_style_guide() -> str:
    """加载个人风格指南（带缓存）"""
    global _style_guide_cache
    if _style_guide_cache is None:
        sg_path = config.vault.system_dir / "style_guide.md"
        if sg_path.exists():
            _style_guide_cache = sg_path.read_text(encoding="utf-8")
        else:
            _style_guide_cache = ""
    return _style_guide_cache

def load_prompt(template_name: str, **variables) -> tuple[str, str]:
    """
    加载提示词模板，返回 (system_prompt, user_prompt)。

    模板使用 Jinja2 语法，通过 block 区分 system 和 user：
    {% block system %}...{% endblock %}
    {% block user %}...{% endblock %}

    Args:
        template_name: 模板文件名，如 "topic_scan.j2"
        **variables: 要注入的变量

    Returns:
        (system_prompt, user_prompt)
    """
    template = _template_env.get_template(template_name)

    # 注入全局变量
    variables.setdefault("domain", config.pipeline.content_domain)
    variables.setdefault("word_count", config.pipeline.default_word_count)
    variables.setdefault("style_guide", _get_style_guide())
    variables.setdefault("today", __import__("datetime").datetime.now().strftime("%Y-%m-%d"))

    rendered = template.render(**variables)

    # 分离 system 和 user 部分
    # 模板中用 <!-- SYSTEM --> 和 <!-- USER --> 标记
    parts = rendered.split("<!-- USER -->")
    system_part = parts[0].replace("<!-- SYSTEM -->", "").strip()
    user_part = parts[1].strip() if len(parts) > 1 else ""

    return system_part, user_part
```

---

## 三、提示词模板设计

### 3.1 选题扫描 (prompts/topic_scan.j2)

```jinja2
<!-- SYSTEM -->
你是一个资深内容策略师，专门为「{{ domain }}」领域的内容创作者发现和评估选题。

你的分析风格：犀利、务实、不堆砌术语。每个判断都要有具体依据。

## 信息收集范围
你基于训练数据中的知识来判断当前热点趋势。重点关注：
1. {{ domain }}领域最近 1-2 周的讨论热点
2. 新发布的技术/产品/政策
3. 行业内的争议话题和认知冲突
4. 高频被问但缺乏好答案的问题

## 评分规则
对每个选题从 5 个维度打分 (1-5 分)：
- **热度**：当前关注度有多高？1=无人讨论，5=全网刷屏
- **持久度**：1 个月后还值得读吗？1=隔夜即忘，5=常青内容
- **匹配度**：适合我的领域和风格吗？1=强行蹭热点，5=天然契合
- **差异度**：我能写出别人写不出的视角吗？1=千篇一律，5=独家视角
- **素材丰度**：我现有知识库有多少相关积累？1=从零开始，5=信手拈来

## 输出格式
对每个选题严格按照以下格式输出：

### [选题标题]
- **一句话价值**：[为什么现在值得写这个，20字以内]
- **评分**：热度⭐x 持久度⭐x 匹配度⭐x 差异度⭐x 素材⭐x 总分：xx/25
- **核心角度**：[与众不同的切入角度]
- **3个关键论点**：
  1. ...
  2. ...
  3. ...
- **目标读者**：[谁会看 + 看完会做什么]
- **推荐指数**：⭐⭐⭐⭐⭐ (根据总分)

<!-- USER -->
请为「{{ domain }}」领域扫描今日值得写的 3-5 个选题。

{% if knowledge_context %}
以下是知识库中最近的相关笔记，供参考：
{{ knowledge_context }}
{% endif %}

请严格按照系统提示中的输出格式，生成今日选题备忘录。
```

### 3.2 正文撰写 (prompts/draft.j2)

```jinja2
<!-- SYSTEM -->
你是一个专业的内容写作者，擅长「{{ domain }}」领域的深度长文。

## 写作铁律

### 必须做
1. **开头三句话必须抓人** — 用场景、故事、对话或反常识结论开场，禁用"随着...的发展""在当今...时代"
2. **一段一个核心观点** — 结构：观点→论据→案例→小结。观点不堆砌
3. **每 500 字至少 1 句金句** — 可以被独立截屏传播的那种
4. **转折用口语** — "但其实""真正的问题是""更深一层看""你可能会问"
5. **结尾回扣开头** — 给读者一个思考题或行动建议，不要"综上所述"
6. **多用具体数字和人名** — "GPT-4 的响应延迟是 2.3 秒" 而不是 "大模型的响应比较慢"

### 禁止做
- ❌ 禁用词：赋能、抓手、闭环、底层逻辑、颗粒度、对齐、倒逼、打法
- ❌ 禁用句式："众所周知""值得注意的是""毋庸置疑""不可否认"
- ❌ 禁用形容词堆砌："极其重要""非常关键""十分显著"
- ❌ 不要编造数据和引用。不确定的地方标注 [待核实]

### 风格指南
{{ style_guide }}

## 字数要求
目标字数：{{ word_count }} 字（允许上下浮动 10%）

<!-- USER -->
请根据以下大纲撰写正文。

## 选题背景
{{ topic_background }}

## 大纲
{{ outline_content }}

## 可用素材
{% for material in materials %}
- {{ material }}
{% endfor %}

请开始写作。注意：不要输出大纲的重复内容，直接进入正文。
```

### 3.3 去AI润色 (prompts/polish.j2)

```jinja2
<!-- SYSTEM -->
你是一个文字编辑，专门给 AI 生成的文章做"去 AI 味"润色。
你的任务不是重写，而是用最小改动去掉机器感，注入人味。

## 润色六式

1. **动词前置**：把藏在句子中间的动词提到开头
   - AI味："在这个过程中，我们通过分析数据发现了一个问题"
   - 人味："数据告诉我，有问题。一眼就能看出来。"

2. **感官锚定**：每 800 字至少出现一处感官描写
   - "凌晨两点盯着屏幕上的报错日志，咖啡凉了第三杯"
   - 不是让你硬写小说，是让读者"看到"你描述的场景

3. **跳切留白**：段落之间不要用"但是""然而""另外"硬连接
   - 两个段落之间如果逻辑自然成立，就直接跳过去
   - 读者不需要你把每一座桥都搭好

4. **情绪物化**：把抽象情绪写成具体物品
   - 不是"我感到焦虑"，是"桌上那杯凉透的咖啡和我一样，等了一个小时"

5. **未完成句**：偶尔用断裂的句子
   - "这就是问题所在。没有人提。也没有人在意。"
   - 不是每句话都要主谓宾齐全

6. **视角监狱**：保持第一人称视角，不要跳上帝视角
   - "我在生产环境跑了一遍" 而不是 "该项目经过了充分的测试验证"

## 他字密度
- 全文"他/她/它/他们/她们/它们"总出现次数 < 总字数 × 0.5%
- 用人名、职位、具体称呼替代代词
- 每发现一处可替换的"他/她/它"，改成具体名称

## 禁用词扫描
以下词在终稿中不应出现（除非是引语）：
赋能、抓手、闭环、底层逻辑、颗粒度、对齐、复盘、倒逼、打法、拉通、沉淀、输出（动词）、赋能、引爆、出圈

## 对话注入
- 至少添加或增强 1 处直接引语
- 引语可以是你自己的内心独白、同事的对话、或者行业大佬的公开言论

## 输出格式
输出包含两部分：

### 润色后正文
[完整润色后的文章]

### 变更清单
- 改动 1：[原句] → [新句] （理由）
- 改动 2：...
- ...

<!-- USER -->
请对以下初稿进行去 AI 味润色。

## 初稿
{{ draft_content }}

## 作者风格参考
{{ style_guide }}
```

---

## 四、流水线阶段实现

### 4.1 主入口 main.py

```python
"""
content_factory/main.py
命令行主入口。用法：
  python main.py scan              # ① 选题扫描
  python main.py deep <slug>       # ② 选题深挖
  python main.py outline <slug>    # ③ 大纲生成
  python main.py draft <slug>      # ④ 正文撰写
  python main.py titles <slug>     # ⑤ 标题优化
  python main.py polish <slug>     # ⑥ 去AI润色
  python main.py publish <slug>    # ⑦ 发布回流
  python main.py auto              # 全自动跑完所有 Pending 选题
  python main.py daily             # 生成今日简报
  python main.py status            # 查看所有选题状态
"""
import sys
import argparse
from content_factory.core.logger import setup_logging

def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="Content Factory - AI 内容工厂")
    subparsers = parser.add_subparsers(dest="command")

    # 各阶段命令
    subparsers.add_parser("scan", help="扫描热点，生成选题备忘录")
    p_deep = subparsers.add_parser("deep", help="选题深度调研")
    p_deep.add_argument("slug", help="选题标识 (文件名不含扩展名)")
    p_outline = subparsers.add_parser("outline", help="生成大纲和标题")
    p_outline.add_argument("slug")
    p_draft = subparsers.add_parser("draft", help="正文扩写")
    p_draft.add_argument("slug")
    p_titles = subparsers.add_parser("titles", help="标题优化")
    p_titles.add_argument("slug")
    p_polish = subparsers.add_parser("polish", help="去AI味润色")
    p_polish.add_argument("slug")
    p_publish = subparsers.add_parser("publish", help="发布并回流知识库")
    p_publish.add_argument("slug")

    # 便捷命令
    subparsers.add_parser("auto", help="全自动模式")
    subparsers.add_parser("daily", help="生成今日简报")
    subparsers.add_parser("status", help="查看当前状态")

    args = parser.parse_args()

    if args.command == "scan":
        from content_factory.stages.stage01_topic_scan import run
        run()
    elif args.command == "deep":
        from content_factory.stages.stage02_topic_deep import run
        run(args.slug)
    elif args.command == "outline":
        from content_factory.stages.stage03_outline import run
        run(args.slug)
    elif args.command == "draft":
        from content_factory.stages.stage04_draft import run
        run(args.slug)
    elif args.command == "titles":
        from content_factory.stages.stage05_titles import run
        run(args.slug)
    elif args.command == "polish":
        from content_factory.stages.stage06_polish import run
        run(args.slug)
    elif args.command == "publish":
        from content_factory.stages.stage07_publish import run
        run(args.slug)
    elif args.command == "auto":
        from content_factory.stages.pipeline_auto import run_auto
        run_auto()
    elif args.command == "daily":
        from content_factory.stages.stage_summary import run_daily
        run_daily()
    elif args.command == "status":
        from content_factory.stages.pipeline_status import run_status
        run_status()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
```

### 4.2 选题扫描 (stage01_topic_scan.py)

```python
"""
content_factory/stages/stage01_topic_scan.py
① 选题扫描 — 生成今日选题备忘录
"""
from datetime import datetime
from content_factory.core.api_router import execute_task, TaskType
from content_factory.core.prompt_loader import load_prompt
from content_factory.core.vault_manager import VaultManager
from content_factory.core.logger import get_logger

logger = get_logger(__name__)

def run():
    """执行选题扫描"""
    vm = VaultManager()
    today = datetime.now().strftime("%Y-%m-%d")
    output_path = f"20_Topics/Pending/{today}-topic-scan.md"

    logger.info("="*60)
    logger.info("Stage 1: 选题扫描开始")
    logger.info("="*60)

    # 1. 搜索知识库，获取最近的笔记作为上下文
    logger.info("正在搜索知识库获取上下文...")
    knowledge_results = vm.search_knowledge("选题 热点 趋势 写作", max_results=15)
    knowledge_context = "\n".join([
        f"- [{r['path']}] (相关度: {r['score']})\n  " + "\n  ".join(r["snippets"][:2])
        for r in knowledge_results[:10]
    ]) if knowledge_results else "（知识库暂无相关笔记）"

    # 2. 加载提示词
    system_prompt, user_prompt = load_prompt(
        "topic_scan.j2",
        knowledge_context=knowledge_context
    )

    # 3. 调用 AI
    logger.info("正在调用 DeepSeek 扫描选题...")
    result = execute_task(
        task_type=TaskType.TOPIC_SCAN,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=4096,
    )

    # 4. 写入文件
    full_content = f"""# 选题备忘录

> 自动生成于: {datetime.now().strftime("%Y-%m-%d %H:%M")}
> 状态: Pending

---

{result}

---

## 下一步
在 Obsidian 中审阅以上选题，将想写的选题文件移动到 `20_Topics/Approved/`，
然后运行: `python main.py deep <选题slug>`
"""
    vm.write(output_path, full_content)

    # 5. 更新索引
    vm._update_topic_index()

    logger.info(f"选题备忘录已保存: {output_path}")
    logger.info("Stage 1 完成 ✓")
    return output_path
```

### 4.3 正文撰写 (stage04_draft.py)

```python
"""
content_factory/stages/stage04_draft.py
④ 正文撰写 — 根据大纲扩写完整正文
"""
from datetime import datetime
from content_factory.core.api_router import execute_task, TaskType
from content_factory.core.prompt_loader import load_prompt
from content_factory.core.vault_manager import VaultManager
from content_factory.core.logger import get_logger

logger = get_logger(__name__)

def run(slug: str):
    """执行正文撰写"""
    vm = VaultManager()
    today_str = datetime.now().strftime("%Y-%m-%d")

    logger.info("="*60)
    logger.info(f"Stage 4: 正文撰写 [{slug}]")
    logger.info("="*60)

    # 1. 定位选题文件和大纲
    topic_status = vm.get_topic_status(slug)
    if topic_status not in ["approved", "in_progress"]:
        logger.error(f"选题 [{slug}] 状态为 {topic_status}，需要先 Approve")
        return

    outline_path = f"30_Drafts/{slug}/outline.md"
    if not vm.exists(outline_path):
        logger.error(f"大纲文件不存在: {outline_path}，请先运行 outline")
        return

    # 2. 读取大纲和选题背景
    outline_content = vm.read(outline_path)

    # 尝试读取选题文件获取背景
    topic_bg = ""
    for status_dir in ["Approved", "In_Progress", "Pending"]:
        tp = f"20_Topics/{status_dir}/{slug}.md"
        if vm.exists(tp):
            topic_bg = vm.read(tp)[:2000]  # 取前 2000 字作为背景
            break

    # 3. 搜索知识库获取相关素材
    logger.info("正在搜索知识库素材...")
    material_results = vm.search_knowledge(slug, max_results=15)
    materials = []
    for r in material_results[:8]:
        for snippet in r["snippets"][:2]:
            materials.append(f"[来源: {r['path']}] {snippet}")

    # 4. 加载提示词
    system_prompt, user_prompt = load_prompt(
        "draft.j2",
        topic_background=topic_bg,
        outline_content=outline_content,
        materials=materials,
    )

    # 5. 调用 Kimi 写正文 (中文长文质量更好)
    logger.info("正在调用 Kimi 撰写正文...")
    result = execute_task(
        task_type=TaskType.DRAFT,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=8192,       # 长文需要更多 token
        temperature=0.8,       # 写作需要一定创造性
    )

    # 6. 保存初稿
    draft_content = f"""# {slug} — 初稿 v1

> 生成于: {datetime.now().strftime("%Y-%m-%d %H:%M")}
> 状态: Draft v1 (待人工审阅)

---

{result}

---

## 审阅 Checklist
- [ ] 开头是否抓人？
- [ ] 核心观点是否清晰？
- [ ] 案例/数据是否真实？（核查标注 [待核实] 的内容）
- [ ] 每 500 字有金句？
- [ ] 结尾是否回扣开头？
- [ ] 字数是否达标？
"""
    output_path = f"30_Drafts/{slug}/draft-v1.md"
    vm.write(output_path, draft_content)

    # 7. 更新选题状态
    if topic_status == "approved":
        vm.move_topic(slug, "Approved", "In_Progress")

    # 8. 更新流水线状态
    state = vm.load_state()
    state["topics"].setdefault(slug, {})["draft_v1"] = today_str
    vm.save_state(state)

    logger.info(f"正文初稿已保存: {output_path}")
    logger.info("Stage 4 完成 ✓")
    logger.info(f"\n下一步操作：")
    logger.info(f"  1. 在 Obsidian 中审阅初稿: {output_path}")
    logger.info(f"  2. 生成多版本标题: python main.py titles {slug}")
    logger.info(f"  3. 去 AI 味润色: python main.py polish {slug}")
    return output_path
```

### 4.4 全自动流水线 (pipeline_auto.py)

```python
"""
content_factory/stages/pipeline_auto.py
全自动模式：自动处理所有 Approved 状态的选题，一步步跑完流水线。
"""
from content_factory.core.vault_manager import VaultManager
from content_factory.core.logger import get_logger
from content_factory.stages import (
    stage02_topic_deep,
    stage03_outline,
    stage04_draft,
    stage05_titles,
    stage06_polish,
)

logger = get_logger(__name__)

def run_auto():
    """
    全自动模式：
    1. 扫描 Approved 选题
    2. 对每个选题依次执行: deep → outline → draft → titles → polish
    3. 每个阶段完成后自动进入下一阶段
    4. 发布环节 (publish) 仍需人工确认，不在 auto 范围内
    """
    vm = VaultManager()
    approved = vm.list_topics("Approved")

    if not approved:
        logger.info("没有待处理的选题。先运行 scan: python main.py scan")
        return

    logger.info(f"发现 {len(approved)} 个已批准选题，开始全自动处理...")

    for topic in approved:
        slug = topic["slug"]
        logger.info(f"\n{'='*60}")
        logger.info(f"自动处理: {slug}")
        logger.info(f"{'='*60}")

        try:
            # ② 深挖
            logger.info(f"[2/5] 选题深挖...")
            stage02_topic_deep.run(slug)

            # ③ 大纲
            logger.info(f"[3/5] 生成大纲...")
            stage03_outline.run(slug)

            # ④ 正文
            logger.info(f"[4/5] 撰写正文...")
            stage04_draft.run(slug)

            # ⑤ 标题
            logger.info(f"[5/6] 优化标题...")
            stage05_titles.run(slug)

            # ⑥ 润色
            logger.info(f"[6/6] 去AI润色...")
            stage06_polish.run(slug)

            logger.info(f"✅ [{slug}] 处理完成！")
            logger.info(f"   终稿位置: 30_Drafts/{slug}/draft-final.md")
            logger.info(f"   发布: python main.py publish {slug}")

        except Exception as e:
            logger.error(f"❌ [{slug}] 处理失败: {e}")
            continue

    # 最终状态报告
    logger.info(f"\n{'='*60}")
    logger.info("全自动处理完成。运行 `python main.py status` 查看状态。")
    logger.info(f"{'='*60}")
```

---

## 五、定时任务配置

### 5.1 Windows Task Scheduler XML

```xml
<!-- 保存为 content_factory_scheduler.xml，在 Windows 任务计划程序中导入 -->
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <!-- 每天早上 8:00 选题扫描 -->
    <CalendarTrigger>
      <StartBoundary>2026-06-11T08:00:00</StartBoundary>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>python</Command>
      <Arguments>D:\vault\content_factory\main.py scan</Arguments>
      <WorkingDirectory>D:\vault</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
```

### 5.2 备选：Python schedule 库

```python
"""
content_factory/scheduler.py
轻量级定时任务调度器（无需 Windows Task Scheduler）。
在后台持续运行，到点自动触发。
"""
import schedule
import time
from content_factory.stages.stage01_topic_scan import run as scan_run
from content_factory.stages.stage_summary import run_daily
from content_factory.core.logger import get_logger

logger = get_logger(__name__)

def start_scheduler():
    """启动定时调度器"""
    # 每天早上 8:00 — 选题扫描
    schedule.every().day.at("08:00").do(scan_run)

    # 每天早上 8:30 — 晨间简报
    schedule.every().day.at("08:30").do(run_daily)

    # 每周五 17:00 — 周报
    schedule.every().friday.at("17:00").do(
        lambda: __import__(
            "content_factory.stages.stage_summary", fromlist=["run_weekly"]
        ).run_weekly()
    )

    logger.info("调度器已启动。等待定时任务...")
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次

if __name__ == "__main__":
    start_scheduler()
```

---

## 六、成本估算

### 6.1 单篇文章的 API 调用成本

| 阶段 | 模型 | 输入 token (估) | 输出 token (估) | 成本 (元) |
|------|------|----------------|----------------|----------|
| ① 选题扫描 | DeepSeek V4 Flash | ~3,000 | ~2,000 | ¥0.003 |
| ② 选题深挖 | Kimi K2.6 | ~15,000 | ~3,000 | ¥0.054 |
| ③ 大纲生成 | DeepSeek V4 Flash | ~5,000 | ~2,000 | ¥0.004 |
| ④ 正文撰写 | Kimi K2.6 | ~10,000 | ~6,000 | ¥0.072 |
| ⑤ 标题生成 | DeepSeek V4 Flash | ~2,000 | ~1,000 | ¥0.002 |
| ⑥ 去AI润色 | DeepSeek V4 Flash | ~8,000 | ~5,000 | ¥0.009 |
| **单篇合计** | | **~43,000** | **~19,000** | **¥0.14** |

> 按 1 USD ≈ 7.2 CNY 估算。实际价格以官方为准。

### 6.2 月度成本

| 场景 | 篇数/月 | 月成本 |
|------|---------|--------|
| 轻度使用 | 10 篇 | **¥1.40** |
| 中度使用 | 30 篇 | **¥4.20** |
| 重度使用 | 60 篇 | **¥8.40** |
| + 每日简报 | 30 次 | +¥0.30 |
| + 周报 | 4 次 | +¥0.04 |

> 💡 成本极低。即使重度使用（每天 2 篇 + 每日简报 + 周报），月成本不到 **¥10**。

---

## 七、部署清单

### 7.1 环境准备 (15 分钟)

```bash
# 1. 创建 Vault 目录
mkdir D:\vault
mkdir D:\vault\00_Inbox
mkdir D:\vault\10_Journal
mkdir D:\vault\20_Topics\Pending
mkdir D:\vault\20_Topics\Approved
mkdir D:\vault\20_Topics\In_Progress
mkdir D:\vault\20_Topics\Completed
mkdir D:\vault\30_Drafts
mkdir D:\vault\40_Published
mkdir D:\vault\50_Knowledge\Concepts
mkdir D:\vault\50_Knowledge\People
mkdir D:\vault\50_Knowledge\Books
mkdir D:\vault\50_Knowledge\Tools
mkdir D:\vault\50_Knowledge\Insights
mkdir D:\vault\60_Content_Library\Headlines
mkdir D:\vault\60_Content_Library\Openings
mkdir D:\vault\60_Content_Library\Closings
mkdir D:\vault\60_Content_Library\Quotes
mkdir D:\vault\60_Content_Library\Cases
mkdir D:\vault\60_Content_Library\Data
mkdir D:\vault\90_System\Templates
mkdir D:\vault\90_System\Prompts

# 2. 设置环境变量
setx DEEPSEEK_API_KEY "sk-your-deepseek-key"
setx KIMI_API_KEY "sk-your-kimi-key"

# 3. 克隆代码 (或直接复制 design_doc 中的代码文件)
cd D:\vault
git init

# 4. 安装 Python 依赖
pip install openai jinja2 pyyaml schedule

# 5. 测试 API 连通性
python -c "from content_factory.core.api_client import APIClient; c=APIClient('deepseek'); print(c.chat([{'role':'user','content':'Hello'}]))"
```

### 7.2 配置个人偏好

创建 `D:\vault\90_System\style_guide.md`:

```markdown
# 个人写作风格指南

## 我的特点
- 语气：像跟朋友聊天，不端着
- 节奏：短句为主，偶尔长句制造气势
- 常用口语词：说白了、你想想、这事、确实、不过
- 常用转折：但其实、真正的问题是、更关键的是

## 我的领域
- [填入你的领域，如：AI产品落地实践]

## 我的口头禅/常用句式
- "我试了一下，结果..."
- "这里有一个坑..."
- "你可能觉得...但实际上..."

## 我绝对不会用的词
- 赋能、抓手、闭环、底层逻辑

## 我喜欢引用的来源
- [列出你常引用的作者/书/网站]
```

### 7.3 初始化 Git

```bash
cd D:\vault
git init
git add -A
git commit -m "init: content factory setup"
```

### 7.4 设置定时任务

```bash
# 方法 1: Windows Task Scheduler (推荐)
# 导入前面提供的 XML 配置文件

# 方法 2: 后台常驻进程
python D:\vault\content_factory\scheduler.py
```

---

## 八、使用指南

### 8.1 日常操作流程

```bash
# 每天早上 (自动或手动)
python main.py scan              # → 生成选题备忘录

# 在 Obsidian 中审阅选题
# 把想写的选题从 Pending/ 移到 Approved/

# 对每个已批准的选题，一键自动处理
python main.py auto              # → deep → outline → draft → titles → polish

# 或者分步手动:
python main.py deep 2026-06-10-topic-scan   # 选题深挖
python main.py outline my-topic-slug        # 生成大纲
python main.py draft my-topic-slug          # 撰写正文
python main.py titles my-topic-slug         # 标题优化
python main.py polish my-topic-slug         # 去AI润色

# 人工终审后发布
python main.py publish my-topic-slug        # 发布 + 知识回流

# 查看状态
python main.py status
python main.py daily                         # 今日简报
```

### 8.2 选题文件示例

运行 `python main.py scan` 后，会在 `20_Topics/Pending/2026-06-10-topic-scan.md` 生成：

```markdown
# 选题备忘录
> 自动生成于: 2026-06-10 08:05
> 状态: Pending

### AI Agent 在 ToB 场景的真正瓶颈：不是模型，是权限
- **一句话价值**：模型够好了，但企业不敢给 Agent 开权限
- **评分**：热度⭐4 持久度⭐5 匹配度⭐5 差异度⭐4 素材⭐3 总分：21/25
- **核心角度**：从"模型能力"转向"权限设计"，业界没人从这个角度写过
- **3个关键论点**：
  1. 当前 Agent 的瓶颈不是推理能力，而是企业不敢给它数据库读写权限
  2. 对比三个真实案例：权限开放 vs 不开放的效率差异
  3. 给出一个可操作的"权限分级模型"
- **目标读者**：AI 产品经理 & 技术决策者，看完会重新审视自己的 Agent 产品设计
- **推荐指数**：⭐⭐⭐⭐
```

---

## 九、扩展路线图

| 阶段 | 内容 | 优先级 |
|------|------|--------|
| Phase 1 | 跑通基础流水线 (scan→deep→outline→draft→titles→polish) | 🔴 立即 |
| Phase 2 | 接入飞书 Webhook 做消息通知 | 🟡 本周 |
| Phase 3 | 飞书机器人 → 手机上发"选题扫描"触发流程 | 🟡 本周 |
| Phase 4 | 接入 Tavily/Brave Search API 做真实热点采集 | 🟢 下周 |
| Phase 5 | 发布后自动回读数据 (阅读量/点赞) → 反馈到选题评估 | 🟢 下周 |
| Phase 6 | Web UI (Flask/Gradio) → 可视化流水线操作 | 🔵 本月 |
| Phase 7 | 向量数据库 (ChromaDB) → 语义搜索替代关键词搜索 | 🔵 本月 |
| Phase 8 | 多平台一键发布 (公众号草稿箱 / 知乎 / 飞书文档) | 🔵 本月 |

---

## 十、风险与缓解

| 风险 | 缓解 |
|------|------|
| Kimi K2.6 长文输出被截断 | 设置 `max_tokens=8192`，或分段生成后用 Python 拼接 |
| DeepSeek API 限流 (Flash: 2500/min) | 在 `api_client.py` 中增加重试 + 指数退避 |
| Kimi API 缓存未命中导致费用高 | 保持相同的 system prompt 前缀以触发缓存 |
| 知识库搜索 (关键词) 精度不足 | Phase 7 升级为 ChromaDB 向量搜索 |
| 全自动模式产出低质量文章 | 默认保持 `semi` 模式，人工确认后再进入下一阶段 |
| API Key 泄露 | 只用环境变量，写入 `.gitignore`，绝不在代码中硬编码 |

---

> 📄 本设计文档位置: `D:\noveos\video_breakdown\design_doc_deepseek_kimi.md`  
> 📋 原始视频复刻报告: `D:\noveos\video_breakdown\replication_guide.md`  
> 🔧 下一步: 让我把这些代码文件实际创建到 `D:\vault\content_factory\` 目录下
