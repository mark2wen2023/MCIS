#!/usr/bin/env python3
"""W2.3 端到端验收（Codex 测试方，2026-11-11）：mcis-core align → 位置类冲突 deltaUnit=m + conflict.schema.json 校验。

- 直接运行已编译的 tools/mcis-core/out/mcis-core.dll（不经 mcis-core.sh，避免触发重编译覆盖实施方产物）。
  运行前检查 dll 不旧于任何被编译源码；若旧于源码则退出码 3 并提示（不自行重编）。
- 输入全部为合成数据（虚构 MARY/LILY 两路 VDR，含 RMC 本船位置与 TLL 目标位置）。
- 合同校验用 jsonschema Draft 2020-12 + FormatChecker，registry 载入 contracts/schemas/*.schema.json。
用法：/workspace/.venv-reports/bin/python tests_acceptance/W2/e2e/w23_align_e2e.py   退出码 0=全过，1=断言失败，3=dll 过期。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from functools import reduce
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[3]
DLL = ROOT / "tools" / "mcis-core" / "out" / "mcis-core.dll"
CSPROJ = ROOT / "tools" / "mcis-core" / "McisCore.csproj"
SCRIPTS = ROOT / "unity" / "Assets" / "_Project" / "Scripts"
DOTNET = Path(os.environ.get("MCIS_DOTNET", str(Path.home() / ".dotnet" / "dotnet")))
SCHEMA_DIR = ROOT / "contracts" / "schemas"
CASE = "CASE-2026-W23-E2E"
EPOCH = "2026-05-18T06:00:00Z"

FAILS: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def nmea(body: str) -> str:
    cs = reduce(lambda a, c: a ^ ord(c), body, 0)
    return f"${body}*{cs:02X}"


def fmt_lat(lat: float) -> str:
    d = int(lat)
    return f"{d:02d}{(lat - d) * 60:07.4f}"


def fmt_lon(lon: float) -> str:
    d = int(lon)
    return f"{d:03d}{(lon - d) * 60:07.4f}"


def vdr_text(own_lon: float, tgt_lon: float) -> str:
    """06:15:00–06:15:20Z 每秒一条 RMC（本船）+ TLL（目标 LILY），日志前缀给时间。"""
    lines = ["# 合成数据（虚构），W2.3 端到端验收"]
    for s in range(21):
        t = f"0615{s:02d}.00"
        prefix = f"2026-05-18T06:15:{s:02d}.000Z,"
        lines.append(prefix + nmea(f"GPRMC,{t},A,{fmt_lat(30.1)},N,{fmt_lon(own_lon)},E,12.0,45.0,180526,,,A"))
        lines.append(prefix + nmea(f"RATLL,01,{fmt_lat(30.12)},N,{fmt_lon(tgt_lon)},E,LILY,{t},T,"))
    return "\n".join(lines) + "\n"


def run_align(payload: dict) -> tuple[int, dict | None, str]:
    proc = subprocess.run(
        [str(DOTNET), str(DLL), "align"],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True, timeout=120, check=False,
        env={**os.environ, "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1",
             "DOTNET_ROOT": str(DOTNET.parent)},
    )
    out = proc.stdout.decode("utf-8", "replace").strip()
    parsed = None
    for line in reversed(out.splitlines()):
        if line.strip().startswith("{"):
            try:
                parsed = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
    return proc.returncode, parsed, proc.stderr.decode("utf-8", "replace")


def validator() -> Draft202012Validator:
    resources = []
    for p in SCHEMA_DIR.glob("*.schema.json"):
        doc = json.loads(p.read_text(encoding="utf-8"))
        resources.append((doc["$id"], Resource.from_contents(doc)))
    return Draft202012Validator(
        {"$ref": "https://mcis.local/contracts/v1/conflict.schema.json"},
        registry=Registry().with_resources(resources), format_checker=FormatChecker())


def dll_fresh() -> bool:
    if not DLL.exists():
        return False
    built = DLL.stat().st_mtime
    roots = [ROOT / "tools" / "mcis-core" / "src", CSPROJ] + [SCRIPTS / p for p in (
        "Core/Primitives", "Domain/Common", "Domain/Models", "Domain/Geo", "Domain/Cpa",
        "Domain/Colreg", "Domain/Evidence", "Domain/Timeline", "Data/Vdr")]
    for r in roots:
        files = [r] if r.is_file() else list(r.rglob("*.cs"))
        for f in files:
            if f.stat().st_mtime > built:
                print(f"STALE: {f} 新于 {DLL}")
                return False
    return True


def main() -> int:
    if not dll_fresh():
        print("mcis-core.dll 缺失或旧于源码；按测试方规则不自行重编，请实施方/架构师先构建。")
        return 3

    v = validator()
    payload = {
        "caseId": CASE, "caseEpochUtc": EPOCH, "referenceSourceId": "GNSS", "calibrate": False,
        "sources": [
            {"sourceId": "MARY-VDR", "format": "nmea", "text": vdr_text(122.060, 122.100)},
            {"sourceId": "LILY-SVDR", "format": "nmea", "text": vdr_text(122.070, 122.110)},
        ],
    }
    code, env, err = run_align(payload)
    check(code == 0 and env is not None and env.get("ok") is True, f"align 成功 exit={code} stderr={err[-300:]!r}")
    if not env or not env.get("ok"):
        return 1
    conflicts = env["result"]["conflicts"]
    print(f"INFO conflicts={len(conflicts)} kinds={sorted({c['trackKind'] for c in conflicts})}")
    for kind in ("Position", "TargetPosition"):
        hits = [c for c in conflicts if c["trackKind"] == kind]
        check(len(hits) >= 1, f"{kind} 冲突存在（{len(hits)} 条）")
        for c in hits:
            check(c.get("deltaUnit") == "m", f"{kind} {c['conflictId']} deltaUnit={c.get('deltaUnit')!r} == 'm'")
            check(isinstance(c.get("delta"), (int, float)) and 900 < c["delta"] < 1100,
                  f"{kind} {c['conflictId']} delta={c.get('delta')} m（0.01° 经度 @30.1°N ≈ 962 m）")
    for c in conflicts:
        errs = [f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}" for e in v.iter_errors(c)]
        check(not errs, f"{c['conflictId']} {c['trackKind']} 通过 conflict.schema.json {errs}")
        check(bool(c.get("deltaUnit")), f"{c['conflictId']} deltaUnit 非空")
        check(c.get("caseId") == CASE, f"{c['conflictId']} caseId={c.get('caseId')}")

    # 观察项（不计失败）：不合格 caseId 经 CLI 时的行为
    bad = dict(payload, caseId="案件 01")
    code2, env2, _ = run_align(bad)
    print(f"OBSERVE 不合格 caseId（有冲突）: exit={code2} ok={env2 and env2.get('ok')} "
          f"error={env2 and env2.get('error')}")
    quiet = dict(bad, sources=[payload["sources"][0]])
    code3, env3, _ = run_align(quiet)
    print(f"OBSERVE 不合格 caseId（无冲突）: exit={code3} ok={env3 and env3.get('ok')} "
          f"result.caseId={env3 and env3.get('result', {}).get('caseId')!r} error={env3 and env3.get('error')}")

    print(f"SUMMARY failures={len(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
