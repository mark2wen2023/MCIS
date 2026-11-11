"""证据登记与保管链。保管链行格式与 C# Mcis.Domain.Evidence.CustodyEvent.ToJsonLine 逐字节一致。"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import service as audit
from ..common.context import problem
from ..common.csjson import ZERO_HASH, flat_line, sha256_hex, sha256_utf8
from ..common.timeutil import iso, now_utc, parse_iso
from ..db import WRITE_LOCK, get_doc, list_docs
from .models import CustodyEventRow, EvidenceRow

ACTIONS = {"Register": "custody.register", "Access": "custody.access", "Change": "custody.change", "Verify": "custody.verify",
           "Review": "custody.review"}
COMMANDS = {"Register": "登记证据 ", "Access": "访问证据 ", "Change": "证据派生/变更 ", "Verify": "校验证据哈希 "}
KIND_BY_ACTION = {v: k for k, v in ACTIONS.items()}


def command_of(kind: str, evidence_id: str, review: bool | None) -> str:
    if kind == "Review":
        return ("标注需复核 " if review else "解除需复核 ") + evidence_id
    return COMMANDS[kind] + evidence_id


def after_of(kind: str, sha256: str, detail: str, review: bool | None) -> str:
    if kind == "Access":
        return detail
    if kind == "Review":
        return "NeedsReview" if review else "Cleared"
    return sha256
REGISTER_FIELDS = ("evidenceId", "caseId", "title", "source", "extractedBy", "extractedUtc", "sha256", "relativePath")


def custody_line(*, seq: int, utc: str, operator: str, kind: str, evidence_id: str, sha256: str, previous_sha256: str,
                 detail: str, matched: bool | None, prev: str, item: dict[str, Any] | None,
                 review: bool | None = None) -> str:
    """与 C# CustodyEvent.ToJsonLine 逐字节一致（含 W3 新增的 Review / case_id / confidentiality）。"""
    before = previous_sha256 if kind in ("Change", "Verify") else ""
    pairs: list[tuple[str, object]] = [
        ("utc", utc), ("operator", operator), ("action", ACTIONS[kind]), ("category", "Custody"),
        ("command", command_of(kind, evidence_id, review)), ("before", before), ("after", after_of(kind, sha256, detail, review)),
        ("seq", seq), ("evidence_id", evidence_id), ("sha256", sha256), ("detail", detail),
    ]
    if matched is not None:
        pairs.append(("result", "match" if matched else "mismatch"))
    if review is not None:
        pairs.append(("result", "needs_review" if review else "cleared"))
    if item is not None:
        pairs += [("title", item.get("title", "")), ("source", item.get("source", "")),
                  ("extracted_by", item.get("extractedBy", "")),
                  ("extracted_utc", iso(parse_iso(item["extractedUtc"]))), ("path", item.get("relativePath", ""))]
        if item.get("caseId"):
            pairs.append(("case_id", item["caseId"]))
        if item.get("confidentiality") == "Restricted":
            pairs.append(("confidentiality", "Restricted"))
    pairs.append(("prev", prev))
    return flat_line(pairs)


def append_custody(s: Session, *, case_id: str, evidence_id: str, kind: str, operator: str, role: str,
                   sha256: str = "", previous_sha256: str = "", detail: str = "", matched: bool | None = None,
                   item: dict[str, Any] | None = None, utc: str | None = None,
                   review: bool | None = None) -> CustodyEventRow:
    with WRITE_LOCK:
        last = s.scalars(select(CustodyEventRow).where(CustodyEventRow.case_id == case_id)
                         .order_by(CustodyEventRow.seq.desc()).limit(1)).first()
        seq = last.seq + 1 if last else 1
        prev = sha256_utf8(last.line) if last else ZERO_HASH
        utc_s = iso(parse_iso(utc)) if utc else iso(now_utc())
        line = custody_line(seq=seq, utc=utc_s, operator=operator, kind=kind, evidence_id=evidence_id, sha256=sha256,
                            previous_sha256=previous_sha256, detail=detail, matched=matched, prev=prev, item=item,
                            review=review)
        row = CustodyEventRow(case_id=case_id, seq=seq, evidence_id=evidence_id, kind=kind, utc=utc_s, operator=operator,
                              sha256=sha256, previous_sha256=previous_sha256, detail=detail,
                              verify_matched=matched if kind == "Verify" else review,
                              prev_line_hash=prev, line=line)
        s.add(row)
        s.flush()
        audit.append(s, case_id=case_id, operator=operator, role=role, action=ACTIONS[kind], category="Custody",
                     command=command_of(kind, evidence_id, review), before=previous_sha256 if kind in ("Change", "Verify") else "",
                     after=after_of(kind, sha256, detail, review) + (f"｜{detail}" if kind == "Review" else ""),
                     entity_type="evidence", entity_id=evidence_id, utc=utc_s)
        return row


def custody_doc(r: CustodyEventRow) -> dict[str, Any]:
    return {"seq": r.seq, "utc": r.utc, "operator": r.operator, "kind": r.kind, "evidenceId": r.evidence_id,
            "sha256": r.sha256, "previousSha256": r.previous_sha256, "detail": r.detail,
            "verifyMatched": r.verify_matched if r.kind == "Verify" else None,
            "needsReview": r.verify_matched if r.kind == "Review" else None,
            "prevLineHash": r.prev_line_hash, "line": r.line}


def custody_events(s: Session, case_id: str, evidence_id: str | None = None) -> list[CustodyEventRow]:
    q = select(CustodyEventRow).where(CustodyEventRow.case_id == case_id)
    if evidence_id:
        q = q.where(CustodyEventRow.evidence_id == evidence_id)
    return list(s.scalars(q.order_by(CustodyEventRow.seq)))


def derive(item: dict[str, Any], events: list[CustodyEventRow]) -> dict[str, Any]:
    """= C# EvidenceStatus 推导：NeedsReview 优先；Change 后未重新校验为 Unverified。"""
    d = dict(item)
    d.setdefault("confidentiality", "Normal")
    current = item["sha256"]
    access = 0
    last_access = None
    verify = "Unverified"
    review = False
    for e in events:
        if e.kind == "Change":
            current = e.sha256
            verify = "Unverified"
        elif e.kind == "Access":
            access += 1
            last_access = e
        elif e.kind == "Verify":
            verify = "Verified" if e.verify_matched else "Mismatch"
        elif e.kind == "Review":
            review = bool(e.verify_matched)
    d.update({"currentSha256": current, "accessCount": access, "status": "NeedsReview" if review else verify,
              "needsReview": review,
              "lastAccessUtc": last_access.utc if last_access else None,
              "lastAccessBy": last_access.operator if last_access else None})
    return d


def load_item(s: Session, case_id: str, evidence_id: str) -> dict[str, Any]:
    doc = get_doc(s, EvidenceRow, case_id, evidence_id)
    if doc is None:
        raise problem(404, "EVIDENCE_NOT_FOUND", f"证据不存在：{evidence_id}")
    return doc


def list_items(s: Session, case_id: str) -> list[dict[str, Any]]:
    events = custody_events(s, case_id)
    by_id: dict[str, list] = {}
    for e in events:
        by_id.setdefault(e.evidence_id, []).append(e)
    docs = sorted(list_docs(s, EvidenceRow, case_id), key=lambda d: d["evidenceId"])
    return [derive(d, by_id.get(d["evidenceId"], [])) for d in docs]


def next_id(s: Session, case_id: str) -> str:
    nums = [int(re.sub(r"\D", "", d["evidenceId"]) or 0) for d in list_docs(s, EvidenceRow, case_id)]
    return f"EV-{(max(nums) + 1 if nums else 1):03d}"


def blob_path(blob_root: Path, case_id: str, relative_path: str) -> Path:
    rel = relative_path.replace("\\", "/").lstrip("/")
    if ".." in rel.split("/"):
        raise problem(400, "BAD_PATH", "非法路径")
    return blob_root / case_id / rel


def write_blob(blob_root: Path, case_id: str, relative_path: str, data: bytes, *, overwrite: bool = False) -> str:
    p = blob_path(blob_root, case_id, relative_path)
    if p.exists() and not overwrite:
        if relative_path.startswith("raw/"):
            raise problem(409, "RAW_READ_ONLY", "raw/ 原始证据只读，不可覆盖")
        raise problem(409, "BLOB_EXISTS", f"文件已存在：{relative_path}")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return sha256_hex(data)


def verify_one(s: Session, blob_root: Path, case_id: str, item: dict[str, Any], operator: str, role: str) -> CustodyEventRow:
    derived = derive(item, custody_events(s, case_id, item["evidenceId"]))
    expected = derived["currentSha256"]
    rel = item.get("relativePath") or ""
    p = blob_path(blob_root, case_id, rel) if rel else None
    if p is None or not p.exists():
        return append_custody(s, case_id=case_id, evidence_id=item["evidenceId"], kind="Verify", operator=operator, role=role,
                              sha256="", previous_sha256=expected, detail="文件缺失，无法校验", matched=False)
    actual = sha256_hex(p.read_bytes())
    return append_custody(s, case_id=case_id, evidence_id=item["evidenceId"], kind="Verify", operator=operator, role=role,
                          sha256=actual, previous_sha256=expected, detail="重新计算 SHA-256", matched=(actual == expected))
