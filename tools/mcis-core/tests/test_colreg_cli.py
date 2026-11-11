#!/usr/bin/env python3
"""CLI end-to-end tests for mcis-core colreg (demo Lily/Mary + haili5 fragment)."""
from __future__ import annotations

import json
import math
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/workspace/maritime-sim-design")
CORE = ROOT / "tools" / "mcis-core" / "mcis-core.sh"
LOGS = ROOT / "logs"
PY = ROOT / "service" / ".venv" / "bin" / "python"
VALIDATOR = ROOT / "tests_acceptance" / "W1" / "validate_colreg_schema.py"
KN = 1852.0 / 3600.0

# ---- demo track (same kinematics as service seed, fictional) ----
EPOCH = datetime(2026, 5, 18, 6, 15, tzinfo=timezone.utc)
P_LAT, P_LON = 21.796667, 113.700000
COLLISION_T = 540.0


def profile(vessel: str, t: float) -> tuple[float, float]:
    if vessel == "vessel_mary":
        sp = 13.5 if t < 240 else max(9.5, 13.5 - (t - 240) * 0.27)
        if t >= 500:
            sp = max(8.6, 9.5 - (t - 500) * 0.03)
        crs = 8.0 if t < 435 else 8.0 - min(52.0, (t - 435) * 0.5)
        return crs % 360, sp
    sp = 10.6 if t < 465 else max(6.0, 10.6 - (t - 465) * 0.06)
    crs = 188.0 if t < 465 else 188.0 + min(52.0, (t - 465) * 0.9)
    return crs % 360, sp


def integrate(vessel: str) -> list[tuple[float, float, float, float, float]]:
    e = n = 0.0
    out = []
    for i in range(int(COLLISION_T) + 1):
        t = float(i)
        crs, sp = profile(vessel, t)
        out.append((t, e, n, crs, sp))
        r = math.radians(crs)
        e += sp / 3600.0 * math.sin(r)
        n += sp / 3600.0 * math.cos(r)
    return out


def iso(t: float) -> str:
    return (EPOCH + timedelta(seconds=t)).strftime("%Y-%m-%dT%H:%M:%SZ")


def demo_tracks() -> dict:
    pts: dict[str, list] = {"vessel_lily": [], "vessel_mary": []}
    m_per_deg_lat = 111320.0
    m_per_deg_lon = 111320.0 * math.cos(math.radians(P_LAT))
    for vid in ("vessel_lily", "vessel_mary"):
        seq = integrate(vid)
        e_c, n_c = seq[-1][1], seq[-1][2]
        lat_c, lon_c = P_LAT, P_LON
        if vid == "vessel_lily":
            lat_c += 25.0 / m_per_deg_lat
            lon_c -= 30.0 / m_per_deg_lon
        samples = [s for s in seq if int(s[0]) % 10 == 0]
        last = seq[-1]
        e, n = last[1], last[2]
        for k in range(1, 19):
            t = COLLISION_T + k * 10
            if vid == "vessel_lily":
                crs, sp = 205.0, max(0.3, 1.5 - k * 0.07)
            else:
                crs, sp = 330.0, max(0.0, 6.0 - k * 0.6)
            r = math.radians(crs)
            e += sp / 360.0 * math.sin(r)
            n += sp / 360.0 * math.cos(r)
            samples.append((t, e, n, crs, sp))
        for (t, e_nm, n_nm, crs, sp) in samples:
            de, dn = (e_nm - e_c) * 1852.0, (n_nm - n_c) * 1852.0
            pts[vid].append({
                "vesselId": vid, "timeSec": t, "utc": iso(t),
                "latDeg": round(lat_c + dn / m_per_deg_lat, 7),
                "lonDeg": round(lon_c + de / m_per_deg_lon, 7),
                "sogKn": round(sp, 2), "cogDeg": round(crs, 1),
                "hdgDeg": round((crs + (1.5 if vid == "vessel_mary" else -1.0)) % 360, 1),
                "provenance": "Measured",
            })
    return pts


def haili5_fragment() -> dict:
    """19:50:00–19:54:32 fragment (t=480–752 from 19:42:00), NUC from 19:51:15."""
    csv = LOGS / "w1.1-retest-haili5-tracks.csv"
    # origin used when building the CSV
    lat0, lon0 = 22.2785, 113.806833
    tracks = {"haili5": [], "wanhai_a17": []}
    for line in csv.read_text(encoding="utf-8").splitlines()[1:]:
        if not line.strip():
            continue
        v, t, e, n, cog, sog, hdg, fromcog = line.split(",")
        t = float(t)
        if t < 480:
            continue
        if int(t) % 10 != 0 and t != 752:
            continue
        e, n = float(e), float(n)
        lat = lat0 + n / 110574.0
        lon = lon0 + e / (111320.0 * math.cos(math.radians(lat0)))
        rec = {
            "vesselId": v, "timeSec": t,
            "latDeg": round(lat, 7), "lonDeg": round(lon, 7),
            "sogKn": round(float(sog) / KN, 3), "cogDeg": round(float(cog), 2),
            "provenance": "Interpolated",
        }
        if fromcog != "1":
            rec["hdgDeg"] = round(float(hdg), 2)
        tracks[v].append(rec)
    return tracks


def run_core(command: str, payload: dict) -> tuple[int, dict]:
    proc = subprocess.run(
        [str(CORE), command],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    text = proc.stdout.decode("utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise SystemExit(f"non-json stdout (exit {proc.returncode}): {text[:500]}\nstderr: {proc.stderr.decode()[-400:]}")
    return proc.returncode, data


def validate_schema(doc: dict, path: Path) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    proc = subprocess.run([str(PY), str(VALIDATOR), str(path)], capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"schema fail {path}:\n{proc.stdout}\n{proc.stderr}")


def main() -> int:
    # unknown still 2; version lists colreg
    code, ver = run_core("version", {})
    assert code == 0 and ver["ok"]
    assert "colreg" in ver["result"]["commands"], ver

    # demo Lily / Mary
    demo_req = {
        "caseId": "CASE-2026-DEMO-LILY-MARY",
        "caseEpochUtc": "2026-05-18T06:15:00Z",
        "origin": {"latDeg": P_LAT, "lonDeg": P_LON},
        "ownVesselId": "vessel_mary",
        "targetVesselId": "vessel_lily",
        "visibilityNm": 8,
        "vesselsInSight": True,
        "inNarrowChannel": True,
        "tracks": demo_tracks(),
    }
    (LOGS / "w1.1-retest-cli-demo-request.json").write_text(json.dumps(demo_req, ensure_ascii=False), encoding="utf-8")
    code, env = run_core("colreg", demo_req)
    assert code == 0 and env["ok"] and env["command"] == "colreg", env
    result = env["result"]
    validate_schema(result, LOGS / "w1.1-retest-cli-demo-result.json")
    assert result["caseId"] == "CASE-2026-DEMO-LILY-MARY"
    assert result["disclaimer"]
    assert result["bands"] and result["checks"]
    sits = {b["situation"] for b in result["bands"]}
    assert "HeadOn" in sits or "Crossing" in sits, sits
    verdicts = {c["verdict"] for c in result["checks"]}
    assert "Satisfied" not in verdicts and "NotSatisfied" not in verdicts
    print("DEMO OK  bands", len(result["bands"]), "checks", len(result["checks"]), "situations", sorted(sits))

    # haili5 fragment with NUC
    h_req = {
        "caseId": "HAILI5-1025-FRAG",
        "ownVesselId": "haili5",
        "targetVesselId": "wanhai_a17",
        "visibilityNm": 8,
        "vesselsInSight": True,
        "tracks": haili5_fragment(),
        "vesselStatus": [
            {"vesselId": "haili5", "timeSec": 0, "status": "PowerDriven"},
            {"vesselId": "haili5", "timeSec": 555, "status": "NotUnderCommand"},
            {"vesselId": "wanhai_a17", "timeSec": 0, "status": "PowerDriven"},
        ],
    }
    (LOGS / "w1.1-retest-cli-haili5-request.json").write_text(json.dumps(h_req, ensure_ascii=False), encoding="utf-8")
    code, env = run_core("colreg", h_req)
    assert code == 0 and env["ok"], env
    result = env["result"]
    validate_schema(result, LOGS / "w1.1-retest-cli-haili5-result.json")
    after = [b for b in result["bands"] if b["startTimeSec"] >= 555 - 1e-6 and b["situation"] not in ("NoRisk",)]
    assert after, result["bands"]
    assert any(b.get("giveWayVesselId") == "wanhai_a17" for b in after), after
    r14_h5 = [c for c in result["checks"] if c["vesselId"] == "haili5" and c["rule"].startswith("R14")
              and (c.get("atTimeSec") or 0) >= 555 - 1e-6]
    assert all(c["verdict"] != "NotComplied" for c in r14_h5), r14_h5
    print("HAILI5 FRAGMENT OK  bands", len(result["bands"]), "post-NUC give-way",
          [b.get("giveWayVesselId") for b in after])

    # bad request still exit 4
    code, env = run_core("colreg", {"caseId": "ab"})
    assert code == 4 and env["ok"] is False and env["error"]["code"] == "BAD_REQUEST"
    print("BAD_REQUEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
