"""离线生成 W12 分析页种子 data/w12-analysis-seed.json（演示求稳：运行时不调用 mcis-core、不重算 W14）。

用法（在 service/ 下）：
    .venv/bin/python -m mcis_service.analysis.build_seed [W14导出.json]

输入：
- data/w12-w14-export.json：项目外临时目录里只读调用已冻结 W14.2 代码导出的对比表/临界/敏感性/航迹
  （导出工程见 logs/w12-export-howto.md；未改 unity/ 与 tools/mcis-core）。
- 曲线：全部由已构建的 mcis-core `cpa` 计算。
  · 虚构 Lily/Mary、海力5：沿用服务 GET /cases/{id}/cpa（案件航迹线性插值 → mcis-core cpa）。
  · W14 各情景（含 YANGZE 22 S0 报告航迹重建）：导出航迹每 STEP_S 秒取一点（东/北 m → 海里，航向作对地航向）→ mcis-core cpa。
- 交叉核对：W14 数值与 logs/w14.2-retest-sensitivity-dump.json / w14.2-retest-scenario-dump.json 逐项比较，不一致即中止。
输出种子内含全部输入文件的 sha256、mcis-core 版本与 dll sha256；同目录写 .sha256 旁注供运行时自检。
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ..colreg import core_client
from ..config import PROJECT_ROOT, Settings

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SEED = DATA / "w12-analysis-seed.json"
EXPORT = DATA / "w12-w14-export.json"
STEP_S = 2.0           # W14 情景曲线步长
CASE_STEP_S = 5.0      # 案件航迹曲线步长
TRACK_PLOT_STEP_S = 5  # 航迹图抽样
NM = 1852.0
TZ8 = timezone(timedelta(hours=8))

LILY = "CASE-2026-DEMO-LILY-MARY"
HAILI = "CASE-2025-HAILI5-WANA17"
YANGZE_CASE_JSON = PROJECT_ROOT / "reports" / "yangze22" / "case.json"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.resolve().relative_to(PROJECT_ROOT))


def src(p: Path, role: str) -> dict[str, str]:
    return {"path": rel(p), "sha256": sha256(p), "role": role}


def clock(epoch: datetime, t: float) -> str:
    """北京时间 HH:MM:SS[.cc]；小数秒截断到 0.01 s（与 W14 TcLocalText 一致）。"""
    cs = int((t + 1e-9) * 100)
    d = epoch + timedelta(seconds=cs // 100)
    frac = cs % 100
    return d.astimezone(TZ8).strftime("%H:%M:%S") + (f".{frac:02d}" if frac else "")


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def series_from_core(results: list[dict[str, Any]], epoch: datetime, cut_at: float | None) -> list[dict[str, Any]]:
    out = []
    for r in results:
        t = float(r["timeSec"])
        if cut_at is not None and t > cut_at + 1e-9:
            break
        out.append({"t": t, "clock": clock(epoch, t), "distanceNm": r.get("currentDistanceNm"), "dcpaNm": r.get("dcpaNm"),
                    "tcpaMin": r.get("tcpaMin"), "riskLevel": r.get("riskLevel"), "isDiverging": r.get("isDiverging")})
    return out


def curve_moments(series: list[dict[str, Any]], epoch: datetime) -> list[dict[str, Any]]:
    """从 mcis-core 曲线本身取：最小 DCPA（TCPA≥0 的点）、最小中心距（采样点）、首次进入 Danger。"""
    m: list[dict[str, Any]] = []
    approaching = [p for p in series if p["dcpaNm"] is not None and (p["tcpaMin"] or 0) >= 0]
    if approaching:
        p = min(approaching, key=lambda x: x["dcpaNm"])
        m.append({"kind": "minDcpa", "label": "最小 DCPA", "t": p["t"], "clock": p["clock"], "value": p["dcpaNm"], "unit": "nm",
                  "source": "mcis-core cpa 曲线（采样点）"})
    if series:
        p = min(series, key=lambda x: x["distanceNm"])
        m.append({"kind": "minDistanceSampled", "label": "最小中心距（曲线采样）", "t": p["t"], "clock": p["clock"],
                  "value": p["distanceNm"], "unit": "nm", "source": "mcis-core cpa 曲线（采样点）"})
    d = next((p for p in series if p["riskLevel"] == "Danger"), None)
    if d:
        m.append({"kind": "firstDanger", "label": "首次进入危险（Danger）", "t": d["t"], "clock": d["clock"], "value": d["dcpaNm"],
                  "unit": "nm", "source": "mcis-core cpa 风险等级"})
    return m


def core_cpa(core_cmd: str, pairs: list[dict[str, Any]]) -> dict[str, Any]:
    return core_client.run(core_cmd, "cpa", {"pairs": pairs}, timeout_s=120)


def scenario_series(core_cmd: str, row: dict[str, Any], own: str, target: str, epoch: datetime) -> tuple[list, str]:
    a = {int(round(s[0])): s for s in row["tracks"][own]["samples"]}
    b = {int(round(s[0])): s for s in row["tracks"][target]["samples"]}
    times = sorted(set(a) & set(b))
    t0, t1 = times[0], times[-1]
    cut = row["tcSeconds"] if row["collision"] else None
    pairs, t = [], float(t0)
    while t <= t1 + 1e-9:
        k = int(round(t))
        if cut is not None and t > cut + 1e-9:
            break
        sa, sb = a[k], b[k]
        pairs.append({"pairId": f"{row['id']}@{t:g}", "timeSec": t,
                      "own": {"vesselId": own, "eastNm": sa[1] / NM, "northNm": sa[2] / NM, "speedKn": sa[4], "courseDeg": sa[3] % 360},
                      "target": {"vesselId": target, "eastNm": sb[1] / NM, "northNm": sb[2] / NM, "speedKn": sb[4], "courseDeg": sb[3] % 360}})
        t += STEP_S
    env = core_cpa(core_cmd, pairs)
    return series_from_core(env["result"]["results"], epoch, None), env["coreVersion"]


def track_plot(row: dict[str, Any]) -> dict[str, list[list[float]]]:
    cut = row["tcSeconds"] if row["collision"] else None
    out = {}
    for vid, tr in row["tracks"].items():
        pts = [[s[0], round(s[1], 1), round(s[2], 1)] for s in tr["samples"]
               if int(round(s[0])) % TRACK_PLOT_STEP_S == 0 and (cut is None or s[0] <= cut + 1e-9)]
        out[vid] = pts
    return out


def whatif_block(core_cmd: str, study: dict[str, Any], vessels: list[dict[str, str]], epoch: datetime, label: str) -> tuple[dict, str]:
    own, target = vessels[0]["vesselId"], vessels[1]["vesselId"]
    rows, ver = [], ""
    for r in study["rows"]:
        series, ver = scenario_series(core_cmd, r, own, target, epoch)
        moments = []
        if r["collision"]:
            moments.append({"kind": "collision", "label": "碰撞（OBB 接触）", "t": r["tcSeconds"], "clock": r["tcLocal"], "value": 0.0,
                            "unit": "m", "source": "W14 ScenarioEvaluator"})
        moments.append({"kind": "minClearance", "label": "全程最小净距（船体外廓）", "t": r["minClearanceTimeSeconds"],
                        "clock": clock(epoch, r["minClearanceTimeSeconds"]), "value": r["minClearanceM"], "unit": "m",
                        "source": "W14 ScenarioEvaluator（全局最小）"})
        # 碰撞情景 W14 的最小中心距出现在接触之后（推演航迹穿越），不作关键时刻，只在表中保留数值
        if not (r["collision"] and r["minDistanceTimeSeconds"] > r["tcSeconds"]):
            moments.append({"kind": "minDistance", "label": "最小中心距", "t": r["minDistanceTimeSeconds"],
                            "clock": clock(epoch, r["minDistanceTimeSeconds"]), "value": r["minDistanceNm"], "unit": "nm",
                            "source": "W14 ScenarioEvaluator"})
        moments += curve_moments(series, epoch)
        moments.sort(key=lambda m: m["t"])
        out = {k: v for k, v in r.items() if k != "tracks"}
        out.update({"series": series, "keyMoments": moments, "trackPlot": track_plot(r),
                    "vesselDims": {vid: {"loaM": tr["loaM"], "beamM": tr["beamM"]} for vid, tr in r["tracks"].items()}})
        rows.append(out)
    block = {k: study[k] for k in ("criticalMarginM", "disclaimer", "markdown", "assumptions", "inputs", "antennaSensitivity")}
    block.update({"label": label, "epochLocal": study["epochLocal"], "ownVesselId": own, "targetVesselId": target,
                  "safeDistanceM": rows[0]["safeDistanceM"], "stepSec": STEP_S, "rows": rows,
                  "curveNote": f"曲线：W14 航迹每 {STEP_S:g} s 取点（航向作对地航向）→ mcis-core cpa；碰撞情景截至碰撞时刻。"})
    for k in ("originalDeviation", "combinedNote", "reportCollisionLocal"):
        if k in study:
            block[k] = study[k]
    return block, ver


def db_baseline(c, cid: str) -> dict[str, Any]:
    H = {"X-MCIS-Role": "Investigator"}
    case = c.get(f"/api/v1/cases/{cid}", headers=H).json()
    vs = c.get(f"/api/v1/cases/{cid}/vessels", headers=H).json()
    cpa = c.get(f"/api/v1/cases/{cid}/cpa?stepSec={CASE_STEP_S:g}", headers=H)
    cpa.raise_for_status()
    cpa = cpa.json()
    epoch = parse_iso(case["caseEpochUtc"])
    tc = (parse_iso(case["incidentTimeUtc"]) - epoch).total_seconds()
    series = series_from_core(cpa["results"], epoch, tc)
    moments = [{"kind": "collision", "label": "碰撞（案件事故时间）", "t": tc, "clock": clock(epoch, tc), "value": None, "unit": "",
                "source": "案件 incidentTimeUtc"}] + curve_moments(series, epoch)
    moments.sort(key=lambda m: m["t"])
    return {"case": case, "vessels": [{"vesselId": v["vesselId"], "name": v.get("name") or v["vesselId"]} for v in vs[:2]],
            "epoch": epoch, "thresholds": cpa["thresholds"], "coreVersion": cpa["coreVersion"],
            "baseline": {"label": "案件航迹（服务 /cases/{id}/cpa，线性插值 → mcis-core cpa）", "stepSec": CASE_STEP_S,
                         "cutAtSec": tc, "series": series, "keyMoments": moments}}


def crosscheck(export: dict[str, Any]) -> dict[str, Any]:
    """W14 导出与 Codex 复测留档逐项一致（1e-6），否则中止。"""
    sens_p = PROJECT_ROOT / "logs" / "w14.2-retest-sensitivity-dump.json"
    scen_p = PROJECT_ROOT / "logs" / "w14.2-retest-scenario-dump.json"
    sens = json.loads(sens_p.read_text(encoding="utf-8-sig"))
    scen = json.loads(scen_p.read_text(encoding="utf-8-sig"))
    worst = 0.0
    checked = 0

    def cmp(a, b, what):
        nonlocal worst, checked
        if a is None and b is None:
            return
        d = abs(float(a) - float(b))
        worst = max(worst, d)
        checked += 1
        if d > 1e-6:
            raise SystemExit(f"交叉核对失败：{what} 导出 {a} vs 留档 {b}")

    yrows = {r["id"]: r for r in export["yangze22"]["rows"]}
    for r in sens["default"]["results"]:
        e = yrows[r["id"]]
        cmp(e["minClearanceM"], r["minClearanceM"], f"YANGZE {r['id']} minClearanceM")
        cmp(e["minClearanceTimeSeconds"], r["minClearanceTime"], f"YANGZE {r['id']} minClearanceTime")
        cmp(e["tcSeconds"], r.get("tcSeconds"), f"YANGZE {r['id']} tc")
        if e["verdict"] != r["verdict"]:
            raise SystemExit(f"交叉核对失败：YANGZE {r['id']} verdict")
    if yrows["Y1"]["isCritical"] != sens["default"]["y1Critical"] or yrows["Y1"]["displayVerdictText"] != sens["default"]["y1Display"] \
            or yrows["Y1"]["sensitivityRangeText"] != sens["default"]["y1Range"]:
        raise SystemExit("交叉核对失败：Y1 临界标注")
    ant = {(a["yangzeAftRatio"], a["vegaAftRatio"]): a for a in export["yangze22"]["antennaSensitivity"]}
    for s in sens["sensitivity"]:
        a = ant[(s["yangzeAft"], s["vegaAft"])]
        for r in s["results"]:
            cmp(a["outcomes"][r["id"]]["minClearanceM"], r["minClearanceM"], f"敏感性 {s['label']} {r['id']}")
    for key in ("demo", "yangze22"):
        er = {r["id"]: r for r in export[key]["rows"]}
        for r in scen[key]["results"]:
            e = er[r["id"]]
            cmp(e["minClearanceM"], r["minClearanceM"], f"{key} {r['id']} minClearanceM")
            cmp(e["minDistanceNm"], r["minDistanceNm"], f"{key} {r['id']} minDistanceNm")
            cmp(e["tcSeconds"], r["tcSeconds"], f"{key} {r['id']} tc")
            if e["tcLocal"] != r["tcLocal"]:
                raise SystemExit(f"交叉核对失败：{key} {r['id']} tcLocal")
    return {"against": [rel(sens_p), rel(scen_p)], "sha256": {rel(sens_p): sha256(sens_p), rel(scen_p): sha256(scen_p)},
            "valuesCompared": checked, "maxAbsDiff": worst, "tolerance": 1e-6, "ok": True}


def build(export_path: Path = EXPORT) -> dict[str, Any]:
    from fastapi.testclient import TestClient
    from ..main import create_app

    export = json.loads(export_path.read_text(encoding="utf-8"))
    xc = crosscheck(export)
    settings = Settings()
    core_cmd = settings.core_cmd
    dll = Path(core_cmd).resolve().parent / "out" / "mcis-core.dll"
    tmp = Path(tempfile.mkdtemp(prefix="w12-seed-"))
    st = Settings()
    st.data_dir = tmp
    st.db_url = f"sqlite:///{tmp / 'seed.db'}"
    st.seed_demo = True
    with TestClient(create_app(st)) as c:
        lily = db_baseline(c, LILY)
        haili = db_baseline(c, HAILI)

    cases = []
    # ---- 虚构 Lily/Mary
    demo_epoch = parse_iso(export["demo"]["epochLocal"])
    demo_vessels = [{"vesselId": "Mary", "name": "Mary"}, {"vesselId": "Lily", "name": "Lily"}]
    demo_block, ver = whatif_block(core_cmd, export["demo"], demo_vessels, demo_epoch, "W14 虚构演示情景（WhatIfDemoFixture）")
    cases.append({
        "caseId": LILY, "key": "lily-mary", "title": lily["case"]["title"], "isFictionalDemo": True,
        "sourceLabel": "虚构演示数据（与任何真实事故无关）",
        "sourceRefs": [src(PROJECT_ROOT / "service/mcis_service/seed/lily_mary.py", "案件航迹/事故时间（虚构种子）"),
                       src(PROJECT_ROOT / "unity/Assets/_Project/Scripts/Simulation/WhatIf/Demo/WhatIfDemoFixture.cs", "W14 虚构情景设定（只读）")],
        "epochLocal": demo_epoch.isoformat(), "timeZone": "UTC+8", "vessels": lily["vessels"], "thresholds": lily["thresholds"],
        "baseline": lily["baseline"], "whatif": demo_block,
        "notes": ["案件航迹曲线与 W14 情景曲线来自不同航迹模型：前者为种子航迹线性插值，后者为 Nomoto 操纵模型推演；W14 S0 碰撞 14:23:59.96，案件事故时间 14:24:00。"],
    })
    # ---- 海力5（真实，W14 未建情景）
    cases.append({
        "caseId": HAILI, "key": "haili5", "title": haili["case"]["title"], "isFictionalDemo": False,
        "sourceLabel": "真实案例 · 公开事故调查报告（Mark 2026-11-11 确认可用）",
        "sourceRefs": [src(PROJECT_ROOT / "reports/haili5/case.json", "报告结构化字段"),
                       src(PROJECT_ROOT / "reports/haili5/tracks_from_report.csv", "报告航迹点"),
                       src(PROJECT_ROOT / "service/mcis_service/colreg/haili5_seed.py", "服务种子（只收录报告给出经纬度的点）")],
        "epochLocal": haili["epoch"].astimezone(TZ8).isoformat(), "timeZone": "UTC+8", "vessels": haili["vessels"],
        "thresholds": haili["thresholds"], "baseline": haili["baseline"], "whatif": None,
        "notes": ["W14 What-if 只建了虚构演示与 YANGZE 22 情景，本案无反事实对比表与天线敏感性。",
                  "航迹点只取报告给出经纬度的时刻，中间线性插值；曲线截至报告碰撞时刻 19:54:32。"],
    })
    # ---- YANGZE 22（真实）
    ycase = json.loads(YANGZE_CASE_JSON.read_text(encoding="utf-8"))
    y_epoch = parse_iso(export["yangze22"]["epochLocal"])
    y_vessels = [{"vesselId": v["vesselId"], "name": v["name"]} for v in ycase["vessels"]][:2]
    y_block, ver = whatif_block(core_cmd, export["yangze22"], y_vessels, y_epoch, "W14 YANGZE 22 情景（Yangze22Case）")
    s0 = next(r for r in y_block["rows"] if r["id"] == "S0")
    rep_t = (parse_iso(export["yangze22"]["reportCollisionLocal"]) - y_epoch).total_seconds()
    base_moments = [m for m in s0["keyMoments"]] + [{"kind": "reportCollision", "label": "报告碰撞时刻", "t": rep_t,
                                                     "clock": clock(y_epoch, rep_t), "value": None, "unit": "",
                                                     "source": "reports/yangze22/case.json collision.time"}]
    base_moments.sort(key=lambda m: m["t"])
    cases.append({
        "caseId": ycase["caseId"], "key": "yangze22", "title": ycase["title"], "isFictionalDemo": False,
        "sourceLabel": "真实案例 · 公开事故调查报告（Mark 2026-11-11 确认可用）",
        "sourceRefs": [src(YANGZE_CASE_JSON, "报告结构化字段（船型/舵令/碰撞）"),
                       src(PROJECT_ROOT / "reports/yangze22/tracks_from_report.csv", "报告航迹点")],
        "epochLocal": y_epoch.isoformat(), "timeZone": "UTC+8", "vessels": y_vessels, "thresholds": lily["thresholds"],
        "baseline": {"label": "W14 S0 原始航迹回放（报告航迹重建，天线改正 YANGZE 0.20L / VEGA 0.375L【估计】）→ mcis-core cpa",
                     "stepSec": STEP_S, "cutAtSec": s0["tcSeconds"], "series": s0["series"], "keyMoments": base_moments},
        "whatif": y_block,
        "notes": ["本案未接入服务数据库（无 /cases/{id}），基线曲线取 W14 S0 报告航迹重建。", export["yangze22"]["originalDeviation"]],
    })

    return {
        "schemaVersion": "w12-analysis-seed/1",
        "generatedAt": datetime.now(TZ8).isoformat(timespec="seconds"),
        "generator": "service/mcis_service/analysis/build_seed.py",
        "coreVersion": ver, "coreDll": {"path": rel(dll), "sha256": sha256(dll)},
        "w14Export": {**src(export_path, "W14.2 导出（项目外临时目录只读运行，见 logs/w12-export-howto.md）"),
                      "exporter": export.get("exporter"), "generatedAtUtc": export.get("generatedAtUtc")},
        "w14Frozen": src(PROJECT_ROOT / "logs" / "w14.2-impl-hashes-frozen.txt", "W14.2 冻结清单"),
        "crossCheck": xc,
        "disclaimer": "仅供分析参考：What-if 为简化操纵模型的反事实推演；本页仅作安全调查技术分析，不作责任认定。",
        "cases": cases,
    }


def main(argv: list[str]) -> None:
    export_path = Path(argv[1]) if len(argv) > 1 else EXPORT
    doc = build(export_path)
    text = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    SEED.write_text(text, encoding="utf-8")
    SEED.with_suffix(".sha256").write_text(sha256(SEED) + "  " + SEED.name + "\n", encoding="utf-8")
    print(f"wrote {rel(SEED)} {len(text)} bytes sha256={sha256(SEED)} cases={[c['key'] for c in doc['cases']]} "
          f"crossCheck={doc['crossCheck']['valuesCompared']} values maxdiff={doc['crossCheck']['maxAbsDiff']}")


if __name__ == "__main__":
    main(sys.argv)
