"""Single-attempt fixed DeepSeek transport. No credential discovery or logging.

Caller owns approval, disclosure binding and persistent pre-dispatch reservation.
This module makes no authenticity claim and must not be enabled implicitly.
"""
import asyncio
import json
import math
import time
import httpx
from research.expert_group.engine import _assistant

ENDPOINT = 'https://api.deepseek.com/chat/completions'
MODEL = 'deepseek-v4-pro'
MAX_BYTES = 262144


class TransportError(ValueError):
    def __init__(self, code, dispatched=False):
        self.code = code
        self.dispatched = dispatched
        super().__init__(code)


def _unknown():
    return {'status': 'unknown', 'value': None}


def _text_meta(value):
    if isinstance(value, str) and value and len(value) <= 256:
        return {'status': 'observed', 'value': value}
    return _unknown()


def _usage(value):
    if type(value) is not dict:
        return _unknown()
    fields = {}
    for name in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
        n = value.get(name)
        fields[name] = {'status': 'observed', 'value': n} if type(n) is int and 0 <= n <= 2**53-1 else _unknown()
    if all(v['status'] == 'unknown' for v in fields.values()):
        return _unknown()
    return {'status': 'observed', 'value': fields}


def _decode(raw, credential=None):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out: raise ValueError('duplicate')
            out[key] = value
        return out
    obj = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                     parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))
    # Reject the exact credential after JSON unescaping, including nested keys.
    # This is a narrow no-echo boundary, not a detector for transformed secrets
    # or the raw Vault secret unavailable to a placeholder-only process.
    if credential:
        pending = [obj]
        while pending:
            value = pending.pop()
            if isinstance(value, str) and credential in value:
                raise ValueError('credential_echo')
            if isinstance(value, dict):
                pending.extend(value.keys()); pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)
    if type(obj) is not dict or type(obj.get('choices')) is not list or len(obj['choices']) != 1:
        raise ValueError('response_shape')
    choice = obj['choices'][0]
    if type(choice) is not dict or choice.get('finish_reason') not in ('stop', 'tool_calls'):
        raise ValueError('response_incomplete')
    assistant = choice.get('message')
    if type(assistant) is not dict or assistant.get('role') != 'assistant':
        raise ValueError('response_shape')
    assistant, pending = _assistant(assistant)
    if (choice['finish_reason'] == 'tool_calls') != bool(pending):
        raise ValueError('response_incomplete')
    # Re-encoding rejects unpaired surrogate escapes and non-finite nested values.
    json.dumps(obj, ensure_ascii=False, allow_nan=False).encode('utf-8')
    return {'assistant': assistant,
            'responseMeta': {'id': _text_meta(obj.get('id')), 'model': _text_meta(obj.get('model')),
                             'usage': _usage(obj.get('usage'))},
            'identityVerified': False}


async def request(messages, tools, *, key, deadline, cancel=None, managed_binding=None):
    """Return one bounded non-stream response; deadline is absolute monotonic time.

    Error.dispatched conservatively means dispatch may have begun, NOT that the
    provider received or charged the request. No retry/redirect occurs. Caller
    must preserve unknown outcomes and never refund dispatch attempts here.
    cancel is a cheap synchronous predicate; callback failure also fails closed.
    """
    dispatched = False
    task = None
    try:
        if ENDPOINT != 'https://api.deepseek.com/chat/completions':
            raise TransportError('endpoint_invalid')
        options = {}
        headers = {'Content-Type':'application/json','Accept':'application/json','Accept-Encoding':'identity'}
        if managed_binding is not None:
            if key is not None or ENDPOINT != 'https://api.deepseek.com/chat/completions': raise TransportError('managed_mode_invalid')
            from research.expert_remote.managed import resolve
            material=resolve(managed_binding)
            options={'proxy':httpx.Proxy(material.proxy,ssl_context=material.context),'verify':material.context}
        else:
            if type(key) is not str or not key or len(key) > 8192 or any(ord(c) < 33 or ord(c) > 126 for c in key):
                raise TransportError('credential_invalid')
            headers['Authorization']='Bearer '+key
        if type(deadline) not in (int, float) or not math.isfinite(deadline):
            raise TransportError('deadline_invalid')
        if cancel is not None and cancel(): raise TransportError('cancelled')
        remaining = deadline - time.monotonic()
        if remaining <= 0: raise TransportError('deadline')
        if type(messages) is not list or not messages or type(tools) is not list:
            raise TransportError('request_invalid')
        try:
            body = json.dumps({'model': MODEL, 'messages': messages, 'tools': tools,
                               'max_tokens': 2400, 'stream': False}, ensure_ascii=False,
                              allow_nan=False, separators=(',', ':')).encode('utf-8')
        except Exception:
            raise TransportError('request_invalid') from None
        if len(body) > MAX_BYTES: raise TransportError('request_limit')

        async def send():
            nonlocal dispatched
            async with httpx.AsyncClient(trust_env=False, follow_redirects=False,
                                         timeout=httpx.Timeout(max(.001, deadline-time.monotonic())), **options) as client:
                if cancel is not None and cancel(): raise TransportError('cancelled')
                if time.monotonic() >= deadline: raise TransportError('deadline')
                dispatched = True
                async with client.stream('POST', ENDPOINT, content=body,
                                         headers=headers) as response:
                    if response.status_code != 200: raise TransportError('http_rejected', True)
                    if response.headers.get('content-encoding', 'identity').lower() != 'identity':
                        raise TransportError('response_encoding', True)
                    length = response.headers.get('content-length')
                    if length is not None and (not length.isdecimal() or int(length) > MAX_BYTES):
                        raise TransportError('response_limit', True)
                    chunks = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=16384):
                        if len(chunks)+len(chunk) > MAX_BYTES: raise TransportError('response_limit', True)
                        chunks.extend(chunk)
                    try:
                        return _decode(bytes(chunks), credential=key)
                    except Exception:
                        raise TransportError('response_invalid', True) from None

        async with asyncio.timeout(max(.001, deadline-time.monotonic())):
            task = asyncio.create_task(send())
            while not task.done():
                if cancel is not None and cancel(): raise TransportError('cancelled', dispatched)
                await asyncio.wait({task}, timeout=min(.05, max(.001, deadline-time.monotonic())))
            if cancel is not None and cancel(): raise TransportError('cancelled', dispatched)
            if time.monotonic() >= deadline: raise TransportError('deadline', dispatched)
            return await task
    except asyncio.CancelledError:
        raise TransportError('cancelled', dispatched) from None
    except TimeoutError:
        raise TransportError('deadline', dispatched) from None
    except TransportError:
        raise
    except Exception:
        raise TransportError('transport_failed', dispatched) from None
    finally:
        if task is not None:
            if not task.done(): task.cancel()
            try: await task
            except (Exception, asyncio.CancelledError): pass


def validate_meta(meta):
    """Reject malformed stored metadata; does not authenticate provider fields."""
    def require(condition):
        if not condition: raise TransportError('metadata_invalid')
    def envelope(value):
        require(type(value) is dict and set(value) == {'status', 'value'})
        require(value['status'] in ('observed', 'unknown'))
        if value['status'] == 'unknown': require(value['value'] is None)
        return value['status'] == 'observed'
    require(type(meta) is dict and set(meta) == {'id', 'model', 'usage'})
    for name in ('id', 'model'):
        if envelope(meta[name]):
            require(type(meta[name]['value']) is str and 0 < len(meta[name]['value']) <= 256)
    if envelope(meta['usage']):
        fields = meta['usage']['value']
        require(type(fields) is dict and set(fields) == {'prompt_tokens', 'completion_tokens', 'total_tokens'})
        observed = False
        for field in fields.values():
            if envelope(field):
                require(type(field['value']) is int and 0 <= field['value'] <= 2**53-1)
                observed = True
        require(observed)
