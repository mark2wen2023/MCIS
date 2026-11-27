#!/usr/bin/env python3
"""Official sandboxed Chrome: same-case pair select and recalculation."""
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
SHA_A = "a8f9109a33b8c80a6c41219473186e69c16fd59ee64ff325a5559c190028bb1c"
SHA_B = "07e043fc227770b6aaa6f1b15a6118e46b85a52e5638ac1b514e9269c6b159ca"
SHA_A_PAIR_B = "8f3e61212730673589068e32383a1677f57255b84ee5879041e8bbd9058ca27a"
EXPECTED_A = {
    120.0: {"distanceNm": 1.070062, "dcpaNm": 0.000226, "tcpaMin": 2.918352, "riskLevel": "Danger"},
    130.0: {"distanceNm": 1.008757, "dcpaNm": 0.000213, "tcpaMin": 2.751155, "riskLevel": "Danger"},
}
EXPECTED_B = {
    120.0: {"distanceNm": 1.226641, "dcpaNm": 0.599765, "tcpaMin": 2.918219, "riskLevel": "Warning"},
    130.0: {"distanceNm": 1.173535, "dcpaNm": 0.599751, "tcpaMin": 2.751011, "riskLevel": "Warning"},
}
NODE_MODULES_FALLBACKS = [
    Path("/workspace/mcis-w12-json-gap-cand/web/node_modules"),
    Path("/workspace/mcis-w12-narrow-cand/web/node_modules"),
    Path("/workspace/mcis-w12-policy-deny-cand/web/node_modules"),
]
ECHART_PROBE = """() => {
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
            if "W12_PAIR_SELECT_READY=" in line:
                return buf
        else:
            time.sleep(0.05)
    raise SystemExit(f"timeout waiting for host ready\n{buf}")


def http_json(url: str, headers: dict | None = None, timeout: float = 15) -> dict:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
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


def assert_short_control(option: dict, table_text: str, expected: dict, label: str) -> None:
    dist = None
    for s in option.get("series") or []:
        if isinstance(s, dict) and s.get("name") == "两船距离 D(t)":
            dist = s
            break
    if not dist:
        raise SystemExit(f"{label}: distance series missing")
    if dist.get("connectNulls") is not False or dist.get("showSymbol") is not True:
        raise SystemExit(f"{label}: unexpected series flags {dist}")
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
        raise SystemExit(f"{label}: T+120/T+130 points missing in series: {data}")
    window = data[i120 + 1:i130]
    saw_null_break = any(pt is None or (isinstance(pt, list) and len(pt) >= 2 and pt[1] is None) for pt in window)
    if not same6(by_t.get(120.0), expected[120.0]["distanceNm"]) or not same6(by_t.get(130.0), expected[130.0]["distanceNm"]):
        raise SystemExit(f"{label}: short control values missing or wrong: {by_t}")
    if not saw_null_break:
        raise SystemExit(f"{label}: missing line break between T+120 and T+130: {window}")
    for t, exp in expected.items():
        token = f"{exp['distanceNm']:.6f} nm"
        if token not in table_text:
            raise SystemExit(f"{label}: metric table missing {token}: {table_text}")


def read_option(page):
    probe = page.evaluate(ECHART_PROBE)
    option = probe.get("option") if isinstance(probe, dict) else probe
    if not option:
        return None, probe
    return option, probe


def identities_ok(page, sha_a: str, sha_b: str, label: str) -> str:
    box = page.locator('[data-testid="registered-identities"]')
    if box.count() != 1:
        raise SystemExit(f"{label}: missing evidence identities")
    text = box.inner_text()
    if sha_a not in text or sha_b not in text:
        raise SystemExit(f"{label}: identities missing expected digests: {text}")
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True, help="service venv python for the host")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--worktree", type=Path, default=DEFAULT_WORKTREE)
    parser.add_argument("--browser", type=Path, default=Path(CHROME))
    parser.add_argument("--port", type=int, default=18785)
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
    require_sha(HERE / "fixtures" / "vessel-a-pair-b.json", SHA_A_PAIR_B, "vessel-a-pair-b.json")
    require_sha(SIBLING / "fixtures" / "vessel-a.json", SHA_A, "locked vessel-a.json")
    require_sha(SIBLING / "fixtures" / "vessel-b.json", SHA_B, "locked vessel-b.json")
    core_dir = args.core_dir.resolve()
    dll = require_sha(core_dir / "mcis-core.dll", CORE_DLL_SHA256, "mcis-core.dll")
    require_sha(core_dir / "mcis-core.runtimeconfig.json", CORE_RUNTIME_SHA256, "runtimeconfig")
    require_sha(core_dir / "mcis-core.deps.json", CORE_DEPS_SHA256, "deps")
    log(logs, f"locked official dll {dll}")

    ensure_node_modules(worktree, logs)
    assembly = build_assembly(worktree, official, logs)

    src = official / "w12-pair-src"
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
        # Server must reject pins and unknown labels without calling a fake success path.
        pin_url = origin + "/assembly/api/view?pair=pair-a&sourceSha256=" + SHA_A
        last_err = None
        for _ in range(20):
            try:
                http_json(pin_url)
                raise SystemExit("server accepted a sourceSha256 pin query")
            except urllib.error.HTTPError as exc:
                last_err = exc
                break
            except urllib.error.URLError as exc:
                last_err = exc
                time.sleep(0.1)
        else:
            raise SystemExit(f"host never accepted connections after READY: {last_err}")
        if not isinstance(last_err, urllib.error.HTTPError):
            raise SystemExit(f"pin rejection did not return HTTP: {last_err}")
        exc = last_err
        if exc.code != 400:
            raise SystemExit(f"pin rejection status {exc.code}, expected 400")
        pin_reject = json.loads(exc.read().decode("utf-8"))
        if pin_reject.get("reason") != "PIN_NOT_ACCEPTED" or pin_reject.get("called") is not False:
            raise SystemExit(f"pin rejection body unexpected: {pin_reject}")
        write_json(official / "pin-rejected.json", pin_reject)
        from playwright.sync_api import sync_playwright, expect
        captures: list[dict] = []
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                executable_path=str(args.browser),
                headless=True,
                chromium_sandbox=True,
                args=["--disable-dev-shm-usage"],
            )
            context = browser.new_context(viewport={"width": 1400, "height": 900})
            context.route("**/*", lambda route: loopback_only(route, args.port))
            page = context.new_page()
            page.set_default_timeout(30000)

            def on_response(resp):
                path = urlsplit(resp.url).path
                if path == "/assembly/api/view":
                    try:
                        body = resp.json()
                    except Exception:
                        body = {"_parse_error": True, "text": resp.text()[:400]}
                    captures.append({
                        "url": resp.url,
                        "status": resp.status,
                        "body": body,
                    })

            page.on("response", on_response)
            access_before = http_json(origin + "/assembly/api/custody-counts")
            if access_before.get("access") != 0:
                raise SystemExit(f"Access must start at 0, got {access_before}")
            page.goto(origin + "/assembly/", wait_until="domcontentloaded")
            expect(page.locator('[data-testid="w12-pair-select"]')).to_have_attribute("data-pair", "pair-a")
            expect(page.locator('[data-testid="w12-pair-select"]')).to_have_attribute("data-loading", "false")
            expect(page.locator('[data-testid="registered-metric-table"]')).to_be_visible()
            page.wait_for_timeout(400)
            option_a, probe_a = read_option(page)
            if not option_a:
                page.screenshot(path=str(shots / "debug-no-option-a.png"), full_page=True)
                write_json(official / "echart-handle-probe-a.json", probe_a)
                raise SystemExit(f"could not read ECharts option for pair A: {probe_a}")
            write_json(official / "echarts-getoption-a.json", export_needed_option(option_a))
            table_a = page.locator('[data-testid="registered-metric-table"]').inner_text()
            assert_short_control(export_needed_option(option_a), table_a, EXPECTED_A, "pair-a")
            ident_a = identities_ok(page, SHA_A, SHA_B, "pair-a")
            if SHA_A_PAIR_B in ident_a:
                raise SystemExit("pair A identities unexpectedly include pair B digest")
            sources_a = page.locator('[data-testid="sources"]').inner_text()
            if "mcis-core.dll" not in sources_a or dll not in sources_a or SHA_A not in sources_a:
                raise SystemExit(f"pair A sources missing official core or digest: {sources_a}")
            access_after_a = http_json(origin + "/assembly/api/custody-counts")
            if access_after_a["access"] - access_before["access"] != 2:
                raise SystemExit(f"pair A Access delta is not 2: {access_before} -> {access_after_a}")
            page.screenshot(path=str(shots / "pair-a-fullpage.png"), full_page=True)
            page.locator("canvas").first.screenshot(path=str(shots / "pair-a-curve.png"))
            page.locator('[data-testid="registered-metric-table"]').screenshot(path=str(shots / "pair-a-metric-table.png"))
            page.locator('[data-testid="sources"]').screenshot(path=str(shots / "pair-a-sources.png"))
            write_json(official / "pair-a-request.json", {
                "pairLabel": "pair-a",
                "accessBefore": access_before,
                "accessAfter": access_after_a,
                "identitiesText": ident_a,
                "tableText": table_a,
                "captures": [c for c in captures if "pair=pair-a" in c.get("url", "") and "delayMs" not in c.get("url", "")],
            })
            log(logs, "pair A shown; locked digests and d49a691 T+120/T+130 match")

            # Delayed B, assert loading clears A, then switch back before B returns.
            delayed_from = len(captures)
            page.locator('[data-testid="select-pair-b-delayed"]').click()
            expect(page.locator('[data-testid="w12-pair-select"]')).to_have_attribute("data-loading", "true")
            expect(page.locator('[data-testid="pair-loading"]')).to_be_visible()
            if page.locator('[data-testid="registered-metric-table"]').count() != 0:
                raise SystemExit("loading B still kept pair A metric table")
            if page.locator('[data-testid="analysis-page"]').count() != 0:
                raise SystemExit("loading B still kept AnalysisView")
            body_text = page.locator("body").inner_text()
            if "1.070062" in body_text:
                raise SystemExit("loading B still displayed pair A T+120 distance")
            page.screenshot(path=str(shots / "pair-b-loading.png"), full_page=True)
            log(logs, "loading B cleared pair A analysis")

            page.locator('[data-testid="select-pair-a"]').click()
            expect(page.locator('[data-testid="w12-pair-select"]')).to_have_attribute("data-pair", "pair-a")
            expect(page.locator('[data-testid="w12-pair-select"]')).to_have_attribute("data-loading", "false")
            expect(page.locator('[data-testid="registered-metric-table"]')).to_be_visible()
            # Wait out the delayed B response (3.5s hold after compute).
            page.wait_for_timeout(6000)
            expect(page.locator('[data-testid="w12-pair-select"]')).to_have_attribute("data-pair", "pair-a")
            expect(page.locator('[data-testid="w12-pair-select"]')).to_have_attribute("data-loading", "false")
            table_after_late = page.locator('[data-testid="registered-metric-table"]').inner_text()
            if "1.226641" in table_after_late or "1.070062" not in table_after_late:
                raise SystemExit(f"late pair B overwrote pair A: {table_after_late}")
            ident_after_late = identities_ok(page, SHA_A, SHA_B, "pair-a-after-late-b")
            if SHA_A_PAIR_B in ident_after_late:
                raise SystemExit("late pair B overwrote pair A identities")
            sha_attr = page.locator('[data-testid="w12-pair-select"]').get_attribute("data-sha-a")
            if sha_attr != SHA_A:
                raise SystemExit(f"late pair B overwrote data-sha-a: {sha_attr}")
            page.screenshot(path=str(shots / "pair-a-after-late-b.png"), full_page=True)
            page.locator('[data-testid="registered-metric-table"]').screenshot(path=str(shots / "pair-a-after-late-b-table.png"))
            delayed_caps = [c for c in captures[delayed_from:] if "delayMs=" in c.get("url", "")]
            if not delayed_caps or delayed_caps[0]["status"] != 200 or (delayed_caps[0]["body"] or {}).get("pairLabel") != "pair-b":
                raise SystemExit(f"delayed pair B request missing or wrong: {delayed_caps}")
            late_core = (delayed_caps[0]["body"] or {}).get("coreAt120") or {}
            if not same6(late_core.get("currentDistanceNm"), EXPECTED_B[120.0]["distanceNm"]):
                raise SystemExit(f"delayed pair B did not actually recompute: {late_core}")
            write_json(official / "late-b-ignored.json", {
                "delayedCapture": delayed_caps[0],
                "tableAfter": table_after_late,
                "identitiesAfter": ident_after_late,
                "dataShaA": sha_attr,
            })
            log(logs, "switched back to A; late B did not overwrite A")

            # Clean B load: actual read and recompute, different digests and T+120 value.
            access_before_b = http_json(origin + "/assembly/api/custody-counts")
            page.locator('[data-testid="select-pair-b"]').click()
            expect(page.locator('[data-testid="w12-pair-select"]')).to_have_attribute("data-pair", "pair-b")
            expect(page.locator('[data-testid="w12-pair-select"]')).to_have_attribute("data-loading", "false")
            expect(page.locator('[data-testid="registered-metric-table"]')).to_be_visible()
            page.wait_for_timeout(400)
            option_b, probe_b = read_option(page)
            if not option_b:
                page.screenshot(path=str(shots / "debug-no-option-b.png"), full_page=True)
                write_json(official / "echart-handle-probe-b.json", probe_b)
                raise SystemExit(f"could not read ECharts option for pair B: {probe_b}")
            write_json(official / "echarts-getoption-b.json", export_needed_option(option_b))
            table_b = page.locator('[data-testid="registered-metric-table"]').inner_text()
            assert_short_control(export_needed_option(option_b), table_b, EXPECTED_B, "pair-b")
            if "1.070062" in table_b:
                raise SystemExit("pair B table still shows pair A T+120 distance")
            ident_b = identities_ok(page, SHA_A_PAIR_B, SHA_B, "pair-b")
            if SHA_A in ident_b:
                raise SystemExit("pair B identities still show locked pair A vessel-A digest")
            sources_b = page.locator('[data-testid="sources"]').inner_text()
            if SHA_A_PAIR_B not in sources_b or dll not in sources_b:
                raise SystemExit(f"pair B sources missing independent digest or core: {sources_b}")
            access_after_b = http_json(origin + "/assembly/api/custody-counts")
            if access_after_b["access"] - access_before_b["access"] != 2:
                raise SystemExit(f"pair B Access delta is not 2: {access_before_b} -> {access_after_b}")
            page.screenshot(path=str(shots / "pair-b-fullpage.png"), full_page=True)
            page.locator("canvas").first.screenshot(path=str(shots / "pair-b-curve.png"))
            page.locator('[data-testid="registered-metric-table"]').screenshot(path=str(shots / "pair-b-metric-table.png"))
            page.locator('[data-testid="sources"]').screenshot(path=str(shots / "pair-b-sources.png"))
            write_json(official / "pair-b-request.json", {
                "pairLabel": "pair-b",
                "accessBefore": access_before_b,
                "accessAfter": access_after_b,
                "identitiesText": ident_b,
                "tableText": table_b,
                "captures": [c for c in captures if "pair=pair-b" in c.get("url", "") and "delayMs" not in c.get("url", "")],
            })
            log(logs, "pair B shown; independent digest and recomputed T+120/T+130 match")

            log_body = http_json(origin + "/assembly/api/request-log")
            write_json(official / "browser-captures.json", captures)
            records = log_body.get("records") or []
            starts = [row for row in records if row.get("event") == "start" and row.get("path") == "/assembly/api/view"]
            finishes = [row for row in records if row.get("event") == "finish" and row.get("ok") is True]
            def _is_pin_query(row: dict) -> bool:
                return any(str(k).lower() in {"sourcesha256", "requestdigest", "evidenceid", "pin", "pins", "previewdigest", "reportsha256"} for k in (row.get("query") or {}))
            start_labels = [row.get("pairLabel") for row in starts if row.get("pairLabel") in {"pair-a", "pair-b"} and not _is_pin_query(row)]
            # Initiation: first A, delayed B, switch-back A, clean B.
            if start_labels[:4] != ["pair-a", "pair-b", "pair-a", "pair-b"]:
                raise SystemExit(f"request start order unexpected: {start_labels}")
            delayed_starts = [row for row in starts if str((row.get("query") or {}).get("delayMs") or "")]
            if not delayed_starts:
                raise SystemExit("missing delayed pair-b start in host log")
            delayed_finish = next((row for row in records if row.get("event") == "finish" and row.get("ok") is True and row.get("delayMs")), None)
            switch_a = next((row for row in starts[2:] if row.get("pairLabel") == "pair-a"), None)
            if delayed_finish is None or switch_a is None or not (switch_a["t"] < delayed_finish["t"]):
                raise SystemExit(f"switch-back A was not initiated before delayed B finished: {switch_a} {delayed_finish}")
            results = {
                "ok": True,
                "chromium_sandbox": True,
                "listen": f"127.0.0.1:{args.port}",
                "pairA": {
                    "sourceSha256": {"SYN-VESSEL-A": SHA_A, "SYN-VESSEL-B": SHA_B},
                    "coreAt120": EXPECTED_A[120.0],
                    "coreAt130": EXPECTED_A[130.0],
                },
                "pairB": {
                    "sourceSha256": {"SYN-VESSEL-A": SHA_A_PAIR_B, "SYN-VESSEL-B": SHA_B},
                    "coreAt120": EXPECTED_B[120.0],
                    "coreAt130": EXPECTED_B[130.0],
                },
                "requestOrder": start_labels,
                "successfulFinishes": [row.get("pairLabel") for row in finishes],
                "lateBDidNotOverwriteA": True,
                "loadingClearedA": True,
                "acceptsPins": False,
            }
            context.close()
            browser.close()
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
