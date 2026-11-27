"""W12 first-registered-input pilot. Product code is imported, not copied or changed."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PIN = "03a8e7867fedbaaabbf8dd12fc9041d6a1a74cd5"
CORE_DLL_SHA256 = "f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf"
CORE_RUNTIME_SHA256 = "3d25821758613e4cd940d143ccb03c93704140077e69104996832510f38f6598"
CORE_DEPS_SHA256 = "fda133109cf9fc926cbda09598ad344f75dc57ec02e345b6923ec5fe2dff9d12"
CPA_CS_SHA256 = "54de148e91e27a4ca39c693410722e42caf88fcb58e339dc3907161dc9210d6c"

CASE_OK = "SYN-W12-FR-AB"
CASE_MISS = "SYN-W12-FR-INCOMPLETE"
OWN, TARGET = "SYN-OWN", "SYN-TGT"
EPOCH = "2026-01-01T00:00:00Z"
ORIGIN = {"latDeg": 31.0, "lonDeg": 121.0}
OPERATOR = "SyntheticPilot"
ROLE = "Investigator"

# Exact samples. Shared UTC instants are 00:00:10Z and 00:00:20Z only.
# No explicit gap marker; crossing a 6-7s hole is 未验.
OWN_ROWS = [
    ("2026-01-01T00:00:00Z", 31.000, 121.000, 10.0, 0.0),    # own only, t=0
    ("2026-01-01T00:00:10Z", 31.010, 121.000, 10.0, 0.0),    # common, t=10
    ("2026-01-01T00:00:20Z", 31.020, 121.000, 10.0, 0.0),    # common, t=20
    ("2026-01-01T00:00:30Z", 31.030, 121.000, 10.0, 0.0),    # own only, t=30
]
TGT_ROWS = [
    ("2026-01-01T00:00:10Z", 31.010, 121.050, 10.0, 270.0),  # common, t=10
    ("2026-01-01T00:00:20Z", 31.010, 121.040, 10.0, 270.0),  # common, t=20
    ("2026-01-01T00:00:40Z", 31.010, 121.030, 10.0, 270.0),  # target only, t=40
]
COMMON_TIMES = (10.0, 20.0)
OUTSIDE_TIMES = (0.0, 15.0, 30.0, 40.0)  # no exact pair at these instants
PROBE_TIME = 10.0

CSV_HEADER = "utc,latDeg,lonDeg,sogKn,sogStatus,cogDeg,cogStatus\n"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_sha(path: Path, expected: str, label: str) -> str:
    actual = sha256_file(path)
    if actual != expected:
        raise SystemExit(f"SHA mismatch for {label}: {actual} != {expected}")
    return actual


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def csv_bytes(rows: list[tuple]) -> bytes:
    body = CSV_HEADER + "".join(
        f"{utc},{lat},{lon},{sog},reported,{cog},reported\n" for utc, lat, lon, sog, cog in rows
    )
    return body.encode("utf-8")


def import_body(vessel_id: str, raw: bytes) -> dict[str, Any]:
    return {
        "profile": "mcis-utc-v1",
        "vesselId": vessel_id,
        "fileName": f"{vessel_id}.csv",
        "source": "synthetic W12 first-registered pilot; not a real case",
        "timeBasis": "declared synthetic UTC Z timestamps",
        "contentBase64": base64.b64encode(raw).decode("ascii"),
    }


def case_body(case_id: str) -> dict[str, Any]:
    return {
        "caseId": case_id,
        "schemaVersion": "1.0.0",
        "title": "Synthetic first-registered CPA pilot",
        "accidentType": "Collision",
        "incidentTimeUtc": EPOCH,
        "caseEpochUtc": EPOCH,
        "displayTimeZoneOffsetMinutes": 0,
        "incidentLocation": {**ORIGIN, "heightM": 0},
        "isFictionalDemo": True,
    }


class Http:
    def __init__(self, base: str):
        self.base = base.rstrip("/")

    def call(self, path: str, body: Any | None = None, method: str | None = None) -> tuple[int, Any]:
        headers = {"X-MCIS-Role": ROLE, "X-MCIS-Operator": OPERATOR}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw, status = resp.read(), resp.status
        except urllib.error.HTTPError as exc:
            raw, status = exc.read(), exc.code
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeError):
            parsed = raw.decode("utf-8", "replace")
        return status, parsed


def exact_times(points: list[dict[str, Any]]) -> dict[float, dict[str, Any]]:
    out: dict[float, dict[str, Any]] = {}
    for p in points:
        t = float(p["timeSec"])
        if t in out:
            raise ValueError(f"duplicate sample time {t}")
        out[t] = p
    return out


def pair_at(own_id: str, tgt_id: str, t: float, a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    def st(vid: str, p: dict[str, Any]) -> dict[str, Any]:
        return {
            "vesselId": vid,
            "latDeg": p["latDeg"],
            "lonDeg": p["lonDeg"],
            "speedKn": p["sogKn"],
            "courseDeg": p["cogDeg"],
        }

    return {"pairId": f"{own_id}|{tgt_id}@{t:g}", "timeSec": t, "own": st(own_id, a), "target": st(tgt_id, b)}


def capture_in_one_transaction(app, case_id: str, expected: list[str], digests: dict[str, str]) -> dict[str, Any]:
    """Load verified receipts and point arrays in one reserved SQLite transaction.

    Uses product load_receipt + track_points. Does not call state_at or GET /cpa.
    Missing vessel, missing receipt, or failed verification => no current analysis.
    """
    from mcis_service.common.context import Ctx
    from mcis_service.cases.service import track_points
    from mcis_service.db import WRITE_LOCK
    from mcis_service.reports.access import begin
    from mcis_service.tracks_import.router import authorize, load_receipt

    class _Req:
        def __init__(self, application):
            self.app = application

    ctx = Ctx(role=ROLE, operator=OPERATOR, request=_Req(app))
    result: dict[str, Any] = {
        "ok": False,
        "reason": None,
        "identities": {},
        "points": {},
        "commonTimes": [],
        "transaction": "WRITE_LOCK+BEGIN IMMEDIATE, read only",
    }
    with WRITE_LOCK, ctx.db.session() as session:
        begin(session)
        authorize(ctx, session, case_id)
        for vid in expected:
            digest = digests.get(vid)
            if not digest:
                result["reason"] = f"missing-receipt:{vid}"
                return result
            saved = load_receipt(ctx, session, case_id, digest)
            if saved is None:
                result["reason"] = f"receipt-not-found:{vid}"
                return result
            receipt = dict(saved[0])
            if receipt.get("vesselId") != vid or receipt.get("caseId") != case_id:
                result["reason"] = f"identity-mismatch:{vid}"
                return result
            pts = [dict(p) for p in track_points(session, case_id, vid)]
            if len(pts) != receipt.get("pointCount"):
                result["reason"] = f"point-count-mismatch:{vid}"
                return result
            if not pts:
                result["reason"] = f"no-points:{vid}"
                return result
            result["identities"][vid] = {
                "caseId": receipt["caseId"],
                "vesselId": receipt["vesselId"],
                "previewDigest": receipt["previewDigest"],
                "sourceSha256": receipt["sourceSha256"],
                "reportSha256": receipt["reportSha256"],
                "pointCount": receipt["pointCount"],
            }
            result["points"][vid] = pts
        own_map = exact_times(result["points"][expected[0]])
        tgt_map = exact_times(result["points"][expected[1]])
        result["commonTimes"] = sorted(set(own_map) & set(tgt_map))
        result["ok"] = True
        return result


def metrics_for_common_samples(identities: dict, points: dict, core_run, core_cmd: str, times: list[float]) -> dict[str, Any]:
    """Build pairs only from exact co-temporal samples; invoke official core twice."""
    own_map = exact_times(points[OWN])
    tgt_map = exact_times(points[TARGET])
    present = []
    missing = []
    for t in times:
        if t in own_map and t in tgt_map:
            present.append(t)
        else:
            missing.append(t)
    payload = {
        "origin": ORIGIN,
        "pairs": [pair_at(OWN, TARGET, t, own_map[t], tgt_map[t]) for t in present],
    }
    if not payload["pairs"]:
        return {
            "metrics": None,
            "reason": "no-exact-common-samples",
            "requestedTimes": times,
            "missingTimes": missing,
            "identities": identities,
        }
    first = core_run(core_cmd, "cpa", payload, timeout_s=60)
    second = core_run(core_cmd, "cpa", payload, timeout_s=60)
    recalculated = first == second
    return {
        "metrics": first.get("result"),
        "coreVersion": first.get("coreVersion"),
        "recalculatedIdentical": recalculated,
        "requestedTimes": times,
        "missingTimes": missing,
        "identities": identities,
        "payloadPairs": payload["pairs"],
        "rawFirst": first,
        "rawSecond": second,
    }


def start_service(app, host: str, port: int):
    import uvicorn

    config = uvicorn.Config(app, host=host, port=port, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="mcis-w12-fr-uvicorn", daemon=True)
    thread.start()
    deadline = time.time() + 20
    last = None
    while time.time() < deadline:
        if server.started:
            return server, thread
        last = "thread-alive" if thread.is_alive() else "thread-dead"
        time.sleep(0.05)
    raise RuntimeError(f"uvicorn failed to start on {host}:{port} ({last})")


def wait_health(http: Http) -> None:
    deadline = time.time() + 20
    last = None
    while time.time() < deadline:
        try:
            status, body = http.call("/health")
            if status == 200 and isinstance(body, dict) and body.get("status") == "ok":
                return
            last = (status, body)
        except Exception as exc:  # noqa: BLE001 — startup probe
            last = str(exc)
        time.sleep(0.05)
    raise RuntimeError(f"health check failed: {last}")


def create_and_import(http: Http, case_id: str, vessels: list[tuple[str, bytes]]) -> dict[str, str]:
    status, body = http.call("/cases", case_body(case_id), method="POST")
    if status != 201:
        raise RuntimeError(f"create case {case_id} failed: {status} {body}")
    for vid, _raw in vessels:
        status, body = http.call(f"/cases/{case_id}/vessels", {"vesselId": vid, "caseId": case_id, "name": f"Synthetic {vid}"}, method="POST")
        if status != 201:
            raise RuntimeError(f"create vessel {vid} failed: {status} {body}")
    digests: dict[str, str] = {}
    for vid, raw in vessels:
        payload = import_body(vid, raw)
        status, preview = http.call(f"/cases/{case_id}/track-imports:preview", payload)
        if status != 200 or not preview.get("canCommit"):
            raise RuntimeError(f"preview {vid} failed: {status} {preview}")
        status, commit = http.call(
            f"/cases/{case_id}/track-imports:commit",
            {**payload, "confirmed": True, "previewDigest": preview["previewDigest"]},
        )
        if status != 200 or commit.get("replayed") is not False:
            raise RuntimeError(f"commit {vid} failed: {status} {commit}")
        if commit.get("vesselId") != vid or commit.get("previewDigest") != preview["previewDigest"]:
            raise RuntimeError(f"commit identity mismatch {vid}: {commit}")
        digests[vid] = commit["previewDigest"]
    return digests


def record_item(out: Path, name: str, passed: bool, payload: dict[str, Any], command: str, exit_code: int) -> None:
    write_json(out / f"{name}.json", {
        "name": name,
        "passed": passed,
        "exitCode": exit_code,
        "command": command,
        "result": payload,
    })


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--core-dir", default="/workspace/mcis-w41-core-out")
    parser.add_argument("--dotnet", default=os.path.expanduser("~/.dotnet/dotnet"))
    parser.add_argument("--port", type=int, default=18774)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    worktree = Path(args.worktree).resolve()
    report = Path(args.report).resolve()
    official = report / "official"
    official.mkdir(parents=True, exist_ok=True)
    started = iso_now()
    log: list[str] = [f"start={started}", f"pin={PIN}", f"host={args.host}:{args.port}"]

    # Lock worktree pin + core sources/artifacts before any compute.
    import subprocess
    head_sha = subprocess.check_output(["git", "-C", str(worktree), "rev-parse", "HEAD"], text=True).strip()
    if not head_sha.startswith("03a8e786") and head_sha != PIN:
        # candidate will move after commit; during official run we accept 03a8e786 or later only-pilot diffs
        changed = subprocess.check_output(["git", "-C", str(worktree), "diff", "--name-only", PIN, "HEAD"], text=True).splitlines()
        unexpected = [n for n in changed if not n.startswith("tests_acceptance/w12-first-registered-pilot/")]
        if unexpected:
            print(f"worktree differs from pin outside pilot dir: {unexpected}", file=sys.stderr)
            return 2
    cpa_cs = require_sha(worktree / "tools/mcis-core/src/CpaCommand.cs", CPA_CS_SHA256, "CpaCommand.cs")
    core_dir = Path(args.core_dir).resolve()
    dll = require_sha(core_dir / "mcis-core.dll", CORE_DLL_SHA256, "mcis-core.dll")
    require_sha(core_dir / "mcis-core.runtimeconfig.json", CORE_RUNTIME_SHA256, "runtimeconfig")
    require_sha(core_dir / "mcis-core.deps.json", CORE_DEPS_SHA256, "deps")
    dotnet = Path(args.dotnet)
    if not dotnet.is_file():
        write_json(official / "breakpoint.json", {
            "firstBreakpoint": "dotnet missing",
            "path": str(dotnet),
        })
        print("首个断点：dotnet 不可用", file=sys.stderr)
        return 3
    dotnet_ver = subprocess.check_output([str(dotnet), "--version"], text=True).strip()

    service_root = worktree / "service"
    sys.path.insert(0, str(service_root))
    os.environ["MCIS_SEED_DEMO"] = "0"
    os.environ["MCIS_CORE_DLL"] = str(core_dir / "mcis-core.dll")
    os.environ["MCIS_DOTNET"] = str(dotnet)
    wrapper = Path(__file__).resolve().parent / "core_norebuild.sh"
    os.environ["MCIS_CORE"] = str(wrapper)
    os.environ.pop("HTTP_PROXY", None)
    os.environ.pop("HTTPS_PROXY", None)
    os.environ.pop("http_proxy", None)
    os.environ.pop("https_proxy", None)
    os.environ.pop("ALL_PROXY", None)

    from mcis_service.colreg import core_client
    from mcis_service.config import Settings
    from mcis_service.main import create_app

    # Preflight official core; do not invent a substitute.
    try:
        version_env = core_client.run(str(wrapper), "version", {}, timeout_s=30)
    except Exception as exc:  # noqa: BLE001
        write_json(official / "breakpoint.json", {
            "firstBreakpoint": "official mcis-core unavailable",
            "dll": str(core_dir / "mcis-core.dll"),
            "dllSha256": dll,
            "errorType": type(exc).__name__,
            "error": str(exc)[:400],
        })
        print(f"首个断点：原核心不可用（{type(exc).__name__}）", file=sys.stderr)
        traceback.print_exc()
        return 3
    write_json(official / "core-version.json", {"dotnet": dotnet_ver, "envelope": version_env, "dllSha256": dll, "cpaCommandSha256": cpa_cs})
    log.append(f"coreVersion={version_env.get('coreVersion')} dll={dll}")

    data_dir = Path(tempfile.mkdtemp(prefix="mcis-w12-fr-"))
    settings = Settings(
        data_dir=data_dir,
        db_url=f"sqlite:///{data_dir / 'mcis.db'}",
        seed_demo=False,
        core_cmd=str(wrapper),
        host=args.host,
        port=args.port,
    )
    if settings.host != "127.0.0.1" or args.host != "127.0.0.1":
        print("host must be 127.0.0.1", file=sys.stderr)
        return 2
    app = create_app(settings)
    server, thread = start_service(app, args.host, args.port)
    http = Http(f"http://{args.host}:{args.port}/api/v1")
    overall = 0
    results: dict[str, Any] = {}
    try:
        wait_health(http)
        log.append("health=ok")
        own_raw, tgt_raw = csv_bytes(OWN_ROWS), csv_bytes(TGT_ROWS)
        (official / "fixtures").mkdir(parents=True, exist_ok=True)
        (official / "fixtures" / "own.csv").write_bytes(own_raw)
        (official / "fixtures" / "target.csv").write_bytes(tgt_raw)

        digests_ok = create_and_import(http, CASE_OK, [(OWN, own_raw), (TARGET, tgt_raw)])
        digests_miss = create_and_import(http, CASE_MISS, [(OWN, own_raw)])
        # register the second vessel on the incomplete case but do not import a track
        status, body = http.call(
            f"/cases/{CASE_MISS}/vessels",
            {"vesselId": TARGET, "caseId": CASE_MISS, "name": f"Synthetic {TARGET}"},
            method="POST",
        )
        if status != 201:
            raise RuntimeError(f"incomplete-case second vessel failed: {status} {body}")
        write_json(official / "import-digests.json", {"complete": digests_ok, "incomplete": digests_miss})
        log.append(f"imported complete={digests_ok} incomplete={digests_miss}")

        capture = capture_in_one_transaction(app, CASE_OK, [OWN, TARGET], digests_ok)
        write_json(official / "capture-complete.json", {
            "ok": capture["ok"],
            "reason": capture["reason"],
            "identities": capture["identities"],
            "commonTimes": capture["commonTimes"],
            "pointTimes": {k: [p["timeSec"] for p in v] for k, v in capture["points"].items()},
            "transaction": capture["transaction"],
        })
        if not capture["ok"]:
            write_json(official / "breakpoint.json", {
                "firstBreakpoint": "same-transaction capture failed on complete case",
                "reason": capture["reason"],
            })
            print("首个断点：同一只读事务未能捕获两船已核验回执与点数组", file=sys.stderr)
            return 3
        if capture["commonTimes"] != list(COMMON_TIMES):
            raise AssertionError(f"unexpected common times {capture['commonTimes']}")

        # Item 1: one recalculable result inside common coverage.
        inside = metrics_for_common_samples(
            capture["identities"], capture["points"], core_client.run, str(wrapper), [PROBE_TIME],
        )
        item1_pass = bool(
            inside.get("metrics")
            and inside.get("recalculatedIdentical")
            and not inside.get("missingTimes")
            and set(inside["identities"]) == {OWN, TARGET}
            and inside["identities"][OWN]["previewDigest"] == digests_ok[OWN]
            and inside["identities"][TARGET]["previewDigest"] == digests_ok[TARGET]
        )
        record_item(official, "item1-inside-common", item1_pass, inside, "core_client.run cpa x2 at t=10 exact samples", 0 if item1_pass else 1)
        results["item1"] = item1_pass
        if not item1_pass:
            overall = 1

        # Item 2: outside common coverage, no metrics.
        outside = metrics_for_common_samples(
            capture["identities"], capture["points"], core_client.run, str(wrapper), list(OUTSIDE_TIMES),
        )
        item2_pass = outside.get("metrics") is None and set(outside.get("missingTimes") or []) == set(OUTSIDE_TIMES)
        record_item(official, "item2-outside-common", item2_pass, outside, "no core call; no exact common samples at 0/15/30/40", 0 if item2_pass else 1)
        results["item2"] = item2_pass
        if not item2_pass:
            overall = 1

        # Item 3: missing one vessel receipt => no current analysis.
        missing = capture_in_one_transaction(app, CASE_MISS, [OWN, TARGET], {OWN: digests_miss[OWN]})
        # Partial identity notes may exist for the ship that did have a receipt;
        # current analysis must still be withheld when the other receipt is missing.
        no_analysis = (not missing["ok"]) and str(missing.get("reason") or "").startswith("missing-receipt")
        item3_pass = no_analysis and "metrics" not in missing
        record_item(official, "item3-missing-receipt", item3_pass, {
            "ok": missing["ok"],
            "reason": missing["reason"],
            "identities": missing["identities"],
            "currentAnalysis": None,
            "metricsReturned": False,
        }, "same-transaction capture requiring both receipts on incomplete case", 0 if item3_pass else 1)
        results["item3"] = item3_pass
        if not item3_pass:
            overall = 1

        write_json(official / "summary.json", {
            "started": started,
            "finished": iso_now(),
            "pin": PIN,
            "head": head_sha,
            "host": f"{args.host}:{args.port}",
            "dataDir": str(data_dir),
            "coreDllSha256": dll,
            "coreVersion": version_env.get("coreVersion"),
            "items": results,
            "gapCrossing": "未验",
            "sameCaseVersionChange": "未验",
            "browser": "未验",
            "notWholeW12": True,
            "exitCode": overall,
        })
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        log.append(f"stop={iso_now()}")
        (official / "runner.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    print(json.dumps({"passed": overall == 0, "items": results, "exitCode": overall}, ensure_ascii=False))
    return overall


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
