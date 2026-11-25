from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..common.context import problem
from ..db import get_doc
from .models import InterviewRow


def utf16_slice(text: str, start: int, length: int) -> str:
    """按 UTF-16 下标截取（与 C# string.Substring 一致）。"""
    b = text.encode("utf-16-le")
    if start < 0 or length < 0 or (start + length) * 2 > len(b):
        raise problem(422, "interview_span_out_of_range", "原文出处超出范围")
    return b[start * 2:(start + length) * 2].decode("utf-16-le")


def utf16_index(text: str, sub: str) -> int:
    i = text.find(sub)
    if i < 0:
        raise ValueError(f"片段不在原文中：{sub}")
    return len(text[:i].encode("utf-16-le")) // 2


def utf16_len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def load(s: Session, case_id: str, record_id: str) -> dict[str, Any]:
    d = get_doc(s, InterviewRow, case_id, record_id)
    if d is None:
        raise problem(404, "INTERVIEW_NOT_FOUND", f"笔录不存在：{record_id}")
    return d


def quote_for(record: dict[str, Any], span: dict[str, Any]) -> str:
    turn = next((t for t in record["turns"] if t["round"] == span["round"]), None)
    if turn is None:
        raise problem(422, "interview_span_out_of_range", f"第 {span['round']} 问不存在")
    text = turn["answer"] if span["field"] == "Answer" else turn["question"]
    return utf16_slice(text, span["start"], span["length"])


def summary(doc: dict[str, Any]) -> dict[str, Any]:
    cc = doc.get("crossChecks", [])
    return {
        "recordId": doc["recordId"], "caseId": doc["caseId"], "interviewee": doc["interviewee"],
        "startUtc": doc["startUtc"], "durationMin": doc.get("durationMin"), "signed": doc.get("signed", False),
        "turnCount": len(doc.get("turns", [])), "statementCount": len(doc.get("statements", [])),
        "contradictionCount": sum(1 for c in cc if c["outcome"] == "Contradictory" and c.get("state") == "Confirmed"),
        "contradictionCandidateCount": sum(1 for c in cc if c["outcome"] == "Contradictory" and c.get("state") != "Dismissed"),
        "pendingConfirmationCount": sum(1 for c in cc if c.get("state") == "PendingConfirmation"),
        "draftStatementCount": sum(1 for st in doc.get("statements", []) if st["reviewStatus"] == "Draft"),
    }
