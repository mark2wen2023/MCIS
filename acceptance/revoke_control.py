"""Independent W11 revoke control. Does not rerun the revision branch or edit run.py checks."""
from __future__ import annotations

import argparse
import ast
import json
import os
import runpy
import shutil
import sqlite3
import stat
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run as iso

PIN_PARENT = "6fe7777fbad84d60ed0854442734bebb967794b4"
EXPECTED_DLL = "f548818bd21c45d640293601f2ae271171c086f7e0b22912472a2d7dc771e75a"
HOST_REVOKE = (
    "UPDATE pilot_single_source SET revoked=1 WHERE singleton=1 AND revoked=0"
)
DELETE_TRIGGER = (
    "CREATE TRIGGER pilot_no_delete BEFORE DELETE ON pilot_single_source "
    "BEGIN SELECT RAISE(ABORT,'pilot association is fixed'); END"
)

def log(logs, msg):
    line = msg if msg.endswith("\n") else msg + "\n"
    sys.stdout.write(line)
    sys.stdout.flush()
    logs.append(line)

def custody_kinds(rows):
    return [a["kind"] for a in rows]

def pin_identifying(row):
    keys = ("case_id", "revision", "graph_digest", "edge_id", "from_id", "to_id",
            "evidence_id", "intake_digest", "source_sha", "start_byte", "end_byte")
    return {k: row[k] for k in keys}

def main():
    if not __debug__:
        raise SystemExit("Assertions must be enabled")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dotnet", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, action="append")
    parser.add_argument("--port", type=int, default=18766)
    args = parser.parse_args()
    if not args.dotnet.is_absolute() or not os.access(args.dotnet, os.X_OK):
        raise SystemExit("BLOCKED: preinstalled SDK executable not found; official run did not start")
    if not args.python.is_absolute() or not os.access(args.python, os.X_OK):
        raise SystemExit("BLOCKED: preinstalled service Python not found; official run did not start")

    pins = iso.PINS
    report = args.report.resolve()
    report.mkdir(parents=True, exist_ok=True)
    out_dir = report / "official"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir()
    logs = []
    sequence = []

    def step(name):
        sequence.append(name)
        log(logs, f"STEP {len(sequence)}: {name}")

    worktree = iso.WORKTREE
    if not (worktree / ".git").exists():
        raise SystemExit("Candidate worktree missing")
    head = subprocess.check_output(["git", "-C", str(worktree), "rev-parse", "HEAD"], text=True).strip()
    if head != PIN_PARENT:
        # Allow only the new control script as uncommitted or later commit still based on 6fe7777.
        merge = subprocess.check_output(
            ["git", "-C", str(worktree), "merge-base", "--is-ancestor", PIN_PARENT, "HEAD"], check=False
        )
        if merge.returncode != 0:
            raise SystemExit(f"HEAD {head} is not 6fe7777 or a descendant")
        diff = subprocess.check_output(
            ["git", "-C", str(worktree), "diff", "--name-only", PIN_PARENT, "HEAD"], text=True
        ).splitlines()
        allowed = {"tests_acceptance/w11-isolated-synthetic-pilot/revoke_control.py"}
        if any(path not in allowed for path in diff):
            raise SystemExit(f"Unexpected changes versus 6fe7777: {diff}")
    log(logs, f"Worktree HEAD={head}; parent assembly {PIN_PARENT}")

    source = subprocess.check_output(["git", "-C", str(worktree), "cat-file", "blob", iso.COMM_BLOB])
    if iso.git_blob(source) != iso.COMM_BLOB or iso.digest(source) != pins["SOURCE_SHA"]:
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
    step("stage isolation assembly and core sources")
    source_dirs = [p.resolve() for p in (args.source_dir or ([iso.SOURCE_EXPORT] if iso.SOURCE_EXPORT.is_dir() else []))]
    if not source_dirs:
        raise SystemExit("Missing local pinned source export; no fetch attempted")
    inherited = runpy.run_path(str(iso.EXCERPT / "run.py"))
    ns = argparse.Namespace(source_dir=source_dirs, repository=None)

    class _Parser:
        def error(self, message):
            raise SystemExit(message)

    pinned = set()
    for line in (iso.EXCERPT / "SOURCES").read_text().splitlines():
        item, data = inherited["get_blob"](line, ns, _Parser())
        iso.stage_file(stage, item.as_posix(), data, 0o644)
        pinned.add(item.as_posix())
    if len(pinned) != 186 or inherited["CORE_MARKER"] not in pinned:
        raise SystemExit(f"Incomplete 186-file assembly: {len(pinned)}")
    core_pins = {}
    for line in (worktree / iso.CORE_DIR).read_text().splitlines():
        mode, blob, item = line.split(" ")
        data = (worktree / item).read_bytes()
        if iso.git_blob(data) != blob:
            raise SystemExit(f"Core blob mismatch: {item}")
        chmod = int(mode, 8) & 0o777
        iso.stage_file(stage, item, data, chmod)
        if stat.S_IMODE((stage / item).stat().st_mode) != chmod:
            raise SystemExit(f"Staged mode mismatch: {item}")
        core_pins[item] = iso.digest(data)
    recipe = ast.parse((stage / iso.RECIPE).read_bytes())
    declared = next(ast.literal_eval(node.value) for node in recipe.body
                    if isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "INPUTS" for t in node.targets))
    if len(declared) != 7 or set(core_pins) != {*declared, iso.RECIPE, iso.LAUNCHER}:
        raise SystemExit("Core input set differs from declared build recipe")
    log(logs, f"Staged {len(pinned)} pinned originals + {len(core_pins)} core blobs")

    env = iso.core_environment(tmp, args.dotnet, initialized_home=True)
    env["PYTHONPATH"] = str(stage / "service")

    def invoke(label, command, **options):
        result = subprocess.run(command, cwd=str(stage), env=env, check=False, timeout=120, **options)
        log(logs, f"{label} exit={result.returncode}")
        if result.returncode:
            if result.stdout:
                log(logs, result.stdout.decode() if isinstance(result.stdout, bytes) else result.stdout)
            raise SystemExit(result.returncode)
        return result

    step("SDK and NuGet preflight, then official offline mcis-ecfc smoke")
    version = invoke("SDK version", [str(args.dotnet), "--version"], stdout=subprocess.PIPE).stdout.decode().strip()
    if version != iso.SDK:
        raise SystemExit(f"Wrong SDK; require {iso.SDK}, got {version}")
    invoke("NuGet local directories check", [str(args.dotnet), "nuget", "locals", "all", "--list"], stdout=subprocess.PIPE)
    smoke = invoke("Core smoke", [str(stage / iso.LAUNCHER)], stdout=subprocess.PIPE,
                   input=json.dumps({"action": "validate", "draft": {"scope": "Synthetic local smoke", "nodes": [], "edges": []}}).encode())
    payload = json.loads(smoke.stdout)
    if not (payload.get("ok") is True and payload["result"]["coreVersion"] == "mcis-ecfc-draft/1"):
        raise SystemExit(f"Core smoke failed: {payload}")
    out = stage / iso.TOOL / "out"
    manifest = json.loads((out / "build-manifest.json").read_text())
    artifacts = manifest["artifacts"]
    if manifest["contract"] != "mcis-ecfc-build/1" or artifacts.get("mcis-ecfc.dll") != EXPECTED_DLL:
        raise SystemExit(f"Unexpected ECFC artifact: {artifacts}")
    if iso.sha_file(out / "mcis-ecfc.dll") != EXPECTED_DLL:
        raise SystemExit("Rebuilt DLL hash mismatch")
    copied = report / "ecfc-core-out"
    if copied.exists():
        shutil.rmtree(copied)
    shutil.copytree(out, copied)
    log(logs, f"Verified mcis-ecfc.dll SHA-256={EXPECTED_DLL}")

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
    for key, value in host_env.items():
        os.environ[key] = value
    os.environ["MCIS_DOTNET"] = str(args.dotnet)
    sys.path[:0] = [str(stage / "service"), str(iso.EXCERPT), str(iso.EDGE_HOST)]
    from sqlalchemy import text
    from mcis_service.config import PROJECT_ROOT, Settings
    from mcis_service.db import WRITE_LOCK
    from mcis_service.ecfc_drafts import router as ec
    from mcis_service.main import create_app
    from host import PATH, setup

    cli = Path(ec.CLI).resolve()
    if cli != (Path(PROJECT_ROOT) / "tools" / "mcis-ecfc" / "mcis-ecfc.sh").resolve() != (stage / iso.LAUNCHER).resolve():
        # Compare both to staged launcher only.
        pass
    if cli != (stage / iso.LAUNCHER).resolve():
        raise SystemExit(f"ECFC launcher mismatch: {cli}")

    data_dir = tmp / "revoke-data"
    data_dir.mkdir()
    db = data_dir / "pilot.sqlite"
    if db.exists():
        raise SystemExit("Temp SQLite was not empty")
    cfg = Settings(data_dir=data_dir, db_url=f"sqlite:///{db}", seed_demo=False)
    app = create_app(cfg)
    if pins["PATH"] in {getattr(route, "path", None) for route in app.router.routes}:
        raise SystemExit("Official create_app registered the pilot excerpt route")
    setup(app)
    if pins["PATH"] not in {getattr(route, "path", None) for route in app.router.routes}:
        raise SystemExit("Pilot setup did not register the excerpt route")
    server, thread = iso.start_loopback(app, "127.0.0.1", args.port)
    ctx = SimpleNamespace(db=app.state.db, settings=cfg, role=iso.LEAD["X-MCIS-Role"], operator=iso.LEAD["X-MCIS-Operator"])
    try:
        step("start 127.0.0.1 loopback on a fresh empty SQLite")
        iso.wait_health(f"http://127.0.0.1:{args.port}")
        listeners = iso.bind_listeners(os.getpid())
        iso.write_json(out_dir / "listeners.json", listeners)
        if any(row["addr"] in {"0.0.0.0", "::", "00000000"} and row["port"] == args.port for row in listeners):
            raise SystemExit(f"Non-loopback bind: {listeners}")
        base = f"http://127.0.0.1:{args.port}"
        CASE, API, CUSTODY = pins["CASE"], pins["API"], pins["CUSTODY"]

        step("seed synthetic case and evidence via existing intake HTTP")
        status, _, created = iso.http_json("POST", base + "/api/v1/cases", headers=iso.LEAD, body=pins["DOC"])
        if status != 201:
            raise SystemExit(f"Create case failed: {status} {created}")
        intake = dict(profile="mcis-evidence-intake-v1", fileName="communication.txt", title="Synthetic communication",
                      source="Handmade synthetic fixture", extractedBy="Synthetic author", extractedUtc="2026-02-01T00:00:00Z",
                      category="Document", confidentiality="Restricted", note="No real record",
                      contentBase64=__import__("base64").b64encode(source).decode())
        status, _, draft_receipt = iso.http_json("POST", base + API + "/evidence-intakes:preview", headers=iso.LEAD, body=intake)
        if status != 200:
            raise SystemExit(f"Intake preview failed: {status} {draft_receipt}")
        status, _, receipt = iso.http_json("POST", base + API + "/evidence-intakes:commit", headers=iso.LEAD,
                                           body={**intake, "confirmed": True, "requestDigest": draft_receipt["requestDigest"]})
        if status != 200 or receipt["sourceSha256"] != pins["SOURCE_SHA"] or receipt.get("replayed") is not False:
            raise SystemExit(f"Intake commit failed: {status} {receipt}")
        iso.write_json(out_dir / "intake-receipt.json", receipt)

        step("save current draft via existing service and real mcis-ecfc")
        draft, expected, edge = iso.draft_body(receipt["metadata"]["title"], "Synthetic edge, no finding")
        preview = iso.service_preview(ec, ctx, CASE, draft, expected)
        iso.write_json(out_dir / "preview.json", preview)
        if preview.get("persisted") is not False or preview.get("validation", {}).get("coreVersion") != "mcis-ecfc-draft/1":
            raise SystemExit(f"Preview contract mismatch: {preview}")
        saved = iso.service_save(ec, ctx, CASE, "9f3c2b1a-4d55-4789-abcd-0123456789ab", None, draft, expected)
        iso.write_json(out_dir / "save-rev1.json", saved)
        doc = saved["document"]
        if doc["revision"] != 1 or doc["validation"]["coreVersion"] != "mcis-ecfc-draft/1":
            raise SystemExit(f"Save mismatch: {doc}")
        log(logs, f"Saved revision=1 digest={doc['digest']} coreVersion={doc['validation']['coreVersion']}")

        step("register the current valid binding with the existing isolated-assembly SQL")
        iso.sqlite_exec(db, pins["DDL"])
        iso.sqlite_exec(db, pins["TRIGGER"])
        iso.sqlite_exec(db, DELETE_TRIGGER)
        iso.sqlite_exec(db, """INSERT INTO pilot_single_source VALUES (1,:case,:rev,:graph,:edge,:from_,:to_,
            'EV-001',:request,:sha,97,121,0)""",
                        dict(case=CASE, rev=doc["revision"], graph=doc["digest"], edge=pins["EDGE"][0],
                             from_=pins["EDGE"][1], to_=pins["EDGE"][2], request=receipt["requestDigest"],
                             sha=pins["SOURCE_SHA"]))
        bind_args = dict(caseId=CASE, revision=1, digest=doc["digest"],
                         edgeId=pins["EDGE"][0], **{"from": pins["EDGE"][1], "to": pins["EDGE"][2]})

        step("explicit read of the same currently valid binding (expect 200 and one Access)")
        status, _, custody0 = iso.http_json("GET", base + CUSTODY, headers=iso.LEAD)
        if status != 200 or custody_kinds(custody0) != ["Register"]:
            raise SystemExit(f"Custody before success: {status} {custody0}")
        status, ok_headers, excerpt = iso.http_json("POST", base + pins["PATH"], headers=iso.LEAD, body=bind_args)
        iso.write_json(out_dir / "read-before-revoke.json", {"status": status, "headers": dict(ok_headers), "body": excerpt})
        if status != 200 or excerpt.get("excerpt") != pins["UTC"] or excerpt.get("sourceUtc") != pins["UTC"]:
            raise SystemExit(f"Expected successful explicit read, got {status} {excerpt}")
        if excerpt.get("locator") != "/sourceBytes/97/121" or excerpt.get("context") != bind_args:
            raise SystemExit(f"Excerpt context mismatch: {excerpt}")
        status, _, custody1 = iso.http_json("GET", base + CUSTODY, headers=iso.LEAD)
        if status != 200 or custody_kinds(custody1) != ["Register", "Access"]:
            raise SystemExit(f"Custody after success: {status} {custody1}")
        log(logs, "Explicit read PASS on the live binding; custody=Register,Access")

        step("revoke via existing host.py mechanism without changing version/digest/identity/edge/span")
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        before = dict(con.execute("SELECT * FROM pilot_single_source WHERE singleton=1").fetchone())
        con.close()
        with WRITE_LOCK, ctx.db.session() as session:
            ec.begin(session, write=True)
            count = session.execute(text(HOST_REVOKE)).rowcount
        if count != 1:
            raise SystemExit(f"Existing revoke UPDATE rowcount={count}")
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        after = dict(con.execute("SELECT * FROM pilot_single_source WHERE singleton=1").fetchone())
        con.close()
        iso.write_json(out_dir / "pin-before-after.json", {"before": before, "after": after})
        if pin_identifying(before) != pin_identifying(after):
            raise SystemExit(f"Revoke changed identifying fields: {before} -> {after}")
        if before["revoked"] != 0 or after["revoked"] != 1:
            raise SystemExit(f"Revoke flag not 0->1: {before['revoked']} -> {after['revoked']}")
        peeked = json.loads(ec.get_draft(CASE, ctx).body)["document"]
        if peeked["revision"] != 1 or peeked["digest"] != doc["digest"]:
            raise SystemExit("Graph version or digest changed during revoke")
        log(logs, "Revoke PASS: identifying fields unchanged; revoked 0->1; draft still revision 1")

        step("repeat the same explicit-read request (expect 404, no new Access, valid audit, zero replay)")
        status, denied_headers, denied = iso.http_json("POST", base + pins["PATH"], headers=iso.LEAD, body=bind_args)
        iso.write_json(out_dir / "read-after-revoke.json", {"status": status, "headers": dict(denied_headers), "body": denied})
        if status != 404 or (denied or {}).get("code") != "SOURCE_UNAVAILABLE":
            raise SystemExit(f"Same request after revoke expected 404 SOURCE_UNAVAILABLE, got {status} {denied}")
        status, _, custody2 = iso.http_json("GET", base + CUSTODY, headers=iso.LEAD)
        if status != 200 or custody_kinds(custody2) != ["Register", "Access"]:
            raise SystemExit(f"New Access after denied read: {custody2}")
        status, _, audit = iso.http_json("GET", base + API + "/audit:verify", headers=iso.LEAD)
        if status != 200 or not audit.get("valid"):
            raise SystemExit(f"Case audit verify failed: {status} {audit}")
        status, _, commands = iso.http_json("GET", base + API + "/sim/commands", headers=iso.LEAD)
        if status != 200 or commands.get("commands") != []:
            raise SystemExit(f"Unexpected sim commands (replay?): {status} {commands}")
        peeked = json.loads(ec.get_draft(CASE, ctx).body)["document"]
        if peeked["revision"] != 1 or peeked["digest"] != doc["digest"]:
            raise SystemExit("Draft changed after the denied reread")
        with ctx.db.session() as session:
            from sqlalchemy import select
            audits = list(session.scalars(select(ec.EcfcAuditRow).where(ec.EcfcAuditRow.case_id == CASE).order_by(ec.EcfcAuditRow.revision)))
        if len(audits) != 1 or audits[0].revision != 1:
            raise SystemExit(f"ECFC audit unexpected (revision branch must not run): {[row.revision for row in audits]}")
        iso.write_json(out_dir / "post-revoke-checks.json", {
            "custody": custody_kinds(custody2),
            "auditValid": True,
            "simCommands": commands.get("commands"),
            "draftRevision": peeked["revision"],
            "draftDigest": peeked["digest"],
            "ecfcAuditRevisions": [row.revision for row in audits],
            "intakeReplayed": receipt.get("replayed"),
            "seekAvailable": excerpt.get("locator") == "/sourceBytes/97/121",
        })
        log(logs, "After revoke: 404 SOURCE_UNAVAILABLE; custody unchanged; audit valid; sim commands []; draft still rev 1")
    finally:
        iso.stop_loopback(server, thread, args.port)
        try:
            app.state.db.engine.dispose()
        except Exception:
            pass

    receipt = {
        "passed": True,
        "kind": "w11-revoke-control",
        "parentCandidate": PIN_PARENT,
        "pin": iso.PIN,
        "httpNotBrowser": True,
        "notWholePackage": True,
        "revisionBranchRun": False,
        "bind": "127.0.0.1",
        "sequence": sequence,
        "ecfc": {"contract": manifest["contract"], "coreVersion": "mcis-ecfc-draft/1",
                 "sdk": iso.SDK, "dllSha256": EXPECTED_DLL},
        "digest": doc["digest"],
        "revoke": {"mechanism": "host.py mode=revoke UPDATE, identifying fields unchanged",
                   "rowcount": 1, "revoked": "0->1"},
        "afterRevoke": {"status": 404, "code": "SOURCE_UNAVAILABLE",
                        "custody": ["Register", "Access"], "auditValid": True,
                        "simCommands": [], "ecfcAuditRevisions": [1]},
        "firstBreakpoint": None,
        "correction": {
            "fullAppMain875ccc50": {
                "path": "service/mcis_service/main.py",
                "sha256": "6859848c5a6255740bcb0bfd93609bec13d5ac9ac67b26c8cbfd44a363d10cfa",
                "includesEcfcDraftsRouter": True,
                "line": "app.include_router(ecfc_drafts_router)",
            },
            "isolationAssemblyMain": {
                "sha256": "2c21e58417fe208462921543762eaf3a9c81e9fd40238be44de50e5a9ff28d93",
                "includesEcfcDraftsRouter": False,
                "note": "Previous receipt 'create_app did not mount ecfc_drafts_router' referred only to this pinned assembly, not to 875ccc50 product main.py",
            },
            "productExcerptInterface": False,
        },
    }
    iso.write_json(out_dir / "receipt.json", receipt)
    (out_dir / "console.log").write_text("".join(logs), encoding="utf-8")
    iso.write_json(out_dir / "sequence.json", sequence)
    log(logs, "OFFICIAL RESULT: revoke-only control PASS (HTTP, not browser); revision branch not run; W11 whole-package 未验")
    # rewrite console after final line
    (out_dir / "console.log").write_text("".join(logs), encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
