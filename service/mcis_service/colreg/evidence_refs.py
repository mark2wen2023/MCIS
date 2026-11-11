"""证据编号校验：格式按共享 common.schema.json#/$defs/evidenceRef，登记状态按案件证据库（evidence.service）。

W6.1 裁定 5：未登记返回 422 evidence_not_registered。
"""
from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy.orm import Session

from ..common import contracts
from ..common.context import problem
from ..evidence import service as ev


def registered_ids(s: Session, case_id: str) -> set[str]:
    return {e["evidenceId"] for e in ev.list_items(s, case_id)}


def require_registered(s: Session, case_id: str, ids: Iterable[str] | None, *, field: str = "evidenceIds") -> list[str]:
    """返回去重后保持顺序的编号列表；格式不对或未登记一律 422 evidence_not_registered。"""
    out: list[str] = []
    for x in ids or []:
        if x not in out:
            out.append(x)
    if not out:
        return out
    bad_format = [x for x in out if not isinstance(x, str) or contracts.errors("common#/$defs/evidenceRef", x)]
    known = registered_ids(s, case_id)
    missing = [x for x in out if x not in known and x not in bad_format]
    if bad_format or missing:
        raise problem(422, "evidence_not_registered", "证据编号未在本案件登记：" + "、".join(map(str, bad_format + missing)),
                      {"field": field, "unregistered": missing, "badFormat": bad_format})
    return out


def dangling(ids: Iterable[str] | None, known: set[str]) -> list[str]:
    return [x for x in ids or [] if x not in known]


def annotate_links(ids: Iterable[str] | None, known: set[str]) -> list[dict[str, Any]]:
    return [{"evidenceId": x, "registered": x in known} for x in ids or []]
