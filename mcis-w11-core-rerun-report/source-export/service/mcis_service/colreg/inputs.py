"""evaluate 输入：vesselStatus 合同形态（W6.1 裁定 1）与 mcis-core 形态之间的转换。

合同（openapi）：{vesselId: [{fromUtc: ISO 8601 UTC, status}]}，按时间排序。
mcis-core colreg：[{vesselId, timeSec, status}]（timeSec 相对 caseEpochUtc）。
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from ..common.context import problem
from ..common.timeutil import iso_ms, parse_iso

VESSEL_STATUS = ("PowerDriven", "NotUnderCommand", "RestrictedManoeuvrability", "ConstrainedByDraught",
                 "Fishing", "Sailing", "Unknown")


def _parse_utc(s: Any) -> Any:
    if not isinstance(s, str) or not s.strip():
        raise ValueError("fromUtc 必须是 ISO 8601 UTC 字符串")
    txt = s.strip()
    if not (txt.endswith("Z") or txt.endswith("+00:00")):
        raise ValueError(f"fromUtc 必须是 UTC（以 Z 或 +00:00 结尾）：{s}")
    return parse_iso(txt)


def to_core(vessel_status: Any, case_epoch_utc: str, vessel_ids: set[str] | None = None) -> list[dict[str, Any]]:
    """合同对象 → core 列表。也接受服务内部旧存档的 core 列表（只用于读取早期播种的 inputs）。"""
    if vessel_status is None:
        return []
    if isinstance(vessel_status, list):  # 旧存档形态（W6 播种的海力5 inputs），只做原样透传
        return [dict(x) for x in vessel_status]
    if not isinstance(vessel_status, dict):
        raise problem(422, "VALIDATION_ERROR", "vesselStatus 必须是以船 id 为键的对象")
    epoch = parse_iso(case_epoch_utc)
    out: list[dict[str, Any]] = []
    errors: list[str] = []
    for vid, items in vessel_status.items():
        if vessel_ids is not None and vid not in vessel_ids:
            errors.append(f"{vid}: 本案件没有这艘船")
            continue
        if not isinstance(items, list):
            errors.append(f"{vid}: 值必须是 [{{fromUtc, status}}] 列表")
            continue
        rows = []
        for i, it in enumerate(items):
            if not isinstance(it, dict) or "fromUtc" not in it or "status" not in it:
                errors.append(f"{vid}[{i}]: 需要 fromUtc 与 status")
                continue
            if it["status"] not in VESSEL_STATUS:
                errors.append(f"{vid}[{i}]: status 取值不合法：{it['status']}")
                continue
            try:
                t = _parse_utc(it["fromUtc"])
            except ValueError as e:
                errors.append(f"{vid}[{i}]: {e}")
                continue
            rows.append({"vesselId": vid, "timeSec": round((t - epoch).total_seconds(), 3), "status": it["status"]})
        rows.sort(key=lambda r: r["timeSec"])
        out.extend(rows)
    if errors:
        raise problem(422, "VALIDATION_ERROR", "vesselStatus 不符合合同（{vesselId: [{fromUtc, status}]}）", errors[:20])
    return out


def from_core(rows: list[dict[str, Any]], case_epoch_utc: str) -> dict[str, list[dict[str, str]]]:
    """core 列表 → 合同对象（用于把旧存档显示/回写成合同形态）。"""
    epoch = parse_iso(case_epoch_utc)
    out: dict[str, list[dict[str, str]]] = {}
    for r in sorted(rows, key=lambda r: float(r.get("timeSec", 0))):
        out.setdefault(r["vesselId"], []).append(
            {"fromUtc": iso_ms(epoch + timedelta(seconds=float(r.get("timeSec", 0)))), "status": r["status"]})
    return out
