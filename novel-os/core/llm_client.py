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

    model: str = "deepseek-ai/DeepSeek-V3"
    api_key: str = ""
    api_base: str = "https://api.siliconflow.cn/v1"
    temperature: float = 0.7
    max_tokens: int = 8000
    timeout: int = 300
    reasoning_effort: str = "high"
    thinking_enabled: bool = True

    @classmethod
    def from_env(cls, model: str | None = None) -> "LLMConfig":
        """从环境变量加载配置。"""
        return cls(
            model=model or os.getenv("LLM_MODEL", "deepseek-ai/DeepSeek-V3"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            api_base=os.getenv("OPENAI_API_BASE", "https://api.siliconflow.cn/v1"),
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
    """统一的 LLM 调用客户端（基于 OpenAI SDK，兼容 DeepSeek 等 OpenAI 格式 API）。

    支持：
    - fallback 配置：主 Provider 失败自动切换
    - 按 Agent 分模型：不同 Agent 可走不同模型/Provider（对标 InkOS）
    """

    def __init__(
        self,
        config: LLMConfig | None = None,
        fallback_config: LLMConfig | None = None,
        agent_configs: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.cfg = config or LLMConfig.from_env()
        self.cfg.validate()
        self._client, self._use_openai = self._build_client(self.cfg)

        # Fallback Provider
        self.fallback_cfg = fallback_config
        self._fallback_client = None
        self._fallback_use_openai = False
        if self.fallback_cfg:
            self.fallback_cfg.validate()
            self._fallback_client, self._fallback_use_openai = self._build_client(self.fallback_cfg)

        # ★ 按 Agent 分模型配置（InkOS 对标）
        self.agent_configs: dict[str, LLMConfig] = {}
        if agent_configs:
            for agent_name, cfg_dict in agent_configs.items():
                self.agent_configs[agent_name] = LLMConfig(
                    model=cfg_dict.get("model", self.cfg.model),
                    api_key=cfg_dict.get("api_key", self.cfg.api_key),
                    api_base=cfg_dict.get("api_base", self.cfg.api_base),
                    temperature=cfg_dict.get("temperature", self.cfg.temperature),
                    max_tokens=cfg_dict.get("max_tokens", self.cfg.max_tokens),
                    timeout=cfg_dict.get("timeout", self.cfg.timeout),
                    reasoning_effort=cfg_dict.get("reasoning_effort", self.cfg.reasoning_effort),
                    thinking_enabled=cfg_dict.get("thinking_enabled", self.cfg.thinking_enabled),
                )
                self.agent_configs[agent_name].validate()
                logger.info("[LLMClient] Agent '%s' → model=%s", agent_name, self.agent_configs[agent_name].model)

    @staticmethod
    def _build_client(cfg: LLMConfig):
        """根据配置构建底层客户端，返回 (client, use_openai_flag)。"""
        if OPENAI_SDK_AVAILABLE:
            client = OpenAI(
                api_key=cfg.api_key,
                base_url=cfg.api_base,
                timeout=cfg.timeout,
            )
            return client, True
        else:
            # 降级到 litellm
            os.environ["OPENAI_API_KEY"] = cfg.api_key
            os.environ["OPENAI_API_BASE"] = cfg.api_base
            return None, False

    def _do_call(
        self,
        client,
        cfg: LLMConfig,
        use_openai: bool,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        timeout: int,
    ) -> str:
        """执行一次实际的 LLM 调用。"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # kimi 模型强制 temperature=1（kimi-k2.5 只接受 temperature=1）
        if "kimi" in cfg.model.lower():
            temperature = 1.0

        # DeepSeek V4 thinking mode 参数
        extra_body: dict[str, Any] | None = None
        if cfg.thinking_enabled and cfg.model.startswith("deepseek-v4"):
            extra_body = {"thinking": {"type": "enabled"}}

        if use_openai:
            kwargs: dict[str, Any] = {
                "model": cfg.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timeout": timeout,
            }
            if extra_body:
                kwargs["extra_body"] = extra_body
            response = client.chat.completions.create(**kwargs)
            msg = response.choices[0].message
            content = msg.content or msg.reasoning_content or ""
        else:
            # litellm 降级路径
            import litellm

            litellm.drop_params = True
            response = completion(
                model=f"openai/{cfg.model}",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                reasoning_effort=cfg.reasoning_effort
                if cfg.thinking_enabled and cfg.model.startswith("deepseek-v4")
                else None,
                extra_body=extra_body,
            )
            msg = response.choices[0].message
            content = msg.content or msg.reasoning_content or ""

        # 防御 DeepSeek V4 thinking 内容泄漏到 content
        if "<think>" in content:
            original_len = len(content)
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            logger.warning(
                "LLM 返回内容中包含 <think> 块，已过滤（移除 %d 字符）",
                original_len - len(content),
            )

        # ★ 防御 Qwen3.6 thinking process 泄漏
        think_markers = [
            "Here's a thinking process:",
            "Here's a thinking process",
            "1.  **Analyze User Input:**",
            "1. **Analyze User Input:**",
            "**Thinking Process**",
            "<thinking>",
        ]
        for marker in think_markers:
            if marker in content:
                original_len = len(content)
                idx = content.find(marker)
                if idx >= 0:
                    content = content[:idx].strip()
                    logger.warning(
                        "LLM 返回内容中包含 thinking process（%s），已过滤（移除 %d 字符）",
                        marker[:30], original_len - len(content),
                    )
                break

        # ★ 防御 Kimi 思考过程泄漏（"用户希望我作为..." / "The user wants me to..."）
        # 只在内容以思考过程开头且总长度>100字时触发过滤，避免误伤正常短文
        kimi_think_prefixes = [
            "用户希望我作为", "用户希望我能", "用户要求我", "用户",
            "The user wants me to", "The user asked me to",
            "我来分析", "让我先理解", "让我来", "让我",
            "好的，", "好的。", "好的，我来", "好的，让我",
            "作为", "作为DialogueTuner", "作为Polish", "作为SpotFix",
            "首先，", "第一步", "1. ", "1、",
            "分析当前", "我需要", "我需要先", "我需要根据", "我需要对",
            "明白了，", "了解了，", "OK，", "Okay，", "ok，", "okay，",
            "任务要求", "根据指令", "指令指出", "修正指令",
        ]
        for prefix in kimi_think_prefixes:
            if content.startswith(prefix) and len(content) > 100:
                original_len = len(content)
                # 尝试找到 "---" 分隔线后的正文
                sep_match = re.search(r"\n---+\s*\n", content)
                if sep_match:
                    content = content[sep_match.end():].strip()
                else:
                    # 没有分隔线，尝试找第一个段落结束后的空行+新段落
                    para_match = re.search(r"[。?!]\n\n", content)
                    if para_match:
                        content = content[para_match.end():].strip()
                    else:
                        content = ""
                if content:
                    logger.warning(
                        "LLM 返回内容中包含 Kimi 思考过程（前缀: %s），已过滤（移除 %d 字符）",
                        prefix[:20], original_len - len(content),
                    )
                break

        if not content.strip():
            raise ValueError("API 返回空内容")
        return content

    def call_for_agent(
        self,
        agent_name: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> str:
        """按 Agent 名调用 LLM，自动选择该 Agent 的专属模型配置。

        对标 InkOS: inkos config set-model writer claude-sonnet-4
        """
        agent_cfg = self.agent_configs.get(agent_name)
        if not agent_cfg:
            # 未配置则回退到默认
            return self.call(system_prompt, user_prompt, temperature, max_tokens, timeout)

        # 为 Agent 构建专属客户端
        client, use_openai = self._build_client(agent_cfg)
        temp = temperature if temperature is not None else agent_cfg.temperature
        tokens = max_tokens if max_tokens is not None else agent_cfg.max_tokens
        to = timeout if timeout is not None else agent_cfg.timeout

        logger.info(
            "[LLMClient] Agent '%s' 调用: model=%s, temp=%.2f, max_tokens=%d",
            agent_name, agent_cfg.model, temp, tokens,
        )

        try:
            return self._do_call(
                client, agent_cfg, use_openai,
                system_prompt, user_prompt, temp, tokens, to,
            )
        except Exception as exc:
            logger.warning("Agent '%s' 专属模型调用失败: %s，回退到默认模型", agent_name, exc)
            return self.call(system_prompt, user_prompt, temperature, max_tokens, timeout)

    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> str:
        """调用 LLM，返回生成的文本。支持自动 fallback。

        Args:
            system_prompt: 系统提示（Agent 角色定义）。
            user_prompt: 用户提示（任务指令）。
            temperature: 覆盖默认温度。
            max_tokens: 覆盖默认最大 token。
            timeout: 覆盖默认超时（秒）。

        Returns:
            模型生成的文本。

        Raises:
            RuntimeError: 主 Provider 和 Fallback 都调用失败。
        """
        temp = temperature if temperature is not None else self.cfg.temperature
        tokens = max_tokens if max_tokens is not None else self.cfg.max_tokens
        to = timeout if timeout is not None else self.cfg.timeout

        logger.debug(
            "LLM 调用: model=%s, temp=%.2f, max_tokens=%d, timeout=%d",
            self.cfg.model, temp, tokens, to,
        )

        # 先尝试主 Provider
        try:
            return self._do_call(
                self._client, self.cfg, self._use_openai,
                system_prompt, user_prompt, temp, tokens, to,
            )
        except Exception as primary_exc:
            logger.warning("主 LLM 调用失败: %s", primary_exc)

            # 如果有 fallback，自动切换
            if self._fallback_client is not None:
                logger.info(
                    "切换到 Fallback LLM: %s @ %s",
                    self.fallback_cfg.model, self.fallback_cfg.api_base,
                )
                try:
                    return self._do_call(
                        self._fallback_client, self.fallback_cfg, self._fallback_use_openai,
                        system_prompt, user_prompt, temp, tokens, to,
                    )
                except Exception as fallback_exc:
                    logger.exception("Fallback LLM 也调用失败")
                    raise RuntimeError(
                        f"主 LLM 失败: {primary_exc}; Fallback 也失败: {fallback_exc}"
                    ) from fallback_exc

            logger.exception("LLM 调用失败，且无 Fallback 配置")
            raise RuntimeError(f"LLM 调用失败: {primary_exc}") from primary_exc

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
