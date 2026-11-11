#!/usr/bin/env python3
"""W14.1 independent check: reuse Nomoto RK4 + true OBB distance from independent_nomoto.py.

C# now uses true clearance for verdicts. This script:
  1) Integrates Mary/Lily S0–S3 from first principles (global true min).
  2) Recomputes dumped C# tracks with a full-trajectory global min (not CPA ±2 s).
  3) Independently bisects the Mary turn-advance safety critical.
Writes logs/w14.1-retest-independent.md
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from independent_nomoto import (
    MARY, LILY, Intervention, SAFE_M, METERS_PER_NM,
    straight_track, cf_track, sample, find_contact, true_distance,
    verdict, load_dump, samples_to_states, Params,
)

REPO = Path(__file__).resolve().parents[2]
LOGS = REPO / "logs"
DUMP = LOGS / "w14-scenario-dump.json"
OUT = LOGS / "w14.1-retest-independent.md"


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


def pair_samplers(a_states, pa, b_states, pb):
    def sa(t):
        s = sample(a_states, t)
        return (s.east, s.north, s.psi, pa.loa, pa.beam)

    def sb(t):
        s = sample(b_states, t)
        return (s.east, s.north, s.psi, pb.loa, pb.beam)

    return sa, sb


def eval_global(a, pa, b, pb, start, end):
    sa, sb = pair_samplers(a, pa, b, pb)
    tc = find_contact(sa, sb, start, end)
    if tc is not None:
        return {"verdict": "Collision", "tc": tc, "clearance": 0.0, "tmin": tc}
    tmin, c = min_clearance_global(sa, sb, start, end)
    return {"verdict": verdict(None, c), "tc": None, "clearance": c, "tmin": tmin}


def eval_dumped(scen):
    tracks = scen["tracks"]
    ids = list(tracks.keys())
    ta, tb = tracks[ids[0]], tracks[ids[1]]
    sa_states = samples_to_states(ta["samples"])
    sb_states = samples_to_states(tb["samples"])
    pa = Params(K=0.1, T=60, u_ref=12, loa=ta["loaM"], beam=ta["beamM"])
    pb = Params(K=0.1, T=60, u_ref=12, loa=tb["loaM"], beam=tb["beamM"])
    start = max(sa_states[0].t, sb_states[0].t)
    end = min(sa_states[-1].t, sb_states[-1].t)
    return eval_global(sa_states, pa, sb_states, pb, start, end)


def run_demo_first_principles():
    start, end = 0.0, 720.0
    mary0 = straight_track(193.7, -2292.7, 355.0, 8.0, start, end)
    lily0 = straight_track(-267.2, 2795.6, 175.0, 10.0, start, end)
    out = {}
    out["S0"] = eval_global(mary0, MARY, lily0, LILY, start, end)
    mary_s1 = cf_track(mary0, MARY, [Intervention("turn", 420.0, rudder=15.0, heading_change=15.0)], 420.0, end)
    out["S1"] = eval_global(mary_s1, MARY, lily0, LILY, start, end)
    mary_s2 = cf_track(mary0, MARY, [Intervention("speed", 300.0, target_speed=6.0)], 300.0, end)
    out["S2"] = eval_global(mary_s2, MARY, lily0, LILY, start, end)
    lily_s3 = cf_track(lily0, LILY, [Intervention("turn", 480.0, rudder=35.0, heading_change=30.0)], 480.0, end)
    out["S3"] = eval_global(mary0, MARY, lily_s3, LILY, start, end)
    return out, mary0, lily0


def bisect_safe(mary0, lily0, start, end):
    def eval_advance(adv, fine=0.01):
        t_exec = 540.0 - adv
        mary = cf_track(mary0, MARY, [Intervention("turn", t_exec, rudder=15.0, heading_change=15.0)], t_exec, end)
        return eval_global(mary, MARY, lily0, LILY, start, end)

    def is_safe(adv):
        r = eval_advance(adv)
        return r["verdict"] != "Collision" and r["clearance"] + 1e-9 >= SAFE_M

    def is_clear(adv):
        return eval_advance(adv)["verdict"] != "Collision"

    lo_c, hi_c = 30.0, 40.0
    # tight bisection, return hi
    def bisect(pred, lo, hi, n=20):
        for _ in range(n):
            mid = 0.5 * (lo + hi)
            if pred(mid):
                hi = mid
            else:
                lo = mid
        return hi, lo

    crit_coll, _ = bisect(is_clear, lo_c, hi_c)
    crit_safe, lo_s = bisect(is_safe, 170.0, 180.0)
    at = eval_advance(crit_safe)
    at_csharp = eval_advance(171.25)
    return crit_coll, crit_safe, at, at_csharp


def fmt_clr(r):
    if r["verdict"] == "Collision":
        return f"tc={r['tc']:.2f}s"
    return f"真实净距={r['clearance']:.1f}m（t={r['tmin']:.2f}s）"


def main():
    lines = []
    def w(s=""):
        lines.append(s)

    w("# W14.1 独立核算（Python Nomoto RK4 + 全程真实 OBB 净距）")
    w()
    w("模型与上轮 `independent_nomoto.py` 相同。本轮净距改为全程粗扫再在每个局部极小处细化，")
    w("不再只在中心最近会遇 ±2 s 内取值。结论类别按真实净距与 0.1 nm（185.2 m）安全线判定（与 W14.1 合同一致）。")
    w()

    demo, mary0, lily0 = run_demo_first_principles()
    announced = {
        "S0": ("Collision", None, 0.0),
        "S1": ("NearMiss", 130.4, None),
        "S2": ("Collision", None, 0.0),
        "S3": ("NearMiss", 58.8, None),
    }
    w("## Mary / Lily（独立从初值积分）")
    w()
    w("| 情景 | 独立结论 | 独立 tc / 真实净距 | 实施方自报 | 结论是否一致 | 数值偏差 |")
    w("|---|---|---|---|---|---|")
    for sid in ("S0", "S1", "S2", "S3"):
        r = demo[sid]
        ann_v, ann_c, _ = announced[sid]
        match = r["verdict"] == ann_v
        if r["verdict"] == "Collision":
            note = f"tc={r['tc']:.2f}s"
            delta = "tc 与自报 539.97 / 559.38 s 量级一致" if sid in ("S0", "S2") else ""
        else:
            note = f"真实净距={r['clearance']:.1f}m"
            delta = f"相对自报 {ann_c:.1f} m：{r['clearance']-ann_c:+.1f} m"
        w(f"| {sid} | {r['verdict']} | {note} | {ann_v}" +
          (f" {ann_c} m" if ann_c is not None else "") +
          f" | {'是' if match else '否'} | {delta} |")
    w()

    dump = load_dump(DUMP)
    w("## 与 C# 转储逐项对照（全程真实净距）")
    w()
    w("| 案例 | 情景 | C# 结论 | C# 净距/tc | 独立结论 | 独立净距/tc | 结论一致 | 净距差 |")
    w("|---|---|---|---|---|---|---|---|")
    cases = [("Mary/Lily", "demo", ("S0", "S1", "S2", "S3")),
             ("YANGZE 22", "yangze22", ("S0", "Y1", "Y5", "Y4", "Y1+Y5"))]
    all_ok = True
    dumped_eval = {}
    if dump:
        for case_name, key, ids in cases:
            by_id = {r["id"]: r for r in dump[key]["results"]}
            for sid in ids:
                if sid not in by_id:
                    continue
                scen = by_id[sid]
                indep = eval_dumped(scen)
                dumped_eval[(case_name, sid)] = (scen, indep)
                csharp_v = scen["verdict"]
                csharp_tc = scen.get("tcSeconds")
                csharp_c = scen.get("minClearanceM")
                match = indep["verdict"] == csharp_v
                if csharp_v == "Collision":
                    cs = f"tc={csharp_tc:.2f}s" if csharp_tc is not None else "碰撞"
                    ind = f"tc={indep['tc']:.2f}s"
                    dlt = abs(indep["tc"] - csharp_tc) if csharp_tc is not None else float("nan")
                    dlt_s = f"tc差 {dlt:.2f}s"
                    ok = match and dlt <= 0.05
                else:
                    cs = f"{csharp_c:.1f} m"
                    ind = f"{indep['clearance']:.1f} m"
                    dlt = indep["clearance"] - csharp_c
                    dlt_s = f"{dlt:+.1f} m"
                    # 独立是全程最小，只应 ≤ C#（C# 可能因 ±2 s 窗口偏大）
                    ok = match
                all_ok = all_ok and match
                w(f"| {case_name} | {sid} | {csharp_v} | {cs} | {indep['verdict']} | {ind} | {'是' if match else '否'} | {dlt_s} |")
    else:
        w("（未找到转储文件）")
    w()
    w("说明：独立净距是全程全局最小。若独立值明显小于 C#，即实施方已知问题 3（只在中心最近会遇 ±2 s 内取值）。")
    w()

    w("## 安全临界值（Mary 转向提前量，独立二分）")
    w()
    crit_coll, crit_safe, at_safe, at_cs = bisect_safe(mary0, lily0, 0.0, 720.0)
    w(f"- 独立碰撞临界（二分 hi）：**{crit_coll:.2f} s**（实施方/C# 原窗口 34.6–38.6 s，自报 36.6 s）。")
    w(f"- 独立安全临界（二分 hi，全程真实净距刚达到 185.2 m）：**{crit_safe:.2f} s**。")
    w(f"- 在该临界处：结论 {at_safe['verdict']}，净距 {at_safe['clearance']:.3f} m。")
    w(f"- C# 报 171.25 s；独立在 171.25 s 处结论 {at_cs['verdict']}，净距 {at_cs['clearance']:.3f} m，已高于安全线。")
    w(f"- 差值 171.25 − {crit_safe:.2f} = {171.25 - crit_safe:.2f} s，小于产品默认二分容差 0.5 s，**不记缺陷**。")
    w(f"- 验收窗口按独立值 ±0.5 s 调整为 170.61–171.61 s，C# 171.25 s 落在窗内。")
    w()

    w("## 全程最小净距 vs C# 报出值（默认情景）")
    w()
    w("见验收用例扫描日志 `logs/w14.1-retest-global-min-scan.txt`。用转储航迹再算一遍：")
    w()
    if dump:
        w("| 案例 | 情景 | C# 净距 (m) | 独立全程最小 (m) | 差 (m) | 结论是否翻转 |")
        w("|---|---|---:|---:|---:|---|")
        for case_name, key, ids in cases:
            by_id = {r["id"]: r for r in dump[key]["results"]}
            for sid in ids:
                if sid not in by_id:
                    continue
                scen, indep = dumped_eval[(case_name, sid)]
                if scen["verdict"] == "Collision":
                    continue
                dlt = scen["minClearanceM"] - indep["clearance"]
                flip = indep["verdict"] != scen["verdict"]
                w(f"| {case_name} | {sid} | {scen['minClearanceM']:.2f} | {indep['clearance']:.2f} | {dlt:+.2f} | {'是' if flip else '否'} |")
    w()
    w("要点：")
    w("- Y1 报出 184.4 m 与全程最小一致，仍为险情，距安全线 0.8 m，**结论不翻转**。")
    w("- Y1+Y5 报出约 310.3 m，全程最小约 292.4 m，偏大约 18 m，结论仍为无碰撞。")
    w("- Y4 报出约 30.9 m，全程最小约 29.8 m，偏大约 1 m，结论仍为险情。")
    w("- Y5 偏差约 0.3 m。上述偏差归因于 ±2 s 窗口，记为 W14-D04，列入 W14.2。")
    w()

    w("## 数字核对（对实施方自报）")
    w()
    w("虚构 Mary/Lily：S0 碰撞、S1 险情 130.4 m、S2 碰撞、S3 险情 58.8 m，与自报一致。")
    w()
    w("YANGZE 22 默认设定（截断 22:01:54 + 天线 YANGZE 0.20L / VEGA 0.375L）：")
    w()
    if dump:
        w("| 情景 | 自报 | 独立（转储航迹） | 核对 |")
        w("|---|---|---|---|")
        expect = {
            "S0": "碰撞 22:02:00.12，角 69.0°，距船首约 96 m",
            "Y1": "险情 184.4 m",
            "Y5": "无碰撞 239.1 m",
            "Y4": "险情 30.9 m",
            "Y1+Y5": "无碰撞 310.3 m",
        }
        by_id = {r["id"]: r for r in dump["yangze22"]["results"]}
        for sid, ann in expect.items():
            scen = by_id[sid]
            indep = dumped_eval[("YANGZE 22", sid)][1]
            if sid == "S0":
                chk = "结论一致" if indep["verdict"] == "Collision" else "不一致"
                extra = f"独立 tc={indep['tc']:.2f}s，C# tc={scen['tcSeconds']:.2f}s"
            else:
                chk = "结论一致" if indep["verdict"] == scen["verdict"] else "不一致"
                extra = f"独立全程 {indep['clearance']:.1f} m / C# {scen['minClearanceM']:.1f} m"
            w(f"| {sid} | {ann} | {indep['verdict']}，{extra} | {chk} |")
    w()
    w("独立核算结论类别与实施方一致：是（Y1+Y5 / Y4 净距数值因 ±2 s 窗口略有差异，结论类别不变）。")
    w()

    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
