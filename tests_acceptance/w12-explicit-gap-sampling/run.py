"""W12 explicit short-gap sampling contrast. Fixtures are byte-identical to 2048c60."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PIN_W12 = "03a8e7867fedbaaabbf8dd12fc9041d6a1a74cd5"
PIN_FIXTURE = "2048c60fd6650c6f2c99a76a16be463a3895655d"
SHA_A = "a8f9109a33b8c80a6c41219473186e69c16fd59ee64ff325a5559c190028bb1c"
SHA_B = "07e043fc227770b6aaa6f1b15a6118e46b85a52e5638ac1b514e9269c6b159ca"
CORE_DLL_SHA256 = "f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf"
CORE_RUNTIME_SHA256 = "3d25821758613e4cd940d143ccb03c93704140077e69104996832510f38f6598"
CORE_DEPS_SHA256 = "fda133109cf9fc926cbda09598ad344f75dc57ec02e345b6923ec5fe2dff9d12"
CPA_CS_SHA256 = "54de148e91e27a4ca39c693410722e42caf88fcb58e339dc3907161dc9210d6c"

EPOCH = datetime.fromisoformat("2026-02-01T12:00:00.000+00:00")
ORIGIN = {"latDeg": -40.0, "lonDeg": -130.0}  # fixture design origin; South Pacific schematic
QUERIES = (120.0, 121.0, 124.250, 127.500, 130.0)
CORE_TIMES = (120.0, 130.0)  # strict same-instant measured positive control
VESSEL_A = "SYN-VESSEL-A"
VESSEL_B = "SYN-VESSEL-B"


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


def parse_utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def tsec(text: str) -> float:
    return (parse_utc(text) - EPOCH).total_seconds()


def aligned(p: dict[str, Any]) -> str:
    return p["time"]["alignedUtc"]


def load_vessel(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def exact_map(doc: dict[str, Any]) -> dict[float, dict[str, Any]]:
    out: dict[float, dict[str, Any]] = {}
    for p in doc["points"]:
        t = tsec(aligned(p))
        if t in out:
            raise SystemExit(f"duplicate aligned time {t} in {doc['vessel']['vesselId']}")
        out[t] = p
    return out


def gaps(doc: dict[str, Any]) -> list[tuple[float, float, str, str]]:
    rows = []
    for item in doc["sampling"].get("missingIntervals") or []:
        rows.append((tsec(item["startUtc"]), tsec(item["endUtc"]), item["startUtc"], item["endUtc"]))
    return rows


def inside_open_gap(t: float, intervals: list[tuple[float, float, str, str]]) -> tuple[float, float, str, str] | None:
    for lo, hi, su, eu in intervals:
        if lo < t < hi:
            return lo, hi, su, eu
    return None


def neighbors(t: float, times: list[float]) -> tuple[float | None, float | None]:
    prevs = [x for x in times if x < t - 1e-12]
    nexts = [x for x in times if x > t + 1e-12]
    return (max(prevs) if prevs else None, min(nexts) if nexts else None)


def field_view(p: dict[str, Any] | None) -> dict[str, Any] | None:
    if p is None:
        return None
    pos = p["position"]
    return {
        "pointId": p["pointId"],
        "alignedUtc": aligned(p),
        "timeStatus": p["time"]["status"],
        "correctionSeconds": p["time"]["correctionSeconds"],
        "sourceUtc": p["time"]["sourceUtc"],
        "positionKind": pos["kind"],
        "latDeg": None if pos["value"] is None else pos["value"]["latDeg"],
        "lonDeg": None if pos["value"] is None else pos["value"]["lonDeg"],
        "headingKind": p["headingDeg"]["kind"],
        "headingDeg": p["headingDeg"]["value"],
        "courseKind": p["courseDeg"]["kind"],
        "courseDeg": p["courseDeg"]["value"],
        "speedKind": p["speedKn"]["kind"],
        "speedKn": p["speedKn"]["value"],
    }


def cpa_inputs_ok(view: dict[str, Any] | None) -> bool:
    if view is None:
        return False
    if view["positionKind"] != "recorded":
        return False
    if view["latDeg"] is None or view["lonDeg"] is None:
        return False
    if view["courseKind"] != "recorded" or view["courseDeg"] is None:
        return False
    if view["speedKind"] != "recorded" or view["speedKn"] is None:
        return False
    return True


def classify(t: float, doc: dict[str, Any]) -> dict[str, Any]:
    by = exact_map(doc)
    intervals = gaps(doc)
    times = sorted(by)
    hit = next((by[x] for x in by if abs(x - t) < 1e-9), None)
    gap = inside_open_gap(t, intervals)
    prev, nxt = neighbors(t, times)
    base = {
        "vesselId": doc["vessel"]["vesselId"],
        "t": t,
        "alignedUtc": (EPOCH.tzinfo and (EPOCH).isoformat()) or None,
        "queryUtc": (EPOCH + __import__("datetime").timedelta(seconds=t)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "exactPoint": field_view(hit),
        "prevExactT": prev,
        "nextExactT": nxt,
        "declaredGapContaining": None if gap is None else {"startT": gap[0], "endT": gap[1], "startUtc": gap[2], "endUtc": gap[3]},
    }
    if hit is not None and hit["position"]["kind"] == "recorded":
        note = "原始实测（合成 recorded，非真实观测认证）"
        if hit["headingDeg"]["kind"] == "missing" or hit["headingDeg"]["value"] is None:
            note += "；艏向缺失，不补值，COG 不代替 HDG"
        return {**base, "status": "原始实测", "note": note, "usableAsMeasuredInput": cpa_inputs_ok(base["exactPoint"])}
    if hit is not None and hit["position"]["kind"] == "interpolated":
        return {**base, "status": "契约已有插值点", "note": "源中已标记 interpolated，不是本轮新插值", "usableAsMeasuredInput": False}
    if gap is not None:
        return {
            **base,
            "status": "缺口内部不可用",
            "note": f"显式开区间 ({gap[0]}, {gap[1]}) 内部无样位，禁止跨缺口插值，不给出位置/间距/DCPA/TCPA",
            "usableAsMeasuredInput": False,
        }
    if prev is not None and nxt is not None:
        mid = inside_open_gap((prev + nxt) / 2.0, intervals)
        if mid is None:
            return {
                **base,
                "status": "按契约派生区段",
                "note": f"无精确原始点，落在 {prev}–{nxt} 有效采样之间；可按契约派生，不能称为实测；本轮不产出派生坐标",
                "usableAsMeasuredInput": False,
            }
        return {**base, "status": "缺口内部不可用", "note": "相邻点跨越声明缺口", "usableAsMeasuredInput": False}
    return {**base, "status": "无覆盖", "note": "查询时刻前后没有可用原始点", "usableAsMeasuredInput": False}


def pair_at(t: float, a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    def st(vid: str, view: dict[str, Any]) -> dict[str, Any]:
        return {
            "vesselId": vid,
            "latDeg": view["latDeg"],
            "lonDeg": view["lonDeg"],
            "speedKn": view["speedKn"],
            "courseDeg": view["courseDeg"],
        }

    va, vb = a["exactPoint"], b["exactPoint"]
    return {"pairId": f"{VESSEL_A}|{VESSEL_B}@{t:g}", "timeSec": t, "own": st(VESSEL_A, va), "target": st(VESSEL_B, vb)}


def start_service(app, host: str, port: int):
    import uvicorn

    config = uvicorn.Config(app, host=host, port=port, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="mcis-w12-gap-uvicorn", daemon=True)
    thread.start()
    deadline = time.time() + 20
    while time.time() < deadline:
        if server.started:
            return server, thread
        time.sleep(0.05)
    raise RuntimeError(f"uvicorn failed to start on {host}:{port}")


def wait_health(host: str, port: int) -> None:
    url = f"http://{host}:{port}/api/v1/health"
    deadline = time.time() + 20
    last = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                body = json.loads(resp.read().decode())
                if resp.status == 200 and body.get("status") == "ok":
                    return
                last = body
        except Exception as exc:  # noqa: BLE001
            last = str(exc)
        time.sleep(0.05)
    raise RuntimeError(f"health failed: {last}")


def recount_times(doc: dict[str, Any]) -> list[float]:
    return [tsec(aligned(p)) for p in doc["points"]]


EXPECTED_A = [0, 10, 20, 30, 40, 50, 60, 100, 110, 120, 121, 127.5, 130, 140, 150, 160, 170, 180, 190, 200, 210, 220]
EXPECTED_B = [0, 10, 20, 30, 40, 50, 60, 65, 70, 80, 90, 95, 100, 110, 120, 125, 130, 140, 150, 160, 170, 180, 190, 200, 210, 220]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--core-dir", default="/workspace/mcis-w41-core-out")
    parser.add_argument("--dotnet", default=os.path.expanduser("~/.dotnet/dotnet"))
    parser.add_argument("--port", type=int, default=18775)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    if args.host != "127.0.0.1":
        print("host must be 127.0.0.1", file=sys.stderr)
        return 2

    worktree = Path(args.worktree).resolve()
    report = Path(args.report).resolve()
    official = report / "official"
    official.mkdir(parents=True, exist_ok=True)
    started = iso_now()
    fixtures = Path(__file__).resolve().parent / "fixtures"
    sha_a = require_sha(fixtures / "vessel-a.json", SHA_A, "vessel-a.json")
    sha_b = require_sha(fixtures / "vessel-b.json", SHA_B, "vessel-b.json")

    head = subprocess.check_output(["git", "-C", str(worktree), "rev-parse", "HEAD"], text=True).strip()
    if head != PIN_W12:
        changed = subprocess.check_output(["git", "-C", str(worktree), "diff", "--name-only", PIN_W12, "HEAD"], text=True).splitlines()
        unexpected = [n for n in changed if not n.startswith("tests_acceptance/w12-explicit-gap-sampling/")]
        if unexpected:
            print("worktree differs from pin outside pilot dir: " + ", ".join(unexpected), file=sys.stderr)
            return 2

    require_sha(worktree / "tools/mcis-core/src/CpaCommand.cs", CPA_CS_SHA256, "CpaCommand.cs")
    core_dir = Path(args.core_dir).resolve()
    dll = require_sha(core_dir / "mcis-core.dll", CORE_DLL_SHA256, "mcis-core.dll")
    require_sha(core_dir / "mcis-core.runtimeconfig.json", CORE_RUNTIME_SHA256, "runtimeconfig")
    require_sha(core_dir / "mcis-core.deps.json", CORE_DEPS_SHA256, "deps")
    dotnet = Path(args.dotnet)
    if not dotnet.is_file():
        write_json(official / "breakpoint.json", {"firstBreakpoint": "dotnet missing", "path": str(dotnet)})
        print("首个断点：dotnet 不可用", file=sys.stderr)
        return 3

    dotnet_ver = subprocess.check_output([str(dotnet), "--version"], text=True).strip()
    wrapper = Path(__file__).resolve().parent / "core_norebuild.sh"
    os.environ["MCIS_CORE_DLL"] = str(core_dir / "mcis-core.dll")
    os.environ["MCIS_DOTNET"] = str(dotnet)
    os.environ["MCIS_CORE"] = str(wrapper)
    os.environ["MCIS_SEED_DEMO"] = "0"
    for k in ("MCIS_API", "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY"):
        os.environ.pop(k, None)

    sys.path.insert(0, str(worktree / "service"))
    from mcis_service.colreg import core_client
    from mcis_service.config import Settings
    from mcis_service.main import create_app

    try:
        version_env = core_client.run(str(wrapper), "version", {}, timeout_s=30)
    except Exception as exc:  # noqa: BLE001
        write_json(official / "breakpoint.json", {
            "firstBreakpoint": "official mcis-core unavailable",
            "dllSha256": dll,
            "errorType": type(exc).__name__,
            "error": str(exc)[:400],
        })
        print(f"首个断点：原核心不可用（{type(exc).__name__}）", file=sys.stderr)
        traceback.print_exc()
        return 3
    write_json(official / "core-version.json", {"dotnet": dotnet_ver, "envelope": version_env, "dllSha256": dll})

    doc_a = load_vessel(fixtures / "vessel-a.json")
    doc_b = load_vessel(fixtures / "vessel-b.json")
    times_a, times_b = recount_times(doc_a), recount_times(doc_b)
    times_ok = times_a == [float(x) for x in EXPECTED_A] and times_b == [float(x) for x in EXPECTED_B]
    write_json(official / "utc-recount.json", {
        "fixturePin": PIN_FIXTURE,
        "sha256": {"vessel-a.json": sha_a, "vessel-b.json": sha_b},
        "caseId": doc_a.get("caseId"),
        "epoch": "2026-02-01T12:00:00.000Z",
        "A": times_a,
        "B": times_b,
        "matchesReadmeAndDot": times_ok,
        "A_missingIntervals": doc_a["sampling"]["missingIntervals"],
        "B_missingIntervals": doc_b["sampling"]["missingIntervals"],
        "dotAgreement": {
            "A_has_recorded_position_at_121_and_127_5": True,
            "A_124_250_in_open_gap": True,
            "B_no_exact_point_at_121_124_250_127_5": True,
            "B_121_and_124_250_between_120_125": True,
            "B_127_5_between_125_130": True,
            "both_have_recorded_position_cog_sog_at_120_and_130": True,
        },
    })
    if not times_ok:
        print("UTC 点列与 README/Dot 复算不一致", file=sys.stderr)
        return 1

    rows = []
    for t in QUERIES:
        ca, cb = classify(t, doc_a), classify(t, doc_b)
        both_measured = ca["usableAsMeasuredInput"] and cb["usableAsMeasuredInput"]
        metrics_policy = (
            "给出间距/DCPA/TCPA：两船均为原始实测且具备位置、COG、航速"
            if both_measured
            else "不给出间距/DCPA/TCPA：至少一船不是该时刻的精确原始实测点（不补值、不派生后送核心）"
        )
        core_called = t in CORE_TIMES and both_measured
        rows.append({
            "t": t,
            "queryUtc": ca["queryUtc"],
            "A": ca,
            "B": cb,
            "pairMetrics": "yes-core" if core_called else "none",
            "metricsPolicy": metrics_policy,
        })

    # Official core only on strict same-instant measured controls.
    core_calls = []
    passed_core = True
    for t in CORE_TIMES:
        ca, cb = classify(t, doc_a), classify(t, doc_b)
        if not (ca["usableAsMeasuredInput"] and cb["usableAsMeasuredInput"]):
            passed_core = False
            core_calls.append({"t": t, "skipped": True, "reason": "missing measured CPA inputs"})
            continue
        payload = {"origin": ORIGIN, "pairs": [pair_at(t, ca, cb)]}
        first = core_client.run(str(wrapper), "cpa", payload, timeout_s=60)
        second = core_client.run(str(wrapper), "cpa", payload, timeout_s=60)
        identical = first == second
        ok = bool(first.get("ok") and identical and (first.get("result") or {}).get("results"))
        if not ok:
            passed_core = False
        core_calls.append({
            "t": t,
            "queryUtc": ca["queryUtc"],
            "command": "mcis-core cpa (core_client.run, twice)",
            "payload": payload,
            "coreVersion": first.get("coreVersion"),
            "recalculatedIdentical": identical,
            "result": first.get("result"),
            "rawFirst": first,
            "rawSecond": second,
            "passed": ok,
        })
        # attach metrics onto the status row
        for row in rows:
            if row["t"] == t:
                row["core"] = {
                    "coreVersion": first.get("coreVersion"),
                    "recalculatedIdentical": identical,
                    "results": (first.get("result") or {}).get("results"),
                }

    write_json(official / "per-time-status.json", {
        "curve": "未验（本轮只测点；若输出曲线，T+120 与 T+130 之间必须断段，不得因两端有效而连线）",
        "sameCaseVersionChange": "未验",
        "browser": "未验",
        "rows": rows,
    })
    write_json(official / "core-calls.json", {
        "dllSha256": dll,
        "coreVersion": version_env.get("coreVersion"),
        "origin": ORIGIN,
        "calls": core_calls,
    })

    # Loopback service envelope (temp SQLite); analysis itself uses locked JSON + official core, not GET /cpa.
    data_dir = Path(tempfile.mkdtemp(prefix="mcis-w12-gap-"))
    settings = Settings(data_dir=data_dir, db_url=f"sqlite:///{data_dir / 'mcis.db'}", seed_demo=False, core_cmd=str(wrapper), host=args.host, port=args.port)
    app = create_app(settings)
    server, thread = start_service(app, args.host, args.port)
    health_ok = False
    try:
        wait_health(args.host, args.port)
        health_ok = True
    finally:
        server.should_exit = True
        thread.join(timeout=5)

    item_status = all(r["A"]["status"] and r["B"]["status"] for r in rows)
    # Expected contract distinctions
    expect = {
        120.0: ("原始实测", "原始实测", "yes-core"),
        121.0: ("原始实测", "按契约派生区段", "none"),
        124.250: ("缺口内部不可用", "按契约派生区段", "none"),
        127.500: ("原始实测", "按契约派生区段", "none"),
        130.0: ("原始实测", "原始实测", "yes-core"),
    }
    expect_ok = True
    for row in rows:
        ev = expect[row["t"]]
        if (row["A"]["status"], row["B"]["status"], row["pairMetrics"]) != ev:
            expect_ok = False
    overall = 0 if (times_ok and expect_ok and passed_core and health_ok and item_status) else 1
    write_json(official / "summary.json", {
        "started": started,
        "finished": iso_now(),
        "pin": PIN_W12,
        "fixturePin": PIN_FIXTURE,
        "head": head,
        "host": f"{args.host}:{args.port}",
        "health": health_ok,
        "dataDir": str(data_dir),
        "fixtureSha256": {"vessel-a.json": sha_a, "vessel-b.json": sha_b},
        "coreDllSha256": dll,
        "coreVersion": version_env.get("coreVersion"),
        "timesMatchDot": times_ok,
        "statusMatchContract": expect_ok,
        "corePositiveControl": passed_core,
        "curve": "未验",
        "gapCrossingClaim": "未验（不宣称可跨或修复 6–7 秒缺口；本轮只按契约区分点状态）",
        "notWholeW12": True,
        "exitCode": overall,
    })
    print(json.dumps({
        "passed": overall == 0,
        "timesMatchDot": times_ok,
        "statusMatchContract": expect_ok,
        "corePositiveControl": passed_core,
        "health": health_ok,
        "exitCode": overall,
    }, ensure_ascii=False))
    return overall


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
