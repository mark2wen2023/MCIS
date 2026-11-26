"""Two purely synthetic analysis cases. Never load the product historical seed."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

CASE_A = "SYN-W12-SNAP-A"
CASE_B = "SYN-W12-SNAP-B"
TITLE_A = "合成夹具甲案（仅测试）"
TITLE_B = "合成夹具乙案（仅测试）"
MARK_A = "SYN-W12-A-MARK"
MARK_B = "SYN-W12-B-MARK"
CURVE_A = "甲案航迹 SYN-W12-A-CURVE"
CURVE_B = "乙案航迹 SYN-W12-B-CURVE"
CLOCK_A = "12:01:00"
CLOCK_B = "15:44:30"
DIST_A = 0.421
DIST_B = 1.908
DCPA_A = 0.187
DCPA_B = 0.776
OWN_A = "合成甲本船"
TGT_A = "合成甲目标"
OWN_B = "合成乙本船"
TGT_B = "合成乙目标"

A_MARKERS = (CASE_A, TITLE_A, MARK_A, CURVE_A, CLOCK_A, OWN_A, TGT_A, "0.421", "0.187")
B_MARKERS = (CASE_B, TITLE_B, MARK_B, CURVE_B, CLOCK_B, OWN_B, TGT_B, "1.908", "0.776")


def _ref(path: str, role: str, digest: str) -> dict:
    return {"path": path, "sha256": digest, "role": role}


def _series(start: int, clocks: list[str], distances: list[float], dcpas: list[float], tcpas: list[float]):
    levels = ["Safe", "Warning", "Danger", "Danger", "Warning", "Safe"]
    out = []
    for i, clock in enumerate(clocks):
        out.append({
            "t": start + i * 60,
            "clock": clock,
            "distanceNm": distances[i],
            "dcpaNm": dcpas[i],
            "tcpaMin": tcpas[i],
            "riskLevel": levels[i],
        })
    return out


def _case(*, case_id, key, title, mark, curve, clock, dist, dcpa, own, tgt, notes_clocks, distances, dcpas, tcpas):
    fake = "a" * 64
    return {
        "caseId": case_id,
        "key": key,
        "title": title,
        "isFictionalDemo": True,
        "sourceLabel": "合成夹具（非真实案卷）",
        "sourceRefs": [_ref(f"synthetic/{key}.json", "synthetic-fixture", fake)],
        "epochLocal": "2026-02-01 12:00:00",
        "timeZone": "Asia/Shanghai",
        "vessels": [{"vesselId": f"{key}-own", "name": own}, {"vesselId": f"{key}-tgt", "name": tgt}],
        "thresholds": {"dangerDcpaNm": 0.25, "dangerTcpaMin": 6, "warningDcpaNm": 0.5, "warningTcpaMin": 12},
        "baseline": {
            "label": curve,
            "stepSec": 60,
            "cutAtSec": 300,
            "series": _series(0, notes_clocks, distances, dcpas, tcpas),
            "keyMoments": [{
                "kind": "minDistance",
                "label": mark,
                "t": 60,
                "clock": clock,
                "value": dist,
                "unit": "nm",
                "source": "synthetic",
            }, {
                "kind": "minDcpa",
                "label": f"{mark} DCPA",
                "t": 60,
                "clock": clock,
                "value": dcpa,
                "unit": "nm",
                "source": "synthetic",
            }],
        },
        "whatif": None,
        "notes": ["合成测试样本，不含真实资料，不代表登记轨迹版本。"],
    }


def build_doc() -> dict:
    fake = "b" * 64
    return {
        "schemaVersion": "synthetic-w12-scope-1",
        "generatedAt": "2026-02-01T04:00:00Z",
        "generator": "tests_acceptance/w12-snapshot-scope-browser/synthetic_seed.py",
        "coreVersion": "synthetic-core/0",
        "coreDll": _ref("synthetic/mcis-core-not-invoked.dll", "unused-placeholder", fake),
        "w14Export": _ref("synthetic/w14-not-used.json", "unused-placeholder", fake),
        "w14Frozen": _ref("synthetic/w14-frozen-not-used.json", "unused-placeholder", fake),
        "crossCheck": {"against": ["synthetic"], "valuesCompared": 0, "maxAbsDiff": 0, "tolerance": 0, "ok": True},
        "disclaimer": "合成测试夹具。未调用模型，未使用真实案卷，未接入登记轨迹换版信号。",
        "cases": [
            _case(
                case_id=CASE_A, key="syn-w12-a", title=TITLE_A, mark=MARK_A, curve=CURVE_A,
                clock=CLOCK_A, dist=DIST_A, dcpa=DCPA_A, own=OWN_A, tgt=TGT_A,
                notes_clocks=["12:00:00", "12:01:00", "12:02:00", "12:03:00", "12:04:00", "12:05:00"],
                distances=[0.860, 0.421, 0.502, 0.640, 0.790, 0.980],
                dcpas=[0.310, 0.187, 0.220, 0.280, 0.360, 0.450],
                tcpas=[8.0, 6.0, 4.0, 2.0, 0.5, -1.0],
            ),
            _case(
                case_id=CASE_B, key="syn-w12-b", title=TITLE_B, mark=MARK_B, curve=CURVE_B,
                clock=CLOCK_B, dist=DIST_B, dcpa=DCPA_B, own=OWN_B, tgt=TGT_B,
                notes_clocks=["15:43:30", "15:44:30", "15:45:30", "15:46:30", "15:47:30", "15:48:30"],
                distances=[2.400, 1.908, 2.050, 2.200, 2.380, 2.600],
                dcpas=[0.920, 0.776, 0.810, 0.860, 0.910, 0.980],
                tcpas=[12.0, 10.0, 8.0, 6.0, 4.0, 2.0],
            ),
        ],
    }


def write_seed(directory: Path) -> tuple[Path, Path, str]:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "w12-synthetic-seed.json"
    raw = json.dumps(build_doc(), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    path.write_bytes(raw)
    sidecar = path.with_suffix(".sha256")
    sidecar.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return path, sidecar, digest
