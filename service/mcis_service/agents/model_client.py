"""Opt-in local OpenAI-compatible transport. No secrets, proxies or remote endpoints."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from ..common.context import problem

MAX_RESPONSE_BYTES = 256 * 1024


@dataclass(frozen=True)
class ModelConfig:
    base_url: str
    model: str


def validate_config(cfg: ModelConfig) -> ModelConfig:
    try:
        if type(cfg) is not ModelConfig or type(cfg.base_url) is not str or type(cfg.model) is not str:raise ValueError()
        base,model=cfg.base_url,cfg.model
        if any(c.isspace() or ord(c)<32 or ord(c)==127 or c=='\\' for c in base):raise ValueError()
        url=urlsplit(base)
        if '?' in base or '#' in base or '@' in url.netloc:raise ValueError()
        valid=(url.scheme=='http' and url.hostname in ('127.0.0.1','::1')
            and url.port is not None and 1<=url.port<=65535 and not url.username and not url.password
            and not url.query and not url.fragment and url.path in ('/v1','/v1/')
            and 0<len(model)<=200 and bool(model.strip()) and all(ord(c)>=32 and ord(c)!=127 for c in model))
        if not valid:raise ValueError()
    except (ValueError,TypeError,AttributeError):
        raise problem(503,'MODEL_CONFIG_INVALID','仅支持显式本机模型配置') from None
    return ModelConfig(base.rstrip('/'),model)


def config() -> ModelConfig | None:
    base=os.environ.get('MCIS_AGENT_BASE_URL','')
    model=os.environ.get('MCIS_AGENT_MODEL','')
    if not base and not model:return None
    return validate_config(ModelConfig(base,model))


def complete(cfg: ModelConfig, messages: list[dict[str, str]]) -> str:
    cfg=validate_config(cfg)
    try:
        # No redirects, retries or environment proxies: one explicit local inference only.
        with httpx.Client(timeout=30, trust_env=False, follow_redirects=False) as client:
            with client.stream("POST", cfg.base_url + "/chat/completions", json={
                "model": cfg.model, "messages": messages, "temperature": 0,
                "max_tokens": 4096, "stream": False, "response_format": {"type": "json_object"},
            }) as response:
                if response.status_code != 200:
                    raise problem(502, "MODEL_HTTP_ERROR", "本地模型返回非成功响应")
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_RESPONSE_BYTES:
                        raise problem(502, "MODEL_RESPONSE_TOO_LARGE", "本地模型响应超过限制")
                    chunks.append(chunk)
                data = json.loads(b"".join(chunks))
        choice = data["choices"][0]
        if choice.get("finish_reason") != "stop":
            raise problem(502, "MODEL_INCOMPLETE", "本地模型未完整生成结果")
        msg = choice["message"]
        if msg.get("tool_calls") or msg.get("function_call"):
            raise problem(502, "MODEL_OUTPUT_INVALID", "不接受模型工具调用")
        content = msg["content"]
        if not isinstance(content, str):
            raise ValueError()
        return content
    except httpx.TimeoutException:
        raise problem(504, "MODEL_TIMEOUT", "本地模型调用超时") from None
    except httpx.HTTPError:
        raise problem(502, "MODEL_UNAVAILABLE", "无法连接本地模型") from None
    except (ValueError, KeyError, IndexError, TypeError, RecursionError):
        raise problem(502, "MODEL_OUTPUT_INVALID", "本地模型响应格式不合法") from None

