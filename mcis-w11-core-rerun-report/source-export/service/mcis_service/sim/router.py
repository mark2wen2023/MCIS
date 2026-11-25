"""Unity ↔ 服务 回放同步。

- Unity 推送当前 SimTime：PUT /sim/state（≤10 Hz，瞬态，只存内存，不入审计——不是案件数据）
- 网页请求跳转：POST /sim/seek（入审计 category=Sim）
- Unity 轮询命令：GET /sim/commands?afterSeq=N
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from ..audit import service as audit
from ..cases.service import load_case
from ..common.context import Ctx, CtxDep, problem
from ..common.timeutil import iso, iso_ms, now_utc, sim_to_utc
from ..db import WRITE_LOCK
from .models import SimCommandRow

# Char.IsWhiteSpace / String.IsNullOrWhiteSpace wire semantics in the C# adapter.
# Python str.strip additionally treats U+001C..U+001F as whitespace.
_DOTNET_WHITESPACE = frozenset(
    "\u0009\u000a\u000b\u000c\u000d\u0020\u0085\u00a0\u1680"
    "\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a"
    "\u2028\u2029\u202f\u205f\u3000"
)

router = APIRouter(prefix="/api/v1/cases/{case_id}/sim", tags=["sim"])


class StateIn(BaseModel):
    simTimeSec: float
    playing: bool = False
    rate: float = Field(1.0, gt=0, le=256)
    source: str = "unity"


class SeekIn(BaseModel):
    simTimeSec: float
    reason: str = ""


class CommandIn(BaseModel):
    type: Literal["seek", "play", "pause", "setRate", "focusVessel"]
    simTimeSec: float | None = None
    rate: float | None = None
    vesselId: str | None = None
    reason: str = ""


def _states(ctx: Ctx) -> dict[str, dict[str, Any]]:
    st = ctx.request.app.state
    if not hasattr(st, "sim_states"):
        st.sim_states = {}
    return st.sim_states


@router.get("/state")
def get_state(case_id: str, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        case = load_case(s, case_id)
    cur = _states(ctx).get(case_id)
    if cur is None:
        cur = {"caseId": case_id, "simTimeSec": 0.0, "utc": sim_to_utc(case["caseEpochUtc"], 0.0), "playing": False,
               "rate": 1.0, "source": "default", "updatedUtc": iso(now_utc())}
    return cur


@router.put("/state")
def put_state(case_id: str, body: StateIn, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        case = load_case(s, case_id)
    dur = float(case.get("durationSec") or 1e9)
    if not (0 <= body.simTimeSec <= dur):
        raise problem(422, "OUT_OF_RANGE", f"simTimeSec 超出 [0, {dur}]")
    st = {"caseId": case_id, "simTimeSec": body.simTimeSec, "utc": sim_to_utc(case["caseEpochUtc"], body.simTimeSec),
          "playing": body.playing, "rate": body.rate, "source": body.source, "updatedUtc": iso_ms(now_utc())}
    _states(ctx)[case_id] = st
    return st


def _issue(ctx: Ctx, case_id: str, cmd: dict[str, Any]) -> dict[str, Any]:
    with ctx.db.session() as s:
        case = load_case(s, case_id)
        if cmd.get("simTimeSec") is not None:
            dur = float(case.get("durationSec") or 1e9)
            if not (0 <= cmd["simTimeSec"] <= dur):
                raise problem(422, "OUT_OF_RANGE", f"simTimeSec 超出 [0, {dur}]")
        with WRITE_LOCK:
            seq = (s.scalar(select(func.max(SimCommandRow.seq)).where(SimCommandRow.case_id == case_id)) or 0) + 1
            doc = {"seq": seq, "caseId": case_id, "createdUtc": iso(now_utc()), "issuedBy": ctx.operator, **cmd}
            s.add(SimCommandRow(case_id=case_id, seq=seq, doc=doc))
            s.flush()
        label = cmd["type"] + (f" → {sim_to_utc(case['caseEpochUtc'], cmd['simTimeSec'])}" if cmd.get("simTimeSec") is not None else "")
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action=f"sim.{cmd['type']}", category="Sim",
                     command=f"回放控制 {label}", after=cmd.get("reason", ""), entity_type="simCommand", entity_id=str(seq))
        return doc


@router.post("/seek", status_code=201)
def seek(case_id: str, body: SeekIn, ctx: Ctx = CtxDep) -> dict[str, Any]:
    return _issue(ctx, case_id, {"type": "seek", "simTimeSec": body.simTimeSec, "rate": None, "vesselId": None, "reason": body.reason})


@router.post("/commands", status_code=201)
def command(case_id: str, body: CommandIn, ctx: Ctx = CtxDep) -> dict[str, Any]:
    if body.type == "seek" and body.simTimeSec is None:
        raise problem(422, "SIMTIME_REQUIRED", "seek 需要 simTimeSec")
    if body.rate is not None and not isfinite(body.rate):
        raise problem(422, "NONFINITE_PARAMETER", "rate 必须是有限数")
    if body.type == "setRate":
        if body.rate is None:
            raise problem(422, "RATE_REQUIRED", "setRate 需要 rate")
        if body.rate not in (0.25, 0.5, 1, 2, 4, 8, 16, 32):
            raise problem(422, "UNSUPPORTED_RATE", "rate 必须为 0.25、0.5、1、2、4、8、16、32")
    if body.type == "focusVessel" and (body.vesselId is None or all(c in _DOTNET_WHITESPACE for c in body.vesselId)):
        raise problem(422, "VESSEL_REQUIRED", "focusVessel 需要非空白 vesselId")
    return _issue(ctx, case_id, body.model_dump())


@router.get("/commands")
def poll(case_id: str, afterSeq: int = 0, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        load_case(s, case_id)
        rows = s.scalars(select(SimCommandRow).where(SimCommandRow.case_id == case_id, SimCommandRow.seq > afterSeq)
                         .order_by(SimCommandRow.seq).limit(100)).all()
        cmds = [dict(r.doc) for r in rows]
        return {"caseId": case_id, "commands": cmds, "lastSeq": cmds[-1]["seq"] if cmds else afterSeq}
