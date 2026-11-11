#!/usr/bin/env python3
"""mcis-core align 子命令端到端测试。

覆盖：
1. 演示案例 CASE-2026-DEMO-LILY-MARY（unity/Tests_W2_Vdr/Samples，虚构数据）
2. 畸形输入：非 0 退出码，不崩溃
3. YANGZE 22 片段：从 reports/yangze22/tracks_from_report.csv 构造，标注来源
   （公开调查报告，Mark 已确认可直接使用真实数据）

输出按 contracts/schemas/conflict.schema.json 用 jsonschema 校验。
"""
from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import jsonschema
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[3]  # tests -> mcis-core -> tools -> project root
CORE_SH = ROOT / "tools" / "mcis-core" / "mcis-core.sh"
DOTNET = Path.home() / ".dotnet" / "dotnet"
SAMPLES = ROOT / "unity" / "Tests_W2_Vdr" / "Samples"
YANGZE_CSV = ROOT / "reports" / "yangze22" / "tracks_from_report.csv"
SCHEMA_DIR = ROOT / "contracts" / "schemas"
VENV_PY = Path("/workspace/.venv-reports/bin/python")

DEMO_CASE = "CASE-2026-DEMO-LILY-MARY"
# 与 W2 样例设计一致：纪元 06:00:00Z，使 06:15 对应 SimTime 900 s。
# 服务种子的 caseEpochUtc 是 06:15:00Z（SimTime 0 = 14:15 北京时间），偏移量不受纪元影响。
DEMO_EPOCH = "2026-05-18T06:00:00Z"
YANGZE_CASE = "CJK-2024-1230-YangZe22-VegaDream"
YANGZE_EPOCH = "2024-12-30T13:00:00Z"  # 北京时间 21:00


def _registry() -> Registry:
    resources = []
    for p in SCHEMA_DIR.glob("*.schema.json"):
        doc = json.loads(p.read_text(encoding="utf-8"))
        resources.append((doc["$id"], Resource.from_contents(doc)))
    return Registry().with_resources(resources)


_REGISTRY = _registry()
_CONFLICT_VALIDATOR = Draft202012Validator(
    {"$ref": "https://mcis.local/contracts/v1/conflict.schema.json"},
    registry=_REGISTRY,
    format_checker=FormatChecker(),
)


def validate_conflict(doc: dict) -> list[str]:
    return [
        f"{'/'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}"
        for e in _CONFLICT_VALIDATOR.iter_errors(doc)
    ]


def run_align(payload, timeout=90):
    env = os.environ.copy()
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    env["DOTNET_NOLOGO"] = "1"
    env.setdefault("MCIS_DOTNET", str(DOTNET))
    proc = subprocess.run(
        [str(CORE_SH), "align"],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        timeout=timeout,
        check=False,
        env=env,
    )
    stdout = proc.stdout.decode("utf-8", "replace").strip()
    stderr = proc.stderr.decode("utf-8", "replace")
    parsed = None
    if stdout:
        # 取最后一行 JSON（构建日志在 stderr；若漏到 stdout 则忽略非 JSON 行）
        for line in reversed(stdout.splitlines()):
            line = line.strip()
            if line.startswith("{") or line.startswith("["):
                try:
                    parsed = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
    return proc.returncode, parsed, stdout, stderr


def scalar_mapping():
    return {
        "timeColumn": "time_utc",
        "columns": [
            {"column": "sog_kn", "kind": "SpeedOverGround"},
            {"column": "cog_deg", "kind": "CourseOverGround"},
            {"column": "hdg_deg", "kind": "Heading"},
            {"column": "rot_deg_per_min", "kind": "RateOfTurn"},
            {"column": "rudder_deg", "kind": "RudderAngle"},
        ],
    }


def demo_request() -> dict:
    return {
        "caseId": DEMO_CASE,
        "caseEpochUtc": DEMO_EPOCH,
        "referenceSourceId": "GNSS",
        "offsetMethod": "Median",
        "sources": [
            {"sourceId": "MARY-VDR", "format": "nmea", "path": str(SAMPLES / "mary_vdr.nmea")},
            {"sourceId": "LILY-SVDR", "format": "nmea", "path": str(SAMPLES / "lily_svdr.nmea")},
            {
                "sourceId": "VTS-AIS",
                "format": "csv",
                "path": str(SAMPLES / "vts_ais.csv"),
                "csvMapping": {
                    "timeColumn": "time_utc",
                    "columns": [
                        {"column": "sog_kn", "kind": "SpeedOverGround"},
                        {"column": "cog_deg", "kind": "CourseOverGround"},
                    ],
                },
            },
            {
                "sourceId": "MARY-BRIDGE",
                "format": "csv",
                "path": str(SAMPLES / "mary_telegraph_rudder.csv"),
                "csvMapping": {
                    "timeColumn": "time_local",
                    "timeFormat": "yyyy-MM-dd HH:mm:ss",
                    "timeZoneOffsetHours": 8,
                    "eventColumn": "event",
                    "columns": [
                        {
                            "column": "telegraph",
                            "kind": "EngineTelegraph",
                            "markChanges": True,
                            "textValues": {
                                "STOP": 0,
                                "HALF AHEAD": 3,
                                "FULL AHEAD": 4,
                                "SLOW AHEAD": 2,
                                "FULL ASTERN": -4,
                            },
                        },
                        {"column": "rudder_deg", "kind": "RudderAngle"},
                    ],
                },
            },
            {
                "sourceId": "MARY-MEDIA",
                "format": "mediaManifest",
                "path": str(SAMPLES / "mary_media_manifest.csv"),
            },
        ],
        "manualAnchors": {"path": str(SAMPLES / "manual_anchors.csv")},
    }


def yangze_fragment_sources() -> tuple[list[dict], dict]:
    """从报告航迹 CSV 抽出 YANGZE 22 在 21:44:44–22:01:54 的片段，按 provenance 分源。

    来源标注：
    - YANGZE22-VDR ← ReportFigure-VDR（报告 VDR 回放截图读数）
    - YANGZE22-AIS ← ReportFigure-AIS（报告 VTS 截图中的 AIS 信息框图读）
    - YANGZE22-NARRATIVE ← ReportNarrative（报告正文文字）
    数据文件：reports/yangze22/tracks_from_report.csv；案件 CJK-2024-1230-YangZe22-VegaDream。
    """
    raw = YANGZE_CSV.read_text(encoding="utf-8")
    lines = [ln for ln in raw.splitlines() if not ln.startswith("#") and ln.strip()]
    rows = list(csv.DictReader(io.StringIO("\n".join(lines))))
    window = ("2024-12-30T21:44:44+08:00", "2024-12-30T22:01:54+08:00")
    by_src: dict[str, list[dict]] = {
        "YANGZE22-VDR": [],
        "YANGZE22-AIS": [],
        "YANGZE22-NARRATIVE": [],
    }
    provenance_map = {
        "ReportFigure-VDR": "YANGZE22-VDR",
        "ReportFigure-AIS": "YANGZE22-AIS",
        "ReportNarrative": "YANGZE22-NARRATIVE",
    }
    used = 0
    for row in rows:
        if row["vesselId"] != "yangze22":
            continue
        t = row["timeBeijing"]
        if t < window[0] or t > window[1]:
            continue
        sid = provenance_map.get(row["provenance"])
        if not sid:
            continue
        by_src[sid].append(row)
        used += 1

    sources = []
    for sid, items in by_src.items():
        buf = io.StringIO()
        buf.write("# YANGZE 22 片段，取自公开调查报告 tracks_from_report.csv，provenance 见 sourceId。\n")
        buf.write("# 不是 AIS/VDR 原始数据；值为报告正文或插图读数。\n")
        buf.write("time_utc,sog_kn,cog_deg,hdg_deg,rot_deg_per_min,rudder_deg\n")
        for r in items:
            def cell(k):
                v = (r.get(k) or "").strip()
                return v
            buf.write(
                ",".join(
                    [
                        cell("timeUtc"),
                        cell("sogKn"),
                        cell("cogDeg"),
                        cell("hdgDeg"),
                        cell("rotDegPerMin"),
                        cell("rudderDeg"),
                    ]
                )
                + "\n"
            )
        sources.append(
            {
                "sourceId": sid,
                "format": "csv",
                "text": buf.getvalue(),
                "csvMapping": scalar_mapping(),
            }
        )
    meta = {
        "rowsUsed": used,
        "sourceFile": str(YANGZE_CSV.relative_to(ROOT)),
        "vesselId": "yangze22",
        "windowBeijing": list(window),
        "provenance": {
            "YANGZE22-VDR": "ReportFigure-VDR",
            "YANGZE22-AIS": "ReportFigure-AIS",
            "YANGZE22-NARRATIVE": "ReportNarrative",
        },
    }
    return sources, meta


def assert_conflicts_valid(conflicts, case_id):
    assert isinstance(conflicts, list) and conflicts, "应至少检出一条冲突"
    errors = []
    for i, c in enumerate(conflicts):
        assert c.get("caseId") == case_id, f"conflicts[{i}].caseId={c.get('caseId')}"
        unit = c.get("deltaUnit")
        if unit == "°":
            raise AssertionError(f"conflicts[{i}].deltaUnit 仍为 '°'，W2.2 写盘应已换成 deg")
        if c.get("trackKind") in ("Position", "TargetPosition") and not unit:
            raise AssertionError(f"conflicts[{i}] 位置冲突 deltaUnit 为空，适配层应临时补成 m（待 W2.3）")
        errs = validate_conflict(c)
        if errs:
            errors.append(f"conflicts[{i}] {c.get('conflictId')}: " + "; ".join(errs))
    if errors:
        raise AssertionError("合同校验失败：\n" + "\n".join(errors))


def test_demo_lily_mary():
    code, env, stdout, stderr = run_align(demo_request())
    assert code == 0, f"exit={code} stderr={stderr[-1500:]}\nstdout={stdout[-500:]}"
    assert env and env.get("ok") is True and env.get("command") == "align"
    result = env["result"]
    assert result["caseId"] == DEMO_CASE
    conflicts = result["conflicts"]
    assert_conflicts_valid(conflicts, DEMO_CASE)

    kinds = {c["trackKind"] for c in conflicts}
    assert "CourseOverGround" in kinds, kinds
    assert "SpeedOverGround" in kinds, kinds

    course = next(
        c
        for c in conflicts
        if c["trackKind"] == "CourseOverGround"
        and {c["a"]["sourceLabel"], c["b"]["sourceLabel"]} == {"MARY-VDR", "VTS-AIS"}
    )
    assert course["delta"] > 2.4
    assert 1300.0 <= course["timeSec"] <= 1320.0
    assert course["deltaUnit"] == "deg"
    assert course["status"] == "Open"
    assert course["detectedBy"] == "RuleEngine"
    assert course["conflictId"].startswith("C-")

    speed = next(
        c
        for c in conflicts
        if c["trackKind"] == "SpeedOverGround"
        and {c["a"]["sourceLabel"], c["b"]["sourceLabel"]} == {"MARY-VDR", "VTS-AIS"}
    )
    assert speed["delta"] > 0.39
    assert 1370.0 <= speed["timeSec"] <= 1380.0

    offsets = {o["sourceId"]: o for o in result["clockOffsets"]}
    assert "MARY-VDR" in offsets and "LILY-SVDR" in offsets and "GNSS" in offsets
    assert abs(offsets["MARY-VDR"]["offsetSeconds"] - 3.2) < 0.1
    assert abs(offsets["LILY-SVDR"]["offsetSeconds"] - (-1.5)) < 0.1
    assert offsets["GNSS"]["isReference"] is True
    print(
        f"DEMO ok: conflicts={len(conflicts)} "
        f"MARY offset={offsets['MARY-VDR']['offsetSeconds']:.3f}s "
        f"LILY offset={offsets['LILY-SVDR']['offsetSeconds']:.3f}s"
    )


def test_malformed_input_does_not_crash():
    cases = [
        ({}, "缺少 caseId"),
        ({"caseId": DEMO_CASE}, "缺少 caseEpochUtc"),
        ({"caseId": DEMO_CASE, "caseEpochUtc": DEMO_EPOCH, "sources": []}, "sources"),
        (
            {
                "caseId": DEMO_CASE,
                "caseEpochUtc": "not-a-date",
                "sources": [{"sourceId": "X", "format": "nmea", "text": "$GPGGA*00"}],
            },
            "caseEpochUtc",
        ),
        (
            {
                "caseId": DEMO_CASE,
                "caseEpochUtc": DEMO_EPOCH,
                "sources": [{"sourceId": "X", "format": "csv", "text": "a,b\n1,2"}],
            },
            "csvMapping",
        ),
    ]
    for payload, hint in cases:
        code, env, stdout, stderr = run_align(payload)
        assert code != 0, f"畸形输入应失败 hint={hint} env={env}"
        assert code == 4, f"期望退出码 4（BAD_REQUEST/BAD_JSON），得到 {code} hint={hint} stderr={stderr[-400:]}"
        assert env is not None, f"应输出 JSON 错误外壳，不崩溃 hint={hint} stdout={stdout!r} stderr={stderr[-400:]}"
        assert env.get("ok") is False
        assert env.get("error", {}).get("code") in {"BAD_REQUEST", "BAD_JSON"}
        assert env.get("command") == "align"

    # 非法 JSON
    env = os.environ.copy()
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    env["DOTNET_NOLOGO"] = "1"
    env.setdefault("MCIS_DOTNET", str(DOTNET))
    proc = subprocess.run(
        [str(CORE_SH), "align"],
        input=b"{not json",
        capture_output=True,
        timeout=90,
        check=False,
        env=env,
    )
    assert proc.returncode == 4
    out = proc.stdout.decode("utf-8", "replace").strip().splitlines()[-1]
    parsed = json.loads(out)
    assert parsed["ok"] is False and parsed["error"]["code"] == "BAD_JSON"
    print("MALFORMED ok: 5 BAD_REQUEST + 1 BAD_JSON，均 exit 4 且不崩溃")


def test_yangze22_fragment():
    sources, meta = yangze_fragment_sources()
    assert all(s["text"].count("\n") > 2 for s in sources), meta
    payload = {
        "caseId": YANGZE_CASE,
        "caseEpochUtc": YANGZE_EPOCH,
        "referenceSourceId": "GNSS",
        "sources": sources,
        "calibrate": True,
    }
    code, env, stdout, stderr = run_align(payload)
    assert code == 0, f"exit={code} stderr={stderr[-1500:]}\nstdout={stdout[-800:]}"
    result = env["result"]
    assert result["caseId"] == YANGZE_CASE
    conflicts = result["conflicts"]
    assert_conflicts_valid(conflicts, YANGZE_CASE)

    # 报告读数本身已对齐到北京时间/UTC，通常没有 GNSS 锚点，钟差估计允许失败并继续检测。
    kinds = {c["trackKind"] for c in conflicts}
    # 22:00:42 AIS cog 113 vs 正文 98；22:01:54 AIS 54 vs 正文 47
    assert "CourseOverGround" in kinds, (kinds, conflicts)
    course_vals = [
        c
        for c in conflicts
        if c["trackKind"] == "CourseOverGround"
        and {c["a"]["sourceLabel"], c["b"]["sourceLabel"]} <= {"YANGZE22-AIS", "YANGZE22-NARRATIVE", "YANGZE22-VDR"}
    ]
    assert course_vals, conflicts
    assert any(c["delta"] >= 6 for c in course_vals), course_vals
    assert all(c["deltaUnit"] == "deg" for c in course_vals)

    rot = [c for c in conflicts if c["trackKind"] == "RateOfTurn"]
    # 22:01:54 AIS ROT 3 vs VDR 20.1；W2.2 把 °/min 写成 deg/min
    if rot:
        assert all(c.get("deltaUnit") == "deg/min" for c in rot)

    print(
        f"YANGZE22 ok: rows={meta['rowsUsed']} conflicts={len(conflicts)} "
        f"kinds={sorted(kinds)} calibration_error={result['calibration'].get('error')!r} "
        f"source={meta['sourceFile']}"
    )
    return meta


def main():
    assert CORE_SH.exists(), CORE_SH
    assert SAMPLES.exists(), SAMPLES
    assert YANGZE_CSV.exists(), YANGZE_CSV
    test_demo_lily_mary()
    test_malformed_input_does_not_crash()
    test_yangze22_fragment()
    print("ALL ALIGN CLI TESTS PASSED")


if __name__ == "__main__":
    main()
