"""Build AnalysisCase documents from a same-transaction capture and official core results."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from registered_read import GAP_UNWIRED_REASON, OWN, TARGET

CST = timezone(timedelta(hours=8))
EPOCH = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
FAKE = "e" * 64


def clock_of(sec: float) -> str:
    t = (EPOCH + timedelta(seconds=sec)).astimezone(CST)
    if abs(sec - int(sec)) < 1e-9:
        return t.strftime("%H:%M:%S")
    ms = int(round((sec - int(sec)) * 1000))
    return t.strftime("%H:%M:%S") + f".{ms:03d}"


def results_by_time(metrics: dict[str, Any] | None) -> dict[float, dict[str, Any]]:
    if not metrics:
        return {}
    out = {}
    for row in metrics.get("results") or []:
        out[float(row["timeSec"])] = row
    return out


def meta(core_version: str, dll_sha: str) -> dict[str, Any]:
    ref = {"path": "synthetic/wiring-unused", "sha256": FAKE, "role": "unused-placeholder"}
    core = {"path": "mcis-core.dll", "sha256": dll_sha, "role": "official-mcis-core"}
    return {
        "seedSha256": "f" * 64,
        "seedVerified": True,
        "generatedAt": "2026-11-27T05:00:00Z",
        "generator": "tests_acceptance/w12-first-registered-wiring/build_view.py",
        "coreVersion": core_version,
        "coreDll": core,
        "w14Export": ref,
        "w14Frozen": ref,
        "crossCheck": {"against": ["synthetic"], "valuesCompared": 0, "maxAbsDiff": 0, "tolerance": 0, "ok": True},
        "disclaimer": "隔离宿主接线。正式 /analysis 入口仍读离线种子，本页不从该种子补指标。",
    }


def complete_case(capture: dict[str, Any], core: dict[str, Any], dll_sha: str, times: list[float]) -> dict[str, Any]:
    by_t = results_by_time(core.get("metrics"))
    series = []
    for t in times:
        row = by_t.get(t)
        if row:
            series.append({
                "t": t,
                "clock": clock_of(t),
                "distanceNm": row["currentDistanceNm"],
                "dcpaNm": row["dcpaNm"],
                "tcpaMin": row["tcpaMin"],
                "riskLevel": row.get("riskLevel") or "Safe",
            })
        else:
            series.append({
                "t": t,
                "clock": clock_of(t),
                "distanceNm": None,
                "dcpaNm": None,
                "tcpaMin": None,
                "riskLevel": None,
            })
    identities = [
        {k: v for k, v in capture["identities"][vid].items() if k in {"vesselId", "previewDigest", "sourceSha256", "reportSha256", "pointCount"}}
        for vid in (OWN, TARGET) if vid in capture["identities"]
    ]
    return {
        "caseId": capture["identities"][OWN]["caseId"],
        "key": "registered-complete",
        "title": "已登记双船（同刻核心）",
        "isFictionalDemo": True,
        "sourceLabel": "已登记合成航迹（同一只读事务回执）",
        "sourceRefs": [{"path": "mcis-core.dll", "sha256": dll_sha, "role": "official-mcis-core"}],
        "epochLocal": "2026-01-01 08:00:00",
        "timeZone": "Asia/Shanghai",
        "vessels": [{"vesselId": OWN, "name": "合成本船"}, {"vesselId": TARGET, "name": "合成目标"}],
        "thresholds": {"dangerDcpaNm": 0.3, "dangerTcpaMin": 6},
        "baseline": {
            "label": "已登记同刻样本（真实核心）",
            "stepSec": 10,
            "cutAtSec": max(times),
            "series": series,
            "keyMoments": [],
        },
        "whatif": None,
        "notes": [
            "仅双船同刻且有出处的样本调用既有 mcis-core cpa；无同刻样本不显示指标，不用离线种子补。",
            GAP_UNWIRED_REASON,
        ],
        "meta": meta(core.get("coreVersion") or "unknown", dll_sha),
        "metricProvenance": {
            "distance": "mcis-core",
            "dcpa": "mcis-core",
            "tcpa": "mcis-core",
            "note": f"仅 {', '.join(f'T+{t:g}' for t in sorted(by_t))} 为真实核心；其它时点无同刻样本，未回填。核心两次调用一致={core.get('recalculatedIdentical')}。DLL SHA-256 {dll_sha}。",
        },
        "registeredIdentities": identities,
        "gapWiring": {"status": "unwired", "reason": GAP_UNWIRED_REASON},
    }


def missing_payload(capture: dict[str, Any]) -> dict[str, Any]:
    return {
        "caseId": "SYN-W12-FR-INCOMPLETE",
        "ok": False,
        "reason": capture.get("reason"),
        "identities": capture.get("identities") or {},
        "currentAnalysis": None,
        "metricsReturned": False,
        "note": "缺一船已核验回执，不显示当前分析指标，未用离线种子补结果。",
        "gapWiring": {"status": "unwired", "reason": GAP_UNWIRED_REASON},
    }
