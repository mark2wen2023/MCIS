# -*- coding: utf-8 -*-
"""REAL_CASES.md 的推算值 + haili5/tracks_from_report.csv。只读 case.json，不改原产物。"""
import csv, json, math, sys
from pathlib import Path
sys.dont_write_bytecode = True
R = Path(__file__).parent

def enu(lat0, lon0, lat, lon):
    k = math.cos(math.radians(lat0))
    return ((lon - lon0) * 60 * k, (lat - lat0) * 60)  # nm east, north

def cpa(p1, c1, s1, p2, c2, s2):
    lat0, lon0 = p1
    x1, y1 = 0.0, 0.0
    x2, y2 = enu(lat0, lon0, *p2)
    v1 = (s1 * math.sin(math.radians(c1)), s1 * math.cos(math.radians(c1)))
    v2 = (s2 * math.sin(math.radians(c2)), s2 * math.cos(math.radians(c2)))
    rx, ry = x2 - x1, y2 - y1
    vx, vy = v2[0] - v1[0], v2[1] - v1[1]
    vv = vx * vx + vy * vy
    t = -(rx * vx + ry * vy) / vv if vv else 0.0
    dx, dy = rx + vx * t, ry + vy * t
    rng = math.hypot(rx, ry)
    brg12 = (math.degrees(math.atan2(rx, ry)) + 360) % 360
    return {"rangeNm": round(rng, 3), "bearing1to2": round(brg12, 1), "dcpaNm": round(math.hypot(dx, dy), 3),
            "tcpaMin": round(t * 60, 2), "relSpeedKn": round(math.sqrt(vv), 2)}

def relb(brg, hdg):
    r = (brg - hdg + 540) % 360 - 180
    return round(r, 1)

out = {}
yz = json.load(open(R / "yangze22/case.json"))
pts = {p["id"]: p for p in yz["trackPoints"]}
def P(i):
    l = pts[i]["location"]; return (l["latDeg"], l["lonDeg"])
for tag, yi, vi in [("22:00:38 图28 AIS", "t-y-ais-fig28", "t-v-ais-fig28"), ("22:00:42 图29 AIS", "t-y-ais-fig29", "t-v-ais-fig29"),
                    ("22:01:54 图6 AIS（碰撞）", "t-y-ais-fig6", "t-v-ais-fig6")]:
    y, v = pts[yi], pts[vi]
    r = cpa(P(yi), y["courseDeg"], y["speedKn"], P(vi), v["courseDeg"], v["speedKn"])
    r["relBearingOfVegaFromYangze"] = relb(r["bearing1to2"], y["hdgDeg"])
    r["relBearingOfYangzeFromVega"] = relb((r["bearing1to2"] + 180) % 360, v["hdgDeg"])
    out[f"YZ {tag}"] = r
# YANGZE VDR GPS track: distance travelled / lateral deviation from 114° line starting 21:58:30
vdr = sorted([p for p in yz["trackPoints"] if p["provenance"] == "ReportFigure-VDR" and p["location"]], key=lambda p: p["time"]["utc"])
lat0, lon0 = vdr[0]["location"]["latDeg"], vdr[0]["location"]["lonDeg"]
rows = []
prev = None
for p in vdr:
    e, n = enu(lat0, lon0, p["location"]["latDeg"], p["location"]["lonDeg"])
    along = e * math.sin(math.radians(114)) + n * math.cos(math.radians(114))
    cross = e * math.cos(math.radians(114)) - n * math.sin(math.radians(114))  # + = right of 114° track, - = left
    sp = None
    if prev:
        from datetime import datetime
        dt = (datetime.fromisoformat(p["time"]["utc"].replace("Z", "+00:00")) - datetime.fromisoformat(prev[0].replace("Z", "+00:00"))).total_seconds()
        if dt > 0:
            sp = round(math.hypot(e - prev[1], n - prev[2]) / (dt / 3600), 1)
    rows.append({"utc": p["time"]["utc"], "fig": p["source"]["figure"], "alongNm": round(along, 3), "rightOfTrackM_negIsLeft": round(cross * 1852), "sogFromFixesKn": sp})
    prev = (p["time"]["utc"], e, n)
out["YZ VDR GPS 相对 21:58:30 点、114° 计划航迹"] = rows

h5 = json.load(open(R / "haili5/case.json"))
hp = {p["id"]: p for p in h5["trackPoints"]}
def HP(i):
    l = hp[i]["location"]; return (l["latDeg"], l["lonDeg"])
for tag, a, b in [("19:53:08 图18 AIS", "t-h5-195308-vts", "t-a17-195308-vts"), ("19:54:32 碰撞 AIS", "t-h5-195432", "t-a17-195432")]:
    r = cpa(HP(a), hp[a]["courseDeg"], hp[a]["speedKn"], HP(b), hp[b]["courseDeg"], hp[b]["speedKn"])
    r["relBearingOfA17FromH5_byCourse"] = relb(r["bearing1to2"], hp[a]["courseDeg"])
    r["relBearingOfH5FromA17_byCourse"] = relb((r["bearing1to2"] + 180) % 360, hp[b]["courseDeg"])
    out[f"H5 {tag}"] = r
json.dump(out, open("/tmp/real_cases_derived.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))

# ---- haili5 tracks CSV (from existing case.json trackPoints; no new extraction) ----
cols = ["vesselId", "timeBeijing", "timeUtc", "approximate", "latDeg", "lonDeg", "cogDeg", "sogKn", "provenance",
        "page", "pdfPage", "figure", "quote", "note"]
with open(R / "haili5/tracks_from_report.csv", "w", encoding="utf-8", newline="") as f:
    f.write("# 广州“10·25”海力5 / WAN HAI A17：航迹样本，取自调查报告正文文字和插图（图18 VTS AIS 框、图24 事故经过图），不是 AIS 原始数据。\n")
    f.write("# 由 haili5/case.json 的 trackPoints 原样导出（_derive_real_cases.py），page 为正文页，pdfPage = page + 5。\n")
    f.write("# 同一时刻可能有多行（正文与图24并存），不要自行取舍；位置为空表示报告只给了航向航速。\n")
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for p in sorted(h5["trackPoints"], key=lambda p: (p["vesselId"], p["time"]["utc"])):
        l = p.get("location") or {}; s = p["source"]
        w.writerow({"vesselId": p["vesselId"], "timeBeijing": p["time"]["beijing"], "timeUtc": p["time"]["utc"],
                    "approximate": p["time"].get("approximate"), "latDeg": l.get("latDeg"), "lonDeg": l.get("lonDeg"),
                    "cogDeg": p.get("courseDeg"), "sogKn": p.get("speedKn"), "provenance": p["provenance"],
                    "page": s.get("page"), "pdfPage": s.get("pdfPage"), "figure": s.get("figure"), "quote": s.get("quote"),
                    "note": p.get("note")})
print("wrote haili5/tracks_from_report.csv", len(h5["trackPoints"]))
