#!/usr/bin/env python3
"""Official isolated-host browser run: first-registered receipts wired to AnalysisView."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
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

HERE = Path(__file__).resolve().parent
DEFAULT_WORKTREE = HERE.parents[1]
CHROME = "/opt/google/chrome/chrome"
CORE_DLL_SHA256 = "f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf"
CORE_RUNTIME_SHA256 = "3d25821758613e4cd940d143ccb03c93704140077e69104996832510f38f6598"
CORE_DEPS_SHA256 = "fda133109cf9fc926cbda09598ad344f75dc57ec02e345b6923ec5fe2dff9d12"
CPA_CS_SHA256 = "54de148e91e27a4ca39c693410722e42caf88fcb58e339dc3907161dc9210d6c"
WRAPPER_SHA256 = "a19eea96864ef424ea9cd1a3541b1c845791d2fd2bb52a2f65b5bff9684096a8"
LOCK_SHA = "e90ca8de08746df1b599de506be1f6d9fe35fa9a67d8a2e55371eed1130e69eb"
LEAK = "9.999"


def log(logs: list[str], msg: str) -> None:
    logs.append(msg)
    print(msg, flush=True)


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def json_strict(obj):
    """Replace non-finite floats (ECharts Infinity) with null. Drop non-JSON values. Do not change runtime options."""
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
            "name": s.get("name"),
            "type": s.get("type"),
            "showSymbol": s.get("showSymbol"),
            "showAllSymbol": s.get("showAllSymbol"),
            "symbol": s.get("symbol"),
            "symbolSize": s.get("symbolSize"),
            "connectNulls": s.get("connectNulls"),
            "yAxisIndex": s.get("yAxisIndex"),
            "data": s.get("data"),
        }))
    xaxis = option.get("xAxis")
    if isinstance(xaxis, list):
        xaxis = xaxis[0] if xaxis else {}
    x_out = None
    if isinstance(xaxis, dict):
        x_out = json_strict({"type": xaxis.get("type"), "data": xaxis.get("data")})
    return {"xAxis": x_out, "series": series_out}


EXPECTED_VISIBLE = {
    10.0: {"distanceNm": 2.578139, "dcpaNm": 1.822610, "tcpaMin": 7.736156},
    20.0: {"distanceNm": 2.147531, "dcpaNm": 1.881462, "tcpaMin": 4.392701},
}


def same6(actual, expected) -> bool:
    if actual is None or expected is None:
        return actual is None and expected is None
    return round(float(actual), 6) == round(float(expected), 6)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_sha(path: Path, expected: str, label: str) -> str:
    actual = sha256(path)
    if actual != expected:
        raise SystemExit(f"SHA mismatch for {label}: {actual} != {expected}")
    return actual


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
        log(logs, proc.stdout)
        log(logs, proc.stderr)
        raise SystemExit("assembly esbuild failed")
    log(logs, f"assembly app.js sha256={sha256(assembly / 'app.js')}")
    return assembly


def wait_ready(url: str, proc: subprocess.Popen, timeout: float, logs: list[str]) -> str:
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
            if "W12_FRW_READY=" in line:
                return buf
        else:
            time.sleep(0.05)
    raise SystemExit(f"timeout waiting for host ready\n{buf}")


def http_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def option_series(option: dict, name: str) -> list:
    for s in option.get("series") or []:
        n = s.get("name") if isinstance(s, dict) else None
        if n == name or (isinstance(n, list) and name in n):
            return s.get("data") or []
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True, help="service venv python (do not resolve through the symlink)")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--worktree", type=Path, default=DEFAULT_WORKTREE)
    parser.add_argument("--browser", type=Path, default=Path(CHROME))
    parser.add_argument("--port", type=int, default=18777)
    parser.add_argument("--core-dir", type=Path, default=Path("/workspace/mcis-w41-core-out"))
    parser.add_argument("--dotnet", default=os.path.expanduser("~/.dotnet/dotnet"))
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
    log(logs, f"locked official dll {dll}")

    ensure_node_modules(worktree, logs)
    run_existing_regressions(worktree, official, logs)
    assembly = build_assembly(worktree, official, logs)

    store = official / "tmp-store"
    if store.exists():
        shutil.rmtree(store)
    store.mkdir()

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
    host_cmd = [
        str(Path(args.python)), "-I", "-B", str(HERE / "host.py"),
        str(assembly), str(store), str(official),
        str(worktree / "service"), str(HERE / "core_norebuild.sh"), str(core_dir),
        "127.0.0.1", str(args.port),
    ]
    log(logs, "host " + " ".join(host_cmd))
    host = subprocess.Popen(host_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    origin = f"http://127.0.0.1:{args.port}"
    results: dict = {"ok": False, "regression31": True, "regression96": True}
    try:
        wait_ready(origin, host, 40, logs)
        payload = http_json(origin + "/assembly/api/registered")
        write_json(official / "registered-api.json", {
            "identities": payload.get("complete", {}).get("registeredIdentities"),
            "provenance": payload.get("complete", {}).get("metricProvenance"),
            "gapWiring": payload.get("complete", {}).get("gapWiring"),
            "series": payload.get("complete", {}).get("baseline", {}).get("series"),
            "missing": payload.get("missing"),
            "liveSeedSha256": payload.get("liveSeedSha256"),
        })
        live = http_json(origin + "/api/v1/cases/SYN-W12-LIVE-ENTRY/analysis")
        write_json(official / "live-entry-analysis.json", {"caseId": live.get("caseId"), "hasDeclaredOpenGaps": "declaredOpenGaps" in live, "leakSeries": live.get("baseline", {}).get("series")})
        if live.get("caseId") != "SYN-W12-LIVE-ENTRY":
            raise SystemExit("live entry missing")

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
                expect(page.locator('[data-testid="w12-frw-assembly"]')).to_have_attribute("data-view", "complete")
                page.wait_for_function("() => document.querySelectorAll('canvas').length >= 1")
                # Public EChart must not default-attach test handles.
                handle_probe = page.evaluate(
                    """() => {
                      const canvases = [...document.querySelectorAll('canvas')];
                      const parents = canvases.map((c) => c.parentElement);
                      return {
                        defaultTestId: parents.some((p) => p && p.getAttribute('data-testid') === 'echart'),
                        hungOption: parents.some((p) => p && '__echartsOption' in p),
                        hungInstance: parents.some((p) => p && '__echartsInstance' in p),
                      };
                    }"""
                )
                option_probe = page.evaluate(
                    """() => {
                      const root = window.echarts;
                      const api = root && (typeof root.getInstanceByDom === 'function' ? root : root.default);
                      const canvases = [...document.querySelectorAll('canvas')];
                      const tried = [];
                      let option = null;
                      for (const c of canvases) {
                        let el = c.parentElement;
                        for (let i = 0; i < 3 && el; i++) {
                          const inst = api && api.getInstanceByDom(el);
                          tried.push({tag: el.tagName, hasInst: !!inst});
                          if (inst) { option = inst.getOption(); break; }
                          el = el.parentElement;
                        }
                        if (option) break;
                      }
                      return {
                        option,
                        hasRoot: !!root,
                        hasGet: !!(api && api.getInstanceByDom),
                        canvasCount: canvases.length,
                        tried,
                      };
                    }"""
                )
                write_json(official / "echarts-getoption-probe.json", json_strict({k: option_probe.get(k) for k in option_probe if k != "option"}))
                option = option_probe.get("option")
                exported = export_needed_option(option) if isinstance(option, dict) else json_strict(option)
                write_json(official / "echarts-getoption.json", exported)
                write_json(official / "echart-handle-probe.json", handle_probe)
                if not option:
                    page.screenshot(path=str(shots / "debug-no-option.png"), full_page=True)
                    raise SystemExit(f"echarts.getInstanceByDom returned no option: { {k: option_probe.get(k) for k in option_probe if k != 'option'} }")
                if handle_probe["defaultTestId"] or handle_probe["hungOption"] or handle_probe["hungInstance"]:
                    raise SystemExit(f"public EChart still exposes default handles: {handle_probe}")

                series_by_t = {p["t"]: p for p in payload["complete"]["baseline"]["series"]}
                dist = option_series(option, "两船距离 D(t)")
                dcpa = option_series(option, "DCPA(t)")
                tcpa = option_series(option, "TCPA(t)")
                # category axis: data arrays align with series order 0,10,15,20,30,40
                expected_times = [0.0, 10.0, 15.0, 20.0, 30.0, 40.0]
                chart_checks = {}
                symbol_flags = []
                for s in option.get("series") or []:
                    if not isinstance(s, dict):
                        continue
                    name = s.get("name")
                    if name in {"两船距离 D(t)", "DCPA(t)", "TCPA(t)"}:
                        flags = {
                            "name": name,
                            "showSymbol": s.get("showSymbol"),
                            "connectNulls": s.get("connectNulls"),
                            "symbolSize": s.get("symbolSize"),
                        }
                        symbol_flags.append(flags)
                        def unwrap(v):
                            if isinstance(v, list) and v:
                                return v[0]
                            return v
                        show = unwrap(s.get("showSymbol"))
                        connect = unwrap(s.get("connectNulls"))
                        flags["showSymbol"] = show
                        flags["connectNulls"] = connect
                        if show is not True:
                            raise SystemExit(f"{name} showSymbol is {s.get('showSymbol')}, expected true for isolated registered points")
                        if connect is True:
                            raise SystemExit(f"{name} connectNulls is true; must not join across nulls")
                if len(symbol_flags) != 3:
                    raise SystemExit(f"expected 3 curve series flags, got {symbol_flags}")

                for i, t in enumerate(expected_times):
                    row = series_by_t[t]
                    chart_checks[f"t{t:g}"] = {
                        "distance": dist[i] if i < len(dist) else None,
                        "dcpa": dcpa[i] if i < len(dcpa) else None,
                        "tcpa": tcpa[i] if i < len(tcpa) else None,
                        "expectedDistance": row["distanceNm"],
                        "expectedDcpa": row["dcpaNm"],
                        "expectedTcpa": row["tcpaMin"],
                    }
                    if row["distanceNm"] is None:
                        if dist[i] not in (None, "-") or dcpa[i] not in (None, "-") or tcpa[i] not in (None, "-"):
                            raise SystemExit(f"non-common t={t} displayed a metric: {dist[i], dcpa[i], tcpa[i]}")
                    else:
                        if dist[i] != row["distanceNm"] or dcpa[i] != row["dcpaNm"] or tcpa[i] != row["tcpaMin"]:
                            raise SystemExit(f"t={t} chart {dist[i], dcpa[i], tcpa[i]} != core {row['distanceNm'], row['dcpaNm'], row['tcpaMin']}")
                        exp = EXPECTED_VISIBLE[t]
                        if not (same6(dist[i], exp["distanceNm"]) and same6(dcpa[i], exp["dcpaNm"]) and same6(tcpa[i], exp["tcpaMin"])):
                            raise SystemExit(f"t={t} chart did not match pinned visible values {exp}")

                # T+15 sits between the two valid points; a null there proves the line cannot cross.
                t15 = expected_times.index(15.0)
                if dist[t15] not in (None, "-") or dcpa[t15] not in (None, "-") or tcpa[t15] not in (None, "-"):
                    raise SystemExit("T+15 unexpectedly has a chart point")
                if dist[expected_times.index(10.0)] in (None, "-") or dist[expected_times.index(20.0)] in (None, "-"):
                    raise SystemExit("T+10 or T+20 missing a chart value")

                table = page.locator('[data-testid="registered-metric-table"]')
                expect(table).to_be_visible()
                table.focus()
                focused = page.evaluate("() => document.activeElement && document.activeElement.getAttribute('data-testid')")
                if focused != "registered-metric-table":
                    raise SystemExit(f"metric table did not take keyboard focus: {focused}")
                table_text = table.inner_text()
                row_count = page.locator('[data-testid="registered-metric-table"] tbody tr').count()
                if row_count != 2:
                    raise SystemExit(f"expected two readable metric rows, got {row_count}: {table_text}")
                if "08:00:15" in table_text or "T+15" in table_text:
                    raise SystemExit(f"T+15 appeared in the readable table: {table_text}")
                for unit in ("nm", "min"):
                    if unit not in table_text:
                        raise SystemExit(f"unit {unit} missing from readable table: {table_text}")
                table_rows = {}
                for handle in page.locator('[data-testid="registered-metric-table"] tbody tr').all():
                    t_attr = handle.get_attribute("data-t")
                    cells = handle.locator("th, td").all_inner_texts()
                    table_rows[float(t_attr)] = cells
                table_checks = {}
                for t, exp in EXPECTED_VISIBLE.items():
                    if t not in table_rows:
                        raise SystemExit(f"T+{t:g} missing from readable table rows {list(table_rows)}")
                    cells = table_rows[t]
                    joined = " ".join(cells)
                    got = {}
                    for key, unit in (("distanceNm", "nm"), ("dcpaNm", "nm"), ("tcpaMin", "min")):
                        token = f"{exp[key]:.6f} {unit}"
                        if token not in joined:
                            raise SystemExit(f"T+{t:g} table missing {token} in {cells}")
                        got[key] = token
                    table_checks[f"t{t:g}"] = got
                if 15.0 in table_rows:
                    raise SystemExit("T+15 row present in readable table")

                body = page.locator("body").inner_text()
                identities = payload["complete"]["registeredIdentities"]
                for ident in identities:
                    if ident["previewDigest"] not in body or ident["sourceSha256"] not in body or ident["reportSha256"] not in body:
                        raise SystemExit(f"identity for {ident['vesselId']} not shown")
                sources = page.locator('[data-testid="sources"]').inner_text()
                core_sha = payload["complete"]["meta"]["coreDll"]["sha256"]
                if "mcis-core.dll" not in sources or core_sha not in sources:
                    raise SystemExit(f"core source missing from registered sources table: {sources}")
                if "已自检" in body or "未自检" in body:
                    raise SystemExit("registered view still shows seed self-check wording")
                if "种子生成" in body or "种子 sha256" in body:
                    raise SystemExit("registered view still shows placeholder seed generation/hash")
                if "ffffffff" in body.lower() or "ffff…" in body or "ffff..." in body:
                    raise SystemExit("registered view still displays ffff placeholder seed")
                if "装配占位" in body:
                    raise SystemExit("registered view still shows assembly-placeholder wording")
                caption = page.locator('[data-testid="metric-caption"]').inner_text()
                provenance = page.locator('[data-testid="metric-provenance"]').inner_text()
                gap = page.locator('[data-testid="gap-wiring"]').inner_text()
                if "真实核心" not in caption and "真实核心" not in provenance:
                    raise SystemExit(f"caption/provenance missing core label: {caption} {provenance}")
                if "装配占位" in caption or ("由 mcis-core cpa 计算" in caption and "图区来源区分" not in caption):
                    raise SystemExit(f"caption still claims placeholder or undifferentiated core: {caption}")
                if "未接" not in gap or "显式缺口" not in gap:
                    raise SystemExit(f"gap wiring not explained: {gap}")
                if LEAK in body:
                    raise SystemExit("live-entry leak value appeared on complete view")

                page.screenshot(path=str(shots / "complete-fullpage.png"), full_page=True)
                page.locator("canvas").first.screenshot(path=str(shots / "complete-curve.png"))
                table.screenshot(path=str(shots / "complete-metric-table.png"))
                page.locator('[data-testid="metric-provenance"]').screenshot(path=str(shots / "complete-provenance.png"))
                page.locator('[data-testid="registered-identities"]').screenshot(path=str(shots / "complete-identities.png"))
                page.locator('[data-testid="sources"]').screenshot(path=str(shots / "complete-sources.png"))

                page.locator('[data-testid="assembly-switcher"] [data-view="missing"]').click()
                expect(page.locator('[data-testid="w12-frw-assembly"]')).to_have_attribute("data-view", "missing")
                expect(page.locator('[data-testid="missing-analysis"]')).to_be_visible()
                missing_text = page.locator('[data-testid="missing-analysis"]').inner_text()
                if "missing-receipt:SYN-TGT" not in missing_text:
                    raise SystemExit(f"missing reason not shown: {missing_text}")
                if "不显示" not in missing_text and "未用离线种子" not in missing_text:
                    raise SystemExit(f"missing note incomplete: {missing_text}")
                if LEAK in missing_text or LEAK in page.locator("body").inner_text():
                    raise SystemExit("offline seed leaked into missing-receipt view")
                # no core metrics on missing view
                for t in (10.0, 20.0):
                    row = series_by_t[t]
                    for val in (str(row["distanceNm"]), str(row["dcpaNm"]), str(row["tcpaMin"])):
                        if val in missing_text:
                            raise SystemExit(f"core metric {val} appeared on missing view")
                if page.locator("canvas").count() != 0:
                    raise SystemExit("missing view unexpectedly has a chart")
                page.screenshot(path=str(shots / "missing-fullpage.png"), full_page=True)
                page.locator('[data-testid="missing-analysis"]').screenshot(path=str(shots / "missing-panel.png"))

                results["browser"] = {
                    "ok": True,
                    "handleProbe": handle_probe,
                    "chartChecks": chart_checks,
                    "symbolFlags": symbol_flags,
                    "tableChecks": table_checks,
                    "tableFocused": focused,
                    "tableRowCount": row_count,
                    "caption": caption,
                    "provenance": provenance,
                    "gapWiring": gap,
                    "identitiesShown": [i["previewDigest"] for i in identities],
                    "sourcesHasCore": "mcis-core.dll" in sources,
                }
                log(logs, f"browser checks ok caption={caption!r}")
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
