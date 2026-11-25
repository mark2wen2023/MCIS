"""Isolated, fixed-source positive Bow-tie acceptance. No browser claims."""
import argparse
import ast
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import select
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

HERE = Path(__file__).resolve().parent
PINS = json.loads((HERE / "pins.json").read_text())
TOOL = Path("tools/mcis-bowtie")
CLI = TOOL / "mcis-bowtie.sh"
RECIPE = TOOL / "build.py"
TEST = Path("tests_acceptance/W153/test_cli.py")
SDK = "8.0.428"


def blob(data):
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_rel(path):
    p = Path(path)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"Unsafe pinned path: {path}")
    return p


def read_fixed(path, locations, sha):
    rel = safe_rel(path)
    for root in locations:
        p = root / rel
        if p.is_file():
            data = p.read_bytes()
            if blob(data) != sha:
                raise ValueError(f"Git blob mismatch: {rel}")
            return data
    raise FileNotFoundError(f"Missing fixed file: {rel}")


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage(root, candidate, sources):
    helper_dir = root / "acceptance-helpers"
    helper_dir.mkdir()
    for path, pin in PINS["negative_helpers"].items():
        out = helper_dir / Path(path).name
        out.write_bytes(read_fixed(path, [candidate], pin))
    base_pins = json.loads((helper_dir / "pins.json").read_text())
    assert base_pins["product"] == PINS["product"] and len(base_pins["paths"]) == 339
    core = PINS["core"]
    assert len(core) == 15
    for path, (pin, _) in core.items():
        assert path not in base_pins["paths"] or base_pins["paths"][path] == pin, path
    combined = {**base_pins["paths"], **{p: v[0] for p, v in core.items()}}
    for path, pin in combined.items():
        rel = safe_rel(path)
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(read_fixed(path, sources, pin))
        mode = core[path][1] if path in core else "100644"
        assert mode in ("100644", "100755")
        dst.chmod(int(mode, 8) & 0o777)
        assert blob(dst.read_bytes()) == pin
        assert dst.stat().st_mode & 0o777 == int(mode, 8) & 0o777
    body = ast.parse((root / RECIPE).read_text())
    assigns = {x.targets[0].id: ast.literal_eval(x.value) for x in body.body
               if isinstance(x, ast.Assign) and len(x.targets) == 1
               and isinstance(x.targets[0], ast.Name) and x.targets[0].id in {"INPUTS", "SDK"}}
    assert assigns["SDK"] == SDK and len(assigns["INPUTS"]) == 12
    assert set(assigns["INPUTS"]) | {str(CLI), str(RECIPE), str(TEST)} == set(core)
    assert not any(tag in (root / TOOL / "McisBowtie.csproj").read_text()
                   for tag in ("<PackageReference", "<ProjectReference"))
    return helper_dir, assigns["INPUTS"], len(combined)


def offline_env(work, sdk):
    interfaces = {s.split(":", 1)[0].strip()
                  for s in Path("/proc/net/dev").read_text().splitlines()[2:] if ":" in s}
    if interfaces != {"lo"}:
        raise RuntimeError("A Linux network namespace with only loopback is required for real execution")
    feed = work / "empty-feed"
    feed.mkdir()
    env = {k: v for k, v in os.environ.items() if k in {"HOME", "PATH", "LANG", "LC_ALL", "LD_LIBRARY_PATH"}}
    env.update(MCIS_DOTNET=str(sdk), DOTNET_ROOT=str(sdk.parent),
               DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_NOLOGO="1", NuGetAudit="false",
               RestoreSources=str(feed), RestoreFallbackFolders="", NUGET_PACKAGES=str(work / "packages"),
               PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    return env


def verify_manifest(root, inputs):
    out = root / TOOL / "out"
    m = json.loads((out / "build-manifest.json").read_text())
    assert m["contract"] == "mcis-bowtie-build/1" and m["sdk"] == SDK
    assert m["recipeSha256"] == digest(root / RECIPE)
    assert m["inputs"] == {p: digest(root / p) for p in inputs}
    artifacts = m["artifacts"]
    assert {"mcis-bowtie.dll", "mcis-bowtie.deps.json", "mcis-bowtie.runtimeconfig.json"} <= set(artifacts)
    for name, sha in artifacts.items():
        assert Path(name).name == name and digest(out / name) == sha
    return m


@contextmanager
def host(python, work, root, db, evidence, env, helper, suffix):
    with (evidence / f"host-{suffix}.log").open("w") as log:
        proc = subprocess.Popen([str(python), str(HERE / "host.py"), str(db)], cwd=work,
                                env={**env, "PYTHONPATH": str(root / "service")}, text=True,
                                stdout=subprocess.PIPE, stderr=log)
        try:
            line = proc.stdout.readline().strip() if select.select([proc.stdout], [], [], 20)[0] else ""
            assert re.fullmatch(r"W15_CORE_PORT=[1-9][0-9]{3,4}", line), "Local service failed to bind"
            origin = "http://127.0.0.1:" + line.split("=")[1]
            for _ in range(100):
                try:
                    helper.send(origin, "GET", "/api/v1/health", 200)
                    break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError("Local service not healthy")
            yield origin
        finally:
            if proc.poll() is None:
                proc.terminate()
            try:
                proc.wait(8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            proc.stdout.close()


def run_http(args, work, root, model, env, helper):
    db = work / "store"
    db.mkdir()
    with host(args.host_python, work, root, db, args.evidence, env, helper, "first") as origin:
        helper.setup(origin)
        before = helper.dump(db)
        path = f"/api/v1/cases/{helper.CASE_A}/systemic/bowtie:preview"
        for kind in ("valid", "unknown"):
            payload = model()
            if kind == "unknown":
                payload["edges"].append({"fromId": "GHOST", "toId": "TOP"})
            result = helper.send(origin, "POST", path, 200,
                                 {"model": payload, "sourceEvidenceIds": ["EV-001"]})
            assert result["persisted"] is False and result["assessment"] == "hypothesis-structure-only"
            assert result["sourceBinding"] == "registered-metadata-only"
            assert result["sources"][0]["title"] == helper.TITLES[helper.CASE_A]
            r = result["result"]
            assert "effective" not in r and "riskScore" not in r
            if kind == "valid":
                assert r["structureValid"] is True and (r["nodeCount"], r["edgeCount"]) == (5, 4)
                assert not r["constructionErrors"] and not r["validationIssues"]
            else:
                assert r["structureValid"] is False and not r["validationIssues"]
                assert any(x["code"] == "sys_unknown_node" for x in r["constructionErrors"])
            (args.evidence / f"{kind}-preview.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    with host(args.host_python, work, root, db, args.evidence, env, helper, "reopened") as origin:
        for case in helper.TITLES:
            helper.source(origin, case)
    assert before == helper.dump(db)
    print("W15 actual service + original C# + SQLite restart: both paths pass without mutation", flush=True)


def main():
    if not __debug__:
        raise RuntimeError("Run with assertions enabled")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", type=Path, required=True, help="Pinned candidate checkout containing negative helpers")
    p.add_argument("--source-dir", type=Path, action="append", required=True)
    p.add_argument("--dotnet", type=Path)
    p.add_argument("--host-python", type=Path)
    p.add_argument("--evidence", type=Path)
    p.add_argument("--verify-only", action="store_true")
    a = p.parse_args()
    if not a.verify_only and (not all([a.dotnet, a.host_python, a.evidence])
                              or not all(x.is_absolute() for x in [a.dotnet, a.host_python, a.evidence])):
        p.error("Full gate needs absolute --dotnet, --host-python, and new --evidence")
    with TemporaryDirectory(prefix="mcis-w15-real-core-") as tmp:
        work = Path(tmp)
        root = work / "fixed"
        root.mkdir()
        h, inputs, n = stage(root, a.candidate, a.source_dir)
        print(f"W15 pinned {n} exact product files; 12 declared original build inputs, original CLI test and 3 unchanged negative helpers", flush=True)
        if a.verify_only:
            return 0
        if not a.dotnet.is_file() or not os.access(a.dotnet, os.X_OK):
            print("BLOCKED: no executable preinstalled .NET SDK; CLI, manifest and HTTP not run", file=sys.stderr)
            return 2
        env = offline_env(work, a.dotnet)
        a.evidence.mkdir()
        version = subprocess.check_output([a.dotnet, "--version"], cwd=root, env=env, text=True, timeout=10).strip()
        assert version == SDK
        print(f"Found preinstalled .NET {version}; starting original W153 CLI checks", flush=True)
        # Original CLI test invokes unmodified launcher and compiler. Do not replace it on failure.
        with (a.evidence / "cli.log").open("w") as log:
            subprocess.run([a.host_python, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            str(root / TEST)], cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT,
                           timeout=600, check=True)
        manifest = verify_manifest(root, inputs)
        print("Original W153 CLI and produced artifact manifest verified", flush=True)
        (a.evidence / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        fixture = load("fixed_w153_cli", root / TEST)
        helper = load("fixed_w15_negative_helpers", h / "run.py")
        run_http(a, work, root, fixture.model, env, helper)
        assert verify_manifest(root, inputs) == manifest
        receipt = {"product": PINS["product"], "fixedSourceCount": n,
                   "sdk": version, "syntheticOnly": True, "browserVerified": False,
                   "originalCliPassed": True, "httpPositivePassed": True,
                   "httpUnknownEndpointPassed": True, "sqliteUnchangedAfterReopen": True}
        (a.evidence / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
