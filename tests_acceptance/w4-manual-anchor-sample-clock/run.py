#!/usr/bin/env python3
"""W4 sample-clock acceptance: build an isolated harness and read calibrated samples. No CLI, no install."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PIN = "94d5e38c926fda232bb987b60fa9145e4bcf01a7"
FIXTURE_SOURCE_SHA = "3c408593143ae1dddc5f065ea8549566fcd40be8"
SDK = "8.0.428"
HERE = Path(__file__).resolve().parent
PROJECT = HERE / "W4.SampleClock.csproj"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def die(msg: str, code: int = 1) -> None:
    print("W4 sample-clock acceptance stopped: " + msg, file=sys.stderr)
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


def preflight(dotnet: Path, out: Path) -> dict:
    notes = {}
    if not dotnet.is_file():
        die(f"dotnet missing: {dotnet}")
    ver = subprocess.check_output([str(dotnet), "--version"], text=True).strip()
    notes["dotnetVersion"] = ver
    notes["dotnetPath"] = str(dotnet)
    if ver != SDK:
        die(f"SDK preflight failed: got {ver}, required {SDK}")

    env = os.environ.copy()
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    env["DOTNET_NOLOGO"] = "1"
    env["DOTNET_ROOT"] = str(dotnet.parent)
    # Do not invent DOTNET_CLI_HOME; keep the real login HOME.
    loc = run([str(dotnet), "nuget", "locals", "all", "--list"], env=env)
    (out / "preflight-nuget-locals.txt").write_text(loc.stdout + loc.stderr, encoding="utf-8")
    if loc.returncode != 0:
        die("SDK/NuGet preflight failed: dotnet nuget locals all --list exit " + str(loc.returncode))
    notes["nugetLocalsExit"] = loc.returncode
    notes["nugetLocals"] = loc.stdout.strip().splitlines()

    unshare = shutil.which("unshare")
    notes["unshare"] = unshare
    if not unshare:
        die("first blocker: unshare is missing, cannot prove an offline network namespace")

    net = run([unshare, "-r", "-n", "sh", "-c", "ip -br addr; echo '---'; getent hosts nuget.org api.nuget.org || true"])
    (out / "preflight-netns.txt").write_text(net.stdout + net.stderr, encoding="utf-8")
    notes["netnsExit"] = net.returncode
    notes["netns"] = (net.stdout + net.stderr).strip()
    if "nuget.org" in net.stdout and "has address" in net.stdout:
        die("offline preflight failed: nuget.org resolved inside the isolated namespace")
    return notes


def build_offline(dotnet: Path, harness_out: Path, obj_dir: Path, logs: Path) -> dict:
    env = os.environ.copy()
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    env["DOTNET_NOLOGO"] = "1"
    env["DOTNET_ROOT"] = str(dotnet.parent)
    env["DOTNET_SKIP_FIRST_TIME_EXPERIENCE"] = "1"
    env["RestoreOffline"] = "true"

    nuget_config = obj_dir / "NuGet.Config"
    nuget_config.parent.mkdir(parents=True, exist_ok=True)
    nuget_config.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <clear />
  </packageSources>
</configuration>
""",
        encoding="utf-8",
    )

    common_props = [
        f"/p:BaseIntermediateOutputPath={obj_dir}/",
        "/p:RestoreOffline=true",
        "/p:DisableImplicitNuGetFallbackFolder=true",
        f"/p:RestoreConfigFile={nuget_config}",
        "/p:Deterministic=true",
        "/p:UseAppHost=false",
        "/p:IncludeSourceRevisionInInformationalVersion=false",
    ]
    restore_cmd = [
        "unshare", "-r", "-n",
        str(dotnet), "restore", str(PROJECT),
        "-v", "n",
        "--configfile", str(nuget_config),
        *common_props,
    ]
    restore = subprocess.run(restore_cmd, env=env, text=True, capture_output=True, cwd=str(HERE))
    (logs / "restore.stdout").write_text(restore.stdout, encoding="utf-8")
    (logs / "restore.stderr").write_text(restore.stderr, encoding="utf-8")
    (logs / "restore.exit").write_text(str(restore.returncode) + "\n", encoding="utf-8")
    (logs / "restore.cmd.txt").write_text(" ".join(restore_cmd) + "\n", encoding="utf-8")
    if restore.returncode != 0:
        die(
            "offline restore failed (no install, no external NuGet). first blocker: "
            f"dotnet restore exit {restore.returncode}. see restore.stderr"
        )

    cmd = [
        "unshare", "-r", "-n",
        str(dotnet), "build", str(PROJECT),
        "-c", "Release",
        "-o", str(harness_out),
        "-v", "n",
        "--no-restore",
        *common_props,
    ]
    proc = subprocess.run(cmd, env=env, text=True, capture_output=True, cwd=str(HERE))
    (logs / "build.stdout").write_text(proc.stdout, encoding="utf-8")
    (logs / "build.stderr").write_text(proc.stderr, encoding="utf-8")
    (logs / "build.exit").write_text(str(proc.returncode) + "\n", encoding="utf-8")
    (logs / "build.cmd.txt").write_text(" ".join(cmd) + "\n", encoding="utf-8")
    if proc.returncode != 0:
        die(
            "offline build failed (no install, no external NuGet). first blocker: "
            f"dotnet build --no-restore exit {proc.returncode}. see build.stderr"
        )
    dll = harness_out / "W4SampleClock.dll"
    if not dll.is_file():
        die("offline build produced no W4SampleClock.dll")
    return {
        "exit": proc.returncode,
        "dll": str(dll),
        "dllSha256": sha256(dll),
        "command": cmd,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="candidate checkout based on 94d5e38")
    parser.add_argument("--dotnet", type=Path, default=Path("/home/box/.dotnet/dotnet"))
    parser.add_argument("--out", type=Path, required=True, help="empty output directory")
    args = parser.parse_args()

    out = args.out
    if out.exists() and any(out.iterdir()):
        die(f"output directory must be empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    logs = out / "logs"
    logs.mkdir()
    harness_out = out / "harness-bin"
    obj_dir = out / "harness-obj"

    source = args.source.resolve()
    head = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    ancestor = run(["git", "-C", str(source), "merge-base", "--is-ancestor", PIN, "HEAD"])
    if ancestor.returncode != 0:
        die(f"source HEAD {head} does not contain pin {PIN}")
    changed = subprocess.check_output(
        ["git", "-C", str(source), "diff", "--name-only", PIN, "HEAD"], text=True
    ).splitlines()
    unexpected = [n for n in changed if not n.startswith("tests_acceptance/w4-manual-anchor-sample-clock/")]
    if unexpected:
        die("source differs from pin outside the acceptance directory: " + ", ".join(unexpected))

    hashes = json.loads((HERE / "fixtures" / "SOURCE-HASHES.json").read_text(encoding="utf-8"))
    if hashes.get("sourceSha") != FIXTURE_SOURCE_SHA or not hashes.get("allCopiedBytesMatch"):
        die("fixture SOURCE-HASHES.json does not match 3c40859")

    pre = preflight(args.dotnet, logs)
    built = build_offline(args.dotnet, harness_out, obj_dir, logs)

    # fingerprint pinned core sources that the harness compiles
    core_globs = [
        "unity/Assets/_Project/Scripts/Core/Primitives",
        "unity/Assets/_Project/Scripts/Domain/Common",
        "unity/Assets/_Project/Scripts/Domain/Models",
        "unity/Assets/_Project/Scripts/Domain/Timeline",
        "unity/Assets/_Project/Scripts/Data/Vdr",
        "unity/Assets/_Project/Scripts/Domain/Evidence",
    ]
    core_files = {}
    for rel in core_globs:
        root = source / rel
        for path in sorted(root.rglob("*.cs")):
            core_files[path.relative_to(source).as_posix()] = sha256(path)

    inventory = {
        "time": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "pin": PIN,
        "sourceHead": head,
        "fixtureSourceSha": FIXTURE_SOURCE_SHA,
        "dotnet": pre,
        "python": sys.version.replace("\n", " "),
        "harness": built,
        "coreSourceFiles": len(core_files),
        "coreSourceSha256": core_files,
        "cliUsed": False,
        "scope": "synthetic sample-clock core path only; not W4 whole package",
        "replayCommand": [
            "timeout", "--signal=TERM", "--kill-after=10s", "150s",
            "python3", "tests_acceptance/w4-manual-anchor-sample-clock/run.py",
            "--source", str(source),
            "--dotnet", str(args.dotnet),
            "--out", "<empty-out>",
        ],
    }
    write_json(out / "inventory.json", inventory)

    dll = Path(built["dll"])
    runtime = [
        str(args.dotnet), str(dll),
        "--fixtures", str(HERE / "fixtures"),
        "--out", str(out / "core-out"),
    ]
    (out / "core-out").mkdir()
    env = os.environ.copy()
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    env["DOTNET_NOLOGO"] = "1"
    env["DOTNET_ROOT"] = str(args.dotnet.parent)
    proc = subprocess.run(runtime, env=env, text=True, capture_output=True, cwd=str(dll.parent), timeout=60)
    (logs / "run.stdout").write_text(proc.stdout, encoding="utf-8")
    (logs / "run.stderr").write_text(proc.stderr, encoding="utf-8")
    (logs / "run.exit").write_text(str(proc.returncode) + "\n", encoding="utf-8")
    (logs / "run.cmd.txt").write_text(" ".join(runtime) + "\n", encoding="utf-8")

    receipt_path = out / "core-out" / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.is_file() else None
    summary = {
        "passed": bool(receipt and receipt.get("passed") and proc.returncode == 0),
        "harnessExit": proc.returncode,
        "firstFailure": None if proc.returncode == 0 else (proc.stderr.strip() or f"harness exit {proc.returncode}"),
        "cliUsed": False,
        "scope": inventory["scope"],
    }
    if receipt and receipt.get("errors"):
        summary["errors"] = receipt["errors"]
        if receipt["errors"] and not summary["firstFailure"]:
            summary["firstFailure"] = receipt["errors"][0]
    write_json(out / "summary.json", summary)
    write_sums(out, out / "SHA256SUMS")
    if not summary["passed"]:
        die(summary["firstFailure"] or "sample-clock failed")
    print(json.dumps({"passed": True, "out": str(out), "harnessDllSha256": built["dllSha256"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        die(type(exc).__name__ + ": " + str(exc))
