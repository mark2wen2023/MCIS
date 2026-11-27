"""Build isolated-assembly AnalysisCase documents from locked synthetic fixtures.

Pair metrics are geometric (haversine) at exact co-temporal recorded points only.
DCPA/TCPA in this assembly are declared synthetic placeholders at those same
points (non-zero), not an official mcis-core rerun. Interior-of-gap and
non-co-temporal instants are null: never filled, never zeroed.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
ORIGIN = datetime(2026, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
CST = timezone(timedelta(hours=8))
FAKE = "c" * 64

CROSS_A = "ddcca8bec01f1b42a6e3d10117ec4f701a75294c45807912d055647c50845575"
CROSS_B = "349a5fa53eeb3a23438019069a4962aa0e1140e9b305e0222fd9dfb71e09f581"
EXP_A = "a8f9109a33b8c80a6c41219473186e69c16fd59ee64ff325a5559c190028bb1c"
EXP_B = "07e043fc227770b6aaa6f1b15a6118e46b85a52e5638ac1b514e9269c6b159ca"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_vessel(path: Path, expected: str) -> dict:
    digest = sha256(path)
    if digest != expected:
        raise SystemExit(f"fixture digest mismatch {path}: {digest}")
    return json.loads(path.read_text(encoding="utf-8"))


def aligned_sec(utc: str) -> float:
    t = datetime.fromisoformat(utc.replace("Z", "+00:00"))
    return (t - ORIGIN).total_seconds()


def clock_of(sec: float) -> str:
    t = ORIGIN + timedelta(seconds=sec)
    local = t.astimezone(CST)
    if abs(sec - round(sec)) < 1e-9 and float(int(sec)) == sec:
        return local.strftime("%H:%M:%S")
    ms = int(round((sec - math.floor(sec)) * 1000))
    return local.strftime("%H:%M:%S") + f".{ms:03d}"


def samples(doc: dict) -> list[dict]:
    out = []
    for p in doc["points"]:
        t = aligned_sec(p["time"]["alignedUtc"])
        pos = p["position"]["value"]
        out.append({
            "t": t,
            "clock": clock_of(t),
            "lat": pos["latDeg"],
            "lon": pos["lonDeg"],
            "speedKn": p["speedKn"]["value"],
        })
    return out


def declared_gaps(doc: dict, vessel_id: str) -> list[dict]:
    gaps = []
    for item in doc.get("sampling", {}).get("missingIntervals") or []:
        gaps.append({
            "vesselId": vessel_id,
            "startSec": aligned_sec(item["startUtc"]),
            "endSec": aligned_sec(item["endUtc"]),
        })
    return gaps


def hav_nm(a: dict, b: dict) -> float:
    r_km = 6371.0
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dphi = p2 - p1
    dl = math.radians(b["lon"] - a["lon"])
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return (2 * r_km * math.asin(min(1.0, math.sqrt(h)))) / 1.852


def point_map(rows: list[dict]) -> dict[float, dict]:
    return {row["t"]: row for row in rows}


def metric_point(t: float, own: dict | None, tgt: dict | None) -> dict:
    if own is None or tgt is None:
        return {
            "t": t,
            "clock": clock_of(t),
            "distanceNm": None,
            "dcpaNm": None,
            "tcpaMin": None,
            "riskLevel": None,
        }
    dist = hav_nm(own, tgt)
    # Declared assembly placeholders at exact co-temporal points only; not a core rerun.
    dcpa = round(dist * 0.4 + 0.01, 6)
    tcpa = 3.0
    return {
        "t": t,
        "clock": clock_of(t),
        "distanceNm": round(dist, 6),
        "dcpaNm": dcpa,
        "tcpaMin": tcpa,
        "riskLevel": "Safe",
    }


def speed_series(vessel_id: str, name: str, rows: list[dict]) -> dict:
    return {
        "vesselId": vessel_id,
        "name": name,
        "points": [{"t": r["t"], "clock": r["clock"], "speedKn": r["speedKn"]} for r in rows],
    }


def meta(seed_sha: str) -> dict:
    ref = {"path": "synthetic/unused", "sha256": FAKE, "role": "unused-placeholder"}
    return {
        "seedSha256": seed_sha,
        "seedVerified": True,
        "generatedAt": "2026-11-27T04:00:00Z",
        "generator": "tests_acceptance/w12-chart-explicit-gap/build_cases.py",
        "coreVersion": "assembly-declared/not-a-core-rerun",
        "coreDll": ref,
        "w14Export": ref,
        "w14Frozen": ref,
        "crossCheck": {"against": ["synthetic"], "valuesCompared": 0, "maxAbsDiff": 0, "tolerance": 0, "ok": True},
        "disclaimer": "隔离装配合成元数据。缺口区间由测试装配显式传入，不是分析入口推断，不是官方核心复算。",
    }


def case(*, case_id, key, title, own_id, own_name, tgt_id, tgt_name, step, series, moments, gaps, speeds, notes, refs):
    return {
        "caseId": case_id,
        "key": key,
        "title": title,
        "isFictionalDemo": True,
        "sourceLabel": "合成夹具（显式缺口元数据，非真实案卷）",
        "sourceRefs": refs,
        "epochLocal": "2026-02-01 20:00:00",
        "timeZone": "Asia/Shanghai",
        "vessels": [
            {"vesselId": own_id, "name": own_name},
            {"vesselId": tgt_id, "name": tgt_name},
        ],
        "thresholds": {"dangerDcpaNm": 0.25, "dangerTcpaMin": 6},
        "baseline": {
            "label": title,
            "stepSec": step,
            "cutAtSec": series[-1]["t"] if series else 0,
            "series": series,
            "keyMoments": moments,
        },
        "whatif": None,
        "notes": notes,
        "declaredOpenGaps": gaps,
        "speedSeries": speeds,
    }


def build_cross() -> dict:
    a = load_vessel(FIXTURES / "shared-trajectory-cross-repo/vessel-a.json", CROSS_A)
    b = load_vessel(FIXTURES / "shared-trajectory-cross-repo/vessel-b.json", CROSS_B)
    sa, sb = samples(a), samples(b)
    ma, mb = point_map(sa), point_map(sb)
    # Display grid 0,5,10,14 plus recorded endpoints 6,7 and interior probe 6.5.
    times = [0.0, 5.0, 6.0, 6.5, 7.0, 10.0, 14.0]
    series = [metric_point(t, ma.get(t), mb.get(t)) for t in times]
    gaps = declared_gaps(a, a["vessel"]["vesselId"])
    assert gaps == [{"vesselId": "SYNTHETIC-VESSEL-A", "startSec": 6.0, "endSec": 7.0}]
    notes = [
        "关键反例：声明开区间 (6,7) 整个落在展示格点 5、10 之间；中点 7.5 不在区间内。",
        "A 在 6、7 有原始点，端点保留；6.5 为缺口内部探测点，指标为 null。B 在 6.5 有原始点，船速不断段。",
        "距离仅在两船同刻原始点给出（几何），DCPA/TCPA 为装配声明占位，非核心复算；不造零。",
    ]
    refs = [
        {"path": "fixtures/shared-trajectory-cross-repo/vessel-a.json", "sha256": CROSS_A, "role": "synthetic-fixture"},
        {"path": "fixtures/shared-trajectory-cross-repo/vessel-b.json", "sha256": CROSS_B, "role": "synthetic-fixture"},
    ]
    return case(
        case_id="SYN-W12-CHART-GAP-67",
        key="gap-6-7",
        title="一秒开区间 (6,7) 关键反例",
        own_id="SYNTHETIC-VESSEL-A",
        own_name="合成船 A",
        tgt_id="SYNTHETIC-VESSEL-B",
        tgt_name="合成船 B",
        step=5,
        series=series,
        moments=[],
        gaps=gaps,
        speeds=[
            speed_series("SYNTHETIC-VESSEL-A", "合成船 A", sa),
            speed_series("SYNTHETIC-VESSEL-B", "合成船 B", sb),
        ],
        notes=notes,
        refs=refs,
    )


def build_expanded() -> dict:
    a = load_vessel(FIXTURES / "shared-trajectory-cross-repo-expanded/vessel-a.json", EXP_A)
    b = load_vessel(FIXTURES / "shared-trajectory-cross-repo-expanded/vessel-b.json", EXP_B)
    sa, sb = samples(a), samples(b)
    ma, mb = point_map(sa), point_map(sb)
    # Focus the second contrast on the 6.5s open interval, keep the earlier (60,100) declaration too.
    times = [100.0, 110.0, 120.0, 121.0, 124.25, 125.0, 127.5, 130.0, 140.0]
    series = [metric_point(t, ma.get(t), mb.get(t)) for t in times]
    gaps = declared_gaps(a, a["vessel"]["vesselId"])
    assert any(g["startSec"] == 121.0 and g["endSec"] == 127.5 for g in gaps)
    notes = [
        "expanded 6.5 秒对照：声明开区间 (121, 127.5)；展示格 120/125/130 中 125 落在缺口内部，不得造零。",
        "A 在 121、127.5 有原始位置（端点保留）但 B 无同刻点，故这对端点不给双船指标。T+124.250 为内部探测点。",
        "距离仅同刻几何值；DCPA/TCPA 为装配声明占位，非本轮核心复算。同时保留 A 的 (60,100) 声明。",
    ]
    refs = [
        {"path": "fixtures/shared-trajectory-cross-repo-expanded/vessel-a.json", "sha256": EXP_A, "role": "synthetic-fixture"},
        {"path": "fixtures/shared-trajectory-cross-repo-expanded/vessel-b.json", "sha256": EXP_B, "role": "synthetic-fixture"},
    ]
    return case(
        case_id="SYN-W12-CHART-GAP-EXP",
        key="gap-expanded-6-5s",
        title="expanded 6.5 秒开区间对照",
        own_id="SYN-VESSEL-A",
        own_name="合成船 A（expanded）",
        tgt_id="SYN-VESSEL-B",
        tgt_name="合成船 B（expanded）",
        step=5,
        series=series,
        moments=[],
        gaps=gaps,
        speeds=[
            speed_series("SYN-VESSEL-A", "合成船 A（expanded）", [r for r in sa if 100 <= r["t"] <= 140]),
            speed_series("SYN-VESSEL-B", "合成船 B（expanded）", [r for r in sb if 100 <= r["t"] <= 140]),
        ],
        notes=notes,
        refs=refs,
    )


def build_offset() -> dict:
    """Non-centered (1,2) inside a 0/10 display interval. Handmade, not a 2048c60 original."""
    own_id, tgt_id = "SYN-OFFSET-A", "SYN-OFFSET-B"
    # Schematic positions only; same-instant pair at 0 and 10.
    own = {
        0.0: {"t": 0.0, "clock": clock_of(0), "lat": 1.0, "lon": 2.0, "speedKn": 8.0},
        1.0: {"t": 1.0, "clock": clock_of(1), "lat": 1.00001, "lon": 2.00002, "speedKn": 8.0},
        2.0: {"t": 2.0, "clock": clock_of(2), "lat": 1.00002, "lon": 2.00004, "speedKn": 8.0},
        10.0: {"t": 10.0, "clock": clock_of(10), "lat": 1.0001, "lon": 2.0002, "speedKn": 8.0},
    }
    tgt = {
        0.0: {"t": 0.0, "clock": clock_of(0), "lat": 1.01, "lon": 2.0, "speedKn": 9.0},
        5.0: {"t": 5.0, "clock": clock_of(5), "lat": 1.01, "lon": 2.0001, "speedKn": 9.0},
        10.0: {"t": 10.0, "clock": clock_of(10), "lat": 1.01, "lon": 2.0002, "speedKn": 9.0},
    }
    times = [0.0, 1.0, 1.5, 2.0, 10.0]
    series = [metric_point(t, own.get(t), tgt.get(t)) for t in times]
    gaps = [{"vesselId": own_id, "startSec": 1.0, "endSec": 2.0}]
    notes = [
        "非居中反例：声明开区间 (1,2) 落在展示间隔 0/10 内；中点 5 不在区间内，不能靠探测中点或等待格点落入缺口。",
        "缺轨船在 1、2 保留端点，内部 1.5 无指标。对照船在 0、5、10 连续，船速不断段。",
        "本条为测试装配手造元数据，不是 2048c60 原件。",
    ]
    return case(
        case_id="SYN-W12-CHART-GAP-12",
        key="gap-1-2-offset",
        title="非居中开区间 (1,2) 反例",
        own_id=own_id,
        own_name="合成缺轨船",
        tgt_id=tgt_id,
        tgt_name="合成对照船",
        step=10,
        series=series,
        moments=[],
        gaps=gaps,
        speeds=[
            speed_series(own_id, "合成缺轨船", list(own.values())),
            speed_series(tgt_id, "合成对照船", list(tgt.values())),
        ],
        notes=notes,
        refs=[{"path": "synthetic/offset-1-2.json", "sha256": FAKE, "role": "synthetic-fixture"}],
    )


def build_doc() -> dict:
    cases = [build_cross(), build_expanded(), build_offset()]
    raw_cases = json.dumps(cases, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    seed_sha = hashlib.sha256(raw_cases).hexdigest()
    for c in cases:
        c["meta"] = meta(seed_sha)
    return {
        "schemaVersion": "synthetic-w12-chart-gap-1",
        "fixturePin": "2048c60fd6650c6f2c99a76a16be463a3895655d",
        "productPin": "309b0ccfdefd71b8c25603e62fbc4f720cb5d805",
        "cases": cases,
    }


def write_cases(directory: Path) -> tuple[Path, str]:
    directory.mkdir(parents=True, exist_ok=True)
    doc = build_doc()
    path = directory / "cases.json"
    raw = json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8")
    path.write_bytes(raw)
    return path, hashlib.sha256(raw).hexdigest()


if __name__ == "__main__":
    dest = Path("/tmp/w12-chart-gap-cases-preview")
    path, digest = write_cases(dest)
    print(path, digest)
