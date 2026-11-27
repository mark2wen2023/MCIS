#!/usr/bin/env python3
"""Official isolated-assembly browser run for W12 explicit-gap chart breaks."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

CHROME = "/opt/google/chrome/chrome"
HERE = Path(__file__).resolve().parent
DEFAULT_WORKTREE = HERE.parents[1]
CASES = [
    {
        "id": "SYN-W12-CHART-GAP-67",
        "key": "gap-6-7",
        "probe": 6.5,
        "label": "cross-6-7",
        "grid": (5.0, 10.0),
        "keep_end": (6.0, 7.0),
        "gapped_speed": "合成船 A",
        "control_speed": "合成船 B",
        "control_point": 6.5,
    },
    {
        "id": "SYN-W12-CHART-GAP-EXP",
        "key": "gap-expanded-6-5s",
        "probe": 124.25,
        "label": "expanded-6-5s",
        "grid": (120.0, 130.0),
        "keep_end": (121.0, 127.5),
        "gapped_speed": "合成船 A（expanded）",
        "control_speed": "合成船 B（expanded）",
        "control_point": 125.0,
    },
    {
        "id": "SYN-W12-CHART-GAP-12",
        "key": "gap-1-2-offset",
        "probe": 1.5,
        "label": "offset-1-2",
        "grid": (0.0, 10.0),
        "keep_end": (1.0, 2.0),
        "gapped_speed": "合成缺轨船",
        "control_speed": "合成对照船",
        "control_point": 5.0,
    },
]


def log(logs: list[str], msg: str) -> None:
    line = msg
    logs.append(line)
    print(line, flush=True)


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wait_http(url: str, proc: subprocess.Popen, timeout: float) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise SystemExit(f"host exited early rc={proc.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError, socket.error):
            time.sleep(0.1)
    raise SystemExit(f"timeout waiting for {url}")


def http_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ensure_node_modules(worktree: Path, logs: list[str]) -> Path:
    dest = worktree / "web" / "node_modules"
    if dest.is_dir():
        log(logs, f"node_modules present at {dest}")
        return dest
    source = Path("/workspace/mcis-w12-narrow-cand/web/node_modules")
    lock_a = sha256(worktree / "web" / "package-lock.json")
    lock_b = sha256(source.parent / "package-lock.json")
    if lock_a != lock_b or lock_a != "e90ca8de08746df1b599de506be1f6d9fe35fa9a67d8a2e55371eed1130e69eb":
        raise SystemExit(f"package-lock mismatch, refusing to reuse node_modules: {lock_a} vs {lock_b}")
    dest.symlink_to(source)
    log(logs, f"symlinked node_modules -> {source} (lock {lock_a})")
    return dest


def build_assembly(worktree: Path, out: Path, logs: list[str]) -> Path:
    from build_cases import write_cases
    assembly = out / "assembly"
    if assembly.exists():
        shutil.rmtree(assembly)
    assembly.mkdir(parents=True)
    cases_path, cases_sha = write_cases(assembly)
    log(logs, f"cases.json sha256={cases_sha}")
    shutil.copy2(HERE / "assembly" / "index.html", assembly / "index.html")
    shutil.copy2(worktree / "web" / "src" / "analysis" / "analysis.css", assembly / "analysis.css")
    esbuild = worktree / "web" / "node_modules" / "esbuild" / "bin" / "esbuild"
    nm = worktree / "web" / "node_modules"
    cmd = [
        str(esbuild),
        str(HERE / "assembly" / "main.tsx"),
        "--bundle",
        f"--outfile={assembly / 'app.js'}",
        "--format=iife",
        "--platform=browser",
        "--jsx=automatic",
        f"--alias:react={nm / 'react'}",
        f"--alias:react-dom={nm / 'react-dom'}",
        f"--alias:react-dom/client={nm / 'react-dom/client'}",
        f"--alias:react/jsx-runtime={nm / 'react/jsx-runtime'}",
        f"--alias:echarts={nm / 'echarts'}",
        "--log-level=warning",
    ]
    log(logs, "esbuild " + " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(worktree / "web"), capture_output=True, text=True)
    if proc.returncode != 0:
        log(logs, proc.stdout)
        log(logs, proc.stderr)
        raise SystemExit(f"esbuild failed rc={proc.returncode}")
    if proc.stdout:
        log(logs, proc.stdout.strip())
    log(logs, f"assembly app.js sha256={sha256(assembly / 'app.js')} bytes={ (assembly / 'app.js').stat().st_size }")
    return assembly


def run_unit_tests(worktree: Path, out: Path, logs: list[str]) -> None:
    esbuild = worktree / "web" / "node_modules" / "esbuild" / "bin" / "esbuild"
    outfile = out / "analysis-chart-gap.test.cjs"
    cmd = [
        str(esbuild),
        str(worktree / "web" / "tests" / "analysis-chart-gap.test.ts"),
        "--bundle",
        "--platform=node",
        "--format=cjs",
        f"--outfile={outfile}",
        "--log-level=warning",
    ]
    log(logs, "unit esbuild " + " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(worktree / "web"), capture_output=True, text=True)
    if proc.returncode != 0:
        log(logs, proc.stderr)
        raise SystemExit("unit test bundle failed")
    node = shutil.which("node") or "/usr/bin/node"
    run = subprocess.run([node, str(outfile)], cwd=str(worktree / "web"), capture_output=True, text=True)
    log(logs, (run.stdout or "") + (run.stderr or ""))
    if run.returncode != 0:
        raise SystemExit(f"unit tests failed rc={run.returncode}")


def option_series(option: dict, name: str) -> list:
    for s in option.get("series") or []:
        if (s.get("name") if isinstance(s, dict) else None) == name:
            return s.get("data") or []
    # echarts getOption may nest names as arrays
    for s in option.get("series") or []:
        n = s.get("name") if isinstance(s, dict) else None
        if isinstance(n, list) and name in n:
            return s.get("data") or []
        if n == name:
            return s.get("data") or []
    return []


def has_null_between(data: list, t0: float, t1: float) -> bool:
    idx = []
    for i, p in enumerate(data):
        if isinstance(p, (list, tuple)) and len(p) >= 1 and p[0] == t0:
            idx.append(i)
        if isinstance(p, (list, tuple)) and len(p) >= 1 and p[0] == t1:
            idx.append(i)
    if len(idx) < 2:
        return False
    a, b = idx[0], idx[-1]
    lo, hi = min(a, b), max(a, b)
    return any(data[i] is None for i in range(lo, hi + 1))


def point_value(data: list, t: float):
    for p in data:
        if isinstance(p, (list, tuple)) and len(p) >= 2 and p[0] == t:
            return p[1]
    return "MISSING"


def find_series(option: dict, name: str) -> list:
    data = option_series(option, name)
    if data:
        return data
    # Official export is the option passed to setOption, names are strings.
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--worktree", type=Path, default=DEFAULT_WORKTREE)
    parser.add_argument("--browser", type=Path, default=Path(CHROME))
    parser.add_argument("--port", type=int, default=18776)
    args = parser.parse_args()

    worktree = args.worktree.resolve()
    report = args.report.resolve()
    official = report / "official"
    shots = official / "shots"
    logs: list[str] = []
    official.mkdir(parents=True, exist_ok=True)
    shots.mkdir(parents=True, exist_ok=True)

    started = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    log(logs, f"official start {started}")
    log(logs, f"worktree={worktree} port={args.port}")

    sums = subprocess.run(["sha256sum", "-c", "SHA256SUMS"], cwd=str(HERE), capture_output=True, text=True)
    log(logs, sums.stdout.strip())
    if sums.returncode != 0:
        log(logs, sums.stderr)
        raise SystemExit("fixture SHA256SUMS failed")

    ensure_node_modules(worktree, logs)
    run_unit_tests(worktree, official, logs)
    assembly = build_assembly(worktree, official, logs)

    from live_seed import write_seed
    store = official / "tmp-store"
    if store.exists():
        shutil.rmtree(store)
    store.mkdir()
    seed, sidecar, seed_sha = write_seed(official / "live-seed")
    log(logs, f"live entry seed sha256={seed_sha}")

    host_cmd = [
        str(Path(args.python)),
        "-I", "-B",
        str(HERE / "host.py"),
        str(official / "unused-assets"),
        str(store),
        str(seed),
        str(sidecar),
        str(assembly),
        "127.0.0.1",
        str(args.port),
        str(worktree / "service"),
    ]
    log(logs, "host " + " ".join(host_cmd))
    env = {k: v for k, v in os.environ.items()
           if k not in {"HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY"}
           and not k.startswith("MCIS_")}
    host = subprocess.Popen(
        host_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    origin = f"http://127.0.0.1:{args.port}"
    results: dict = {"cases": {}, "liveEntry": None, "ok": False}
    try:
        wait_http(origin + "/assembly/", host, 20)
        log(logs, "assembly host ready")
        live = http_json(origin + "/api/v1/cases/SYN-W12-LIVE-ENTRY/analysis")
        write_json(official / "live-entry-analysis.json", live)
        has_gaps = "declaredOpenGaps" in live and live["declaredOpenGaps"]
        results["liveEntry"] = {
            "caseId": live.get("caseId"),
            "hasDeclaredOpenGapsField": "declaredOpenGaps" in live,
            "declaredOpenGaps": live.get("declaredOpenGaps", None),
            "ok": live.get("caseId") == "SYN-W12-LIVE-ENTRY" and not has_gaps,
        }
        if not results["liveEntry"]["ok"]:
            raise SystemExit("live analysis entry unexpectedly carries declared gaps")
        log(logs, "live /analysis entry has no declaredOpenGaps")

        from playwright.sync_api import sync_playwright, expect

        safe_env = {k: v for k, v in env.items()}
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                executable_path=str(args.browser),
                headless=True,
                chromium_sandbox=True,
                env=safe_env,
                args=["--no-proxy-server"],
            )
            try:
                context = browser.new_context(
                    viewport={"width": 1280, "height": 900},
                    device_scale_factor=1,
                    service_workers="block",
                )

                def route(r):
                    target = urlsplit(r.request.url)
                    if r.request.url.startswith("data:"):
                        r.continue_()
                        return
                    if not (target.scheme in {"http", "ws"} and target.hostname == "127.0.0.1" and target.port == args.port):
                        r.abort()
                        return
                    r.continue_()

                context.route("**/*", route)
                page = context.new_page()
                page.set_default_timeout(15000)
                page.goto(origin + "/assembly/", wait_until="domcontentloaded")
                expect(page.locator('[data-testid="w12-chart-gap-assembly"]')).to_be_visible()
                page.wait_for_function("() => document.querySelectorAll('canvas').length >= 1")

                for spec in CASES:
                    log(logs, f"case {spec['id']}")
                    page.locator(f'[data-testid="assembly-switcher"] [data-case="{spec["id"]}"]').click()
                    expect(page.locator('[data-testid="w12-chart-gap-assembly"]')).to_have_attribute("data-case", spec["id"])
                    page.wait_for_function(
                        """(id) => {
                          const ex = window.__W12_CHART_GAP_EXPORT__;
                          return !!(ex && ex.caseId === id && ex.curve && ex.speed);
                        }""",
                        arg=spec["id"],
                    )
                    export = page.evaluate("() => window.__W12_CHART_GAP_EXPORT__")
                    write_json(official / "options" / f"{spec['label']}-export.json", export)
                    curve = export["curve"]
                    speed = export["speed"]
                    dist = find_series(curve, "两船距离 D(t)")
                    dcpa = find_series(curve, "DCPA(t)")
                    tcpa = find_series(curve, "TCPA(t)")
                    g0, g1 = spec["grid"]
                    e0, e1 = spec["keep_end"]
                    checks = {
                        "distanceNullBetweenGrid": has_null_between(dist, g0, g1),
                        "dcpaNullBetweenGrid": has_null_between(dcpa, g0, g1),
                        "tcpaNullBetweenGrid": has_null_between(tcpa, g0, g1),
                        "connectNullsFalse": all(
                            (s.get("connectNulls") is False) for s in (curve.get("series") or []) if isinstance(s, dict)
                        ),
                    }
                    # Endpoints kept on speed of the gapped ship when present in that series.
                    gapped = find_series(speed, spec["gapped_speed"])
                    control = find_series(speed, spec["control_speed"])
                    checks["gappedSpeedBroken"] = None in gapped
                    checks["controlSpeedUnbroken"] = None not in control
                    if spec["label"] == "cross-6-7":
                        checks["endpoint6"] = point_value(gapped, 6.0) == 5.5
                        checks["endpoint7"] = point_value(gapped, 7.0) == 5.5
                        checks["controlAt65"] = point_value(control, 6.5) == 5.5
                        checks["distanceKeeps6"] = point_value(dist, 6.0) not in (None, "MISSING")
                        checks["distanceKeeps7"] = point_value(dist, 7.0) not in (None, "MISSING")
                        checks["distanceInteriorNull"] = point_value(dist, 6.5) in (None,)
                    if spec["label"] == "expanded-6-5s":
                        checks["grid125NotZero"] = point_value(dist, 125.0) in (None, "MISSING")
                        checks["distance120"] = point_value(dist, 120.0) not in (None, "MISSING")
                        checks["distance130"] = point_value(dist, 130.0) not in (None, "MISSING")
                        checks["noPairAt121"] = point_value(dist, 121.0) in (None, "MISSING")
                        checks["controlAt125"] = point_value(control, 125.0) not in (None, "MISSING")
                    if spec["label"] == "offset-1-2":
                        checks["endpoint1speed"] = point_value(gapped, 1.0) == 8.0
                        checks["endpoint2speed"] = point_value(gapped, 2.0) == 8.0
                        checks["controlAt5"] = point_value(control, 5.0) == 9.0
                        checks["pairAt0"] = point_value(dist, 0.0) not in (None, "MISSING")
                        checks["pairAt10"] = point_value(dist, 10.0) not in (None, "MISSING")
                        checks["interiorNull"] = point_value(dist, 1.5) in (None,)

                    shot_curve = shots / f"{spec['label']}-curve.png"
                    page.locator('[data-testid="curve-chart"]').screenshot(path=str(shot_curve))
                    shot_speed = shots / f"{spec['label']}-speed.png"
                    page.locator('[data-testid="speed-chart"]').screenshot(path=str(shot_speed))
                    shot_full = shots / f"{spec['label']}-fullpage.png"
                    page.screenshot(path=str(shot_full), full_page=True)

                    tip = page.evaluate(
                        """(t) => {
                          const el = document.querySelector('[data-testid="curve-chart"]');
                          const inst = el && el.__echartsInstance;
                          if (!inst) return {ok:false, text:''};
                          const x = inst.convertToPixel({xAxisIndex:0}, t);
                          const y = Math.max(40, (el.clientHeight || 200) / 3);
                          inst.dispatchAction({type:'showTip', x, y});
                          return {ok:true, x, y};
                        }""",
                        spec["probe"],
                    )
                    page.wait_for_timeout(200)
                    tip_text = page.evaluate(
                        """() => {
                          const node = document.querySelector('.w12-gap-tooltip');
                          return node ? (node.innerText || node.textContent || '') : '';
                        }"""
                    )
                    shot_tip = shots / f"{spec['label']}-tooltip.png"
                    page.screenshot(path=str(shot_tip), full_page=False)
                    checks["tooltipOk"] = bool(tip.get("ok"))
                    checks["tooltipHasNoMetricPhrase"] = "缺口内无指标" in (tip_text or "")
                    # Fabricated zeros or numeric pair metrics must not appear inside the gap tooltip.
                    lowered = (tip_text or "")
                    checks["tooltipHasNoNumericMetric"] = not any(
                        tok in lowered for tok in ("0.000", "DCPA(t): 0", "D(t): 0", "TCPA(t): 0")
                    ) and "缺口内无指标" in lowered and "DCPA(t):" not in lowered and "两船距离" not in lowered

                    canvas_b64 = page.evaluate(
                        """() => {
                          const c = document.querySelector('[data-testid="curve-chart"] canvas');
                          return c ? c.toDataURL('image/png') : '';
                        }"""
                    )
                    if canvas_b64.startswith("data:image/png;base64,"):
                        import base64
                        (official / "canvas" / f"{spec['label']}-curve.png").parent.mkdir(parents=True, exist_ok=True)
                        (official / "canvas" / f"{spec['label']}-curve.png").write_bytes(
                            base64.b64decode(canvas_b64.split(",", 1)[1])
                        )

                    ok = all(bool(v) for v in checks.values())
                    results["cases"][spec["id"]] = {
                        "ok": ok,
                        "checks": checks,
                        "tooltip": tip_text,
                        "probe": spec["probe"],
                        "shots": {
                            "curve": str(shot_curve),
                            "speed": str(shot_speed),
                            "fullpage": str(shot_full),
                            "tooltip": str(shot_tip),
                        },
                    }
                    log(logs, f"  checks={json.dumps(checks, ensure_ascii=False)} tooltip={tip_text!r} ok={ok}")
                    if not ok:
                        raise SystemExit(f"case {spec['id']} failed")
            finally:
                browser.close()
        results["ok"] = True
    finally:
        if host.poll() is None:
            host.terminate()
            try:
                out, _ = host.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                host.kill()
                out, _ = host.communicate(timeout=5)
        else:
            out = host.stdout.read() if host.stdout else ""
        (official / "host-log.txt").write_text(out or "", encoding="utf-8")
        log(logs, f"host exit={host.returncode}")

    ended = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    results["started"] = started
    results["ended"] = ended
    results["port"] = args.port
    results["origin"] = origin
    write_json(official / "summary.json", results)
    (official / "run.log").write_text("\n".join(logs) + "\n", encoding="utf-8")
    log(logs, f"official end {ended} ok={results['ok']}")
    return 0 if results["ok"] else 1


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    try:
        raise SystemExit(main())
    except SystemExit as e:
        raise
    except Exception as exc:
        print(f"UNCAUGHT {type(exc).__name__}: {exc}", flush=True)
        raise
