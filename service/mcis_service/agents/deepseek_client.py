"""Explicit remote DeepSeek transport; never selected by local-provider configuration.

Only host code may supply credentials. This module does not authorize case-data
transmission, register routes, persist results, or fall back to a fixture.
"""
from dataclasses import dataclass, field
import json
import os

import httpx

from ..common.context import problem

ENDPOINT = 'https://api.deepseek.com/chat/completions'
MODELS = ('deepseek-v4-pro', 'deepseek-flash')
MAX_RESPONSE_BYTES = 256 * 1024
MAX_REQUEST_BYTES = 128 * 1024


@dataclass(frozen=True)
class DeepSeekConfig:
    api_key: str = field(repr=False)
    model: str = 'deepseek-v4-pro'


def validate_config(cfg):
    if (type(cfg) is not DeepSeekConfig or type(cfg.api_key) is not str
            or not 1 <= len(cfg.api_key) <= 4096
            or any(ord(c) < 33 or ord(c) > 126 for c in cfg.api_key)
            or type(cfg.model) is not str or cfg.model not in MODELS):
        raise problem(503, 'DEEPSEEK_CONFIG_INVALID', 'DeepSeek 配置无效')
    return cfg


def config_from_environment():
    """Call only after explicit host selection; never log/serialize the result."""
    key = os.environ.get('DEEPSEEK_API_KEY', '')
    if not key:
        return None
    return validate_config(DeepSeekConfig(key, os.environ.get('DEEPSEEK_MODEL', 'deepseek-v4-pro')))


def complete(cfg, messages):
    cfg = validate_config(cfg)
    try:
        if type(messages) is not list or not 1 <= len(messages) <= 20:
            raise ValueError()
        if any(type(m) is not dict or set(m) != {'role', 'content'}
               or m['role'] not in ('system', 'user', 'assistant')
               or type(m['content']) is not str for m in messages):
            raise ValueError()
        payload = {'model': cfg.model, 'messages': messages, 'stream': False,
                   'thinking': {'type': 'disabled'}, 'max_tokens': 4096,
                   'response_format': {'type': 'json_object'}}
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode('utf-8')
        if len(body) > MAX_REQUEST_BYTES:
            raise ValueError()
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise problem(422, 'DEEPSEEK_INPUT_INVALID', 'DeepSeek 输入格式或大小无效') from None
    try:
        # TLS verification remains enabled. Honor managed runtime proxy/CA settings.
        # No retries, tools, redirects, or caller-supplied destination.
        with httpx.Client(timeout=60, trust_env=True, follow_redirects=False) as client:
            with client.stream('POST', ENDPOINT, content=body, headers={
                'Authorization': 'Bearer ' + cfg.api_key, 'Content-Type': 'application/json',
            }) as response:
                if response.status_code != 200:
                    raise problem(502, 'DEEPSEEK_HTTP_ERROR', 'DeepSeek 返回非成功响应')
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_RESPONSE_BYTES:
                        raise problem(502, 'DEEPSEEK_RESPONSE_TOO_LARGE', 'DeepSeek 响应超过限制')
                    chunks.append(chunk)
                data = json.loads(b''.join(chunks))
        if type(data) is not dict or type(data.get('choices')) is not list or len(data['choices']) != 1:
            raise ValueError()
        choice = data['choices'][0]
        if type(choice) is not dict or type(choice.get('message')) is not dict:
            raise ValueError()
        msg = choice['message']
        if (choice.get('finish_reason') != 'stop' or msg.get('tool_calls')
                or msg.get('function_call') or msg.get('server_tool_calls')):
            raise ValueError()
        content = msg['content']
        if type(content) is not str or not content.strip():
            raise ValueError()
        return content
    except httpx.TimeoutException:
        raise problem(504, 'DEEPSEEK_TIMEOUT', 'DeepSeek 调用超时') from None
    except httpx.HTTPError:
        raise problem(502, 'DEEPSEEK_UNAVAILABLE', '无法连接 DeepSeek') from None
    except (ValueError, KeyError, IndexError, TypeError, UnicodeError, RecursionError):
        raise problem(502, 'DEEPSEEK_OUTPUT_INVALID', 'DeepSeek 响应格式无效') from None
