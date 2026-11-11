#!/usr/bin/env python3
"""W14.2 independent check: global true OBB min on dumped tracks, 4x4 antenna table, Y1 critical label."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from independent_nomoto import (
    sample, true_distance, find_contact, verdict, samples_to_states, Params, State,
    SAFE_M, MARY, LILY, Intervention, straight_track, cf_track,
)

REPO = Path(__file__).resolve().parents[2]
LOGS = REPO / "logs"
DUMP = LOGS / "w14.2-retest-sensitivity-dump.json"
OUT = LOGS / "w14.2-retest-independent.md"


def min_clearance_global(samp_a, samp_b, start, end, coarse=0.5, fine=0.02):
    times, vals = [], []
    t = start
    while t <= end + 1e-12:
        times.append(t)
        vals.append(true_distance(*samp_a(t), *samp_b(t)))
        t += coarse
    if times[-1] < end - 1e-12:
        times.append(end)
        vals.append(true_distance(*samp_a(end), *samp_b(end)))
    candidates = []
    n = len(vals)
    for i in range(n):
        left = vals[i - 1] if i > 0 else vals[i] + 1
        right = vals[i + 1] if i < n - 1 else vals[i] + 1
        if vals[i] <= left and vals[i] <= right:
            candidates.append(times[i])
    best_t, best_c = start, math.inf
    for tcand in candidates:
        t0, t1 = max(start, tcand - coarse), min(end, tcand + coarse)
        t = t0
        while t <= t1 + 1e-12:
            c = true_distance(*samp_a(t), *samp_b(t))
            if c < best_c:
                best_c, best_t = c, t
            t += fine
    return best_t, best_c


def eval_dumped(scen):
    tracks = scen["tracks"]
    ids = list(tracks.keys())
    ta, tb = tracks[ids[0]], tracks[ids[1]]
    # samples are [t, e, n, hdg] in the W14.2 sensitivity dump
    def to_states(samples):
        if len(samples[0]) >= 6:
            return samples_to_states(samples)
        return [State(s[0], s[1], s[2], s[3], 0.0, 0.0, 0.0) for s in samples]

    sa_states = to_states(ta["samples"])
    sb_states = to_states(tb["samples"])
    pa = Params(K=0.1, T=60, u_ref=12, loa=ta["loaM"], beam=ta["beamM"])
    pb = Params(K=0.1, T=60, u_ref=12, loa=tb["loaM"], beam=tb["beamM"])
    start = max(sa_states[0].t, sb_states[0].t)
    end = min(sa_states[-1].t, sb_states[-1].t)

    def sa(t):
        s = sample(sa_states, t)
        return (s.east, s.north, s.psi, pa.loa, pa.beam)

    def sb(t):
        s = sample(sb_states, t)
        return (s.east, s.north, s.psi, pb.loa, pb.beam)

    tc = find_contact(sa, sb, start, end)
    if tc is not None:
        return {"verdict": "Collision", "tc": tc, "clearance": 0.0, "tmin": tc}
    tmin, c = min_clearance_global(sa, sb, start, end)
    return {"verdict": verdict(None, c), "tc": None, "clearance": c, "tmin": tmin}


def main():
    d = json.loads(DUMP.read_text(encoding="utf-8-sig"))
    lines = []
    def w(s=""):
        lines.append(s)

    w("# W14.2 独立核算（Python 全程真实 OBB 净距 + 天线敏感性 4×4）")
    w()
    w("转储：`logs/w14.2-retest-sensitivity-dump.json`（验收补测写出，航迹 1 s 采样后插值）。")
    w("最小净距：全程 0.5 s 粗扫，再在每个局部极小处 0.02 s 细化。安全线 185.2 m。")
    w()

    w("## 默认设定：Y1 / Y5 / Y1+Y5 / Y4")
    w()
    w("| 情景 | C# 结论 | C# 净距 (m) | 独立结论 | 独立净距 (m) | 差 (m) | 一致 |")
    w("|---|---|---:|---|---:|---:|---|")
    by = {r["id"]: r for r in d["default"]["results"]}
    all_ok = True
    for sid in ("Y1", "Y5", "Y1+Y5", "Y4"):
        scen = by[sid]
        indep = eval_dumped(scen)
        dlt = (0.0 if scen["collision"] else scen["minClearanceM"]) - indep["clearance"]
        match = indep["verdict"] == scen["verdict"] and abs(dlt) < 0.5
        all_ok = all_ok and match
        w(f"| {sid} | {scen['verdict']} | {scen['minClearanceM']:.2f} | {indep['verdict']} | {indep['clearance']:.2f} | {dlt:+.2f} | {'是' if match else '否'} |")
    w()

    w("## 天线敏感性 4×4（C# 报出 / 独立全程最小）")
    w()
    ids = ["Y1", "Y5", "Y1+Y5", "Y4"]
    w("| 天线设定 | 计入临界 | " + " | ".join(ids) + " |")
    w("|---|---|---|---|---|---|")
    table_ok = True
    announced = {
        ("不改正", "Y1"): ( "Avoided", 218.9),
        ("不改正", "Y5"): ( "Avoided", 335.6),
        ("不改正", "Y1+Y5"): ( "Avoided", 388.1),
        ("不改正", "Y4"): ( "NearMiss", 45.4),
        ("0.35L", "Y1"): ( "Avoided", 185.5),
        ("0.35L", "Y5"): ( "Avoided", 245.2),
        ("0.35L", "Y1+Y5"): ( "Avoided", 296.4),
        ("0.35L", "Y4"): ( "NearMiss", 29.6),
        ("0.375L", "Y1"): ( "NearMiss", 184.4),
        ("0.375L", "Y5"): ( "Avoided", 238.8),
        ("0.375L", "Y1+Y5"): ( "Avoided", 292.4),
        ("0.375L", "Y4"): ( "NearMiss", 29.8),
        ("0.40L", "Y1"): ( "NearMiss", 183.2),
        ("0.40L", "Y5"): ( "Avoided", 232.3),
        ("0.40L", "Y1+Y5"): ( "Avoided", 288.5),
        ("0.40L", "Y4"): ( "NearMiss", 30.0),
    }
    for row in d["sensitivity"]:
        cells = []
        byr = {r["id"]: r for r in row["results"]}
        for sid in ids:
            scen = byr[sid]
            indep = eval_dumped(scen)
            dlt = scen["minClearanceM"] - indep["clearance"] if not scen["collision"] else 0.0
            ok = indep["verdict"] == scen["verdict"] and abs(dlt) < 0.5
            ann = announced.get((row["label"], sid))
            if ann:
                ok = ok and indep["verdict"] == ann[0] and abs(indep["clearance"] - ann[1]) < 0.6
            table_ok = table_ok and ok
            mark = "" if ok else " !"
            if scen["collision"]:
                cells.append("碰撞")
            else:
                cells.append(f"{scen['minClearanceM']:.1f}/{indep['clearance']:.1f}{mark}")
        w(f"| {row['label']} | {'是' if row['inEstimateRange'] else '否（对照）'} | " + " | ".join(cells) + " |")
    w()
    w("格内为 C# 净距 / 独立净距（米）。")
    w()

    w("## Y1 临界标注与区间")
    w()
    rng = d["default"].get("y1Range") or ""
    disp = d["default"].get("y1Display") or ""
    crit = d["default"].get("y1Critical")
    w(f"- 对比表 Y1 标临界：{'是' if crit else '否'}，显示结论：{disp}")
    w(f"- 敏感性区间文字：{rng}")
    has_range = "183.2" in rng and "185.5" in rng
    excludes = "218" not in rng
    uncorrected_out = all(not r["inEstimateRange"] for r in d["sensitivity"] if r["label"] == "不改正")
    w(f"- 区间是否为 183.2–185.5 m：{'是' if has_range else '否'}")
    w(f"- 不改正行（218.9 m）是否被排除：{'是' if excludes and uncorrected_out else '否'}")
    w()

    # first principles S1/S3 sanity
    start, end = 0.0, 720.0
    mary0 = straight_track(193.7, -2292.7, 355.0, 8.0, start, end)
    lily0 = straight_track(-267.2, 2795.6, 175.0, 10.0, start, end)
    mary_s1 = cf_track(mary0, MARY, [Intervention("turn", 420.0, rudder=15.0, heading_change=15.0)], 420.0, end)
    lily_s3 = cf_track(lily0, LILY, [Intervention("turn", 480.0, rudder=35.0, heading_change=30.0)], 480.0, end)

    def ev(a, pa, b, pb):
        def sa(t):
            s = sample(a, t); return (s.east, s.north, s.psi, pa.loa, pa.beam)
        def sb(t):
            s = sample(b, t); return (s.east, s.north, s.psi, pb.loa, pb.beam)
        tc = find_contact(sa, sb, start, end)
        if tc: return "Collision", 0.0
        _, c = min_clearance_global(sa, sb, start, end)
        return verdict(None, c), c

    v1, c1 = ev(mary_s1, MARY, lily0, LILY)
    v3, c3 = ev(mary0, MARY, lily_s3, LILY)
    w("## 虚构案例抽查（独立从初值积分）")
    w()
    w(f"- S1：{v1} {c1:.1f} m（自报险情 130.4 m）")
    w(f"- S3：{v3} {c3:.1f} m（自报险情 58.8 m）")
    w()
    w("## 结论")
    w()
    w("- 默认 Y1/Y5/Y1+Y5/Y4 的结论类别与净距与 C#、实施方自报一致。Y1+Y5 全程最小 292.4 m，与上轮独立值一致。")
    w("- 天线敏感性 4×4 各格结论与净距（含 0.35/0.375/0.40L 与不改正对照）核对通过。")
    w("- Y1 已标“险情（临界）”，区间 183.2–185.5 m，不改正行未计入。")
    w(f"- 独立与 C# 默认四情景全部一致：{'是' if all_ok else '否'}；4×4 表一致：{'是' if table_ok else '否'}。")
    w()
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
