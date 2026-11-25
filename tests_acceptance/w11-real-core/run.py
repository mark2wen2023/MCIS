"""Offline exact-source W11 actual core gate. Python prerequisites already installed."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory

BASE = "d9187fef1f979866ac4d8ce2064d1ac92f34bb36"
SDK = "8.0.428"
PILOT = "b40a6cacf91ba0d8b297377d31162e404e468e8d"
PILOT_PINS = {
    "SOURCES": "a51a6566753fdbff1f2eba0028b485f21ac2ee25",
    "check.py": "0f77b3626fefe20fd0fed7b3b6ea72f928610a56",
    "pilot.py": "78c44747d6709ec5142aa413f167866c1f7d70f4",
    "run.py": "d09ac4bbc605eb77ac4049357f6f286f92d909dd",
}
HERE = Path(__file__).resolve().parent
TOOL = "tools/mcis-ecfc/"
RECIPE = TOOL + "build.py"
LAUNCHER = TOOL + "mcis-ecfc.sh"
BOOT = """
import runpy, sys
from pathlib import Path
root, script, fixture, marker = map(Path, sys.argv[1:])
sys.path[:0] = [str(root / 'service'), str(fixture)]
sys.argv = [str(script), str(root / marker), str(root)]
runpy.run_path(str(script), run_name='__main__')
"""

def digest(data):
    return hashlib.sha256(data).hexdigest()

def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def sha_file(path):
    return digest(path.read_bytes())

def stage(root, item, data, mode):
    target = root / item
    if target.exists():
        raise ValueError(f"Duplicate fixed input: {item}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    target.chmod(mode)

def core_environment(tmp, sdk, initialized_home):
    feed = tmp / "empty-feed"
    feed.mkdir()
    env = {k:v for k,v in os.environ.items() if k in ("PATH","LANG","LC_ALL","LD_LIBRARY_PATH")}
    env.update(MCIS_DOTNET=str(sdk), TMPDIR=str(tmp),
               DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_NOLOGO="1",
               RestoreSources=str(feed), NuGetAudit="false")
    if initialized_home:
        interfaces = {line.split(":", 1)[0].strip()
                      for line in Path("/proc/net/dev").read_text().splitlines()[2:] if ":" in line}
        if interfaces != {"lo"}:
            raise RuntimeError("Initialized-home mode requires Linux with only loopback")
        current = Path(os.environ.get("HOME", ""))
        if not current.is_absolute() or not current.is_dir():
            raise RuntimeError("Initialized-home mode requires the existing normal user HOME")
        env.update(HOME=str(current), DOTNET_ROOT=str(sdk.parent),
                   NUGET_PACKAGES=str(tmp / "packages"),
                   NUGET_HTTP_CACHE_PATH=str(tmp / "http-cache"),
                   NUGET_PLUGINS_CACHE_PATH=str(tmp / "plugins-cache"),
                   RestoreFallbackFolders="")
    else:
        cli_home = tmp / "cli-home"
        cli_home.mkdir()
        env.update(HOME=str(cli_home), DOTNET_CLI_HOME=str(cli_home))
    return env

def main():
    if not __debug__:
        raise SystemExit("Assertions must be enabled")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pilot", type=Path, required=True, help="W11 pinned local candidate checkout, root")
    p.add_argument("--source-dir", type=Path, action="append", required=True,
                   help="Local export of exact original blobs. Repeat for disjoint exports.")
    p.add_argument("--dotnet", type=Path, help="Absolute executable of preinstalled SDK 8.0.428")
    p.add_argument("--verify-only", action="store_true")
    p.add_argument("--initialized-home", action="store_true",
                   help="Explicitly reuse the normal already-initialized user HOME, only in loopback isolation")
    a = p.parse_args()
    if not a.verify_only and (not a.dotnet or not a.dotnet.is_absolute()):
        p.error("--dotnet requires an absolute existing executable; no automatic installation")
    a.source_dir = [x.resolve() for x in a.source_dir]
    prior = a.pilot.resolve() / "tests_acceptance/w11-excerpt-binding-local"

    with TemporaryDirectory(prefix="mcis-w11-real-core-") as tmp:
        tmp = Path(tmp)
        source = prior
        prior = tmp / "pilot-pinned"
        prior.mkdir()
        for name, pin in PILOT_PINS.items():
            file = source / name
            if not file.is_file():
                p.error(f"Missing pilot helper: {name}")
            data = file.read_bytes()
            if git_blob(data) != pin:
                p.error(f"Pilot {PILOT[:7]} helper mismatch: {name}")
            stage(prior, name, data, 0o644)
        inherited = runpy.run_path(str(prior / "run.py"))
        original = inherited["CORE_MARKER"]
        root = tmp / "fixed"
        root.mkdir()
        pinned = set()
        for line in (prior / "SOURCES").read_text().splitlines():
            item, data = inherited["get_blob"](line, a, p)
            stage(root, item, data, 0o644)
            pinned.add(item.as_posix())
        if len(pinned) != 186 or original not in pinned:
            p.error("Expected complete 186-file W11 original manifest")
        fixed = {}
        for line in (HERE / "CORE_SOURCES").read_text().splitlines():
            mode, blob, item = line.split(" ")
            if not re.fullmatch(r"(tools/mcis-ecfc|unity/Assets/_Project/Scripts)/[\w./-]+", item) or ".." in Path(item).parts:
                p.error(f"Invalid core pin path: {item}")
            loc = next((x / item for x in a.source_dir if (x / item).is_file()), None)
            if loc is None:
                p.error(f"Missing fixed core blob from local export: {item}")
            data = loc.read_bytes()
            got = git_blob(data)
            if got != blob or mode != ("100755" if item == LAUNCHER else "100644"):
                p.error(f"Core blob or mode mismatch: {item}")
            chmod = int(mode, 8) & 0o777
            stage(root, item, data, chmod)
            if stat.S_IMODE((root/item).stat().st_mode) != chmod:
                p.error(f"Staged mode mismatch: {item}")
            fixed[item] = digest(data)
        recipe = ast.parse((root / RECIPE).read_bytes())
        declared = next(ast.literal_eval(n.value) for n in recipe.body
                        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "INPUTS" for t in n.targets))
        if len(declared) != 7 or set(fixed) != {*declared, RECIPE, LAUNCHER}:
            p.error("Core input set differs from declared build recipe")
        print(f"W11 verified {len(pinned)} W11 originals + {len(PILOT_PINS)} pilot helpers + {len(fixed)} exact core blobs/modes ({BASE[:7]}); no fetch", flush=True)
        if a.verify_only:
            return 0
        if not a.dotnet.is_file() or not os.access(a.dotnet, os.X_OK):
            print("BLOCKED: preinstalled SDK executable not found; smoke, preview, save and reopen did not run", file=sys.stderr)
            return 2
        env = core_environment(tmp, a.dotnet, a.initialized_home)
        def invoke(label, command, **options):
            result = subprocess.run(command,cwd=root,env=env,check=False,timeout=120,**options)
            print(f"{label} exit={result.returncode}", flush=True)
            if result.returncode:
                raise SystemExit(result.returncode)
            return result
        version = invoke("SDK version", [a.dotnet,"--version"],stdout=subprocess.PIPE).stdout.decode().strip()
        if version != SDK:
            p.error(f"Wrong SDK; require {SDK}")
        invoke("NuGet local directories check", [a.dotnet,"nuget","locals","all","--list"],stdout=subprocess.DEVNULL)
        smoke = invoke("Core smoke", [root / LAUNCHER],stdout=subprocess.PIPE,input=json.dumps(
            {"action":"validate","draft":{"scope":"Synthetic local smoke","nodes":[],"edges":[]}}).encode())
        payload = json.loads(smoke.stdout)
        assert payload["ok"] is True and payload["result"]["coreVersion"] == "mcis-ecfc-draft/1"
        assert payload["result"]["nodes"] == payload["result"]["edges"] == []
        out = root / TOOL / "out"
        manifest = json.loads((out / "build-manifest.json").read_text())
        assert manifest["sdk"] == SDK and manifest["contract"] == "mcis-ecfc-build/1"
        assert manifest["recipeSha256"] == fixed[RECIPE]
        assert manifest["inputs"] == {p: fixed[p] for p in declared}
        assert all(sha_file(root/p) == h for p,h in fixed.items())
        artifacts = manifest["artifacts"]
        assert "mcis-ecfc.dll" in artifacts
        for name, sha in artifacts.items():
            assert Path(name).name == name and sha_file(out/name) == sha
        print("Verified original SDK/core smoke and source-artifact manifest", flush=True)
        invoke("Real W11 core business flow", [sys.executable,"-I","-B","-c",BOOT,str(root),
            str(HERE/"workflow.py"),str(prior),original])
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
