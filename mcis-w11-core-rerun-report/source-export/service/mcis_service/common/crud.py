"""文档型实体的小工具：编号分配、差异摘要。"""
from __future__ import annotations

import json
import re
from typing import Any


def next_key(existing: list[str], prefix: str, width: int = 2) -> str:
    nums = [int(m.group(1)) for k in existing if (m := re.match(re.escape(prefix) + r"(\d+)$", k))]
    return f"{prefix}{(max(nums) + 1 if nums else 1):0{width}d}"


def diff_summary(before: dict[str, Any], after: dict[str, Any], keys: list[str] | None = None) -> tuple[str, str]:
    keys = keys or sorted(set(before) | set(after))
    b = {k: before.get(k) for k in keys if before.get(k) != after.get(k)}
    a = {k: after.get(k) for k in keys if before.get(k) != after.get(k)}
    dump = lambda d: json.dumps(d, ensure_ascii=False, sort_keys=True)
    return dump(b), dump(a)
