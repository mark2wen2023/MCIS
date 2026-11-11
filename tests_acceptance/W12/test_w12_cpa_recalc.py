"""用已构建的 tools/mcis-core cpa 独立重算三案例 D/DCPA/TCPA 曲线，抽样比对种子。不重编核心。"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from mcis_service.colreg import core_client

from conftest import CASE_IDS, CORE_CMD, HAILI, HAS_CORE, LILY, NM, ROOT, YANGZE, get_analysis

EXPORT = json.loads((ROOT / "service/mcis_service/analysis/data/w12-w14-export.json").read_text(encoding="utf-8"))
SEED = json.loads((ROOT / "service/mcis_service/analysis/data/w12-analysis-seed.json").read_text(encoding="utf-8"))
DIFF_LOG = ROOT / "logs" / "w12-retest-cpa-diffs.txt"
ABS_TOL = 1e-6
# 案件航迹基线按 5 s；W14 情景（含 YANGZE 基线）按 2 s，与 build_seed 一致。
CASE_STEP = 5.0
W14_STEP = 2.0


def _lerp_angle(a: float, b: float, f: float) -> float:
    d = ((b - a + 540.0) % 360.0) - 180.0
    return (a + d * f) % 360.0


def _state_at(points: list[dict], t: float) -> dict:
    """独立线性插值（lat/lon/sog 线性，航向按最短角插值）。不调用服务端 state_at。"""
    pts = sorted(points, key=lambda p: p["timeSec"])
    if t <= pts[0]["timeSec"]:
        return dict(pts[0])
    for a, b in zip(pts, pts[1:]):
        if a["timeSec"] <= t <= b["timeSec"]:
            span = b["timeSec"] - a["timeSec"] or 1.0
            f = (t - a["timeSec"]) / span
            out = dict(a)
            out["timeSec"] = t
            for k in ("latDeg", "lonDeg", "sogKn"):
                out[k] = a[k] + (b[k] - a[k]) * f
            out["cogDeg"] = _lerp_angle(a["cogDeg"], b["cogDeg"], f)
            return out
    return dict(pts[-1])


def _core_cpa(pairs: list[dict], origin: dict | None = None) -> list[dict]:
    payload: dict = {"pairs": pairs}
    if origin is not None:
        payload["origin"] = origin
    env = core_client.run(CORE_CMD, "cpa", payload, timeout_s=180)
    return env["result"]["results"]


def _cmp_series(seed_series: list[dict], core_results: list[dict], label: str) -> dict:
    """按 timeSec 对齐，比较 distanceNm / dcpaNm / tcpaMin。"""
    by_t = {round(float(r["timeSec"]), 3): r for r in core_results}
    n = 0
    max_d = max_dcpa = max_tcpa = 0.0
    misses = []
    samples = []
    for i, p in enumerate(seed_series):
        r = by_t.get(round(float(p["t"]), 3))
        if r is None:
            misses.append(p["t"])
            continue
        n += 1
        dd = abs((r.get("currentDistanceNm") or 0) - (p.get("distanceNm") or 0))
        ddcpa = abs((r.get("dcpaNm") or 0) - (p.get("dcpaNm") or 0)) if p.get("dcpaNm") is not None and r.get("dcpaNm") is not None else 0.0
        dtcpa = abs((r.get("tcpaMin") or 0) - (p.get("tcpaMin") or 0)) if p.get("tcpaMin") is not None and r.get("tcpaMin") is not None else 0.0
        max_d = max(max_d, dd)
        max_dcpa = max(max_dcpa, ddcpa)
        max_tcpa = max(max_tcpa, dtcpa)
        if i in (0, len(seed_series) // 2, len(seed_series) - 1) or i % 20 == 0:
            samples.append({"t": p["t"], "d": dd, "dcpa": ddcpa, "tcpa": dtcpa})
    return {"label": label, "n": n, "misses": misses, "maxAbsDistanceNm": max_d,
            "maxAbsDcpaNm": max_dcpa, "maxAbsTcpaMin": max_tcpa, "samples": samples,
            "maxAbs": max(max_d, max_dcpa, max_tcpa)}


def _tracks_from_client(client, cid: str):
    H = {"X-MCIS-Role": "Investigator"}
    case = client.get(f"/api/v1/cases/{cid}", headers=H).json()
    vs = client.get(f"/api/v1/cases/{cid}/vessels", headers=H).json()
    tr = client.get(f"/api/v1/cases/{cid}/tracks", headers=H).json()
    by: dict[str, list] = {}
    if isinstance(tr, dict) and isinstance(tr.get("tracks"), list):
        for item in tr["tracks"]:
            by[item["vesselId"]] = list(item["points"])
    elif isinstance(tr, list):
        for p in tr:
            by.setdefault(p["vesselId"], []).append(p)
    else:
        raise AssertionError(f"未识别的 tracks 形态：{type(tr)} keys={list(tr)[:8] if isinstance(tr, dict) else ''}")
    own, target = vs[0]["vesselId"], vs[1]["vesselId"]
    loc = case["incidentLocation"]
    epoch = datetime.fromisoformat(case["caseEpochUtc"].replace("Z", "+00:00"))
    incident = datetime.fromisoformat(case["incidentTimeUtc"].replace("Z", "+00:00"))
    cut = (incident - epoch).total_seconds()
    return by, own, target, {"latDeg": loc["latDeg"], "lonDeg": loc["lonDeg"]}, cut


def _pairs_geo(by, own, target, times):
    pairs = []
    for t in times:
        a, b = _state_at(by[own], t), _state_at(by[target], t)
        pairs.append({
            "pairId": f"{own}|{target}@{t:g}", "timeSec": t,
            "own": {"vesselId": own, "latDeg": a["latDeg"], "lonDeg": a["lonDeg"], "speedKn": a["sogKn"], "courseDeg": a["cogDeg"]},
            "target": {"vesselId": target, "latDeg": b["latDeg"], "lonDeg": b["lonDeg"], "speedKn": b["sogKn"], "courseDeg": b["cogDeg"]},
        })
    return pairs


def _pairs_enu(row: dict, own: str, target: str, step: float):
    a = {int(round(s[0])): s for s in row["tracks"][own]["samples"]}
    b = {int(round(s[0])): s for s in row["tracks"][target]["samples"]}
    times = sorted(set(a) & set(b))
    t0, t1 = times[0], times[-1]
    cut = row["tcSeconds"] if row.get("collision") else None
    pairs, t = [], float(t0)
    while t <= t1 + 1e-9:
        if cut is not None and t > cut + 1e-9:
            break
        k = int(round(t))
        sa, sb = a[k], b[k]
        pairs.append({
            "pairId": f"{row['id']}@{t:g}", "timeSec": t,
            "own": {"vesselId": own, "eastNm": sa[1] / NM, "northNm": sa[2] / NM, "speedKn": sa[4], "courseDeg": sa[3] % 360},
            "target": {"vesselId": target, "eastNm": sb[1] / NM, "northNm": sb[2] / NM, "speedKn": sb[4], "courseDeg": sb[3] % 360},
        })
        t += step
    return pairs


@pytest.mark.skipif(not HAS_CORE, reason="需要 dotnet + 已构建 mcis-core.dll")
def test_independent_mcis_core_cpa_matches_seed(client):
    reports = []

    # 1) Lily/Mary、海力5：案件航迹（服务库存原始点 → 本文件独立插值 → mcis-core）
    seed_by_id = {c["caseId"]: c for c in SEED["cases"]}
    for cid in (LILY, HAILI):
        by, own, target, origin, cut = _tracks_from_client(client, cid)
        series = seed_by_id[cid]["baseline"]["series"]
        times = [p["t"] for p in series]
        # 种子曲线截至事故时刻；不应超出 cut
        assert times[-1] <= cut + 1e-6
        results = _core_cpa(_pairs_geo(by, own, target, times), origin)
        reports.append(_cmp_series(series, results, f"{cid} baseline"))

    # 2) YANGZE 22 基线 = W14 S0 报告航迹重建
    yrow = next(r for r in EXPORT["yangze22"]["rows"] if r["id"] == "S0")
    own, tgt = "yangze22", "vega_dream"
    yseries = seed_by_id[YANGZE]["baseline"]["series"]
    results = _core_cpa(_pairs_enu(yrow, own, tgt, W14_STEP))
    reports.append(_cmp_series(yseries, results, f"{YANGZE} baseline(=S0)"))

    # 3) W14 情景曲线（虚构 S0–S3，YANGZE S0/Y1/Y5/Y1+Y5/Y4）
    demo_map = {r["id"]: r for r in EXPORT["demo"]["rows"]}
    lily_seed_rows = {r["id"]: r for r in seed_by_id[LILY]["whatif"]["rows"]}
    for sid in ("S0", "S1", "S2", "S3"):
        results = _core_cpa(_pairs_enu(demo_map[sid], "Mary", "Lily", W14_STEP))
        reports.append(_cmp_series(lily_seed_rows[sid]["series"], results, f"demo {sid}"))

    yexp = {r["id"]: r for r in EXPORT["yangze22"]["rows"]}
    yseed = {r["id"]: r for r in seed_by_id[YANGZE]["whatif"]["rows"]}
    for sid in ("S0", "Y1", "Y5", "Y1+Y5", "Y4"):
        results = _core_cpa(_pairs_enu(yexp[sid], own, tgt, W14_STEP))
        reports.append(_cmp_series(yseed[sid]["series"], results, f"yangze22 {sid}"))

    lines = ["# W12 独立 mcis-core cpa 重算 vs 种子", f"# 容差 {ABS_TOL}", ""]
    worst = 0.0
    for r in reports:
        worst = max(worst, r["maxAbs"])
        lines.append(
            f"{r['label']}: n={r['n']} max|D|={r['maxAbsDistanceNm']:.3e} nm  "
            f"max|DCPA|={r['maxAbsDcpaNm']:.3e} nm  max|TCPA|={r['maxAbsTcpaMin']:.3e} min  "
            f"misses={len(r['misses'])}"
        )
    DIFF_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")

    for r in reports:
        assert r["n"] == len(SEED["cases"][0]["baseline"]["series"]) or r["n"] > 50, r
        assert not r["misses"], f"{r['label']} 有未对齐的采样时刻 {r['misses'][:5]}"
        assert r["maxAbsDistanceNm"] <= ABS_TOL, f"{r['label']} 距离偏差 {r['maxAbsDistanceNm']}"
        assert r["maxAbsDcpaNm"] <= ABS_TOL, f"{r['label']} DCPA 偏差 {r['maxAbsDcpaNm']}"
        assert r["maxAbsTcpaMin"] <= ABS_TOL, f"{r['label']} TCPA 偏差 {r['maxAbsTcpaMin']}"
    # 把总偏差挂到测试报告，便于验收汇报
    test_independent_mcis_core_cpa_matches_seed.worst = worst  # type: ignore[attr-defined]
    test_independent_mcis_core_cpa_matches_seed.reports = reports  # type: ignore[attr-defined]
