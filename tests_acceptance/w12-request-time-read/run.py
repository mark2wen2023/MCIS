#!/usr/bin/env python3
"""Official sandboxed Chrome: request-time authorized/denied snapshot assembly."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
SIBLING = HERE.parent / "w12-registered-json-gap"
DEFAULT_WORKTREE = HERE.parents[1]
CHROME = "/opt/google/chrome/chrome"
CORE_DLL_SHA256 = "f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf"
CORE_RUNTIME_SHA256 = "3d25821758613e4cd940d143ccb03c93704140077e69104996832510f38f6598"
CORE_DEPS_SHA256 = "fda133109cf9fc926cbda09598ad344f75dc57ec02e345b6923ec5fe2dff9d12"
CPA_CS_SHA256 = "54de148e91e27a4ca39c693410722e42caf88fcb58e339dc3907161dc9210d6c"
WRAPPER_SHA256 = "a19eea96864ef424ea9cd1a3541b1c845791d2fd2bb52a2f65b5bff9684096a8"
LOCK_SHA = "e90ca8de08746df1b599de506be1f6d9fe35fa9a67d8a2e55371eed1130e69eb"
EXPECTED = {
    120.0: {"distanceNm": 1.070062, "dcpaNm": 0.000226, "tcpaMin": 2.918352},
    130.0: {"distanceNm": 1.008757, "dcpaNm": 0.000213, "tcpaMin": 2.751155},
}
ROLE_HEADER = "X-W12-Synthetic-Role-Context"
ROLE_AUTHORIZED = "synthetic-authorized-reader"
ROLE_DENIED = "synthetic-denied-reader"
NODE_MODULES_FALLBACKS = [
    Path("/workspace/mcis-w12-json-gap-cand/web/node_modules"),
    Path("/workspace/mcis-w12-narrow-cand/web/node_modules"),
]


def log(logs: list[str], msg: str) -> None:
    logs.append(msg)
    print(msg, flush=True)


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_sha(path: Path, expected: str, label: str) -> str:
    actual = sha256(path)
    if actual != expected:
        raise SystemExit(f"SHA mismatch for {label}: {actual} != {expected}")
    return actual


def json_strict(obj):
    if obj is True or obj is False or obj is None:
        return obj
    if isinstance(obj, int) and not isinstance(obj, bool):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return {str(k): json_strict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_strict(v) for v in obj]
    return None


def export_needed_option(option: dict) -> dict:
    series_out = []
    for s in option.get("series") or []:
        if not isinstance(s, dict):
            continue
        series_out.append(json_strict({
            "name": s.get("name"), "type": s.get("type"), "showSymbol": s.get("showSymbol"),
            "connectNulls": s.get("connectNulls"), "symbol": s.get("symbol"),
            "symbolSize": s.get("symbolSize"), "data": s.get("data"),
        }))
    return {"series": series_out}


def series_value(point):
    if point is None or point == "-":
        return None
    if isinstance(point, (int, float)):
        return point
    if isinstance(point, list) and len(point) >= 2:
        return point[1]
    return point


def same6(actual, expected) -> bool:
    if actual is None or expected is None:
        return actual is None and expected is None
    return round(float(actual), 6) == round(float(expected), 6)


def ensure_node_modules(worktree: Path, logs: list[str]) -> None:
    dest = worktree / "web" / "node_modules"
    if dest.is_dir():
        log(logs, f"node_modules present at {dest}")
        return
    lock_a = sha256(worktree / "web" / "package-lock.json")
    if lock_a != LOCK_SHA:
        raise SystemExit(f"package-lock mismatch: {lock_a} != {LOCK_SHA}")
    for source in NODE_MODULES_FALLBACKS:
        if not source.is_dir():
            continue
        lock_b = sha256(source.parent / "package-lock.json")
        if lock_b != lock_a:
            continue
        dest.symlink_to(source)
        log(logs, f"symlinked node_modules -> {source}")
        return
    raise SystemExit("no reusable node_modules with matching package-lock")


def build_assembly(worktree: Path, out: Path, logs: list[str]) -> Path:
    assembly = out / "assembly"
    if assembly.exists():
        shutil.rmtree(assembly)
    assembly.mkdir(parents=True)
    shutil.copy2(HERE / "assembly" / "index.html", assembly / "index.html")
    shutil.copy2(worktree / "web" / "src" / "analysis" / "analysis.css", assembly / "analysis.css")
    esbuild = worktree / "web" / "node_modules" / "esbuild" / "bin" / "esbuild"
    nm = worktree / "web" / "node_modules"
    cmd = [
        str(esbuild), str(HERE / "assembly" / "main.tsx"),
        "--bundle", f"--outfile={assembly / 'app.js'}",
        "--format=iife", "--platform=browser", "--jsx=automatic",
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
        raise SystemExit("assembly esbuild failed")
    log(logs, f"assembly app.js sha256={sha256(assembly / 'app.js')}")
    return assembly


def wait_ready(proc: subprocess.Popen, timeout: float, logs: list[str]) -> str:
    deadline = time.time() + timeout
    buf = ""
    while time.time() < deadline:
        if proc.poll() is not None:
            rest = proc.stdout.read() if proc.stdout else ""
            raise SystemExit(f"host exited early rc={proc.returncode}\n{buf}{rest}")
        line = proc.stdout.readline() if proc.stdout else ""
        if line:
            buf += line
            log(logs, line.rstrip())
            if "W12_RTR_READY=" in line:
                return buf
        else:
            time.sleep(0.05)
    raise SystemExit(f"timeout waiting for host ready\n{buf}")


def http_json(url: str, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def materialize_source(git_dir: Path, source: Path, logs: list[str]) -> None:
    sys.path.insert(0, str(SIBLING))
    from materialize import materialize
    source.mkdir(parents=True, exist_ok=True)
    log(logs, f"materialize {source} from {git_dir}")
    materialize(source, git_dir=git_dir)


def loopback_only(route, port: int) -> None:
    target = urlsplit(route.request.url)
    if route.request.url.startswith("data:"):
        route.continue_()
        return
    if not (target.scheme in {"http", "ws"} and target.hostname == "127.0.0.1" and target.port == port):
        route.abort()
        return
    route.continue_()


def assert_short_control(option: dict, table_text: str) -> None:
    dist = None
    for s in option.get("series") or []:
        if isinstance(s, dict) and s.get("name") == "两船距离 D(t)":
            dist = s
            break
    if not dist:
        raise SystemExit("distance series missing")
    if dist.get("connectNulls") is not False or dist.get("showSymbol") is not True:
        raise SystemExit(f"unexpected series flags {dist}")
    data = dist.get("data") or []
    by_t = {}
    i120 = i130 = None
    for i, pt in enumerate(data):
        if isinstance(pt, list) and len(pt) >= 2:
            t = float(pt[0])
            by_t[t] = pt[1]
            if t == 120.0:
                i120 = i
            if t == 130.0:
                i130 = i
    if i120 is None or i130 is None or i130 <= i120:
        raise SystemExit(f"T+120/T+130 points missing in series: {data}")
    window = data[i120 + 1:i130]
    saw_null_break = any(pt is None or (isinstance(pt, list) and len(pt) >= 2 and pt[1] is None) for pt in window)
    if not same6(by_t.get(120.0), EXPECTED[120.0]["distanceNm"]) or not same6(by_t.get(130.0), EXPECTED[130.0]["distanceNm"]):
        raise SystemExit(f"short control values missing or wrong: {by_t}")
    if not saw_null_break:
        raise SystemExit(f"missing line break between T+120 and T+130: {window}")
    for t, exp in EXPECTED.items():
        if f"{exp['distanceNm']:.6f}" not in table_text or f"{exp['dcpaNm']:.6f}" not in table_text or f"{exp['tcpaMin']:.6f}" not in table_text:
            raise SystemExit(f"table missing T+{t} values: {table_text}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True, help="service venv python for the host")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--worktree", type=Path, default=DEFAULT_WORKTREE)
    parser.add_argument("--browser", type=Path, default=Path(CHROME))
    parser.add_argument("--port", type=int, default=18784)
    parser.add_argument("--core-dir", type=Path, default=Path("/workspace/mcis-w41-core-out"))
    parser.add_argument("--dotnet", default=os.path.expanduser("~/.dotnet/dotnet"))
    parser.add_argument("--git-dir", type=Path, default=Path("/workspace/maritime-sim-design"))
    args = parser.parse_args()

    worktree = args.worktree.resolve()
    report = args.report.resolve()
    official = report / "official"
    shots = official / "shots"
    official.mkdir(parents=True, exist_ok=True)
    shots.mkdir(parents=True, exist_ok=True)
    logs: list[str] = []
    started = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    log(logs, f"official start {started}")

    require_sha(SIBLING / "core_norebuild.sh", WRAPPER_SHA256, "core_norebuild.sh")
    require_sha(worktree / "tools/mcis-core/src/CpaCommand.cs", CPA_CS_SHA256, "CpaCommand.cs")
    core_dir = args.core_dir.resolve()
    dll = require_sha(core_dir / "mcis-core.dll", CORE_DLL_SHA256, "mcis-core.dll")
    require_sha(core_dir / "mcis-core.runtimeconfig.json", CORE_RUNTIME_SHA256, "runtimeconfig")
    require_sha(core_dir / "mcis-core.deps.json", CORE_DEPS_SHA256, "deps")
    log(logs, f"locked official dll {dll}")

    ensure_node_modules(worktree, logs)
    assembly = build_assembly(worktree, official, logs)

    src = official / f"w12-rtr-src"
    if src.exists():
        shutil.rmtree(src)
    src.mkdir(parents=True)
    materialize_source(args.git_dir, src, logs)

    env = os.environ.copy()
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    env["DOTNET_NOLOGO"] = "1"
    env["DOTNET_ROOT"] = str(Path(args.dotnet).expanduser().resolve().parent)
    env["MCIS_CORE_DLL"] = str(core_dir / "mcis-core.dll")
    env["PATH"] = str(Path(args.dotnet).expanduser().resolve().parent) + os.pathsep + env.get("PATH", "")

    request_log = official / "host-request-log.json"
    host_cmd = [
        str(args.python), "-I", "-B", str(HERE / "host.py"),
        str(assembly), str(src), str(SIBLING / "fixtures"),
        str(worktree), str(SIBLING / "core_norebuild.sh"), dll,
        "127.0.0.1", str(args.port), str(request_log),
    ]
    log(logs, "host " + " ".join(host_cmd))
    host = subprocess.Popen(host_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    origin = f"http://127.0.0.1:{args.port}"
    results: dict = {"ok": False}
    try:
        wait_ready(host, 40, logs)
        from playwright.sync_api import sync_playwright, expect

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                executable_path=str(args.browser),
                headless=True,
                chromium_sandbox=True,
                env={k: v for k, v in env.items() if not k.startswith("MCIS_")},
                args=["--no-proxy-server"],
            )
            try:
                # Session 1: authorized synthetic context — must call frozen _load_registered_pair.
                auth_ctx = browser.new_context(
                    viewport={"width": 1280, "height": 900},
                    device_scale_factor=1,
                    service_workers="block",
                    extra_http_headers={ROLE_HEADER: ROLE_AUTHORIZED},
                )
                auth_ctx.route("**/*", lambda r: loopback_only(r, args.port))
                auth_captures: list[dict] = []

                def on_auth_response(resp):
                    if urlsplit(resp.url).path == "/assembly/api/view":
                        auth_captures.append({
                            "url": resp.url, "status": resp.status,
                            "body": resp.json(),
                        })

                auth_page = auth_ctx.new_page()
                auth_page.on("response", on_auth_response)
                auth_page.set_default_timeout(30000)
                access_before_auth = http_json(origin + "/assembly/api/custody-counts", {ROLE_HEADER: ROLE_AUTHORIZED})
                auth_page.goto(origin + "/assembly/", wait_until="domcontentloaded")
                expect(auth_page.locator('[data-testid="w12-rtr-assembly"]')).to_have_attribute("data-ok", "true")
                expect(auth_page.locator('[data-testid="w12-rtr-assembly"]')).to_have_attribute("data-status", "200")
                auth_page.wait_for_function("() => document.querySelectorAll('canvas').length >= 1")
                if not auth_captures:
                    raise SystemExit("no browser view request captured for authorized session")
                acap = auth_captures[0]
                abody = acap["body"]
                if acap["status"] != 200 or abody.get("ok") is not True:
                    raise SystemExit(f"authorized raw request unexpected: {acap}")
                if "denied" in abody or "unpaired" in abody or abody.get("view") is None:
                    raise SystemExit("authorized response is not a single authorized view")
                policy_ok = abody.get("policyResult") or {}
                if policy_ok.get("called") is not True or policy_ok.get("entry") != "_load_registered_pair" or policy_ok.get("outcome") != "allowed":
                    raise SystemExit(f"authorized request did not report frozen-entry allow: {policy_ok}")
                if abody.get("deltaAccess") != 2:
                    raise SystemExit(f"authorized request did not add exactly 2 Access: {abody.get('deltaAccess')} {abody.get('accessBefore')} -> {abody.get('accessAfter')}")
                access_after_auth = http_json(origin + "/assembly/api/custody-counts", {ROLE_HEADER: ROLE_AUTHORIZED})
                if access_after_auth["access"] - access_before_auth["access"] != 2:
                    raise SystemExit(f"authorized Access delta is not 2: {access_before_auth} -> {access_after_auth}")
                if access_after_auth["access"] != abody["accessAfter"]["access"]:
                    raise SystemExit("counts endpoint disagrees with request-time Access after")

                auth_page.wait_for_selector('[data-testid="registered-metric-table"]')
                auth_page.wait_for_timeout(400)
                option_probe = auth_page.evaluate(
                    """() => {
                      const root = window.echarts;
                      const api = root && (typeof root.getInstanceByDom === 'function' ? root : (root && root.default));
                      const canvases = [...document.querySelectorAll('canvas')];
                      let option = null;
                      for (const c of canvases) {
                        let el = c.parentElement;
                        for (let i = 0; i < 5 && el; i++) {
                          const inst = api && api.getInstanceByDom(el);
                          if (inst) { option = inst.getOption(); break; }
                          el = el.parentElement;
                        }
                        if (option) break;
                      }
                      return { option, canvasCount: canvases.length, hasApi: Boolean(api && api.getInstanceByDom) };
                    }"""
                )
                option = option_probe.get("option") if isinstance(option_probe, dict) else option_probe
                if not option:
                    auth_page.screenshot(path=str(shots / "debug-no-option.png"), full_page=True)
                    write_json(official / "echart-handle-probe.json", option_probe)
                    raise SystemExit(f"could not read ECharts option: {option_probe}")
                write_json(official / "echarts-getoption.json", export_needed_option(option))
                table = auth_page.locator('[data-testid="registered-metric-table"]')
                table_text = table.inner_text()
                assert_short_control(export_needed_option(option), table_text)
                sources = auth_page.locator('[data-testid="sources"]').inner_text()
                if "mcis-core.dll" not in sources or dll not in sources:
                    raise SystemExit(f"authorized sources missing official core: {sources}")
                if auth_page.locator('[data-testid="registered-identities"]').count() != 1:
                    raise SystemExit("authorized view missing evidence identities")

                box = auth_page.locator("canvas").first.bounding_box()
                if not box:
                    raise SystemExit("canvas missing for hover")
                auth_page.mouse.move(box["x"] + box["width"] * 0.4, box["y"] + box["height"] * 0.5)
                auth_page.wait_for_timeout(300)
                auth_page.mouse.move(box["x"] + box["width"] * 0.7, box["y"] + box["height"] * 0.5)
                auth_page.wait_for_timeout(300)
                after_hover = http_json(origin + "/assembly/api/custody-counts", {ROLE_HEADER: ROLE_AUTHORIZED})
                if after_hover["access"] != access_after_auth["access"]:
                    raise SystemExit(f"hover reread originals: {access_after_auth} -> {after_hover}")

                auth_page.screenshot(path=str(shots / "authorized-fullpage.png"), full_page=True)
                auth_page.locator("canvas").first.screenshot(path=str(shots / "authorized-curve.png"))
                table.screenshot(path=str(shots / "authorized-metric-table.png"))
                auth_page.locator('[data-testid="sources"]').screenshot(path=str(shots / "authorized-sources.png"))
                write_json(official / "authorized-request.json", {
                    "session": "synthetic-authorized-reader",
                    "roleContextKind": "synthetic-test-server-role",
                    "notRealAuthentication": True,
                    "accessBefore": access_before_auth,
                    "accessAfter": access_after_auth,
                    "hoverAccess": after_hover,
                    "policyResult": policy_ok,
                    "raw": {
                        "url": acap["url"],
                        "status": acap["status"],
                        "ok": abody.get("ok"),
                        "roleContext": abody.get("roleContext"),
                        "deltaAccess": abody.get("deltaAccess"),
                        "accessBefore": abody.get("accessBefore"),
                        "accessAfter": abody.get("accessAfter"),
                        "coreVersion": abody.get("coreVersion"),
                        "declaredOpenGaps": abody.get("declaredOpenGaps"),
                        "hasView": abody.get("view") is not None,
                        "hasDeniedFixture": "denied" in abody,
                        "hasUnpairedFixture": "unpaired" in abody,
                        "policyResult": policy_ok,
                    },
                })
                auth_ctx.close()

                # Session 2: brand-new browser session, independent synthetic deny context.
                denied_ctx = browser.new_context(
                    viewport={"width": 1280, "height": 900},
                    device_scale_factor=1,
                    service_workers="block",
                    extra_http_headers={ROLE_HEADER: ROLE_DENIED},
                )
                denied_ctx.route("**/*", lambda r: loopback_only(r, args.port))
                denied_captures: list[dict] = []

                def on_denied_response(resp):
                    if urlsplit(resp.url).path == "/assembly/api/view":
                        denied_captures.append({
                            "url": resp.url, "status": resp.status,
                            "body": resp.json(),
                        })

                denied_page = denied_ctx.new_page()
                denied_page.on("response", on_denied_response)
                denied_page.set_default_timeout(20000)
                access_before_denied = http_json(origin + "/assembly/api/custody-counts", {ROLE_HEADER: ROLE_DENIED})
                denied_page.goto(origin + "/assembly/", wait_until="domcontentloaded")
                expect(denied_page.locator('[data-testid="w12-rtr-assembly"]')).to_have_attribute("data-ok", "false")
                expect(denied_page.locator('[data-testid="w12-rtr-assembly"]')).to_have_attribute("data-status", "403")
                denied_text = denied_page.locator('[data-testid="denied-analysis"]').inner_text()
                lowered = denied_text.lower()
                if "policy" not in lowered or "deny" not in lowered or "403" not in denied_text or "metricsreturned=false" not in lowered:
                    raise SystemExit(f"denied view incomplete: {denied_text!r}")
                if denied_page.locator("canvas").count() != 0:
                    raise SystemExit("denied view has a chart")
                if denied_page.locator('[data-testid="registered-identities"]').count() != 0:
                    raise SystemExit("denied view leaked evidence identity")
                if denied_page.locator('[data-testid="registered-metric-table"]').count() != 0:
                    raise SystemExit("denied view leaked metric table")
                for exp in EXPECTED.values():
                    for val in exp.values():
                        if f"{val:.6f}" in denied_text:
                            raise SystemExit(f"denied view leaked metric {val}")
                access_after_denied = http_json(origin + "/assembly/api/custody-counts", {ROLE_HEADER: ROLE_DENIED})
                if access_after_denied["access"] != access_before_denied["access"]:
                    raise SystemExit(f"unauthorized Access increased: {access_before_denied} -> {access_after_denied}")
                if access_after_denied["access"] != 0 or access_before_denied["access"] != 0:
                    raise SystemExit(f"independent deny context Access was not 0->0: {access_before_denied} -> {access_after_denied}")
                if not denied_captures:
                    raise SystemExit("no browser view request captured for denied session")
                cap = denied_captures[0]
                body = cap["body"]
                if cap["status"] != 403 or body.get("ok") is not False:
                    raise SystemExit(f"denied raw request unexpected: {cap}")
                if body.get("view") is not None or body.get("registeredIdentities") or body.get("currentAnalysis") is not None:
                    raise SystemExit(f"denied response contained snapshot or identity: {body}")
                dumped = json.dumps(body)
                if "1.070062" in dumped or "sourceSha256" in dumped:
                    raise SystemExit("denied response leaked metrics or evidence hashes")
                policy_deny = body.get("policyResult") or {}
                if policy_deny.get("called") is not True or policy_deny.get("entry") != "_load_registered_pair":
                    raise SystemExit(f"deny path did not call frozen entry: {policy_deny}")
                if policy_deny.get("outcome") != "evidence-policy-deny" or policy_deny.get("statusCode") != 403:
                    raise SystemExit(f"deny path was not evidence-policy 403: {policy_deny}")
                detail = policy_deny.get("detail") or {}
                if not isinstance(detail, dict) or detail.get("code") != "FORBIDDEN":
                    raise SystemExit(f"deny path missing FORBIDDEN policy detail: {policy_deny}")
                denied_page.screenshot(path=str(shots / "denied-fullpage.png"), full_page=True)
                write_json(official / "denied-request.json", {
                    "session": "synthetic-denied-reader",
                    "roleContextKind": "synthetic-test-server-role",
                    "notRealAuthentication": True,
                    "independentContext": True,
                    "accessBefore": access_before_denied,
                    "accessAfter": access_after_denied,
                    "policyResult": policy_deny,
                    "raw": cap,
                })
                denied_ctx.close()

            finally:
                browser.close()

        results.update({
            "ok": True,
            "denied": json.loads((official / "denied-request.json").read_text()),
            "authorized": json.loads((official / "authorized-request.json").read_text()),
        })
        log(logs, "browser checks ok")
    finally:
        if host.poll() is None:
            host.terminate()
            try:
                host.wait(timeout=8)
            except subprocess.TimeoutExpired:
                pass
        rc = host.poll()
        log(logs, f"host exit={rc}")

    ended = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    log(logs, f"official end {ended} ok={results.get('ok')}")
    results.update(started=started, ended=ended, port=args.port, origin=origin, coreDllSha256=dll)
    write_json(official / "summary.json", results)
    (official / "run.log").write_text("\n".join(logs) + "\n", encoding="utf-8")
    return 0 if results.get("ok") else 1


if __name__ == "__main__":
    if not sys.flags.isolated:
        raise SystemExit("Use existing Python -I")
    raise SystemExit(main())
