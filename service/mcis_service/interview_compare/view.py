"""W5 询问笔录比对页的纯函数视图（与 C# Mcis.Domain.InterviewCompare 同口径），只读写 interview 合同文档（dict）。

W5.1（DEFECTS/W5.md 21:32 裁定）：
- crossCheckResult.statementVersion（缺省 1）与 statement.revision（缺省 1）不同 → 结论过期（stale），页面显示「需重新比对」；
  过期结论不计入矛盾数 / 已确认矛盾数 / 待确认数，不高亮矛盾，不给数据时刻，不能确认。
- 同一陈述可有多条比对记录：被重新提交取代的旧条目 state=Superseded 留在 crossChecks 中；当前条目 = 该陈述最后一条非 Superseded 记录。
确定性规则，不调用 LLM。
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from ..common.timeutil import iso, parse_iso

STALE_LABEL = "需重新比对"
SUPERSEDED = "Superseded"
PENDING = "PendingConfirmation"
CONFIRMED = "Confirmed"
DISMISSED = "Dismissed"
OPEN_REVIEW = ("Draft", "Modified")


def revision(st: dict[str, Any] | None) -> int:
    return int((st or {}).get("revision") or 1)


def version(cc: dict[str, Any] | None) -> int:
    return int((cc or {}).get("statementVersion") or 1)


def current_entries(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """statementId → 当前比对条目（最后一条非 Superseded 且属于本笔录的记录）。"""
    out: dict[str, dict[str, Any]] = {}
    for c in doc.get("crossChecks", []):
        if c.get("state") == SUPERSEDED or c.get("recordId", doc["recordId"]) != doc["recordId"]:
            continue
        out[c["statementId"]] = c
    return out


def statement(doc: dict[str, Any], sid: str) -> dict[str, Any] | None:
    return next((s for s in doc.get("statements", []) if s["statementId"] == sid), None)


def is_stale(cc: dict[str, Any] | None, st: dict[str, Any] | None) -> bool:
    return cc is not None and st is not None and version(cc) != revision(st)


def _live_contradiction(cc: dict[str, Any] | None) -> bool:
    return cc is not None and cc.get("outcome") == "Contradictory" and cc.get("state") in (PENDING, CONFIRMED)


def _data_text(cc: dict[str, Any]) -> str:
    src = cc.get("sourceLabel") or ""
    return cc.get("observedText", "") if not src else f"{cc.get('observedText', '')} ({src})"


def _visible(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [s for s in doc.get("statements", []) if s.get("reviewStatus") != "Rejected"]


def rows(doc: dict[str, Any]) -> list[dict[str, Any]]:
    cur = current_entries(doc)
    sup: dict[str, int] = {}
    for c in doc.get("crossChecks", []):
        if c.get("state") == SUPERSEDED:
            sup[c["statementId"]] = sup.get(c["statementId"], 0) + 1
    out = []
    seen = set()
    for s in doc.get("statements", []):
        seen.add(s["statementId"])
    for s in _visible(doc):
        cc = cur.get(s["statementId"])
        stale = is_stale(cc, s)
        out.append({
            "statementId": s["statementId"], "citation": f"{doc['recordId']} 第 {s['span']['round']} 问",
            "summary": s.get("summary", ""), "quote": s.get("quote", ""), "kind": s.get("kind"),
            "reviewStatus": s.get("reviewStatus"), "statementRevision": revision(s), "statementMissing": False,
            **_entry_fields(cc, stale), "supersededCount": sup.get(s["statementId"], 0),
        })
    # 只有比对记录、没有结构化陈述的笔录（种子 IR-01/02/04/05/06）：按比对记录成行，不判过期。
    for sid, cc in cur.items():
        if sid in seen:
            continue
        out.append({
            "statementId": sid, "citation": doc["recordId"], "summary": cc.get("claimedText", ""), "quote": "", "kind": None,
            "reviewStatus": None, "statementRevision": None, "statementMissing": True,
            **_entry_fields(cc, False), "supersededCount": sup.get(sid, 0),
        })
    return out


def _entry_fields(cc: dict[str, Any] | None, stale: bool) -> dict[str, Any]:
    if cc is None:
        return {"outcome": None, "state": None, "dataDisplay": "", "delta": None, "deltaUnit": "", "rule": "",
                "statementVersion": None, "isStale": False, "isContradiction": False, "decidedBy": None, "note": ""}
    return {"outcome": cc.get("outcome"), "state": cc.get("state"), "dataDisplay": _data_text(cc), "delta": cc.get("delta"),
            "deltaUnit": cc.get("deltaUnit", ""), "rule": cc.get("rule", ""), "statementVersion": version(cc), "isStale": stale,
            "isContradiction": (not stale) and _live_contradiction(cc), "decidedBy": cc.get("decidedBy"), "note": cc.get("note", "")}


def summarize(doc: dict[str, Any]) -> dict[str, Any]:
    s = {"statementCount": 0, "contradictionCount": 0, "confirmedContradictionCount": 0, "pendingCount": 0,
         "uncheckedCount": 0, "staleCount": 0}
    for r in rows(doc):
        s["statementCount"] += 1
        if r["state"] is None:
            s["uncheckedCount"] += 1
            continue
        if r["isStale"]:
            s["staleCount"] += 1
            continue
        if r["isContradiction"]:
            s["contradictionCount"] += 1
        if r["state"] == CONFIRMED and r["outcome"] == "Contradictory":
            s["confirmedContradictionCount"] += 1
        if r["state"] == PENDING:
            s["pendingCount"] += 1
    s["headerText"] = f"{s['statementCount']} 条陈述 · {s['contradictionCount']} 条矛盾" + (
        f" · {s['staleCount']} 条{STALE_LABEL}" if s["staleCount"] else "")
    return s


def roster_entry(doc: dict[str, Any]) -> dict[str, Any]:
    s = summarize(doc)
    iv = doc.get("interviewee", {})
    e = {"recordId": doc["recordId"], "name": iv.get("name", ""), "role": iv.get("role", ""), "affiliation": iv.get("affiliation", ""),
         "startUtc": doc.get("startUtc"), "durationMin": doc.get("durationMin"), "signed": bool(doc.get("signed", False)),
         "statementCount": s["statementCount"], "confirmedContradictions": s["confirmedContradictionCount"],
         "pendingCount": s["pendingCount"], "uncheckedCount": s["uncheckedCount"], "staleCount": s["staleCount"]}
    open_parts = ([f"{s['pendingCount']} 条待确认"] if s["pendingCount"] else []) + (
        [f"{s['staleCount']} 条{STALE_LABEL}"] if s["staleCount"] else [])
    if s["confirmedContradictionCount"]:
        e["status"], e["label"] = "Contradictions", " · ".join([f"{s['confirmedContradictionCount']} 处矛盾", *open_parts])
    elif open_parts:
        e["status"], e["label"] = "Pending", " · ".join(open_parts)
    elif s["statementCount"] > s["uncheckedCount"]:
        e["status"] = "Consistent"
        e["label"] = "一致" + (f" · {s['uncheckedCount']} 条未比对" if s["uncheckedCount"] else "")
    else:
        e["status"], e["label"] = "NotChecked", "未比对"
    return e


def _mark(cc: dict[str, Any] | None, st: dict[str, Any]) -> str:
    if cc is None or cc.get("outcome") != "Contradictory" or is_stale(cc, st):
        return "None"
    return {CONFIRMED: "Confirmed", PENDING: "Pending"}.get(cc.get("state"), "None")


def _u16(text: str) -> bytes:
    return text.encode("utf-16-le")


def segments(doc: dict[str, Any], rnd: int, field: str, text: str) -> list[dict[str, Any]]:
    """把一轮问/答切成覆盖全文的片段（UTF-16 下标，与 SourceSpan 一致）；已驳回的陈述不高亮。"""
    b = _u16(text)
    n = len(b) // 2
    cur = current_entries(doc)
    spans = []
    for s in doc.get("statements", []):
        sp = s.get("span", {})
        if s.get("reviewStatus") == "Rejected" or sp.get("round") != rnd or sp.get("field") != field:
            continue
        st, ln = int(sp.get("start", 0)), int(sp.get("length", 0))
        if ln <= 0 or st < 0 or st + ln > n:
            continue
        spans.append((st, st + ln, s))
    cuts = sorted({0, n, *[a for a, _, _ in spans], *[z for _, z, _ in spans]})
    out = []
    for a, z in zip(cuts, cuts[1:]):
        if a == z:
            continue
        cover = [s for (x, y, s) in spans if x <= a and z <= y]
        marks = [_mark(cur.get(s["statementId"]), s) for s in cover]
        mark = "Confirmed" if "Confirmed" in marks else "Pending" if "Pending" in marks else "None"
        out.append({"start": a, "length": z - a, "text": b[a * 2:z * 2].decode("utf-16-le", "replace"),
                    "kinds": sorted({s["kind"] for s in cover}), "statementIds": [s["statementId"] for s in cover], "contradiction": mark})
    return out


def chart(doc: dict[str, Any]) -> dict[str, Any]:
    cur = current_entries(doc)
    pts = []
    for s in _visible(doc):
        claim = s.get("claim") or {}
        at = claim.get("time") if claim.get("valueType") == "EventTime" else s.get("referenceUtc")
        if not at:
            continue
        cc = cur.get(s["statementId"])
        p = {"statementId": s["statementId"], "summary": s.get("summary", ""), "statementUtc": iso(parse_iso(at)),
             "observedUtc": None, "deltaSeconds": None, "outcome": None, "isStale": False, "note": "未比对"}
        if cc is not None and is_stale(cc, s):
            p["isStale"], p["note"] = True, STALE_LABEL
        elif cc is not None:
            p["outcome"], p["note"] = cc.get("outcome"), _data_text(cc)
            d = cc.get("delta")
            if claim.get("valueType") == "EventTime" and d is not None and cc.get("deltaUnit") == "s":
                p["deltaSeconds"] = d
                p["observedUtc"] = iso(parse_iso(at) - timedelta(seconds=float(d)))
        pts.append(p)
    pts.sort(key=lambda p: p["statementUtc"])  # 稳定排序：同一时刻保持陈述顺序
    times = [t for p in pts for t in (p["statementUtc"], p["observedUtc"]) if t]
    lo = min(times) if times else None
    hi = max(times) if times else None
    return {"points": pts, "axisStartUtc": _floor_min(lo), "axisEndUtc": _ceil_min(hi)}


def _floor_min(t: str | None) -> str | None:
    if t is None:
        return None
    return iso(parse_iso(t).replace(second=0))


def _ceil_min(t: str | None) -> str | None:
    if t is None:
        return None
    dt = parse_iso(t)
    return iso(dt if dt.second == 0 else dt.replace(second=0) + timedelta(minutes=1))


def summary_text(cc: dict[str, Any]) -> str:
    """审计摘要，与 C# CrossCheckRegister.Summarize 同格式。"""
    d = cc.get("delta")
    delta = "-" if d is None else f"{float(d):.3f}".rstrip("0").rstrip(".") + f" {cc.get('deltaUnit', '')}"
    return (f"{cc.get('state')}；{cc.get('outcome')}；陈述={cc.get('claimedText', '')}；数据={cc.get('observedText', '')}"
            f"（{cc.get('sourceLabel', '')}）；Δ={delta}；规则={cc.get('rule', '')}")
