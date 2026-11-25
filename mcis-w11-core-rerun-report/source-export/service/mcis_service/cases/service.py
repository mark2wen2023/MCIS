from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..common.context import problem
from ..db import get_doc, list_docs
from .models import CaseRow, TrackPointRow, VesselRow


def load_case(s: Session, case_id: str) -> dict[str, Any]:
    doc = get_doc(s, CaseRow, case_id, case_id)
    if doc is None:
        raise problem(404, "CASE_NOT_FOUND", f"案件不存在：{case_id}")
    return doc


def list_cases(s: Session) -> list[dict[str, Any]]:
    return [dict(r.doc) for r in s.scalars(select(CaseRow).order_by(CaseRow.id))]


def vessels(s: Session, case_id: str) -> list[dict[str, Any]]:
    return list_docs(s, VesselRow, case_id)


def track_points(s: Session, case_id: str, vessel_id: str | None = None, from_sec: float | None = None,
                 to_sec: float | None = None) -> list[dict[str, Any]]:
    q = select(TrackPointRow).where(TrackPointRow.case_id == case_id)
    if vessel_id:
        q = q.where(TrackPointRow.vessel_id == vessel_id)
    if from_sec is not None:
        q = q.where(TrackPointRow.time_sec >= from_sec)
    if to_sec is not None:
        q = q.where(TrackPointRow.time_sec <= to_sec)
    q = q.order_by(TrackPointRow.vessel_id, TrackPointRow.time_sec)
    return [dict(r.doc) for r in s.scalars(q)]


def _lerp_angle(a: float, b: float, f: float) -> float:
    d = ((b - a + 540.0) % 360.0) - 180.0
    return (a + d * f) % 360.0


def state_at(points: list[dict[str, Any]], t: float) -> dict[str, Any] | None:
    """线性插值（仅用于服务端预览；Unity 端用 Hermite 插值 TrackInterpolator）。"""
    if not points:
        return None
    if t <= points[0]["timeSec"]:
        return dict(points[0])
    for a, b in zip(points, points[1:]):
        if a["timeSec"] <= t <= b["timeSec"]:
            # An exact recorded sample is not an interpolation. Preserve its metadata.
            # For duplicate timestamps, the first encountered recorded point wins.
            if t == b["timeSec"]:
                return dict(b)
            span = b["timeSec"] - a["timeSec"] or 1.0
            f = (t - a["timeSec"]) / span
            out = dict(a)
            out["timeSec"] = t
            for k in ("latDeg", "lonDeg", "sogKn"):
                out[k] = a[k] + (b[k] - a[k]) * f
            out["cogDeg"] = _lerp_angle(a["cogDeg"], b["cogDeg"], f)
            if a.get("hdgDeg") is not None and b.get("hdgDeg") is not None:
                out["hdgDeg"] = _lerp_angle(a["hdgDeg"], b["hdgDeg"], f)
            out["provenance"] = "Interpolated"
            return out
    return dict(points[-1])


def require_case_exists(s: Session, case_id: str) -> None:
    load_case(s, case_id)
