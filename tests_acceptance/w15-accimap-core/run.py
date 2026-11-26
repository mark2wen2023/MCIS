#!/usr/bin/env python3
"""W15 AcciMap core acceptance: run the pinned original xunit suite (filtered, synthetic). No install, no product changes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

PIN = "2447b14076bbf39db014b8bf4a3a3b350cbf0e05"
SDK = "8.0.428"
METHOD = "原套件"
PROJECT_REL = "tests_acceptance/W15/W15.Acceptance.csproj"
ACCIMAP_REL = "unity/Assets/_Project/Scripts/Domain/Systemic/AcciMap.cs"
FILTER = (
    "FullyQualifiedName~AcciMapAcceptanceTests|"
    "FullyQualifiedName~A2_InformationFlow_UpwardAllowed_IgnoredInCycleCheck"
)
EXPECTED_TESTS = 9
HERE = Path(__file__).resolve().parent

CORE_GLOBS = [
    "unity/Assets/_Project/Scripts/Core/Primitives",
    "unity/Assets/_Project/Scripts/Domain/Common",
    "unity/Assets/_Project/Scripts/Domain/Models",
    "unity/Assets/_Project/Scripts/Domain/Evidence",
    "unity/Assets/_Project/Scripts/Domain/HumanFactors",
    "unity/Assets/_Project/Scripts/Domain/Recommendations",
    "unity/Assets/_Project/Scripts/Domain/Systemic",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def die(msg: str, code: int = 1) -> None:
    print("W15 AcciMap core acceptance stopped: " + msg, file=sys.stderr)
    raise SystemExit(code)


def run(cmd, **kwargs):
    return subprocess.run(cmd, check=False, text=True, capture_output=True, **kwargs)


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_sums(root: Path, dest: Path) -> None:
    lines = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS"):
        lines.append(f"{sha256(path)}  {path.relative_to(root).as_posix()}")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def preflight(dotnet: Path, logs: Path) -> dict:
    if not dotnet.is_file():
        die(f"dotnet missing: {dotnet}")
    ver = subprocess.check_output([str(dotnet), "--version"], text=True).strip()
    if ver != SDK:
        die(f"SDK preflight failed: got {ver}, required {SDK}")
    env = os.environ.copy()
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    env["DOTNET_NOLOGO"] = "1"
    env["DOTNET_ROOT"] = str(dotnet.parent)
    loc = run([str(dotnet), "nuget", "locals", "all", "--list"], env=env)
    (logs / "preflight-nuget-locals.txt").write_text(loc.stdout + loc.stderr, encoding="utf-8")
    if loc.returncode != 0:
        die("SDK/NuGet preflight failed: dotnet nuget locals all --list exit " + str(loc.returncode))
    unshare = shutil.which("unshare")
    if not unshare:
        die("first blocker: unshare is missing, cannot prove an offline network namespace")
    ip = shutil.which("ip") or "/usr/sbin/ip"
    # Prove isolation first with lo down; nuget.org must not resolve.
    net = run([unshare, "-r", "-n", "sh", "-c", "ip -br addr; echo '---'; (getent hosts nuget.org api.nuget.org || true)"])
    (logs / "preflight-netns.txt").write_text(net.stdout + net.stderr, encoding="utf-8")
    if "nuget.org" in net.stdout and "has address" in net.stdout:
        die("offline preflight failed: nuget.org resolved inside the isolated namespace")
    # testhost needs loopback; still no external route
    lo = run([unshare, "-r", "-n", "sh", "-c", f"{ip} link set lo up; {ip} -br addr; echo '---'; (getent hosts nuget.org api.nuget.org || true)"])
    (logs / "preflight-netns-lo-up.txt").write_text(lo.stdout + lo.stderr, encoding="utf-8")
    if "nuget.org" in lo.stdout and "has address" in lo.stdout:
        die("offline preflight failed: nuget.org resolved after lo up")
    if "127.0.0.1" not in lo.stdout and "lo" not in lo.stdout:
        die("first blocker: could not bring loopback up inside the isolated namespace (needed by testhost)")
    return {
        "dotnetVersion": ver,
        "dotnetPath": str(dotnet),
        "nugetLocalsExit": loc.returncode,
        "nugetLocals": loc.stdout.strip().splitlines(),
        "unshare": unshare,
        "netnsExit": net.returncode,
        "netns": net.stdout.strip(),
        "netnsLoUp": lo.stdout.strip(),
        "method": METHOD,
    }


def offline_env(dotnet: Path) -> dict:
    env = os.environ.copy()
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    env["DOTNET_NOLOGO"] = "1"
    env["DOTNET_ROOT"] = str(dotnet.parent)
    env["DOTNET_SKIP_FIRST_TIME_EXPERIENCE"] = "1"
    env["RestoreOffline"] = "true"
    return env


def write_nuget_config(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <clear />
  </packageSources>
</configuration>
""",
        encoding="utf-8",
    )


def parse_trx(path: Path) -> dict:
    if not path.is_file():
        return {"present": False, "tests": []}
    tree = ET.parse(path)
    root = tree.getroot()
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"
    tests = []
    for result in root.iter(f"{ns}UnitTestResult"):
        tests.append(
            {
                "name": result.attrib.get("testName"),
                "outcome": result.attrib.get("outcome"),
                "duration": result.attrib.get("duration"),
            }
        )
    counters = {}
    for el in root.iter(f"{ns}ResultSummary"):
        counters["outcome"] = el.attrib.get("outcome")
    for el in root.iter(f"{ns}Counters"):
        counters.update({k: int(v) if v.isdigit() else v for k, v in el.attrib.items()})
    return {"present": True, "counters": counters, "tests": tests, "path": str(path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="candidate checkout based on 2447b140")
    parser.add_argument("--dotnet", type=Path, default=Path("/home/box/.dotnet/dotnet"))
    parser.add_argument("--out", type=Path, required=True, help="empty output directory")
    args = parser.parse_args()

    out = args.out
    if out.exists() and any(out.iterdir()):
        die(f"output directory must be empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    logs = out / "logs"
    logs.mkdir()
    harness_bin = out / "harness-bin"
    obj_dir = out / "harness-obj"
    nuget_config = out / "NuGet.Config"
    write_nuget_config(nuget_config)

    source = args.source.resolve()
    head = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    ancestor = run(["git", "-C", str(source), "merge-base", "--is-ancestor", PIN, "HEAD"])
    if ancestor.returncode != 0:
        die(f"source HEAD {head} does not contain pin {PIN}")
    changed = subprocess.check_output(
        ["git", "-C", str(source), "diff", "--name-only", PIN, "HEAD"], text=True
    ).splitlines()
    unexpected = [n for n in changed if not n.startswith("tests_acceptance/w15-accimap-core/")]
    if unexpected:
        die("source differs from pin outside the acceptance directory: " + ", ".join(unexpected))

    project = source / PROJECT_REL
    accimap = source / ACCIMAP_REL
    if not project.is_file() or not accimap.is_file():
        die("pinned original project or AcciMap.cs missing")

    pre = preflight(args.dotnet, logs)
    env = offline_env(args.dotnet)
    common_props = [
        f"/p:BaseIntermediateOutputPath={obj_dir}/",
        "/p:RestoreOffline=true",
        f"/p:RestoreConfigFile={nuget_config}",
        "/p:Deterministic=true",
    ]

    restore_cmd = [
        "unshare", "-r", "-n",
        str(args.dotnet), "restore", str(project),
        "-v", "n",
        "--configfile", str(nuget_config),
        *common_props,
    ]
    restore = subprocess.run(restore_cmd, env=env, text=True, capture_output=True)
    (logs / "restore.stdout").write_text(restore.stdout, encoding="utf-8")
    (logs / "restore.stderr").write_text(restore.stderr, encoding="utf-8")
    (logs / "restore.exit").write_text(str(restore.returncode) + "\n", encoding="utf-8")
    (logs / "restore.cmd.txt").write_text(" ".join(restore_cmd) + "\n", encoding="utf-8")
    if restore.returncode != 0:
        die(
            "offline restore failed (no install, no external NuGet). first blocker: "
            f"dotnet restore exit {restore.returncode}. see restore.stderr"
        )

    build_cmd = [
        "unshare", "-r", "-n",
        str(args.dotnet), "build", str(project),
        "-c", "Release",
        "-o", str(harness_bin),
        "-v", "n",
        "--no-restore",
        *common_props,
    ]
    build = subprocess.run(build_cmd, env=env, text=True, capture_output=True)
    (logs / "build.stdout").write_text(build.stdout, encoding="utf-8")
    (logs / "build.stderr").write_text(build.stderr, encoding="utf-8")
    (logs / "build.exit").write_text(str(build.returncode) + "\n", encoding="utf-8")
    (logs / "build.cmd.txt").write_text(" ".join(build_cmd) + "\n", encoding="utf-8")
    if build.returncode != 0:
        die(
            "offline build failed (no install, no external NuGet). first blocker: "
            f"dotnet build --no-restore exit {build.returncode}. see build.stderr"
        )

    dll = harness_bin / "W15.Acceptance.dll"
    if not dll.is_file():
        die("offline build produced no W15.Acceptance.dll")

    core_files = {}
    for rel in CORE_GLOBS:
        root = source / rel
        if not root.is_dir():
            die("missing compile input directory: " + rel)
        for path in sorted(root.rglob("*.cs")):
            core_files[path.relative_to(source).as_posix()] = sha256(path)
    # original test sources (hashed, not modified)
    test_files = {}
    for path in sorted((source / "tests_acceptance/W15").glob("*.cs")):
        test_files[path.relative_to(source).as_posix()] = sha256(path)
    test_files[PROJECT_REL] = sha256(project)

    results_dir = out / "test-results"
    results_dir.mkdir()
    trx_name = "accimap-core.trx"
    # testhost needs lo UP; namespace remains offline (no nuget.org).
    # Quote carefully: --logger uses a semicolon that must not be a shell separator.
    test_argv = [
        str(args.dotnet),
        "test",
        str(project),
        "-c",
        "Release",
        "--no-restore",
        "--no-build",
        "--filter",
        FILTER,
        f"/p:BaseIntermediateOutputPath={obj_dir}/",
        "-o",
        str(harness_bin),
        "--logger",
        f"trx;LogFileName={trx_name}",
        "--results-directory",
        str(results_dir),
        "-v",
        "n",
    ]
    inner = (
        "ip link set lo up && "
        "echo '--- netns ---' && ip -br addr && "
        "(getent hosts nuget.org api.nuget.org || echo 'nuget.org: UNRESOLVED') && "
        "echo '--- test ---' && "
        + " ".join(shlex.quote(a) for a in test_argv)
    )
    test_cmd = ["unshare", "-r", "-n", "sh", "-c", inner]
    test = subprocess.run(test_cmd, env=env, text=True, capture_output=True, timeout=120)
    (logs / "test.stdout").write_text(test.stdout, encoding="utf-8")
    (logs / "test.stderr").write_text(test.stderr, encoding="utf-8")
    (logs / "test.exit").write_text(str(test.returncode) + "\n", encoding="utf-8")
    (logs / "test.cmd.txt").write_text(inner + "\n", encoding="utf-8")

    trx_files = sorted(results_dir.rglob("*.trx"))
    trx = trx_files[0] if trx_files else results_dir / trx_name
    parsed = parse_trx(trx)
    passed = int((parsed.get("counters") or {}).get("passed", 0) or 0)
    total = int((parsed.get("counters") or {}).get("total", 0) or 0)
    failed = int((parsed.get("counters") or {}).get("failed", 0) or 0)
    outcomes = {t["name"]: t["outcome"] for t in parsed.get("tests") or [] if t.get("name")}

    summary = {
        "passed": bool(
            test.returncode == 0
            and parsed.get("present")
            and failed == 0
            and total == EXPECTED_TESTS
            and passed == EXPECTED_TESTS
        ),
        "method": METHOD,
        "filter": FILTER,
        "harnessExit": test.returncode,
        "restoreExit": restore.returncode,
        "buildExit": build.returncode,
        "expectedTests": EXPECTED_TESTS,
        "trx": parsed,
        "cliUsed": False,
        "webUiUsed": False,
        "realCaseTestsRun": False,
        "scope": "synthetic original AcciMap xunit tests only; not W15 whole package",
        "firstFailure": None,
    }
    if not summary["passed"]:
        if test.returncode != 0:
            summary["firstFailure"] = (test.stderr or test.stdout or f"dotnet test exit {test.returncode}").strip().splitlines()[-1] if (test.stderr or test.stdout) else f"dotnet test exit {test.returncode}"
        elif total != EXPECTED_TESTS:
            summary["firstFailure"] = f"expected {EXPECTED_TESTS} tests, trx total={total} passed={passed}"
        else:
            bad = [n for n, o in outcomes.items() if o != "Passed"]
            summary["firstFailure"] = "failed or not passed: " + ", ".join(bad or ["unknown"])

    inventory = {
        "time": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "pin": PIN,
        "sourceHead": head,
        "method": METHOD,
        "dotnet": pre,
        "python": sys.version.replace("\n", " "),
        "filter": FILTER,
        "expectedTests": EXPECTED_TESTS,
        "acciMapCsSha256": sha256(accimap),
        "testAssembly": str(dll),
        "testAssemblySha256": sha256(dll),
        "coreSourceFiles": len(core_files),
        "coreSourceSha256": core_files,
        "originalTestSourceSha256": test_files,
        "restoreExit": restore.returncode,
        "buildExit": build.returncode,
        "testExit": test.returncode,
        "cliUsed": False,
        "webUiUsed": False,
        "scope": summary["scope"],
        "replayCommand": [
            "timeout", "--signal=TERM", "--kill-after=10s", "150s",
            "python3", "tests_acceptance/w15-accimap-core/run.py",
            "--source", str(source),
            "--dotnet", str(args.dotnet),
            "--out", "<empty-out>",
        ],
    }
    write_json(out / "inventory.json", inventory)
    write_json(out / "summary.json", summary)
    write_sums(out, out / "SHA256SUMS")
    if not summary["passed"]:
        die(summary["firstFailure"] or "AcciMap core tests failed")
    print(json.dumps({
        "passed": True,
        "method": METHOD,
        "tests": passed,
        "out": str(out),
        "acciMapCsSha256": inventory["acciMapCsSha256"],
        "testAssemblySha256": inventory["testAssemblySha256"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        die(type(exc).__name__ + ": " + str(exc))
