"""Tiny synthetic seed for the official /analysis entry. Distinctive values must not leak into the wiring view."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

FAKE = "d" * 64
LEAK = 9.999


def build_doc() -> dict:
    ref = {"path": "synthetic/live-entry-unused", "sha256": FAKE, "role": "unused-placeholder"}
    series = [
        {"t": 0, "clock": "08:00:00", "distanceNm": LEAK, "dcpaNm": LEAK, "tcpaMin": LEAK, "riskLevel": "Safe"},
        {"t": 10, "clock": "08:00:10", "distanceNm": LEAK, "dcpaNm": LEAK, "tcpaMin": LEAK, "riskLevel": "Safe"},
    ]
    case = {
        "caseId": "SYN-W12-LIVE-ENTRY",
        "key": "live-entry",
        "title": "合成入口对照（离线种子，不得回填）",
        "isFictionalDemo": True,
        "sourceLabel": "合成夹具（非真实案卷）",
        "sourceRefs": [ref],
        "epochLocal": "2026-01-01 08:00:00",
        "timeZone": "Asia/Shanghai",
        "vessels": [{"vesselId": "live-own", "name": "入口本船"}, {"vesselId": "live-tgt", "name": "入口目标"}],
        "thresholds": {"dangerDcpaNm": 0.25},
        "baseline": {"label": "入口对照航迹", "stepSec": 10, "cutAtSec": 10, "series": series, "keyMoments": []},
        "whatif": None,
        "notes": ["现场分析入口种子，不得用于补已登记分析指标。"],
    }
    raw_cases = json.dumps([case], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    seed_sha = hashlib.sha256(raw_cases).hexdigest()
    case["meta"] = {
        "seedSha256": seed_sha, "seedVerified": True, "generatedAt": "2026-01-01T00:00:00Z",
        "generator": "tests_acceptance/w12-first-registered-wiring/live_seed.py",
        "coreVersion": "unused", "coreDll": ref, "w14Export": ref, "w14Frozen": ref,
        "crossCheck": {"against": ["synthetic"], "valuesCompared": 0, "maxAbsDiff": 0, "tolerance": 0, "ok": True},
        "disclaimer": "合成入口对照。",
    }
    return {
        "schemaVersion": "synthetic-w12-frw-live-1",
        "generatedAt": "2026-01-01T00:00:00Z",
        "generator": "tests_acceptance/w12-first-registered-wiring/live_seed.py",
        "coreVersion": "unused", "coreDll": ref, "w14Export": ref, "w14Frozen": ref,
        "crossCheck": {"against": ["synthetic"], "valuesCompared": 0, "maxAbsDiff": 0, "tolerance": 0, "ok": True},
        "disclaimer": "合成入口对照。",
        "cases": [case],
    }


def write_seed(directory: Path) -> tuple[Path, Path, str]:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "w12-live-entry-seed.json"
    raw = json.dumps(build_doc(), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    path.write_bytes(raw)
    sidecar = path.with_suffix(".sha256")
    sidecar.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return path, sidecar, digest
