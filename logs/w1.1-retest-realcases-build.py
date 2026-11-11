#!/usr/bin/env python3
"""Build 1-second ENU tracks for haili5 and yangze22 real-case reference runs.
Positions are dead-reckoned or interpolated from public report points (not raw AIS).
"""
from __future__ import annotations
import csv, json, math
from datetime import datetime
from pathlib import Path

ROOT = Path("/workspace/maritime-sim-design")
LOGS = ROOT / "logs"
NM = 1852.0
KN = 1852.0 / 3600.0

def parse_bj(s: str) -> datetime:
    s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s)

def sec_of(s: str) -> float:
    t = parse_bj(s)
    return t.hour * 3600 + t.minute * 60 + t.second + t.microsecond / 1e6

def enu(lat, lon, lat0, lon0):
    return ((lon - lon0) * 111320.0 * math.cos(math.radians(lat0)),
            (lat - lat0) * 110574.0)

def load_csv(path: Path):
    text = path.read_text(encoding="utf-8")
    lines = [l for l in text.splitlines() if l.strip() and not l.startswith("#")]
    return list(csv.DictReader(lines))

def num(row, *keys):
    for k in keys:
        v = (row.get(k) or "").strip()
        if v:
            try:
                return float(v)
            except ValueError:
                pass
    return None

def merge_by_time(rows, vid):
    """Merge duplicate timestamps, preferring rows with position and filling blanks."""
    by = {}
    for r in rows:
        if r["vesselId"] != vid:
            continue
        t = sec_of(r["timeBeijing"])
        slot = by.setdefault(t, {})
        for k, v in r.items():
            if v is None or str(v).strip() == "":
                continue
            # prefer existing pos; otherwise overwrite empty
            if k in slot and slot[k] not in (None, "") and k in ("latDeg", "lonDeg") and slot.get(k):
                continue
            if k not in slot or slot[k] in (None, ""):
                slot[k] = v
            elif k in ("latDeg", "lonDeg", "hdgDeg") and not slot.get("_had_pos") and num(r, "latDeg") is not None:
                slot[k] = v
        if num(r, "latDeg") is not None:
            slot["_had_pos"] = True
            if num(r, "latDeg"):
                slot["latDeg"] = r["latDeg"]
                slot["lonDeg"] = r["lonDeg"]
            if num(r, "hdgDeg") is not None:
                slot["hdgDeg"] = r["hdgDeg"]
            if num(r, "cogDeg") is not None and "cogDeg" not in slot:
                slot["cogDeg"] = r["cogDeg"]
    return [(t, by[t]) for t in sorted(by)]

def lerp_angle(a, b, f):
    d = ((b - a + 540) % 360) - 180
    return (a + d * f) % 360

def series_of(points, key_candidates, t0, t1):
    samples = []
    for t, r in points:
        v = num(r, *key_candidates)
        if v is not None:
            samples.append((t, v))
    if not samples:
        return None
    def at(t):
        if t <= samples[0][0]:
            return samples[0][1]
        for a, b in zip(samples, samples[1:]):
            if a[0] <= t <= b[0]:
                if key_candidates[0].endswith("Deg") or "hdg" in key_candidates[0].lower() or "cog" in key_candidates[0].lower():
                    f = 0 if b[0] == a[0] else (t - a[0]) / (b[0] - a[0])
                    return lerp_angle(a[1], b[1], f)
                f = 0 if b[0] == a[0] else (t - a[0]) / (b[0] - a[0])
                return a[1] + (b[1] - a[1]) * f
        return samples[-1][1]
    return at

def write_csv(path, rows, header):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(header + "\n")
        for r in rows:
            f.write(",".join(r) + "\n")

def build_haili5():
    # Proven DR from previous retest, anchored at 19:53:08 VTS AIS.
    d = json.loads((ROOT / "reports/haili5/case.json").read_text(encoding="utf-8"))
    def ts(p):
        h, m, s = p["time"]["beijing"][11:19].split(":")
        return int(h) * 3600 + int(m) * 60 + int(s)
    T0 = ts({"time": {"beijing": "2025-10-25T19:42:00"}})
    T1 = ts({"time": {"beijing": "2025-10-25T19:54:32"}})
    lat0, lon0 = 22.2785, 113.806833
    pts = {"haili5": [], "wanhai_a17": []}
    for p in d["trackPoints"]:
        if p["id"] == "t-a17-195115-fig24":
            continue
        pts[p["vesselId"]].append((
            ts(p) - T0, p["courseDeg"], p["speedKn"],
            enu(p["location"]["latDeg"], p["location"]["lonDeg"], lat0, lon0) if p["location"] else None,
        ))
    for k in pts:
        pts[k].sort()

    def cs_at(lst, t):
        prev = lst[0]
        for q in lst:
            if q[0] >= t:
                if q[0] == prev[0]:
                    return q[1], q[2]
                f = (t - prev[0]) / (q[0] - prev[0])
                dc = ((q[1] - prev[1] + 180) % 360) - 180
                return (prev[1] + dc * f) % 360, prev[2] + (q[2] - prev[2]) * f
            prev = q
        return lst[-1][1], lst[-1][2]

    dur = T1 - T0
    out_rows = []
    for v, anchor_abs in (("haili5", ts({"time": {"beijing": "2025-10-25T19:53:08"}})),
                          ("wanhai_a17", ts({"time": {"beijing": "2025-10-25T19:53:08"}}))):
        lst = [q for q in pts[v] if q[0] >= -1800]
        anchor_t = anchor_abs - T0
        anc = [q for q in lst if q[3] is not None and q[0] == anchor_t][0][3]
        pos = {anchor_t: anc}
        e, n = anc
        for t in range(anchor_t, dur):
            c, s = cs_at(lst, t + 0.5)
            e += s * KN * math.sin(math.radians(c))
            n += s * KN * math.cos(math.radians(c))
            pos[t + 1] = (e, n)
        e, n = anc
        for t in range(anchor_t, 0, -1):
            c, s = cs_at(lst, t - 0.5)
            e -= s * KN * math.sin(math.radians(c))
            n -= s * KN * math.cos(math.radians(c))
            pos[t - 1] = (e, n)
        for t in range(0, dur + 1):
            c, s = cs_at(lst, t)
            out_rows.append((v, t, pos[t][0], pos[t][1], c, s * KN, c, 0))  # hdg=cog (report "航向")
    path = LOGS / "w1.1-retest-haili5-tracks.csv"
    write_csv(path, [
        [v, str(t), f"{e:.3f}", f"{n:.3f}", f"{cog:.3f}", f"{sog:.4f}", f"{hdg:.3f}", str(int(fromcog))]
        for v, t, e, n, cog, sog, hdg, fromcog in out_rows
    ], "vessel,t,e,n,cog,sogMps,hdg,headingFromCog")
    print("wrote", path, "rows", len(out_rows), "dur", dur)
    return path

def build_yangze22():
    rows = load_csv(ROOT / "reports/yangze22/tracks_from_report.csv")
    T0 = sec_of("2024-12-30T21:58:30+08:00")
    T1 = sec_of("2024-12-30T22:01:54+08:00")
    # origin near first YANGZE VDR fix
    lat0, lon0 = 31.284085, 121.818538
    out_rows = []
    for vid in ("yangze22", "vega_dream"):
        pts = merge_by_time(rows, vid)
        # position samples
        fixes = []
        for t, r in pts:
            la, lo = num(r, "latDeg"), num(r, "lonDeg")
            if la is not None and lo is not None:
                fixes.append((t, enu(la, lo, lat0, lon0)))
        cog_at = series_of(pts, ["cogDeg"], T0, T1)
        sog_at = series_of(pts, ["sogKn"], T0, T1)
        hdg_at = series_of(pts, ["hdgDeg"], T0, T1)
        if not fixes:
            raise SystemExit(f"no positions for {vid}")
        # If first fix is after T0, DR backward; after last, DR forward; between fixes, lerp position.
        pos = {}
        # fill between fixes by linear interpolation (GPS/AIS points are dense enough for YANGZE)
        for i in range(len(fixes) - 1):
            t0, (e0, n0) = fixes[i]
            t1, (e1, n1) = fixes[i + 1]
            steps = max(1, int(round(t1 - t0)))
            for k in range(steps + 1):
                t = t0 + k
                if t < t0 or t > t1:
                    continue
                f = 0 if t1 == t0 else (t - t0) / (t1 - t0)
                pos[int(round(t))] = (e0 + (e1 - e0) * f, n0 + (n1 - n0) * f)
        # also exact fix times
        for t, xy in fixes:
            pos[int(round(t))] = xy
        first_t, first_xy = fixes[0]
        last_t, last_xy = fixes[-1]
        def cs(t):
            c = cog_at(t) if cog_at else (hdg_at(t) if hdg_at else 0)
            s = sog_at(t) if sog_at else 0
            return c, s
        # backward DR
        e, n = first_xy
        for t in range(int(round(first_t)), int(math.floor(T0)) - 1, -1):
            pos.setdefault(t, (e, n))
            if t <= T0:
                break
            c, s = cs(t - 0.5)
            e -= s * KN * math.sin(math.radians(c))
            n -= s * KN * math.cos(math.radians(c))
            pos[t - 1] = (e, n)
        # forward DR after last
        e, n = last_xy
        for t in range(int(round(last_t)), int(math.ceil(T1))):
            pos.setdefault(t, (e, n))
            c, s = cs(t + 0.5)
            e += s * KN * math.sin(math.radians(c))
            n += s * KN * math.cos(math.radians(c))
            pos[t + 1] = (e, n)
        for t in range(int(T0), int(T1) + 1):
            if t not in pos:
                # should not happen often; skip or nearest
                continue
            c = cog_at(t) if cog_at else 0
            s = (sog_at(t) if sog_at else 0) * KN
            if hdg_at and hdg_at(t) is not None:
                hdg = hdg_at(t)
                fromcog = 0
            else:
                hdg = c
                fromcog = 1
            out_rows.append((vid, t - T0, pos[t][0], pos[t][1], c, s, hdg, fromcog))
    path = LOGS / "w1.1-retest-yangze22-tracks.csv"
    write_csv(path, [
        [v, f"{t:.0f}", f"{e:.3f}", f"{n:.3f}", f"{cog:.3f}", f"{sog:.4f}", f"{hdg:.3f}", str(int(fromcog))]
        for v, t, e, n, cog, sog, hdg, fromcog in out_rows
    ], "vessel,t,e,n,cog,sogMps,hdg,headingFromCog")
    print("wrote", path, "rows", len(out_rows))
    return path

if __name__ == "__main__":
    build_haili5()
    build_yangze22()
