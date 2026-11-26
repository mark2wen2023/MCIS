#!/usr/bin/env python3
"""W4 manual-anchor core CLI acceptance. Synthetic inputs only. Does not build or install."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PIN = "94d5e38c926fda232bb987b60fa9145e4bcf01a7"
ALIGN_CS_SHA256 = "4ce13b7fec0898f01d3157b99278561a1ea391d0f4ce3140c1bc9f79fda99b58"
CORE_DLL_SHA256 = "f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf"
CORE_RUNTIME_SHA256 = "3d25821758613e4cd940d143ccb03c93704140077e69104996832510f38f6598"
CORE_DEPS_SHA256 = "fda133109cf9fc926cbda09598ad344f75dc57ec02e345b6923ec5fe2dff9d12"
EXPECTED_OFFSET = 12.0
OFFSET_TOL = 1e-6
CASE_ID = "SYN-W4-MANUAL-ANCHOR-1"
EPOCH = "2026-03-01T08:00:00Z"
REF = "SYN-GNSS"
SRC = "SYN-VDR"
HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def die(msg: str, code: int = 1) -> None:
    print("W4 manual-anchor acceptance stopped: " + msg, file=sys.stderr)
    raise SystemExit(code)


def require_sha(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        die(f"{label} missing: {path}")
    got = sha256(path)
    if got != expected:
        die(f"{label} SHA-256 mismatch: {path} got {got} expected {expected}")
    return got


def iso_now() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def csv_mapping() -> dict:
    return {
        "timeColumn": "time_utc",
        "columns": [
            {"column": "sog_kn", "kind": "SpeedOverGround"},
            {"column": "cog_deg", "kind": "CourseOverGround"},
        ],
    }


def source_entry(source_id: str, rel: str) -> dict:
    return {
        "sourceId": source_id,
        "format": "csv",
        "path": str(FIXTURES / rel),
        "emitGnssAnchors": False,
        "csvMapping": csv_mapping(),
    }


def sources() -> list:
    return [source_entry(REF, "syn-gnss.csv"), source_entry(SRC, "syn-vdr.csv")]


def request_group1() -> dict:
    return {
        "caseId": CASE_ID,
        "caseEpochUtc": EPOCH,
        "referenceSourceId": REF,
        "offsetMethod": "Median",
        "calibrate": True,
        "sources": sources(),
        "manualAnchors": {"path": str(FIXTURES / "manual-anchors-valid.csv")},
    }


def request_group2() -> dict:
    body = request_group1()
    body.pop("manualAnchors", None)
    return body


def request_group3() -> dict:
    body = request_group1()
    body["manualAnchors"] = {"path": str(FIXTURES / "manual-anchors-bad-time.csv")}
    return body


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_align(dotnet: Path, dll: Path, request: dict, raw_out: Path, raw_err: Path, timeout: int):
    env = os.environ.copy()
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    env["DOTNET_NOLOGO"] = "1"
    env["DOTNET_ROOT"] = str(dotnet.parent)
    payload = json.dumps(request, ensure_ascii=False).encode("utf-8")
    proc = subprocess.run(
        [str(dotnet), str(dll), "align"],
        input=payload,
        capture_output=True,
        timeout=timeout,
        check=False,
        env=env,
        cwd=str(dll.parent),
    )
    raw_out.write_bytes(proc.stdout)
    raw_err.write_bytes(proc.stderr)
    parsed = None
    stdout = proc.stdout.decode("utf-8", "replace")
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{") or line.startswith("["):
            try:
                parsed = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
    return proc.returncode, parsed, stdout


def finite_offsets(clock_offsets) -> list:
    found = []
    if not isinstance(clock_offsets, list):
        return found
    for item in clock_offsets:
        if not isinstance(item, dict):
            continue
        val = item.get("offsetSeconds")
        if isinstance(val, (int, float)):
            found.append(item)
    return found


def source_cal(result: dict, source_id: str):
    sources = ((result or {}).get("calibration") or {}).get("sources") or []
    for item in sources:
        if item.get("sourceId") == source_id:
            return item
    return None


def check_group1(exit_code: int, parsed) -> list[str]:
    errors = []
    if exit_code != 0:
        errors.append(f"group1 exit {exit_code}, expected 0")
    if not parsed or parsed.get("ok") is not True:
        errors.append("group1 did not report ok=true")
        return errors
    result = parsed.get("result") or {}
    offsets = {o.get("sourceId"): o for o in (result.get("clockOffsets") or [])}
    vdr = offsets.get(SRC)
    gnss = offsets.get(REF)
    if not vdr:
        errors.append("group1 missing SYN-VDR clockOffsets entry")
    else:
        got = vdr.get("offsetSeconds")
        if not isinstance(got, (int, float)) or abs(got - EXPECTED_OFFSET) > OFFSET_TOL:
            errors.append(f"group1 SYN-VDR offsetSeconds={got}, expected +{EXPECTED_OFFSET} (source − reference)")
        if got is not None and got < 0:
            errors.append(f"group1 SYN-VDR offset sign is negative, definition is source − reference (+{EXPECTED_OFFSET})")
        if vdr.get("isReference") is True:
            errors.append("group1 SYN-VDR must not be the reference")
        if vdr.get("status") != "Calibrated":
            errors.append(f"group1 SYN-VDR status={vdr.get('status')}, expected Calibrated")
        if (vdr.get("manualAnchorCount") or 0) < 1:
            errors.append("group1 SYN-VDR manualAnchorCount expected >= 1")
    if not gnss:
        errors.append("group1 missing SYN-GNSS clockOffsets entry")
    else:
        if gnss.get("isReference") is not True or gnss.get("status") != "Reference":
            errors.append(f"group1 SYN-GNSS should be Reference, got {gnss}")
        off = gnss.get("offsetSeconds")
        if not isinstance(off, (int, float)) or abs(off) > OFFSET_TOL:
            errors.append(f"group1 SYN-GNSS offsetSeconds={off}, expected 0")
    cal = result.get("calibration") or {}
    if cal.get("allCalibrated") is not True:
        errors.append(f"group1 allCalibrated={cal.get('allCalibrated')}, expected true")
    if cal.get("uncalibratedSources"):
        errors.append(f"group1 uncalibratedSources={cal.get('uncalibratedSources')}")
    stats = result.get("stats") or {}
    if (stats.get("manualAnchorCount") or 0) < 1:
        errors.append(f"group1 stats.manualAnchorCount={stats.get('manualAnchorCount')}")
    if stats.get("anchorCount") and stats.get("anchorCount") != stats.get("manualAnchorCount"):
        errors.append(
            f"group1 auto anchors may have mixed in: anchorCount={stats.get('anchorCount')} manual={stats.get('manualAnchorCount')}"
        )
    return errors


def check_group2(exit_code: int, parsed) -> list[str]:
    errors = []
    if exit_code != 0:
        errors.append(f"group2 exit {exit_code}, expected 0 with explicit uncalibrated result")
    if not parsed or parsed.get("ok") is not True:
        errors.append("group2 did not report ok=true with an uncalibrated result")
        return errors
    result = parsed.get("result") or {}
    stats = result.get("stats") or {}
    if (stats.get("manualAnchorCount") or 0) != 0:
        errors.append(f"group2 manualAnchorCount={stats.get('manualAnchorCount')}, expected 0")
    if (stats.get("anchorCount") or 0) != 0:
        errors.append(f"group2 anchorCount={stats.get('anchorCount')}, expected 0 (auto anchors must stay off)")
    finite = finite_offsets(result.get("clockOffsets"))
    if finite:
        errors.append(f"group2 must not forge a finite clock offset, got {finite}")
    cal = result.get("calibration") or {}
    if cal.get("allCalibrated") is True:
        errors.append("group2 allCalibrated is true, expected uncalibrated")
    uncal = cal.get("uncalibratedSources") or []
    for required in (REF, SRC):
        if required not in uncal:
            errors.append(f"group2 uncalibratedSources missing {required}: {uncal}")
    vdr = source_cal(result, SRC)
    if not vdr:
        errors.append("group2 missing SYN-VDR in calibration.sources")
    else:
        if vdr.get("status") != "Uncalibrated":
            errors.append(f"group2 SYN-VDR status={vdr.get('status')}, expected Uncalibrated")
        if vdr.get("offsetSeconds") is not None:
            errors.append(f"group2 SYN-VDR offsetSeconds={vdr.get('offsetSeconds')}, must not forge a value")
        desc = vdr.get("description") or ""
        if "未校准" not in desc:
            errors.append(f"group2 SYN-VDR description should state 未校准, got {desc}")
    err = cal.get("error")
    if not err or "timeline_no_reference" not in str(err):
        errors.append(f"group2 expected calibration.error with timeline_no_reference, got {err}")
    return errors


def check_group3(exit_code: int, parsed) -> list[str]:
    errors = []
    if exit_code == 0:
        errors.append("group3 exit 0, expected non-zero")
    if parsed is None:
        errors.append("group3 produced no JSON")
        return errors
    if parsed.get("ok") is True:
        errors.append("group3 reported ok=true, must not report calibration success")
    result = parsed.get("result")
    if isinstance(result, dict) and (result.get("calibration") or {}).get("allCalibrated") is True:
        errors.append("group3 result.calibration.allCalibrated is true")
    err = parsed.get("error") or {}
    if err.get("code") != "BAD_REQUEST":
        errors.append(f"group3 error.code={err.get('code')}, expected BAD_REQUEST")
    msg = err.get("message") or ""
    if "人工锚点导入失败" not in msg:
        errors.append(f"group3 message missing 人工锚点导入失败: {msg}")
    if "vdr_manual_anchor_bad_time" not in msg and "无效" not in msg:
        errors.append(f"group3 message should identify the bad anchor time: {msg}")
    if exit_code != 4:
        errors.append(f"group3 exit {exit_code}, expected 4 for RequestException")
    return errors


def write_sums(root: Path, dest: Path) -> None:
    lines = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS"):
        rel = path.relative_to(root).as_posix()
        lines.append(f"{sha256(path)}  {rel}")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="94d5e38 checkout (read-only)")
    parser.add_argument("--core-dir", type=Path, required=True, help="verified mcis-core output directory")
    parser.add_argument("--dotnet", type=Path, default=Path("/home/box/.dotnet/dotnet"))
    parser.add_argument("--out", type=Path, required=True, help="empty output directory")
    parser.add_argument("--inner-timeout", type=int, default=60, help="per-group subprocess timeout seconds")
    args = parser.parse_args()

    out = args.out
    if out.exists() and any(out.iterdir()):
        die(f"output directory must be empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    raw_dir = out / "raw"
    raw_dir.mkdir()

    source = args.source.resolve()
    head = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if head != PIN:
        die(f"source HEAD {head} is not pin {PIN}")
    align = source / "tools/mcis-core/src/AlignCommand.cs"
    require_sha(align, ALIGN_CS_SHA256, "AlignCommand.cs")

    core_dir = args.core_dir.resolve()
    dll = core_dir / "mcis-core.dll"
    require_sha(dll, CORE_DLL_SHA256, "mcis-core.dll")
    require_sha(core_dir / "mcis-core.runtimeconfig.json", CORE_RUNTIME_SHA256, "runtimeconfig")
    require_sha(core_dir / "mcis-core.deps.json", CORE_DEPS_SHA256, "deps")

    if not args.dotnet.is_file():
        die(f"dotnet missing: {args.dotnet}")
    dotnet_ver = subprocess.check_output([str(args.dotnet), "--version"], text=True).strip()
    py_ver = sys.version.replace("\n", " ")

    inventory = {
        "time": iso_now(),
        "pin": PIN,
        "sourceHead": head,
        "alignCommandSha256": ALIGN_CS_SHA256,
        "coreDir": str(core_dir),
        "artifacts": {
            "mcis-core.dll": CORE_DLL_SHA256,
            "mcis-core.runtimeconfig.json": CORE_RUNTIME_SHA256,
            "mcis-core.deps.json": CORE_DEPS_SHA256,
        },
        "dotnet": {"path": str(args.dotnet), "version": dotnet_ver},
        "python": py_ver,
        "scope": "synthetic manual-anchor core CLI only; not W4 whole package",
        "offsetDefinition": "offsetSeconds = source time − reference time; calibrated = source − offset",
        "knownSyntheticOffsetSeconds": EXPECTED_OFFSET,
        "perPointAlignedTimes": "未验",
        "perPointAlignedTimesNote": "CLI align JSON has no per-sample aligned timestamps; do not infer them from conflicts",
    }
    write_json(out / "inventory.json", inventory)

    groups = [
        ("group1-manual-calibrate", request_group1(), check_group1),
        ("group2-no-manual-no-auto", request_group2(), check_group2),
        ("group3-bad-manual-anchors", request_group3(), check_group3),
    ]
    receipt = {
        "passed": False,
        "pin": PIN,
        "coreDllSha256": CORE_DLL_SHA256,
        "groups": [],
        "firstFailure": None,
        "perPointAlignedTimes": "未验",
        "scope": inventory["scope"],
    }

    for name, request, checker in groups:
        req_path = raw_dir / f"{name}-request.json"
        write_json(req_path, request)
        exit_code = None
        parsed = None
        try:
            exit_code, parsed, _stdout = run_align(
                args.dotnet,
                dll,
                request,
                raw_dir / f"{name}-stdout.json",
                raw_dir / f"{name}-stderr.txt",
                args.inner_timeout,
            )
        except subprocess.TimeoutExpired:
            (raw_dir / f"{name}-timeout.txt").write_text("subprocess timeout\n", encoding="utf-8")
            receipt["firstFailure"] = f"{name}: subprocess timeout"
            receipt["groups"].append({"name": name, "exitCode": None, "error": "timeout"})
            write_json(out / "receipt.json", receipt)
            write_sums(out, out / "SHA256SUMS")
            die(receipt["firstFailure"])

        if parsed is not None:
            write_json(raw_dir / f"{name}-parsed.json", parsed)
        (raw_dir / f"{name}-exit.txt").write_text(str(exit_code) + "\n", encoding="utf-8")
        errors = checker(exit_code, parsed)
        entry = {
            "name": name,
            "exitCode": exit_code,
            "ok": (parsed or {}).get("ok"),
            "errors": errors,
        }
        receipt["groups"].append(entry)
        if errors:
            receipt["firstFailure"] = name + ": " + errors[0]
            write_json(out / "receipt.json", receipt)
            write_sums(out, out / "SHA256SUMS")
            die(receipt["firstFailure"])

    receipt["passed"] = True
    write_json(out / "receipt.json", receipt)
    write_sums(out, out / "SHA256SUMS")
    print(json.dumps({"passed": True, "out": str(out), "coreDllSha256": CORE_DLL_SHA256}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        die(type(exc).__name__ + ": " + str(exc))
