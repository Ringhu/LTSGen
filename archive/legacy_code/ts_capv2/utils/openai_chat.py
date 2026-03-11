# ts_capv2/utils/openai_chat.py
from __future__ import annotations

import json
import logging
import os
import random
import re
import time
from typing import Any, Dict, Optional, Union

from openai import OpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# -------------------------
# Configuration via Pydantic
# -------------------------
class LLMConfig(BaseModel):
    provider: str = Field(default="openai", description="LLM provider: openai/linkapi/deepseek/...")
    model: Optional[str] = Field(default=None, description="Model name")
    api_key: Optional[str] = Field(default=None, description="API Key")
    base_url: Optional[str] = Field(default=None, description="Base URL")
    
    system_prompt: str = "You are a careful assistant. Follow instructions strictly."
    timeout: int = 180
    max_retries: int = 10
    temperature: float = 0.0
    
    # New: Context window safety
    max_context_chars: int = 12000  # Truncate input context to roughly 3-4k tokens

_GLOBAL_CFG: Optional[LLMConfig] = None

def configure_global_client(cfg: LLMConfig) -> None:
    global _GLOBAL_CFG
    _GLOBAL_CFG = cfg

# -------------------------
# Provider defaults
# -------------------------
_PROVIDER_DEFAULTS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "base_url_env": "OPENAI_BASE_URL",
        "model_env": "OPENAI_MODEL",
        "default_model": "gpt-4o-mini",
        "supports_json_mode": True,
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url_env": "DEEPSEEK_BASE_URL",
        "model_env": "DEEPSEEK_MODEL",
        "default_model": "deepseek-chat",
        "supports_json_mode": True,
    },
    # Add others as needed...
}

def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name)
    if v is None or str(v).strip() == "":
        return default
    return v

def _strip_code_fence(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()

def _truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...(truncated due to length limit)"

class OpenAIChatClient:
    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        # Backward compatibility args
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        # Resolve config: Argument > Global > Default
        base_cfg = config or _GLOBAL_CFG or LLMConfig()
        
        # Override if specific args passed
        if model: base_cfg.model = model
        if system_prompt: base_cfg.system_prompt = system_prompt

        self.cfg = base_cfg
        
        provider_key = self.cfg.provider.lower()
        p_defaults = _PROVIDER_DEFAULTS.get(provider_key, {})
        
        # Resolve credentials
        api_key = self.cfg.api_key or _env(p_defaults.get("api_key_env", "OPENAI_API_KEY"))
        base_url = self.cfg.base_url or _env(p_defaults.get("base_url_env", "OPENAI_BASE_URL"), p_defaults.get("base_url"))
        self.model = self.cfg.model or _env(p_defaults.get("model_env"), p_defaults.get("default_model"))
        
        if not api_key:
             # Just a warning here, might fail later
             logger.warning(f"[LLM] No API key found for provider {provider_key}")

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self.supports_json_mode = p_defaults.get("supports_json_mode", False)

    def chat_text(self, *, user_prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        sys_p = system_prompt if system_prompt is not None else self.cfg.system_prompt
        timeout_cnt = 0
        
        while True:
            if timeout_cnt > self.cfg.max_retries:
                raise RuntimeError(f"LLM API failed after {self.cfg.max_retries} retries.")
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": sys_p},
                        {"role": "user", "content": user_prompt},
                    ],
                    timeout=self.cfg.timeout,
                    temperature=self.cfg.temperature,
                )
                break
            except Exception as e:
                timeout_cnt += 1
                sleep_s = min(8.0, 0.5 * (2 ** min(timeout_cnt, 4))) + random.random() * 0.2
                logger.warning(f"[LLM] API error (attempt {timeout_cnt}): {e}. Retrying in {sleep_s:.2f}s...")
                time.sleep(sleep_s)

        msg = resp.choices[0].message
        content = (getattr(msg, "content", "") or "").strip()
        usage = {}
        if resp.usage:
            usage = {
                "prompt_tokens": resp.usage.prompt_tokens,
                "completion_tokens": resp.usage.completion_tokens,
                "total_tokens": resp.usage.total_tokens,
            }
        return {"content": content, "token_usage": usage}

    def chat_json(self, *, user_prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Force JSON output. Uses 'json_object' mode if supported, otherwise pure prompting.
        """
        sys_p = system_prompt if system_prompt is not None else self.cfg.system_prompt
        # Instructions for JSON
        if "json" not in sys_p.lower() and "json" not in user_prompt.lower():
             user_prompt += "\n\nIMPORTANT: Output valid JSON only."

        # Use native JSON mode if available
        kwargs = {}
        if self.supports_json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        timeout_cnt = 0
        while True:
            if timeout_cnt > self.cfg.max_retries:
                 raise RuntimeError(f"LLM API failed after {self.cfg.max_retries} retries.")
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": sys_p},
                        {"role": "user", "content": user_prompt},
                    ],
                    timeout=self.cfg.timeout,
                    temperature=self.cfg.temperature,
                    **kwargs
                )
                break
            except Exception as e:
                timeout_cnt += 1
                sleep_s = min(8.0, 0.5 * (2 ** min(timeout_cnt, 4))) + random.random() * 0.2
                logger.warning(f"[LLM] API error (attempt {timeout_cnt}): {e}")
                time.sleep(sleep_s)

        content = resp.choices[0].message.content or ""
        # Parse
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Fallback cleanup
            clean = _strip_code_fence(content)
            try:
                return json.loads(clean)
            except json.JSONDecodeError:
                raise ValueError(f"Failed to parse JSON from LLM output:\n{content}")

def enhance_caption_hook(payload: Dict[str, Any]) -> str:
    """
    Hook to enhance caption using LLM.
    Includes Context Truncation to save tokens.
    """
    # 1. Get Global Config
    cfg = _GLOBAL_CFG or LLMConfig()
    client = OpenAIChatClient(config=cfg)

    # 2. Extract Data
    cap = (
        payload.get("base_caption")
        or payload.get("caption")
        or ""
    )
    if isinstance(cap, dict):
        cap = cap.get("zh") or cap.get("text") or ""
        
    dataset_name = payload.get("dataset", "Unknown")
    
    # 3. Handle Domain Context (Token Saving)
    raw_context = payload.get("domain_context", "")
    context_str = ""
    if isinstance(raw_context, (dict, list)):
        context_str = json.dumps(raw_context, ensure_ascii=False)
    else:
        context_str = str(raw_context)
    
    # *** TRUNCATION ***
    context_str = _truncate_text(context_str, cfg.max_context_chars)

    # 4. Construct Prompt
    user_prompt = f"""
任务：润色时间序列描述。
背景信息 (参考用，勿过度复述):
数据集: {dataset_name}
上下文: {context_str}

原始描述:
{cap}

要求：
1. 改写为流畅、专业的中文。
2. 绝对【禁止修改】原始描述中的任何数值、趋势判断或统计结论。
3. 仅输出润色后的文本，不要包含 "好的" 或 Markdown 标记。
"""
    out = client.chat_text(user_prompt=user_prompt)
    return out["content"]