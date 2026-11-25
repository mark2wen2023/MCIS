"""与 C# SimpleJson / AuditJson 逐字节一致的 JSON 字符串转义与行构造。

C# 规则：\\ \" \n \r \t 转义；其他 <0x20 的字符写成 \\u00xx（小写）；其余字符（含中文）原样输出。
Python json.dumps 对 \b \f 的处理不同，所以这里自己实现。
"""
from __future__ import annotations

import hashlib

ZERO_HASH = "0" * 64


def escape(s: str | None) -> str:
    if s is None:
        return ""
    out = []
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ord(ch) < 32:
            out.append("\\u%04x" % ord(ch))
        else:
            out.append(ch)
    return "".join(out)


def quote(s: str | None) -> str:
    return '"' + escape(s or "") + '"'


def flat_line(pairs: list[tuple[str, object]]) -> str:
    """按给定顺序构造扁平 JSON 对象行。值可以是 str / int / bool。"""
    parts = []
    for k, v in pairs:
        if isinstance(v, bool):
            val = "true" if v else "false"
        elif isinstance(v, int):
            val = str(v)
        else:
            val = quote(None if v is None else str(v))
        parts.append(quote(k) + ":" + val)
    return "{" + ",".join(parts) + "}"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_utf8(text: str) -> str:
    return sha256_hex(text.encode("utf-8"))
