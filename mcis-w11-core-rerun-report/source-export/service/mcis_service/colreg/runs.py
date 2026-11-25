"""COLREG 分析版本化（W6.1 裁定 9）。

存储（colreg_analyses 表，按 key 区分）：
- ``runs``           版本索引 {activeRunId, currentSha, runs:[meta…]}
- ``run:R-0001``     单个版本 {meta…, analysis: <colreg.schema 文档>, annotations: {bands, checks}}
- ``current``        当前激活版本的 analysis 镜像（GET /colreg、.mcase 导出读这里）

规则：每次 evaluate 新建一个版本并激活；旧版本（含种子与已做的复核）原样保留，可切换、可对比，永不覆盖。
首次访问时把已有的 ``current`` 收编为第 1 版（种子或初始）。``current`` 被外部（如 .mcase 导入）改写时，
按内容哈希发现并另存为新版本，而不是丢弃。
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
from typing import Any

from sqlalchemy.orm import Session

from ..common.context import problem
from ..common.timeutil import iso, now_utc
from ..db import get_doc, put_doc
from .models import ColregAnalysisRow
from .seed_annotations import seed_band_evidence

INDEX_KEY = "runs"
CURRENT_KEY = "current"
LOCK = threading.RLock()
KIND_LABEL = {"Seed": "种子（报告整理）", "Initial": "初始", "RuleEngine": "规则引擎", "External": "外部导入"}


def _sha(doc: dict[str, Any] | None) -> str:
    return hashlib.sha256(json.dumps(doc or {}, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def run_key(run_id: str) -> str:
    return f"run:{run_id}"


def _new_id(idx: dict[str, Any]) -> tuple[str, int]:
    n = max([r["version"] for r in idx["runs"]] or [0]) + 1
    return f"R-{n:04d}", n


def _kind_of(analysis: dict[str, Any]) -> str:
    checks = analysis.get("checks") or []
    if checks and all(c.get("source") == "Seed" for c in checks):
        return "Seed"
    if checks and any(c.get("source") == "RuleEngine" for c in checks):
        return "RuleEngine"
    return "Initial"


def _summary(analysis: dict[str, Any]) -> dict[str, Any]:
    checks = analysis.get("checks") or []
    reviewed = sum(1 for c in checks if (c.get("reviewStatus") or "Draft") != "Draft")
    return {"bandCount": len(analysis.get("bands") or []), "checkCount": len(checks), "reviewedCount": reviewed}


def _create(s: Session, case_id: str, idx: dict[str, Any], analysis: dict[str, Any], *, kind: str, created_by: str,
            band_evidence: dict[str, list[str]] | None = None, note: str = "", activate: bool = True) -> dict[str, Any]:
    run_id, version = _new_id(idx)
    meta = {"runId": run_id, "version": version, "kind": kind,
            "label": f"v{version} · {KIND_LABEL.get(kind, kind)}", "createdUtc": iso(now_utc()), "createdBy": created_by,
            "parentRunId": idx.get("activeRunId"), "engineVersion": analysis.get("engineVersion") or "", "note": note}
    bands = {b["bandId"]: {"evidenceIds": list((band_evidence or {}).get(b["bandId"], []))}
             for b in analysis.get("bands") or []}
    run = {**meta, "analysis": analysis, "annotations": {"bands": bands, "checks": {}}}
    put_doc(s, ColregAnalysisRow, case_id, run_key(run_id), run)
    idx["runs"].append(meta)
    if activate:
        idx["activeRunId"] = run_id
        put_doc(s, ColregAnalysisRow, case_id, CURRENT_KEY, analysis)
        idx["currentSha"] = _sha(analysis)
    put_doc(s, ColregAnalysisRow, case_id, INDEX_KEY, idx)
    return run


def ensure(s: Session, case_id: str, operator: str = "系统（版本收编）") -> dict[str, Any]:
    """返回版本索引；必要时收编现有 current。幂等。"""
    idx = get_doc(s, ColregAnalysisRow, case_id, INDEX_KEY)
    cur = get_doc(s, ColregAnalysisRow, case_id, CURRENT_KEY)
    if idx is None:
        idx = {"caseId": case_id, "activeRunId": None, "currentSha": None, "runs": []}
        if cur is None:
            put_doc(s, ColregAnalysisRow, case_id, INDEX_KEY, idx)
            return idx
        kind = _kind_of(cur)
        _create(s, case_id, idx, copy.deepcopy(cur), kind=kind, created_by=operator,
                band_evidence=seed_band_evidence(case_id) if kind == "Seed" else None,
                note="首次访问时由已有 current 收编")
        return idx
    if cur is not None and idx.get("currentSha") != _sha(cur):
        # current 被外部改写（如 .mcase 导入）：另存为新版本，不丢弃旧版本
        _create(s, case_id, idx, copy.deepcopy(cur), kind="External", created_by=operator,
                note="current 被外部改写，按内容另存")
    return idx


def get_run(s: Session, case_id: str, run_id: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    idx = ensure(s, case_id)
    rid = idx.get("activeRunId") if run_id in (None, "", "active") else run_id
    if not rid:
        raise problem(404, "colreg_run_not_found", "本案件还没有 COLREG 分析版本")
    run = get_doc(s, ColregAnalysisRow, case_id, run_key(rid))
    if run is None:
        raise problem(404, "colreg_run_not_found", f"COLREG 分析版本不存在：{rid}")
    return idx, run


def save_run(s: Session, case_id: str, idx: dict[str, Any], run: dict[str, Any]) -> None:
    """保存版本；若是激活版本，同时刷新 current 镜像。"""
    put_doc(s, ColregAnalysisRow, case_id, run_key(run["runId"]), run)
    if idx.get("activeRunId") == run["runId"]:
        put_doc(s, ColregAnalysisRow, case_id, CURRENT_KEY, run["analysis"])
        idx["currentSha"] = _sha(run["analysis"])
        put_doc(s, ColregAnalysisRow, case_id, INDEX_KEY, idx)


def add_engine_run(s: Session, case_id: str, analysis: dict[str, Any], *, created_by: str,
                   band_evidence_ids: list[str]) -> dict[str, Any]:
    idx = ensure(s, case_id)
    be = {b["bandId"]: list(band_evidence_ids) for b in analysis.get("bands") or []}
    return _create(s, case_id, idx, analysis, kind="RuleEngine", created_by=created_by, band_evidence=be,
                   note="规则引擎结果（Draft，需逐条复核）")


def activate(s: Session, case_id: str, run_id: str) -> tuple[dict[str, Any], dict[str, Any], str | None]:
    idx, run = get_run(s, case_id, run_id)
    prev = idx.get("activeRunId")
    idx["activeRunId"] = run["runId"]
    put_doc(s, ColregAnalysisRow, case_id, CURRENT_KEY, run["analysis"])
    idx["currentSha"] = _sha(run["analysis"])
    put_doc(s, ColregAnalysisRow, case_id, INDEX_KEY, idx)
    return idx, run, prev


def list_runs(s: Session, case_id: str) -> dict[str, Any]:
    idx = ensure(s, case_id)
    out = []
    for meta in idx["runs"]:
        run = get_doc(s, ColregAnalysisRow, case_id, run_key(meta["runId"])) or {}
        out.append({**meta, **_summary(run.get("analysis") or {}), "active": meta["runId"] == idx.get("activeRunId")})
    return {"caseId": case_id, "activeRunId": idx.get("activeRunId"), "runs": out}


def _match_key(c: dict[str, Any]) -> tuple[str, str]:
    return (str(c.get("rule")), str(c.get("vesselId")))


def compare(base: dict[str, Any], other: dict[str, Any]) -> dict[str, Any]:
    """按（规则, 船）+ 出现顺序配对两个版本的核查项；时间带按序号对齐。"""
    def grouped(run: dict[str, Any]) -> dict[tuple[str, str], list[dict[str, Any]]]:
        g: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for c in run["analysis"].get("checks") or []:
            g.setdefault(_match_key(c), []).append(c)
        return g

    def brief(c: dict[str, Any] | None) -> dict[str, Any] | None:
        if c is None:
            return None
        return {"checkId": c["checkId"], "verdict": c["verdict"], "reviewStatus": c.get("reviewStatus") or "Draft",
                "source": c.get("source"), "title": c.get("title") or ""}

    ga, gb = grouped(base), grouped(other)
    keys = list(dict.fromkeys([*ga.keys(), *gb.keys()]))
    rows = []
    for k in keys:
        la, lb = ga.get(k, []), gb.get(k, [])
        for i in range(max(len(la), len(lb))):
            a = la[i] if i < len(la) else None
            b = lb[i] if i < len(lb) else None
            changed = a is None or b is None or a["verdict"] != b["verdict"]
            rows.append({"rule": k[0], "vesselId": k[1], "base": brief(a), "other": brief(b), "verdictChanged": changed})
    bands = []
    ba, bb = base["analysis"].get("bands") or [], other["analysis"].get("bands") or []
    for i in range(max(len(ba), len(bb))):
        a = ba[i] if i < len(ba) else None
        b = bb[i] if i < len(bb) else None
        pick = lambda x: None if x is None else {k: x.get(k) for k in ("bandId", "startTimeSec", "endTimeSec", "situation", "dangerStage", "giveWayVesselId", "standOnVesselId")}  # noqa: E731
        bands.append({"base": pick(a), "other": pick(b),
                      "changed": a is None or b is None or pick(a)["situation"] != pick(b)["situation"]
                      or pick(a)["dangerStage"] != pick(b)["dangerStage"]})
    return {"baseRunId": base["runId"], "otherRunId": other["runId"],
            "checks": rows, "bands": bands,
            "changedCheckCount": sum(1 for r in rows if r["verdictChanged"]),
            "changedBandCount": sum(1 for b in bands if b["changed"])}
