"""W6 验收：手写 JSON Schema 子集校验器（独立于实现方 contracts.validate）。

支持：$ref（本文件 #/$defs/x 与 xxx.schema.json#/$defs/y）、type（含数组与 null/integer）、enum、required、
properties、additionalProperties(false/schema)、items、pattern、minLength、minimum、maximum、format=date-time。
pattern 末尾的 $ 按 \\z 处理（Python 用 \\Z，不允许尾随换行）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SCHEMAS = Path(__file__).resolve().parents[2] / "contracts" / "schemas"
_cache: dict[str, dict] = {}
_ISO_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z\Z")


def load(name: str) -> dict:
    if name not in _cache:
        _cache[name] = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    return _cache[name]


def _pattern(p: str) -> re.Pattern:
    if p.endswith("$") and not p.endswith("\\$"):
        p = p[:-1] + "\\Z"
    return re.compile(p)


def _type_ok(t: str, v: Any) -> bool:
    return {
        "object": isinstance(v, dict),
        "array": isinstance(v, list),
        "string": isinstance(v, str),
        "boolean": isinstance(v, bool),
        "null": v is None,
        "integer": isinstance(v, int) and not isinstance(v, bool),
        "number": isinstance(v, (int, float)) and not isinstance(v, bool),
    }[t]


def _resolve(ref: str, base: str) -> tuple[dict, str]:
    file, _, frag = ref.partition("#")
    file = file or base
    node: Any = load(file)
    for part in [p for p in frag.split("/") if p]:
        node = node[part]
    return node, file


def errors(schema: dict, v: Any, base: str, path: str = "$") -> list[str]:
    out: list[str] = []
    if "$ref" in schema:
        sub, f = _resolve(schema["$ref"], base)
        out += errors(sub, v, f, path)
    t = schema.get("type")
    if t is not None:
        ts = t if isinstance(t, list) else [t]
        if not any(_type_ok(x, v) for x in ts):
            return out + [f"{path}: 类型应为 {ts}，实际 {type(v).__name__}"]
    if "enum" in schema and v not in schema["enum"]:
        out.append(f"{path}: {v!r} 不在枚举 {schema['enum']}")
    if isinstance(v, str):
        if "minLength" in schema and len(v) < schema["minLength"]:
            out.append(f"{path}: 长度 < {schema['minLength']}")
        if "pattern" in schema and not _pattern(schema["pattern"]).search(v):
            out.append(f"{path}: 不匹配 {schema['pattern']}")
        if schema.get("format") == "date-time" and not _ISO_Z.match(v):
            out.append(f"{path}: 非 UTC ISO-8601（…Z）")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if "minimum" in schema and v < schema["minimum"]:
            out.append(f"{path}: < minimum")
        if "maximum" in schema and v > schema["maximum"]:
            out.append(f"{path}: > maximum")
    if isinstance(v, dict):
        for k in schema.get("required", []):
            if k not in v:
                out.append(f"{path}: 缺必填 {k}")
        props = schema.get("properties", {})
        ap = schema.get("additionalProperties", True)
        for k, x in v.items():
            if k in props:
                out += errors(props[k], x, base, f"{path}.{k}")
            elif ap is False:
                out.append(f"{path}: 不允许的属性 {k}")
            elif isinstance(ap, dict):
                out += errors(ap, x, base, f"{path}.{k}")
    if isinstance(v, list) and isinstance(schema.get("items"), dict):
        for i, x in enumerate(v):
            out += errors(schema["items"], x, base, f"{path}[{i}]")
    return out


def check(ref: str, v: Any) -> list[str]:
    """ref 形如 'colreg' 或 'colreg#/$defs/check' 或 'common#/$defs/problem'。"""
    name, _, frag = ref.partition("#")
    file = f"{name}.schema.json"
    node, f = _resolve(f"{file}#{frag}", file) if frag else (load(file), file)
    return errors(node, v, f)
