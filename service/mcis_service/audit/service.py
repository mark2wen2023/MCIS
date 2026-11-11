"""审计：所有写操作都调用 append()。行格式兼容 C# AuditRecord.ToJsonLine（7 个标准键）+ snake_case 扩展键。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..common.csjson import ZERO_HASH, flat_line, sha256_utf8
from ..common.timeutil import iso, now_utc, parse_iso
from ..db import WRITE_LOCK
from .models import AuditEventRow


def _summ(v: Any, limit: int = 400) -> str:
    if v is None:
        return ""
    s = v if isinstance(v, str) else str(v)
    return s if len(s) <= limit else s[: limit - 1] + "…"


def build_line(*, utc: str, operator: str, action: str, category: str, command: str, before: str, after: str,
               seq: int, role: str, entity_type: str, entity_id: str, prev: str, reason: str | None = None) -> str:
    pairs: list[tuple[str, object]] = [
        ("utc", utc), ("operator", operator), ("action", action), ("category", category),
        ("command", command), ("before", before), ("after", after),
        ("seq", seq), ("role", role), ("entity_type", entity_type), ("entity_id", entity_id), ("prev", prev),
    ]
    if reason is not None:
        # 扩展键：理由全文（不截断），进入哈希链；C# AuditLog.ReadAll 忽略扩展键
        pairs.append(("reason", reason))
    return flat_line(pairs)


def append(s: Session, *, case_id: str, operator: str, role: str, action: str, category: str, command: str,
           before: Any = "", after: Any = "", entity_type: str = "", entity_id: str = "",
           utc: datetime | str | None = None, reason: str | None = None) -> AuditEventRow:
    with WRITE_LOCK:
        last = s.scalars(select(AuditEventRow).where(AuditEventRow.case_id == case_id)
                         .order_by(AuditEventRow.seq.desc()).limit(1)).first()
        seq = (last.seq + 1) if last else 1
        prev = sha256_utf8(last.line) if last else ZERO_HASH
        if utc is None:
            utc_s = iso(now_utc())
        elif isinstance(utc, str):
            utc_s = iso(parse_iso(utc))
        else:
            utc_s = iso(utc)
        b, a = _summ(before), _summ(after)
        line = build_line(utc=utc_s, operator=operator, action=action, category=category, command=command,
                          before=b, after=a, seq=seq, role=role, entity_type=entity_type, entity_id=entity_id, prev=prev,
                          reason=reason)
        row = AuditEventRow(case_id=case_id, seq=seq, utc=utc_s, operator=operator, role=role, action=action,
                            category=category, command=command, before=b, after=a, entity_type=entity_type,
                            entity_id=entity_id, prev_hash=prev, line=line)
        s.add(row)
        s.flush()
        return row


def append_raw_line(s: Session, case_id: str, rec: dict[str, Any], line: str, seq: int, prev: str) -> None:
    """导入 .mcase 时按原文保留审计行。"""
    s.add(AuditEventRow(case_id=case_id, seq=seq, utc=rec.get("utc", ""), operator=rec.get("operator", ""),
                        role=rec.get("role", ""), action=rec.get("action", ""), category=rec.get("category", ""),
                        command=rec.get("command", ""), before=rec.get("before", ""), after=rec.get("after", ""),
                        entity_type=rec.get("entity_type", ""), entity_id=rec.get("entity_id", ""),
                        prev_hash=prev, line=line))
    s.flush()


def to_doc(r: AuditEventRow) -> dict[str, Any]:
    return {"seq": r.seq, "caseId": r.case_id, "utc": r.utc, "operator": r.operator, "role": r.role or "Investigator",
            "action": r.action, "category": r.category, "command": r.command, "before": r.before, "after": r.after,
            "entityType": r.entity_type, "entityId": r.entity_id, "prevHash": r.prev_hash, "line": r.line}


def list_events(s: Session, case_id: str, *, category: str | None = None, entity_id: str | None = None,
                action: str | None = None, entity_type: str | None = None, after_seq: int = 0, limit: int = 200, newest_first: bool = False) -> list[dict[str, Any]]:
    q = select(AuditEventRow).where(AuditEventRow.case_id == case_id, AuditEventRow.seq > after_seq)
    if category:
        q = q.where(AuditEventRow.category == category)
    if entity_id:
        q = q.where(AuditEventRow.entity_id == entity_id)
    if action:
        q = q.where(AuditEventRow.action == action)
    if entity_type:
        q = q.where(AuditEventRow.entity_type == entity_type)
    q = q.order_by(AuditEventRow.seq.desc() if newest_first else AuditEventRow.seq).limit(limit)
    return [to_doc(r) for r in s.scalars(q)]


def all_lines(s: Session, case_id: str) -> list[str]:
    return [r.line for r in s.scalars(select(AuditEventRow).where(AuditEventRow.case_id == case_id).order_by(AuditEventRow.seq))]


def verify_chain(lines: list[str]) -> dict[str, Any]:
    """校验 prev 链（适用于 audit.jsonl 与 custody.jsonl）。"""
    import json

    prev = ZERO_HASH
    for i, line in enumerate(lines):
        try:
            rec = json.loads(line)
        except ValueError:
            return {"valid": False, "count": len(lines), "brokenAt": i + 1, "reason": "bad json"}
        if rec.get("prev", prev) != prev:
            return {"valid": False, "count": len(lines), "brokenAt": i + 1, "reason": "prev hash mismatch"}
        if "seq" in rec and int(rec["seq"]) != i + 1:
            return {"valid": False, "count": len(lines), "brokenAt": i + 1, "reason": "seq gap"}
        prev = sha256_utf8(line)
    return {"valid": True, "count": len(lines), "brokenAt": None, "reason": "", "headHash": prev}


def count(s: Session, case_id: str) -> int:
    return s.scalar(select(func.count()).select_from(AuditEventRow).where(AuditEventRow.case_id == case_id)) or 0
