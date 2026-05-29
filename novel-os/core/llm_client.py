"""Novel-OS LLM 客户端 —— 统一封装 OpenAI SDK 调用。"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("novel-os.llm")

# 优先使用 OpenAI SDK；回退到 litellm
try:
    from openai import OpenAI
    OPENAI_SDK_AVAILABLE = True
except ImportError:
    OPENAI_SDK_AVAILABLE = False

try:
    from litellm import completion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False


@dataclass
class LLMConfig:
    """LLM 调用配置。"""

    model: str = "deepseek-v4-flash"
    api_key: str = ""
    api_base: str = "https://api.deepseek.com/v1"
    temperature: float = 0.7
    max_tokens: int = 8000
    timeout: int = 300
    reasoning_effort: str = "high"
    thinking_enabled: bool = True

    @classmethod
    def from_env(cls, model: str | None = None) -> "LLMConfig":
        """从环境变量加载配置。"""
        return cls(
            model=model or os.getenv("LLM_MODEL", "deepseek-v4-flash"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            api_base=os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "8000")),
            timeout=int(os.getenv("LLM_TIMEOUT", "300")),
            reasoning_effort=os.getenv("LLM_REASONING_EFFORT", "high"),
            thinking_enabled=os.getenv("LLM_THINKING_ENABLED", "true").lower() == "true",
        )

    def validate(self) -> None:
        """校验配置是否可调用。"""
        if not self.api_key:
            raise ValueError(
                "LLM API Key 未设置。请设置环境变量 OPENAI_API_KEY，"
                "或在 book.yaml 中配置 api_key。"
            )
        if not OPENAI_SDK_AVAILABLE and not LITELLM_AVAILABLE:
            raise RuntimeError(
                "未安装任何 LLM 客户端。请执行: pip install openai"
            )


class LLMClient:
    """统一的 LLM 调用客户端（基于 OpenAI SDK，兼容 DeepSeek 等 OpenAI 格式 API）。"""

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.cfg = config or LLMConfig.from_env()
        self.cfg.validate()

        # 优先使用 OpenAI SDK（避免 litellm 大 max_tokens 下的假超时问题）
        if OPENAI_SDK_AVAILABLE:
            self._client = OpenAI(
                api_key=self.cfg.api_key,
                base_url=self.cfg.api_base,
                timeout=self.cfg.timeout,
            )
            self._use_openai = True
        else:
            # 降级到 litellm
            os.environ["OPENAI_API_KEY"] = self.cfg.api_key
            os.environ["OPENAI_API_BASE"] = self.cfg.api_base
            self._client = None
            self._use_openai = False

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
        temp = temperature if temperature is not None else self.cfg.temperature
        tokens = max_tokens if max_tokens is not None else self.cfg.max_tokens
        to = timeout if timeout is not None else self.cfg.timeout

        logger.debug(
            "LLM 调用: model=%s, temp=%.2f, max_tokens=%d, timeout=%d",
            self.cfg.model, temp, tokens, to,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # DeepSeek V4 thinking mode 参数
        extra_body: dict[str, Any] | None = None
        if self.cfg.thinking_enabled and self.cfg.model.startswith("deepseek-v4"):
            extra_body = {"thinking": {"type": "enabled"}}

        try:
            if self._use_openai:
                kwargs: dict[str, Any] = {
                    "model": self.cfg.model,
                    "messages": messages,
                    "temperature": temp,
                    "max_tokens": tokens,
                    "timeout": to,
                }
                if extra_body:
                    kwargs["extra_body"] = extra_body
                response = self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
            else:
                # litellm 降级路径
                import litellm

                litellm.drop_params = True
                response = completion(
                    model=f"openai/{self.cfg.model}",
                    messages=messages,
                    temperature=temp,
                    max_tokens=tokens,
                    timeout=to,
                    reasoning_effort=self.cfg.reasoning_effort
                    if self.cfg.thinking_enabled and self.cfg.model.startswith("deepseek-v4")
                    else None,
                    extra_body=extra_body,
                )
                content = response.choices[0].message.content or ""

            # 防御 DeepSeek V4 thinking 内容泄漏到 content
            if "<think>" in content:
                original_len = len(content)
                content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
                logger.warning(
                    "LLM 返回内容中包含 <think> 块，已过滤（移除 %d 字符）",
                    original_len - len(content),
                )

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
