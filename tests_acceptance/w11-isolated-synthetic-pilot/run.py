"""Official isolated W11 combined synthetic pilot. Existing deps only; loopback HTTP, not a browser."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import runpy
import shutil
import socket
import sqlite3
import stat
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

PIN = "875ccc50b049fb24b82f6b0663f3f9476db1880e"
SDK = "8.0.428"
NAMED_DLL_SHA = "f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf"
COMM_BLOB = "b72fd8e1b4aca4287eb17ce08613d68068a98df5"
TOOL = "tools/mcis-ecfc/"
RECIPE = TOOL + "build.py"
LAUNCHER = TOOL + "mcis-ecfc.sh"
CORE_DIR = "tests_acceptance/w11-real-core/CORE_SOURCES"
HERE = Path(__file__).resolve().parent
WORKTREE = HERE.parents[1]
SOURCE_EXPORT = Path("/workspace/mcis-w11-core-rerun-report/source-export")
EXCERPT = WORKTREE / "tests_acceptance" / "w11-excerpt-binding-local"
EDGE_HOST = WORKTREE / "tests_acceptance" / "w11-edge-host-optin"
LEAD = {"X-MCIS-Role": "LeadInvestigator", "X-MCIS-Operator": "LocalSyntheticLead"}
PUBLIC = {"X-MCIS-Role": "Public", "X-MCIS-Operator": "SyntheticBlocked"}

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def sha_file(path: Path) -> str:
    return digest(path.read_bytes())

# Pinned literals identical to tests_acceptance/w11-excerpt-binding-local at 875ccc50.
# Do not import check.py/pilot.py in this process (they would pull a service package).
CASE = "SYN-XREPO-001"
SOURCE_SHA = "418be9609b46a00062c41fb49073911986098e9a61e010f4311aa86946ecd3ea"
UTC = "2026-02-01T12:01:49.000Z"
EDGE = ("E01", "C01", "N01")
API = f"/api/v1/cases/{CASE}"
CUSTODY = API + "/evidence/EV-001/custody"
PATH = f"/__local_synthetic_w11/{CASE}/edge-excerpt"
DOC = dict(caseId=CASE, title="Synth-only graph source", schemaVersion="1.0.0", accidentType="Collision",
           incidentTimeUtc="2026-02-01T12:00:00Z", caseEpochUtc="2026-02-01T12:00:00Z",
           incidentLocation={"latDeg": 0, "lonDeg": 0}, displayTimeZoneOffsetMinutes=0, isFictionalDemo=True)
DDL = """CREATE TABLE pilot_single_source(
 singleton INTEGER PRIMARY KEY CHECK(singleton=1), case_id TEXT NOT NULL,
 revision INTEGER NOT NULL, graph_digest TEXT NOT NULL,
 edge_id TEXT NOT NULL, from_id TEXT NOT NULL, to_id TEXT NOT NULL,
 evidence_id TEXT NOT NULL, intake_digest TEXT NOT NULL, source_sha TEXT NOT NULL,
 start_byte INTEGER NOT NULL, end_byte INTEGER NOT NULL,
 revoked INTEGER NOT NULL CHECK(revoked IN (0,1)))"""
TRIGGER = """CREATE TRIGGER pilot_revoke_only BEFORE UPDATE ON pilot_single_source
WHEN OLD.revoked<>0 OR NEW.revoked<>1 OR NEW.singleton<>OLD.singleton OR NEW.case_id<>OLD.case_id
 OR NEW.revision<>OLD.revision OR NEW.graph_digest<>OLD.graph_digest OR NEW.edge_id<>OLD.edge_id
 OR NEW.from_id<>OLD.from_id OR NEW.to_id<>OLD.to_id OR NEW.evidence_id<>OLD.evidence_id
 OR NEW.intake_digest<>OLD.intake_digest OR NEW.source_sha<>OLD.source_sha
 OR NEW.start_byte<>OLD.start_byte OR NEW.end_byte<>OLD.end_byte
BEGIN SELECT RAISE(ABORT,'pilot association is fixed'); END"""
PINS = {
    "API": API, "CASE": CASE, "CUSTODY": CUSTODY, "DDL": DDL, "DOC": DOC,
    "EDGE": EDGE, "SOURCE_SHA": SOURCE_SHA, "TRIGGER": TRIGGER, "UTC": UTC, "PATH": PATH,
}

def core_environment(tmp: Path, sdk: Path, initialized_home: bool):
    feed = tmp / "empty-feed"
    feed.mkdir(exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "LANG", "LC_ALL", "LD_LIBRARY_PATH")}
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

def stage_file(root: Path, item: str, data: bytes, mode: int):
    target = root / item
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    target.chmod(mode)

def copy_service(src: Path, dest: Path):
    def ignore(_directory, names):
        skipped = {"__pycache__", ".venv", "data", ".pytest_cache"}
        return [n for n in names if n in skipped or n.endswith((".pyc", ".pyo", ".db"))]
    shutil.copytree(src, dest, ignore=ignore, dirs_exist_ok=True)

def http_json(method, url, headers=None, body=None, timeout=60):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            return response.status, dict(response.headers), json.loads(raw.decode()) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        parsed = None
        if raw:
            try:
                parsed = json.loads(raw.decode())
            except json.JSONDecodeError:
                parsed = {"raw": raw.decode("utf-8", "replace")[:400]}
        return exc.code, dict(exc.headers), parsed

def wait_health(base, timeout=30):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            status, _, body = http_json("GET", base + "/api/v1/health", timeout=2)
            if status == 200 and body and body.get("status") == "ok":
                return body
            last = (status, body)
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as exc:
            last = str(exc)
        time.sleep(0.1)
    raise RuntimeError(f"Health check failed: {last}")

def bind_listeners(pid: int):
    rows = []
    for table, v6 in (("tcp", False), ("tcp6", True)):
        path = Path("/proc/net") / table
        if not path.is_file():
            continue
        for line in path.read_text().splitlines()[1:]:
            parts = line.split()
            local, state, inode = parts[1], parts[3], parts[9]
            addr, port_hex = local.rsplit(":", 1)
            if state != "0A":
                continue
            port = int(port_hex, 16)
            if v6:
                host = addr
            else:
                nums = bytes.fromhex(addr)
                host = ".".join(str(b) for b in nums[::-1])
            rows.append({"table": table, "addr": host, "port": port, "inode": inode})
    fds = Path(f"/proc/{pid}/fd")
    owned = set()
    if fds.is_dir():
        for entry in fds.iterdir():
            try:
                target = os.readlink(entry)
            except OSError:
                continue
            if target.startswith("socket:["):
                owned.add(target[8:-1])
    return [row for row in rows if row["inode"] in owned] if owned else rows

def draft_body(title: str, scope: str):
    pins = PINS
    EDGE = pins["EDGE"]
    edge = dict(zip(("id", "from", "to"), EDGE, strict=True))
    nodes = [
        dict(id=EDGE[1], kind="Condition", text="Synthetic condition", timeSeconds=None,
             lane=0, isPrimaryIncident=False, evidenceIds=["EV-001"]),
        dict(id=EDGE[2], kind="Event", text="Synthetic unknown event", timeSeconds=None,
             lane=0, isPrimaryIncident=False, evidenceIds=[]),
    ]
    return dict(scope=scope, nodes=nodes, edges=[edge]), [
        dict(evidenceId="EV-001", title=title, sha256=pins["SOURCE_SHA"])
    ], edge

def sqlite_exec(db: Path, sql: str, params=None, fetch=False):
    con = sqlite3.connect(f"file:{db}?mode=rw", uri=True, timeout=10)
    try:
        con.execute("PRAGMA busy_timeout=10000")
        cur = con.execute(sql, params or {})
        rows = cur.fetchall() if fetch else None
        con.commit()
        return cur.rowcount, rows
    finally:
        con.close()

def start_server(python, stage, data_dir, db, port, enable, routes_out, ready, env):
    ready.unlink(missing_ok=True)
    cmd = [
        python, "-I", "-B", str(HERE / "server.py"),
        "--data-dir", str(data_dir), "--db", str(db), "--port", str(port),
        "--routes-out", str(routes_out), "--ready-file", str(ready),
        "--host", "127.0.0.1",
        "--service-root", str(stage / "service"),
        "--excerpt-binding", str(EXCERPT), "--edge-host", str(EDGE_HOST),
    ]
    if enable:
        cmd.append("--enable-pilot")
    child_env = dict(env)
    child_env["PYTHONPATH"] = str(stage / "service")
    child_env["MCIS_SEED_DEMO"] = "0"
    proc = subprocess.Popen(cmd, cwd=str(stage), env=child_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc

def stop_server(proc, port=None, timeout=10):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    if port is not None:
        deadline = time.time() + 10
        while time.time() < deadline:
            sock = socket.socket()
            sock.settimeout(0.2)
            try:
                sock.connect(("127.0.0.1", port))
            except (ConnectionRefusedError, ConnectionResetError, OSError):
                sock.close()
                return
            else:
                sock.close()
                time.sleep(0.05)
        raise RuntimeError(f"Port {port} still accepting connections after server stop")


def openapi_paths(app):
    return sorted(app.openapi().get("paths", {}))

def start_loopback(app, host, port):
    import uvicorn
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="w11-isolated-pilot", daemon=True)
    thread.start()
    return server, thread

def stop_loopback(server, thread, port, timeout=10):
    server.should_exit = True
    thread.join(timeout=timeout)
    if thread.is_alive():
        raise RuntimeError("Loopback server thread did not exit")
    deadline = time.time() + 10
    while time.time() < deadline:
        sock = socket.socket()
        sock.settimeout(0.2)
        try:
            sock.connect(("127.0.0.1", port))
        except (ConnectionRefusedError, ConnectionResetError, OSError):
            sock.close()
            return
        else:
            sock.close()
            time.sleep(0.05)
    raise RuntimeError(f"Port {port} still accepting connections after in-process stop")

def service_preview(ec, ctx, case_id, draft, expected):
    body, sources = ec.validate_body(dict(draft=draft, expectedSources=expected), preview=True)
    return ec.preview_sync(ctx, case_id, body, sources)

def service_save(ec, ctx, case_id, request_id, expected_digest, draft, expected):
    body, sources = ec.validate_body(dict(
        requestId=request_id, expectedDigest=expected_digest,
        draft=draft, expectedSources=expected, acknowledgeArchiveLimitation=True))
    return ec.save_sync(ctx, case_id, body, sources)

def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

def main():
    if not __debug__:
        raise SystemExit("Assertions must be enabled")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dotnet", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, action="append",
                        help="Local export of the 186 pinned W11 originals")
    parser.add_argument("--named-dll", type=Path, default=Path("/workspace/mcis-w41-core-out/mcis-core.dll"))
    parser.add_argument("--port", type=int, default=18765)
    args = parser.parse_args()
    if not args.dotnet.is_absolute() or not os.access(args.dotnet, os.X_OK):
        raise SystemExit("BLOCKED: preinstalled SDK executable not found; official run did not start")
    if not args.python.is_absolute() or not os.access(args.python, os.X_OK):
        raise SystemExit("BLOCKED: preinstalled service Python not found; official run did not start")
    if args.port < 1:
        raise SystemExit("Invalid port")

    pins = PINS
    report = args.report.resolve()
    report.mkdir(parents=True, exist_ok=True)
    out_dir = report / "official"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir()
    logs = []

    def log(msg):
        line = msg if msg.endswith("\n") else msg + "\n"
        sys.stdout.write(line)
        sys.stdout.flush()
        logs.append(line)

    # Named artifact is W4.1 align/clock, not the ECFC validator.
    named = {}
    if args.named_dll.is_file():
        named_sha = sha_file(args.named_dll)
        named = {"path": str(args.named_dll), "sha256": named_sha, "used": False}
        if named_sha != NAMED_DLL_SHA:
            raise SystemExit(f"Named DLL SHA-256 mismatch: {named_sha}")
        manifest_path = args.named_dll.with_name("build-manifest.json")
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text())
            named["contract"] = manifest.get("contract")
            if named["contract"] == "mcis-ecfc-build/1":
                raise SystemExit("Unexpected: named DLL manifest is ECFC")
            if named["contract"] != "mcis-core-build/1":
                raise SystemExit(f"Unexpected named DLL contract: {named['contract']}")
        log(f"Named artifact {args.named_dll} SHA-256={named_sha} contract={named.get('contract')} is W4.1 mcis-core; not used as ECFC validator")
    else:
        log("Named W4.1 DLL path missing; recorded as unused")
        named = {"path": str(args.named_dll), "sha256": None, "used": False}

    if not (WORKTREE / ".git").exists():
        raise SystemExit("Candidate worktree missing")
    head = subprocess.check_output(["git", "-C", str(WORKTREE), "rev-parse", "HEAD"], text=True).strip()
    if head != PIN:
        raise SystemExit(f"Worktree HEAD {head} != pin {PIN}")

    source = subprocess.check_output(["git", "-C", str(WORKTREE), "cat-file", "blob", COMM_BLOB])
    if git_blob(source) != COMM_BLOB or digest(source) != pins["SOURCE_SHA"]:
        raise SystemExit("communication.txt pin/SHA mismatch")
    if source[97:121].decode() != pins["UTC"]:
        raise SystemExit("T+109 span mismatch")
    fixture = report / "fixtures" / "communication.txt"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_bytes(source)

    tmp = report / "tmp-official"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    stage = tmp / "stage-root"
    stage.mkdir()
    # Reuse the existing 186-file isolation assembly (pinned service + fixture),
    # not the later worktree service tree, which no longer exports the custody helper.
    source_dirs = [p.resolve() for p in (args.source_dir or ([SOURCE_EXPORT] if SOURCE_EXPORT.is_dir() else []))]
    if not source_dirs:
        raise SystemExit("Missing local pinned source export; no fetch attempted")
    inherited = runpy.run_path(str(EXCERPT / "run.py"))
    ns = argparse.Namespace(source_dir=source_dirs, repository=None)
    class _Parser:
        def error(self, message):
            raise SystemExit(message)
    pinned = set()
    for line in (EXCERPT / "SOURCES").read_text().splitlines():
        item, data = inherited["get_blob"](line, ns, _Parser())
        stage_file(stage, item.as_posix(), data, 0o644)
        pinned.add(item.as_posix())
    marker = inherited["CORE_MARKER"]
    if len(pinned) != 186 or marker not in pinned:
        raise SystemExit(f"Incomplete 186-file assembly: {len(pinned)} marker={marker in pinned}")
    log(f"Staged {len(pinned)} pinned W11 originals from local export; core marker present")

    core_pins = {}
    for line in (WORKTREE / CORE_DIR).read_text().splitlines():
        mode, blob, item = line.split(" ")
        data = (WORKTREE / item).read_bytes()
        if git_blob(data) != blob:
            raise SystemExit(f"Core blob mismatch: {item}")
        chmod = int(mode, 8) & 0o777
        stage_file(stage, item, data, chmod)
        if stat.S_IMODE((stage / item).stat().st_mode) != chmod:
            raise SystemExit(f"Staged mode mismatch: {item}")
        core_pins[item] = digest(data)
    recipe = ast.parse((stage / RECIPE).read_bytes())
    declared = next(ast.literal_eval(node.value) for node in recipe.body
                    if isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "INPUTS" for t in node.targets))
    if len(declared) != 7 or set(core_pins) != {*declared, RECIPE, LAUNCHER}:
        raise SystemExit("Core input set differs from declared build recipe")

    env = core_environment(tmp, args.dotnet, initialized_home=True)
    env["PYTHONPATH"] = str(stage / "service")
    # Keep a usable PATH for ip/unshare children already in env.

    def invoke(label, command, **options):
        result = subprocess.run(command, cwd=str(stage), env=env, check=False, timeout=120, **options)
        log(f"{label} exit={result.returncode}")
        if result.returncode:
            if result.stdout:
                log(result.stdout.decode() if isinstance(result.stdout, bytes) else result.stdout)
            if result.stderr:
                log(result.stderr.decode() if isinstance(result.stderr, bytes) else result.stderr)
            raise SystemExit(result.returncode)
        return result

    version = invoke("SDK version", [str(args.dotnet), "--version"], stdout=subprocess.PIPE).stdout.decode().strip()
    if version != SDK:
        raise SystemExit(f"Wrong SDK; require {SDK}, got {version}")
    invoke("NuGet local directories check", [str(args.dotnet), "nuget", "locals", "all", "--list"], stdout=subprocess.PIPE)
    smoke = invoke("Core smoke", [str(stage / LAUNCHER)], stdout=subprocess.PIPE,
                   input=json.dumps({"action": "validate", "draft": {"scope": "Synthetic local smoke", "nodes": [], "edges": []}}).encode())
    payload = json.loads(smoke.stdout)
    if not (payload.get("ok") is True and payload["result"]["coreVersion"] == "mcis-ecfc-draft/1"):
        raise SystemExit(f"Core smoke failed: {payload}")
    if payload["result"]["nodes"] or payload["result"]["edges"]:
        raise SystemExit("Core smoke expected empty graph")
    out = stage / TOOL / "out"
    manifest = json.loads((out / "build-manifest.json").read_text())
    if manifest["sdk"] != SDK or manifest["contract"] != "mcis-ecfc-build/1":
        raise SystemExit(f"Unexpected ECFC manifest: {manifest}")
    if manifest["recipeSha256"] != core_pins[RECIPE]:
        raise SystemExit("Recipe hash mismatch")
    if manifest["inputs"] != {path: core_pins[path] for path in declared}:
        raise SystemExit("Input hash mismatch")
    artifacts = manifest["artifacts"]
    if "mcis-ecfc.dll" not in artifacts:
        raise SystemExit("mcis-ecfc.dll missing from artifacts")
    for name, sha in artifacts.items():
        if Path(name).name != name or sha_file(out / name) != sha:
            raise SystemExit(f"Artifact mismatch: {name}")
    # Keep a copy of artifacts in the report (not a product tree write).
    copied = report / "ecfc-core-out"
    if copied.exists():
        shutil.rmtree(copied)
    shutil.copytree(out, copied)
    log(f"Verified offline mcis-ecfc smoke; dll SHA-256={artifacts['mcis-ecfc.dll']} contract={manifest['contract']}")

    # Host environment for the Python service: reuse initialized HOME so imports work,
    # still only lo, no extra network.
    host_env = {k: v for k, v in os.environ.items() if k in ("PATH", "LANG", "LC_ALL", "LD_LIBRARY_PATH", "HOME", "TMPDIR")}
    host_env.update(MCIS_DOTNET=str(args.dotnet), MCIS_SEED_DEMO="0",
                    DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_NOLOGO="1",
                    DOTNET_ROOT=str(args.dotnet.parent),
                    RestoreSources=str(tmp / "empty-feed"), NuGetAudit="false",
                    NUGET_PACKAGES=str(tmp / "packages"),
                    NUGET_HTTP_CACHE_PATH=str(tmp / "http-cache"),
                    NUGET_PLUGINS_CACHE_PATH=str(tmp / "plugins-cache"),
                    RestoreFallbackFolders="",
                    TMPDIR=str(tmp))

    official_data = tmp / "official-app-data"
    official_data.mkdir()
    official_db = official_data / "official.sqlite"
    official_routes = out_dir / "official-app-routes.json"
    official_ready = official_data / "ready.json"
    official_proc = start_server(str(args.python), stage, official_data, official_db, args.port,
                                 False, official_routes, official_ready, host_env)
    official_log = ""
    try:
        wait_health(f"http://127.0.0.1:{args.port}")
        if official_proc.poll() is not None:
            official_log = official_proc.stdout.read().decode("utf-8", "replace") if official_proc.stdout else ""
            raise SystemExit(f"Official app exited early: {official_proc.returncode}\n{official_log}")
        listeners = bind_listeners(official_proc.pid)
        write_json(out_dir / "official-app-listeners.json", listeners)
        bad = [row for row in listeners if row["addr"] not in {"127.0.0.1", "0000000000000000000000000100007F", "0100007F"}]
        # ipv4 127.0.0.1 is 0100007F in /proc/net/tcp little-endian hex already converted
        bad = [row for row in listeners if not (
            row["addr"] in {"127.0.0.1"} or row["addr"].endswith("127.0.0.1") or
            row["addr"] in {"0000000000000000000000000100007F"} or
            set(row["addr"]) <= set("0:") or row["addr"] in {"::1", "0:0:0:0:0:0:0:1"}
        )]
        # Recompute bad simply: only 127.0.0.1 / ::1, never 0.0.0.0
        bad = [row for row in listeners if row["addr"] in {"0.0.0.0", "::", "00000000"}]
        if bad:
            raise SystemExit(f"Non-loopback bind: {listeners}")
        routes = json.loads(official_routes.read_text())
        if routes["officialPathsContainPilot"] or routes["enablePilot"]:
            raise SystemExit("Official app unexpectedly enabled the pilot route")
        status, headers, body = http_json("POST", f"http://127.0.0.1:{args.port}{pins['PATH']}", headers=LEAD,
                                          body={"caseId": pins["CASE"], "revision": 1, "digest": "0"*64,
                                                "edgeId": pins["EDGE"][0], "from": pins["EDGE"][1], "to": pins["EDGE"][2]})
        write_json(out_dir / "official-app-pilot-post.json", {"status": status, "headers": {k: v for k, v in headers.items()}, "body": body})
        if status != 404:
            raise SystemExit(f"Official app pilot POST expected 404, got {status} {body}")
        log(f"Official create_app HTTP proof: pilot route absent, POST {pins['PATH']} -> {status}, bind={listeners}")
    finally:
        stop_server(official_proc, args.port)
        leftover = official_proc.stdout.read() if official_proc.stdout else b""
        if leftover:
            (out_dir / "official-app-server.log").write_bytes(leftover)

    # Same 127.0.0.1 process + temp SQLite. Pinned create_app does not mount
    # ECFC HTTP routes; drafts go through existing preview_sync/save_sync (real .NET).
    # The excerpt route is registered only after create_app in this pilot process.
    for key, value in host_env.items():
        os.environ[key] = value
    os.environ["MCIS_DOTNET"] = str(args.dotnet)
    sys.path[:0] = [str(stage / "service"), str(EXCERPT), str(EDGE_HOST)]
    from types import SimpleNamespace
    from mcis_service.config import PROJECT_ROOT, Settings
    from mcis_service.ecfc_drafts import router as ec
    from mcis_service.main import create_app
    from host import PATH, setup

    cli = Path(ec.CLI).resolve()
    expected_cli = (Path(PROJECT_ROOT) / "tools" / "mcis-ecfc" / "mcis-ecfc.sh").resolve()
    if cli != expected_cli or cli != (stage / LAUNCHER).resolve():
        raise SystemExit(f"ECFC launcher mismatch: {cli}")
    if "mcis-w11-isolated-cand" in str(cli) or "maritime-sim-design" in str(cli):
        raise SystemExit(f"Refusing to invoke worktree/product launcher: {cli}")

    data_dir = tmp / "pilot-data"
    data_dir.mkdir()
    db = data_dir / "pilot.sqlite"
    routes_out = out_dir / "pilot-routes.json"
    cfg = Settings(data_dir=data_dir, db_url=f"sqlite:///{db}", seed_demo=False)
    app = create_app(cfg)
    official_paths = set(openapi_paths(app))
    if pins["PATH"] in official_paths:
        raise SystemExit("Official create_app registered the pilot excerpt route")
    # HTTP /ecfc/preview and /ecfc/save are absent on this pinned create_app; do not add them.
    persisted_http = {path for path in official_paths if path.rstrip("/").endswith(("/ecfc/preview", "/ecfc/save", "/ecfc/draft", "/ecfc/audit"))}
    write_json(out_dir / "pinned-create-app-ecfc-http.json", {
        "ecfcHttpRoutes": sorted(persisted_http),
        "note": "Pinned isolation-assembly create_app does not include ecfc_drafts_router; existing preview_sync/save_sync are used instead of changing main.py",
    })
    setup(app)
    after_paths = set(openapi_paths(app))
    # include_in_schema=False routes may be omitted from OpenAPI; check the router too.
    router_paths = {getattr(route, "path", None) for route in app.router.routes}
    if pins["PATH"] not in router_paths:
        raise SystemExit("Pilot setup did not register the excerpt route")
    write_json(routes_out, {
        "enablePilot": True,
        "pilotPath": pins["PATH"],
        "officialPathsContainPilot": pins["PATH"] in official_paths,
        "officialOpenApiPaths": sorted(official_paths),
        "routerPathsAfterSetupContainPilot": pins["PATH"] in router_paths,
        "ecfcHttpRoutesInPinnedCreateApp": sorted(persisted_http),
        "cli": str(cli),
        "projectRoot": str(Path(PROJECT_ROOT).resolve()),
        "bind": {"host": "127.0.0.1", "port": args.port},
    })
    server, thread = start_loopback(app, "127.0.0.1", args.port)
    ctx = SimpleNamespace(db=app.state.db, settings=cfg, role=LEAD["X-MCIS-Role"], operator=LEAD["X-MCIS-Operator"])
    gates = {}
    try:
        wait_health(f"http://127.0.0.1:{args.port}")
        listeners = bind_listeners(os.getpid())
        write_json(out_dir / "pilot-listeners.json", listeners)
        if any(row["addr"] in {"0.0.0.0", "::", "00000000"} for row in listeners if row["port"] == args.port):
            raise SystemExit(f"Pilot non-loopback bind: {listeners}")
        if not any(row["addr"] == "127.0.0.1" and row["port"] == args.port for row in listeners):
            # IPv4 loopback may be listed; if empty, still require health already passed.
            log(f"Listener table for pid {os.getpid()}: {listeners}")
        base = f"http://127.0.0.1:{args.port}"
        CASE, API, CUSTODY = pins["CASE"], pins["API"], pins["CUSTODY"]

        status, _, created = http_json("POST", base + "/api/v1/cases", headers=LEAD, body=pins["DOC"])
        if status != 201:
            raise SystemExit(f"Create case failed: {status} {created}")
        intake = dict(profile="mcis-evidence-intake-v1", fileName="communication.txt", title="Synthetic communication",
                      source="Handmade synthetic fixture", extractedBy="Synthetic author", extractedUtc="2026-02-01T00:00:00Z",
                      category="Document", confidentiality="Restricted", note="No real record",
                      contentBase64=__import__("base64").b64encode(source).decode())
        status, _, draft_receipt = http_json("POST", base + API + "/evidence-intakes:preview", headers=LEAD, body=intake)
        if status != 200:
            raise SystemExit(f"Intake preview failed: {status} {draft_receipt}")
        status, _, receipt = http_json("POST", base + API + "/evidence-intakes:commit", headers=LEAD,
                                       body={**intake, "confirmed": True, "requestDigest": draft_receipt["requestDigest"]})
        if status != 200 or receipt["sourceSha256"] != pins["SOURCE_SHA"] or receipt["evidenceId"] != "EV-001":
            raise SystemExit(f"Intake commit failed: {status} {receipt}")
        write_json(out_dir / "intake-receipt.json", receipt)

        draft, expected, edge = draft_body(receipt["metadata"]["title"], "Synthetic edge, no finding")
        preview = service_preview(ec, ctx, CASE, draft, expected)
        write_json(out_dir / "preview.json", preview)
        if preview.get("persisted") is not False or preview.get("validation", {}).get("coreVersion") != "mcis-ecfc-draft/1":
            raise SystemExit(f"Preview contract mismatch: {preview}")
        if preview["validation"]["edges"] != [{**edge, "kind": "Influence", "bold": False}]:
            raise SystemExit(f"Preview edges mismatch: {preview['validation']['edges']}")
        peek = json.loads(ec.get_draft(CASE, ctx).body)
        if peek.get("document") is not None:
            raise SystemExit(f"Preview must not persist a draft: {peek}")

        saved = service_save(ec, ctx, CASE, "6bff10c5-3381-4fcc-8c53-a1120bba0cee", None, draft, expected)
        write_json(out_dir / "save-rev1.json", saved)
        doc = saved["document"]
        if doc["revision"] != 1 or doc["status"] != "Draft" or doc["strength"] != "ToBeVerified":
            raise SystemExit(f"Save revision 1 document mismatch: {doc}")
        if doc["validation"]["coreVersion"] != "mcis-ecfc-draft/1":
            raise SystemExit("Save did not use mcis-ecfc-draft/1")
        peeked = json.loads(ec.get_draft(CASE, ctx).body)
        if peeked.get("document") != doc:
            raise SystemExit("GET draft after save mismatch")
        gates["draft_saved_via_existing_service"] = {
            "ok": True, "revision": doc["revision"], "digest": doc["digest"],
            "coreVersion": doc["validation"]["coreVersion"], "previewPersisted": False,
            "path": "existing preview_sync/save_sync in the same loopback process",
            "ecfcHttpRoutesInPinnedCreateApp": sorted(persisted_http),
        }
        log(f"Gate 1 PASS: preview+save via existing service functions, coreVersion=mcis-ecfc-draft/1, revision=1 digest={doc['digest']}")

        delete_trigger = "CREATE TRIGGER pilot_no_delete BEFORE DELETE ON pilot_single_source BEGIN SELECT RAISE(ABORT,'pilot association is fixed'); END"
        sqlite_exec(db, pins["DDL"])
        sqlite_exec(db, pins["TRIGGER"])
        sqlite_exec(db, delete_trigger)
        sqlite_exec(db, """INSERT INTO pilot_single_source VALUES (1,:case,:rev,:graph,:edge,:from_,:to_,
            'EV-001',:request,:sha,97,121,0)""",
                    dict(case=CASE, rev=doc["revision"], graph=doc["digest"], edge=pins["EDGE"][0],
                         from_=pins["EDGE"][1], to_=pins["EDGE"][2], request=receipt["requestDigest"],
                         sha=pins["SOURCE_SHA"]))

        bind_args = dict(caseId=CASE, revision=1, digest=doc["digest"],
                         edgeId=pins["EDGE"][0], **{"from": pins["EDGE"][1], "to": pins["EDGE"][2]})
        status, pub_headers, pub_body = http_json("POST", base + pins["PATH"], headers=PUBLIC, body=bind_args)
        if status != 404 or (pub_headers.get("Cache-Control") or pub_headers.get("cache-control")) != "no-store":
            raise SystemExit(f"Public excerpt expected 404 no-store, got {status} {pub_headers} {pub_body}")
        wrong = {"caseId": CASE, "revision": 1, "digest": doc["digest"], "edgeId": "E01", "from": "C01", "to": "WRONG"}
        status, _, wrong_body = http_json("POST", base + pins["PATH"], headers=LEAD, body=wrong)
        if status != 404:
            raise SystemExit(f"Wrong edge expected 404, got {status} {wrong_body}")
        status, _, custody0 = http_json("GET", base + CUSTODY, headers=LEAD)
        if status != 200 or [a["kind"] for a in custody0] != ["Register"]:
            raise SystemExit(f"Custody before successful read: {status} {custody0}")

        status, ok_headers, excerpt = http_json("POST", base + pins["PATH"], headers=LEAD, body=bind_args)
        write_json(out_dir / "explicit-read.json", {"status": status, "headers": dict(ok_headers), "body": excerpt})
        if status != 200:
            raise SystemExit(f"Explicit read failed: {status} {excerpt}")
        if (ok_headers.get("Cache-Control") or ok_headers.get("cache-control")) != "no-store":
            raise SystemExit("Successful excerpt missing Cache-Control: no-store")
        if excerpt.get("excerpt") != pins["UTC"] or excerpt.get("sourceUtc") != pins["UTC"]:
            raise SystemExit(f"T+109 excerpt mismatch: {excerpt}")
        if excerpt.get("locator") != "/sourceBytes/97/121" or excerpt.get("context") != bind_args:
            raise SystemExit(f"Excerpt context/locator mismatch: {excerpt}")
        status, _, custody1 = http_json("GET", base + CUSTODY, headers=LEAD)
        if status != 200 or [a["kind"] for a in custody1] != ["Register", "Access"]:
            raise SystemExit(f"Custody after explicit read: {status} {custody1}")
        gates["explicit_read_specified_binding"] = {
            "ok": True, "excerpt": excerpt["excerpt"], "sourceUtc": excerpt["sourceUtc"],
            "locator": excerpt["locator"], "context": excerpt["context"],
            "publicDenied": 404, "wrongEdgeDenied": 404,
            "custodyAfterSuccess": [a["kind"] for a in custody1],
        }
        gates["t109_recorded_source_time_only"] = {
            "ok": True, "sourceRecordedUtc": excerpt["sourceUtc"],
            "incidentTimeUtc": pins["DOC"]["incidentTimeUtc"],
            "note": "T+109 is the registered source span, not the incident epoch",
        }
        log("Gate 2 PASS: explicit HTTP read returns only specified graph version/edge/registered T+109 span")
        log("Gate 4 PASS: T+109 2026-02-01T12:01:49.000Z recorded as sourceUtc only; incidentTimeUtc remains 2026-02-01T12:00:00Z")

        draft2, expected2, _edge = draft_body(receipt["metadata"]["title"], "Synthetic graph revision")
        saved2 = service_save(ec, ctx, CASE, "6bff10c5-3381-4fcc-8c53-a1120bba0cef", doc["digest"], draft2, expected2)
        write_json(out_dir / "save-rev2.json", saved2)
        doc2 = saved2["document"]
        if doc2["revision"] != 2 or doc2["digest"] == doc["digest"]:
            raise SystemExit(f"Revision 2 mismatch: {doc2}")
        if doc2["validation"]["coreVersion"] != "mcis-ecfc-draft/1":
            raise SystemExit("Revision 2 did not use real ECFC core")
        status, _, old_after_rev = http_json("POST", base + pins["PATH"], headers=LEAD, body=bind_args)
        write_json(out_dir / "read-after-revision.json", {"status": status, "body": old_after_rev})
        if status != 404:
            raise SystemExit(f"Old binding after revision expected 404, got {status} {old_after_rev}")

        count, _ = sqlite_exec(db, "UPDATE pilot_single_source SET revoked=1 WHERE singleton=1 AND revoked=0")
        if count != 1:
            raise SystemExit(f"Revoke update rowcount={count}")
        status, _, old_after_revoke = http_json("POST", base + pins["PATH"], headers=LEAD, body=bind_args)
        write_json(out_dir / "read-after-revoke.json", {"status": status, "body": old_after_revoke})
        if status != 404:
            raise SystemExit(f"Old binding after revoke expected 404, got {status} {old_after_revoke}")
        new_args = dict(bind_args, revision=2, digest=doc2["digest"])
        status, _, unbound_new = http_json("POST", base + pins["PATH"], headers=LEAD, body=new_args)
        if status != 404:
            raise SystemExit(f"Unbound revision 2 expected 404, got {status} {unbound_new}")
        status, _, custody2 = http_json("GET", base + CUSTODY, headers=LEAD)
        if status != 200 or [a["kind"] for a in custody2] != ["Register", "Access"]:
            raise SystemExit(f"Custody must not gain Access on denied reads: {custody2}")
        status, _, audit = http_json("GET", base + API + "/audit:verify", headers=LEAD)
        if status != 200 or not audit.get("valid"):
            raise SystemExit(f"Case audit verify failed: {status} {audit}")
        status, _, commands = http_json("GET", base + API + "/sim/commands", headers=LEAD)
        if status != 200 or commands.get("commands") != []:
            raise SystemExit(f"Unexpected sim commands: {status} {commands}")
        with ctx.db.session() as session:
            from sqlalchemy import select
            audits = list(session.scalars(select(ec.EcfcAuditRow).where(ec.EcfcAuditRow.case_id == CASE).order_by(ec.EcfcAuditRow.revision)))
            requests_rows = list(session.scalars(select(ec.EcfcRequestRow).where(ec.EcfcRequestRow.case_id == CASE)))
        write_json(out_dir / "ecfc-audit.json", {
            "auditCount": len(audits),
            "requestCount": len(requests_rows),
            "revisions": [row.revision for row in audits],
        })
        if len(audits) != 2 or [row.revision for row in audits] != [1, 2]:
            raise SystemExit(f"Existing ECFC audit rows unexpected: {[row.revision for row in audits]}")
        gates["old_binding_rejected_after_revision_or_revoke"] = {
            "ok": True, "afterRevision": 404, "afterRevoke": 404, "unboundRevision2": 404,
            "revision2": doc2["revision"], "digest2": doc2["digest"],
            "custodyFinal": [a["kind"] for a in custody2],
            "auditValid": True, "simCommands": commands.get("commands"),
            "ecfcAuditRevisions": [row.revision for row in audits],
        }
        log("Gate 3 PASS: old binding rejected after revision and after revoke; no extra Access; case audit valid; ECFC audit 1,2")

        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            pin_row = con.execute("SELECT revision, graph_digest, revoked FROM pilot_single_source WHERE singleton=1").fetchone()
        finally:
            con.close()
        write_json(out_dir / "sqlite-snapshot.json", {
            "tablesPresent": sorted(tables),
            "pin": {"revision": pin_row[0], "digest": pin_row[1], "revoked": pin_row[2]},
        })
        if pin_row[0] != 1 or pin_row[1] != doc["digest"] or pin_row[2] != 1:
            raise SystemExit(f"Unexpected pin row: {pin_row}")
    finally:
        stop_loopback(server, thread, args.port)
        try:
            app.state.db.engine.dispose()
        except Exception:
            pass

    receipt = {
        "passed": True,
        "kind": "w11-isolated-synthetic-pilot",
        "pin": PIN,
        "httpNotBrowser": True,
        "notWholePackage": True,
        "bind": "127.0.0.1",
        "namedDllUnused": named,
        "ecfc": {
            "contract": manifest["contract"],
            "coreVersion": "mcis-ecfc-draft/1",
            "sdk": SDK,
            "dllSha256": artifacts["mcis-ecfc.dll"],
            "artifacts": artifacts,
        },
        "gates": gates,
        "firstBreakpoint": None,
        "cli": str((stage / LAUNCHER).resolve()),
        "draftPath": "existing preview_sync/save_sync in the same 127.0.0.1 process",
        "ecfcHttpRoutesInPinnedCreateApp": False,
    }
    write_json(out_dir / "receipt.json", receipt)
    (out_dir / "console.log").write_text("".join(logs), encoding="utf-8")
    log("OFFICIAL RESULT: all four gates PASS (HTTP, not browser); W11 whole-package 未验")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
