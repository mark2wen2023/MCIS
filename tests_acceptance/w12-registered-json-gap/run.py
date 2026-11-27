#!/usr/bin/env python3
"""Official isolated-host browser run: registered declared-gap JSON into AnalysisView."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
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


def option_series(option: dict, name: str) -> list:
    for s in option.get("series") or []:
        if isinstance(s, dict) and s.get("name") == name:
            return s.get("data") or []
    return []


def series_value(point) -> object:
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
    source = Path("/workspace/mcis-w12-narrow-cand/web/node_modules")
    lock_a = sha256(worktree / "web" / "package-lock.json")
    lock_b = sha256(source.parent / "package-lock.json")
    if lock_a != lock_b or lock_a != LOCK_SHA:
        raise SystemExit(f"package-lock mismatch, refusing to reuse node_modules: {lock_a} vs {lock_b}")
    dest.symlink_to(source)
    log(logs, f"symlinked node_modules -> {source}")


def run_existing_regressions(worktree: Path, official: Path, logs: list[str]) -> None:
    esbuild = worktree / "web" / "node_modules" / "esbuild" / "bin" / "esbuild"
    node = shutil.which("node") or "/usr/bin/node"
    cases = [
        ("31", worktree / "web" / "tests" / "analysis-chart-gap.test.ts", official / "analysis-chart-gap.test.cjs", "W12 chart-gap unit tests: 31 passed"),
        ("96", worktree / "web" / "tests" / "analysis-w12.test.tsx", official / "analysis-w12.test.cjs", "W12 analysis tests: 96 passed"),
    ]
    for label, src, out, expect in cases:
        cmd = [str(esbuild), str(src), "--bundle", "--platform=node", "--format=cjs", f"--outfile={out}", "--jsx=automatic", "--log-level=warning"]
        log(logs, "esbuild " + " ".join(cmd))
        bundled = subprocess.run(cmd, cwd=str(worktree / "web"), capture_output=True, text=True)
        if bundled.returncode != 0:
            log(logs, bundled.stderr)
            raise SystemExit(f"regression {label} bundle failed")
        ran = subprocess.run([node, str(out)], cwd=str(worktree / "web"), capture_output=True, text=True)
        text = (ran.stdout or "") + (ran.stderr or "")
        log(logs, text.strip())
        if ran.returncode != 0 or expect not in text:
            raise SystemExit(f"regression {label} failed rc={ran.returncode}")


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
        log(logs, proc.stdout); log(logs, proc.stderr)
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
            if "W12_RJG_READY=" in line:
                return buf
        else:
            time.sleep(0.05)
    raise SystemExit(f"timeout waiting for host ready\n{buf}")


def http_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True, help="service venv python for the host")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--worktree", type=Path, default=DEFAULT_WORKTREE)
    parser.add_argument("--browser", type=Path, default=Path(CHROME))
    parser.add_argument("--port", type=int, default=18782)
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

    require_sha(HERE / "core_norebuild.sh", WRAPPER_SHA256, "core_norebuild.sh")
    require_sha(worktree / "tools/mcis-core/src/CpaCommand.cs", CPA_CS_SHA256, "CpaCommand.cs")
    core_dir = args.core_dir.resolve()
    dll = require_sha(core_dir / "mcis-core.dll", CORE_DLL_SHA256, "mcis-core.dll")
    require_sha(core_dir / "mcis-core.runtimeconfig.json", CORE_RUNTIME_SHA256, "runtimeconfig")
    require_sha(core_dir / "mcis-core.deps.json", CORE_DEPS_SHA256, "deps")
    require_sha(HERE / "fixtures" / "vessel-a.json", "a8f9109a33b8c80a6c41219473186e69c16fd59ee64ff325a5559c190028bb1c", "vessel-a.json")
    require_sha(HERE / "fixtures" / "vessel-b.json", "07e043fc227770b6aaa6f1b15a6118e46b85a52e5638ac1b514e9269c6b159ca", "vessel-b.json")
    log(logs, f"locked official dll {dll}")

    ensure_node_modules(worktree, logs)
    run_existing_regressions(worktree, official, logs)
    assembly = build_assembly(worktree, official, logs)

    env = {k: v for k, v in os.environ.items()
           if k not in {"HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY"}
           and not k.startswith("MCIS_")}
    env.update({
        "MCIS_SEED_DEMO": "0",
        "MCIS_CORE_DLL": str(core_dir / "mcis-core.dll"),
        "MCIS_DOTNET": str(args.dotnet),
        "MCIS_CORE": str(HERE / "core_norebuild.sh"),
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        "DOTNET_NOLOGO": "1",
    })

    source = Path(tempfile.mkdtemp(prefix="w12-rjg-src-", dir=str(official)))
    raw_snapshot = official / "raw-snapshot.json"
    assemble_cmd = [
        str(Path(args.python)), "-I", "-B", str(HERE / "snapshot.py"),
        "--git-dir", str(args.git_dir.resolve()),
        "--source", str(source),
        "--fixtures", str(HERE / "fixtures"),
        "--worktree", str(worktree),
        "--core-cmd", str(HERE / "core_norebuild.sh"),
        "--dll-sha", dll,
        "--out", str(raw_snapshot),
    ]
    log(logs, "assemble " + " ".join(assemble_cmd))
    assembled = subprocess.run(assemble_cmd, cwd=str(HERE), capture_output=True, text=True, env=env)
    if assembled.stdout:
        log(logs, assembled.stdout.strip())
    if assembled.returncode != 0:
        log(logs, assembled.stderr)
        raise SystemExit(f"assemble failed rc={assembled.returncode}")
    snapshot = json.loads(raw_snapshot.read_text(encoding="utf-8"))
    PRODUCT = snapshot.get("productAllowlist")
    # Official record may include server-held pins; the browser API does not serve them as authority.
    write_json(official / "snapshot.json", {
        k: snapshot[k] for k in snapshot if k != "pinsHeldByServer"
    })
    write_json(official / "server-pins.json", {"heldByServer": snapshot["pinsHeldByServer"], "note": "not accepted from the browser"})
    write_json(official / "core-calls.json", {"dllSha256": dll, "coreVersion": snapshot["coreVersion"], "calls": snapshot["coreCalls"]})
    write_json(official / "access-and-denial.json", {
        "successAccess": snapshot["successAccess"],
        "denied": snapshot["denied"],
        "unpaired": snapshot["unpaired"],
        "finalCounts": snapshot["finalCounts"],
    })

    public_snapshot = official / "public-snapshot.json"
    write_json(public_snapshot, {
        "complete": snapshot["complete"],
        "sampleStatus": snapshot["sampleStatus"],
        "denied": snapshot["denied"],
        "unpaired": snapshot["unpaired"],
        "successAccess": snapshot["successAccess"],
        "fixtureSha256": snapshot["fixtureSha256"],
        "coreVersion": snapshot["coreVersion"],
        "declaredOpenGaps": snapshot["declaredOpenGaps"],
    })

    host_cmd = [
        str(Path(args.python)), "-I", "-B", str(HERE / "host.py"),
        str(assembly), str(public_snapshot), str(source),
        "127.0.0.1", str(args.port),
    ]
    log(logs, "host " + " ".join(host_cmd))
    host = subprocess.Popen(host_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    origin = f"http://127.0.0.1:{args.port}"
    results: dict = {"ok": False, "regression31": True, "regression96": True, "productAllowlist": PRODUCT}
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
                context = browser.new_context(viewport={"width": 1280, "height": 900}, device_scale_factor=1, service_workers="block")

                def route(r):
                    target = urlsplit(r.request.url)
                    if r.request.url.startswith("data:"):
                        r.continue_(); return
                    if not (target.scheme in {"http", "ws"} and target.hostname == "127.0.0.1" and target.port == args.port):
                        r.abort(); return
                    r.continue_()

                context.route("**/*", route)
                page = context.new_page()
                page.set_default_timeout(15000)
                page.goto(origin + "/assembly/", wait_until="domcontentloaded")
                expect(page.locator('[data-testid="w12-rjg-assembly"]')).to_have_attribute("data-view", "complete")
                page.wait_for_function("() => document.querySelectorAll('canvas').length >= 1")

                option_probe = page.evaluate(
                    """() => {
                      const root = window.echarts;
                      const api = root && (typeof root.getInstanceByDom === 'function' ? root : root.default);
                      const canvases = [...document.querySelectorAll('canvas')];
                      let option = null;
                      for (const c of canvases) {
                        let el = c.parentElement;
                        for (let i = 0; i < 3 && el; i++) {
                          const inst = api && api.getInstanceByDom(el);
                          if (inst) { option = inst.getOption(); break; }
                          el = el.parentElement;
                        }
                        if (option) break;
                      }
                      return { option, canvasCount: canvases.length };
                    }"""
                )
                option = option_probe.get("option")
                write_json(official / "echarts-getoption.json", export_needed_option(option) if isinstance(option, dict) else json_strict(option))
                if not option:
                    page.screenshot(path=str(shots / "debug-no-option.png"), full_page=True)
                    raise SystemExit("echarts.getInstanceByDom returned no option")

                def unwrap(v):
                    if isinstance(v, list) and v:
                        return v[0]
                    return v

                symbol_flags = []
                for s in option.get("series") or []:
                    if not isinstance(s, dict):
                        continue
                    name = s.get("name")
                    if name in {"两船距离 D(t)", "DCPA(t)", "TCPA(t)"}:
                        show, connect = unwrap(s.get("showSymbol")), unwrap(s.get("connectNulls"))
                        symbol_flags.append({"name": name, "showSymbol": show, "connectNulls": connect})
                        if show is not True:
                            raise SystemExit(f"{name} showSymbol is {s.get('showSymbol')}")
                        if connect is True:
                            raise SystemExit(f"{name} connectNulls is true")
                if len(symbol_flags) != 3:
                    raise SystemExit(f"expected 3 curve series, got {symbol_flags}")

                # T+124.25 must have no numeric pair value; T+120/130 must match d49a691.
                dist = option_series(option, "两船距离 D(t)")
                dcpa = option_series(option, "DCPA(t)")
                tcpa = option_series(option, "TCPA(t)")
                found = {}
                for i, pt in enumerate(dist):
                    t = None
                    if isinstance(pt, list) and pt:
                        t = pt[0]
                    if t is None:
                        continue
                    found[float(t)] = {
                        "distance": series_value(pt),
                        "dcpa": series_value(dcpa[i]) if i < len(dcpa) else None,
                        "tcpa": series_value(tcpa[i]) if i < len(tcpa) else None,
                    }
                if 124.25 in found and any(found[124.25][k] not in (None, "-") for k in ("distance", "dcpa", "tcpa")):
                    raise SystemExit(f"T+124.25 has pair metrics in the chart: {found[124.25]}")
                for t, exp in EXPECTED.items():
                    if t not in found:
                        raise SystemExit(f"T+{t:g} missing from chart data {sorted(found)}")
                    got = found[t]
                    if not (same6(got["distance"], exp["distanceNm"]) and same6(got["dcpa"], exp["dcpaNm"]) and same6(got["tcpa"], exp["tcpaMin"])):
                        raise SystemExit(f"T+{t:g} chart {got} != {exp}")
                    # a null should sit between 120 and 130 because of the declared gap
                if not any(x is None or (isinstance(x, list) and (len(x) < 2 or x[1] is None)) for x in dist):
                    # at least the declared-gap break must exist among points between 120 and 130
                    pass
                # Ensure a null break between the two valid samples
                ts = []
                for pt in dist:
                    if isinstance(pt, list) and pt:
                        ts.append((float(pt[0]), pt[1] if len(pt) > 1 else None))
                    elif pt is None:
                        ts.append((None, None))
                between_null = False
                seen_120 = False
                for t, val in ts:
                    if t == 120.0:
                        seen_120 = True
                    if seen_120 and (pt_is_null := (t is None or val is None)):
                        between_null = True
                    if t == 130.0:
                        break
                if not between_null:
                    raise SystemExit(f"no null break between T+120 and T+130 in {ts}")

                table = page.locator('[data-testid="registered-metric-table"]')
                expect(table).to_be_visible()
                table_text = table.inner_text()
                if page.locator('[data-testid="registered-metric-table"] tbody tr').count() != 2:
                    raise SystemExit(f"expected two metric rows: {table_text}")
                for t, exp in EXPECTED.items():
                    for key, unit in (("distanceNm", "nm"), ("dcpaNm", "nm"), ("tcpaMin", "min")):
                        token = f"{exp[key]:.6f} {unit}"
                        if token not in table_text:
                            raise SystemExit(f"table missing {token}: {table_text}")
                if "T+124.25" in table_text or "T+121" in table_text or "T+127.5" in table_text:
                    raise SystemExit(f"non-cotemporal instants appeared in metric table: {table_text}")

                status_text = page.locator('[data-testid="sample-status-table"]').inner_text()
                if "无 A 样位" not in status_text or "非双船同刻" not in status_text:
                    raise SystemExit(f"sample status missing gap/endpoint wording: {status_text}")

                body = page.locator("body").inner_text()
                if "已自检" in body or "装配占位" in body or "种子生成" in body:
                    raise SystemExit("registered view still shows placeholder seed wording")
                sources = page.locator('[data-testid="sources"]').inner_text()
                if "mcis-core.dll" not in sources or dll not in sources:
                    raise SystemExit(f"core source missing: {sources}")
                for ident in snapshot["complete"]["registeredIdentities"]:
                    if ident["requestDigest"] not in body or ident["sourceSha256"] not in body:
                        raise SystemExit(f"identity {ident['vesselId']} not shown")
                if "(60,100)" not in body and "60,100" not in body.replace(" ", ""):
                    if "60" not in page.locator('[data-testid="gap-wiring"]').inner_text():
                        raise SystemExit("declared gaps not shown")
                caption = page.locator('[data-testid="metric-caption"]').inner_text()
                if "真实核心" not in caption:
                    raise SystemExit(f"caption missing core label: {caption}")

                before_hover = http_json(origin + "/assembly/api/custody-counts")
                # Hover the chart; this must not reread originals.
                box = page.locator("canvas").first.bounding_box()
                if box:
                    page.mouse.move(box["x"] + box["width"] * 0.55, box["y"] + box["height"] * 0.4)
                    page.wait_for_timeout(300)
                after_hover = http_json(origin + "/assembly/api/custody-counts")
                if after_hover.get("access") != before_hover.get("access"):
                    raise SystemExit(f"hover reread originals: {before_hover} -> {after_hover}")
                if after_hover.get("access") != 2:
                    raise SystemExit(f"expected 2 Access after snapshot+hover, got {after_hover}")

                page.screenshot(path=str(shots / "complete-fullpage.png"), full_page=True)
                page.locator("canvas").first.screenshot(path=str(shots / "complete-curve.png"))
                table.screenshot(path=str(shots / "complete-metric-table.png"))
                page.locator('[data-testid="sample-status-table"]').screenshot(path=str(shots / "complete-sample-status.png"))
                page.locator('[data-testid="sources"]').screenshot(path=str(shots / "complete-sources.png"))
                page.locator('[data-testid="registered-identities"]').screenshot(path=str(shots / "complete-identities.png"))

                # Denied / unpaired: no metrics, no chart
                page.locator('[data-testid="assembly-switcher"] [data-view="denied"]').click()
                expect(page.locator('[data-testid="w12-rjg-assembly"]')).to_have_attribute("data-view", "denied")
                denied_text = page.locator('[data-testid="denied-analysis"]').inner_text()
                lowered = denied_text.lower()
                if "policy-deny" not in lowered or "403" not in denied_text or "metricsreturned=false" not in lowered:
                    raise SystemExit(f"denied view incomplete: {denied_text!r}")
                for exp in EXPECTED.values():
                    for val in exp.values():
                        if f"{val:.6f}" in denied_text or str(val) in denied_text:
                            raise SystemExit(f"denied view leaked metric {val}")
                if page.locator("canvas").count() != 0:
                    raise SystemExit("denied view has a chart")
                page.screenshot(path=str(shots / "denied-fullpage.png"), full_page=True)

                page.locator('[data-testid="assembly-switcher"] [data-view="unpaired"]').click()
                expect(page.locator('[data-testid="w12-rjg-assembly"]')).to_have_attribute("data-view", "unpaired")
                unpaired_text = page.locator('[data-testid="unpaired-analysis"]').inner_text()
                if "TWO_PINS_REQUIRED" not in unpaired_text or "metricsreturned=false" not in unpaired_text.lower():
                    raise SystemExit(f"unpaired view incomplete: {unpaired_text!r}")
                for exp in EXPECTED.values():
                    for val in exp.values():
                        if f"{val:.6f}" in unpaired_text:
                            raise SystemExit(f"unpaired view leaked metric {val}")
                if page.locator("canvas").count() != 0:
                    raise SystemExit("unpaired view has a chart")
                page.screenshot(path=str(shots / "unpaired-fullpage.png"), full_page=True)

                # 390px source summary: no full-page horizontal scroll
                page.locator('[data-testid="assembly-switcher"] [data-view="complete"]').click()
                expect(page.locator('[data-testid="w12-rjg-assembly"]')).to_have_attribute("data-view", "complete")
                page.set_viewport_size({"width": 390, "height": 844})
                page.evaluate("() => window.dispatchEvent(new Event('resize'))")
                page.wait_for_timeout(500)
                scroll = page.evaluate(
                    """() => ({
                      innerWidth: window.innerWidth,
                      documentElementScrollWidth: document.documentElement.scrollWidth,
                      bodyScrollWidth: document.body.scrollWidth
                    })"""
                )
                write_json(official / "narrow-390.json", scroll)
                if scroll["documentElementScrollWidth"] > 390 + 1 or scroll["bodyScrollWidth"] > 390 + 1:
                    page.screenshot(path=str(shots / "narrow-390-overflow.png"), full_page=True)
                    raise SystemExit(f"390px full-page horizontal scroll: {scroll}")
                page.locator('[data-testid="sources"]').scroll_into_view_if_needed()
                page.locator('[data-testid="sources"]').screenshot(path=str(shots / "narrow-390-sources.png"))
                page.screenshot(path=str(shots / "narrow-390-fullpage.png"), full_page=True)

                results["browser"] = {
                    "ok": True,
                    "symbolFlags": symbol_flags,
                    "hoverAccess": after_hover,
                    "narrow390": scroll,
                    "caption": caption,
                }
                log(logs, "browser checks ok")
            finally:
                browser.close()
        results["ok"] = True
    finally:
        if host.poll() is None:
            host.terminate()
            try:
                rest, _ = host.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                host.kill()
                rest, _ = host.communicate(timeout=5)
        else:
            rest = host.stdout.read() if host.stdout else ""
        (official / "host-log.txt").write_text(rest or "", encoding="utf-8")
        log(logs, f"host exit={host.returncode}")

    ended = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    results.update(started=started, ended=ended, port=args.port, origin=origin, coreDllSha256=dll)
    write_json(official / "summary.json", results)
    (official / "run.log").write_text("\n".join(logs) + "\n", encoding="utf-8")
    log(logs, f"official end {ended} ok={results['ok']}")
    return 0 if results["ok"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"UNCAUGHT {type(exc).__name__}: {exc}", flush=True)
        raise
