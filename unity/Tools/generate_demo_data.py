#!/usr/bin/env python3
"""生成示例数据（虚构）：Lily / Mary 窄航道会遇碰撞，改编自论文 5.4 节。

输出（相对本脚本 ../Assets/StreamingAssets/Mcis/Demo/）：
  lily_mary_demo.csv   列 mmsi,timestamp_utc,lat,lon,sog_kn,cog_deg,hdg_deg,vessel_name
  lily_mary_demo.nmea  !AIVDM 类型 1（位置）+ 类型 5（静态，两句）
仅依赖 Python 标准库。关键点取自 prototype/index.html 的 DEFAULT_*_WAYPOINTS。
"""
import math
import os
from datetime import datetime, timedelta, timezone

ORIGIN_LAT = 21.78
ORIGIN_LON = 113.70
EPOCH = datetime(2026, 5, 18, 10, 0, 0, tzinfo=timezone.utc)
STEP_S = 10
DURATION_S = 900
COS_LAT = math.cos(math.radians(ORIGIN_LAT))

# (t, x_east_nm, y_north_nm, hdg_deg)
LILY = [(0, -1.38, 0.56, 104), (150, -0.96, 0.43, 121), (300, -0.58, 0.19, 125),
        (450, -0.21, -0.04, 139), (540, 0.00, -0.18, 154), (690, 0.08, -0.27, 167),
        (900, 0.13, -0.33, 172)]
MARY = [(0, 1.66, -0.96, 304), (150, 1.18, -0.64, 302), (300, 0.70, -0.35, 299),
        (450, 0.28, -0.15, 274), (540, 0.01, -0.175, 258), (690, -0.12, -0.20, 251),
        (900, -0.20, -0.22, 248)]

SHIPS = [
    dict(mmsi=999000001, name="LILY", wps=LILY, callsign="LILY1", shiptype=70,
         bow=140, stern=40, port=15, stbd=15, draught=9.5, dest="OFFSHORE"),
    dict(mmsi=999000002, name="MARY", wps=MARY, callsign="MARY2", shiptype=71,
         bow=200, stern=60, port=20, stbd=20, draught=12.0, dest="ISLAND PORT"),
]


def hermite(wps, t):
    """三次 Hermite（切线=相邻关键点有限差分）；返回 (x, y, vx, vy) 单位 nm, nm/s。"""
    n = len(wps)
    i = 0
    while i < n - 2 and t > wps[i + 1][0]:
        i += 1
    t0, x0, y0, _ = wps[i]
    t1, x1, y1, _ = wps[i + 1]

    def tangent(k):
        a, b = max(k - 1, 0), min(k + 1, n - 1)
        dt = wps[b][0] - wps[a][0]
        return ((wps[b][1] - wps[a][1]) / dt, (wps[b][2] - wps[a][2]) / dt)

    m0, m1 = tangent(i), tangent(i + 1)
    h = t1 - t0
    s = (t - t0) / h
    h00, h10 = 2 * s**3 - 3 * s**2 + 1, s**3 - 2 * s**2 + s
    h01, h11 = -2 * s**3 + 3 * s**2, s**3 - s**2
    d00, d10 = 6 * s**2 - 6 * s, 3 * s**2 - 4 * s + 1
    d01, d11 = -6 * s**2 + 6 * s, 3 * s**2 - 2 * s
    x = h00 * x0 + h10 * h * m0[0] + h01 * x1 + h11 * h * m1[0]
    y = h00 * y0 + h10 * h * m0[1] + h01 * y1 + h11 * h * m1[1]
    vx = (d00 * x0 + d10 * h * m0[0] + d01 * x1 + d11 * h * m1[0]) / h
    vy = (d00 * y0 + d10 * h * m0[1] + d01 * y1 + d11 * h * m1[1]) / h
    return x, y, vx, vy


def hdg_at(wps, t):
    for i in range(len(wps) - 1):
        if wps[i][0] <= t <= wps[i + 1][0]:
            a, b = wps[i], wps[i + 1]
            f = (t - a[0]) / (b[0] - a[0])
            return (a[3] + (b[3] - a[3]) * f) % 360
    return wps[-1][3]


def state(ship, t):
    x, y, vx, vy = hermite(ship["wps"], t)
    sog = math.hypot(vx, vy) * 3600.0
    cog = math.degrees(math.atan2(vx, vy)) % 360
    lat = ORIGIN_LAT + y / 60.0
    lon = ORIGIN_LON + x / (60.0 * COS_LAT)
    return dict(lat=lat, lon=lon, sog=sog, cog=cog, hdg=hdg_at(ship["wps"], t))


def timeline():
    return list(range(0, DURATION_S + 1, STEP_S))


def write_csv(path):
    rows = []
    for t in timeline():
        ts = (EPOCH + timedelta(seconds=t)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for s in SHIPS:
            st = state(s, t)
            rows.append("%d,%s,%.6f,%.6f,%.1f,%.1f,%d,%s" % (
                s["mmsi"], ts, st["lat"], st["lon"], st["sog"], st["cog"],
                round(st["hdg"]) % 360, s["name"]))
    with open(path, "w", newline="\n") as f:
        f.write("mmsi,timestamp_utc,lat,lon,sog_kn,cog_deg,hdg_deg,vessel_name\n")
        f.write("\n".join(rows) + "\n")


# ---------------- NMEA / AIS 6-bit 编码 ----------------
def bits(value, n):
    if value < 0:
        value += 1 << n
    return format(value & ((1 << n) - 1), "0%db" % n)


def text6(s, chars):
    out = ""
    for c in s.upper()[:chars].ljust(chars, "@"):
        v = ord(c)
        out += bits(v - 64 if v >= 64 else v, 6)
    return out


def armor(bitstr):
    fill = (-len(bitstr)) % 6
    bitstr += "0" * fill
    chars = ""
    for i in range(0, len(bitstr), 6):
        v = int(bitstr[i:i + 6], 2)
        chars += chr(v + 48 if v < 40 else v + 56)
    return chars, fill


def checksum(body):
    x = 0
    for c in body:
        x ^= ord(c)
    return "%02X" % x


def sentence(total, num, seq, chan, payload, fill):
    body = "AIVDM,%d,%d,%s,%s,%s,%d" % (total, num, seq, chan, payload, fill)
    return "!%s*%s" % (body, checksum(body))


def type1(ship, st, second):
    b = bits(1, 6) + bits(0, 2) + bits(ship["mmsi"], 30) + bits(0, 4) + bits(-128, 8)
    b += bits(min(1022, int(round(st["sog"] * 10))), 10) + bits(1, 1)
    b += bits(int(round(st["lon"] * 600000)), 28) + bits(int(round(st["lat"] * 600000)), 27)
    b += bits(int(round(st["cog"] * 10)) % 3600, 12) + bits(int(round(st["hdg"])) % 360, 9)
    b += bits(second, 6) + bits(0, 2) + bits(0, 3) + bits(0, 1) + bits(0, 19)
    payload, fill = armor(b)
    return [sentence(1, 1, "", "A", payload, fill)]


def type5(ship, seq):
    b = bits(5, 6) + bits(0, 2) + bits(ship["mmsi"], 30) + bits(0, 2) + bits(0, 30)
    b += text6(ship["callsign"], 7) + text6(ship["name"], 20) + bits(ship["shiptype"], 8)
    b += bits(ship["bow"], 9) + bits(ship["stern"], 9) + bits(ship["port"], 6) + bits(ship["stbd"], 6)
    b += bits(1, 4) + bits(0, 20) + bits(int(round(ship["draught"] * 10)), 8)
    b += text6(ship["dest"], 20) + bits(0, 1) + bits(0, 1)
    payload, fill = armor(b)
    cut = 60
    return [sentence(2, 1, str(seq), "A", payload[:cut], 0),
            sentence(2, 2, str(seq), "A", payload[cut:], fill)]


def write_nmea(path):
    lines = ["# 示例数据（虚构），改编自论文 5.4 节；Lily MMSI 999000001 / Mary MMSI 999000002",
             "# epoch_utc: " + EPOCH.strftime("%Y-%m-%dT%H:%M:%SZ")]
    seq = 0
    for t in timeline():
        if t % 300 == 0:
            for s in SHIPS:
                lines += type5(s, seq % 10)
                seq += 1
        second = (EPOCH + timedelta(seconds=t)).second
        for s in SHIPS:
            lines += type1(s, state(s, t), second)
    with open(path, "w", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.normpath(os.path.join(here, "..", "Assets", "StreamingAssets", "Mcis", "Demo"))
    os.makedirs(out, exist_ok=True)
    write_csv(os.path.join(out, "lily_mary_demo.csv"))
    write_nmea(os.path.join(out, "lily_mary_demo.nmea"))
    print("written to", out)


if __name__ == "__main__":
    main()
