"""Exact offline .NET 8 custody interop acceptance, pure synthetic."""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
BASE = "d40e3b5fd2e208af84c84d6faf61095d0a0a89fb"
SIBLING = HERE.parent / "w17-restart-reexport"
REASON = '合成理由：含"引号"、反斜线\\与换行\n第二行'
ENV = {k: v for k, v in os.environ.items()
       if not k.startswith(("MCIS_", "PYTHON", "DOTNET_", "MSBUILD", "MSBuild", "NUGET_"))}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_fixed(path, expected):
    data = path.read_bytes()
    if digest(data) != expected:
        raise SystemExit(f"Unexpected acceptance helper bytes: {path.name}")
    return data


def source_copy(root, work, pins, scopes):
    for name, want in pins.items():
        p = PurePosixPath(name)
        if p.is_absolute() or ".." in p.parts or p.parts[0] not in scopes:
            raise SystemExit(f"Unexpected pinned path: {name}")
        src = root / p
        if src.resolve(strict=True) != src or not src.is_file():
            raise SystemExit(f"Expected a regular pinned file: {name}")
        data = src.read_bytes()
        if hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest() != want:
            raise SystemExit(f"Incorrect fixed blob: {name}")
        out = work / p
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)


def custody(dll, dotnet, env):
    with TemporaryDirectory(prefix="w17-custody-") as t:
        t = Path(t)
        spec = importlib.util.spec_from_file_location("acceptance_helpers", SIBLING / "check.py")
        common = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(common)
        with common.server(t / "store") as (port, _):
            rec, _, _ = common.populate(port)
            restricted = rec["evidenceId"]
            payload = dict(title="Synthetic verified document", source="Synthetic",
                           extractedBy="Synthetic", extractedUtc="2026-01-01T00:00:00Z",
                           category="Document", fileName="verified.txt",
                           contentBase64=base64.b64encode(b"synthetic-only verified\n").decode())
            verified = common.request(port, "POST", common.ROOT + "/evidence",
                                      code=201, body=payload)["evidenceId"]
            assert common.request(port, "POST", common.ROOT + f"/evidence/{verified}/verify")["verifyMatched"]
            update = common.request(port, "PATCH", common.ROOT + f"/evidence/{restricted}",
                                    body={"needsReview": True, "reason": REASON})
            assert update["status"] == "NeedsReview"
            entries = common.request(port, "GET", common.ROOT + f"/evidence/{restricted}/custody")
            assert [x["kind"] for x in entries] == ["Register", "Review"]
            assert entries[-1]["detail"] == REASON
            _, files = common.outer(port)  # demands HTTP 200, ZIP/no-store, 1.4
            original = files["audit/custody.jsonl"]
        lines = original.splitlines()
        assert len(lines) == 4
        assert entries[-1]["line"].encode() in lines
        control = t / "exact-custody.jsonl"
        control.write_bytes(original)
        assert control.read_bytes() == original

        def invoke(path):
            p = subprocess.run([str(dotnet), str(dll), "custody", str(path)], env=env,
                               capture_output=True, text=True, timeout=30)
            return p.returncode, json.loads(p.stdout.strip())

        rc, read = invoke(control)
        assert rc == 0 and read == {"ok": True, "events": 4, "items": 2,
                                    "status": {restricted: "NeedsReview", verified: "Verified"},
                                    "restricted": [restricted]}, (rc, read)
        # A harmless non-canonical final row: previous-link values are unchanged.
        negative = t / "noncanonical-custody.jsonl"
        assert lines[-1].endswith(b"}")
        negative.write_bytes(b"\n".join([*lines[:-1], lines[-1][:-1] + b" }"]) + b"\n")
        rc, denied = invoke(negative)
        assert rc == 1 and denied["ok"] is False and denied["code"] == "custody_chain_broken", (rc, denied)
        print(json.dumps({"archive": "1.4.0", "custodySha256": digest(original),
                          "events": read["events"], "items": read["items"],
                          "statuses": sorted(read["status"].values()),
                          "restrictedCount": len(read["restricted"]),
                          "nonCanonicalRejected": denied["code"]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="materialized exact d40e3b5 root")
    parser.add_argument("--dotnet", required=True, type=Path, help="already installed dotnet 8 executable")
    parser.add_argument("--pins-only", action="store_true", help="check source pins only, not interop")
    args = parser.parse_args()
    if not sys.flags.isolated or not sys.dont_write_bytecode or sys.flags.optimize:
        parser.error("use existing environment's Python -I -B")
    source = args.source.resolve(strict=True)
    read_fixed(SIBLING / "check.py", "bf50cc829737b597e15ac67e4166860b165b16f8090f23c6afe2f67b67064c24")
    pins = json.loads(read_fixed(SIBLING / "pins.json", "cfc31837262c05996ecdbf029dd2c898298849447a42e0f7a30e44ac4eff5468"))
    assert pins["commit"] == BASE and len(pins["gitBlobPins"]) == 190
    csharp = json.loads((HERE / "csharp-pins.json").read_text())
    assert len(csharp) == 9
    with TemporaryDirectory(prefix="w17-csharp-offline-") as t:
        t = Path(t)
        source_copy(source, t, pins["gitBlobPins"], {"service", "contracts"})
        source_copy(source, t, csharp, {"tools", "unity"})
        print(f"Verified {BASE}: 190 service/contract + 9 C# blob pins", file=sys.stderr)
        if args.pins_only:
            return
        dotnet = args.dotnet.resolve()
        if not dotnet.is_file() or not os.access(dotnet, os.X_OK):
            parser.error("No executable .NET 8 SDK specified; nothing compiled or run")
        env = {**ENV, "DOTNET_CLI_HOME": str(t / "dotnet-home"), "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
               "DOTNET_NOLOGO": "1", "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
               "DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE": "1", "NUGET_PACKAGES": str(t / "packages"),
               "DOTNET_ROOT": str(dotnet.parent)}
        ver = subprocess.check_output([str(dotnet), "--version"], cwd=t, env=env, text=True,
                                      timeout=30).strip()
        if not ver.startswith("8."):
            parser.error(f".NET 8 SDK required, found {ver}")
        rt = subprocess.check_output([str(dotnet), "--list-runtimes"], cwd=t, env=env, text=True,
                                     timeout=30)
        if not any(line.startswith("Microsoft.NETCore.App 8.") for line in rt.splitlines()):
            parser.error("Installed Microsoft.NETCore.App 8.x runtime required")
        print(f"SDK {ver}; installed runtimes:\n{rt}", file=sys.stderr)
        nuget = t / "NuGet.Config"
        nuget.write_text('<configuration><packageSources><clear /></packageSources>'
                         '<fallbackPackageFolders><clear /></fallbackPackageFolders>'
                         '<auditSources><clear /></auditSources></configuration>')
        project = t / "tools/mcis-compat/McisCompat.csproj"
        subprocess.run([str(dotnet), "restore", str(project), "--configfile", str(nuget),
                        "-p:NuGetAudit=false"], cwd=t, env=env, timeout=120, check=True)
        out = t / "build"
        subprocess.run([str(dotnet), "build", str(project), "--no-restore", "-c", "Release",
                        "-o", str(out)], cwd=t, env=env, timeout=120, check=True)
        # Start real FastAPI with the pinned service import path only.
        env.update(PYTHONPATH=str(t / "service"), PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1")
        os.environ.clear()
        os.environ.update(env)
        custody(out / "mcis-compat.dll", dotnet, env)


if __name__ == "__main__":
    main()
