# ts_cap/utils/openai_chat.py
from __future__ import annotations

import json
import logging
import os
import threading
import time
import re
from pathlib import Path
from typing import Any, Dict, Optional

from openai import OpenAI, APITimeoutError
from pydantic import BaseModel, Field

from ts_cap.core.llm_schemas import HierarchicalCaption

logger = logging.getLogger(__name__)

# --- Provider presets ---
LLM_PRESETS = {
    "deepseek": {
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url_env": "DEEPSEEK_BASE_URL",
        "default_base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-reasoner",
    },
    "linkapi": {
        "api_key_env": "LINKAPI_API_KEY",
        "base_url_env": "LINKAPI_BASE_URL",
        "model_env": "LINKAPI_MODEL",
        "default_base_url": "https://api.linkapi.org/v1/",
        "default_model": "gpt-5",
    },
    "doubao": {
        "api_key_env": "DOUBAO_API_KEY",
        "base_url_env": "DOUBAO_BASE_URL",
        "model_env": "DOUBAO_MODEL",
        "default_base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "default_model": "doubao-seed-1-6-thinking-250715",
    },
    "qwen": {
        "api_key_env": "QWEN_API_KEY",
        "base_url_env": "QWEN_BASE_URL",
        "model_env": "QWEN_MODEL",
        "default_base_url": "https://api.linkapi.org/v1/",
        "default_model": "qwen-plus",
    },
    "qwenlocal": {
        "api_key_env": "QWENLOCAL_API_KEY",
        "base_url_env": "QWENLOCAL_BASE_URL",
        "model_env": "QWENLOCAL_MODEL",
        "default_api_key": "EMPTY",
        "default_base_url": "http://0.0.0.0:9411/v1",
        "default_model": "Qwen/Qwen3-8B",
    },
}


class LLMConfig(BaseModel):
    provider: str = Field(default="linkapi", description="linkapi/deepseek/doubao/qwen")
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    system_prompt: str = "You are a helpful assistant."
    # [修改点1] 将默认超时时间从 120 改为 600 (10分钟)，以容忍 API 的 400s+ 响应
    timeout: int = 600
    max_retries: int = 5
    temperature: float = 0.1


_GLOBAL_CFG: Optional[LLMConfig] = None

# Global concurrency limiter (optional)
_GLOBAL_SEMAPHORE: Optional[threading.Semaphore] = None

# Thread-local client cache
_THREAD_LOCAL = threading.local()
_KEY_ENV_LOADED = False


def _load_project_key_env() -> None:
    global _KEY_ENV_LOADED
    if _KEY_ENV_LOADED:
        return

    key_env_path = Path(__file__).resolve().parents[2] / "key.env"
    if not key_env_path.is_file():
        _KEY_ENV_LOADED = True
        return

    for raw_line in key_env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        os.environ.setdefault(key, value)

    _KEY_ENV_LOADED = True


def configure_global_client(cfg: LLMConfig) -> None:
    global _GLOBAL_CFG
    _GLOBAL_CFG = cfg


def configure_global_concurrency(max_concurrency: Optional[int]) -> None:
    """
    Limit total concurrent LLM requests across all threads.
    If None: disable limiter.
    """
    global _GLOBAL_SEMAPHORE
    if max_concurrency is None:
        _GLOBAL_SEMAPHORE = None
        return
    n = int(max_concurrency)
    if n <= 0:
        _GLOBAL_SEMAPHORE = None
        return
    _GLOBAL_SEMAPHORE = threading.Semaphore(n)


def get_thread_local_client() -> "OpenAIChatClient":
    """
    One OpenAIChatClient per thread to reduce overhead and avoid thread-safety issues
    with shared http sessions.
    """
    cli = getattr(_THREAD_LOCAL, "client", None)
    if cli is None:
        cli = OpenAIChatClient()
        _THREAD_LOCAL.client = cli
    return cli


class OpenAIChatClient:
    def __init__(self, config: Optional[LLMConfig] = None, system_prompt: Optional[str] = None):
        _load_project_key_env()
        self.cfg = config or _GLOBAL_CFG or LLMConfig()

        provider = (self.cfg.provider or "linkapi").lower()

        final_api_key = self.cfg.api_key
        final_base_url = self.cfg.base_url
        final_model = self.cfg.model

        if provider in LLM_PRESETS:
            preset = LLM_PRESETS[provider]
            logger.debug(f"[LLM] Using preset provider={provider}")

            if not final_api_key:
                api_key_env = preset.get("api_key_env")
                if api_key_env:
                    final_api_key = os.environ.get(api_key_env)
                if not final_api_key:
                    final_api_key = preset.get("default_api_key")
            if not final_base_url:
                base_url_env = preset.get("base_url_env")
                if base_url_env:
                    final_base_url = os.environ.get(base_url_env)
                if not final_base_url:
                    final_base_url = preset.get("default_base_url")
            if not final_model:
                model_env = preset.get("model_env")
                if model_env:
                    final_model = os.environ.get(model_env)
                if not final_model:
                    final_model = preset["default_model"]
        else:
            if not final_api_key:
                final_api_key = os.environ.get("OPENAI_API_KEY")
            if not final_base_url:
                final_base_url = os.environ.get("OPENAI_BASE_URL")

        self.cfg.model = final_model or "gpt-4o-mini"
        self.cfg.system_prompt = system_prompt or self.cfg.system_prompt

        if not final_api_key:
            raise ValueError(f"Missing API Key. Provider '{provider}' not found in presets and no env var set.")

        self._client = OpenAI(api_key=final_api_key, base_url=final_base_url)

    def _acquire(self) -> None:
        if _GLOBAL_SEMAPHORE is not None:
            _GLOBAL_SEMAPHORE.acquire()

    def _release(self) -> None:
        if _GLOBAL_SEMAPHORE is not None:
            _GLOBAL_SEMAPHORE.release()
            
    def _clean_json_content(self, content: str) -> str:
        """
        [新增] 强力清洗 LLM 返回的 JSON 字符串
        去掉 Markdown 代码块标记，去掉首尾无关字符
        """
        content = content.strip()
        # 去掉 ```json 和 ```
        if content.startswith("```"):
            content = re.sub(r"^```(json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        
        content = content.strip()
        
        # 尝试找到第一个 { 和最后一个 }
        # 防止模型在 JSON 前后说废话 (例如 "Here is the json: { ... }")
        idx_start = content.find("{")
        idx_end = content.rfind("}")
        if idx_start != -1 and idx_end != -1:
            content = content[idx_start : idx_end + 1]
            
        return content
    
    def _extract_message_text(self, resp) -> str:
        """
        兼容 OpenAI-compatible 服务的多种字段：
        - content（常规）
        - reasoning（vLLM 推理输出字段）
        - reasoning_content（旧字段/部分实现）
        """
        try:
            choice0 = resp.choices[0]
            msg = choice0.message
        except Exception:
            return ""

        # openai python SDK 的 message 是 pydantic 对象，额外字段可用 model_dump() 拿到
        md = {}
        try:
            md = msg.model_dump()
        except Exception:
            pass

        for k in ("content", "reasoning", "reasoning_content"):
            v = md.get(k, None)
            if isinstance(v, str) and v.strip():
                return v

        # 兜底：有些实现可能把内容塞在别的层级
        v = getattr(msg, "content", None)
        if isinstance(v, str) and v.strip():
            return v

        return ""
    
    def _extract_text_anywhere(self, resp) -> str:
        """兼容 ms-swift / OpenAI-compatible：content 可能为空，答案在 reasoning_content 里"""
        try:
            choice0 = resp.choices[0]
            msg = choice0.message
        except Exception:
            return ""

        # pydantic v2: model_dump() 能拿到 reasoning_content 等扩展字段
        md = {}
        try:
            md = msg.model_dump()
        except Exception:
            md = {}

        # 有些 SDK 会把扩展字段放在 model_extra / __pydantic_extra__
        extra = getattr(msg, "model_extra", None) or getattr(msg, "__pydantic_extra__", None)
        if isinstance(extra, dict):
            md = {**md, **extra}

        def norm(v):
            if v is None:
                return ""
            if isinstance(v, str):
                return v.strip()
            if isinstance(v, list):
                # content parts: [{"type":"text","text":"..."}]
                out = []
                for p in v:
                    if isinstance(p, dict) and isinstance(p.get("text"), str):
                        out.append(p["text"])
                    elif isinstance(p, str):
                        out.append(p)
                return "".join(out).strip()
            return str(v).strip()

        # 1) 正常 content
        txt = norm(md.get("content"))
        if txt:
            return txt

        # 2) ms-swift 的 reasoning_content / reasoning
        for k in ("reasoning_content", "reasoning"):
            txt = norm(md.get(k))
            if txt:
                return txt

        # 3) 可选：tool_calls arguments
        tool_calls = md.get("tool_calls")
        if isinstance(tool_calls, list) and tool_calls:
            tc0 = tool_calls[0]
            if isinstance(tc0, dict):
                fn = tc0.get("function") or {}
                txt = norm(fn.get("arguments"))
                if txt:
                    return txt

        return ""


    def chat_json(self, user_prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        A generic JSON-mode chat helper.
        Returns parsed dict or raises after retries.
        """
        sys_p = system_prompt or self.cfg.system_prompt
        messages = [{"role": "system", "content": sys_p}, {"role": "user", "content": user_prompt}]

        retries = 0
        while retries <= self.cfg.max_retries:
            try:
                self._acquire()
                kwargs: Dict[str, Any] = {
                    "model": self.cfg.model,
                    "messages": messages,
                    "response_format": {"type": "json_object"},
                    "timeout": self.cfg.timeout,
                    "max_tokens":4096,
                    "extra_body":{"chat_template_kwargs": {"enable_thinking": False}},
                }
                # DeepSeek-reasoner / some reasoning models may not support temperature
                if "reasoner" not in (self.cfg.model or ""):
                    kwargs["temperature"] = self.cfg.temperature

                resp = self._client.chat.completions.create(**kwargs)
                content = self._extract_message_text(resp)
                if not content:
                    # 建议把 finish_reason / message dump 打出来，方便确认到底返回了什么
                    try:
                        logger.error(f"[LLM] Empty extracted text. finish_reason={resp.choices[0].finish_reason}, message={resp.choices[0].message.model_dump()}")
                    except Exception:
                        pass
                    raise ValueError("Empty response from LLM")

            except Exception as e:
                retries += 1
                if retries > self.cfg.max_retries:
                    logger.error(f"[LLM] chat_json failed after max retries: {e}")
                    raise

                # [修改点2] 优化退避策略，如果是超时，增加等待时间
                # 增加等待上限到 60s (原为 10s)，以应对拥堵的后端
                wait_time = min(60, 2**retries) 
                
                # 如果是明确的超时错误，日志提示更清晰
                if isinstance(e, APITimeoutError):
                     logger.warning(f"[LLM] TIMEOUT limit={self.cfg.timeout}s (attempt {retries}): {e}. Retrying in {wait_time}s...")
                else:
                     logger.warning(f"[LLM] Error (attempt {retries}): {e}. Retrying in {wait_time}s...")
                
                time.sleep(wait_time)
            finally:
                self._release()

        raise RuntimeError("Unreachable")

    def generate_structured_caption(self, user_prompt: str, system_prompt: str) -> Optional[HierarchicalCaption]:
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]

        retries = 0
        while retries <= self.cfg.max_retries:
            try:
                self._acquire()
                kwargs: Dict[str, Any] = {
                    "model": self.cfg.model,
                    "messages": messages,
                    "response_format": {"type": "json_object"},
                    "timeout": self.cfg.timeout,
                    "max_tokens":4096,
                    "extra_body":{"chat_template_kwargs": {"enable_thinking": False}},
                }
                if "reasoner" not in (self.cfg.model or ""):
                    kwargs["temperature"] = self.cfg.temperature

                response = self._client.chat.completions.create(**kwargs)
                content = self._extract_text_anywhere(response)
                
                if not content:
                    raise ValueError("Empty response from LLM")

                # [关键修改] 先清洗，再解析，且捕获解析错误打印原始内容
                cleaned_content = self._clean_json_content(content)
                
                try:
                    data = json.loads(cleaned_content)
                except json.JSONDecodeError as e:
                    # [DEBUG] 解析失败时，打印原始内容的前200个字符，方便排查
                    logger.error(f"[LLM] JSON Decode Error! Raw preview: {content[:200]}...")
                    raise e # 抛出异常以触发重试

                return HierarchicalCaption(**data)

            except Exception as e:
                retries += 1
                if retries > self.cfg.max_retries:
                    logger.error(f"[LLM] FAILED after {self.cfg.max_retries} retries. Cause: {e}")
                    return None

                wait_time = min(60, 2**retries)
                err_type = "TIMEOUT" if isinstance(e, APITimeoutError) else "Error"
                
                # 如果是 JSON 错误，日志里会显示 Raw preview，如果是网络错误则显示网络信息
                logger.warning(f"[LLM] {err_type} (attempt {retries}/{self.cfg.max_retries}): {e}. Retry in {wait_time}s...")
                
                time.sleep(wait_time)
            finally:
                self._release()

        return None
