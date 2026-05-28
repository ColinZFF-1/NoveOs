"""Novel-OS LLM 客户端 —— 统一封装 litellm 调用。"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("novel-os.llm")

# 延迟导入 litellm，避免无网络环境启动时报错
try:
    from litellm import completion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    logger.warning("litellm 未安装，LLM 调用将降级为 MOCK")


@dataclass
class LLMConfig:
    """LLM 调用配置。"""
    model: str = "deepseek-chat"
    api_key: str = ""
    api_base: str = "https://api.deepseek.com/v1"
    temperature: float = 0.7
    max_tokens: int = 8000
    timeout: int = 300

    @classmethod
    def from_env(cls, model: str | None = None) -> "LLMConfig":
        """从环境变量加载配置。"""
        return cls(
            model=model or os.getenv("LLM_MODEL", "deepseek-chat"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            api_base=os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "8000")),
            timeout=int(os.getenv("LLM_TIMEOUT", "300")),
        )

    def validate(self) -> None:
        """校验配置是否可调用。"""
        if not self.api_key:
            raise ValueError(
                "LLM API Key 未设置。请设置环境变量 OPENAI_API_KEY，"
                "或在 book.yaml 中配置 api_key。"
            )
        if not LITELLM_AVAILABLE:
            raise RuntimeError("litellm 未安装。请执行: pip install litellm")


class LLMClient:
    """统一的 LLM 调用客户端。"""

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.cfg = config or LLMConfig.from_env()
        self.cfg.validate()

        # 将 key 和 base 注入环境变量（litellm 通过环境变量读取）
        os.environ["OPENAI_API_KEY"] = self.cfg.api_key
        os.environ["OPENAI_API_BASE"] = self.cfg.api_base

    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> str:
        """调用 LLM，返回生成的文本。

        Args:
            system_prompt: 系统提示（Agent 角色定义）。
            user_prompt: 用户提示（任务指令）。
            temperature: 覆盖默认温度。
            max_tokens: 覆盖默认最大 token。
            timeout: 覆盖默认超时（秒）。

        Returns:
            模型生成的文本。

        Raises:
            RuntimeError: 调用失败或返回空内容。
        """
        model_name = f"openai/{self.cfg.model}"  # litellm 的 OpenAI 兼容格式
        temp = temperature if temperature is not None else self.cfg.temperature
        tokens = max_tokens if max_tokens is not None else self.cfg.max_tokens
        to = timeout if timeout is not None else self.cfg.timeout

        logger.debug(
            "LLM 调用: model=%s, temp=%.2f, max_tokens=%d, timeout=%d",
            model_name, temp, tokens, to,
        )

        try:
            response = completion(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temp,
                max_tokens=tokens,
                timeout=to,
            )
            content = response.choices[0].message.content or ""
            if not content.strip():
                raise ValueError("API 返回空内容")
            return content
        except Exception as exc:
            logger.exception("LLM 调用失败")
            raise RuntimeError(f"LLM 调用失败: {exc}") from exc

    def call_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """调用 LLM 并尝试解析返回内容为 JSON。"""
        text = self.call(system_prompt, user_prompt, temperature, max_tokens)
        import json
        # 尝试提取 markdown 代码块中的 JSON
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
